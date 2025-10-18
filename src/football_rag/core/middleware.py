"""
FastAPI middleware for basic observability (request_id + latency).
Why: minimal tracing without extra deps; enables /metrics integration later.
"""

import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .logging import get_logger
from .metrics import metrics

_LOG = get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            metrics.increment_requests()
            metrics.record_latency(duration_ms)
            status = getattr(response, "status_code", "NA") if response else "ERROR"
            _LOG.info(
                f"path={request.url.path} method={request.method} "
                f"status={status} "
                f"duration_ms={duration_ms} request_id={request_id}"
            )
            if response:
                try:
                    response.headers["X-Request-ID"] = request_id
                except Exception:
                    pass  # keep middleware robust
