from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.access import router as access_router
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.cameras import router as cameras_router
from app.api.employees import router as employees_router
from app.api.logs import router as logs_router
from app.config.redis import check_redis_connection, get_redis_client
from app.core.config import settings
from app.db.health import check_database_connection
from app.db.session import SessionLocal


app = FastAPI(title="DeepFace Access Control API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(employees_router)
app.include_router(cameras_router)
app.include_router(logs_router)
app.include_router(access_router)


@app.get("/health", response_model=None)
def health_check():
    database_ok, database_error = check_database_connection()
    redis_ok, redis_error = check_redis_connection()

    if not database_ok or not redis_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "service": "backend",
                "environment": settings.app_env,
                "database": "ok" if database_ok else "error",
                "database_error": database_error,
                "redis": "ok" if redis_ok else "error",
                "redis_error": redis_error,
            },
        )

    return {
        "status": "ok",
        "service": "backend",
        "environment": settings.app_env,
        "database": "ok",
        "redis": "ok",
    }


@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def metrics() -> str:
    lines = [
        "# HELP deepface_backend_up Backend process health.",
        "# TYPE deepface_backend_up gauge",
        "deepface_backend_up 1",
    ]

    database_ok, _database_error = check_database_connection()
    redis_ok, _redis_error = check_redis_connection()
    lines.extend(
        [
            "# HELP deepface_database_up PostgreSQL connectivity from backend.",
            "# TYPE deepface_database_up gauge",
            f"deepface_database_up {1 if database_ok else 0}",
            "# HELP deepface_redis_up Redis connectivity from backend.",
            "# TYPE deepface_redis_up gauge",
            f"deepface_redis_up {1 if redis_ok else 0}",
        ]
    )

    if redis_ok:
        redis_client = get_redis_client()
        lines.append("# HELP deepface_queue_length Redis queue length.")
        lines.append("# TYPE deepface_queue_length gauge")
        for queue_name in ("embedding_jobs", "access_jobs"):
            lines.append(
                f'deepface_queue_length{{queue="{queue_name}"}} {redis_client.llen(queue_name)}'
            )

    if database_ok:
        try:
            with SessionLocal() as db:
                if inspect(db.get_bind()).has_table("access_logs"):
                    rows = db.execute(
                        text(
                            "SELECT status, COUNT(*) AS count FROM access_logs GROUP BY status"
                        )
                    )
                    lines.append("# HELP deepface_access_logs_total Access logs by status.")
                    lines.append("# TYPE deepface_access_logs_total gauge")
                    for row in rows:
                        lines.append(
                            f'deepface_access_logs_total{{status="{row.status}"}} {row.count}'
                        )
        except SQLAlchemyError:
            lines.append("# HELP deepface_access_logs_metric_error Access log metric collection error.")
            lines.append("# TYPE deepface_access_logs_metric_error gauge")
            lines.append("deepface_access_logs_metric_error 1")

    return "\n".join(lines) + "\n"
