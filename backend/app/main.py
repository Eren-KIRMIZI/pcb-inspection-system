from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .errors import register_error_handlers
from .logging_config import configure_logging
from .middleware import register_middleware
from .routers import history, inspections, references, system, uploads
from .schemas import ErrorResponse, HealthResponse
from .services.history import init_db

configure_logging()

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    responses={
        400: {"description": "Ortak hata şeması", "model": ErrorResponse},
        404: {"description": "Kaynak bulunamadı", "model": ErrorResponse},
        422: {"description": "Doğrulama hatası", "model": ErrorResponse},
        500: {"description": "Sunucu hatası", "model": ErrorResponse},
    },
)

register_middleware(app)
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.data_dir.mkdir(parents=True, exist_ok=True)
init_db()
app.mount("/media", StaticFiles(directory=settings.data_dir), name="media")

app.include_router(uploads.router, prefix=settings.api_prefix)
app.include_router(inspections.router, prefix=settings.api_prefix)
app.include_router(references.router, prefix=settings.api_prefix)
app.include_router(history.router, prefix=settings.api_prefix)
app.include_router(system.router, prefix=settings.api_prefix)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name)
