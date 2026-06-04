from short_factory.config.logging import get_logger
from short_factory.research.scoring import RawTopic

logger = get_logger(__name__)


def scrape_google_trends(limit: int = 10) -> list[RawTopic]:
    """Google Trends stub — returns mock trending queries until pytrends/API is wired."""
    logger.info("google_trends_scraper_stub", limit=limit)
    return [
        RawTopic(
            title="Signs of emotional unavailability in dating",
            source="google_trends",
            source_url="https://trends.google.com/trends/explore?q=emotional+unavailability",
            metadata={"interest_score": 88},
        ),
        RawTopic(
            title="How to set boundaries without guilt",
            source="google_trends",
            source_url="https://trends.google.com/trends/explore?q=boundaries+guilt",
            metadata={"interest_score": 76},
        ),
        RawTopic(
            title="Attachment styles explained simply",
            source="google_trends",
            source_url="https://trends.google.com/trends/explore?q=attachment+styles",
            metadata={"interest_score": 92},
        ),
    ][:limit]
