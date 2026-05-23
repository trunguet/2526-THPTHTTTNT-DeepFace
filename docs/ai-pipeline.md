# AI Pipeline

Tài liệu này mô tả luồng xử lý AI hiện tại của DeepFace Access Control MVP. Mục tiêu là giúp người đọc hiểu rõ ảnh đi qua những bước nào, thành phần nào xử lý, dữ liệu được lưu ở đâu, và kết quả `granted`, `denied`, `error` được tạo ra như thế nào.

Phiên bản hiện tại tập trung vào luồng nhận diện khuôn mặt ổn định và có thể kiểm chứng:

- kiểm tra và lưu ảnh đầu vào;
- phát hiện đúng một khuôn mặt;
- tạo vector embedding bằng DeepFace;
- tìm vector gần nhất trong Qdrant;
- xác minh lại bằng PostgreSQL;
- cập nhật access log.

## 1. Tổng Quan Luồng

```text
Frontend
  -> Backend API
  -> Validate ảnh upload
  -> Lưu ảnh vào MinIO
  -> Tạo access log hoặc embedding job
  -> Đẩy job vào Redis
  -> Worker lấy job
  -> Worker tải ảnh từ MinIO về file tạm
  -> DeepFace detect face
  -> DeepFace tạo embedding
  -> Qdrant search/upsert vector
  -> PostgreSQL lưu/xác minh dữ liệu nghiệp vụ
  -> Cập nhật trạng thái cuối cùng
```

Các file chính:

- Backend upload/queue: `backend/app/api/employees.py`, `backend/app/api/access.py`
- Validate ảnh: `backend/app/utils/image_utils.py`
- Lưu ảnh vào MinIO: `backend/app/services/storage_service.py`
- Redis queue: `backend/app/queues/embedding_queue.py`, `backend/app/queues/access_queue.py`
- Worker queue: `worker/app/tasks/queue_worker.py`
- Tạo embedding employee: `worker/app/services/embedding_service.py`
- Check access: `worker/app/services/face_pipeline_service.py`
- DeepFace wrapper: `worker/app/ml/detector.py`, `worker/app/ml/embedder.py`
- Qdrant wrapper: `worker/app/services/vector_store_service.py`

## 2. Luồng Đăng Ký Ảnh Nhân Viên

Luồng này dùng khi admin upload ảnh khuôn mặt cho employee.

```text
Admin UI
  -> POST /employees/{employee_id}/face-image
  -> Backend validate ảnh
  -> Backend upload ảnh vào MinIO
  -> Backend queue embedding job vào Redis
  -> Worker xử lý embedding job
  -> Worker tạo vector DeepFace
  -> Worker kiểm tra trùng mặt trong Qdrant
  -> Worker lưu embedding vào PostgreSQL
  -> Worker upsert vector vào Qdrant
  -> Employee embedding_status = success/error
```

### 2.1. Backend nhận ảnh

Endpoint:

```text
POST /employees/{employee_id}/face-image
```

Backend kiểm tra employee có tồn tại không. Nếu employee không tồn tại, API trả `404`.

Sau đó backend gọi:

```text
upload_fastapi_image(file, prefix=f"employee-faces/{employee_id}")
```

### 2.2. Validate ảnh trước khi lưu

Logic validate nằm trong:

```text
backend/app/utils/image_utils.py
```

Hiện tại backend kiểm tra:

- extension hợp lệ: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`;
- content type hợp lệ: `image/jpeg`, `image/png`, `image/webp`, `image/bmp`;
- file không rỗng;
- file không vượt quá `5 MB`.

Nếu ảnh không hợp lệ, backend trả `400 Bad Request`, ảnh không được đưa vào MinIO và worker không phải xử lý file rác.

### 2.3. Lưu ảnh vào MinIO

Ảnh hợp lệ được lưu vào MinIO với object key dạng:

```text
employee-faces/{employee_id}/{uuid}.{ext}
```

Ví dụ:

```text
employee-faces/8/4b6f2f7b8f6b4f5f9c7f2c1a8c2e0b11.jpg
```

PostgreSQL hiện vẫn dùng một số field tên `image_path` để tương thích ngược, nhưng giá trị trong flow mới thực chất là MinIO object key.

### 2.4. Tạo embedding job

Sau khi upload thành công, backend đẩy job vào Redis queue:

```text
embedding_jobs
```

Payload có dạng:

```json
{
  "job_id": "uuid",
  "type": "embedding",
  "employee_id": 8,
  "image_path": "employee-faces/8/xxx.jpg",
  "image_key": "employee-faces/8/xxx.jpg"
}
```

Đồng thời employee được cập nhật:

```text
embedding_status = pending
embedding_error = null
```

### 2.5. Worker xử lý embedding job

Worker chạy:

```text
worker/app/tasks/queue_worker.py
```

Worker lắng nghe Redis theo thứ tự:

```text
embedding_jobs
access_jobs
```

Khi nhận embedding job, worker gọi:

```text
handle_embedding_job()
-> create_employee_embedding()
```

### 2.6. Worker lấy ảnh từ MinIO

Worker nhận `image_key` hoặc `image_path`. Nếu giá trị là object key, worker tải ảnh từ MinIO về file tạm:

```text
worker/app/services/storage_service.py
-> resolved_image_file()
-> download_image_object()
```

File tạm được xóa sau khi xử lý xong.

Worker vẫn chấp nhận đường dẫn local như `/app/data/smoke/...` để phục vụ smoke test/dev, nhưng flow UI/API mới dùng MinIO object key.

### 2.7. Detect face

Worker gọi:

```text
require_face()
-> DeepFace.extract_faces()
```

Logic nằm trong:

```text
worker/app/ml/detector.py
```

Detector hiện dùng default:

```text
DEEPFACE_DETECTOR_BACKEND=mtcnn
DEEPFACE_ENFORCE_DETECTION=true
DEEPFACE_ALIGN=false
```

Kết quả detect gồm:

- có phát hiện mặt hay không;
- bounding box khuôn mặt;
- confidence;
- số lượng khuôn mặt;
- face crop do DeepFace trả về.

Nếu ảnh có nhiều hơn một khuôn mặt, pipeline reject với lỗi:

```text
Multiple faces detected. Frame rejected. Please keep exactly one face in the camera frame.
```

Điều này giúp hệ thống giữ đúng mô hình điểm danh một người trong một khung hình.

### 2.8. Tạo embedding từ face crop

Nếu detector trả về `face_image`, worker dùng luôn face crop đó để tạo embedding:

```text
create_face_embedding_from_face()
-> DeepFace.represent(detector_backend="skip")
```

Điểm quan trọng: bước embedding không detect lại từ đầu nếu đã có face crop. `detector_backend="skip"` nghĩa là DeepFace nhận ảnh khuôn mặt đã cắt sẵn và chỉ tạo vector.

Nếu không có face crop, worker fallback sang:

```text
create_face_embedding()
-> DeepFace.represent()
```

### 2.9. Kiểm tra trùng khuôn mặt

Trước khi lưu embedding mới, worker tìm trong Qdrant xem vector này có quá giống employee khác không:

```text
search_face_embeddings(limit=5)
```

Nếu tìm thấy employee khác đang active và score vượt:

```text
DEEPFACE_DUPLICATE_THRESHOLD=0.95
```

worker báo lỗi để tránh một khuôn mặt bị đăng ký cho nhiều employee.

### 2.10. Lưu embedding

Khi pass các bước trên:

1. Worker lưu vector vào PostgreSQL bảng `face_embeddings`.
2. Worker lưu `model_name`, ví dụ `Facenet512`.
3. Worker lưu `source_image_key` để biết embedding này được tạo từ ảnh nào.
4. Worker upsert vector vào Qdrant.
5. Worker cập nhật employee:

```text
embedding_status = success
embedding_error = null
```

Nếu có lỗi, worker cập nhật:

```text
embedding_status = error
embedding_error = <message>
```

## 3. Luồng Check Access

Luồng này dùng khi user/camera gửi ảnh để kiểm tra có được mở cổng hay không.

```text
User UI / webcam
  -> POST /access/check-image
  -> Backend validate ảnh
  -> Backend upload ảnh vào MinIO
  -> Backend tạo access_log status=processing
  -> Backend đẩy access job vào Redis
  -> Worker detect face
  -> Worker tạo embedding snapshot
  -> Worker search Qdrant
  -> Worker verify candidate trong PostgreSQL
  -> Worker cập nhật access_log thành granted/denied/error
```

### 3.1. Backend nhận snapshot

Endpoint chính của UI:

```text
POST /access/check-image
```

Request gồm:

- `camera_id`;
- file ảnh snapshot.

Backend validate ảnh giống luồng employee upload, sau đó lưu ảnh vào MinIO với prefix:

```text
access-snapshots/{uuid}.{ext}
```

### 3.2. Giới hạn queue để tránh spam frame

Trước khi tạo access log mới, backend đếm số log `processing` của camera đó:

```text
count_processing_access_logs(camera_id)
```

Nếu số log đang xử lý vượt hoặc bằng:

```text
MAX_PROCESSING_ACCESS_LOGS_PER_CAMERA
```

API trả `429 Too Many Requests`. Cơ chế này giúp user UI không spam quá nhiều frame làm worker/DeepFace bị nghẽn.

### 3.3. Tạo access log và access job

Nếu queue chưa đầy, backend tạo record:

```text
access_logs.status = processing
access_logs.employee_id = null
access_logs.score = null
access_logs.image_path = <MinIO object key>
```

Sau đó backend đẩy job vào Redis queue:

```text
access_jobs
```

Payload có dạng:

```json
{
  "job_id": "uuid",
  "type": "access_check",
  "log_id": 123,
  "camera_id": 1,
  "image_path": "access-snapshots/xxx.jpg",
  "image_key": "access-snapshots/xxx.jpg"
}
```

API trả response ngay với `status=processing`. Kết quả thật sẽ được worker cập nhật sau.

### 3.4. Worker xử lý access job

Worker gọi:

```text
handle_access_job()
-> process_access_check()
```

Các bước xử lý ảnh giống luồng embedding:

1. Tải ảnh từ MinIO về file tạm.
2. Detect đúng một khuôn mặt bằng DeepFace.
3. Tạo embedding từ face crop bằng `detector_backend="skip"`.
4. Search Qdrant theo vector vừa tạo.

### 3.5. Search Qdrant

Worker gọi:

```text
search_face_embeddings(query_vector, model_name, limit=10)
```

Qdrant chỉ search các vector có cùng:

```text
model_name
```

Điều này tránh match nhầm giữa các embedding được tạo từ model khác nhau.

Qdrant dùng distance:

```text
Cosine
```

Score càng cao thì vector càng giống nhau.

### 3.6. Verify lại bằng PostgreSQL

Qdrant chỉ là vector search index. Sau khi Qdrant trả candidate, worker vẫn kiểm tra lại trong PostgreSQL:

- embedding id có tồn tại không;
- employee id có khớp không;
- employee còn `active` không;
- `model_name` có khớp không.

Lý do: PostgreSQL là source of truth, còn Qdrant chỉ giúp tìm kiếm vector nhanh.

### 3.7. Quyết định granted/denied/error

Worker so sánh score tốt nhất với:

```text
DEEPFACE_MATCH_THRESHOLD=0.70
```

Kết quả:

- `granted`: tìm thấy employee active và score >= threshold;
- `denied`: có candidate nhưng score < threshold, hoặc không có embedding active phù hợp;
- `error`: ảnh lỗi, không detect được mặt, nhiều mặt, MinIO/Qdrant lỗi, hoặc DeepFace không tạo được embedding.

Sau khi quyết định, worker cập nhật record trong `access_logs`:

```text
status
employee_id
score
message
```

User UI đọc lịch sử access log để hiển thị kết quả cho người dùng.

## 4. Cấu Hình AI Hiện Tại

Worker đọc các biến môi trường trong `worker/app/config/settings.py`.

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `DEEPFACE_MODEL_NAME` | `Facenet512` | Model dùng để tạo embedding. |
| `DEEPFACE_DETECTOR_BACKEND` | `mtcnn` | Detector chính dùng cho đăng ký employee. |
| `DEEPFACE_ACCESS_DETECTOR_BACKEND` | fallback theo `DEEPFACE_DETECTOR_BACKEND` | Detector riêng cho access nếu muốn override. Hiện không cần set riêng vì đều dùng `mtcnn`. |
| `DEEPFACE_FACE_COUNT_BACKEND` | rỗng | Optional detector riêng để đếm mặt trước. Nếu rỗng thì không chạy bước đếm riêng. |
| `DEEPFACE_ENFORCE_DETECTION` | `true` | Nếu không detect được mặt thì DeepFace báo lỗi. |
| `DEEPFACE_ALIGN` | `false` | Có căn chỉnh mặt trước khi detect/represent hay không. |
| `DEEPFACE_NORMALIZATION` | `base` | Cách chuẩn hóa ảnh đầu vào cho DeepFace. |
| `DEEPFACE_MATCH_THRESHOLD` | `0.70` | Ngưỡng mở cổng khi so khớp access. |
| `DEEPFACE_DUPLICATE_THRESHOLD` | `0.95` | Ngưỡng chặn đăng ký trùng khuôn mặt giữa hai employee. |
| `DEEPFACE_WARMUP_ON_START` | `true` | Worker khởi động sẽ warm up model để giảm độ trễ request đầu. |
| `QDRANT_URL` | `http://qdrant:6333` | Endpoint Qdrant. |
| `QDRANT_COLLECTION` | `deepface_embeddings` | Collection lưu/search vector. |

`.env` chỉ cần set các biến muốn override. Các biến không set sẽ lấy default từ Docker Compose hoặc code.

## 5. Vì Sao Có PostgreSQL Và Qdrant Cùng Lúc

PostgreSQL lưu dữ liệu nghiệp vụ:

- employee;
- camera;
- access log;
- face embedding metadata;
- vector embedding làm source of truth;
- `source_image_key` để biết ảnh gốc.

Qdrant dùng cho tìm kiếm vector nhanh:

- lưu vector theo `embedding_id`;
- payload gồm `employee_id`, `embedding_id`, `model_name`;
- search top candidate theo cosine similarity.

Thiết kế này giúp hệ thống vừa có database nghiệp vụ rõ ràng, vừa có vector search đủ nhanh cho face matching.

## 6. Reindex Là Gì

Reindex là việc tạo lại vector trong Qdrant từ ảnh gốc.

Cần reindex khi:

- đổi `DEEPFACE_MODEL_NAME`;
- đổi cấu hình embedding làm vector cũ không còn tương thích;
- xóa/rebuild Qdrant collection;
- muốn làm sạch vector index.

Repo hiện đã lưu `source_image_key` trong PostgreSQL, nên về mặt dữ liệu đã biết mỗi embedding được tạo từ ảnh nào. Automated reindex có thể được bổ sung ở bước mở rộng để tái tạo Qdrant index khi đổi model hoặc rebuild collection.

## 7. Trạng Thái Lỗi Thường Gặp Trong Pipeline

Một số lỗi phổ biến:

- Ảnh upload không đúng định dạng hoặc quá lớn: backend trả `400`.
- Camera không tồn tại: backend trả `404`.
- Camera còn quá nhiều frame `processing`: backend trả `429`.
- Worker không tải được ảnh từ MinIO: access log thành `error`.
- DeepFace không detect được mặt: access log thành `error`.
- Có nhiều hơn một khuôn mặt: access log thành `error`.
- Qdrant không có embedding phù hợp: access log thành `denied`.
- Score thấp hơn threshold: access log thành `denied`.

## 8. Smoke Test AI Thật

Repo có smoke test riêng để chứng minh DeepFace chạy thật trong container:

```powershell
.\scripts\smoke-deepface.ps1
```

Script này không chạy full frontend/nginx/monitoring. Nó chỉ dùng các service cần thiết cho AI runtime.

Ảnh test nằm trong:

```text
data/smoke/
```

Các case chính:

```text
employee_a_ref.jpg -> tạo embedding employee A
employee_a_ok.jpg  -> granted
employee_b_ok.jpg  -> denied
no_face.jpg        -> error
```

Script sẽ in score và thời gian xử lý từng case. Đây là bằng chứng thực nghiệm cho thấy pipeline AI được kiểm tra bằng ảnh mẫu và worker thật.

## 9. Phạm Vi Hiện Tại Và Hướng Mở Rộng

Pipeline hiện tại đáp ứng luồng chính của bài toán nhận diện một người trong một khung hình. Các hướng mở rộng hợp lý gồm:

- Bổ sung job reindex Qdrant tự động.
- Accuracy phụ thuộc mạnh vào ảnh đăng ký, ánh sáng, góc mặt và threshold.
- DeepFace/Facenet512 vẫn khá nặng, nên realtime trên webcam chỉ gửi frame định kỳ thay vì 30 FPS.
- UI user nên giữ đúng một người trong khung hình để tránh reject nhiều mặt.

## 10. Tóm Tắt Ngắn

```text
Đăng ký nhân viên:
upload ảnh -> MinIO -> Redis embedding_jobs -> worker -> detect face -> embedding -> chống trùng -> PostgreSQL + Qdrant

Check access:
upload/chụp snapshot -> MinIO -> Redis access_jobs -> worker -> detect face -> embedding -> Qdrant search -> PostgreSQL verify -> access_logs
```

Kết quả cuối cùng nằm trong `access_logs`:

- `processing`: backend đã nhận job, worker chưa xử lý xong;
- `granted`: nhận diện thành công và đủ threshold;
- `denied`: có xử lý nhưng không đủ điều kiện mở cổng;
- `error`: ảnh/input/pipeline gặp lỗi.
