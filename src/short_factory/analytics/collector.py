from datetime import date, timedelta

from short_factory.config.logging import get_logger
from short_factory.db.models import (
    AnalyticsEvent,
    OptimizationWeight,
    Platform,
    Publication,
    Script,
    Topic,
)
from short_factory.db.session import SessionLocal

logger = get_logger(__name__)


def _normalize_hook(hook: str) -> str:
    return hook.strip()[:120]


def collect_youtube_analytics(publication_id: int) -> dict:
    db = SessionLocal()
    try:
        publication = db.get(Publication, publication_id)
        if not publication or publication.platform != Platform.YOUTUBE:
            raise ValueError(f"Publication {publication_id} not found or not YouTube")

        if publication.external_id and not publication.external_id.startswith(
            ("stub_", "dry_run_")
        ):
            metrics = _fetch_youtube_metrics(publication.external_id)
        else:
            metrics = _mock_metrics(publication_id)

        event = AnalyticsEvent(
            publication_id=publication_id,
            views=metrics.get("views"),
            avg_view_duration_sec=metrics.get("avg_view_duration_sec"),
            ctr=metrics.get("ctr"),
            comments=metrics.get("comments"),
            shares=metrics.get("shares"),
            retention_rate=metrics.get("retention_rate"),
            raw_data=metrics,
        )
        db.add(event)
        db.commit()
        return metrics
    finally:
        db.close()


def _youtube_credentials():
    from short_factory.config.settings import settings

    if not (
        settings.youtube_refresh_token
        and settings.youtube_client_id
        and settings.youtube_client_secret
    ):
        return None

    from google.oauth2.credentials import Credentials

    return Credentials(
        token=None,
        refresh_token=settings.youtube_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.youtube_client_id,
        client_secret=settings.youtube_client_secret,
    )


def _fetch_youtube_metrics(video_id: str) -> dict:
    from short_factory.config.settings import settings

    metrics: dict = {}

    if settings.youtube_api_key:
        from googleapiclient.discovery import build

        youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)
        response = youtube.videos().list(part="statistics", id=video_id).execute()
        items = response.get("items", [])
        if items:
            stats = items[0].get("statistics", {})
            metrics.update(
                {
                    "views": int(stats.get("viewCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "shares": 0,
                }
            )

    analytics = _fetch_youtube_analytics_report(video_id)
    metrics.update(analytics)

    if not metrics:
        return _mock_metrics(0)

    if "retention_rate" not in metrics:
        metrics["retention_rate"] = min(
            1.0,
            (metrics.get("avg_view_duration_sec") or 0) / 45.0,
        )
    if "ctr" not in metrics:
        metrics["ctr"] = 0.05
    metrics["source"] = "youtube_api"
    return metrics


def _fetch_youtube_analytics_report(video_id: str) -> dict:
    from short_factory.config.settings import settings

    creds = _youtube_credentials()
    if not creds or not settings.youtube_channel_id:
        return {}

    try:
        from googleapiclient.discovery import build

        analytics = build("youtubeAnalytics", "v2", credentials=creds)
        end = date.today()
        start = end - timedelta(days=28)
        response = (
            analytics.reports()
            .query(
                ids=f"channel=={settings.youtube_channel_id}",
                startDate=start.isoformat(),
                endDate=end.isoformat(),
                metrics="views,estimatedMinutesWatched,averageViewDuration,annotationClickThroughRate",
                filters=f"video=={video_id}",
            )
            .execute()
        )
        rows = response.get("rows", [])
        if not rows:
            return {}

        row = rows[0]
        views = int(row[0]) if len(row) > 0 else 0
        avg_view_duration_sec = float(row[2]) if len(row) > 2 else 0.0
        ctr = float(row[3]) if len(row) > 3 else 0.0
        retention_rate = min(1.0, avg_view_duration_sec / 45.0) if avg_view_duration_sec else 0.0
        return {
            "views": views,
            "avg_view_duration_sec": avg_view_duration_sec,
            "ctr": ctr,
            "retention_rate": retention_rate,
            "analytics_api": True,
        }
    except Exception as exc:
        logger.warning("youtube_analytics_api_failed", video_id=video_id, error=str(exc))
        return {}


def _mock_metrics(publication_id: int) -> dict:
    seed = publication_id * 17
    return {
        "views": 1000 + seed * 10,
        "comments": 20 + seed,
        "shares": 5 + seed // 2,
        "ctr": 0.04 + (seed % 10) / 100,
        "avg_view_duration_sec": 25.0 + (seed % 15),
        "retention_rate": 0.5 + (seed % 30) / 100,
        "source": "mock",
    }


def _upsert_weight(db, dimension: str, value: str, weight: float) -> None:
    existing = (
        db.query(OptimizationWeight)
        .filter(OptimizationWeight.dimension == dimension, OptimizationWeight.value == value)
        .first()
    )
    if existing:
        existing.weight = weight
    else:
        db.add(OptimizationWeight(dimension=dimension, value=value, weight=weight))


def run_optimization_feedback() -> dict:
    """Apply rule-based feedback loop to optimization weights."""
    db = SessionLocal()
    try:
        events = db.query(AnalyticsEvent).all()
        if not events:
            return {"updated": 0}

        category_scores: dict[str, list[float]] = {}
        emotion_scores: dict[str, list[float]] = {}
        hook_scores: dict[str, list[float]] = {}

        for event in events:
            pub = db.get(Publication, event.publication_id)
            if not pub or not pub.video:
                continue
            script = db.get(Script, pub.video.script_id)
            if not script:
                continue
            topic = db.get(Topic, script.topic_id)
            if not topic:
                continue

            score = (event.retention_rate or 0) * 0.6 + (event.ctr or 0) * 0.4
            category_scores.setdefault(topic.category or "unknown", []).append(score)
            emotion_scores.setdefault(topic.emotion or "unknown", []).append(score)
            hook_scores.setdefault(_normalize_hook(script.hook), []).append(score)

        updated = 0
        for dimension, scores_map in [
            ("category", category_scores),
            ("emotion", emotion_scores),
            ("hook_pattern", hook_scores),
        ]:
            for value, scores in scores_map.items():
                avg = sum(scores) / len(scores)
                weight = min(2.0, max(0.5, 0.5 + avg))
                _upsert_weight(db, dimension, value, weight)
                updated += 1

        db.commit()
        report = generate_weekly_report()
        logger.info("optimization_feedback_applied", weights_updated=updated)
        return {
            "updated": updated,
            "categories": len(category_scores),
            "emotions": len(emotion_scores),
            "hook_patterns": len(hook_scores),
            "report_path": report.get("path"),
        }
    finally:
        db.close()


def generate_weekly_report() -> dict:
    from pathlib import Path

    from short_factory.config.settings import settings

    summary = get_performance_summary()
    top_topics = get_top_topics(limit=5)
    top_scripts = get_top_scripts(limit=5)
    report = {
        "generated_at": date.today().isoformat(),
        "summary": summary,
        "top_topics": top_topics,
        "top_scripts": top_scripts,
    }
    report_dir = Path(settings.render_dir) / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"weekly-report-{date.today().isoformat()}.json"
    report_path.write_text(__import__("json").dumps(report, indent=2))
    return {"path": str(report_path), "report": report}


def get_performance_summary() -> dict:
    db = SessionLocal()
    try:
        events = db.query(AnalyticsEvent).all()
        if not events:
            return {"total_views": 0, "avg_retention": 0, "publications": 0, "top_categories": []}

        total_views = sum(e.views or 0 for e in events)
        retentions = [e.retention_rate for e in events if e.retention_rate is not None]
        avg_retention = sum(retentions) / len(retentions) if retentions else 0

        weights = db.query(OptimizationWeight).all()
        top_categories = sorted(
            [w for w in weights if w.dimension == "category"],
            key=lambda w: w.weight,
            reverse=True,
        )[:5]

        return {
            "total_views": total_views,
            "avg_retention": round(avg_retention, 3),
            "publications": len(events),
            "top_categories": [{"value": w.value, "weight": w.weight} for w in top_categories],
        }
    finally:
        db.close()


def _performance_by_entity(entity: str, limit: int = 10) -> list[dict]:
    db = SessionLocal()
    try:
        events = db.query(AnalyticsEvent).all()
        aggregates: dict[int, dict] = {}

        for event in events:
            pub = db.get(Publication, event.publication_id)
            if not pub or not pub.video:
                continue
            script = db.get(Script, pub.video.script_id)
            if not script:
                continue

            entity_id = script.topic_id if entity == "topic" else script.id
            bucket = aggregates.setdefault(
                entity_id,
                {"views": 0, "retention_total": 0.0, "retention_count": 0, "ctr_total": 0.0, "ctr_count": 0},
            )
            bucket["views"] += event.views or 0
            if event.retention_rate is not None:
                bucket["retention_total"] += event.retention_rate
                bucket["retention_count"] += 1
            if event.ctr is not None:
                bucket["ctr_total"] += event.ctr
                bucket["ctr_count"] += 1

        results: list[dict] = []
        for entity_id, stats in aggregates.items():
            if entity == "topic":
                row = db.get(Topic, entity_id)
                label = row.topic if row else str(entity_id)
                category = row.category if row else None
            else:
                row = db.get(Script, entity_id)
                label = row.hook if row else str(entity_id)
                category = None

            avg_retention = (
                stats["retention_total"] / stats["retention_count"]
                if stats["retention_count"]
                else 0.0
            )
            avg_ctr = stats["ctr_total"] / stats["ctr_count"] if stats["ctr_count"] else 0.0
            score = avg_retention * 0.6 + avg_ctr * 0.4
            results.append(
                {
                    "id": entity_id,
                    "label": label,
                    "category": category,
                    "views": stats["views"],
                    "avg_retention": round(avg_retention, 3),
                    "avg_ctr": round(avg_ctr, 3),
                    "score": round(score, 3),
                }
            )

        return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]
    finally:
        db.close()


def get_top_topics(limit: int = 10) -> list[dict]:
    return _performance_by_entity("topic", limit)


def get_top_scripts(limit: int = 10) -> list[dict]:
    return _performance_by_entity("script", limit)


def get_category_performance() -> list[dict]:
    db = SessionLocal()
    try:
        events = db.query(AnalyticsEvent).all()
        by_category: dict[str, list[float]] = {}

        for event in events:
            pub = db.get(Publication, event.publication_id)
            if not pub or not pub.video:
                continue
            script = db.get(Script, pub.video.script_id)
            if not script:
                continue
            topic = db.get(Topic, script.topic_id)
            if not topic:
                continue
            score = (event.retention_rate or 0) * 0.6 + (event.ctr or 0) * 0.4
            by_category.setdefault(topic.category or "unknown", []).append(score)

        return [
            {
                "category": category,
                "avg_score": round(sum(scores) / len(scores), 3),
                "samples": len(scores),
            }
            for category, scores in sorted(
                by_category.items(),
                key=lambda item: sum(item[1]) / len(item[1]),
                reverse=True,
            )
        ]
    finally:
        db.close()
