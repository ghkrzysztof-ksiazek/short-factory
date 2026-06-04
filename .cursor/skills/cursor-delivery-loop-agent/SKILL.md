---
name: cursor-delivery-loop-agent
description: >-
  Launch the cursor-delivery-loop orchestrator subagent (composer-2.5) via Task.
  Use instead of /cursor-delivery-loop when you want the dedicated agent, not the
  skill on the current chat.
user_invocable: true
disable-model-invocation: true
---

# Launch cursor-delivery-loop agent

**Do not** run the delivery loop in this parent thread. **Immediately** delegate to the **`cursor-delivery-loop`** subagent via the **`Task`** tool.

Project command file: [`.cursor/commands/cursor-delivery-loop-agent.md`](../../commands/cursor-delivery-loop-agent.md).

## When to use

- Mandated delivery (`delivery_loop_check.py` exit 2) or live-trading paths.
- Full pipeline: implement → domain review → fast gates → full pytest → **implementation-review loop** → quality review.
- When `/cursor-delivery-loop` on the default agent previously stopped after implement + pytest only.

## Usage

```
/cursor-delivery-loop-agent [.cursor/plans/<slug>.md] [task notes...]
/cursor-delivery-loop --agent [.cursor/plans/<slug>.md] [task notes...]
```

## Workflow

### Step 1: Parse arguments

- First token ending in `.md` or under `.cursor/plans/`: plan path (resolve absolute; verify exists).
- Remaining text: user task context for the subagent.
- If no plan: infer from `.cursor/delivery-state.json` `planPath`, or ask once.

### Step 2: Mandate and state (when plan known)

```bash
python3 scripts/delivery_loop_check.py --json
python3 scripts/delivery_record_gate.py init --plan <absolute-plan-path>
```

If mandate is required and no plan exists, stop and ask for a plan path.

### Step 3: Dispatch the Cursor subagent

Use the **`Task`** tool:

- **subagent_type**: `cursor-delivery-loop` (`.cursor/agents/cursor-delivery-loop.md`)
- **Do not pass `model`** — agent frontmatter sets `composer-2.5`
- **description**: `Delivery loop` (3–5 words)

**Prompt template** (substitute placeholders):

```text
Run as the cursor-delivery-loop orchestrator agent.

PLAN_PATH: {ABSOLUTE_PLAN_PATH_OR_"none"}
WORKTREE_PATH: {ABSOLUTE_REPO_ROOT}
USER_TASK: {USER_TASK_OR_"execute the approved plan end to end"}

Instructions:
- Follow `.cursor/skills/cursor-delivery-loop/SKILL.md` as the primary runbook.
- Run the full delivery loop including domain review, fast gates, full pytest, and the
  obligatory implementation-review loop (steps 6–8) until 0 CRITICAL, 0 IMPORTANT, proceed.
- Record gates via `scripts/delivery_record_gate.py` when applicable.
- Do not deploy unless USER_TASK explicitly requests deployment.
- Return the completion summary from the skill (plan path, validation, review iterations, quality review).
```

### Step 4: Present results

Summarize the subagent return: plan path, implement scope, fast/full validation, implementation-review iterations until clean, quality review, deploy/status if any.

## vs `/cursor-delivery-loop`

| Slash | Behavior |
|-------|----------|
| `/cursor-delivery-loop` | Skill on **this chat** |
| `/cursor-delivery-loop-agent` | **Subagent** orchestrator (this skill) |

## Hook

`.cursor/hooks.json` runs `scripts/delivery_loop_prompt_hook.py` on `beforeSubmitPrompt` when this slash command is used, injecting launch context (best-effort; skill instructions remain authoritative).
