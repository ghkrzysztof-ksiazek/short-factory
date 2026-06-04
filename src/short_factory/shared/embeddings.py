import math

from short_factory.config.logging import get_logger
from short_factory.config.settings import settings

logger = get_logger(__name__)

_embedding_cache: dict[str, list[float]] = {}


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_embedding(text: str) -> list[float] | None:
    if text in _embedding_cache:
        return _embedding_cache[text]

    if not settings.openai_api_key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=text,
        )
        vector = response.data[0].embedding
        _embedding_cache[text] = vector
        return vector
    except Exception as exc:
        logger.warning("embedding_failed", error=str(exc))
        return None


def is_semantic_duplicate(topic: str, existing_topics: list[str], threshold: float = 0.85) -> bool:
    topic_vec = get_embedding(topic)
    if topic_vec is None:
        return _word_overlap_duplicate(topic, existing_topics, threshold)

    for existing in existing_topics:
        existing_vec = get_embedding(existing)
        if existing_vec and cosine_similarity(topic_vec, existing_vec) >= threshold:
            return True
    return False


def _word_overlap_duplicate(topic: str, existing_topics: list[str], threshold: float) -> bool:
    topic_words = set(topic.lower().split())
    for existing in existing_topics:
        existing_words = set(existing.lower().split())
        if not topic_words or not existing_words:
            continue
        overlap = len(topic_words & existing_words) / len(topic_words | existing_words)
        if overlap >= threshold:
            return True
    return False
