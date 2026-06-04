
from short_factory.research.classifier import is_duplicate
from short_factory.research.scoring import compute_virality_score
from short_factory.scripts.validator import validate_script


def test_virality_score_formula():
    score = compute_virality_score(0.8, 0.5, 0.7, 0.4)
    expected = 0.8 * 0.4 + 0.5 * 0.2 + 0.7 * 0.3 + 0.4 * 0.1
    assert abs(score - expected) < 0.001


def test_duplicate_detection():
    existing = ["Why emotionally unavailable people feel addictive"]
    assert is_duplicate("Why emotionally unavailable people feel addictive", existing)
    assert not is_duplicate("Completely different topic about boundaries", existing)


def test_script_validator_passes_good_script():
    script = {
        "hook": "Emotionally safe men are different.",
        "body": "They don't perform strength. They create space. Their consistency feels boring until you've been hurt enough to recognize safety.",
        "ending": "Safety isn't silence. It's reliability without conditions.",
        "cta": "Save this if it hit home.",
        "estimated_duration_sec": 38,
    }
    passed, score, issues = validate_script(script)
    assert passed
    assert score >= 0.6
    assert "weak_hook" not in issues


def test_script_validator_rejects_generic():
    script = {
        "hook": "Communication is key in relationships.",
        "body": "Just be yourself and love yourself first. Everything happens for a reason when you trust the process.",
        "ending": "Time heals all wounds eventually.",
        "cta": "Follow for more.",
        "estimated_duration_sec": 50,
    }
    passed, score, issues = validate_script(script)
    assert not passed
    assert "generic_advice" in issues or "too_long" in issues
