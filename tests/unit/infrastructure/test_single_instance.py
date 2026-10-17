"""SingleInstanceLock tests (Phase 13)."""

from __future__ import annotations

from pathlib import Path

import pytest

from insightflow.infrastructure.process.single_instance import (
    SingleInstanceError,
    SingleInstanceLock,
)


def test_first_lock_acquires_successfully(tmp_path: Path) -> None:
    lock = SingleInstanceLock(tmp_path / "agent.lock")
    try:
        assert lock.acquire() is True
    finally:
        lock.release()


def test_second_acquisition_fails_while_first_holds_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / "agent.lock"
    first = SingleInstanceLock(lock_path)
    second = SingleInstanceLock(lock_path)
    assert first.acquire() is True
    try:
        assert second.acquire() is False
    finally:
        first.release()


def test_release_allows_a_subsequent_acquire(tmp_path: Path) -> None:
    lock_path = tmp_path / "agent.lock"
    first = SingleInstanceLock(lock_path)
    assert first.acquire() is True
    first.release()

    second = SingleInstanceLock(lock_path)
    try:
        assert second.acquire() is True
    finally:
        second.release()


def test_context_manager_raises_single_instance_error_when_already_held(
    tmp_path: Path,
) -> None:
    lock_path = tmp_path / "agent.lock"
    first = SingleInstanceLock(lock_path)
    assert first.acquire() is True
    try:
        with pytest.raises(SingleInstanceError), SingleInstanceLock(lock_path):
            pass
    finally:
        first.release()


def test_context_manager_releases_on_normal_exit(tmp_path: Path) -> None:
    lock_path = tmp_path / "agent.lock"
    with SingleInstanceLock(lock_path):
        blocked = SingleInstanceLock(lock_path)
        assert blocked.acquire() is False

    # Released automatically on __exit__ — a fresh acquire now succeeds.
    after = SingleInstanceLock(lock_path)
    try:
        assert after.acquire() is True
    finally:
        after.release()


def test_double_release_is_a_safe_noop(tmp_path: Path) -> None:
    lock = SingleInstanceLock(tmp_path / "agent.lock")
    assert lock.acquire() is True
    lock.release()
    lock.release()  # must not raise
