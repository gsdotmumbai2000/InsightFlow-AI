"""SQLite AI analysis repository."""

from __future__ import annotations

import sqlite3

from insightflow.domain import AIAnalysis, AIAnalysisId, EventId
from insightflow.infrastructure.database.errors import run_db
from insightflow.infrastructure.database.mappers import (
    analysis_from_row,
    analysis_to_row,
)


class SQLiteAIAnalysisRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, analysis: AIAnalysis) -> None:
        def _op() -> None:
            version_id = self._resolve_version_id(
                analysis.profile_id.value, analysis.profile_version
            )
            row = analysis_to_row(analysis, profile_version_id=version_id)
            self._connection.execute(
                """
                INSERT INTO ai_analyses (
                    id, event_id, ai_profile_id, ai_profile_version_id, provider,
                    model, headline, summary, why_it_matters, facts_json,
                    what_to_watch_json, entities_json, importance, priority,
                    confidence, sentiment, uncertainty_json, topic_analysis_json,
                    market_impact_json, follow_up_json, status, failure_reason,
                    raw_response_reference, input_tokens, output_tokens, latency_ms,
                    created_at, updated_at
                ) VALUES (
                    :id, :event_id, :ai_profile_id, :ai_profile_version_id, :provider,
                    :model, :headline, :summary, :why_it_matters, :facts_json,
                    :what_to_watch_json, :entities_json, :importance, :priority,
                    :confidence, :sentiment, NULL, NULL,
                    :market_impact_json, NULL, :status, :failure_reason,
                    NULL, NULL, NULL, :latency_ms,
                    :created_at, :updated_at
                )
                """,
                row,
            )

        run_db(_op, entity="ai_analysis")

    def get(self, analysis_id: AIAnalysisId) -> AIAnalysis | None:
        def _op() -> AIAnalysis | None:
            row = self._connection.execute(
                """
                SELECT a.*, v.version_number
                FROM ai_analyses a
                JOIN ai_profile_versions v ON v.id = a.ai_profile_version_id
                WHERE a.id = ?
                """,
                (analysis_id.value,),
            ).fetchone()
            return analysis_from_row(row) if row else None

        return run_db(_op, entity="ai_analysis")

    def list_by_event(self, event_id: EventId) -> list[AIAnalysis]:
        def _op() -> list[AIAnalysis]:
            rows = self._connection.execute(
                """
                SELECT a.*, v.version_number
                FROM ai_analyses a
                JOIN ai_profile_versions v ON v.id = a.ai_profile_version_id
                WHERE a.event_id = ?
                ORDER BY a.created_at DESC
                """,
                (event_id.value,),
            ).fetchall()
            return [analysis_from_row(row) for row in rows]

        return run_db(_op, entity="ai_analysis")

    def find_latest_by_event(self, event_id: EventId) -> AIAnalysis | None:
        items = self.list_by_event(event_id)
        return items[0] if items else None

    def _resolve_version_id(self, profile_id: str, version_number: int) -> str:
        row = self._connection.execute(
            """
            SELECT id FROM ai_profile_versions
            WHERE ai_profile_id = ? AND version_number = ?
            """,
            (profile_id, version_number),
        ).fetchone()
        if row is None:
            raise sqlite3.IntegrityError(
                f"FOREIGN KEY constraint failed: ai_profile_version "
                f"{profile_id}@{version_number}"
            )
        return str(row["id"])
