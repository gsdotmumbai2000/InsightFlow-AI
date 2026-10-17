"""GmailMonitoringWorker tests (Phase 10) — fakes only, real background thread."""

from __future__ import annotations

import time
from collections.abc import Callable

import pytest
from tests.fakes.pubsub import FakePubSubSubscriber

from insightflow.application.dto.monitoring import (
    PubSubMessageDto,
    PubSubNotificationDto,
)
from insightflow.application.services.gmail_monitoring_worker import (
    GmailMonitoringWorker,
)


class _StubProcessor:
    def __init__(self, *, result: bool = True) -> None:
        self.result = result
        self.processed: list[PubSubNotificationDto] = []
        self.errors: list[tuple[str, str]] = []

    def process(self, notification: PubSubNotificationDto) -> bool:
        self.processed.append(notification)
        return self.result

    def record_worker_error(self, account_id: str, message: str) -> None:
        self.errors.append((account_id, message))


class _StubWatchLifecycle:
    def __init__(self) -> None:
        self.renew_calls = 0

    def renew_if_needed(self, *, account_id: str, margin_hours: float) -> None:
        self.renew_calls += 1


def _valid_notification_bytes() -> bytes:
    return b'{"emailAddress": "user@example.com", "historyId": "100"}'


def _build_worker(
    subscriber: FakePubSubSubscriber,
    processor: _StubProcessor,
    watch_lifecycle: _StubWatchLifecycle,
    *,
    parse: Callable[[bytes], PubSubNotificationDto | None] | None = None,
) -> GmailMonitoringWorker:
    def default_parse(data: bytes) -> PubSubNotificationDto | None:
        import json

        payload = json.loads(data)
        return PubSubNotificationDto(
            email_address=payload["emailAddress"], history_id=payload["historyId"]
        )

    return GmailMonitoringWorker(
        account_id="user@example.com",
        subscriber=subscriber,
        processor=processor,  # type: ignore[arg-type]
        watch_lifecycle=watch_lifecycle,  # type: ignore[arg-type]
        parse_notification=parse or default_parse,
        pull_max_messages=10,
        idle_poll_seconds=0.05,
        watch_renewal_margin_hours=24.0,
    )


def _wait_until(predicate: Callable[[], bool], *, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def test_successful_processing_acknowledges() -> None:
    subscriber = FakePubSubSubscriber()
    subscriber.enqueue(
        PubSubMessageDto(ack_id="ack-1", data=_valid_notification_bytes())
    )
    processor = _StubProcessor(result=True)
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)

    worker.start()
    try:
        assert _wait_until(lambda: "ack-1" in subscriber.acknowledged)
        assert len(processor.processed) == 1
    finally:
        worker.stop()


def test_failed_processing_does_not_acknowledge() -> None:
    subscriber = FakePubSubSubscriber()
    subscriber.enqueue(
        PubSubMessageDto(ack_id="ack-1", data=_valid_notification_bytes())
    )
    processor = _StubProcessor(result=False)
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)

    worker.start()
    try:
        assert _wait_until(lambda: len(processor.processed) >= 1)
        time.sleep(0.1)
        assert subscriber.acknowledged == []
    finally:
        worker.stop()


def test_malformed_notification_is_acknowledged_to_avoid_poison_loop() -> None:
    subscriber = FakePubSubSubscriber()
    subscriber.enqueue(PubSubMessageDto(ack_id="ack-bad", data=b"not json"))
    processor = _StubProcessor(result=True)
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)

    worker.start()
    try:
        assert _wait_until(lambda: "ack-bad" in subscriber.acknowledged)
        assert processor.processed == []
    finally:
        worker.stop()


def test_pull_failure_does_not_crash_worker_and_retries() -> None:
    subscriber = FakePubSubSubscriber()
    subscriber.raise_on_pull = RuntimeError("transient network error")
    processor = _StubProcessor()
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)

    worker.start()
    try:
        assert _wait_until(lambda: subscriber.pull_calls >= 2)
        assert worker.is_running
    finally:
        worker.stop()


def test_watch_renewal_checked_each_cycle() -> None:
    subscriber = FakePubSubSubscriber()
    processor = _StubProcessor()
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)

    worker.start()
    try:
        assert _wait_until(lambda: watch_lifecycle.renew_calls >= 1)
    finally:
        worker.stop()


def test_stop_joins_cleanly_and_worker_is_no_longer_running() -> None:
    subscriber = FakePubSubSubscriber()
    processor = _StubProcessor()
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)

    worker.start()
    assert _wait_until(lambda: worker.is_running)
    worker.stop(join_timeout_seconds=2.0)

    assert worker.is_running is False


def test_start_does_not_block_the_calling_thread() -> None:
    """Regression guard for UI-thread isolation: start() must return quickly
    even while the subscriber pull is slow (a stand-in for a blocking Qt
    call site never freezing while monitoring runs)."""

    class SlowSubscriber(FakePubSubSubscriber):
        def pull(self, *, max_messages: int) -> list[PubSubMessageDto]:
            time.sleep(0.2)
            return super().pull(max_messages=max_messages)

    subscriber = SlowSubscriber()
    processor = _StubProcessor()
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)

    started_at = time.monotonic()
    worker.start()
    elapsed = time.monotonic() - started_at

    try:
        assert elapsed < 0.1
    finally:
        worker.stop()


def test_double_start_is_a_noop() -> None:
    subscriber = FakePubSubSubscriber()
    processor = _StubProcessor()
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)

    worker.start()
    first_thread = worker._thread
    worker.start()
    try:
        assert worker._thread is first_thread
    finally:
        worker.stop()


@pytest.mark.parametrize("stop_calls", [1, 2])
def test_stop_is_safe_to_call_multiple_times(stop_calls: int) -> None:
    subscriber = FakePubSubSubscriber()
    processor = _StubProcessor()
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)
    worker.start()
    for _ in range(stop_calls):
        worker.stop(join_timeout_seconds=2.0)
    assert worker.is_running is False


def test_stop_with_zero_timeout_does_not_block_even_mid_pull() -> None:
    """Regression guard for the shutdown-hang fix: closing the app calls
    stop(join_timeout_seconds=0) synchronously on the Qt GUI thread, so it
    must return near-instantly even if the worker thread is currently
    blocked inside a slow Google API call. No unsafe thread termination is
    used — the background thread is simply abandoned (it is a daemon
    thread, so it cannot block process exit) and stop_event.set() remains
    the only shutdown signal sent to it."""

    class SlowSubscriber(FakePubSubSubscriber):
        def pull(self, *, max_messages: int) -> list[PubSubMessageDto]:
            time.sleep(1.0)
            return super().pull(max_messages=max_messages)

    subscriber = SlowSubscriber()
    processor = _StubProcessor()
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)

    worker.start()
    assert _wait_until(lambda: subscriber.pull_calls >= 1, timeout=1.0)

    started_at = time.monotonic()
    stopped = worker.stop(join_timeout_seconds=0)
    elapsed = time.monotonic() - started_at

    assert elapsed < 0.1
    assert worker._stop_event.is_set()
    # The background thread is still inside the slow pull() call, so it
    # cannot be confirmed stopped yet — stop() must say so honestly rather
    # than pretending, and must not have blocked waiting to find out.
    assert stopped is False

    # Let the slow pull() finish and the thread exit naturally, so it
    # doesn't leak into other tests' thread-count expectations.
    assert _wait_until(lambda: not worker.is_running, timeout=2.0)


def test_pull_failure_records_worker_error_without_leaking_details() -> None:
    subscriber = FakePubSubSubscriber()
    subscriber.raise_on_pull = RuntimeError("token=super-secret-value-should-not-leak")
    processor = _StubProcessor()
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)

    worker.start()
    try:
        assert _wait_until(lambda: len(processor.errors) >= 1)
        account_id, message = processor.errors[0]
        assert account_id == "user@example.com"
        assert "RuntimeError" in message
        assert "super-secret-value-should-not-leak" not in message
        assert worker.is_running
    finally:
        worker.stop()


def test_acknowledge_failure_records_worker_error_without_leaking_details() -> None:
    subscriber = FakePubSubSubscriber()
    subscriber.enqueue(
        PubSubMessageDto(ack_id="ack-1", data=_valid_notification_bytes())
    )
    subscriber.raise_on_ack = RuntimeError("token=super-secret-value-should-not-leak")
    processor = _StubProcessor(result=True)
    watch_lifecycle = _StubWatchLifecycle()
    worker = _build_worker(subscriber, processor, watch_lifecycle)

    worker.start()
    try:
        assert _wait_until(lambda: len(processor.errors) >= 1)
        account_id, message = processor.errors[0]
        assert account_id == "user@example.com"
        assert "RuntimeError" in message
        assert "super-secret-value-should-not-leak" not in message
        assert worker.is_running
    finally:
        worker.stop()
