import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api.access import router as access_router
from app.api.employees import router as employees_router
from app.api.logs import router as logs_router
from app.db import init_db
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


@app.on_event("startup")
def startup() -> None:
	init_db()
	init_bucket()
	init_collection()


@app.get("/api/files/{object_key:path}")
def read_file(object_key: str) -> Response:
	return Response(content=read_bytes(object_key), media_type="image/jpeg")


@app.get("/favicon.ico")
def favicon() -> Response:
	return Response(status_code=204)
