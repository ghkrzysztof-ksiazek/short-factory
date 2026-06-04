---
name: cursor-implementation-composer25
description: >-
  Implements approved plans inside Cursor using Composer 2.5. Use for delivery-loop
  implementation after planning and plan review. Vendored from ~/.cursor/skills/.
---

# Cursor Implementation With Composer 2.5

Implement an approved working plan in **ibkr-worktree-2**.

## Invocation

Used by `cursor-delivery-loop` implement phase and `cursor-delivery-loop` agent (`model: composer-2.5`).

## Model intent

- Use Composer 2.5 when available.
- If unavailable, stop and report — do not silently substitute.

## Constraints

- Working plan under `.cursor/plans/` is source of truth.
- No unrelated scope; no commit/push/deploy unless explicitly requested.
- Live trading paths are high risk — use existing services and `BrokerAdapter`.
- Alembic migrations must stay SQLite-compatible.

## Parallelization

- Parallelize read-only exploration.
- Avoid parallel writes to the same module, migration, or shared test fixtures.

## Workflow

1. Read the plan and relevant code (`.cursor/APP_MEMORY.md` for architecture).
2. Implement in small steps; add/update tests for risky behavior.
3. Hand off to **domain-review** (step 3b) and **fast verify skills** (step 4) before claiming validate complete.
4. Do not skip the obligatory **full** pytest run — that is the orchestrator's step 5.

## Output

Implemented steps, files changed, deviations, remaining risks.

## Provenance

Vendored from `~/.cursor/skills/cursor-implementation-composer25/` and adapted for this repository (2026-05-28).
