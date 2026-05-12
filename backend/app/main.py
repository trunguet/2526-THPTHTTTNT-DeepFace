import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api.access import router as access_router
from app.api.auth import router as auth_router
from app.api.cache_debug import router as cache_router
from app.api.db_debug import router as db_debug_router
from app.api.employees import router as employees_router
from app.api.logs import router as logs_router
from app.db import init_db
from app.ml.pipeline import get_face_pipeline
from app.runtime import env_bool, run_startup_step
from app.storage import init_bucket, read_bytes
from app.vector_store import init_collection


app = FastAPI(title="DeepFace Access API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(access_router)
app.include_router(auth_router)
app.include_router(cache_router)
app.include_router(db_debug_router)
app.include_router(employees_router)
app.include_router(logs_router)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def health() -> dict:
    return {"status": "ok"}


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/api/health")
def api_health_check() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
def startup() -> None:
    # In Kubernetes, external dependencies or model preloading can be slow.
    # Set STRICT_STARTUP=false to let the API start even if some init steps fail.
    strict_startup = env_bool("STRICT_STARTUP", True)
    init_external = env_bool("INIT_EXTERNAL_DEPENDENCIES", True)
    preload_models = env_bool("PRELOAD_MODELS", True)

    db_retries = 30 if strict_startup else 3
    external_retries = 20 if strict_startup else 3

    run_startup_step(
        "Startup init_db",
        lambda: init_db(retries=db_retries),
        strict=strict_startup,
    )

    if init_external:
        run_startup_step(
            "Startup init_bucket",
            lambda: init_bucket(retries=external_retries),
            strict=strict_startup,
        )
        run_startup_step(
            "Startup init_collection",
            lambda: init_collection(retries=external_retries),
            strict=strict_startup,
        )

    if preload_models:
        print("Preloading FaceRecognitionPipeline...", flush=True)
        models_loaded = run_startup_step(
            "Startup model preload",
            get_face_pipeline,
            strict=strict_startup,
        )
        if models_loaded:
            print("AI models preloaded.", flush=True)


@app.get("/api/files/{object_key:path}")
def read_file(object_key: str) -> Response:
    return Response(content=read_bytes(object_key), media_type="image/jpeg")


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)
