import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

try:
	from ultralytics import YOLO
except Exception as exc:  # pragma: no cover - optional dependency
	YOLO = None
	_YOLO_IMPORT_ERROR = exc


# Ensure local model packages are importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
MINIFAS_CORE = os.path.join(MODELS_DIR, "anti_spoofing", "minifas_core")
if MINIFAS_CORE not in sys.path:
	sys.path.insert(0, MINIFAS_CORE)

try:
	from src.anti_spoof_predict import AntiSpoofPredict
except Exception as exc:  # pragma: no cover - optional dependency
	AntiSpoofPredict = None
	_ANTISPOOF_IMPORT_ERROR = exc

try:
	from models.extraction.arcface_wrapper import get_arcface_extractor
except Exception as exc:  # pragma: no cover - optional dependency
	get_arcface_extractor = None
	_ARCFACE_IMPORT_ERROR = exc


@dataclass
class DetectionResult:
	bbox_xyxy: Tuple[int, int, int, int]
	landmarks_5: Optional[np.ndarray]
	score: float


@dataclass
class AntiSpoofResult:
	is_real: bool
	confidence: float
	model_scores: Dict[str, Tuple[float, float]]


@dataclass
class MatchResult:
	employee_id: Optional[str]
	score: Optional[float]
	payload: Optional[Dict[str, Any]]


@dataclass
class PipelineResult:
	status: str
	reason: str
	employee_id: Optional[str]
	similarity: Optional[float]
	audit_object: Optional[str]
	payload: Optional[Dict[str, Any]] = None


class FaceDetector:
	def __init__(self, model_path: str, device: str = "cpu"):
		if YOLO is None:
			raise RuntimeError(f"YOLO import failed: {_YOLO_IMPORT_ERROR}")
		self.model = YOLO(model_path, task="pose")
		self.device = device

	def detect(self, image_bgr: np.ndarray) -> Optional[DetectionResult]:
		results = self.model(image_bgr, verbose=False)
		if not results or results[0].boxes is None or len(results[0].boxes) == 0:
			return None

		boxes = results[0].boxes.xyxy.cpu().numpy()
		scores = results[0].boxes.conf.cpu().numpy()
		keypoints = None
		if results[0].keypoints is not None:
			keypoints = results[0].keypoints.xy.cpu().numpy()

		best_idx = int(np.argmax(scores))
		x1, y1, x2, y2 = map(int, boxes[best_idx])
		landmarks = None
		if keypoints is not None and len(keypoints) > best_idx:
			lm = keypoints[best_idx]
			if lm.shape[0] >= 5:
				landmarks = lm[:5]

		return DetectionResult(
			bbox_xyxy=(x1, y1, x2, y2),
			landmarks_5=landmarks,
			score=float(scores[best_idx]),
		)


class FaceAligner:
	def __init__(self, output_size: Tuple[int, int] = (112, 112)):
		self.output_size = output_size
		self._target = np.array(
			[
				[38.2946, 51.6963],
				[73.5318, 51.5014],
				[56.0252, 71.7366],
				[41.5493, 92.3655],
				[70.7299, 92.2041],
			],
			dtype=np.float32,
		)

	def align(self, image_bgr: np.ndarray, landmarks_5: np.ndarray) -> np.ndarray:
		src = landmarks_5.astype(np.float32)
		dst = self._target.copy()
		transform, _ = cv2.estimateAffinePartial2D(src, dst, method=cv2.LMEDS)
		if transform is None:
			return self._fallback_crop(image_bgr, landmarks_5)
		return cv2.warpAffine(image_bgr, transform, self.output_size, flags=cv2.INTER_LINEAR)

	def _fallback_crop(self, image_bgr: np.ndarray, landmarks_5: np.ndarray) -> np.ndarray:
		x_min = int(np.min(landmarks_5[:, 0]))
		y_min = int(np.min(landmarks_5[:, 1]))
		x_max = int(np.max(landmarks_5[:, 0]))
		y_max = int(np.max(landmarks_5[:, 1]))
		pad = int(0.3 * max(x_max - x_min, y_max - y_min))
		h, w = image_bgr.shape[:2]
		x1 = max(0, x_min - pad)
		y1 = max(0, y_min - pad)
		x2 = min(w, x_max + pad)
		y2 = min(h, y_max + pad)
		crop = image_bgr[y1:y2, x1:x2]
		return cv2.resize(crop, self.output_size, interpolation=cv2.INTER_LINEAR)


class AntiSpoofing:
	def __init__(self, model_dir: str, device_id: int = 0):
		if AntiSpoofPredict is None:
			raise RuntimeError(f"AntiSpoofPredict import failed: {_ANTISPOOF_IMPORT_ERROR}")
		self.predictor = AntiSpoofPredict(device_id)
		self.model_dir = model_dir

	def predict(self, image_bgr: np.ndarray, bbox_xyxy: Tuple[int, int, int, int]) -> AntiSpoofResult:
		x1, y1, x2, y2 = bbox_xyxy
		fas_bbox = [x1, y1, x2 - x1, y2 - y1]

		model_files = [f for f in os.listdir(self.model_dir) if f.endswith(".pth")]
		if not model_files:
			raise RuntimeError(f"No anti-spoof models found in {self.model_dir}")

		prediction = np.zeros((1, 3), dtype=np.float32)
		scores: Dict[str, Tuple[float, float]] = {}

		for model_name in model_files:
			model_path = os.path.join(self.model_dir, model_name)
			self.predictor._load_model(model_path)
			result = self.predictor.predict(image_bgr, fas_bbox)
			prediction += result

			spoof_score = float(result[0][0])
			real_score = float(result[0][1])
			scores[model_name] = (real_score, spoof_score)

		label = int(np.argmax(prediction))
		confidence = float(prediction[0][label] / len(model_files))
		is_real = label == 1

		return AntiSpoofResult(is_real=is_real, confidence=confidence, model_scores=scores)


class ArcFaceEmbedder:
	def __init__(self, model_name: str = "ArcFace"):
		if get_arcface_extractor is None:
			raise RuntimeError(f"ArcFace import failed: {_ARCFACE_IMPORT_ERROR}")
		self.extractor = get_arcface_extractor(model_name=model_name)

	def embed(self, face_bgr: np.ndarray) -> np.ndarray:
		return self.extractor.extract_embedding(face_bgr)


class QdrantMatcher:
	def __init__(self, host: str, port: int, collection: str, threshold: float = 0.45):
		try:
			from qdrant_client import QdrantClient
		except Exception as exc:  # pragma: no cover - optional dependency
			raise RuntimeError(f"qdrant-client import failed: {exc}")

		self.client = QdrantClient(host=host, port=port)
		self.collection = collection
		self.threshold = threshold

	def match(self, embedding: np.ndarray) -> MatchResult:
		search = self.client.search(
			collection_name=self.collection,
			query_vector=embedding.tolist(),
			limit=1,
		)

		if not search:
			return MatchResult(employee_id=None, score=None, payload=None)

		top = search[0]
		score = float(top.score)
		if score < self.threshold:
			return MatchResult(employee_id=None, score=score, payload=top.payload)

		employee_id = None
		if top.payload and "employee_id" in top.payload:
			employee_id = str(top.payload["employee_id"])

		return MatchResult(employee_id=employee_id, score=score, payload=top.payload)


class MinioStorage:
	def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool = False):
		try:
			from minio import Minio
		except Exception as exc:  # pragma: no cover - optional dependency
			raise RuntimeError(f"minio import failed: {exc}")

		self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
		self.bucket = bucket

		if not self.client.bucket_exists(bucket):
			self.client.make_bucket(bucket)

	def upload_image(self, image_bgr: np.ndarray, object_name: str) -> str:
		_, buffer = cv2.imencode(".jpg", image_bgr)
		data = buffer.tobytes()

		self.client.put_object(
			self.bucket,
			object_name,
			data=data,
			length=len(data),
			content_type="image/jpeg",
		)
		return object_name


class SimpleLogger:
	def log_spoof(self, camera_id: str, client_id: str, confidence: float) -> None:
		print(f"[LOG] Spoof detected camera_id={camera_id} client_id={client_id} confidence={confidence:.4f}")

	def log_access(self, employee_id: str, camera_id: str, similarity: float) -> None:
		print(f"[LOG] Access OK employee_id={employee_id} camera_id={camera_id} similarity={similarity:.4f}")

	def log_failed(self, status: str, camera_id: str, client_id: str, audit_object: Optional[str]) -> None:
		print(f"[LOG] Attendance {status} camera_id={camera_id} client_id={client_id} audit={audit_object}")


class TiDBLogger:
	def __init__(self, host: str, port: int, user: str, password: str, database: str, ssl_required: bool = True):
		try:
			import pymysql
		except Exception as exc:  # pragma: no cover - optional dependency
			raise RuntimeError(f"pymysql import failed: {exc}")

		self._pymysql = pymysql
		self._conn = None
		self._cfg = {
			"host": host,
			"port": port,
			"user": user,
			"password": password,
			"database": database,
			"autocommit": True,
		}
		if ssl_required:
			self._cfg["ssl"] = {}

	def _get_conn(self):
		if self._conn is None or not self._conn.open:
			self._conn = self._pymysql.connect(**self._cfg)
		return self._conn

	def _execute(self, sql: str, params: Tuple[Any, ...]) -> None:
		conn = self._get_conn()
		with conn.cursor() as cursor:
			cursor.execute(sql, params)

	def log_spoof(self, camera_id: str, client_id: str, confidence: float) -> None:
		sql = (
			"INSERT INTO attendance_logs (employee_id, status, minio_snapshot_path, camera_id, client_id, similarity) "
			"VALUES (%s, %s, %s, %s, %s, %s)"
		)
		self._execute(sql, (None, "FAILED", None, camera_id, client_id, confidence))

	def log_access(self, employee_id: str, camera_id: str, similarity: float) -> None:
		sql = (
			"INSERT INTO attendance_logs (employee_id, status, minio_snapshot_path, camera_id, similarity) "
			"VALUES (%s, %s, %s, %s, %s)"
		)
		self._execute(sql, (employee_id, "SUCCESS", None, camera_id, similarity))

	def log_failed(self, status: str, camera_id: str, client_id: str, audit_object: Optional[str]) -> None:
		sql = (
			"INSERT INTO attendance_logs (employee_id, status, minio_snapshot_path, camera_id, client_id) "
			"VALUES (%s, %s, %s, %s, %s)"
		)
		self._execute(sql, (None, status, audit_object, camera_id, client_id))


def load_image(input_data: Union[str, bytes, np.ndarray]) -> np.ndarray:
	if isinstance(input_data, np.ndarray):
		return input_data

	if isinstance(input_data, bytes):
		array = np.frombuffer(input_data, dtype=np.uint8)
		image = cv2.imdecode(array, cv2.IMREAD_COLOR)
		if image is None:
			raise ValueError("Failed to decode image bytes")
		return image

	image = cv2.imread(input_data)
	if image is None:
		raise ValueError(f"Failed to read image from path: {input_data}")
	return image


def crop_from_bbox(image_bgr: np.ndarray, bbox_xyxy: Tuple[int, int, int, int]) -> np.ndarray:
	x1, y1, x2, y2 = bbox_xyxy
	h, w = image_bgr.shape[:2]
	x1 = max(0, min(w - 1, x1))
	x2 = max(0, min(w, x2))
	y1 = max(0, min(h - 1, y1))
	y2 = max(0, min(h, y2))
	crop = image_bgr[y1:y2, x1:x2]
	return cv2.resize(crop, (112, 112), interpolation=cv2.INTER_LINEAR)


def run_pipeline(
	frame: Union[str, bytes, np.ndarray],
	camera_id: str,
	client_id: str,
	detector: FaceDetector,
	anti_spoof: AntiSpoofing,
	embedder: ArcFaceEmbedder,
	matcher: QdrantMatcher,
	aligner: Optional[FaceAligner] = None,
	storage: Optional[MinioStorage] = None,
	logger: Optional[SimpleLogger] = None,
) -> PipelineResult:
	logger = logger or build_logger_from_env() or SimpleLogger()
	aligner = aligner or FaceAligner()

	image_bgr = load_image(frame)

	detection = detector.detect(image_bgr)
	if detection is None:
		logger.log_failed("FAILED", camera_id=camera_id, client_id=client_id, audit_object=None)
		return PipelineResult(
			status="rejected",
			reason="no_face",
			employee_id=None,
			similarity=None,
			audit_object=None,
			payload=None,
		)

	audit_object = None
	if storage is not None:
		object_name = f"audit/{camera_id}/{datetime.utcnow().strftime('%Y%m%d')}/{uuid.uuid4().hex}.jpg"
		try:
			audit_object = storage.upload_image(image_bgr, object_name)
		except Exception as exc:
			print(f"[WARN] Failed to upload audit image: {exc}")

	if detection.landmarks_5 is not None:
		face = aligner.align(image_bgr, detection.landmarks_5)
	else:
		face = crop_from_bbox(image_bgr, detection.bbox_xyxy)

	spoof = anti_spoof.predict(image_bgr, detection.bbox_xyxy)
	if not spoof.is_real:
		logger.log_spoof(camera_id=camera_id, client_id=client_id, confidence=spoof.confidence)
		return PipelineResult(
			status="rejected",
			reason="spoof",
			employee_id=None,
			similarity=None,
			audit_object=audit_object,
			payload=None,
		)

	embedding = embedder.embed(face)
	match = matcher.match(embedding)

	if not match.employee_id:
		logger.log_failed("STRANGER", camera_id=camera_id, client_id=client_id, audit_object=audit_object)
		return PipelineResult(
			status="rejected",
			reason="no_match",
			employee_id=None,
			similarity=match.score,
			audit_object=audit_object,
			payload=match.payload,
		)

	logger.log_access(employee_id=match.employee_id, camera_id=camera_id, similarity=match.score or 0.0)
	return PipelineResult(
		status="accepted",
		reason="matched",
		employee_id=match.employee_id,
		similarity=match.score,
		audit_object=audit_object,
		payload=match.payload,
	)


def build_logger_from_env() -> Optional[TiDBLogger]:
	host = os.getenv("TIDB_HOST")
	user = os.getenv("TIDB_USER")
	password = os.getenv("TIDB_PASSWORD")
	database = os.getenv("TIDB_DB")

	if not host or not user or not password or not database:
		return None

	port = int(os.getenv("TIDB_PORT", "4000"))
	ssl_required = os.getenv("TIDB_SSL", "REQUIRE").upper() == "REQUIRE"

	return TiDBLogger(
		host=host,
		port=port,
		user=user,
		password=password,
		database=database,
		ssl_required=ssl_required,
	)


def build_default_components() -> Tuple[FaceDetector, AntiSpoofing, ArcFaceEmbedder, QdrantMatcher, Optional[MinioStorage]]:
	yolo_model = os.getenv("YOLO_FACE_MODEL", os.path.join(MODELS_DIR, "detection", "yolov8n-face.pt"))
	fas_model_dir = os.getenv(
		"FAS_MODEL_DIR", os.path.join(MINIFAS_CORE, "resources", "anti_spoof_models")
	)
	qdrant_host = os.getenv("QDRANT_HOST", "localhost")
	qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
	qdrant_collection = os.getenv("QDRANT_COLLECTION", "face_embeddings")
	qdrant_threshold = float(os.getenv("QDRANT_THRESHOLD", "0.45"))

	detector = FaceDetector(model_path=yolo_model)
	anti_spoof = AntiSpoofing(model_dir=fas_model_dir)
	embedder = ArcFaceEmbedder()
	matcher = QdrantMatcher(
		host=qdrant_host,
		port=qdrant_port,
		collection=qdrant_collection,
		threshold=qdrant_threshold,
	)

	storage = None
	minio_endpoint = os.getenv("MINIO_ENDPOINT")
	if minio_endpoint:
		storage = MinioStorage(
			endpoint=minio_endpoint,
			access_key=os.getenv("MINIO_ACCESS_KEY", ""),
			secret_key=os.getenv("MINIO_SECRET_KEY", ""),
			bucket=os.getenv("MINIO_BUCKET", "audit"),
			secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
		)

	return detector, anti_spoof, embedder, matcher, storage


if __name__ == "__main__":
	detector, anti_spoof, embedder, matcher, storage = build_default_components()
	test_image = os.getenv("TEST_IMAGE", os.path.join(MODELS_DIR, "detection", "test.jpg"))
	result = run_pipeline(
		frame=test_image,
		camera_id="camera-001",
		client_id="client-001",
		detector=detector,
		anti_spoof=anti_spoof,
		embedder=embedder,
		matcher=matcher,
		storage=storage,
	)
	print(result)
