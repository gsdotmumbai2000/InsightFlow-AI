"""AIWorker lifecycle tests (Phase 11)."""

from __future__ import annotations

import queue
import time
from collections.abc import Callable

from insightflow.application.dto.ai import AIAnalysisJob
from insightflow.application.services.ai_worker import AIWorker
from insightflow.application.services.ai_worker_handle import AIWorkerHandle


class _RecordingAnalyze:
    def __init__(self, *, fail_on: set[str] | None = None) -> None:
        self.calls: list[AIAnalysisJob] = []
        self._fail_on = fail_on or set()

    def execute(self, job: AIAnalysisJob) -> None:
        self.calls.append(job)
        if job.event_id in self._fail_on:
            raise RuntimeError("boom")


def _wait_for(predicate: Callable[[], bool], *, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition not met within timeout")


def test_worker_processes_queued_jobs() -> None:
    job_queue: queue.Queue[AIAnalysisJob] = queue.Queue()
    analyze = _RecordingAnalyze()
    worker = AIWorker(job_queue=job_queue, analyze=analyze, idle_poll_seconds=0.05)
    worker.start()
    try:
        job_queue.put_nowait(AIAnalysisJob(event_id="e1"))
        job_queue.put_nowait(AIAnalysisJob(event_id="e2"))
        _wait_for(lambda: len(analyze.calls) == 2)
        assert {job.event_id for job in analyze.calls} == {"e1", "e2"}
    finally:
        worker.stop()


def test_worker_survives_job_exceptions() -> None:
    job_queue: queue.Queue[AIAnalysisJob] = queue.Queue()
    analyze = _RecordingAnalyze(fail_on={"bad"})
    worker = AIWorker(job_queue=job_queue, analyze=analyze, idle_poll_seconds=0.05)
    worker.start()
    try:
        job_queue.put_nowait(AIAnalysisJob(event_id="bad"))
        job_queue.put_nowait(AIAnalysisJob(event_id="good"))
        _wait_for(lambda: len(analyze.calls) == 2)
        assert worker.is_running
    finally:
        worker.stop()


def test_worker_picks_up_pending_jobs_when_queue_is_empty() -> None:
    """Jobs persisted by another process (Desktop) are found by the scan."""
    job_queue: queue.Queue[AIAnalysisJob] = queue.Queue()
    analyze = _RecordingAnalyze()
    pending = [AIAnalysisJob(event_id="from-desktop")]

    def _pending_jobs() -> list[AIAnalysisJob]:
        jobs = list(pending)
        pending.clear()  # analysis moves the event out of AI_PROCESSING
        return jobs

    worker = AIWorker(
        job_queue=job_queue,
        analyze=analyze,
        idle_poll_seconds=0.05,
        pending_jobs=_pending_jobs,
        pending_scan_seconds=0.05,
    )
    worker.start()
    try:
        _wait_for(lambda: len(analyze.calls) == 1)
        assert analyze.calls[0].event_id == "from-desktop"
    finally:
        worker.stop()


def test_worker_drops_jobs_should_run_rejects() -> None:
    job_queue: queue.Queue[AIAnalysisJob] = queue.Queue()
    analyze = _RecordingAnalyze()
    worker = AIWorker(
        job_queue=job_queue,
        analyze=analyze,
        idle_poll_seconds=0.05,
        should_run=lambda job: job.manual,
    )
    worker.start()
    try:
        job_queue.put_nowait(AIAnalysisJob(event_id="automatic"))
        job_queue.put_nowait(AIAnalysisJob(event_id="clicked", manual=True))
        _wait_for(lambda: len(analyze.calls) == 1)
        time.sleep(0.1)
        assert [job.event_id for job in analyze.calls] == ["clicked"]
        assert job_queue.unfinished_tasks == 0  # the dropped job is not left over
    finally:
        worker.stop()


def test_worker_reports_failed_jobs() -> None:
    job_queue: queue.Queue[AIAnalysisJob] = queue.Queue()
    analyze = _RecordingAnalyze(fail_on={"bad"})
    failed: list[str] = []
    worker = AIWorker(
        job_queue=job_queue,
        analyze=analyze,
        idle_poll_seconds=0.05,
        on_job_failed=lambda job: failed.append(job.event_id),
    )
    worker.start()
    try:
        job_queue.put_nowait(AIAnalysisJob(event_id="bad"))
        job_queue.put_nowait(AIAnalysisJob(event_id="good"))
        _wait_for(lambda: len(analyze.calls) == 2)
        assert failed == ["bad"]
    finally:
        worker.stop()


def test_worker_stop_is_non_blocking_and_idempotent() -> None:
    job_queue: queue.Queue[AIAnalysisJob] = queue.Queue()
    analyze = _RecordingAnalyze()
    worker = AIWorker(job_queue=job_queue, analyze=analyze, idle_poll_seconds=0.05)
    worker.start()
    assert worker.is_running
    stopped = worker.stop(join_timeout_seconds=1.0)
    assert stopped
    assert not worker.is_running
    # Calling stop again with no worker running must be a safe no-op.
    assert worker.stop(join_timeout_seconds=0) is True


def test_worker_handle_stops_the_set_worker() -> None:
    job_queue: queue.Queue[AIAnalysisJob] = queue.Queue()
    analyze = _RecordingAnalyze()
    worker = AIWorker(job_queue=job_queue, analyze=analyze, idle_poll_seconds=0.05)
    handle = AIWorkerHandle()
    worker.start()
    handle.set(worker)
    assert handle.is_running
    handle.stop(join_timeout_seconds=1.0)
    assert not handle.is_running


def test_worker_handle_stop_without_a_worker_is_a_noop() -> None:
    handle = AIWorkerHandle()
    handle.stop(join_timeout_seconds=0)
    assert not handle.is_running
