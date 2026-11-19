from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import inspections, references, uploads
from .schemas import HealthResponse

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.data_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.data_dir), name="media")

app.include_router(uploads.router, prefix=settings.api_prefix)
app.include_router(inspections.router, prefix=settings.api_prefix)
app.include_router(references.router, prefix=settings.api_prefix)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name)
