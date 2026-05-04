import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://deepface:deepface_password@postgres:5432/deepface",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "deepface-media")

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "face_embeddings")
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "1024"))
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.82"))

PUBLIC_API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", "http://localhost:18000")
