# Use Case

Tài liệu này mô tả use case chính của DeepFace Access Control theo góc nhìn người dùng, admin và người vận hành. Nội dung dùng để giải thích hệ thống giải quyết bài toán gì, ai dùng, dùng như thế nào và kết quả mong đợi là gì.

---

## 1. Tổng Quan Use Case

Hệ thống nhận diện khuôn mặt để kiểm soát ra/vào.

Bối cảnh:

- công ty, phòng lab hoặc khu vực cần kiểm soát ra/vào;
- nhân viên được admin đăng ký khuôn mặt trước;
- khi nhân viên đứng trước camera/webcam, hệ thống chụp snapshot, nhận diện và quyết định cho phép/từ chối.

Mục tiêu chính:

- đăng ký nhân viên và ảnh khuôn mặt;
- tạo embedding khuôn mặt và lưu vào vector database;
- kiểm tra khuôn mặt từ camera/webcam;
- ghi access logs;
- có dashboard admin;
- chạy được bằng Docker Compose;
- có monitoring, backup và CI/CD baseline.

---

## 2. Actor

| Actor | Vai trò | Giao diện |
|---|---|---|
| Admin | Quản lý nhân viên, user, logs và cấu hình hệ thống | Admin Console |
| Employee/User | Quét khuôn mặt để kiểm tra ra/vào và xem lịch sử | User Terminal |
| Operator/DevOps | Chạy stack, monitor, backup, kiểm tra CI/Helm | CLI, Docker, Grafana |

---

## 3. UC-01: Đăng Nhập

### Mục tiêu

Admin/user đăng nhập để lấy access token.

### Luồng chính

1. Người dùng mở User UI hoặc Admin UI.
2. Nhập username/password.
3. Frontend gọi `POST /auth/login`.
4. Backend xác thực mật khẩu.
5. Backend trả JWT token và thông tin user.
6. Frontend lưu token và gửi kèm các request sau.

### Kết quả

- đăng nhập thành công;
- user vào đúng giao diện;
- token được gửi trong header `Authorization`.

### Luồng lỗi

| Trường hợp | Kết quả |
|---|---|
| Sai username/password | API trả `401`, UI hiện lỗi đăng nhập |
| Thiếu token | API trả `401` |
| User gọi admin API | API trả `403` |

---

## 4. UC-02: Admin Quản Lý Nhân Viên

### Mục tiêu

Admin tạo, sửa, xóa và xem danh sách nhân viên.

### Luồng chính

1. Admin đăng nhập.
2. Admin mở Employees.
3. Admin tạo employee với code, name, department.
4. Backend lưu employee vào PostgreSQL.
5. Employee xuất hiện trong danh sách.

### Kết quả

- employee mới được tạo;
- code employee là duy nhất;
- employee có `status=active`;
- `embedding_status=none` trước khi upload ảnh.

### Luồng lỗi

| Trường hợp | Kết quả |
|---|---|
| Trùng code | API trả `409` |
| Thiếu field bắt buộc | API trả `422` |
| User role gọi API employee | API trả `403` |

---

## 5. UC-03: Admin Đăng Ký Khuôn Mặt Employee

### Mục tiêu

Admin upload ảnh khuôn mặt cho employee để worker tạo embedding và lưu vào Qdrant.

### Luồng chính

1. Admin chọn employee.
2. Admin upload ảnh khuôn mặt.
3. Backend validate ảnh.
4. Backend lưu ảnh vào MinIO.
5. Backend queue job vào `embedding_jobs`.
6. Employee chuyển sang `embedding_status=pending`.
7. Worker tải ảnh từ MinIO về temp file.
8. Worker detect khuôn mặt bằng DeepFace.
9. Worker tạo embedding.
10. Worker kiểm tra trùng khuôn mặt trong Qdrant.
11. Worker lưu embedding vào PostgreSQL.
12. Worker upsert vector vào Qdrant.
13. Employee chuyển sang `embedding_status=success`.

### Kết quả

- employee có embedding sẵn sàng;
- ảnh nguồn được lưu trong MinIO;
- vector được lưu trong PostgreSQL và Qdrant;
- admin thấy trạng thái embedding trên UI.

### Luồng lỗi

| Trường hợp | Kết quả |
|---|---|
| Không có mặt trong ảnh | `embedding_status=error` và có message |
| Nhiều mặt trong ảnh | job bị từ chối để tránh gán sai người |
| Ảnh trùng với employee khác | worker báo duplicate face |
| MinIO/Qdrant lỗi | worker ghi `embedding_status=error` |

---

## 6. UC-04: User Quét Mặt Để Check Access

### Mục tiêu

User dùng webcam/camera để quét khuôn mặt và nhận kết quả ra/vào.

### Điều kiện trước

- user đã đăng nhập;
- có camera mặc định;
- employee đã có embedding `success`;
- worker đang chạy.

### Luồng chính

1. User mở User UI.
2. User bấm Start camera.
3. Frontend chụp snapshot theo interval.
4. Frontend gọi `POST /access/check-image`.
5. Backend validate ảnh.
6. Backend upload ảnh vào MinIO.
7. Backend tạo access log `processing`.
8. Backend queue job vào `access_jobs`.
9. Worker tải ảnh từ MinIO.
10. Worker detect khuôn mặt.
11. Worker tạo embedding.
12. Worker search Qdrant.
13. Worker verify employee trong PostgreSQL.
14. Worker so score với threshold.
15. Worker cập nhật access log.
16. UI hiển thị kết quả.

### Kết quả

| Status | Ý nghĩa |
|---|---|
| `granted` | Match employee active và đủ threshold |
| `denied` | Có mặt nhưng không match đủ threshold |
| `error` | Ảnh không hợp lệ, không có mặt, nhiều mặt hoặc pipeline lỗi |

---

## 7. UC-05: Admin Xem Access Logs

### Mục tiêu

Admin xem lịch sử ra/vào.

### Luồng chính

1. Admin mở Access Logs.
2. Frontend gọi `GET /logs`.
3. Backend trả danh sách log mới nhất trước.
4. UI hiển thị status, camera, employee, score, image path, created time.

### Kết quả

- log mới nhất xuất hiện sau khi worker xử lý;
- có thể phân biệt `granted`, `denied`, `error`, `processing`;
- UI có phân trang để bảng không quá dài.

---

## 8. UC-06: Admin Quản Lý Camera

### Mục tiêu

Hiển thị camera/cổng được dùng cho access check.

### Luồng hiện tại

1. Admin mở Cameras.
2. Backend trả danh sách camera hiện có.
3. UI hiển thị camera mặc định.
4. Tạo/sửa/xóa camera được giới hạn read-only trong phiên bản hiện tại.

### Lý do thiết kế

- User UI dùng webcam trình duyệt làm nguồn ảnh chính.
- Một camera mặc định giúp access logs nhất quán.
- Schema vẫn giữ `stream_url`, `location`, `status` để mở rộng sang camera IP/RTSP.

---

## 9. UC-07: Admin Quản Lý Users

### Mục tiêu

Admin tạo/sửa/xóa user hệ thống.

### Luồng chính

1. Admin mở Users.
2. Admin tạo tài khoản mới.
3. Backend hash password.
4. Backend lưu user vào PostgreSQL.
5. User mới đăng nhập được.

### Rule quan trọng

- username unique;
- role là `admin` hoặc `user`;
- admin không được xóa chính mình.

---

## 10. UC-08: Operator Chạy Và Kiểm Tra Hệ Thống

### Mục tiêu

Người chấm hoặc thành viên nhóm clone repo và chạy lại hệ thống bằng Docker.

### Luồng chính

```powershell
git clone <repo-url>
cd 2526-THPTHTTTNT-DeepFace
docker compose up --build -d
```

Kiểm tra:

```powershell
docker compose ps
Invoke-WebRequest http://localhost:8080/health
```

Kết quả:

- stack chạy được;
- backend healthy;
- frontend mở được;
- worker xử lý queue;
- MinIO/Qdrant/Redis/PostgreSQL chạy đúng.

---

## 11. UC-09: Monitoring Và Backup

### Monitoring

Operator mở:

```text
http://localhost:9090
http://localhost:3000
```

Kiểm tra:

- backend up;
- database up;
- Redis up;
- queue length;
- access logs by status.

### Backup

Chạy:

```powershell
docker compose exec cron-backup /usr/local/bin/backup.sh
```

Kiểm tra:

```powershell
docker compose exec cron-backup aws s3 ls s3://deepface-images/deepface-db-backups/ --endpoint-url http://minio:9000
```

Kết quả:

- có backup `postgres.sql`;
- có `manifest.txt`;
- backup lưu trong MinIO/S3-compatible storage.

---

## 12. Mapping Use Case Với Yêu Cầu Đề Bài

| Yêu cầu | Use case / thành phần |
|---|---|
| Nhận diện khuôn mặt realtime | UC-04 User quét mặt bằng webcam/snapshot interval |
| Frontend người dùng | `frontend/user` |
| Frontend admin | `frontend/admin` |
| Backend API | FastAPI backend |
| Database | PostgreSQL |
| Queue xử lý nền | Redis + worker |
| AI model | DeepFace pipeline |
| Object storage | MinIO |
| Vector database | Qdrant |
| Docker Compose | `docker-compose.yml` |
| CI/CD | GitHub Actions + Docker Hub |
| Monitoring | Prometheus + Grafana + Alertmanager |
| Backup | `cron-backup`, backup scripts |
| Kubernetes baseline | Helm chart |

---

## 13. Phạm Vi Hiện Tại Và Hướng Mở Rộng

Các hướng mở rộng:

- Playwright E2E test trên browser;
- nhiều ảnh/embedding cho mỗi employee;
- worker metrics riêng;
- backup MinIO/Qdrant;
- Helm TLS/HPA/resource limits/migration job;
- phân quyền log chi tiết hơn theo user/camera;

---

## 14. Tóm Tắt

Use case chính:

```text
Admin đăng ký employee + ảnh khuôn mặt
-> Worker tạo embedding
-> User quét mặt
-> Worker nhận diện
-> Access log cập nhật granted/denied/error
```

Hệ thống không chỉ có AI model, mà có đầy đủ các lớp cần cho một hệ thống AI engineering: API, UI, queue, worker, database, object storage, vector search, monitoring, backup, CI/CD và Helm baseline.
