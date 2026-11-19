"""İstek kimliği ve yapılandırılmış erişim log'u."""

from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from .logging_config import get_logger, request_id_ctx

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        token = request_id_ctx.set(request_id)
        started = perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "İstek tamamlandı",
                extra={
                    "event": "request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": int((perf_counter() - started) * 1000),
                    "client": request.client.host if request.client else None,
                },
            )
            return response
        finally:
            request_id_ctx.reset(token)


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestContextMiddleware)
