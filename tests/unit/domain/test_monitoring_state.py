"""MonitoringState domain entity tests (Phase 10)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from insightflow.domain import MonitoringState, MonitoringStatus


def _state() -> MonitoringState:
    return MonitoringState.create(account_id="user@example.com")


def test_create_defaults_to_not_configured() -> None:
    state = _state()
    assert state.status is MonitoringStatus.NOT_CONFIGURED
    assert state.current_history_id is None
    assert state.watch_expiration is None
    assert state.last_error is None


def test_status_transitions() -> None:
    state = _state()
    state.mark_starting()
    assert state.status is MonitoringStatus.STARTING
    state.mark_running()
    assert state.status is MonitoringStatus.RUNNING
    state.mark_paused()
    assert state.status is MonitoringStatus.PAUSED
    state.mark_stopped()
    assert state.status is MonitoringStatus.STOPPED
    state.mark_error("boom")
    assert state.status is MonitoringStatus.ERROR
    assert state.last_error == "boom"


def test_mark_running_clears_previous_error() -> None:
    state = _state()
    state.mark_error("boom")
    assert state.last_error == "boom"
    state.mark_running()
    assert state.last_error is None
    assert state.status is MonitoringStatus.RUNNING


def test_record_error_sets_last_error_without_changing_status() -> None:
    state = _state()
    state.mark_running()
    state.record_error("Pub/Sub pull failed: RuntimeError")
    assert state.last_error == "Pub/Sub pull failed: RuntimeError"
    assert state.status is MonitoringStatus.RUNNING


def test_update_watch_sets_cursor_and_expiration() -> None:
    state = _state()
    expiration = datetime.now(UTC) + timedelta(days=7)
    state.update_watch(history_id="100", expiration=expiration)
    assert state.current_history_id == "100"
    assert state.watch_expiration == expiration


def test_advance_history_updates_cursor_and_last_sync() -> None:
    state = _state()
    state.advance_history("200")
    assert state.current_history_id == "200"
    assert state.last_sync_at is not None


def test_record_notification_sets_timestamp() -> None:
    state = _state()
    assert state.last_notification_at is None
    state.record_notification()
    assert state.last_notification_at is not None


def test_is_active_only_for_starting_or_running() -> None:
    state = _state()
    assert state.is_active is False
    state.mark_starting()
    assert state.is_active is True
    state.mark_running()
    assert state.is_active is True
    state.mark_stopped()
    assert state.is_active is False


def test_watch_needs_renewal_when_no_expiration() -> None:
    state = _state()
    assert state.watch_needs_renewal(now=datetime.now(UTC), margin_hours=24) is True


def test_watch_needs_renewal_respects_margin() -> None:
    state = _state()
    now = datetime.now(UTC)
    state.update_watch(history_id="1", expiration=now + timedelta(hours=48))
    assert state.watch_needs_renewal(now=now, margin_hours=24) is False
    assert state.watch_needs_renewal(now=now, margin_hours=72) is True


def test_watch_needs_renewal_true_when_past_expiration() -> None:
    state = _state()
    now = datetime.now(UTC)
    state.update_watch(history_id="1", expiration=now - timedelta(hours=1))
    assert state.watch_needs_renewal(now=now, margin_hours=24) is True
