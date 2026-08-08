"""Correlation ID behavior tests."""

from __future__ import annotations

from insightflow.shared.correlation import (
    clear_correlation_id,
    correlation_context,
    create_correlation_id,
    get_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)


def test_create_and_retrieve_correlation_id() -> None:
    clear_correlation_id()
    assert get_correlation_id() is None
    created = create_correlation_id()
    token = set_correlation_id(created)
    try:
        assert get_correlation_id() == created
        assert len(created) == 32
    finally:
        reset_correlation_id(token)
    assert get_correlation_id() is None


def test_nested_correlation_context() -> None:
    clear_correlation_id()
    with correlation_context("outer") as outer:
        assert outer == "outer"
        assert get_correlation_id() == "outer"
        with correlation_context("inner") as inner:
            assert inner == "inner"
            assert get_correlation_id() == "inner"
        assert get_correlation_id() == "outer"
    assert get_correlation_id() is None


def test_correlation_context_generates_id_when_omitted() -> None:
    clear_correlation_id()
    with correlation_context() as generated:
        assert generated
        assert get_correlation_id() == generated
    assert get_correlation_id() is None
