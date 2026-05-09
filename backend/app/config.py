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
FAS_BBOX_PAD_RATIO = float(os.getenv("FAS_BBOX_PAD_RATIO", "0.15"))

PUBLIC_API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", "http://localhost:18000")

# Admin auth (for Admin UI + protected endpoints).
ADMIN_AUTH_SECRET = os.getenv("ADMIN_AUTH_SECRET", "dev-secret-change-me")
ADMIN_TOKEN_TTL_SECONDS = int(os.getenv("ADMIN_TOKEN_TTL_SECONDS", "86400"))

# Cache (multi-layer)
CACHE_REDIS_ENABLED = os.getenv("CACHE_REDIS_ENABLED", "true").lower() in {"1", "true", "yes"}
CACHE_L1_MAX_ENTRIES = int(os.getenv("CACHE_L1_MAX_ENTRIES", "512"))
# Cache TTLs should be larger than typical request latency, otherwise entries may expire
# before you can observe or benefit from them (e.g. access logs payload can be large).
CACHE_EMPLOYEES_TTL_SECONDS = int(os.getenv("CACHE_EMPLOYEES_TTL_SECONDS", "60"))
CACHE_LOGS_TTL_SECONDS = int(os.getenv("CACHE_LOGS_TTL_SECONDS", "60"))
# Optional: cache verify result by image hash (seconds). Keep low to avoid replay risks.
CACHE_VERIFY_TTL_SECONDS = int(os.getenv("CACHE_VERIFY_TTL_SECONDS", "0"))

# Quality gates (heuristic rejects) to reduce false accepts.
# All brightness thresholds use grayscale mean in range [0..255].
QUALITY_MIN_FRAME_BRIGHTNESS = float(os.getenv("QUALITY_MIN_FRAME_BRIGHTNESS", "35"))
QUALITY_MIN_FACE_BRIGHTNESS = float(os.getenv("QUALITY_MIN_FACE_BRIGHTNESS", "45"))
# Reject if face bbox occupies too much of the frame (too close to camera).
# Defaults tuned for approx 40–80cm (needs per-camera calibration).
QUALITY_MAX_FACE_AREA_RATIO = float(os.getenv("QUALITY_MAX_FACE_AREA_RATIO", "0.8"))
# Optional: reject if face bbox is too small (too far from camera).
QUALITY_MIN_FACE_AREA_RATIO = float(os.getenv("QUALITY_MIN_FACE_AREA_RATIO", "0.047"))
# Distance approximation using bbox height ratio (more stable than area ratio across crops).
# Tune these to map to your 50–100cm constraint per camera FOV/resolution.
QUALITY_MIN_FACE_HEIGHT_RATIO = float(os.getenv("QUALITY_MIN_FACE_HEIGHT_RATIO", "0.18"))
QUALITY_MAX_FACE_HEIGHT_RATIO = float(os.getenv("QUALITY_MAX_FACE_HEIGHT_RATIO", "0.56"))
# Reject if face is very bright while background is dark (typical screen/flash artifact).
QUALITY_BRIGHT_FACE_DARK_BG_FACE_MIN = float(os.getenv("QUALITY_BRIGHT_FACE_DARK_BG_FACE_MIN", "170"))
QUALITY_BRIGHT_FACE_DARK_BG_BG_MAX = float(os.getenv("QUALITY_BRIGHT_FACE_DARK_BG_BG_MAX", "55"))
QUALITY_BRIGHT_FACE_DARK_BG_RATIO_MIN = float(os.getenv("QUALITY_BRIGHT_FACE_DARK_BG_RATIO_MIN", "3.0"))

# Reject faces with too much roll (tilt). Degrees, absolute value.
QUALITY_MAX_FACE_ROLL_DEG = float(os.getenv("QUALITY_MAX_FACE_ROLL_DEG", "25"))

# Head pose thresholds (yaw/pitch) in degrees, absolute value.
# Used to "recognize face is turned" and optionally reject frames that are too angled.
QUALITY_MAX_FACE_YAW_DEG = float(os.getenv("QUALITY_MAX_FACE_YAW_DEG", "35"))
QUALITY_MAX_FACE_PITCH_DEG = float(os.getenv("QUALITY_MAX_FACE_PITCH_DEG", "30"))
QUALITY_ENFORCE_POSE_GATE = os.getenv("QUALITY_ENFORCE_POSE_GATE", "false").lower() in {"1", "true", "yes"}

# Reject if face is too blurry (variance of Laplacian on face crop).
QUALITY_MIN_FACE_SHARPNESS = float(os.getenv("QUALITY_MIN_FACE_SHARPNESS", "60"))

# Reject if detector confidence is too low (reduces false accepts on bad frames).
DETECTOR_MIN_SCORE = float(os.getenv("DETECTOR_MIN_SCORE", "0.5"))
