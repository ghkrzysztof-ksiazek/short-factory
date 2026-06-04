# Implementation Review — Short Factory Full Build Plan

**Plan:** `/Users/krzysztof/.cursor/plans/Short Factory Build-7c3879a7.plan.md`  
**Worktree:** `/Users/krzysztof/git/short-factory`  
**Reviewed:** 2026-06-04  
**Validation:** `PYTHONPATH=src python -m pytest tests/ -q` → **6 passed**, exit 0

---

## Coverage Summary

| Phase | Plan Goal | Status | Notes |
|-------|-----------|--------|-------|
| 0 — Foundation | Skeleton + job plumbing | **PARTIAL** | All infra files present; research task is full pipeline (not no-op stub); Celery retry/DLQ incomplete |
| 1 — Research | Scrape, score, store topics | **PARTIAL** | Reddit/YouTube scrapers, taxonomy, virality formula, LLM classify, Beat schedule, `GET /topics` — word-overlap dedup (not embeddings); mock data yields ~13 topics (<20 exit) |
| 2 — Scripts | LLM scripts + validation | **PARTIAL** | Prompts, validator, hook variants, statuses, APIs present; no optimization weight injection |
| 3 — Scene + Voice | Scene plan + TTS | **PARTIAL** | Scene planner, per-scene TTS, merge, S3 upload — **master audio not persisted as Asset row**; timing is estimated not word-level from TTS |
| 4 — Visuals + Subs | Stock + subtitles | **PARTIAL** | Pexels + FFmpeg fallback, SRT/ASS — verification checks S3 existence only, not duration alignment |
| 5 — Render + QA | FFmpeg 9:16 + QA | **PARTIAL** | Concat, subs overlay, duration/vertical/audio QA — no black-frame check, no subtitle overlap QA, no channel template profiles; MoviePy not used |
| 6 — Publish | YouTube + stubs | **PARTIAL** | Publisher adapters, publications table — OAuth client creds empty; no Celery scheduled publish task |
| 7 — Analytics | Feedback loop | **PARTIAL** | Collection + `OptimizationWeight` writes — **weights never read** by research/scripts; winning hooks not injected |
| 8 — Hardening | Queues, deploy, monitoring | **PARTIAL** | Separate queues, rate limit, admin UI, Hetzner script, `/metrics` JSON — no backup strategy; not Prometheus |

**Structural coverage:** ~75% of planned modules/files exist  
**Behavioral / exit-criteria coverage:** ~45%

---

## Gap Analysis

### CRITICAL

| ID | Gap | Evidence |
|----|-----|----------|
| C1 | **Master audio asset not stored in DB** — render pipeline cannot find narration | `media/pipeline.py` uploads master to S3 but never `db.add(Asset(...))`; `render/ffmpeg_renderer.py` searches `AssetType.VOICE` with `"master"` in key |
| C2 | **Celery retry/DLQ non-functional** — tasks never call `self.retry()` | `workers/tasks.py` `_task_wrapper` catches exceptions, updates job status, re-raises — no `self.retry(exc=exc)` despite `max_retries=3` on decorators |
| C3 | **Analytics feedback loop not wired to pipeline** | `OptimizationWeight` written in `analytics/collector.py` but zero reads in `research/` or `scripts/`; Phase 7 exit criterion unmet |
| C4 | **YouTube OAuth publisher broken for real uploads** | `publish/publishers.py` `Credentials(client_id="", client_secret="")` — token refresh will fail without configured OAuth client |

### IMPORTANT

| ID | Gap | Evidence |
|----|-----|----------|
| I1 | Phase 0 exit: plan says research stub/no-op; implementation runs full scrape pipeline | `workers/tasks.py` `run_research` calls `run_research_pipeline()` |
| I2 | Semantic dedup specified; word-overlap heuristic implemented | `research/classifier.py` `is_duplicate()` — no embeddings |
| I3 | Grok LLM adapter planned; only OpenAI + Anthropic | `shared/llm.py` — no Grok provider |
| I4 | Google Trends / TikTok sources in architecture; not implemented | Only Reddit + YouTube scrapers |
| I5 | Mock research produces ~13 topics; exit requires ≥20 | `reddit_scraper._mock_reddit_topics()` returns 10 + YouTube mock 3 |
| I6 | No integration tests (DB, Celery, render end-to-end) | Only 6 unit/API smoke tests |
| I7 | Docker Compose stack not verified | Docker daemon unavailable during build |
| I8 | Scheduled publish via Celery not implemented | `publish/publishers.py` accepts `scheduled_at` but no beat task or delayed publish |
| I9 | Channel template profiles (font, colors) for render missing | Plan Phase 5 — no `style_config` consumption in renderer |
| I10 | QA missing black frames, subtitle overlap/unreadable speed checks | `render/ffmpeg_renderer.py` `run_qa_checks` — duration, vertical, audio quiet only |
| I11 | Asset verification: duration match not checked | `media/pipeline.py` `verified=storage.exists()` only |
| I12 | Backup strategy for Postgres + object storage absent | Phase 8 requirement |

### MINOR

| ID | Gap | Evidence |
|----|-----|----------|
| M1 | MoviePy listed in tech stack; not in dependencies or code | `pyproject.toml` — FFmpeg only |
| M2 | `/metrics` returns JSON, not Prometheus format | `api/metrics.py` |
| M3 | Admin UI lacks script approval / publish calendar | `/admin` — trigger buttons only |
| M4 | `ping` Celery task exists but no API endpoint | Plan Phase 0 checklist item 4 |
| M5 | TTS timing estimated from word count, not provider timestamps | `media/tts.py` `_estimate_word_timing` |
| M6 | `delivery_record_gate.py` absent (delivery-loop gate) | Not in repo |
| M7 | Plan todos still `pending` in frontmatter | Plan file not updated post-implementation |

---

## Alignment Score

**58%**

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Repository layout | 95% | Matches proposed structure |
| Data model | 90% | All planned tables + migration |
| API surface | 85% | Most endpoints present |
| Pipeline behavior | 50% | Master audio bug breaks render; feedback loop open |
| Exit criteria | 35% | Most phase exit checks unverified or unmet |
| Test coverage | 25% | Unit only, no integration |
| Production readiness | 40% | OAuth, retry, backup gaps |

---

## Recommendations

### Priority 1 (before merge / first production run)

1. **Fix C1:** After master audio upload in `media/pipeline.py`, add `Asset(scene_plan_id=..., asset_type=VOICE, s3_key=master_key, verified=True)`.
2. **Fix C2:** In bound Celery tasks, pass `self` to wrapper and call `self.retry(exc=exc)` when retries remain; only mark DEAD_LETTER after final failure.
3. **Fix C3:** Read `OptimizationWeight` in `research/pipeline.py` (category boost) and `scripts/generator.py` (prompt injection for top categories/emotions).
4. **Fix C4:** Load YouTube OAuth client ID/secret from settings; document OAuth setup in README.

### Priority 2 (next sprint)

5. Add integration test: research → script → media → render with testcontainers (postgres, redis, minio) or pytest fixtures.
6. Implement Celery delayed publish for `scheduled_at`.
7. Replace word-overlap dedup with embedding similarity (OpenAI embeddings + cosine threshold).
8. Expand QA: ffprobe black-frame sampling, subtitle timing validation.
9. Wire channel `style_config` into ASS subtitle styling and render templates.

### Priority 3 (plan amendment or defer)

10. Grok adapter, Google Trends, TikTok scrapers — document as deferred.
11. MoviePy — remove from plan or add dependency.
12. Prometheus `/metrics` exporter.
13. Backup runbook + scripts for Postgres/MinIO.

---

## Final Recommendation

**fix required**

| Check | Required | Actual |
|-------|----------|--------|
| CRITICAL count | 0 | **4** |
| IMPORTANT count | 0 | **12** |
| Final recommendation | proceed | **fix required** |

The implementation delivers a credible skeleton across all nine phases with correct module boundaries, schema, and API shape. However, four critical gaps — especially the missing master audio asset record — would break the core render path in production. The analytics feedback loop is write-only. Celery retries do not actually retry.

**Do not advance the delivery loop** until C1–C4 are resolved and at least integration smoke coverage exists for the render path.

---

## Validation Evidence

| Gate | Result |
|------|--------|
| `scripts/delivery_record_gate.py assert-full-pytest` | Script absent — gate skipped |
| Full pytest | `PYTHONPATH=src python -m pytest tests/ -q` → 6 passed |
| Ruff | All checks passed (E501 ignored) |
| Docker Compose | Not verified — daemon unavailable |
| Integration / E2E | None |
