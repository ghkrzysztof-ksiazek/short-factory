from short_factory.config.logging import get_logger
from short_factory.db.models import Topic
from short_factory.db.session import SessionLocal
from short_factory.research.classifier import classify_and_score, is_duplicate
from short_factory.research.reddit_scraper import scrape_reddit
from short_factory.research.tiktok_scraper import scrape_tiktok
from short_factory.research.trends_scraper import scrape_google_trends
from short_factory.research.youtube_scraper import scrape_youtube
from short_factory.shared.optimization import get_category_weight, get_emotion_weight

logger = get_logger(__name__)


def run_research_pipeline() -> dict:
    raw_topics = scrape_reddit() + scrape_youtube() + scrape_tiktok() + scrape_google_trends()
    logger.info("research_scraped", count=len(raw_topics))

    db = SessionLocal()
    try:
        existing = [t.topic for t in db.query(Topic.topic).all()]
        created = 0
        skipped = 0

        for raw in raw_topics:
            if is_duplicate(raw.title, existing):
                skipped += 1
                continue

            scored = classify_and_score(raw)
            category_weight = get_category_weight(scored.get("category"))
            emotion_weight = get_emotion_weight(scored.get("emotion"))
            scored["virality_score"] = min(
                1.0,
                scored["virality_score"] * category_weight * emotion_weight,
            )

            topic = Topic(
                topic=scored["topic"],
                category=scored["category"],
                emotion=scored["emotion"],
                emotional_score=scored["emotional_score"],
                virality_score=scored["virality_score"],
                source=scored["source"],
                source_url=scored["source_url"],
                metadata_=scored["metadata"],
            )
            db.add(topic)
            existing.append(scored["topic"])
            created += 1

        db.commit()
        result = {"scraped": len(raw_topics), "created": created, "skipped_duplicates": skipped}
        logger.info("research_complete", **result)
        return result
    finally:
        db.close()
