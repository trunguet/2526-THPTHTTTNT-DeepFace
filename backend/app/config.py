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

_APP_DIR = os.path.dirname(__file__)
_REPO_LAYOUT_DIR = os.path.abspath(os.path.join(_APP_DIR, "..", ".."))
_CONTAINER_LAYOUT_DIR = os.path.abspath(os.path.join(_APP_DIR, ".."))
BASE_DIR = _REPO_LAYOUT_DIR if os.path.isdir(os.path.join(_REPO_LAYOUT_DIR, "models")) else _CONTAINER_LAYOUT_DIR
MODELS_DIR = os.getenv("MODELS_DIR", os.path.join(BASE_DIR, "models"))
YOLO_FACE_MODEL = os.getenv("YOLO_FACE_MODEL", os.path.join(MODELS_DIR, "detection", "yolov8n-face.pt"))
MINIFAS_CORE_DIR = os.getenv(
    "MINIFAS_CORE_DIR",
    os.path.join(MODELS_DIR, "anti_spoofing", "minifas_core"),
)
FAS_MODEL_DIR = os.getenv(
    "FAS_MODEL_DIR",
    os.path.join(MINIFAS_CORE_DIR, "resources", "anti_spoof_models"),
)
ARCFACE_WEIGHTS_PATH = os.getenv(
    "ARCFACE_WEIGHTS_PATH",
    os.path.join(MODELS_DIR, "extraction", "arcface_weights.h5"),
)
FACE_DEVICE = os.getenv("FACE_DEVICE", "cpu")
ANTISPOOF_DEVICE_ID = int(os.getenv("ANTISPOOF_DEVICE_ID", "0"))
ANTISPOOF_REAL_THRESHOLD = float(os.getenv("ANTISPOOF_REAL_THRESHOLD", "0.5"))

PUBLIC_API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", "http://localhost:18000")
