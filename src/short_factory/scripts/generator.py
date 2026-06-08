from short_factory.config.logging import get_logger
from short_factory.config.settings import settings
from short_factory.db.models import Script, ScriptStatus, Topic
from short_factory.db.session import SessionLocal
from short_factory.scripts.prompts import HOOK_VARIANT_PROMPT, SCRIPT_PROMPT, SCRIPT_SYSTEM
from short_factory.scripts.validator import validate_script
from short_factory.shared.llm import get_llm_client, parse_json_response
from short_factory.shared.optimization import build_script_context

logger = get_logger(__name__)


def _generate_script_content(topic: Topic, hook_override: str | None = None) -> dict:
    llm = get_llm_client()
    prompt = SCRIPT_PROMPT.format(
        duration=40,
        topic=topic.topic,
        category=topic.category or "attachment_styles",
        emotion=topic.emotion or "curiosity",
    )
    optimization_context = build_script_context()
    if optimization_context:
        prompt += f"\n\n{optimization_context}"
    if hook_override:
        prompt += f"\n\nUse this exact hook: {hook_override}"

    result = llm.complete(prompt, system=SCRIPT_SYSTEM, json_mode=True)
    return parse_json_response(result)


def _generate_hook_variants(topic_text: str) -> list[str]:
    llm = get_llm_client()
    try:
        result = llm.complete(
            HOOK_VARIANT_PROMPT.format(topic=topic_text),
            system="Generate compelling short-form video hooks.",
            json_mode=True,
        )
        data = parse_json_response(result)
        return data.get("hooks", [])
    except Exception as exc:
        logger.warning("hook_variants_failed", error=str(exc))
        return []


def generate_scripts_for_topic(topic_id: int, hook_variants: bool = True) -> list[int]:
    db = SessionLocal()
    script_ids: list[int] = []
    try:
        topic = db.get(Topic, topic_id)
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")

        hooks = [None]
        if hook_variants:
            hooks = [None] + _generate_hook_variants(topic.topic)

        for i, hook in enumerate(hooks[:3]):
            try:
                content = _generate_script_content(topic, hook_override=hook)
            except Exception as exc:
                logger.error("script_generation_failed", topic_id=topic_id, error=str(exc))
                content = _fallback_script(topic)

            passed, quality_score, issues = validate_script(content)
            script = Script(
                topic_id=topic_id,
                hook=content["hook"],
                body=content["body"],
                ending=content["ending"],
                cta=content["cta"],
                estimated_duration_sec=content.get("estimated_duration_sec", 40),
                quality_score=quality_score,
                status=ScriptStatus.APPROVED if passed else ScriptStatus.REJECTED,
                hook_variant=i + 1,
                metadata_={"validation_issues": issues, "review_source": "auto"},
            )
            db.add(script)
            db.flush()
            script_ids.append(script.id)

        db.commit()
        return script_ids
    finally:
        db.close()


def generate_scripts_for_top_topics(limit: int = 5) -> dict:
    db = SessionLocal()
    try:
        topics = (
            db.query(Topic)
            .filter(Topic.virality_score >= settings.virality_threshold)
            .order_by(Topic.virality_score.desc())
            .limit(limit)
            .all()
        )
        all_ids: list[int] = []
        for topic in topics:
            ids = generate_scripts_for_topic(topic.id)
            all_ids.extend(ids)
        return {"topics_processed": len(topics), "scripts_created": len(all_ids), "script_ids": all_ids}
    finally:
        db.close()


def _fallback_script(topic: Topic) -> dict:
    return {
        "hook": topic.topic + ".",
        "body": "Most people miss the psychology behind this. It's not about what they say — it's about what consistency reveals over time.",
        "ending": "When you understand the pattern, you stop chasing confusion and start choosing clarity.",
        "cta": "Save this if it hit home.",
        "estimated_duration_sec": 35,
    }
