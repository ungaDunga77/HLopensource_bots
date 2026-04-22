"""AppError hierarchy.

Derived from the hypersdk Rust pattern (`is_retryable()` on the error enum) and
Copy Trading Bot's typed error flow. Every error carries (retryable, category) so
the main loop can branch on transient vs structural vs auth without sniffing strings.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCategory(StrEnum):
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    STRUCTURAL = "structural"
    AUTH = "auth"
    UNKNOWN = "unknown"


class AppError(Exception):
    retryable: bool = False
    category: ErrorCategory = ErrorCategory.UNKNOWN

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause


class NetworkError(AppError):
    retryable = True
    category = ErrorCategory.NETWORK


class RateLimitError(AppError):
    retryable = True
    category = ErrorCategory.RATE_LIMIT


class StructuralError(AppError):
    """Margin too low, reduce-only violated, min-notional — do not retry, drop action."""

    retryable = False
    category = ErrorCategory.STRUCTURAL


class AuthError(AppError):
    """Signature/nonce/permission failures — halt and alert."""

    retryable = False
    category = ErrorCategory.AUTH


_STRUCTURAL_MARKERS = (
    "insufficient margin",
    "reduce only",
    "min notional",
    "invalid size",
)
_AUTH_MARKERS = ("signature", "unauthorized", "invalid nonce")
_RATE_MARKERS = ("rate limit", "too many requests", "429")
_NETWORK_MARKERS = ("timeout", "connection", "502", "503", "504")


def classify(err: BaseException) -> AppError:
    """Map an arbitrary exception/HL error string to the AppError hierarchy.

    M0: string-marker heuristic. M1 will add HL-code-based dispatch once the
    connector wraps the SDK and we know which codes the SDK surfaces.
    """
    if isinstance(err, AppError):
        return err
    msg = str(err).lower()
    if any(m in msg for m in _AUTH_MARKERS):
        return AuthError(str(err), cause=err)
    if any(m in msg for m in _STRUCTURAL_MARKERS):
        return StructuralError(str(err), cause=err)
    if any(m in msg for m in _RATE_MARKERS):
        return RateLimitError(str(err), cause=err)
    if any(m in msg for m in _NETWORK_MARKERS):
        return NetworkError(str(err), cause=err)
    return AppError(str(err), cause=err)
