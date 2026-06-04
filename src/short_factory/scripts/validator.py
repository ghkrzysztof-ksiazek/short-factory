import re

GENERIC_PHRASES = [
    "communication is key",
    "just be yourself",
    "love yourself first",
    "everything happens for a reason",
    "time heals all wounds",
    "trust the process",
]

WEAK_HOOK_PATTERNS = [
    r"^in this video",
    r"^today i",
    r"^let me tell you",
    r"^have you ever wondered",
]


def validate_script(script: dict) -> tuple[bool, float, list[str]]:
    issues: list[str] = []
    hook = script.get("hook", "")
    body = script.get("body", "")
    ending = script.get("ending", "")
    cta = script.get("cta", "")
    duration = float(script.get("estimated_duration_sec", 0))

    if not hook or len(hook) < 10:
        issues.append("weak_hook")
    for pattern in WEAK_HOOK_PATTERNS:
        if re.search(pattern, hook.lower()):
            issues.append("weak_hook_pattern")
            break

    full_text = f"{hook} {body} {ending} {cta}".lower()
    for phrase in GENERIC_PHRASES:
        if phrase in full_text:
            issues.append("generic_advice")

    words = full_text.split()
    if len(words) != len(set(words)) and len(words) > 0:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.6:
            issues.append("repetitive")

    if duration > 45:
        issues.append("too_long")
    if duration < 20:
        issues.append("too_short")

    word_count = len(words)
    if word_count < 50:
        issues.append("low_emotional_intensity")

    score = 1.0
    score -= 0.3 * issues.count("weak_hook")
    score -= 0.2 * issues.count("weak_hook_pattern")
    score -= 0.25 * issues.count("generic_advice")
    score -= 0.2 * issues.count("repetitive")
    score -= 0.3 * issues.count("too_long")
    score -= 0.15 * issues.count("too_short")
    score -= 0.2 * issues.count("low_emotional_intensity")
    score = max(0.0, min(1.0, score))

    passed = score >= 0.6 and "too_long" not in issues and "weak_hook" not in issues
    return passed, score, issues
