"""Tüm API hata cevapları için ortak şema ve exception handler'lar."""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .logging_config import get_logger, request_id_ctx

logger = get_logger(__name__)

_STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    503: "service_unavailable",
}


class ServiceError(Exception):
    """Servis katmanından gelen, kullanıcıya anlamlı biçimde gösterilebilir hata."""

    code = "service_error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ModelUnavailableError(ServiceError):
    code = "model_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class ImageReadError(ServiceError):
    code = "image_unreadable"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


def _payload(code: str, detail: str) -> dict[str, str | None]:
    return {
        "error": code,
        "detail": detail,
        "request_id": request_id_ctx.get(),
    }


def _headers() -> dict[str, str]:
    request_id = request_id_ctx.get()
    return {"X-Request-ID": request_id} if request_id else {}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "http_error")
        detail = str(exc.detail)
        logger.info(
            "İstek reddedildi",
            extra={
                "event": "api_error",
                "status_code": exc.status_code,
                "error_code": code,
                "path": request.url.path,
                "method": request.method,
                "detail": detail,
            },
        )
        headers = dict(exc.headers or {})
        headers.update(_headers())
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(code, detail),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        location = ".".join(str(part) for part in first.get("loc", []))
        message = str(first.get("msg", "Geçersiz istek")).strip()
        detail = f"Geçersiz istek alanı: {location} — {message}" if location else message
        logger.info(
            "İstek doğrulanamadı",
            extra={
                "event": "validation_error",
                "path": request.url.path,
                "method": request.method,
                "error_count": len(errors),
                "detail": detail,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_payload("validation_error", detail),
            headers=_headers(),
        )

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        logger.warning(
            "Servis hatası",
            extra={
                "event": "service_error",
                "error_code": exc.code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
                "detail": exc.detail,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.detail),
            headers=_headers(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Beklenmeyen sunucu hatası",
            extra={
                "event": "unhandled_error",
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload(
                "internal_error", "Beklenmeyen bir sunucu hatası oluştu."
            ),
            headers=_headers(),
        )
