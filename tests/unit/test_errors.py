from __future__ import annotations

from osbot.connector import (
    AppError,
    AuthError,
    ErrorCategory,
    NetworkError,
    RateLimitError,
    StructuralError,
    classify,
)


def test_classify_network() -> None:
    err = classify(RuntimeError("connection timeout"))
    assert isinstance(err, NetworkError)
    assert err.retryable
    assert err.category is ErrorCategory.NETWORK


def test_classify_rate_limit() -> None:
    err = classify(RuntimeError("429 Too Many Requests"))
    assert isinstance(err, RateLimitError)
    assert err.retryable


def test_classify_structural() -> None:
    err = classify(RuntimeError("insufficient margin for this order"))
    assert isinstance(err, StructuralError)
    assert not err.retryable


def test_classify_auth() -> None:
    err = classify(RuntimeError("invalid signature"))
    assert isinstance(err, AuthError)
    assert not err.retryable


def test_classify_passthrough_apperror() -> None:
    original = NetworkError("boom")
    assert classify(original) is original


def test_unknown_falls_back_to_apperror() -> None:
    err = classify(RuntimeError("something weird"))
    assert isinstance(err, AppError)
    assert err.category is ErrorCategory.UNKNOWN
