from short_factory.config.logging import get_logger
from short_factory.research.scoring import RawTopic

logger = get_logger(__name__)


def scrape_tiktok(limit: int = 15) -> list[RawTopic]:
    """TikTok scraper stub — returns mock data until API access is configured."""
    logger.info("tiktok_scraper_stub", limit=limit)
    return [
        RawTopic(
            title="Why breadcrumbing keeps you hooked",
            source="tiktok",
            source_url="https://tiktok.com/@mock/video/1",
            metadata={"views": 85000, "likes": 4200},
        ),
        RawTopic(
            title="Anxious attachment looks like this in texts",
            source="tiktok",
            source_url="https://tiktok.com/@mock/video/2",
            metadata={"views": 120000, "likes": 6800},
        ),
        RawTopic(
            title="The psychology of slow replies",
            source="tiktok",
            source_url="https://tiktok.com/@mock/video/3",
            metadata={"views": 95000, "likes": 5100},
        ),
        RawTopic(
            title="Why closure rarely comes from them",
            source="tiktok",
            source_url="https://tiktok.com/@mock/video/4",
            metadata={"views": 67000, "likes": 3900},
        ),
    ][:limit]
