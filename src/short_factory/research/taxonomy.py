import enum


class Emotion(enum.StrEnum):
    CURIOSITY = "curiosity"
    FEAR_OF_LOSS = "fear_of_loss"
    VALIDATION = "validation"
    LONELINESS = "loneliness"
    DESIRE = "desire"
    REJECTION = "rejection"


class TopicCategory(enum.StrEnum):
    ATTACHMENT_STYLES = "attachment_styles"
    TEXTING_PSYCHOLOGY = "texting_psychology"
    EMOTIONAL_SAFETY = "emotional_safety"
    TOXIC_RELATIONSHIPS = "toxic_relationships"
    BREAKUPS = "breakups"
    MASCULINE_FEMININE = "masculine_feminine_dynamics"
    BOUNDARIES = "boundaries"
    SELF_WORTH = "self_worth"


REDDIT_SUBREDDITS = [
    "relationship_advice",
    "dating",
    "attachment_theory",
    "BreakUps",
    "AskWomen",
    "AskMen",
]
