"""Background AI-analysis worker (Phase 11).

Runs on a plain ``threading.Thread`` daemon, never Qt — mirrors
``GmailMonitoringWorker`` (Phase 10). One bounded queue, one worker: both
automatic dispatch and manual re-analysis enqueue an ``AIAnalysisJob`` and
this worker is the single place ``AnalyzeIntelligenceEventUseCase`` actually
runs. Exceptions from a single job are caught and logged so the loop never
dies and one bad job never blocks the rest of the queue.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable, Sequence
from typing import Protocol

from insightflow.application.dto.ai import AIAnalysisJob

logger = logging.getLogger("insightflow.application.ai")

DEFAULT_IDLE_POLL_SECONDS = 1.0
DEFAULT_PENDING_SCAN_SECONDS = 5.0
DEFAULT_STOP_JOIN_TIMEOUT_SECONDS = 10.0


class AnalyzeJob(Protocol):
    """Narrow view of ``AnalyzeIntelligenceEventUseCase`` the worker needs."""

    def execute(self, job: AIAnalysisJob) -> object: ...


class AIWorker:
    """Owns one background thread draining the AI analysis job queue."""

    def __init__(
        self,
        *,
        job_queue: queue.Queue[AIAnalysisJob],
        analyze: AnalyzeJob,
        idle_poll_seconds: float = DEFAULT_IDLE_POLL_SECONDS,
        pending_jobs: Callable[[], Sequence[AIAnalysisJob]] | None = None,
        on_job_failed: Callable[[AIAnalysisJob], None] | None = None,
        pending_scan_seconds: float = DEFAULT_PENDING_SCAN_SECONDS,
        should_run: Callable[[AIAnalysisJob], bool] | None = None,
    ) -> None:
        """``pending_jobs`` (Phase 13) lets the Agent's worker pick up work
        persisted by another process: it is called only while the queue is
        empty (so nothing is queued or in flight here), at most every
        ``pending_scan_seconds``. ``on_job_failed`` runs when a job raises,
        so its event leaves AI_PROCESSING instead of being re-found forever.
        ``should_run`` is asked right before each job's AI call; a job it
        rejects (e.g. automatic analysis turned off in Settings, or the
        event's analysis cancelled) is dropped without calling the AI.
        """
        self._queue = job_queue
        self._analyze = analyze
        self._idle_poll_seconds = idle_poll_seconds
        self._pending_jobs = pending_jobs
        self._on_job_failed = on_job_failed
        self._pending_scan_seconds = pending_scan_seconds
        self._should_run = should_run
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="ai-analysis-worker", daemon=True
        )
        self._thread.start()
        logger.info("AI worker started")

    def stop(
        self,
        *,
        join_timeout_seconds: float | None = DEFAULT_STOP_JOIN_TIMEOUT_SECONDS,
    ) -> bool:
        """Request the worker to stop.

        Pass ``0``/``None`` for a non-blocking stop (e.g. on GUI thread
        shutdown) — the worker thread is a daemon and can never block
        process exit either way.
        """
        self._stop_event.set()
        thread = self._thread
        if thread is not None and join_timeout_seconds:
            thread.join(timeout=join_timeout_seconds)
        still_alive = thread is not None and thread.is_alive()
        if not still_alive:
            self._thread = None
        logger.info("AI worker stop requested stopped=%s", not still_alive)
        return not still_alive

    def _run(self) -> None:
        next_scan = time.monotonic()  # scan immediately: recover after restart
        while not self._stop_event.is_set():
            if self._pending_jobs is not None and time.monotonic() >= next_scan:
                if self._queue.empty():
                    self._enqueue_pending()
                next_scan = time.monotonic() + self._pending_scan_seconds
            try:
                job = self._queue.get(timeout=self._idle_poll_seconds)
            except queue.Empty:
                continue
            try:
                if not self._wanted(job):
                    continue  # finally: still marks the queue item done
                self._analyze.execute(job)
            except Exception:
                logger.error(
                    "AI worker job failed event_id=%s", job.event_id, exc_info=True
                )
                self._mark_failed(job)
            finally:
                self._queue.task_done()

    def _wanted(self, job: AIAnalysisJob) -> bool:
        if self._should_run is None:
            return True
        try:
            wanted = self._should_run(job)
        except Exception:
            # Fail open, as before this check existed: a settings read error
            # must not silently drop analyses.
            logger.warning(
                "AI job check failed event_id=%s", job.event_id, exc_info=True
            )
            return True
        if not wanted:
            logger.info("AI job skipped event_id=%s", job.event_id)
        return wanted

    def _enqueue_pending(self) -> None:
        assert self._pending_jobs is not None
        try:
            jobs = self._pending_jobs()
        except Exception:
            logger.warning("AI pending-job scan failed", exc_info=True)
            return
        for job in jobs:
            try:
                self._queue.put_nowait(job)
            except queue.Full:
                break  # the rest are re-found by the next scan
        if jobs:
            logger.info("AI worker picked up pending jobs count=%s", len(jobs))

    def _mark_failed(self, job: AIAnalysisJob) -> None:
        if self._on_job_failed is None:
            return
        try:
            self._on_job_failed(job)
        except Exception:
            logger.warning(
                "AI worker could not mark job failed event_id=%s",
                job.event_id,
                exc_info=True,
            )
