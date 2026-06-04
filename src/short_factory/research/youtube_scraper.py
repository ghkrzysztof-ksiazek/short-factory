from short_factory.config.logging import get_logger
from short_factory.config.settings import settings
from short_factory.research.scoring import RawTopic
from short_factory.shared.rate_limit import rate_limit

logger = get_logger(__name__)


@rate_limit(calls=10, period_sec=60)
def scrape_youtube(query: str = "relationship psychology shorts", max_results: int = 25) -> list[RawTopic]:
    if not settings.youtube_api_key:
        logger.warning("youtube_api_key_missing", using="mock_data")
        return _mock_youtube_topics()

    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)
    search_response = (
        youtube.search()
        .list(q=query, part="snippet", type="video", videoDuration="short", maxResults=max_results)
        .execute()
    )
    video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
    if not video_ids:
        return []

    stats_response = (
        youtube.videos()
        .list(part="statistics,snippet", id=",".join(video_ids))
        .execute()
    )

    topics: list[RawTopic] = []
    for item in stats_response.get("items", []):
        stats = item.get("statistics", {})
        topics.append(
            RawTopic(
                title=item["snippet"]["title"],
                source="youtube",
                source_url=f"https://youtube.com/watch?v={item['id']}",
                metadata={
                    "views": int(stats.get("viewCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                },
            )
        )
    return topics


def _mock_youtube_topics() -> list[RawTopic]:
    return [
        RawTopic(
            title="The psychology of mixed signals in dating",
            source="youtube",
            source_url="https://youtube.com/watch?v=mock1",
            metadata={"views": 45000, "comments": 320, "likes": 2100},
        ),
        RawTopic(
            title="Why secure attachment is the real flex",
            source="youtube",
            source_url="https://youtube.com/watch?v=mock2",
            metadata={"views": 82000, "comments": 540, "likes": 4800},
        ),
        RawTopic(
            title="3 signs someone is emotionally unavailable",
            source="youtube",
            source_url="https://youtube.com/watch?v=mock3",
            metadata={"views": 120000, "comments": 890, "likes": 7200},
        ),
    ]
