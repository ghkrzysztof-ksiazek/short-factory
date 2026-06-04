---
name: cursor-delivery-loop
description: >-
  Delivers an approved plan end to end inside Cursor: strengthen the plan,
  implement (optionally per plan step), domain review, tests-for-path + verify
  fast gate, obligatory full test suite, plan review, defect pass, optional deploy.
---

# Cursor Delivery Loop

Run this workflow for implementation tasks that reference (or need) a plan.

**Launch the orchestrator subagent (recommended for full runs):** `/cursor-delivery-loop-agent` — spawns the `cursor-delivery-loop` agent via `Task` (see `.cursor/skills/cursor-delivery-loop-agent/SKILL.md`). This skill (`/cursor-delivery-loop`) runs the same runbook **in the current chat**, which can stop early if the prompt is narrow.

New plans must follow `.cursor/plans/TEMPLATE.md`.

## Skills and agents in this repo

| Phase | Prefer |
|-------|--------|
| Plan draft / strengthen | `cursor-planning-gpt54-xhigh` or `consult-codex` |
| Plan review | `codex-plan-review` |
| Implement (multi-step) | `plan-step-implement` per `### Step N` with **Files:** |
| Implement (single pass) | `cursor-implementation-composer25` or main agent |
| Domain review | `domain-review` → parallel domain agents (step 3b) |
| Fast gate 4a | `tests-for-path` → `scripts/test_impact.py` |
| Fast gate 4b | `verify-*` per `.cursor/domain-review-triggers.json` |
| Full gate | `PYTHONPATH=src python -m pytest tests/ -q` (step 5) |
| Plan vs code | `implementation-review` |
| Defect pass | `cursor-quality-review-gpt54-xhigh` |
| Deploy | `hetzner-deploy` (explicit user request only) |
| Post-deploy status | `deploy-hetzner-status` (read-only, after deploy) |

All phase skills live under `.cursor/skills/`.

## Mandate and state

At workflow start:

```bash
python3 scripts/delivery_loop_check.py --json
python3 scripts/delivery_record_gate.py init --plan .cursor/plans/<slug>.md
```

Exit code `2` from the check means delivery loop is **required** (see `.cursor/rules/agent-delivery-mandate.mdc`).

After gates, record evidence:

```bash
python3 scripts/delivery_record_gate.py record-fast --exit-code 0 --matched-keys '["src/app/foo.py"]'
python3 scripts/delivery_record_gate.py record-domain-verify --domain temperature-workflow --exit-code 0
python3 scripts/delivery_record_gate.py record-full-pytest --exit-code 0
python3 scripts/delivery_record_gate.py assert-full-pytest   # before step 6
python3 scripts/delivery_record_gate.py record-implementation-review --review-path .cursor/plans/reviews/<file>.md --parse
python3 scripts/delivery_record_gate.py assert-implementation-review   # before quality review / loop exit
python3 scripts/delivery_record_gate.py assert-review-loop   # steps 5 + 6 together
```

State file: `.cursor/delivery-state.json` (gitignored). Example: `.cursor/delivery-state.example.json`.

## Workflow

1. **Identify or draft the plan.** Use `cursor-planning-gpt54-xhigh` or `consult-codex`. Copy from `.cursor/plans/TEMPLATE.md` if new. Save under `.cursor/plans/`.
2. **Pre-implementation plan review.** Run `codex-plan-review`. Ensure **`## Test plan`** has copy-paste pytest commands.
3. **Implement.**
   - If the plan has **two or more** `### Step N` sections with **`Files:`** lines → for each step in order: run **`plan-step-implement`**, then **step 4a–4b** for that step's files. Parent integrates only when steps share symbols.
   - Otherwise → single implementation pass (`cursor-implementation-composer25` or main agent). No unrelated scope.
3b. **Domain review (when paths match).** `domain-review` skill — parallel domain agents; save under `.cursor/plans/reviews/`. Block on **blocked** or **CRITICAL**.
4. **Fast validation gate** (both when applicable):
   - **4a `tests-for-path`:** `python3 scripts/test_impact.py --run` (or `--print-cmd` then run). Uses `.cursor/test-impact-manifest.yaml`. On no match, note and continue to 4b.
   - **4b `verify-*`:** For each domain matched in `domain-review-triggers.json`, run the corresponding verify skill. Parity extras per `verify-temperature-workflow` when needed. **Do not proceed** on non-zero exit.
5. **Full validation (obligatory).**

   ```bash
   PYTHONPATH=src python -m pytest tests/ -q
   ```

   Prefer `Task` for long runs. **Do not enter the review loop** (step 6) if tests fail.
   Record step 5: `python3 scripts/delivery_record_gate.py record-full-pytest --exit-code 0`

### Review loop (obligatory — repeat until clean)

Run **6 → 7 → 8** as one iteration. **Do not** finish the delivery loop after implement + pytest only. **Do not** offer implementation-review as an optional follow-up — it is always in-loop.

6. **Implementation review (every iteration).** Run `python3 scripts/delivery_record_gate.py assert-full-pytest` first. Then **`implementation-review`** with plan path, changed files, domain summaries, and test evidence (4a, 4b, 5). Reviewer checks each plan step **Done when** vs implementation. Save review under `.cursor/plans/reviews/`, then record: `python3 scripts/delivery_record_gate.py record-implementation-review --review-path <file> --parse`.
7. **Apply findings.** Fix every **CRITICAL** and **IMPORTANT** gap from step 6. Address **MINOR** when cheap; they do not block loop exit. Re-record implementation-review after each clean pass.
8. **Re-validate after fixes.** Re-run **3b → 4a → 4b → 5** (domain review when paths still match). Record gates again.

**Exit the review loop** only when the latest implementation-review has:

- **0 CRITICAL** and **0 IMPORTANT** findings, and
- **Final recommendation: proceed** (not `fix required` or `blocked`).

If any CRITICAL/IMPORTANT remain → next iteration at **step 6** (always re-run implementation-review; never skip).

9. **Final defect pass.** After `assert-review-loop` passes, run `cursor-quality-review-gpt54-xhigh`. Missing full-suite evidence = IMPORTANT gap.

**Cursor hook:** `.cursor/hooks.json` runs `scripts/delivery_loop_stop_hook.py` on agent `stop` when `.cursor/delivery-state.json` exists, full pytest is recorded, and implementation-review is not clean — it auto-submits a follow-up to run step 6 (max 3 loops).
10. **Stuck-loop guard.** Same CRITICAL/IMPORTANT finding text twice in a row → stop and explain; do not spin forever.
11. **Deploy** only if the user explicitly requested it. `hetzner-deploy` + `CLAUDE.md`.
11b. **Status (optional).** If step 11 ran, `deploy-hetzner-status` (read-only ps/logs).

## Plan archive

When work merges, move plan to `.cursor/plans/archive/pr-<number>-<slug>.md` and keep reviews in `.cursor/plans/reviews/` (prefix filenames with `pr-<number>-` when helpful).

## Operating rules

- Plan is source of truth; steps need **`Files:`** and **`Done when:`** for subagent-driven work.
- **Fast gate** (4a+4b) + **full suite** (5) before each implementation-review iteration.
- **Implementation-review is mandatory** and runs inside the loop until clean (see review loop above).
- Alembic migrations stay SQLite-compatible.
- Never deploy implicitly.

## Completion summary (required)

When the loop is done, report: plan path, implement scope, fast/full validation, **each implementation-review iteration** (path + CRITICAL/IMPORTANT counts until clean), quality review, deploy/status.

**Forbidden:** ending with only “plan saved” or “say if you want implementation-review” after code changed — that means the review loop was skipped.

## Provenance

Tier 1 + Tier 2 agent engineering (2026-05-28).
