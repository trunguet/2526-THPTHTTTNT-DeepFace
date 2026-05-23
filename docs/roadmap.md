# Roadmap

Tài liệu này tóm tắt quá trình xây dựng DeepFace Access Control từ skeleton ban đầu đến hệ thống hiện tại. Nội dung dùng để giải thích nhóm đã phát triển theo hướng nào, mỗi giai đoạn thêm thành phần gì và kết quả đạt được ra sao.

---

## 1. Định Hướng Chung

Chiến lược phát triển:

```text
chạy được trước
-> nối flow thực tế
-> thay prototype AI bằng DeepFace
-> thêm MinIO/Qdrant
-> bổ sung CI/CD, monitoring, backup, Helm
```

Nguyên tắc:

- đi theo flow người dùng, không chỉ code rời rạc từng folder;
- backend nhận request và queue job;
- worker xử lý AI nền;
- PostgreSQL là source of truth;
- MinIO lưu ảnh;
- Qdrant search vector;
- Docker Compose giúp chạy lại toàn bộ hệ thống.

---

## 2. Giai Đoạn 1: Skeleton Chạy Được

Mục tiêu: có khung hệ thống nhiều service chạy được bằng Docker Compose.

Thành phần:

- `backend`: FastAPI skeleton;
- `frontend-user`: UI người dùng tối thiểu;
- `frontend-admin`: UI admin tối thiểu;
- `worker`: process Python;
- `database`: PostgreSQL;
- `redis`: Redis queue;
- `docker-compose.yml`.

Kết quả:

- stack start được;
- các service chính có container riêng;
- tạo nền tảng để nối API và AI worker.

---

## 3. Giai Đoạn 2: Database Và Backend API

Mục tiêu: thiết kế dữ liệu và API cốt lõi.

Bảng chính:

- `users`;
- `employees`;
- `cameras`;
- `face_embeddings`;
- `access_logs`.

API chính:

- auth login/me;
- employee CRUD;
- camera read/default;
- access logs;
- access check.

Kết quả:

- mở được Swagger;
- đăng nhập được bằng tài khoản seed;
- quản lý employee/camera/log qua API;
- có database schema rõ ràng.

---

## 4. Giai Đoạn 3: Redis Queue Và Worker

Mục tiêu: tách xử lý nền khỏi request API.

Queue:

```text
embedding_jobs: tạo embedding cho ảnh employee
access_jobs: xử lý ảnh check ra/vào
```

Backend:

- tạo log `processing`;
- enqueue Redis job;
- trả response nhanh.

Worker:

- lắng nghe queue;
- xử lý job;
- cập nhật database.

Kết quả:

- hệ thống có xử lý nền đúng yêu cầu;
- request API không bị giữ lâu bởi tác vụ AI;
- lỗi worker được ghi vào status/message.

---

## 5. Giai Đoạn 4: DeepFace AI Pipeline

Mục tiêu: thay flow prototype bằng DeepFace thật.

Pipeline:

```text
ảnh
-> detect mặt
-> reject nếu không có mặt hoặc nhiều mặt
-> tạo embedding
-> so khớp vector
-> cập nhật access log
```

Cấu hình chính:

- model: `Facenet512`;
- detector: `mtcnn`;
- threshold: `0.70`;
- duplicate threshold: `0.95`.

Kết quả:

- đăng ký employee bằng ảnh kiểm thử tạo được embedding;
- check access trả về `granted`, `denied` hoặc `error`;
- worker Docker import và chạy được DeepFace;
- smoke test AI kiểm chứng được runtime.

---

## 6. Giai Đoạn 5: Frontend User/Admin

Mục tiêu: người dùng thao tác flow chính bằng UI, không phụ thuộc Swagger.

User UI:

- login;
- bật webcam;
- gửi snapshot theo interval;
- hiển thị result card;
- xem history/session.

Admin UI:

- login;
- quản lý employees;
- upload face image;
- xem access logs;
- quản lý users;
- settings/report.

Điều chỉnh UI:

- camera user được mở rộng để dễ lấy mặt;
- history/logs có phân trang frontend;
- camera management admin chuyển read-only;
- employees tách phần thêm mới và danh sách;
- result card hiển thị employee name, score, status.

Kết quả:

- admin tạo employee và upload ảnh được;
- user check access được;
- UI hiển thị lỗi rõ khi pipeline trả `error`.

---

## 7. Giai Đoạn 6: MinIO Và Qdrant

Mục tiêu: đưa object storage và vector database vào flow chính.

MinIO:

- lưu ảnh employee;
- lưu ảnh access snapshot;
- backend/worker trao đổi qua object key.

Qdrant:

- lưu vector embedding;
- search vector theo `model_name`;
- worker verify lại bằng PostgreSQL.

Kết quả:

- ảnh upload không nằm trực tiếp trong database;
- vector search nhanh và rõ vai trò;
- PostgreSQL vẫn giữ metadata và source of truth.

---

## 8. Giai Đoạn 7: Bảo Mật Và Trạng Thái Job

Mục tiêu: làm flow chắc hơn khi trình bày.

Đã bổ sung:

- JWT Bearer token;
- role `admin`/`user`;
- `embedding_status`;
- `embedding_error`;
- queue limit cho access processing;
- chặn đăng ký trùng khuôn mặt bằng duplicate threshold;
- message rõ trong access log.

Kết quả:

- user không gọi được admin API;
- admin thấy embedding thành công/thất bại;
- duplicate face không bị đăng ký thành nhân viên khác;
- access logs giải thích được kết quả.

---

## 9. Giai Đoạn 8: Docker Compose Và Nginx

Mục tiêu: người chấm clone repo và chạy lại được bằng một lệnh.

Đã có:

- Docker Compose full stack;
- Nginx gateway port `8080`;
- frontend-home;
- healthcheck;
- seed service;
- MinIO, Qdrant, Redis, PostgreSQL;
- Prometheus, Grafana, Alertmanager;
- cron-backup.

Kết quả:

```powershell
docker compose up --build -d
```

là đủ để chạy hệ thống chính.

---

## 10. Giai Đoạn 9: CI/CD Và Docker Hub

Mục tiêu: kiểm tra code tự động và publish Docker images.

GitHub Actions có:

- backend tests;
- worker tests;
- frontend builds;
- Docker image builds;
- publish Docker Hub khi push main.

Images chính:

- `deepface-backend`;
- `deepface-worker`;
- `deepface-frontend-user`;
- `deepface-frontend-home`;
- `deepface-frontend-admin`.

GitHub secrets cần có:

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

Kết quả:

- CI bắt lỗi test/build;
- Docker images có tag `latest` và commit SHA;
- Docker Compose/Helm dùng được image đã publish.

---

## 11. Giai Đoạn 10: Monitoring, Backup Và Helm

Mục tiêu: bổ sung lớp vận hành.

Monitoring:

- `/health`;
- `/metrics`;
- Prometheus;
- Alertmanager;
- Grafana dashboard.

Backup:

- `scripts/backup.ps1`;
- `scripts/backup-s3.ps1`;
- `cron-backup`;
- backup PostgreSQL lên MinIO/S3.

Helm:

- chart baseline;
- backend/worker/frontend/database/redis/minio/qdrant templates;
- ingress baseline.

Kết quả:

- có dashboard vận hành;
- có alert rules;
- có backup PostgreSQL;
- có hướng triển khai Kubernetes.

---

## 12. Trạng Thái Hiện Tại

Repo hiện có:

- frontend user/admin/home;
- backend API có auth;
- worker AI dùng DeepFace;
- Redis queue;
- PostgreSQL schema;
- MinIO object storage;
- Qdrant vector search;
- Docker Compose full stack;
- CI build/test/publish image;
- monitoring;
- backup;
- Helm baseline;
- docs trình bày hệ thống.

---

## 13. Hướng Mở Rộng

Các hướng cải thiện tiếp:

1. Lưu nhiều ảnh/embedding cho mỗi employee.
2. Mở rộng bộ ảnh đánh giá accuracy/latency.
3. Bổ sung worker metrics và latency histogram.
4. Bổ sung reindex Qdrant tự động.
5. Bổ sung backup MinIO/Qdrant.
6. Bổ sung Playwright E2E test.
7. Bổ sung Helm Job cho migration/seed.
8. Bổ sung CD lên VPS hoặc Kubernetes.
9. Tối ưu model/detector nếu latency cao.

---

## 14. Checklist Trước Khi Chốt

```powershell
docker compose up --build -d
docker compose ps
Invoke-WebRequest http://localhost:8080/health
.\scripts\smoke-deepface.ps1
.\scripts\test.ps1
```

Kiểm tra Docker Hub:

```powershell
.\scripts\check-dockerhub-readiness.ps1 -Namespace <dockerhub-username> -ImageTag latest
```

Kiểm tra UI:

1. Admin login.
2. Tạo employee.
3. Upload ảnh face.
4. Chờ embedding `success`.
5. User login.
6. Start camera.
7. Quét đúng người -> `granted`.
8. Quét sai/nhiều mặt/không có mặt -> `denied` hoặc `error`.
9. Mở logs/history.
10. Mở Grafana/Prometheus/MinIO/Qdrant nếu cần trình bày lớp vận hành.
