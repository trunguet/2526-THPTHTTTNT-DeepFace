# Backend API

Tài liệu này mô tả API hiện tại của backend DeepFace Access Control. Mục tiêu là giúp người đọc hiểu nhanh backend cung cấp những endpoint nào, endpoint đó dùng cho màn hình nào, dữ liệu đi vào/đi ra ra sao và luồng nào được xử lý bất đồng bộ qua worker.

Swagger chi tiết có tại:

```text
http://localhost:8000/docs
```

Khi chạy qua Nginx/Docker Compose, backend thường được proxy qua:

```text
http://localhost:8080/api
```

Ví dụ:

```text
http://localhost:8080/api/health
http://localhost:8080/api/auth/login
```

---

## 1. Tổng Quan

Backend dùng FastAPI và chia API thành các nhóm chính:

| Nhóm API | Mục đích |
|---|---|
| `/auth` | Đăng nhập, lấy thông tin user hiện tại. |
| `/employees` | Quản lý nhân viên và ảnh embedding. |
| `/cameras` | Đọc camera/cổng mặc định. Phần tạo/sửa/xóa được giới hạn để giữ dữ liệu camera nhất quán. |
| `/access` | Upload ảnh điểm danh, tạo access check job. |
| `/logs` | Xem lịch sử access log. |
| `/admin` | Trạng thái vận hành, user admin, evaluation report. |
| `/health` | Health check cho Docker/Kubernetes. |
| `/metrics` | Prometheus metrics. |

Luồng AI chính không xử lý nặng trực tiếp trong request API. Backend chỉ:

1. validate request;
2. lưu ảnh vào MinIO;
3. tạo bản ghi trạng thái ban đầu;
4. đẩy job vào Redis;
5. worker xử lý DeepFace/Qdrant sau đó cập nhật database.

Vì vậy các endpoint như `/access/check-image` hoặc `/employees/{id}/face-image` thường trả `202 Accepted` hoặc `201 Created` rất nhanh, còn kết quả AI cuối cùng xem ở log hoặc trạng thái employee.

---

## 2. Authentication Và Role

Hầu hết endpoint cần Bearer token:

```text
Authorization: Bearer <access_token>
```

Có 2 role chính:

| Role | Quyền |
|---|---|
| `admin` | Quản lý nhân viên, xem camera, xem log, xem admin status, quản lý user. |
| `user` | Dùng màn hình access, upload/check ảnh điểm danh, xem thông tin session của chính mình. |

Các endpoint không cần token:

```text
POST /auth/login
GET /health
GET /metrics
```

Lỗi auth thường gặp:

| HTTP code | Ý nghĩa |
|---|---|
| `401` | Thiếu token, token sai hoặc token hết hạn. |
| `403` | Có token nhưng không phải role `admin` khi gọi API admin-only. |

---

## 3. Auth API

### 3.1. `POST /auth/login`

Đăng nhập bằng username/password và nhận Bearer token.

Không cần token.

Request:

```json
{
  "username": "admin",
  "password": "admin123"
}
```

Response:

```json
{
  "access_token": "<jwt-token>",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "created_at": "2026-05-20T10:00:00"
  }
}
```

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `401` | Sai username/password. |

---

### 3.2. `GET /auth/me`

Trả về user hiện tại dựa trên Bearer token.

Cần token.

Response:

```json
{
  "id": 1,
  "username": "admin",
  "role": "admin",
  "created_at": "2026-05-20T10:00:00"
}
```

Endpoint này được frontend dùng để biết user đang đăng nhập là `admin` hay `user`.

---

## 4. Employees API

Nhóm endpoint này dùng cho Admin UI phần quản lý nhân viên.

Tất cả endpoint `/employees` cần role `admin`.

### 4.1. `GET /employees`

Lấy danh sách nhân viên.

Response:

```json
[
  {
    "id": 1,
    "code": "EMP001",
    "name": "Nguyen Van A",
    "department": "Security",
    "status": "active",
    "embedding_status": "success",
    "embedding_error": null,
    "created_at": "2026-05-20T10:00:00"
  }
]
```

Các trạng thái quan trọng:

| Field | Ý nghĩa |
|---|---|
| `status` | `active` hoặc `inactive`. Employee inactive không nên được nhận diện mở cổng. |
| `embedding_status` | Trạng thái tạo vector khuôn mặt. |
| `embedding_error` | Lỗi gần nhất nếu tạo embedding thất bại. |

`embedding_status` có thể là:

| Giá trị | Ý nghĩa |
|---|---|
| `none` | Chưa từng queue embedding. |
| `pending` | Đã upload ảnh/queue job, worker chưa xử lý xong. |
| `success` | Đã tạo embedding và upsert Qdrant thành công. |
| `error` | Tạo embedding thất bại. |

---

### 4.2. `POST /employees`

Tạo nhân viên mới.

Request:

```json
{
  "code": "EMP001",
  "name": "Nguyen Van A",
  "department": "Security",
  "status": "active"
}
```

Response `201 Created`:

```json
{
  "id": 1,
  "code": "EMP001",
  "name": "Nguyen Van A",
  "department": "Security",
  "status": "active",
  "embedding_status": "none",
  "embedding_error": null,
  "created_at": "2026-05-20T10:00:00"
}
```

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `409` | `code` đã tồn tại. |
| `422` | Request thiếu field hoặc field không hợp lệ. |

---

### 4.3. `GET /employees/{employee_id}`

Xem chi tiết một nhân viên.

Response giống `EmployeeRead`.

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `404` | Không tìm thấy employee. |

---

### 4.4. `PUT /employees/{employee_id}`

Cập nhật thông tin nhân viên.

Request có thể gửi một phần:

```json
{
  "name": "Nguyen Van A Updated",
  "department": "AI Lab",
  "status": "active"
}
```

Các field có thể cập nhật:

```text
code, name, department, status
```

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `404` | Không tìm thấy employee. |
| `409` | Đổi sang `code` đã tồn tại. |

---

### 4.5. `DELETE /employees/{employee_id}`

Soft-delete employee.

Backend không xóa cứng record mà đổi:

```text
status = inactive
```

Response:

```text
204 No Content
```

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `404` | Không tìm thấy employee. |

---

### 4.6. `POST /employees/{employee_id}/face-image`

Upload ảnh khuôn mặt cho employee, lưu ảnh vào MinIO và queue job tạo embedding.

Đây là endpoint quan trọng nhất khi đăng ký khuôn mặt nhân viên.

Content type:

```text
multipart/form-data
```

Form field:

| Field | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `file` | image file | Có | Ảnh khuôn mặt dùng để tạo embedding. |

Ảnh hợp lệ:

```text
.jpg, .jpeg, .png, .webp, .bmp
```

Content type hợp lệ:

```text
image/jpeg
image/png
image/webp
image/bmp
```

Giới hạn dung lượng:

```text
5 MB
```

Response `201 Created`:

```json
{
  "object_key": "employee-faces/1/abcd1234.jpg",
  "bucket": "deepface-images",
  "content_type": "image/jpeg",
  "size": 123456,
  "job_id": "embedding-uuid",
  "type": "embedding",
  "employee_id": 1,
  "queue_name": "embedding_jobs",
  "message": "Image uploaded and embedding job queued."
}
```

Sau response này:

1. ảnh đã nằm trong MinIO;
2. Redis có job trong queue `embedding_jobs`;
3. employee chuyển sang `embedding_status = pending`;
4. worker sẽ detect mặt, tạo embedding, lưu PostgreSQL và upsert Qdrant.

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `400` | File rỗng, quá 5 MB, sai extension hoặc sai content type. |
| `404` | Không tìm thấy employee. |

---

### 4.7. `POST /employees/{employee_id}/embedding-jobs`

Queue lại job tạo embedding từ một ảnh đã có sẵn trong MinIO/local path.

Endpoint này hữu ích khi:

- đã upload ảnh trước đó;
- cần tạo lại embedding;
- cần debug/retry worker.

Request:

```json
{
  "image_key": "employee-faces/1/abcd1234.jpg"
}
```

Có thể dùng `image_path` để tương thích ngược:

```json
{
  "image_path": "employee-faces/1/abcd1234.jpg"
}
```

Response `202 Accepted`:

```json
{
  "job_id": "embedding-uuid",
  "type": "embedding",
  "employee_id": 1,
  "image_key": "employee-faces/1/abcd1234.jpg",
  "image_path": "employee-faces/1/abcd1234.jpg",
  "queue_name": "embedding_jobs",
  "message": "Embedding job queued. Worker will process it in background."
}
```

Lưu ý:

- `image_key` là tên object trong MinIO.
- `image_path` còn tồn tại để tránh migration lớn, nhưng trong flow mới thường chứa cùng giá trị với `image_key`.

---

## 5. Cameras API

Camera hiện được vận hành theo hướng read-only. Hệ thống dùng một camera/cổng mặc định để dữ liệu access log nhất quán trong quá trình kiểm thử và trình bày.

### 5.1. `GET /cameras/active-default`

Lấy camera mặc định đang dùng cho User UI.

Cần token `admin` hoặc `user`.

Response:

```json
{
  "id": 1,
  "name": "DeepFace Smoke Camera",
  "location": "Container smoke test",
  "stream_url": null,
  "status": "active",
  "created_at": "2026-05-20T10:00:00"
}
```

Nếu không có camera:

```text
404 No active camera is configured
```

---

### 5.2. `GET /cameras`

Admin xem danh sách camera hiện có.

Cần role `admin`.

Response:

```json
[
  {
    "id": 1,
    "name": "DeepFace Smoke Camera",
    "location": "Container smoke test",
    "stream_url": null,
    "status": "active",
    "created_at": "2026-05-20T10:00:00"
  }
]
```

---

### 5.3. `GET /cameras/{camera_id}`

Admin xem chi tiết một camera.

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `404` | Không tìm thấy camera. |

---

### 5.4. `POST /cameras`, `PUT /cameras/{id}`, `DELETE /cameras/{id}`

Các endpoint này hiện được khóa read-only trong phạm vi phiên bản hiện tại.

Response:

```text
405 Method Not Allowed
```

Detail:

```text
Camera management is read-only in the current version. The system uses a single built-in gate camera.
```

Lý do:

- User UI đang dùng webcam trình duyệt làm nguồn ảnh chính;
- hệ thống ưu tiên một camera mặc định để access log dễ kiểm chứng;
- bảng `cameras` vẫn giữ đủ field để mở rộng sang IP camera/RTSP ở bước sau.

---

## 6. Access API

Nhóm endpoint này phục vụ luồng điểm danh/mở cổng.

Endpoint chính frontend user đang dùng là:

```text
POST /access/check-image
```

### 6.1. `POST /access/snapshots`

Upload ảnh snapshot lên MinIO nhưng chưa tạo access check.

Cần token `admin` hoặc `user`.

Content type:

```text
multipart/form-data
```

Form field:

| Field | Kiểu | Bắt buộc |
|---|---|---|
| `file` | image file | Có |

Response `201 Created`:

```json
{
  "object_key": "access-snapshots/abcd1234.jpg",
  "bucket": "deepface-images",
  "content_type": "image/jpeg",
  "size": 123456
}
```

Endpoint này chỉ upload ảnh. Nếu muốn chạy nhận diện, cần gọi tiếp `/access/check` với `image_key` vừa nhận.

---

### 6.2. `POST /access/check`

Tạo access check từ ảnh đã có sẵn trong MinIO/local path.

Cần token `admin` hoặc `user`.

Request:

```json
{
  "camera_id": 1,
  "image_key": "access-snapshots/abcd1234.jpg"
}
```

Hoặc dùng `image_path` để tương thích ngược:

```json
{
  "camera_id": 1,
  "image_path": "access-snapshots/abcd1234.jpg"
}
```

Response `202 Accepted`:

```json
{
  "log_id": 10,
  "job_id": "access-uuid",
  "status": "processing",
  "employee_id": null,
  "employee_name": null,
  "camera_id": 1,
  "score": null,
  "image_key": "access-snapshots/abcd1234.jpg",
  "image_path": "access-snapshots/abcd1234.jpg",
  "message": "Access check queued. Worker will process it in background.",
  "created_at": "2026-05-20T10:00:00"
}
```

Sau response:

1. backend tạo access log trạng thái `processing`;
2. backend đẩy job vào Redis queue `access_jobs`;
3. worker detect mặt, tạo embedding, search Qdrant;
4. worker cập nhật log thành `granted`, `denied` hoặc `error`.

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `404` | Không tìm thấy camera. |
| `429` | Camera đang có quá nhiều frame `processing`. |
| `422` | Thiếu `image_key`/`image_path` hoặc request sai. |

Queue limit hiện lấy từ:

```text
MAX_PROCESSING_ACCESS_LOGS_PER_CAMERA
```

Default:

```text
3
```

Mục đích là tránh spam quá nhiều frame làm worker bị nghẽn.

---

### 6.3. `POST /access/check-image`

Upload ảnh snapshot và tạo access check trong cùng một request.

Đây là endpoint chính của User UI.

Cần token `admin` hoặc `user`.

Content type:

```text
multipart/form-data
```

Form field:

| Field | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `camera_id` | int | Có | ID camera/cổng đang check. |
| `file` | image file | Có | Ảnh snapshot từ webcam. |

Response `202 Accepted`:

```json
{
  "log_id": 11,
  "job_id": "access-uuid",
  "status": "processing",
  "employee_id": null,
  "employee_name": null,
  "camera_id": 1,
  "score": null,
  "image_key": "access-snapshots/abcd1234.jpg",
  "image_path": "access-snapshots/abcd1234.jpg",
  "message": "Image uploaded and access check queued.",
  "created_at": "2026-05-20T10:00:00"
}
```

Các trạng thái cuối cùng:

| Status | Ý nghĩa |
|---|---|
| `processing` | Backend đã nhận ảnh, worker chưa xử lý xong. |
| `granted` | Nhận diện được employee active và score đạt ngưỡng. |
| `denied` | Có mặt nhưng không match đủ ngưỡng hoặc không có candidate phù hợp. |
| `error` | Ảnh lỗi, không có mặt, nhiều mặt, DeepFace lỗi, MinIO/Qdrant lỗi. |

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `400` | Ảnh upload không hợp lệ. |
| `404` | Camera không tồn tại. |
| `429` | Quá nhiều frame đang processing cho camera đó. |

---

## 7. Logs API

### 7.1. `GET /logs`

Lấy danh sách access logs mới nhất trước.

Cần token `admin` hoặc `user`.

Response:

```json
[
  {
    "id": 10,
    "employee_id": 1,
    "employee_name": "Nguyen Van A",
    "camera_id": 1,
    "status": "granted",
    "score": 0.86,
    "image_path": "access-snapshots/abcd1234.jpg",
    "message": "Access granted.",
    "created_at": "2026-05-20T10:00:00"
  }
]
```

Thứ tự sắp xếp:

```text
created_at desc, id desc
```

Lưu ý:

- API hiện trả danh sách log theo thứ tự mới nhất trước.
- Frontend chia trang ở UI để bảng lịch sử dễ đọc hơn.
- `image_path` trong flow mới thường là MinIO object key.

---

## 8. Admin API

Nhóm endpoint này cần role `admin`.

### 8.1. `GET /admin/status`

Trả về trạng thái vận hành cơ bản.

Response:

```json
{
  "status": "ok",
  "database": "ok",
  "database_error": null,
  "redis": "ok",
  "redis_error": null,
  "queue_lengths": {
    "embedding_jobs": 0,
    "access_jobs": 0
  }
}
```

Ý nghĩa:

| Field | Ý nghĩa |
|---|---|
| `status` | `ok` nếu database và Redis đều ổn, ngược lại là `degraded`. |
| `database` | Trạng thái kết nối PostgreSQL. |
| `redis` | Trạng thái kết nối Redis. |
| `queue_lengths.embedding_jobs` | Số job embedding đang chờ. |
| `queue_lengths.access_jobs` | Số job access đang chờ. |

Endpoint này dùng cho Admin Settings/Monitoring UI.

---

### 8.2. `GET /admin/evaluation-report`

Trả về báo cáo đánh giá accuracy/latency nhỏ được lưu trong repo.

Nguồn file:

```text
backend/app/data/evaluation_report.json
```

Response ví dụ:

```json
{
  "updated_at": "2026-05-20",
  "source": "Internal controlled access evaluation",
  "dataset": {
    "subjects": 4,
    "registered_subjects": 3,
    "impostor_subjects": 1,
    "total_cases": 28
  },
  "metrics": {
    "correct": 23,
    "wrong": 2,
    "rejected": 3,
    "average_access_seconds": 4.8
  }
}
```

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `404` | Không có file report. |
| `500` | File JSON bị lỗi format. |

---

### 8.3. `GET /admin/users`

Lấy danh sách user hệ thống.

Response:

```json
[
  {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "created_at": "2026-05-20T10:00:00"
  }
]
```

Backend không trả `password_hash`.

---

### 8.4. `POST /admin/users`

Tạo user mới.

Request:

```json
{
  "username": "guard",
  "password": "guard123",
  "role": "user"
}
```

Role hợp lệ:

```text
admin, user
```

Response `201 Created`:

```json
{
  "id": 2,
  "username": "guard",
  "role": "user",
  "created_at": "2026-05-20T10:00:00"
}
```

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `409` | Username đã tồn tại. |

---

### 8.5. `PUT /admin/users/{user_id}`

Cập nhật username, role hoặc password.

Request có thể gửi một phần:

```json
{
  "role": "admin"
}
```

Hoặc:

```json
{
  "username": "new_guard",
  "password": "new-password"
}
```

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `404` | Không tìm thấy user. |
| `409` | Username mới đã tồn tại. |

---

### 8.6. `DELETE /admin/users/{user_id}`

Xóa user.

Response:

```text
204 No Content
```

Lỗi:

| HTTP code | Khi nào |
|---|---|
| `400` | Admin đang đăng nhập cố xóa chính mình. |
| `404` | Không tìm thấy user. |

---

## 9. Health Và Metrics

### 9.1. `GET /health`

Không cần token.

Dùng cho Docker/Kubernetes health check.

Response khi ổn:

```json
{
  "status": "ok",
  "service": "backend",
  "environment": "dev",
  "database": "ok",
  "redis": "ok"
}
```

Response khi lỗi dependency:

```json
{
  "status": "error",
  "service": "backend",
  "environment": "dev",
  "database": "error",
  "database_error": "OperationalError",
  "redis": "ok",
  "redis_error": null
}
```

Nếu database hoặc Redis lỗi, HTTP status là:

```text
503 Service Unavailable
```

---

### 9.2. `GET /metrics`

Không cần token.

Trả Prometheus text format.

Metric chính:

```text
deepface_backend_up
deepface_database_up
deepface_redis_up
deepface_queue_length{queue="embedding_jobs"}
deepface_queue_length{queue="access_jobs"}
deepface_access_logs_total{status="granted"}
deepface_access_logs_total{status="denied"}
deepface_access_logs_total{status="error"}
deepface_access_logs_total{status="processing"}
```

Ví dụ:

```text
# HELP deepface_backend_up Backend process health.
# TYPE deepface_backend_up gauge
deepface_backend_up 1
deepface_database_up 1
deepface_redis_up 1
deepface_queue_length{queue="embedding_jobs"} 0
deepface_queue_length{queue="access_jobs"} 0
```

Endpoint này được Prometheus scrape để hiển thị dashboard Grafana và cảnh báo.

---

## 10. Upload Ảnh Và MinIO

Các endpoint upload ảnh:

```text
POST /employees/{employee_id}/face-image
POST /access/snapshots
POST /access/check-image
```

Quy tắc validate chung:

| Điều kiện | Giá trị |
|---|---|
| Extension | `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp` |
| Content type | `image/jpeg`, `image/png`, `image/webp`, `image/bmp` |
| Dung lượng tối đa | 5 MB |
| File rỗng | Bị reject |

Prefix object key:

| Loại ảnh | Prefix |
|---|---|
| Ảnh employee | `employee-faces/{employee_id}/...` |
| Ảnh access | `access-snapshots/...` |

Ví dụ object key:

```text
employee-faces/1/0d9a8f.jpg
access-snapshots/ab12cd.jpg
```

MinIO bucket default:

```text
deepface-images
```

---

## 11. Redis Queue

Backend dùng Redis queue để tránh request bị chậm vì DeepFace.

| Queue | Ai tạo job | Ai xử lý | Mục đích |
|---|---|---|---|
| `embedding_jobs` | `/employees/{id}/face-image`, `/employees/{id}/embedding-jobs` | worker | Tạo vector khuôn mặt nhân viên. |
| `access_jobs` | `/access/check`, `/access/check-image` | worker | Kiểm tra ảnh access. |

Khi API trả `processing`, điều đó nghĩa là:

- backend đã nhận request;
- job đã vào Redis;
- worker sẽ xử lý sau;
- kết quả cuối cùng xem qua `/logs`.

---

## 12. Các Mã Lỗi Thường Gặp

| HTTP code | Ý nghĩa |
|---|---|
| `400` | Request hợp lệ về format nhưng dữ liệu không dùng được, ví dụ ảnh lỗi. |
| `401` | Thiếu/sai token. |
| `403` | Không đủ quyền admin. |
| `404` | Không tìm thấy resource. |
| `405` | Camera create/update/delete đang được giới hạn read-only trong phiên bản hiện tại. |
| `409` | Trùng username hoặc employee code. |
| `422` | Body/form thiếu field hoặc sai kiểu dữ liệu. |
| `429` | Queue access của camera đang đầy. |
| `500` | Lỗi server, ví dụ evaluation JSON hỏng. |
| `503` | Health check thấy database hoặc Redis lỗi. |

---

## 13. Luồng API Chính Cho Demo

### 13.1. Đăng nhập admin

```text
POST /auth/login
```

Lấy token admin.

### 13.2. Tạo employee

```text
POST /employees
```

### 13.3. Upload ảnh employee

```text
POST /employees/{employee_id}/face-image
```

Backend lưu ảnh vào MinIO và queue `embedding_jobs`.

### 13.4. Chờ embedding thành công

```text
GET /employees
```

Kiểm tra:

```text
embedding_status = success
```

### 13.5. User check access

```text
GET /cameras/active-default
POST /access/check-image
```

### 13.6. Xem kết quả

```text
GET /logs
```

Kết quả mong đợi:

```text
granted / denied / error
```

---

## 14. Tóm Tắt Ngắn

API backend hiện tại làm 4 việc chính:

1. Auth bằng JWT Bearer token.
2. Quản lý employee và upload ảnh đăng ký.
3. Nhận ảnh access, queue job để worker xử lý AI.
4. Cung cấp log, health, metrics và admin report để phục vụ vận hành/monitoring.

Điểm quan trọng nhất: DeepFace không chạy trực tiếp trong request chính. Backend nhận ảnh và queue job, worker xử lý phía sau, kết quả cuối cùng nằm trong `access_logs` và được đọc qua `/logs`.
