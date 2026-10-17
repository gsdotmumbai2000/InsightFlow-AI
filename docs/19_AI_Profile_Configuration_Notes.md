# AI Profile Configuration (Phase 11 follow-up)

This is a small addendum to Phase 11, not a new phase. It adds the minimum
application/UI capability needed to create an `AIProfile` and assign it to
an existing Topic, so the already-complete Phase 11 AI pipeline
(`AnalyzeIntelligenceEventUseCase` → `AIPromptBuilder` → `BedrockAIProvider`
→ `AIResponseValidator` → `AIAnalysis`) has something to run against. No
part of that pipeline was changed.

## What an AI Profile represents

An `AIProfile` is **topic-specific analysis intent** — what the AI should
look for in an event and how it should interpret it. It is *not* provider
or model configuration; that remains controlled entirely by `AISettings`
(the `INSIGHTFLOW_AI_*` environment variables — provider, model ID, region,
timeout, temperature, etc.). A profile's `instructions` field is the first
block of the system prompt `AIPromptBuilder` sends to the provider; nothing
about a specific topic (e.g. "US market impact" vs. "celebrity reputation")
is ever hardcoded in application code — it is entirely data, stored in the
profile.

Fields (unchanged from the existing domain entity, `domain/entities/ai_profile.py`):

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Human-readable label shown in the Topics page picker. |
| `instructions` | yes | The analysis intent — what to look for, how to interpret it. |
| `output_schema_version` | yes | Forward-compatibility marker; `"v1"` today. |
| `description` | no | Free-text note about the profile's purpose. |
| `version` | no (defaults to `1`) | Version number; profile updates are out of scope for now. |
| `enabled` | no (defaults to `true`) | A disabled profile is refused by both automatic dispatch and manual analysis. |

## How to create one

1. Open **Topics**.
2. Select the Topic you want to analyze (e.g. `TRUMP`).
3. Click **Create AI Profile**.
4. Fill in **Name**, optionally **Description**, the **Instructions** (multi-line — this is the analysis intent, described above), and **Output schema version** (defaults to `v1`).
5. If a Topic is selected, check **"Assign to '<topic>' after creation"** (checked by default) to attach the new profile immediately, or leave it unchecked to just add the profile to the picker for later use.
6. Click OK.

This calls `CreateAIProfileUseCase` (`application/commands/ai_profiles.py`), which builds the profile via the existing `AIProfile.create(...)` domain factory and persists it through the existing `AIProfileRepository` — no new domain rules, no schema change.

## How to assign a profile to a Topic

- **At creation time**: check the "Assign to '<topic>'" box in the Create AI Profile dialog (above).
- **At any other time**: select the Topic, then choose a profile from the **AI Profile** dropdown next to the Topics list. This calls the existing `UpdateTopicUseCase` (unchanged) with the selected profile's ID — the same use case that already existed and was already tested before this addendum; only the UI to invoke it was added.
- Selecting **"Not configured"** clears the Topic's profile assignment (`UpdateTopicUseCase` with `clear_ai_profile=True`).

The Topics table and the dropdown always show the profile's **name**, never its UUID.

## After assignment

Once a Topic has a profile attached, the existing Phase 11 Analyze / Re-analyze
flow works exactly as documented in
`docs/18_Phase11_AI_Analysis_and_Summary_Notes.md` — this addendum changes
nothing about how analysis is triggered, validated, or displayed.
