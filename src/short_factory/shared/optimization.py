from short_factory.db.models import OptimizationWeight
from short_factory.db.session import SessionLocal


def get_weights(dimension: str) -> dict[str, float]:
    db = SessionLocal()
    try:
        rows = db.query(OptimizationWeight).filter(OptimizationWeight.dimension == dimension).all()
        return {row.value: row.weight for row in rows}
    finally:
        db.close()


def get_category_weight(category: str | None) -> float:
    if not category:
        return 1.0
    return get_weights("category").get(category, 1.0)


def get_emotion_weight(emotion: str | None) -> float:
    if not emotion:
        return 1.0
    return get_weights("emotion").get(emotion, 1.0)


def get_top_hook_patterns(limit: int = 3) -> list[tuple[str, float]]:
    hooks = get_weights("hook_pattern")
    return sorted(hooks.items(), key=lambda item: item[1], reverse=True)[:limit]


def build_script_context() -> str:
    category_weights = get_weights("category")
    emotion_weights = get_weights("emotion")
    hook_weights = get_weights("hook_pattern")
    if not category_weights and not emotion_weights and not hook_weights:
        return ""

    lines = ["Optimization hints from analytics (prioritize high-performing patterns):"]
    if category_weights:
        top = sorted(category_weights.items(), key=lambda x: x[1], reverse=True)[:3]
        lines.append(f"- Favor categories: {', '.join(f'{k} (weight {v:.2f})' for k, v in top)}")
    if emotion_weights:
        top = sorted(emotion_weights.items(), key=lambda x: x[1], reverse=True)[:3]
        lines.append(f"- Favor emotions: {', '.join(f'{k} (weight {v:.2f})' for k, v in top)}")
    if hook_weights:
        top = sorted(hook_weights.items(), key=lambda x: x[1], reverse=True)[:3]
        lines.append("- Winning hook patterns to emulate:")
        for hook, weight in top:
            lines.append(f"  • \"{hook}\" (weight {weight:.2f})")
    return "\n".join(lines)
