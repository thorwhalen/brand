"""HTTP helpers shared by network scorers: retry on throttling, and rate limiting."""

import threading
import time

import requests

DEFAULT_RETRY_ON = (429, 503)
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF = 1.0  # seconds; doubled on each retry
MAX_RETRY_AFTER = 30.0  # never sleep longer than this on a Retry-After header


def _retry_delay(response, attempt: int, *, backoff: float) -> float:
    """Seconds to wait before retry number *attempt* (0-based).

    >>> class R: headers = {'Retry-After': '2'}
    >>> _retry_delay(R(), 0, backoff=1.0)
    2.0
    >>> class R: headers = {}
    >>> _retry_delay(R(), 2, backoff=1.0)
    4.0
    """
    try:
        return min(float(getattr(response, "headers", {})["Retry-After"]), MAX_RETRY_AFTER)
    except (AttributeError, KeyError, TypeError, ValueError):
        return backoff * 2**attempt


def request_with_retry(
    method: str,
    url: str,
    *,
    retry_on=DEFAULT_RETRY_ON,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    **kwargs,
) -> requests.Response:
    """``requests.request`` that retries throttled responses with backoff.

    Waits for ``Retry-After`` when the server sends one, else exponentially.
    After *max_retries* the last response is returned, so callers still see
    the status code.  Network exceptions propagate.
    """
    for attempt in range(max_retries + 1):
        r = getattr(requests, method.lower())(url, **kwargs)
        if r.status_code not in retry_on or attempt == max_retries:
            return r
        time.sleep(_retry_delay(r, attempt, backoff=backoff))
    return r  # pragma: no cover


class RateLimiter:
    """Thread-safe limiter spacing calls at least ``1 / rate`` seconds apart.

    >>> RateLimiter(None).wait()  # no limit: returns at once
    """

    def __init__(self, rate: float | None):
        self.interval = 1.0 / rate if rate else 0.0
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        if not self.interval:
            return
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next)
            self._next = start + self.interval
        if start > now:
            time.sleep(start - now)
