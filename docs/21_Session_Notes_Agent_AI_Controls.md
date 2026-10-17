# Session Notes — Agent reliability, AI controls, and housekeeping

What this session added on top of Phases 8–13, why, and where the code
lives. Read this first when picking the codebase up again.

## 1. How the app runs now (the big picture)

InsightFlow is **two processes** sharing one SQLite database
(`%LOCALAPPDATA%\InsightFlow\database\insightflow.db`):

| Process | Start command | Owns |
|---|---|---|
| **Desktop UI** | `.\.venv\Scripts\pythonw.exe -m insightflow` | The window. Never runs monitoring or AI itself. |
| **Background Agent** | started automatically by the Desktop (or `python -m insightflow.bootstrap.agent`, or the Windows logon task) | Gmail/Pub/Sub monitoring worker, AI worker, desired-state reconciler. |

The **database is the only channel between them** — no IPC, no ports.
The Desktop writes intent (desired monitoring state, settings, "please
analyze this event"); the Agent polls and acts.

**Starting the app is now one command:** the Desktop launches the Agent
(see §2.1). A second Agent exits immediately (single-instance lock), so
starting the Desktop twice is harmless. Closing the Desktop does **not**
stop the Agent.

To stop the Agent (e.g. before restarting after a code change):

```powershell
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object CommandLine -like '*bootstrap.agent*' | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

**Logs:** the venv uses Microsoft Store Python, whose AppData writes are
redirected. Real log folder:
`%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\Local\InsightFlow\logs\`
(`insightflow.log`, plus `agent-output.log` for the windowless Agent).

## 2. Features and fixes

### 2.1 Desktop starts the Background Agent
- `infrastructure/process/agent_launcher.py` — starts
  `pythonw -m insightflow.bootstrap.agent` detached (no console window,
  own process group, stdout/stderr → `agent-output.log`).
- Called from `bootstrap/startup.py:main()`. Best effort: if it fails the
  Desktop still opens and logs a warning.
- No "is it running?" probe — probing the lock could make a starting Agent
  exit; the Agent's own `SingleInstanceLock` handles duplicates.

### 2.2 Fix: Start Monitoring permanently disabled after an unclean Agent exit
- **Bug:** if the Agent was closed/killed while monitoring, the DB kept
  status `RUNNING`. The Desktop never reconciles worker liveness and
  disables *Start Monitoring* while status is RUNNING → deadlock.
- **Fix:** `MonitoringDesiredStateReconciler` runs the existing liveness
  reconciliation once on Agent start (`_correct_stale_status`), turning a
  leftover RUNNING into PAUSED.
  Files: `application/services/monitoring_reconciler.py`,
  `application/use_cases.py`.

### 2.3 Fix: Analyze clicks never ran (stuck in AI_PROCESSING)
- **Bug:** the Desktop put AI jobs on an in-memory queue inside the
  *Desktop* process, which has no AI worker.
- **Fix:** the database is the hand-off. The Desktop only marks the event
  `AI_PROCESSING`; the Agent's `AIWorker` scans for such events
  (`find_pending_ai_jobs`) when its queue is idle (every ~5 s and at
  start, which also recovers jobs lost on an Agent restart). A job that
  raises (e.g. topic has no AI profile) marks its event `FAILED` instead of
  being re-found forever (`mark_ai_job_failed`).
  Files: `application/services/ai_worker.py`, `ai_dispatch.py`,
  `use_cases.py`; new repo query `IntelligenceEventRepository.list_by_status`.

### 2.4 Fix: "Market impact requires direction, score, relevance…" failures
- **Cause:** the prompt offered `NOT_APPLICABLE` as a direction and allowed
  null details, but the validator rejected that combination.
- **Fix:** `NOT_APPLICABLE`/blank direction with no details = "no market
  impact"; the prompt now says to set all four fields to null. Genuinely
  partial answers are still rejected.
- Also: a Bedrock reply cut off at the token limit now fails with
  "AI response was cut off at the output token limit (N)…" instead of a
  generic "provider error" (`infrastructure/ai/bedrock_adapter.py`).

### 2.5 AI profiles: edit, delete, output style
On **Topics**: *Edit AI Profile*, *Delete AI Profile*, *Create AI Profile*.

- **Edit** — name, description, instructions, output style. Changing the
  instructions or style creates a **new profile version**; earlier analyses
  keep the version they used. Use *Re-analyze* to apply a change to an
  existing event.
- **Delete** — the profile disappears from lists and lookups, every topic
  using it becomes "Not configured", and **analyses it produced are kept**
  (they reference the profile by foreign key, so the row is retained and
  recorded in `ai_profile_deletions`). The name can be reused immediately.
- **Output style** (`AIOutputStyle`):
  - `ANALYSIS` — the fixed structured analysis (summary, key facts, why it
    matters, what to watch, sentiment, market impact).
  - `CUSTOM_TEXT` — the AI writes exactly what the instructions ask for
    (e.g. a Tamil YouTube Shorts news script), stored as
    **Generated content**, plus a one-line English summary for lists. No
    market/sentiment fields are requested.
  - Stored inside the profile version's `output_schema_json`
    (`{"schema_version": "v1", "output_style": "..."}`), older versions
    default to `ANALYSIS`.
- Files: `domain/entities/ai_profile.py` (`revise`, `output_style`),
  `application/commands/ai_profiles.py`
  (`UpdateAIProfileUseCase`, `DeleteAIProfileUseCase`, `GetAIProfileUseCase`),
  `application/services/ai_prompt_builder.py`,
  `application/services/ai_response_validator.py`,
  `presentation/dialogs/create_ai_profile_dialog.py`,
  `presentation/views/topics_view.py`.

### 2.6 Intelligence page shows only what the AI produced
Empty sections (e.g. "Market impact: —") are hidden; a `CUSTOM_TEXT`
result shows a **Generated content** section first
(`presentation/views/intelligence_view.py:_ai_sections`).

### 2.7 Settings → AI analysis
- **"Analyze new emails automatically"** switch.
  - **Off:** new emails are still collected and toasted but stay
    `RECEIVED`; turning it off **cancels every analysis still waiting**
    (`AI_PROCESSING` → `RECEIVED`, new domain method
    `IntelligenceEvent.cancel_ai_processing`); automatic jobs already queued
    in the Agent are dropped just before their AI call (`ai_job_should_run`).
  - **Analyze / Re-analyze clicks always run**, even while off
    (`AIAnalysisJob.manual = True`).
  - **Back on:** only emails arriving from then on are analyzed — the
    backlog is never worked through automatically (cost control).
- **Max output tokens** — overrides `INSIGHTFLOW_AI_MAX_OUTPUT_TOKENS`
  (64–64000); *Reset to default* goes back to `.env`. Read per analysis.
- Both settings live in the new `app_settings` table, so the Agent applies
  them **without a restart**. `INSIGHTFLOW_AI_ENABLED` in `.env` is still
  the master switch (AI unavailable at all when false).
- Files: `application/commands/ai_settings.py`,
  `presentation/viewmodels/settings_view_model.py`,
  `presentation/views/settings_view.py`.

### 2.8 Clear all
- **Notifications → Clear all** — deletes every notification; events and
  analyses stay.
- **Intelligence → Clear all** — deletes every event with its analyses,
  generated content and notifications (FK cascades). Gmail is untouched.
  Cleared messages are **remembered** (`cleared_event_sources`) and never
  re-imported: full sync re-reads the latest ~50 messages per label on each
  Agent start, which would otherwise bring them all back with new toasts
  and AI cost. Ingestion treats them as duplicates
  (`CreateIntelligenceEventUseCase`).
- Both ask for confirmation; neither can be undone.

### 2.9 Smaller changes
- All timestamps display as `dd/mm/yyyy` (`presentation/formatting.py`).
- Analysis failure reasons for invalid AI responses now include the
  adapter's message (never raw model output).

## 3. Database migrations added

All additive (`CREATE TABLE IF NOT EXISTS`, no `ALTER TABLE`, per
`infrastructure/database/migrations.py`). Applied automatically on start.

| # | Table | Purpose |
|---|---|---|
| 004 | `app_settings` | Settings changed in the UI that the Agent reads live (`ai.max_output_tokens`, `ai.analysis_enabled`). Missing key = `.env` default. |
| 005 | `ai_analysis_contents` | Generated text of `CUSTOM_TEXT` analyses. |
| 005 | `ai_profile_deletions` | Deleted profiles (rows kept for analysis FKs). |
| 006 | `cleared_event_sources` | Gmail message ids cleared by the user, so they are not re-imported. Ids only, never content. |

## 4. Operational notes

- **Pub/Sub subscription expiry.** Google deletes a pull subscription after
  31 days without activity (default). That silently broke real-time
  monitoring once (every pull failed with `PubSubSubscriptionError`).
  `insightflow-gmail-sub-1` was recreated; set **Expiration period → Never
  expire** in Google Cloud Console.
- **Pub/Sub errors are logged by type only.** If pulls fail again, the next
  improvement is logging Google's error message so the cause is visible.
- **Real-time vs catch-up:** new mail arrives in real time via Pub/Sub; on
  every Agent start a full sync also catches up the latest messages per
  monitored label.
- **AI cost:** Bedrock `claude-opus-4-6` averaged ~13 s per analysis.
  Leave automatic analysis off while testing; use Analyze on demand.

## 5. Tests

`pytest` — 491 passed, 1 skipped (live Bedrock smoke test, opt-in via
`INSIGHTFLOW_RUN_REAL_AI_TESTS=1`). `ruff check`, `ruff format --check`,
and `mypy src` are clean. New/extended tests cover every item above:
`test_ai_settings.py`, `test_ai_custom_output.py`, `test_clear_all.py`,
`test_ai_worker.py`, `test_monitoring_commands.py`,
`test_agent_launcher.py`, the presentation UI tests, and
`tests/integration/test_repositories.py` / `test_migrations.py`.
