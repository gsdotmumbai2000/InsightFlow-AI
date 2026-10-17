"""Resolve currently-monitored Gmail label <-> Topic mappings (Phase 10).

A single shared helper so the watch lifecycle, history sync, and full-sync
paths all agree on which labels/Topics are "currently monitored" — never
hardcoded, always derived from enabled Gmail-backed Topics.
"""

from __future__ import annotations

from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import SourceType


def monitored_label_topic_map(uow: UnitOfWork) -> dict[str, str]:
    """Map Gmail label_id -> topic_id for enabled Gmail-backed Topics."""
    result: dict[str, str] = {}
    for topic in uow.topics.list_enabled():
        if topic.source_configuration.source_type is not SourceType.GMAIL:
            continue
        result[topic.source_configuration.source_identifier] = topic.id.value
    return result


def monitored_label_ids(uow: UnitOfWork) -> tuple[str, ...]:
    """Return the distinct Gmail label IDs currently eligible for watching."""
    return tuple(monitored_label_topic_map(uow).keys())
