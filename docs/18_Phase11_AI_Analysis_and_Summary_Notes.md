# Phase 11 — AI Analysis and Summary

## 1. Scope

Phase 11 turns a persisted `IntelligenceEvent` into a validated `AIAnalysis`:
summary, key facts, why it matters, what to watch, sentiment, market
impact, confidence, and entities — generically, for any Topic, via a
provider-neutral boundary. It covers both roadmap "Phase 11 — AI Provider"
and "Phase 12 — AI Analysis and Summary" from `docs/13_Implementation_Roadmap.md`,
since the domain/persistence layers already assumed both exist together and
splitting them would have meant a half-working intermediate state.

The initial (and only) provider is **AWS Bedrock**, selected because
`.env.example` already reserved `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/
`AWS_REGION` "for later phases" and `docs/12_AI_Analysis_and_Summary_Design.md`
/ `docs/13_Implementation_Roadmap.md` both name Bedrock as the intended first
provider.

## 2. Architecture

```
Gmail ingestion (Phase 9/10)
      |
IntelligenceEvent created  --(on_event_created callback)-->  AIAnalysisDispatcher
      |                                                              |
      |                                            (profile configured + AI enabled?)
      |                                                              |
      |                                                      mark_processing()
      |                                                              |
      |                                                     enqueue AIAnalysisJob
      |                                                              |
                                                              AIWorker (daemon thread)
                                                                      |
                                                     AnalyzeIntelligenceEventUseCase
                                                                      |
                                                    AIPromptBuilder -> AIProvider.analyze()
                                                                      |
                                                          AIResponseValidator
                                                                      |
                                                 AIAnalysis persisted (COMPLETED/FAILED)
                                                                      |
                                            IntelligenceEvent.mark_completed()/mark_failed()
                                                                      |
                                     MonitoringEventBroadcaster.notify() (Phase 10 refresh chain)
                                                                      |
                                                        Intelligence page auto-refreshes
```

Manual "Analyze"/"Re-analyze" in the Intelligence UI calls
`ReprocessAIAnalysisUseCase`, which does the same `mark_processing()` +
enqueue, then returns immediately — the actual provider call always
happens on the `AIWorker` thread, never on the Qt GUI thread or the Gmail
monitoring worker thread.

## 3. What's new

- `application/ports/ai.py` — `AIProvider` protocol, `AIAnalysisRequest`/`AIAnalysisResponse`.
- `application/exceptions/ai.py` — `AIProviderError` family, `AIResponseValidationError`.
- `application/dto/ai.py` — `AIAnalysisJob`.
- `application/services/ai_prompt_builder.py` — provider-neutral prompt construction.
- `application/services/ai_response_validator.py` — reuses domain constructors (`Sentiment`, `Confidence`, `MarketImpact`, `MarketImpactDirection`) as validation.
- `application/services/ai_dispatch.py` — `AIAnalysisDispatcher`, wired as `IngestTopicMessagesUseCase`'s `on_event_created` callback.
- `application/services/ai_worker.py` / `ai_worker_handle.py` — background worker + process-wide handle, mirroring `GmailMonitoringWorker`/`MonitoringWorkerHandle`.
- `application/commands/ai.py` — `AnalyzeIntelligenceEventUseCase` (new); `ReprocessAIAnalysisUseCase` (real implementation, replacing the Phase 5 placeholder).
- `infrastructure/ai/bedrock_adapter.py` + `errors.py` — the only files that import `boto3`/`botocore`.
- `configuration/models.py` / `loader.py` — `AISettings`, `INSIGHTFLOW_AI_*` env vars.
- Intelligence UI: AI status line, entities/sentiment/confidence display, Analyze/Re-analyze button, status bar AI indicator.

## 4. Reuse, not reimplementation

- **No new domain entities, value objects, or DB tables.** `AIAnalysis`, `AIProfile`, `MarketImpact`, `Confidence`, `Sentiment`, and the `ai_profiles`/`ai_profile_versions`/`ai_analyses` tables already existed and had every field Phase 11 needs.
- **No migration.** `002_monitoring_state.sql` remains the latest; nothing new was required.
- **The domain event that was built but never dispatched, finally gets dispatched.** `IngestTopicMessagesUseCase.ingest_message()` already constructed an `IntelligenceEventCreated` domain event on every successful creation; it was previously discarded by every caller. Phase 11 adds an optional `on_event_created` callback invoked at that exact site — one hook point shared by Pub/Sub history sync, full sync, and manual "Save recent messages."
- **The event state machine that was built but never driven, finally gets driven.** `EventProcessingStatus.AI_PENDING`/`AI_PROCESSING` existed since Phase 4 but nothing ever set them. `AIAnalysisDispatcher` and `ReprocessAIAnalysisUseCase` now call the existing `IntelligenceEvent.mark_processing()`/`mark_completed()`/`mark_failed()` methods.
- **The exact Phase 10 refresh chain is reused unchanged**: `MonitoringEventBroadcaster` → `MonitoringRefreshBridge` (Qt signal, debounced) → `PresentationRefreshHub` → `MainWindow._on_refresh_signal` → `page.refresh()`. `AnalyzeIntelligenceEventUseCase` calls the same broadcaster instance with a new reason string (`"ai_analysis_completed"`/`"ai_analysis_failed"`). No new refresh plumbing, no polling.
- **`AIAnalysisRepository` stays append-only.** Rather than adding an `update()` method to persist an interim "PENDING" row, "AI analysis in progress…" is signaled entirely via `IntelligenceEvent.status == AI_PROCESSING`. Only one, final, terminal `AIAnalysis` row (`COMPLETED` or `FAILED`) is ever inserted per analysis attempt — consistent with the existing version-history design.

## 5. The one domain change (and why)

`IntelligenceEvent._PROCESSING_SOURCES` (in `domain/entities/intelligence_event.py`)
did not include `COMPLETED`/`FAILED`, so `mark_processing()` could not restart
an already-terminal event. Manual re-analysis is an explicit Phase 11
requirement (spec §9/§18, Test 5), so this one-line addition was made:

```python
_PROCESSING_SOURCES = frozenset({
    ...,
    EventProcessingStatus.COMPLETED,
    EventProcessingStatus.FAILED,
})
```

This is the only change to a domain entity in Phase 11. No new states, no
new methods, no signature changes — both the first analysis and every
re-analysis now go through the identical `mark_processing()` →
`mark_completed()`/`mark_failed()` path.

## 6. AI profile → provider request

`AIPromptBuilder` builds one `AIAnalysisRequest` per job from:

- `AIProfile.instructions` (the profile's own system prompt — topic-specific, data-driven; nothing about Trump/Iran/Modi/celebrities/companies is hardcoded anywhere in the pipeline)
- the event's title/content (truncated to `AISettings.max_input_chars`)
- the resolved Topic's name (for context only)
- mandatory safety instructions: distinguish facts from interpretation, never fabricate missing information, reflect genuine uncertainty in `confidence`, never output trading orders/position sizes/buy-sell instructions, market impact is interpretive judgment, not a guaranteed prediction
- a strict JSON response schema (`concise_summary`, `key_points`, `why_it_matters`, `what_to_watch`, `sentiment`, `market_impact_direction`, `market_impact_score`, `market_impact_relevance`, `market_impact_reasoning`, `market_impact_affected_assets`, `confidence`, `entities`)

`Topic.ai_profile_id` was already fully wired (domain, DTOs, persistence)
from earlier phases — Phase 11 only had to consume it, not build it.

## 7. Structured output validation

`BedrockAIProvider` parses the model's JSON text into a provider-neutral
`AIAnalysisResponse` (raising `AIProviderInvalidResponseError` on malformed
JSON — this happens in infrastructure, so raw provider JSON never crosses
into the application layer). `AIResponseValidator` then applies semantic
validation, reusing domain constructors instead of re-implementing rules:

- `summary` must be non-empty
- `key_points`/`what_to_watch`/`entities` must be lists of non-empty strings
- `sentiment`, if present, must construct `Sentiment(value)`
- `confidence`, if present, must construct `Confidence(value)` (`0.0`–`1.0` inclusive, enforced by the value object itself)
- market impact is all-or-nothing: if any of direction/score/relevance/reasoning is present, all four must validate into a `MarketImpact`, or the whole response is rejected — no fabricated defaults

Any validation failure results in a `FAILED` `AIAnalysis`, never a silently
coerced/fabricated one.

## 8. Idempotency and re-analysis

- Duplicate Gmail Pub/Sub notifications for the same message never reach the dispatcher a second time — Phase 9's `find_by_external_id` dedup means `CreateIntelligenceEventUseCase` raises `DuplicateEventError`, and `ingest_message()` never constructs a second `IntelligenceEventCreated` for it.
- The dispatcher additionally guards `mark_processing()` with `InvalidStateTransitionError` handling, so even a hypothetical double-dispatch of the same event is a no-op, not a duplicate analysis.
- Manual re-analysis calls the identical `mark_processing()` → enqueue → `AnalyzeIntelligenceEventUseCase` path. Each attempt inserts one new, final `AIAnalysis` row; `find_latest_by_event` (ordered by `created_at DESC`) always surfaces the most recent one. History is preserved, not overwritten.

## 9. AI worker

`AIWorker` mirrors `GmailMonitoringWorker` deliberately:

- plain `threading.Thread(daemon=True)`, never Qt
- one bounded `queue.Queue[AIAnalysisJob]` (`AISettings.queue_max_size`, default 100)
- `stop(join_timeout_seconds=0)` is non-blocking and safe to call from the Qt GUI thread on shutdown
- exceptions from one job are caught and logged; the loop and the rest of the queue are unaffected

`AIWorkerHandle` mirrors `MonitoringWorkerHandle`: one process-wide slot,
stopped from `bootstrap/shutdown.py` alongside the monitoring worker.

Unlike Gmail monitoring (started only by an explicit "Start Monitoring"
click), the AI worker starts automatically at app boot when
`AISettings.enabled` is true — reprocessing and automatic analysis must
work independently of whether Gmail real-time monitoring is running.

## 10. Automatic vs. manual triggering — one shared path

Both triggers only ever enqueue an `AIAnalysisJob`; `AnalyzeIntelligenceEventUseCase`
is the single place a provider is ever called:

- **Automatic**: `AIAnalysisDispatcher.dispatch()`, called from `IngestTopicMessagesUseCase.ingest_message()`. Gated by `AISettings.enabled and AISettings.automatic_analysis_enabled`, the event having a `topic_id`, and that topic having a configured, enabled `AIProfile`. Never raises.
- **Manual**: `ReprocessAIAnalysisUseCase.execute()`, called from the Intelligence UI's Analyze/Re-analyze button. Gated only by `AISettings.enabled` (not `automatic_analysis_enabled` — a global "AI enabled" switch, separate from "auto-trigger on new mail"). Accepts an explicit profile override or falls back to the topic's configured profile; raises `AIProfileNotConfiguredError`/`AIProviderUnavailableError` on failure so the UI can show a clear message.

## 11. Error handling and privacy

- AI failures never roll back `IntelligenceEvent`/ingestion: `AnalyzeIntelligenceEventUseCase` persists a `FAILED` `AIAnalysis` and transitions the event to `FAILED`, but this happens in a separate, later unit-of-work from ingestion — a broken AI call can never undo a persisted email.
- `BedrockAIProvider` never logs the prompt, the raw response text, or credentials — only event id, model id, token counts (if present), and sanitized exception type names.
- `AnalyzeIntelligenceEventUseCase` caps persisted failure reasons at 500 characters and only ever stores `type(exc).__name__`-style messages or the validator's own field-name-only messages — never raw provider output.
- AWS credentials are resolved by boto3's default credential chain; InsightFlow never reads, stores, or logs them (no `SecretStore` entry, no config field, no DB column).

## 12. Cost / safety controls

- `AISettings.enabled` defaults to `false` — no AI calls, no AWS cost, until explicitly turned on.
- Bounded `timeout_seconds`/`max_retries`/`max_output_tokens` are enforced by botocore's own `Config(read_timeout=..., retries={"max_attempts": ...})` — no custom retry loop.
- Bounded job queue (`queue_max_size`) — a burst of new events cannot grow memory unbounded; when full, automatic dispatch silently drops (logged) and manual reprocess surfaces `AIProviderUnavailableError` to the user.
- `max_input_chars` truncates event content before it reaches the provider.

## 13. Explicitly NOT implemented in Phase 11

- YouTube, video generation, speech/audio generation
- Story grouping
- Notifications/toasts
- Attachment downloading
- Social-media publishing
- Scheduled reports
- Autonomous trading / trading orders / market prediction guarantees
- A second AI provider (OpenAI/Anthropic direct/Gemini/local) — the port is provider-neutral and ready for one, but only Bedrock is implemented
- A durable AI job queue table — the in-process `queue.Queue` is intentionally in-memory only (Phase 10's monitoring worker follows the same pattern); a job dropped because the app closed mid-queue is recoverable via manual "Re-analyze"

## 14. Design decisions worth a second look

- **In-memory job queue, not a DB-backed queue.** If the app closes while jobs are queued, they are lost (not persisted as "pending" anywhere) — the user would need to notice and click "Re-analyze". This mirrors the existing Gmail monitoring worker's philosophy (daemon thread, no durable queue) but is worth revisiting if AI volume grows.
- **`IntelligenceEvent.status` reused as the sole "in progress" signal.** This avoids an `AIAnalysisRepository.update()` method, but it does mean the event's own status field is now doing double duty (overall pipeline lifecycle *and* "is AI currently running"). If a future phase adds more post-AI pipeline steps (e.g. notification dispatch) that also need their own event-status transitions, this may need revisiting.
- **One shared `MonitoringEventBroadcaster`** is reused for both Gmail monitoring events and AI analysis events (distinguished only by reason string). Simpler than adding a second broadcaster; revisit if reason-string collisions ever become a real risk.
- **Reprocess is gated only by `AISettings.enabled`, not `automatic_analysis_enabled`.** Chosen deliberately (manual action should work even when auto-trigger is off), but is a judgment call — flag if product intent differs.

## 15. Testing

- `tests/fakes/ai.py` — `FakeAIProvider`, used by all application-layer tests; no real AI credentials required for the normal suite.
- `tests/unit/application/test_ai_prompt_builder.py`, `test_ai_response_validator.py`, `test_ai_dispatch.py`, `test_ai_worker.py`, `test_ai.py` — cover success, provider timeout/auth/unavailable/malformed-JSON, invalid sentiment/confidence/market-impact, profile-not-configured, AI-disabled, queue-full, re-analysis from a completed event, worker exception containment and non-blocking shutdown.
- `tests/unit/infrastructure/test_bedrock_adapter.py` — fully offline via `botocore.stub.Stubber`; exercises success mapping, malformed JSON, throttling, access-denied, and read-timeout translation.
- `tests/manual/test_bedrock_live_smoke.py` — real AWS Bedrock call; skipped unless `INSIGHTFLOW_RUN_REAL_AI_TESTS=1` is set. Not part of the normal suite.
- `tests/architecture/test_dependency_rules.py` — `test_infrastructure_ai_may_import_aws_sdk` (positive) + `test_non_ai_layers_do_not_import_aws_sdk` (negative), mirroring the existing Gmail/Google-SDK guard pair.

### Manual provider setup (for the live smoke test)

1. Ensure AWS credentials are resolvable via boto3's default chain (env vars, `~/.aws/credentials`, or an IAM role) and the account has Bedrock model access for the configured `model_id`.
2. Set `INSIGHTFLOW_AI_MODEL_ID`/`INSIGHTFLOW_AI_REGION` if not using the defaults.
3. Run `INSIGHTFLOW_RUN_REAL_AI_TESTS=1 pytest tests/manual/test_bedrock_live_smoke.py -s`.

## 16. Deferred to later phases

- A second AI provider implementation
- Durable/DB-backed AI job queue
- **AI-profile authoring UI.** The Topic creation dialog already has an
  `ai_profile_id` text field (from earlier phases) — a user can attach an
  *existing* profile's ID to a Topic. But there is no UI to actually create
  an `AIProfile` (name/instructions/output_schema_version); today that
  requires inserting one directly via the repository/DB. Without at least
  one seeded profile, "Analyze" will raise `AIProfileNotConfiguredError`.
  This is the main practical gap between "Phase 11 is implemented" and
  "a user can drive it end-to-end from the GUI alone."
- Notification dispatch driven by completed AI analyses
- Story grouping using AI analysis output
