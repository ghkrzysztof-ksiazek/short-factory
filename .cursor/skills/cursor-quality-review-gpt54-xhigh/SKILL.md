---
name: cursor-quality-review-gpt54-xhigh
description: >-
  Read-only code quality and defect review using GPT 5.4 xhigh. Use before commit
  in the delivery loop for bugs, regressions, security—not plan alignment.
  Vendored from ~/.cursor/skills/ for this repo.
---

# Cursor Quality and Defect Review With GPT 5.4 Xhigh

Final **quality pass** on the change set before commit. Not plan-vs-code alignment (use `implementation-review` for that).

## Invocation

Delivery-loop step 9 (`model: gpt-5.4[reasoning=xhigh]`). Do not pass `model` on Task when agent/skill frontmatter sets it.

## Model intent

- GPT 5.4 xhigh / xtra-high when available; stop if unavailable.

## Constraints

- Read-only; no file edits in this pass.
- Inspect `git diff` and surrounding context.
- Read `.cursor/APP_MEMORY.md` for trading/workflow invariants on touched paths.

## Review focus

1. Correctness and bugs (including Decimal/quantity and async worker races)
2. Regressions and broken contracts
3. Security (auth, secrets, injection)
4. Data integrity (migrations, transactions, idempotency)
5. Tests — risky changes without coverage; missing fast-gate or full-suite evidence
6. Live trading — bypassing adapters or guardrails

Do not re-litigate plan bullets unless they imply a concrete defect.

## Workflow

1. Identify changed files; read diffs and callers.
2. Cross-check validation evidence: fast verify skills + **full** `PYTHONPATH=src python -m pytest tests/ -q`.
3. Severity: **CRITICAL** / **IMPORTANT** / **MINOR**.

## Output

Findings (severity, file, issue, evidence, fix), hotspots checked, validation gaps, recommendation: **proceed to commit** | **fix required** | **blocked**.

## Provenance

Vendored from `~/.cursor/skills/cursor-quality-review-gpt54-xhigh/` and adapted for this repository (2026-05-28).
