from dataclasses import dataclass


@dataclass
class RawTopic:
    title: str
    source: str
    source_url: str
    metadata: dict | None = None


def compute_virality_score(
    emotional_intensity: float,
    controversy: float,
    relatability: float,
    novelty: float,
) -> float:
    return (
        emotional_intensity * 0.4
        + controversy * 0.2
        + relatability * 0.3
        + novelty * 0.1
    )
