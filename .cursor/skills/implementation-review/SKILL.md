---
name: implementation-review
description: >-
  Use a Cursor subagent (implementation-review, GPT 5.4 xhigh) to compare
  implemented code against a plan. Provide a plan file and optional paths or
  globs. Returns structured gap analysis with CRITICAL / IMPORTANT / MINOR tags.
  Invoked as /implementation-review.
user_invocable: true
disable-model-invocation: true
---

# Implementation Review (Cursor)

Cursor-native plan-vs-code review. Spawns the **`implementation-review`** agent via the `Task` tool in a fresh context — no external `codex`, Claude, or Copilot CLIs.

**Canonical** plan-vs-code review for Cursor. Deprecated counterparts: `implementation-review-by-codex`, `implementation-review-by-claude` — do not use.

## When to use

- **Inside `cursor-delivery-loop`:** after every validate pass (step 5), **before** quality review or declaring the loop complete. The delivery loop **re-runs** this skill until there are **0 CRITICAL**, **0 IMPORTANT**, and **final recommendation: proceed**.
- After an implementation pass, before merging.
- When the user runs `/implementation-review <plan-file>`.
- After obligatory validation; include test evidence when code changed.

**Do not** treat implementation-review as optional in the delivery loop.

## Usage

```
/implementation-review <plan-file> [file-or-glob...]
```

**Examples:**

```
/implementation-review .cursor/plans/my-plan.md
/implementation-review .cursor/plans/my-plan.md src/app/temperature_workflow.py
/implementation-review .cursor/plans/my-plan.md "src/app/**/*.py"
```

## Workflow

### Step 1: Parse arguments

- First argument: plan file. Resolve to an absolute path; verify it exists.
- Remaining arguments: files or globs for the implementation surface.
- If none given, enumerate changes:
  - `git diff --name-only origin/main...HEAD` (or `main...HEAD` if no `origin/main`)
  - `git ls-files --others --exclude-standard` for untracked files
- Resolve globs with the `Glob` tool before delegating.

### Step 2: Plan step checklist

If the plan follows `.cursor/plans/TEMPLATE.md`, build a checklist from each `### Step N`:

- **Files:** listed vs actually changed
- **Done when:** criteria vs implementation + tests

Include this checklist in the subagent prompt under `PLAN_STEP_CHECKLIST`.

### Step 3: Validation evidence (required when code changed)

Before dispatching, run:

```bash
python3 scripts/delivery_record_gate.py assert-full-pytest
```

If `.cursor/delivery-state.json` exists, require `gates.fullPytest.passed === true` and `gates.fullPytest.at` after `phases.implement.completedAt`. If missing or invalid → **do not dispatch**; print:

```text
BLOCKED: implementation-review requires full pytest (delivery loop step 5).
Run: PYTHONPATH=src python -m pytest tests/ -q
Then: python3 scripts/delivery_record_gate.py record-full-pytest --exit-code 0
```

Pass evidence from the delivery loop:

- **4a** `tests-for-path` / `scripts/test_impact.py` (command, exit code, matched keys)
- **4b** `verify-*` skills run
- **5** full suite `PYTHONPATH=src python -m pytest tests/ -q`

Compare commands to the plan's **`## Test plan`** section. Missing evidence for non-docs changes → reviewer should flag **blocked** or **fix required**.

### Step 4: Generate a unique review path

```bash
RUN_ID="${SESSION_ID:-$(date +%s)-$$}"
REVIEW_PATH=".cursor/plans/reviews/implementation-review-$RUN_ID.md"
mkdir -p .cursor/plans/reviews
```

Resolve `REVIEW_PATH` to an absolute path.

### Step 5: Dispatch the Cursor subagent

Use the **`Task`** tool:

- **Delegate** to the **`implementation-review`** subagent (`.cursor/agents/implementation-review.md`).
- **Do not pass `model` on Task** — the agent sets `model` in frontmatter.
- **description**: `Plan-vs-code review` (3–5 words).

**Prompt template** (substitute placeholders):

```text
Run as the implementation-review agent.

PLAN_PATH: {ABSOLUTE_PLAN_PATH}
REVIEW_PATH: {ABSOLUTE_REVIEW_PATH}
WORKTREE_PATH: {ABSOLUTE_REPO_ROOT}

FILES_IN_SCOPE:
{FILE_LIST_BULLETS}

PLAN_STEP_CHECKLIST:
{STEP_CHECKLIST_OR_"plan has no ### Step sections"}

VALIDATION_EVIDENCE:
{VALIDATION_SUMMARY_OR_"none — flag if code changed"}

Instructions:
- Compare PLAN_STEP_CHECKLIST to git diff and tests.
- Read the plan and every in-scope file; use git diff for anything missing from the list.
- Read CLAUDE.md / AGENTS.md for conventions.
- Save the full structured review to REVIEW_PATH (Coverage Summary, Gap Analysis, Alignment Score, Recommendations, final recommendation).
- Return a short summary: review path, CRITICAL/IMPORTANT/MINOR counts, alignment score, top fix.
- Read-only: do not edit implementation files.
```

### Step 6: Present results

1. Read `$REVIEW_PATH`.
2. Surface **CRITICAL** gaps prominently — they block advancing the delivery loop.
3. Surface **IMPORTANT** as required next-pass work.
4. Note **MINOR** without blocking.
5. If inside `cursor-delivery-loop`, hand findings back for steps **7–8** and schedule another **step 6** until clean (see `cursor-delivery-loop` review loop). The orchestrator must not exit while CRITICAL or IMPORTANT remain.
6. After saving the review file, the orchestrator must run: `python3 scripts/delivery_record_gate.py record-implementation-review --review-path <REVIEW_PATH> --parse` then `assert-implementation-review` before quality review or declaring the loop complete.

### Delivery-loop exit criteria

The parent loop may advance to quality review only when this review reports:

| Check | Required |
|-------|----------|
| CRITICAL count | 0 |
| IMPORTANT count | 0 |
| Final recommendation | **proceed** |

MINOR findings may remain. `fix required` or `blocked` → parent applies step 7 and re-runs this skill after step 8.

## Common mistakes

- **Inlining file contents in the prompt** — pass paths; the subagent reads files.
- **Passing `model` on Task** — overrides agent frontmatter; breaks routing.
- **Skipping globs** — expand with `Glob` before delegating.
- **Reused review paths** — always use a unique `RUN_ID`.
- **Treating EXTRA as always bad** — often needs a small plan amendment, not deleting code.

## Provenance

Combines patterns from `implementation-review-by-codex`, `implementation-review-by-claude`, and `cursor-implementation-review-gpt54-xhigh` (`.cursor/sources/home-cursor-skills/`).
