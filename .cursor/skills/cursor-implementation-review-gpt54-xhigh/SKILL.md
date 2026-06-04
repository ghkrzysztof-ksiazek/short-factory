---
name: cursor-implementation-review-gpt54-xhigh
description: >-
  Reviews implemented code against the working plan inside Cursor using GPT 5.4
  xhigh/xtra-high reasoning. Loaded by the implementation-review agent and
  delivery-loop impl-review phase.
---

# Cursor Implementation Review With GPT 5.4 Xhigh

Compare implementation against the working plan. Read-only — do not edit files during this pass.

## Model intent

- Use GPT 5.4 xhigh / xtra-high reasoning when available in Cursor.
- If unavailable, stop and report which model frontmatter failed. Do not silently substitute.

## Constraints

- Stay inside Cursor. No external agent binaries (`codex`, `claude`, `gemini`, Copilot CLIs).
- Prioritize correctness, security, regressions, missing tests, and plan misalignment.
- Require validation evidence: missing or failed **full test suite** output is an IMPORTANT gap unless the change set is provably docs-only.

## Workflow

1. Read the working plan in full.
2. Read `CLAUDE.md` / `AGENTS.md` for project conventions.
3. Inspect changed files (`git diff`, `git status`) and relevant tests.
4. Compare each plan requirement to the implementation; flag EXTRA scope.
5. Cross-check validation evidence from the validate phase.

## Severity rubric

- **CRITICAL**: blocks correctness, breaks a plan contract, security, or data-integrity risk.
- **IMPORTANT**: meaningful divergence, missing test on risky behavior, failed/missing full-suite run.
- **MINOR**: cosmetic or safe to defer.

## Required output structure

When saving a review file, use these sections:

### Coverage Summary

For each phase or task in the plan: **DONE** | **PARTIAL** | **MISSING** | **EXTRA** (keyed by plan section).

### Gap Analysis

For each gap:

- What the plan specified
- What was implemented (or not)
- **Severity**: CRITICAL / IMPORTANT / MINOR
- Suggested fix (file path + concrete change)

### Alignment Score

X/10 with brief justification.

### Recommendations

Top 3–5 actions to close gaps, priority order.

### Final recommendation

**proceed** | **fix required** | **blocked**

- Use **`proceed`** only when there are **no CRITICAL or IMPORTANT** gaps (MINOR may remain).
- Use **`fix required`** when any CRITICAL or IMPORTANT gap exists — the delivery loop must iterate (fix → re-validate → re-review).
- Use **`blocked`** for missing evidence (e.g. full pytest not recorded) or unreviewable scope.

## Short summary (when returning to parent)

Under 250 words: review path (if saved), CRITICAL/IMPORTANT/MINOR counts, alignment score, final recommendation, single most important fix if not **proceed**.

When invoked from **`cursor-delivery-loop`**, state explicitly whether the parent may exit the review loop (0 CRITICAL, 0 IMPORTANT, **proceed**).
