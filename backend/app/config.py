import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://deepface:deepface_password@mysql:3306/deepface?charset=utf8mb4",
)
DATABASE_SSL = os.getenv("DATABASE_SSL", "false").lower() in {"1", "true", "yes", "require"}
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "deepface-media")

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "face_embeddings")
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "512"))
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.45"))

PUBLIC_API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", "http://localhost:18000")
