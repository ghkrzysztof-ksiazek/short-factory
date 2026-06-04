---
name: cursor-planning-gpt54-xhigh
description: >-
  Creates or strengthens implementation plans using GPT 5.4 xhigh. New plans must
  follow .cursor/plans/TEMPLATE.md. Vendored for this repo.
---

# Cursor Planning With GPT 5.4 Xhigh

Create or strengthen working plans in **ibkr-worktree-2**.

## Plan format (required)

Copy structure from **`.cursor/plans/TEMPLATE.md`**:

- `## Goal`, `## Non-goals`, `## Design decisions`
- `## Steps` — each `### Step N` must include **`Files:`** and **`Done when:`**
- `## Test plan` — exact shell commands (fast + full gate)
- `## Rollback`, `## Deploy notes`

Save new plans as `.cursor/plans/<feature-slug>.md`.

## Invocation

Planning subagents use `model: gpt-5.4[reasoning=xhigh]`. Orchestrator must not pass `model` on Task when agent frontmatter sets it.

## Workflow

1. Read existing plan or draft from TEMPLATE.
2. Read `.cursor/APP_MEMORY.md` and relevant `.cursor/rules/*.mdc`.
3. Number steps small enough for **`plan-step-implement`** (one Composer subagent per step).
4. In **`## Test plan`**, include:

```markdown
### Fast gate
PYTHONPATH=src python3 scripts/test_impact.py --run
# Plus domain verify skills when applicable — see domain-review-triggers.json

### Full gate
PYTHONPATH=src python -m pytest tests/ -q
```

5. Note expected domain reviewers from `.cursor/domain-review-triggers.json`.

## Output

Plan path, step list with files, test commands, blockers.

## Provenance

Vendored and extended for Tier 2 plan lifecycle (2026-05-28).
