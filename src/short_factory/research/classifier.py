
from short_factory.config.logging import get_logger
from short_factory.research.scoring import RawTopic, compute_virality_score
from short_factory.research.taxonomy import Emotion, TopicCategory
from short_factory.shared.llm import get_llm_client, parse_json_response

logger = get_logger(__name__)

CLASSIFY_SYSTEM = """You classify relationship psychology topics for short-form video content.
Respond with JSON: {"emotion": "<one of curiosity|fear_of_loss|validation|loneliness|desire|rejection>",
"category": "<one of attachment_styles|texting_psychology|emotional_safety|toxic_relationships|breakups|masculine_feminine_dynamics|boundaries|self_worth>",
"emotional_intensity": 0.0-1.0, "controversy": 0.0-1.0, "relatability": 0.0-1.0, "novelty": 0.0-1.0}"""


def classify_and_score(raw: RawTopic) -> dict:
    llm = get_llm_client()
    try:
        result = llm.complete(
            f"Classify this topic for virality:\n\nTitle: {raw.title}\nSource: {raw.source}",
            system=CLASSIFY_SYSTEM,
            json_mode=True,
        )
        data = parse_json_response(result)
    except Exception as exc:
        logger.warning("llm_classify_failed", title=raw.title, error=str(exc))
        data = _heuristic_classify(raw)

    virality = compute_virality_score(
        float(data.get("emotional_intensity", 0.5)),
        float(data.get("controversy", 0.3)),
        float(data.get("relatability", 0.5)),
        float(data.get("novelty", 0.4)),
    )
    engagement_boost = _engagement_boost(raw)
    virality = min(1.0, virality + engagement_boost)

    return {
        "topic": raw.title,
        "category": data.get("category", TopicCategory.ATTACHMENT_STYLES.value),
        "emotion": data.get("emotion", Emotion.CURIOSITY.value),
        "emotional_score": float(data.get("emotional_intensity", 0.5)),
        "virality_score": virality,
        "source": raw.source,
        "source_url": raw.source_url,
        "metadata": {**(raw.metadata or {}), "classification": data},
    }


def _engagement_boost(raw: RawTopic) -> float:
    meta = raw.metadata or {}
    if raw.source == "reddit":
        score = meta.get("score", 0)
        comments = meta.get("num_comments", 0)
        return min(0.2, (score / 5000) * 0.1 + (comments / 500) * 0.1)
    if raw.source == "youtube":
        views = meta.get("views", 0)
        return min(0.2, (views / 100000) * 0.15)
    return 0.0


def _heuristic_classify(raw: RawTopic) -> dict:
    title_lower = raw.title.lower()
    emotion = Emotion.CURIOSITY.value
    if any(w in title_lower for w in ["breakup", "leave", "loss", "gone"]):
        emotion = Emotion.FEAR_OF_LOSS.value
    elif any(w in title_lower for w in ["reject", "ignore", "ghost"]):
        emotion = Emotion.REJECTION.value
    elif any(w in title_lower for w in ["lonely", "alone"]):
        emotion = Emotion.LONELINESS.value
    elif any(w in title_lower for w in ["desire", "want", "attract"]):
        emotion = Emotion.DESIRE.value
    elif any(w in title_lower for w in ["valid", "enough", "worth"]):
        emotion = Emotion.VALIDATION.value

    return {
        "emotion": emotion,
        "category": TopicCategory.ATTACHMENT_STYLES.value,
        "emotional_intensity": 0.6,
        "controversy": 0.3,
        "relatability": 0.7,
        "novelty": 0.4,
    }


def is_duplicate(topic: str, existing_topics: list[str], threshold: float = 0.85) -> bool:
    from short_factory.shared.embeddings import is_semantic_duplicate

    return is_semantic_duplicate(topic, existing_topics, threshold)
