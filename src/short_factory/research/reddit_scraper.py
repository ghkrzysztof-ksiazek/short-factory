from short_factory.config.logging import get_logger
from short_factory.config.settings import settings
from short_factory.research.scoring import RawTopic
from short_factory.research.taxonomy import REDDIT_SUBREDDITS
from short_factory.shared.rate_limit import rate_limit

logger = get_logger(__name__)


@rate_limit(calls=30, period_sec=60)
def scrape_reddit(limit_per_sub: int = 25) -> list[RawTopic]:
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        logger.warning("reddit_credentials_missing", using="mock_data")
        return _mock_reddit_topics()

    import praw

    reddit = praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
    )
    topics: list[RawTopic] = []
    for sub_name in REDDIT_SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.hot(limit=limit_per_sub):
                topics.append(
                    RawTopic(
                        title=post.title,
                        source="reddit",
                        source_url=f"https://reddit.com{post.permalink}",
                        metadata={
                            "subreddit": sub_name,
                            "score": post.score,
                            "num_comments": post.num_comments,
                        },
                    )
                )
        except Exception as exc:
            logger.error("reddit_scrape_failed", subreddit=sub_name, error=str(exc))
    return topics


def _mock_reddit_topics() -> list[RawTopic]:
    return [
        RawTopic(
            title="Why emotionally unavailable people feel addictive",
            source="reddit",
            source_url="https://reddit.com/r/dating/mock1",
            metadata={"subreddit": "dating", "score": 1200, "num_comments": 340},
        ),
        RawTopic(
            title="The people who love hardest often fear intimacy the most",
            source="reddit",
            source_url="https://reddit.com/r/relationship_advice/mock2",
            metadata={"subreddit": "relationship_advice", "score": 890, "num_comments": 210},
        ),
        RawTopic(
            title="Signs you're dating someone with avoidant attachment",
            source="reddit",
            source_url="https://reddit.com/r/attachment_theory/mock3",
            metadata={"subreddit": "attachment_theory", "score": 650, "num_comments": 180},
        ),
        RawTopic(
            title="Why silence after a breakup hurts more than anger",
            source="reddit",
            source_url="https://reddit.com/r/BreakUps/mock4",
            metadata={"subreddit": "BreakUps", "score": 2100, "num_comments": 520},
        ),
        RawTopic(
            title="Emotionally safe men don't perform confidence",
            source="reddit",
            source_url="https://reddit.com/r/AskWomen/mock5",
            metadata={"subreddit": "AskWomen", "score": 430, "num_comments": 95},
        ),
        RawTopic(
            title="The psychology of breadcrumbing in modern dating",
            source="reddit",
            source_url="https://reddit.com/r/dating/mock6",
            metadata={"subreddit": "dating", "score": 780, "num_comments": 160},
        ),
        RawTopic(
            title="Why setting boundaries makes anxious partners pull away",
            source="reddit",
            source_url="https://reddit.com/r/relationship_advice/mock7",
            metadata={"subreddit": "relationship_advice", "score": 540, "num_comments": 130},
        ),
        RawTopic(
            title="The difference between loneliness and being alone",
            source="reddit",
            source_url="https://reddit.com/r/AskMen/mock8",
            metadata={"subreddit": "AskMen", "score": 320, "num_comments": 75},
        ),
        RawTopic(
            title="Why validation-seeking destroys attraction over time",
            source="reddit",
            source_url="https://reddit.com/r/dating/mock9",
            metadata={"subreddit": "dating", "score": 910, "num_comments": 200},
        ),
        RawTopic(
            title="How to rebuild self-worth after a toxic relationship",
            source="reddit",
            source_url="https://reddit.com/r/relationship_advice/mock10",
            metadata={"subreddit": "relationship_advice", "score": 1500, "num_comments": 380},
        ),
        RawTopic(
            title="Why avoidants come back when you finally move on",
            source="reddit",
            source_url="https://reddit.com/r/BreakUps/mock11",
            metadata={"subreddit": "BreakUps", "score": 980, "num_comments": 240},
        ),
        RawTopic(
            title="The hidden cost of people-pleasing in relationships",
            source="reddit",
            source_url="https://reddit.com/r/relationship_advice/mock12",
            metadata={"subreddit": "relationship_advice", "score": 720, "num_comments": 190},
        ),
        RawTopic(
            title="What secure attachment actually feels like day to day",
            source="reddit",
            source_url="https://reddit.com/r/attachment_theory/mock13",
            metadata={"subreddit": "attachment_theory", "score": 610, "num_comments": 140},
        ),
        RawTopic(
            title="Why mixed signals are often emotional unavailability",
            source="reddit",
            source_url="https://reddit.com/r/dating/mock14",
            metadata={"subreddit": "dating", "score": 1100, "num_comments": 260},
        ),
        RawTopic(
            title="How masculine vulnerability builds trust over time",
            source="reddit",
            source_url="https://reddit.com/r/AskMen/mock15",
            metadata={"subreddit": "AskMen", "score": 480, "num_comments": 110},
        ),
        RawTopic(
            title="The psychology of waiting for someone to choose you",
            source="reddit",
            source_url="https://reddit.com/r/AskWomen/mock16",
            metadata={"subreddit": "AskWomen", "score": 860, "num_comments": 220},
        ),
        RawTopic(
            title="Why conflict avoidance creates resentment later",
            source="reddit",
            source_url="https://reddit.com/r/relationship_advice/mock17",
            metadata={"subreddit": "relationship_advice", "score": 690, "num_comments": 175},
        ),
        RawTopic(
            title="Signs you're healing from an anxious attachment pattern",
            source="reddit",
            source_url="https://reddit.com/r/attachment_theory/mock18",
            metadata={"subreddit": "attachment_theory", "score": 540, "num_comments": 130},
        ),
        RawTopic(
            title="Why consistency matters more than chemistry",
            source="reddit",
            source_url="https://reddit.com/r/dating/mock19",
            metadata={"subreddit": "dating", "score": 1300, "num_comments": 310},
        ),
        RawTopic(
            title="How to stop chasing emotional closure from the wrong person",
            source="reddit",
            source_url="https://reddit.com/r/BreakUps/mock20",
            metadata={"subreddit": "BreakUps", "score": 1750, "num_comments": 410},
        ),
    ]
