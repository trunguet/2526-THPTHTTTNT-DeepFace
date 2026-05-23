# Architecture

Tài liệu này mô tả kiến trúc hiện tại của DeepFace Access Control. Repo đang có một hệ thống end-to-end gồm frontend, backend API, worker AI, database, queue, object storage, vector database, monitoring, backup và baseline Helm cho Kubernetes.

---

## 1. Mục Tiêu Kiến Trúc

Hệ thống được thiết kế theo hướng tách service:

- frontend chỉ lo UI;
- backend chỉ nhận request, validate, lưu metadata và queue job;
- worker xử lý AI nặng ở background;
- PostgreSQL giữ dữ liệu nghiệp vụ;
- MinIO giữ file ảnh;
- Qdrant giữ vector embedding để search nhanh;
- Redis làm hàng đợi giữa backend và worker;
- Prometheus/Grafana theo dõi vận hành;
- cron-backup sao lưu database định kỳ.

Điểm quan trọng: DeepFace không chạy trực tiếp trong request chính. Backend trả nhanh, worker xử lý sau.

---

## 2. Sơ Đồ Tổng Quan

```text
Browser
  |
  | http://localhost:8080
  v
Nginx
  |-----------------------> frontend-home
  |-----------------------> frontend-user
  |-----------------------> frontend-admin
  |
  | /api, /health, /metrics, /docs
  v
Backend API
  |-----------------------> PostgreSQL
  |-----------------------> Redis
  |-----------------------> MinIO
  |
  | queue embedding_jobs / access_jobs
  v
Worker
  |-----------------------> MinIO
  |-----------------------> PostgreSQL
  |-----------------------> Qdrant
  |
  v
DeepFace Pipeline
```

Monitoring và backup chạy song song:

```text
Prometheus ---> Backend /metrics
     |
     v
Grafana Dashboard

Prometheus ---> Alertmanager

cron-backup ---> PostgreSQL dump ---> MinIO/S3
```

---

## 3. Runtime Services Trong Docker Compose

| Service | Công nghệ | Vai trò |
|---|---|---|
| `frontend-home` | Nginx static | Trang home chọn User/Admin. |
| `frontend-user` | React/Vite build qua Nginx | UI điểm danh bằng webcam, xem history/session. |
| `frontend-admin` | React/Vite build qua Nginx | UI quản trị employee, logs, users, settings/report. |
| `nginx` | Nginx | Reverse proxy tổng, gom các frontend và backend về port `8080`. |
| `backend` | FastAPI | Auth, API nghiệp vụ, upload ảnh, queue job, health/metrics. |
| `db-seed` | Python one-shot | Seed database, admin/user mặc định và dữ liệu mẫu. |
| `database` | PostgreSQL 16 | Lưu users, employees, cameras, face_embeddings, access_logs. |
| `redis` | Redis 7 | Queue `embedding_jobs` và `access_jobs`. |
| `worker` | Python + DeepFace | Tạo embedding, nhận diện access, cập nhật log. |
| `minio` | MinIO | Object storage cho ảnh employee và ảnh access. |
| `qdrant` | Qdrant | Vector database cho face embedding search. |
| `prometheus` | Prometheus | Scrape `/metrics` từ backend. |
| `grafana` | Grafana | Dashboard trạng thái hệ thống. |
| `alertmanager` | Alertmanager | Nhận alert từ Prometheus. |
| `cron-backup` | Alpine + supercronic | Dump PostgreSQL định kỳ và upload vào MinIO/S3. |

---

## 4. Port Và Entry Point

| Thành phần | URL/port |
|---|---|
| Nginx tổng | `http://localhost:8080` |
| User UI qua Nginx | `http://localhost:8080/user/` |
| Admin UI qua Nginx | `http://localhost:8080/admin/` |
| Backend API qua Nginx | `http://localhost:8080/api/...` |
| Swagger qua Nginx | `http://localhost:8080/docs` |
| Backend trực tiếp | `http://localhost:8000` |
| User frontend trực tiếp | `http://localhost:5173` |
| Admin frontend trực tiếp | `http://localhost:5174` |
| Home frontend trực tiếp | `http://localhost:5172` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |
| MinIO API | `http://localhost:9000` |
| MinIO Console | `http://localhost:9001` |
| Qdrant REST | `http://localhost:6333` |
| Prometheus | `http://localhost:9090` |
| Alertmanager | `http://localhost:9093` |
| Grafana | `http://localhost:3000` |

Nginx route chính:

| Route | Đi tới |
|---|---|
| `/` | `frontend-home` |
| `/user/` | `frontend-user` |
| `/admin/` | `frontend-admin` |
| `/api/` | `backend` |
| `/health` | `backend /health` |
| `/metrics` | `backend /metrics` |
| `/docs` | `backend /docs` |
| `/openapi.json` | `backend /openapi.json` |

---

## 5. Backend API Layer

Backend là FastAPI service.

Các router chính:

| Router | Vai trò |
|---|---|
| `/auth` | Login, lấy thông tin user hiện tại. |
| `/employees` | CRUD employee, upload ảnh face, queue embedding. |
| `/cameras` | Đọc camera mặc định. Tạo/sửa/xóa được giới hạn trong phiên bản hiện tại. |
| `/access` | Upload snapshot, tạo access check job. |
| `/logs` | Xem access logs. |
| `/admin` | Status, users, evaluation report. |
| `/health` | Health check database/Redis. |
| `/metrics` | Prometheus metrics. |

Backend chịu trách nhiệm:

- xác thực JWT Bearer token;
- phân quyền `admin`/`user`;
- validate ảnh upload;
- upload ảnh vào MinIO;
- tạo/cập nhật PostgreSQL record;
- enqueue Redis job;
- expose health/metrics.

Backend không chịu trách nhiệm:

- chạy DeepFace nặng trong request;
- giữ ảnh trực tiếp trong database;
- search vector trực tiếp thay Qdrant.

---

## 6. Database Layer

PostgreSQL là source of truth của hệ thống.

Các bảng chính:

| Bảng | Nội dung |
|---|---|
| `users` | Tài khoản đăng nhập, role `admin/user`, password hash. |
| `employees` | Hồ sơ nhân viên, mã nhân viên, tên, trạng thái embedding. |
| `cameras` | Camera/cổng. Phiên bản hiện tại dùng một camera mặc định. |
| `face_embeddings` | Metadata embedding, employee_id, model, source_image_key. |
| `access_logs` | Lịch sử check access, status, score, employee, camera, image_path. |

PostgreSQL giữ dữ liệu chuẩn. Qdrant chỉ là index vector để tìm kiếm nhanh.

---

## 7. Object Storage Layer

MinIO dùng để lưu ảnh upload.

Bucket default:

```text
deepface-images
```

Prefix chính:

| Prefix | Nội dung |
|---|---|
| `employee-faces/{employee_id}/...` | Ảnh dùng để tạo embedding employee. |
| `access-snapshots/...` | Ảnh snapshot khi check access. |
| `deepface-db-backups/...` | File backup database do `cron-backup` upload. |

Lý do dùng MinIO:

- không lưu ảnh lớn trong PostgreSQL;
- backend/worker đều có thể đọc cùng object key;
- phù hợp khi triển khai lên S3 hoặc object storage thật.

Trong database, một số field vẫn tên là `image_path`, nhưng ở flow mới giá trị thường là MinIO object key.

---

## 8. Queue Và Worker Layer

Redis dùng làm queue giữa backend và worker.

| Queue | Tạo bởi | Xử lý bởi | Mục đích |
|---|---|---|---|
| `embedding_jobs` | Employee upload/embedding endpoint | worker | Tạo vector khuôn mặt employee. |
| `access_jobs` | Access check endpoint | worker | Nhận diện ảnh access. |

Worker chạy:

```text
python -m app.main
```

Worker lắng nghe Redis, lấy job, tải ảnh từ MinIO, chạy DeepFace và cập nhật PostgreSQL/Qdrant.

Queue giúp:

- API không bị treo khi DeepFace xử lý lâu;
- giới hạn backlog;
- có thể scale worker sau này;
- dễ quan sát queue length qua Prometheus.

---

## 9. AI Pipeline Layer

AI pipeline hiện dùng:

| Thành phần | Cấu hình hiện tại |
|---|---|
| Model embedding | `Facenet512` |
| Detector | `mtcnn` |
| Access detector | `mtcnn` |
| Align | `false` |
| Normalization | `base` |
| Match threshold | `0.70` |
| Duplicate threshold | `0.95` |

Luồng chính:

```text
image key
  -> worker tải ảnh từ MinIO/local
  -> detect mặt bằng DeepFace
  -> reject nếu không có mặt hoặc nhiều mặt
  -> tạo embedding từ face crop
  -> Qdrant search/upsert
  -> cập nhật PostgreSQL
```

Điểm tối ưu hiện tại:

- nếu detector đã trả `face_image`, worker tạo embedding từ face crop;
- bước embedding dùng `detector_backend="skip"` để tránh detect lại lần hai;
- access check có queue limit theo camera để tránh spam frame.

---

## 10. Vector Search Layer

Qdrant lưu vector embedding và dùng Cosine distance để tìm khuôn mặt gần nhất.

Qdrant collection default:

```text
deepface_embeddings
```

Payload trong Qdrant gồm:

```text
embedding_id
employee_id
model_name
```

Access matching:

1. worker tạo embedding từ ảnh access;
2. worker search Qdrant theo `model_name`;
3. Qdrant trả candidate gần nhất;
4. worker kiểm tra lại employee trong PostgreSQL;
5. nếu employee active và score đạt threshold thì `granted`;
6. nếu không đạt thì `denied`;
7. nếu pipeline lỗi thì `error`.

Qdrant không thay PostgreSQL. Nếu Qdrant cần được rebuild, hệ thống đã có metadata ảnh nguồn để bổ sung cơ chế reindex ở bước mở rộng.

---

## 11. Luồng Đăng Ký Employee

```text
Admin UI
  -> POST /employees
  -> POST /employees/{id}/face-image
  -> Backend validate ảnh
  -> Backend upload MinIO
  -> Backend queue embedding_jobs
  -> Worker tải ảnh
  -> Worker detect một khuôn mặt
  -> Worker tạo embedding
  -> Worker check trùng trong Qdrant
  -> Worker lưu face_embeddings
  -> Worker upsert Qdrant
  -> Employee embedding_status = success/error
```

Trạng thái employee:

| `embedding_status` | Ý nghĩa |
|---|---|
| `none` | Chưa có job embedding. |
| `pending` | Đang chờ worker xử lý. |
| `success` | Embedding đã sẵn sàng. |
| `error` | Ảnh lỗi hoặc pipeline thất bại. |

---

## 12. Luồng Check Access

```text
User UI webcam
  -> POST /access/check-image
  -> Backend validate ảnh
  -> Backend upload MinIO
  -> Backend tạo access_logs status=processing
  -> Backend queue access_jobs
  -> Worker tải ảnh
  -> Worker detect một khuôn mặt
  -> Worker tạo embedding
  -> Worker search Qdrant
  -> Worker verify employee trong PostgreSQL
  -> access_logs status=granted/denied/error
  -> User UI đọc /logs để hiển thị kết quả
```

Status access:

| Status | Ý nghĩa |
|---|---|
| `processing` | Đã nhận ảnh, worker chưa xử lý xong. |
| `granted` | Nhận diện thành công và đạt threshold. |
| `denied` | Có mặt nhưng không match đủ tốt. |
| `error` | Không có mặt, nhiều mặt, ảnh lỗi hoặc lỗi dependency. |

---

## 13. Frontend Architecture

Repo có 3 frontend:

| Frontend | Path | Vai trò |
|---|---|---|
| Home | `frontend/home` | Trang mở đầu, link tới User/Admin. |
| User | `frontend/user` | Điểm danh bằng webcam, history, session. |
| Admin | `frontend/admin` | Quản trị employees, logs, users, settings/report. |

Build-time args:

| Biến | Ý nghĩa |
|---|---|
| `VITE_API_BASE_URL` | Base URL gọi backend. |
| `VITE_BASE_PATH` | Base path khi chạy sau Nginx, ví dụ `/user/`, `/admin/`. |

Trong Docker Compose:

- User UI chạy trực tiếp ở `5173`;
- Admin UI chạy trực tiếp ở `5174`;
- Home UI chạy trực tiếp ở `5172`;
- Nginx gom lại ở `8080`.

---

## 14. Monitoring Architecture

Backend expose:

```text
/metrics
```

Prometheus scrape target:

```text
backend:8000/metrics
```

Metric chính:

```text
deepface_backend_up
deepface_database_up
deepface_redis_up
deepface_queue_length{queue="embedding_jobs"}
deepface_queue_length{queue="access_jobs"}
deepface_access_logs_total{status="..."}
```

Grafana đọc Prometheus datasource:

```text
http://prometheus:9090
```

Alert hiện có:

| Alert | Ý nghĩa |
|---|---|
| `BackendMetricsDown` | Prometheus không scrape được backend. |
| `DatabaseUnavailable` | Backend không kết nối được PostgreSQL. |
| `RedisUnavailable` | Backend không kết nối được Redis. |
| `QueueBacklogHigh` | Tổng queue jobs quá cao. |
| `AccessProcessingBacklog` | Nhiều access log kẹt `processing`. |
| `AccessErrorsPresent` | Có access log trạng thái `error`. |

Alertmanager hiện dùng local receiver; các kênh Slack/email/webhook có thể được bổ sung khi triển khai môi trường vận hành thật.

---

## 15. Backup Architecture

Repo có 2 hướng backup:

| Cách | File/service | Mục đích |
|---|---|---|
| Backup thủ công local | `scripts/backup.ps1` | Dump PostgreSQL và backup data local. |
| Backup tự động Docker | `cron-backup` | Dump PostgreSQL định kỳ và upload lên MinIO/S3. |

`cron-backup` gồm:

```text
backup/cron/Dockerfile
backup/cron/backup.sh
backup/cron/backup.cron
```

Lịch chạy:

```text
0 0 */5 * *
```

Nghĩa là chạy 5 ngày/lần lúc 00:00 theo timezone container.

Backup output:

```text
s3://deepface-images/deepface-db-backups/<timestamp>/postgres.sql
s3://deepface-images/deepface-db-backups/<timestamp>/manifest.txt
```

Trong local Docker, S3 endpoint thực chất là MinIO:

```text
http://minio:9000
```

---

## 16. CI/CD Và Image

GitHub Actions hiện có job:

| Job | Việc làm |
|---|---|
| `backend-tests` | Cài backend deps và chạy backend tests. |
| `worker-tests` | Cài worker deps và chạy worker tests. |
| `frontend-builds` | Build user/admin frontend. |
| `docker-builds` | Build Docker images và push Docker Hub khi push main. |

Images chính:

```text
deepface-backend
deepface-worker
deepface-frontend-user
deepface-frontend-home
deepface-frontend-admin
```

Tag:

```text
latest
<commit-sha>
```

Lưu ý: `cron-backup` hiện build được bằng Docker Compose local. Nếu muốn publish backup image lên Docker Hub như các image chính, cần thêm bước build/push `deepface-cron-backup` vào CI.

---

## 17. Helm/Kubernetes Baseline

Helm chart nằm ở:

```text
helm/deepface-access
```

Chart có template cho:

- backend;
- worker;
- frontend-user;
- frontend-admin;
- database;
- redis;
- minio;
- qdrant;
- ingress nginx.

Vai trò hiện tại:

- thể hiện hướng triển khai Kubernetes;
- render/lint được baseline;
- là nền tảng để mở rộng thành deployment production.

Phạm vi hiện tại:

- monitoring stack có thể được bổ sung vào Helm ở bước sau;
- `cron-backup` có thể được chuyển thành Kubernetes CronJob;
- MinIO/Qdrant trong Helm đang để optional;
- cần đồng bộ Helm values khi thay đổi cấu hình DeepFace trong Docker Compose.

---

## 18. Healthcheck Và Startup Order

Docker Compose dùng `depends_on` + healthcheck để giảm lỗi khởi động sai thứ tự.

Ví dụ:

- `database` phải healthy trước khi `db-seed` chạy;
- `backend` chờ `db-seed`, database, Redis, MinIO;
- `worker` chờ `db-seed`, database, Redis, MinIO;
- `nginx` chờ backend và frontend healthy;
- `cron-backup` chờ database healthy.

Healthcheck chính:

| Service | Kiểm tra |
|---|---|
| `database` | `pg_isready` |
| `redis` | `redis-cli ping` |
| `backend` | gọi `/health` |
| `frontend-*` | `wget` vào trang static |
| `nginx` | gọi `/health` qua proxy |
| `worker` | ping Redis |
| `minio` | `mc ready local` |

---

## 19. Data Persistence

Docker volumes:

| Volume | Lưu gì |
|---|---|
| `postgres_data` | Dữ liệu PostgreSQL. |
| `minio_data` | Object ảnh và backup trong MinIO. |
| `qdrant_data` | Vector index Qdrant. |
| `redis` | Không dùng volume persistent mặc định. |
| `prometheus_data` | Time-series Prometheus. |
| `grafana_data` | Grafana state. |
| `alertmanager_data` | Alertmanager state. |
| `deepface_weights` | Model weights DeepFace cache. |

Lưu ý:

- `data/smoke` được mount vào backend/worker để phục vụ smoke test/dev.
- Ảnh upload thật đi qua MinIO volume, không nằm trực tiếp trong repo.

---

## 20. Phạm Vi Hiện Tại Và Hướng Mở Rộng

Các điểm mở rộng nên nêu rõ khi trình bày:

- Realtime hiện xử lý theo snapshot interval, phù hợp với luồng điểm danh theo khung hình.
- Camera management đang read-only và dùng một camera mặc định để giữ log nhất quán.
- Qdrant reindex có thể được tự động hóa thêm.
- Alertmanager có thể bổ sung Slack/email/webhook.
- Helm là baseline để triển khai Kubernetes và có thể kiểm chứng thêm trên cluster thật.
- CI hiện publish các app images chính; `cron-backup` có thể được bổ sung vào pipeline publish.
- Accuracy report là bộ đánh giá nội bộ có tổ chức, phù hợp để minh họa chất lượng pipeline.

---

## 21. Tóm Tắt Ngắn

Kiến trúc hiện tại là một hệ thống AI service-based:

```text
Frontend -> Nginx -> Backend -> Redis Queue -> Worker AI -> PostgreSQL/Qdrant/MinIO
```

Backend giữ API và trạng thái nghiệp vụ. Worker xử lý DeepFace. PostgreSQL giữ dữ liệu chuẩn. MinIO giữ ảnh. Qdrant search vector. Redis nối backend với worker. Prometheus/Grafana theo dõi hệ thống. cron-backup sao lưu database định kỳ.

Kiến trúc này phù hợp để trình bày một hệ thống AI engineering end-to-end, có separation of concerns, queue xử lý nền, observability, backup và hướng triển khai Kubernetes.
