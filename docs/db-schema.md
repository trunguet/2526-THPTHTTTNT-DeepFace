# Database Schema

Tài liệu này mô tả schema PostgreSQL hiện tại của DeepFace Access Control. PostgreSQL là database nghiệp vụ chính, còn MinIO và Qdrant là các hệ thống hỗ trợ bên ngoài database.

---

## 1. Vai Trò Của PostgreSQL

PostgreSQL lưu dữ liệu chuẩn của hệ thống:

- tài khoản đăng nhập;
- hồ sơ nhân viên;
- camera/cổng;
- metadata embedding khuôn mặt;
- lịch sử access check.

Các dữ liệu không lưu trực tiếp trong PostgreSQL:

| Dữ liệu | Nơi lưu chính |
|---|---|
| File ảnh upload | MinIO/S3 |
| Vector search index | Qdrant |
| Queue job tạm thời | Redis |
| Model weights DeepFace | Docker volume `deepface_weights` |

PostgreSQL vẫn lưu `vector` trong bảng `face_embeddings` như source of truth, còn Qdrant dùng để search nhanh.

---

## 2. Sơ Đồ Quan Hệ

```text
users

employees 1 ---- n face_embeddings
employees 1 ---- n access_logs

cameras   1 ---- n access_logs
```

Quan hệ chính:

- một employee có thể có nhiều face embedding;
- một employee có thể có nhiều access log;
- một camera có thể có nhiều access log;
- access log có thể không có employee nếu bị denied/error;
- access log có thể không có camera trong vài flow cũ/manual, nhưng flow hiện tại thường có camera.

---

## 3. Cách Tạo Bảng

Repo hiện dùng SQLAlchemy `Base.metadata.create_all()` cho MVP/dev.

File chính:

```text
backend/app/db/init_db.py
```

Lệnh tạo bảng:

```powershell
docker compose run --rm backend python -m app.db.init_db
```

Trong Docker Compose, service `db-seed` cũng gọi seed và đảm bảo bảng tồn tại:

```text
python -m app.db.seed
```

Lưu ý: repo hiện dùng cơ chế SQLAlchemy `create_all()` kết hợp các hàm `ensure_*` để bổ sung cột khi database cũ thiếu cột mới.

Các cột được đảm bảo thêm nếu thiếu:

```text
employees.embedding_status
employees.embedding_error
face_embeddings.source_image_key
access_logs.message
```

---

## 4. Bảng `users`

Lưu tài khoản đăng nhập cho Admin UI và User UI.

SQLAlchemy model:

```text
backend/app/models/user.py
```

| Cột | Kiểu | Null | Index/constraint | Ý nghĩa |
|---|---|---|---|---|
| `id` | integer | no | primary key, index | ID user. |
| `username` | varchar(100) | no | unique, index | Tên đăng nhập. |
| `password_hash` | varchar(255) | no |  | Mật khẩu đã hash. Không lưu plain text. |
| `role` | varchar(50) | no | default `user` | Quyền user. |
| `created_at` | timestamptz | no | server default `now()` | Thời điểm tạo. |

Role hiện dùng:

| Role | Quyền |
|---|---|
| `admin` | Quản lý employee, users, logs, settings. |
| `user` | Dùng màn hình access/check điểm danh. |

Seed mặc định:

| Username | Role | Password default |
|---|---|---|
| `admin` | `admin` | `admin123` |
| `user` | `user` | `user123` |

Có thể đổi bằng biến môi trường:

```text
SEED_ADMIN_USERNAME
SEED_ADMIN_PASSWORD
SEED_USER_USERNAME
SEED_USER_PASSWORD
```

---

## 5. Bảng `employees`

Lưu hồ sơ nhân viên và trạng thái embedding.

SQLAlchemy model:

```text
backend/app/models/employee.py
```

| Cột | Kiểu | Null | Index/constraint | Ý nghĩa |
|---|---|---|---|---|
| `id` | integer | no | primary key, index | ID employee. |
| `code` | varchar(50) | no | unique, index | Mã nhân viên. |
| `name` | varchar(150) | no | index | Tên hiển thị. |
| `department` | varchar(150) | yes |  | Phòng ban. |
| `status` | varchar(50) | no | index, default `active` | Trạng thái nhân viên. |
| `embedding_status` | varchar(50) | no | index, default/server default `none` | Trạng thái tạo embedding. |
| `embedding_error` | varchar(1000) | yes |  | Lỗi embedding gần nhất. |
| `created_at` | timestamptz | no | server default `now()` | Thời điểm tạo. |

`status`:

| Giá trị | Ý nghĩa |
|---|---|
| `active` | Employee còn hiệu lực, có thể được nhận diện. |
| `inactive` | Employee bị vô hiệu hóa hoặc đã nghỉ. |

`embedding_status`:

| Giá trị | Ý nghĩa |
|---|---|
| `none` | Chưa upload/queue embedding. |
| `pending` | Đã queue job, worker chưa xử lý xong. |
| `success` | Worker đã tạo embedding và upsert Qdrant thành công. |
| `error` | Worker xử lý lỗi. Xem `embedding_error`. |

Quan hệ:

```text
employees.id -> face_embeddings.employee_id
employees.id -> access_logs.employee_id
```

Khi xóa employee qua API, repo dùng soft-delete:

```text
status = inactive
```

Không xóa cứng để giữ lịch sử access log.

---

## 6. Bảng `cameras`

Lưu thông tin camera/cổng.

SQLAlchemy model:

```text
backend/app/models/camera.py
```

| Cột | Kiểu | Null | Index/constraint | Ý nghĩa |
|---|---|---|---|---|
| `id` | integer | no | primary key, index | ID camera. |
| `name` | varchar(150) | no | index | Tên camera/cổng. |
| `location` | varchar(255) | yes |  | Vị trí. |
| `stream_url` | text | yes |  | URL stream nếu có. |
| `status` | varchar(50) | no | index, default `active` | Trạng thái camera. |
| `created_at` | timestamptz | no | server default `now()` | Thời điểm tạo. |

`status`:

| Giá trị | Ý nghĩa |
|---|---|
| `active` | Camera/cổng đang dùng. |
| `inactive` | Camera/cổng không dùng. |

Quan hệ:

```text
cameras.id -> access_logs.camera_id
```

Lưu ý hiện tại:

- Admin UI đã chuyển camera management sang read-only.
- Seed hiện ưu tiên một camera chính đầu tiên.
- Nếu có camera thừa từ dữ liệu cũ, seed sẽ chuyển access log về camera chính rồi xóa camera thừa.

---

## 7. Bảng `face_embeddings`

Lưu vector khuôn mặt của employee.

SQLAlchemy model:

```text
backend/app/models/face_embedding.py
```

| Cột | Kiểu | Null | Index/constraint | Ý nghĩa |
|---|---|---|---|---|
| `id` | integer | no | primary key, index | ID embedding. |
| `employee_id` | integer | no | foreign key, index | Employee sở hữu embedding. |
| `vector` | json/jsonb tùy dialect | no |  | Vector embedding dạng list float. |
| `model_name` | varchar(100) | no |  | Tên model tạo vector. |
| `source_image_key` | text | yes |  | Object key MinIO/local path của ảnh nguồn. |
| `created_at` | timestamptz | no | server default `now()` | Thời điểm tạo. |

Vai trò:

- lưu vector như source of truth;
- lưu model name để tránh trộn embedding giữa nhiều model;
- lưu `source_image_key` để biết embedding được tạo từ ảnh nào;
- hỗ trợ reindex Qdrant về sau.

Quan hệ:

```text
face_embeddings.employee_id -> employees.id
```

Khi employee bị xóa cứng ở ORM, relationship có:

```text
cascade="all, delete-orphan"
```

Nhưng API hiện ưu tiên soft-delete employee nên embedding thường vẫn được giữ.

---

## 8. Bảng `access_logs`

Lưu lịch sử check access.

SQLAlchemy model:

```text
backend/app/models/access_log.py
```

| Cột | Kiểu | Null | Index/constraint | Ý nghĩa |
|---|---|---|---|---|
| `id` | integer | no | primary key, index | ID log. |
| `employee_id` | integer | yes | foreign key, index | Employee match được, null nếu không match. |
| `camera_id` | integer | yes | foreign key, index | Camera/cổng tạo log. |
| `status` | varchar(50) | no | index | Kết quả access. |
| `score` | float | yes |  | Điểm matching. |
| `image_path` | text | yes |  | Object key ảnh snapshot trong MinIO hoặc path mẫu/local. |
| `message` | text | yes |  | Thông điệp giải thích kết quả/lỗi. |
| `created_at` | timestamptz | no | index, server default `now()` | Thời điểm tạo log. |

`status`:

| Giá trị | Ý nghĩa |
|---|---|
| `processing` | Backend đã nhận request, worker chưa xử lý xong. |
| `granted` | Match employee active và score đạt threshold. |
| `denied` | Có xử lý nhưng không được cấp quyền. |
| `error` | Ảnh lỗi, không có mặt, nhiều mặt hoặc pipeline lỗi. |

Quan hệ:

```text
access_logs.employee_id -> employees.id
access_logs.camera_id -> cameras.id
```

`employee_id` nullable vì:

- denied không match employee;
- error không có employee;
- ảnh không hợp lệ không thể gắn employee.

`camera_id` nullable để giữ tương thích với flow cũ, nhưng flow hiện tại thường có camera mặc định.

Model có property:

```text
employee_name
```

Property này lấy từ relationship `employee.name`, không phải cột thật trong database.

---

## 9. Qdrant Và `face_embeddings`

Qdrant không thay thế PostgreSQL.

PostgreSQL lưu:

```text
face_embeddings.id
face_embeddings.employee_id
face_embeddings.vector
face_embeddings.model_name
face_embeddings.source_image_key
```

Qdrant lưu index để search nhanh, payload thường gồm:

```text
embedding_id
employee_id
model_name
```

Luồng access:

```text
access image -> embedding vector -> Qdrant search -> candidate employee -> verify PostgreSQL
```

Lý do vẫn verify lại PostgreSQL:

- employee có thể đã inactive;
- PostgreSQL là source of truth;
- Qdrant chỉ là search index.

---

## 10. MinIO Và `image_path/source_image_key`

Ảnh upload không lưu trực tiếp trong PostgreSQL.

MinIO lưu file thật:

```text
employee-faces/{employee_id}/<uuid>.jpg
access-snapshots/<uuid>.jpg
```

PostgreSQL chỉ lưu object key:

| Cột | Ý nghĩa |
|---|---|
| `face_embeddings.source_image_key` | Ảnh nguồn tạo embedding. |
| `access_logs.image_path` | Ảnh snapshot của access log. Tên cột giữ lại để tương thích ngược. |

Vì sao `access_logs.image_path` vẫn tên là `image_path`:

- flow cũ từng dùng local path;
- đổi tên cột sẽ cần migration rộng hơn;
- hiện tại giá trị thực tế thường là MinIO object key.

---

## 11. Seed Data

File seed:

```text
backend/app/db/seed.py
```

Lệnh chạy:

```powershell
docker compose run --rm backend python -m app.db.seed
```

Trong Docker Compose, service `db-seed` chạy:

```text
python -m app.db.seed
```

Seed tạo:

| Loại | Dữ liệu |
|---|---|
| Users | `admin`, `user` |
| Camera | `Main Gate` |
| Employees | `EMP001`, `EMP002`, `EMP003` |
| Access logs mẫu | granted, denied, error |

Biến điều khiển:

```text
SEED_ADMIN_USERNAME
SEED_ADMIN_PASSWORD
SEED_USER_USERNAME
SEED_USER_PASSWORD
SEED_DEMO_DATA
```

Tắt dữ liệu mẫu:

```text
SEED_DEMO_DATA=false
```

Lưu ý mới nhất:

- seed giữ một camera chính;
- camera thừa từ dữ liệu cũ có thể bị xóa;
- access log từ camera thừa được chuyển về camera chính.

---

## 12. Index Và Constraint Chính

Các index/constraint đáng chú ý:

| Bảng | Cột | Loại |
|---|---|---|
| `users` | `id` | primary key |
| `users` | `username` | unique + index |
| `employees` | `id` | primary key |
| `employees` | `code` | unique + index |
| `employees` | `name` | index |
| `employees` | `status` | index |
| `employees` | `embedding_status` | index |
| `cameras` | `id` | primary key |
| `cameras` | `name` | index |
| `cameras` | `status` | index |
| `face_embeddings` | `id` | primary key |
| `face_embeddings` | `employee_id` | foreign key + index |
| `access_logs` | `id` | primary key |
| `access_logs` | `employee_id` | foreign key + index |
| `access_logs` | `camera_id` | foreign key + index |
| `access_logs` | `status` | index |
| `access_logs` | `created_at` | index |

---

## 13. Chiến Lược Schema Hiện Tại

Repo hiện dùng SQLAlchemy `create_all()` cho schema baseline.

Cách hiện tại:

```text
Base.metadata.create_all()
ensure_* columns
```

Ưu điểm:

- đơn giản;
- phù hợp MVP và môi trường trình bày;
- dễ chạy trong Docker Compose.

Khi mở rộng production, nên cân nhắc:

- version schema rõ ràng hơn;
- kiểm soát thay đổi cột phức tạp;
- rollback migration khi cần.

Alembic là lựa chọn phù hợp nếu hệ thống được vận hành dài hạn.

---

## 14. Câu Lệnh Kiểm Tra Nhanh

Xem bảng trong PostgreSQL:

```powershell
docker compose exec database psql -U deepface -d deepface_access -c "\dt"
```

Xem cột bảng employees:

```powershell
docker compose exec database psql -U deepface -d deepface_access -c "\d employees"
```

Đếm access logs:

```powershell
docker compose exec database psql -U deepface -d deepface_access -c "SELECT status, COUNT(*) FROM access_logs GROUP BY status;"
```

Xem embedding status:

```powershell
docker compose exec database psql -U deepface -d deepface_access -c "SELECT id, code, name, embedding_status, embedding_error FROM employees ORDER BY id;"
```

---

## 15. Phạm Vi Hiện Tại Và Hướng Mở Rộng

- Có thể bổ sung Alembic migration để version schema rõ hơn.
- `image_path` là tên cột cũ nhưng đang chứa MinIO object key.
- Có thể bổ sung Qdrant reindex job tự động.
- Vector lưu dạng JSON trong PostgreSQL; `pgvector` là hướng mở rộng nếu muốn search vector ngay trong PostgreSQL.
- Camera management hiện read-only ở API/UI, nhưng bảng `cameras` vẫn giữ đủ field để mở rộng sau.

---

## 16. Tóm Tắt Ngắn

Schema hiện tại có 5 bảng chính:

```text
users
employees
cameras
face_embeddings
access_logs
```

PostgreSQL là source of truth. MinIO giữ ảnh. Qdrant giữ vector index. Redis giữ queue tạm thời.

Luồng dữ liệu chính:

```text
employee image -> MinIO -> worker -> face_embeddings + Qdrant
access snapshot -> MinIO -> access_logs -> worker -> access_logs updated
```

Thiết kế này phù hợp để trình bày hệ thống AI end-to-end. Nếu vận hành dài hạn, nên bổ sung Alembic migration, backup MinIO/Qdrant và reindex flow đầy đủ.
