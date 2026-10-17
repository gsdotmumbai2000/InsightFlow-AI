"""SQLite AI profile repository."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from insightflow.domain import AIProfile, AIProfileId
from insightflow.infrastructure.database.errors import run_db
from insightflow.infrastructure.database.mappers import (
    profile_from_rows,
    profile_to_rows,
)
from insightflow.infrastructure.database.serialization import datetime_to_db


class SQLiteAIProfileRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, profile: AIProfile) -> None:
        def _op() -> None:
            profile_row, version_row = profile_to_rows(profile)
            self._connection.execute(
                """
                INSERT INTO ai_profiles (
                    id, name, description, active_version_id, enabled,
                    created_at, updated_at
                ) VALUES (
                    :id, :name, :description, :active_version_id, :enabled,
                    :created_at, :updated_at
                )
                """,
                profile_row,
            )
            self._connection.execute(
                """
                INSERT INTO ai_profile_versions (
                    id, ai_profile_id, version_number, system_prompt,
                    output_schema_json, model_preferences_json, created_at,
                    created_by, is_active
                ) VALUES (
                    :id, :ai_profile_id, :version_number, :system_prompt,
                    :output_schema_json, :model_preferences_json, :created_at,
                    :created_by, :is_active
                )
                """,
                version_row,
            )

        run_db(_op, entity="ai_profile")

    def get(self, profile_id: AIProfileId) -> AIProfile | None:
        def _op() -> AIProfile | None:
            return self._load(profile_id.value)

        return run_db(_op, entity="ai_profile")

    def update(self, profile: AIProfile) -> None:
        def _op() -> None:
            existing = self._load(profile.id.value)
            if existing is None:
                raise KeyError(profile.id.value)
            profile_row, version_row = profile_to_rows(profile)
            # Keep one active version row for this version_number (replace content).
            self._connection.execute(
                """
                UPDATE ai_profile_versions
                SET is_active = 0
                WHERE ai_profile_id = ?
                """,
                (profile.id.value,),
            )
            current = self._connection.execute(
                """
                SELECT id FROM ai_profile_versions
                WHERE ai_profile_id = ? AND version_number = ?
                """,
                (profile.id.value, profile.version),
            ).fetchone()
            if current is None:
                self._connection.execute(
                    """
                    INSERT INTO ai_profile_versions (
                        id, ai_profile_id, version_number, system_prompt,
                        output_schema_json, model_preferences_json, created_at,
                        created_by, is_active
                    ) VALUES (
                        :id, :ai_profile_id, :version_number, :system_prompt,
                        :output_schema_json, :model_preferences_json, :created_at,
                        :created_by, :is_active
                    )
                    """,
                    version_row,
                )
                active_version_id = version_row["id"]
            else:
                active_version_id = current["id"]
                self._connection.execute(
                    """
                    UPDATE ai_profile_versions SET
                        system_prompt = ?,
                        output_schema_json = ?,
                        is_active = 1
                    WHERE id = ?
                    """,
                    (
                        version_row["system_prompt"],
                        version_row["output_schema_json"],
                        active_version_id,
                    ),
                )
            self._connection.execute(
                """
                UPDATE ai_profiles SET
                    name = ?,
                    description = ?,
                    active_version_id = ?,
                    enabled = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    profile_row["name"],
                    profile_row["description"],
                    active_version_id,
                    profile_row["enabled"],
                    profile_row["updated_at"],
                    profile.id.value,
                ),
            )

        run_db(_op, entity="ai_profile")

    def delete(self, profile_id: AIProfileId) -> None:
        def _op() -> None:
            self._connection.execute(
                """
                INSERT OR IGNORE INTO ai_profile_deletions (ai_profile_id, deleted_at)
                VALUES (?, ?)
                """,
                (profile_id.value, datetime_to_db(datetime.now(UTC))),
            )

        run_db(_op, entity="ai_profile")

    def list_all(self) -> list[AIProfile]:
        def _op() -> list[AIProfile]:
            rows = self._connection.execute(
                """
                SELECT id FROM ai_profiles
                WHERE id NOT IN (SELECT ai_profile_id FROM ai_profile_deletions)
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()
            profiles: list[AIProfile] = []
            for row in rows:
                loaded = self._load(row["id"])
                if loaded is not None:
                    profiles.append(loaded)
            return profiles

        return run_db(_op, entity="ai_profile")

    def _load(self, profile_id: str) -> AIProfile | None:
        profile_row = self._connection.execute(
            """
            SELECT * FROM ai_profiles
            WHERE id = ?
              AND id NOT IN (SELECT ai_profile_id FROM ai_profile_deletions)
            """,
            (profile_id,),
        ).fetchone()
        if profile_row is None:
            return None
        version_row = None
        if profile_row["active_version_id"]:
            version_row = self._connection.execute(
                "SELECT * FROM ai_profile_versions WHERE id = ?",
                (profile_row["active_version_id"],),
            ).fetchone()
        if version_row is None:
            version_row = self._connection.execute(
                """
                SELECT * FROM ai_profile_versions
                WHERE ai_profile_id = ?
                ORDER BY version_number DESC
                LIMIT 1
                """,
                (profile_id,),
            ).fetchone()
        if version_row is None:
            return None
        return profile_from_rows(profile_row, version_row)
