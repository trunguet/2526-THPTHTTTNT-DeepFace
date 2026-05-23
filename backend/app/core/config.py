from dataclasses import dataclass, field
from os import getenv


def _get_csv(name: str, default: str) -> list[str]:
    value = getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_env: str = getenv("APP_ENV", "dev")
    database_url: str = getenv(
        "DATABASE_URL",
        "postgresql://deepface:deepface@localhost:5432/deepface_access",
    )
    redis_url: str = getenv("REDIS_URL", "redis://localhost:6379/0")
    backend_cors_origins: list[str] = field(
        default_factory=lambda: _get_csv(
            "BACKEND_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:8080,http://127.0.0.1:8080",
        )
    )
    auth_secret_key: str = getenv(
        "AUTH_SECRET_KEY",
        "deepface-access-dev-secret",
    )
    access_token_expire_minutes: int = int(
        getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )
    max_processing_access_logs_per_camera: int = int(
        getenv("MAX_PROCESSING_ACCESS_LOGS_PER_CAMERA", "3")
    )

settings = Settings()
