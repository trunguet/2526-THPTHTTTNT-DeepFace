# Setup

Tài liệu này hướng dẫn chuẩn bị môi trường dev và chạy demo DeepFace Access Control.

---

## 1. Yêu Cầu

Cần cài:

- Docker Desktop;
- Git;
- Python 3.12 nếu muốn chạy test ngoài container;
- Node/npm nếu muốn build frontend ngoài container;
- Helm nếu muốn kiểm tra chart Kubernetes.

---

## 2. Chạy Local Bằng Docker

Luồng nhanh cho người mới clone repo:

```powershell
git clone <repo-url>
cd 2526-THPTHTTTNT-DeepFace
docker compose up --build -d
```

Lệnh trên sẽ:

- build backend, worker, frontend;
- chạy PostgreSQL, Redis, MinIO, Qdrant;
- chạy `db-seed` để tạo bảng và seed tài khoản/dữ liệu mẫu;
- chạy Nginx gateway;
- chạy Prometheus, Alertmanager, Grafana;
- chạy `cron-backup`.

Chỉ cần copy `.env.example` thành `.env` khi muốn đổi port, secret hoặc thông tin seed.

---

## 3. URL Chính

| Thành phần | URL |
|---|---|
| Gateway/Home | `http://localhost:8080` |
| User UI | `http://localhost:8080/user/` |
| Admin UI | `http://localhost:8080/admin/` |
| Swagger | `http://localhost:8080/docs` |
| Backend trực tiếp | `http://localhost:8000` |
| MinIO Console | `http://localhost:9001` |
| Qdrant | `http://localhost:6333/dashboard` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |

Tài khoản mặc định:

```text
admin / admin123
user  / user123
```

Grafana mặc định:

```text
admin / admin
```

MinIO mặc định:

```text
minioadmin / minioadmin
```

---

## 4. Kiểm Tra Nhanh

```powershell
docker compose ps
```

Backend health:

```powershell
Invoke-WebRequest http://localhost:8080/health
```

Backend metrics:

```powershell
Invoke-WebRequest http://localhost:8080/metrics
```

---

## 5. Smoke Test AI

Nếu cần xác minh AI runtime trong container:

```powershell
.\scripts\smoke-deepface.ps1
```

Script này kiểm tra:

- worker import được DeepFace;
- tạo embedding thật;
- Qdrant search được vector;
- PostgreSQL access log được cập nhật đúng trạng thái.

---

## 6. Chạy Test

Chạy test tổng hợp:

```powershell
.\scripts\test.ps1
```

Script kiểm tra:

- backend tests;
- worker tests;
- admin frontend build nếu có npm;
- user frontend build nếu có npm.

---

## 7. Dữ Liệu Ảnh Và Vector

MinIO đã nối vào flow upload ảnh employee/access snapshot.

PostgreSQL hiện lưu object key trong cột `image_path` để giữ tương thích schema.

Qdrant đã nối vào flow matching. PostgreSQL vẫn là source of truth cho employee/embedding metadata.

---

## 8. Lỗi Hay Gặp

| Lỗi | Cách xử lý |
|---|---|
| Docker Desktop chưa chạy | Start Docker Desktop rồi chạy lại `docker compose`. |
| Port bị trùng | Kiểm tra các port `5172`, `5173`, `5174`, `8000`, `8080`, `9000`, `9001`, `9090`, `9093`, `3000`. |
| DeepFace lần đầu chậm | Worker cần tải/cache model weight trong volume `deepface_weights`. |
| Webcam không mở được | Trình duyệt cần chạy trên `localhost` hoặc HTTPS và được cấp quyền camera. |
| Worker xử lý chậm | Tăng RAM/CPU Docker Desktop hoặc chạy smoke test riêng thay vì full stack. |
