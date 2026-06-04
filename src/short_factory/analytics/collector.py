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


def collect_youtube_analytics(publication_id: int) -> dict:
    db = SessionLocal()
    try:
        publication = db.get(Publication, publication_id)
        if not publication or publication.platform != Platform.YOUTUBE:
            raise ValueError(f"Publication {publication_id} not found or not YouTube")

        if publication.external_id and not publication.external_id.startswith("stub_"):
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


def _fetch_youtube_metrics(video_id: str) -> dict:
    from short_factory.config.settings import settings

    if not settings.youtube_api_key:
        return _mock_metrics(0)

    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)
    response = youtube.videos().list(part="statistics", id=video_id).execute()
    items = response.get("items", [])
    if not items:
        return _mock_metrics(0)

    stats = items[0].get("statistics", {})
    views = int(stats.get("viewCount", 0))
    comments = int(stats.get("commentCount", 0))
    return {
        "views": views,
        "comments": comments,
        "shares": 0,
        "ctr": 0.05,
        "avg_view_duration_sec": 28.0,
        "retention_rate": 0.65,
    }


def _mock_metrics(publication_id: int) -> dict:
    seed = publication_id * 17
    return {
        "views": 1000 + seed * 10,
        "comments": 20 + seed,
        "shares": 5 + seed // 2,
        "ctr": 0.04 + (seed % 10) / 100,
        "avg_view_duration_sec": 25.0 + (seed % 15),
        "retention_rate": 0.5 + (seed % 30) / 100,
    }


def run_optimization_feedback() -> dict:
    """Apply rule-based feedback loop to optimization weights."""
    db = SessionLocal()
    try:
        events = db.query(AnalyticsEvent).all()
        if not events:
            return {"updated": 0}

        category_scores: dict[str, list[float]] = {}
        emotion_scores: dict[str, list[float]] = {}

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

        updated = 0
        for dimension, scores_map in [("category", category_scores), ("emotion", emotion_scores)]:
            for value, scores in scores_map.items():
                avg = sum(scores) / len(scores)
                weight = min(2.0, max(0.5, 0.5 + avg))
                existing = (
                    db.query(OptimizationWeight)
                    .filter(OptimizationWeight.dimension == dimension, OptimizationWeight.value == value)
                    .first()
                )
                if existing:
                    existing.weight = weight
                else:
                    db.add(OptimizationWeight(dimension=dimension, value=value, weight=weight))
                updated += 1

        db.commit()
        logger.info("optimization_feedback_applied", weights_updated=updated)
        return {"updated": updated, "categories": len(category_scores), "emotions": len(emotion_scores)}
    finally:
        db.close()


def get_performance_summary() -> dict:
    db = SessionLocal()
    try:
        events = db.query(AnalyticsEvent).all()
        if not events:
            return {"total_views": 0, "avg_retention": 0, "publications": 0}

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
