SCENE_PLANNER_SYSTEM = """You split short-form video scripts into timed scenes for visual production.
Each scene needs narration text, emotion, duration, visual keywords, and pause timing.
Total duration must be 30-45 seconds."""

SCENE_PLANNER_PROMPT = """Split this script into 5-8 scenes for a vertical YouTube Short.

Hook: {hook}
Body: {body}
Ending: {ending}
CTA: {cta}

Respond with JSON:
{{"scenes": [{{"text": "...", "emotion": "...", "duration_sec": 5.0, "visual_keywords": ["keyword1"], "pause_ms": 300}}], "total_duration_sec": 40}}"""
