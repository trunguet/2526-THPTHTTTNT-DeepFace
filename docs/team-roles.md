# Phân Công Thành Viên Và Phạm Vi Phối Hợp

Tài liệu này trình bày cách nhóm phân công công việc theo module trong hệ thống
`DeepFace Access Control`. Mỗi thành viên có một phần phụ trách chính để đảm bảo
trách nhiệm rõ ràng, đồng thời tham gia các điểm kết nối với module khác vì sản
phẩm được xây dựng theo một luồng end-to-end:

```text
Frontend -> Backend API -> Redis Queue -> AI Worker -> PostgreSQL / MinIO / Qdrant
                                      |
                              Monitoring / Demo / QA
```

Vì vậy, khi trình bày hoặc trả lời câu hỏi, thành viên phụ trách module chính
sẽ trả lời trước; thành viên liên quan có thể bổ sung ở phần giao tiếp dữ liệu,
tích hợp, kiểm thử hoặc vận hành mà mình đã trực tiếp tham gia.

---

## 1. Bảng Phân Công Tổng Quan

| Thành viên | Phụ trách chính | Nội dung chính | Các phần phối hợp nắm được |
| --- | --- | --- | --- |
| Thành viên 1 | Backend/API | Auth, role, employees, access, logs, upload ảnh, health/metrics, database schema | Nắm payload frontend gửi lên, cách tạo Redis job cho worker, object key lưu trên MinIO và metric để DevOps theo dõi |
| Thành viên 2 | AI/Worker | DeepFace, detector, embedding, Qdrant search, threshold, queue jobs, xử lý `granted`/`denied`/`error` | Nắm API tạo job và access log, cấu trúc bảng embedding/log, luồng UI nhận kết quả, smoke test trong Docker |
| Thành viên 3 | Frontend | Home, User Terminal, Admin Console, webcam/snapshot, trạng thái UI, lỗi người dùng | Nắm endpoint auth/access/employees/logs, trạng thái worker trả về, cách gateway Nginx route UI và API |
| Thành viên 4 | DevOps/Docs/QA | Docker Compose, Nginx, MinIO, Redis, monitoring, CI/CD, backup, README, demo checklist | Nắm luồng backend-worker để cấu hình service, cách UI gọi API qua gateway, kịch bản kiểm thử kết quả AI |

---

## 2. Thành Viên 1 - Backend/API

### Phụ trách chính

- Xây dựng FastAPI backend và các router chính: `/auth`, `/employees`,
  `/cameras`, `/access`, `/logs`, `/admin`.
- Xử lý đăng nhập JWT Bearer token và phân quyền `admin` / `user`.
- Thiết kế và làm việc với database schema cho `users`, `employees`,
  `cameras`, `face_embeddings`, `access_logs`.
- Nhận file ảnh từ frontend, validate upload và lưu ảnh vào MinIO.
- Tạo access log ban đầu, đưa job embedding/access vào Redis queue.
- Cung cấp `/health`, `/metrics` để theo dõi trạng thái backend, database,
  Redis và queue.

### Phối hợp trực tiếp

- Với Thành viên 2: thống nhất cấu trúc job, `image_key`, `log_id`,
  `employee_id`, và các status `processing`, `granted`, `denied`, `error`.
- Với Thành viên 3: thống nhất request/response API, authentication token,
  upload form-data và thông điệp lỗi hiển thị trên UI.
- Với Thành viên 4: cung cấp health endpoint, metrics và biến môi trường để
  chạy backend trong Docker Compose/Nginx.

---

## 3. Thành Viên 2 - AI/Worker

### Phụ trách chính

- Xây dựng worker lắng nghe hai hàng đợi Redis: `embedding_jobs` và
  `access_jobs`.
- Tích hợp DeepFace để detect khuôn mặt và tạo embedding bằng model
  `Facenet512`.
- Sử dụng detector, xử lý trường hợp không có mặt hoặc có nhiều mặt trong ảnh.
- Lưu và tìm kiếm vector khuôn mặt trên Qdrant.
- Cài đặt ngưỡng so khớp và kiểm tra trùng khuôn mặt khi đăng ký employee.
- Cập nhật kết quả về access log và trạng thái embedding:
  `success`, `error`, `granted`, `denied`.

### Phối hợp trực tiếp

- Với Thành viên 1: nhận job từ backend, đọc/ghi đúng database record và trả
  lại kết quả để API cung cấp cho UI.
- Với Thành viên 3: thống nhất ý nghĩa các trạng thái hiển thị trên terminal,
  đặc biệt là trường hợp frame đang xử lý, bị từ chối hoặc bị lỗi.
- Với Thành viên 4: kiểm tra worker container, model weights, MinIO/Qdrant,
  smoke test AI và các trường hợp demo.

---

## 4. Thành Viên 3 - Frontend

### Phụ trách chính

- Xây dựng trang Home để chọn luồng User hoặc Admin.
- Xây dựng User Terminal: login, webcam/snapshot, gửi ảnh kiểm tra,
  hiển thị result card, history và session.
- Xây dựng Admin Console: dashboard, employee management, upload face image,
  access logs, user management và settings/report.
- Xử lý trạng thái UI: loading, processing, success, denied, error và lỗi API.
- Kết nối frontend với backend bằng token và các API nghiệp vụ.

### Phối hợp trực tiếp

- Với Thành viên 1: kiểm thử endpoint, payload, token, upload image và hiển
  thị response của backend.
- Với Thành viên 2: xác định cách hiển thị trạng thái nhận diện và thông điệp
  khi AI không tìm thấy mặt, nhiều mặt hoặc không đạt threshold.
- Với Thành viên 4: cấu hình base path `/user/`, `/admin/`, API base URL và
  truy cập giao diện qua Nginx gateway khi demo.

---

## 5. Thành Viên 4 - DevOps/Docs/QA

### Phụ trách chính

- Cấu hình Docker Compose để khởi động full stack: frontend, backend, worker,
  PostgreSQL, Redis, MinIO, Qdrant và monitoring.
- Cấu hình Nginx gateway điều hướng `/`, `/user/`, `/admin/`, `/api/`,
  `/health`, `/metrics`.
- Cấu hình các dịch vụ hạ tầng: MinIO lưu ảnh, Redis queue, Prometheus,
  Grafana và Alertmanager.
- Tham gia CI/CD, Docker images, backup và Helm baseline cho triển khai.
- Viết/cập nhật README, tài liệu setup, kiến trúc, checklist demo.
- Chuẩn bị và kiểm thử kịch bản end-to-end cùng bộ ảnh mẫu.

### Phối hợp trực tiếp

- Với Thành viên 1: cấu hình database, API, health/metrics, seed data và
  routing backend qua Nginx.
- Với Thành viên 2: khởi động worker, Redis/MinIO/Qdrant, smoke test AI và
  theo dõi lỗi xử lý nền.
- Với Thành viên 3: build/deploy frontend, base path và xác minh luồng demo
  trên gateway.

---

## 6. Các Điểm Giao Thoa Bắt Buộc

Đây là các hạng mục không thuộc riêng một người, mà cần ít nhất hai thành viên
cùng hiểu và cùng kiểm thử:

| Hạng mục liên kết | Thành viên phụ trách chính | Thành viên nắm để hỗ trợ | Lý do |
| --- | --- | --- | --- |
| Login và phân quyền | Thành viên 1 | Thành viên 3 | Backend cấp token, frontend lưu token và điều hướng UI |
| Đăng ký employee bằng ảnh | Thành viên 1 | Thành viên 2, Thành viên 3 | UI upload ảnh, API tạo job, worker tạo embedding |
| Check access từ webcam | Thành viên 3 | Thành viên 1, Thành viên 2 | UI chụp ảnh, API queue job, AI xử lý kết quả |
| Kết quả `granted`/`denied`/`error` | Thành viên 2 | Thành viên 1, Thành viên 3 | Worker quyết định, DB/API lưu kết quả, UI hiển thị |
| MinIO và Qdrant | Thành viên 2, Thành viên 4 | Thành viên 1 | Backend lưu object key, worker tải ảnh và index/search vector |
| Health, metrics và dashboard | Thành viên 4 | Thành viên 1 | Backend expose dữ liệu, monitoring thu thập và hiển thị |
| Docker demo end-to-end | Thành viên 4 | Thành viên 1, 2, 3 | Tất cả module phải chạy và kết nối đúng với nhau |
| Kiểm thử tình huống mẫu | Thành viên 4 | Thành viên 2, Thành viên 3 | QA chuẩn bị case, AI giải thích kết quả, UI thể hiện kết quả |