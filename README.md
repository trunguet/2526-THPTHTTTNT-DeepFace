# DeepFace UET - Face Access Control System

Hệ thống nhận diện khuôn mặt thời gian thực cho bài toán kiểm soát ra vào/điểm danh. Giảng viên có thể khởi động toàn bộ hệ thống bằng Docker Compose:

```powershell
docker compose up --build -d
```

## Tính năng chính

- User UI mở webcam, chụp/quét tự động frame camera và hiển thị kết quả xác thực.
- Admin UI đăng ký tài khoản quản trị, thêm/sửa/xóa nhân viên, upload ảnh gốc, xem log truy cập và cảnh báo người lạ.
- Backend FastAPI xử lý nghiệp vụ, xác thực admin, lưu log, quản lý nhân viên và gọi pipeline AI.
- Worker nền tạo embedding khi thêm nhân viên hoặc re-index toàn bộ dữ liệu.
- Lưu trữ đủ 3 nhóm yêu cầu: MySQL, MinIO object storage, Qdrant vector database.
- Redis dùng làm message queue cho worker và cache L2; backend có thêm cache L1 in-memory.
- Nginx gateway đóng vai trò reverse proxy/load balancer cho frontend và backend.
- Có backup service cho MySQL, MinIO, Qdrant và manifests Kubernetes.

## Kiến trúc

```text
Browser
  |
  v
Nginx Gateway (:8080)
  |-- /                 -> frontend-home
  |-- /admin/           -> frontend-admin
  |-- /user/            -> frontend-user
  |-- /api/*, /health   -> backend FastAPI
                             |
                             |-- MySQL: employees, admin_accounts, attendance_logs
                             |-- MinIO: employee images and audit snapshots
                             |-- Qdrant: 512-d face embeddings
                             |-- Redis: cache + embedding_jobs queue
                             |
                             v
                          AI Pipeline
                          YOLOv8-Face -> quality gates -> MiniFASNet -> ArcFace -> Qdrant match

Admin upload employee image
  -> Backend creates employee row
  -> Redis queue: extract_embedding
  -> Worker reads image from MinIO
  -> ArcFace embedding
  -> Upsert vector into Qdrant
```

## Thành phần Docker Compose

| Service | Vai trò | URL local |
| --- | --- | --- |
| `gateway` | Nginx reverse proxy/load balancer | http://localhost:8080 |
| `frontend-home` | Trang điều hướng | http://localhost:3000 |
| `frontend-admin` | Admin UI | http://localhost:3001 |
| `frontend-user` | User UI | http://localhost:3002 |
| `backend` | FastAPI | http://localhost:18000/health |
| `worker` | Background embedding worker | internal |
| `mysql` | Database | localhost:13306 |
| `minio` | Object storage | http://localhost:19001 |
| `qdrant` | Vector DB | http://localhost:16333/dashboard |
| `redis` | Queue/cache | localhost:16379 |
| `backup` | Backup dữ liệu | `./backups` |

Các đường dẫn khuyến nghị khi demo qua gateway:

- Home: http://localhost:8080
- Admin: http://localhost:8080/admin/
- User: http://localhost:8080/user/
- API health: http://localhost:8080/health

## Yêu cầu môi trường

- Docker Desktop
- Docker Compose v2
- Tối thiểu 8 GB RAM trống khi build/chạy backend ML trên CPU
- Internet ở lần build/chạy đầu nếu image chưa có sẵn weights ArcFace

Không cần cài Python nếu chỉ chạy bằng Docker.

## Cấu hình môi trường

Repo đã có `.env.example`. Có thể chạy ngay với giá trị mặc định local. Khi cần tùy biến:

```powershell
Copy-Item .env.example .env
```

Các biến quan trọng:

- `ADMIN_AUTH_SECRET`: đổi khi chạy ngoài môi trường local.
- `GATEWAY_PORT`: port gateway, mặc định `8080`.
- `BACKEND_IMAGE`, `FRONTEND_HOME_IMAGE`, `FRONTEND_ADMIN_IMAGE`, `FRONTEND_USER_IMAGE`: dùng khi chạy image đã push lên Docker Hub.
- `DATABASE_URL`, `DATABASE_SSL`: dùng nếu chuyển sang TiDB/MySQL managed.

Quan trọng: web chỉ thống nhất với MySQL Workbench khi backend đang trỏ đúng cùng MySQL server/schema mà Workbench đang mở. Cùng tên schema `DB_Employee` nhưng khác server thì dữ liệu vẫn khác nhau. Để kiểm tra backend đang nối đâu, đăng nhập admin rồi gọi:

```powershell
curl http://localhost:18000/api/debug/db -H "Authorization: Bearer <admin_token>"
```

Nếu Workbench đang nối MySQL ngoài container, đặt `DATABASE_URL` trong `.env` trực tiếp với đúng host/user/password/db đó. Ví dụ MySQL chạy trên Windows host:

```env
DATABASE_URL=mysql+pymysql://root:deepface_root_password@host.docker.internal:3306/DB_Employee?charset=utf8mb4
DATABASE_SSL=false
```

Repo có sẵn file mẫu `.env.mysql-old.example` cho trường hợp dùng MySQL cũ/cloud. Copy các dòng phù hợp từ file này sang `.env`, thay `USER`, `PASSWORD`, `HOST`, `PORT`, rồi chạy lại:

```powershell
docker compose up -d --force-recreate backend worker
```

Nếu DB cũ có sẵn `minio_image_path`, cần trỏ `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` về đúng object storage cũ để ảnh cũ mở được.

### Chạy nhiều máy dùng chung dữ liệu

Để các máy khác nhau cùng thấy một danh sách nhân viên và log quét, tất cả máy phải dùng cùng một MySQL server. Cách làm khuyến nghị:

1. Chuẩn bị một MySQL chung mà mọi máy truy cập được, ví dụ MySQL/TiDB Cloud, VPS, hoặc một máy trong mạng LAN mở port `3306`.
2. Copy `.env.shared.example` thành `.env` trên từng máy.
3. Điền cùng một `DATABASE_URL` trên mọi máy:

```env
DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:PORT/DB_Employee?charset=utf8mb4
DATABASE_SSL=false
```

4. Nếu muốn ảnh nhân viên cũng mở được trên mọi máy, cấu hình chung `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`.
5. Nếu muốn kết quả nhận diện giống nhau ngay trên mọi máy, dùng chung `QDRANT_URL`; nếu mỗi máy dùng Qdrant local thì sau khi đồng bộ nhân viên/ảnh cần chạy re-index trên từng máy.
6. Restart backend và worker:

```powershell
docker compose up -d --force-recreate backend worker
```

7. Đăng nhập admin, kiểm tra backend đang nối đúng DB chung:

```powershell
curl http://localhost:18000/api/debug/db -H "Authorization: Bearer <admin_token>"
```

Trong kết quả, `configured_target.host` phải là host MySQL chung, không phải `mysql`. Nếu là `mysql` thì backend vẫn đang dùng MySQL container local.

Không commit `.env`, API key, token, password thật hoặc file nhạy cảm.

## Model weights

Repo giữ các model nhỏ cần thiết cho YOLOv8-Face và MiniFASNet. ArcFace weight lớn (`arcface_weights.h5`, hơn 100 MB) không commit vào Git để tránh vượt giới hạn GitHub.

Lựa chọn khuyến nghị:

1. Khi build image nộp bài/Docker Hub, build trên máy đã có cache DeepFace để image tự tải/bake dependency trong quá trình kiểm thử.
2. Khi chạy local, đặt file ArcFace vào:

```text
model_cache/arcface_weights.h5
```

Compose mount thư mục này vào container tại `/root/.deepface/weights`. Nếu file chưa có, DeepFace sẽ tải ở lần chạy đầu khi pipeline được preload.

## Chạy hệ thống

```powershell
docker compose up --build -d
```

Kiểm tra:

```powershell
docker compose ps
docker compose logs -f backend
docker compose logs -f worker
```

Mở:

- http://localhost:8080/admin/
- http://localhost:8080/user/

## Luồng demo đề xuất

1. Vào Admin UI: http://localhost:8080/admin/
2. Đăng ký admin đầu tiên. Tài khoản đầu tiên sẽ là `super_admin`.
3. Vào `Thêm Nhân Viên`, nhập mã nhân viên, họ tên, email, phòng ban và ảnh mặt rõ.
4. Chờ worker tạo vector. Trong danh sách nhân viên, trạng thái embedding chuyển sang `indexed`.
5. Vào User UI: http://localhost:8080/user/
6. Mở camera, chọn `Chụp & Xác thực` hoặc `Tự Động Quét`.
7. Xem kết quả allowed/denied/stranger và kiểm tra log trong Admin UI.

Nếu vector cũ sai hoặc dữ liệu Qdrant bẩn, dùng Admin API:

```powershell
curl -X POST http://localhost:18000/api/employees/qdrant/reset -H "Authorization: Bearer <admin_token>"
```

## Docker Hub

Các image đã push lên Docker Hub namespace `trungngd`:

- `trungngd/deepface-backend:latest`
- `trungngd/deepface-frontend-home:latest`
- `trungngd/deepface-frontend-admin:latest`
- `trungngd/deepface-frontend-user:latest`
- `trungngd/deepface-backup:latest`

Giảng viên có thể chạy trực tiếp bằng image đã push, không cần build:

```powershell
docker compose --env-file .env.dockerhub.example -f docker-compose.images.yml pull
docker compose --env-file .env.dockerhub.example -f docker-compose.images.yml up -d
```

Build và tag image thủ công:

```powershell
docker build -t <dockerhub-user>/deepface-backend:latest -f backend/Dockerfile .
docker build -t <dockerhub-user>/deepface-frontend-home:latest -f frontend/home/Dockerfile .
docker build -t <dockerhub-user>/deepface-frontend-admin:latest -f frontend/admin/Dockerfile .
docker build -t <dockerhub-user>/deepface-frontend-user:latest -f frontend/user/Dockerfile .
```

Hoặc dùng script có sẵn để build, tag và push đủ image project-owned:

```powershell
docker login
.\scripts\push-dockerhub.ps1 -Namespace <dockerhub-user>
```

Script này push các image:

- `<dockerhub-user>/deepface-backend:latest`
- `<dockerhub-user>/deepface-frontend-home:latest`
- `<dockerhub-user>/deepface-frontend-admin:latest`
- `<dockerhub-user>/deepface-frontend-user:latest`
- `<dockerhub-user>/deepface-backup:latest`

Push thủ công nếu không dùng script:

```powershell
docker push <dockerhub-user>/deepface-backend:latest
docker push <dockerhub-user>/deepface-frontend-home:latest
docker push <dockerhub-user>/deepface-frontend-admin:latest
docker push <dockerhub-user>/deepface-frontend-user:latest
docker push <dockerhub-user>/deepface-backup:latest
```

Chạy bằng image đã push:

```powershell
docker compose --env-file .env.dockerhub.example -f docker-compose.images.yml pull
docker compose --env-file .env.dockerhub.example -f docker-compose.images.yml up -d
```

File `docker-compose.images.yml` không có `build`, nên giảng viên chỉ cần pull image và chạy. Kiểm tra nhanh:

```powershell
docker compose --env-file .env.dockerhub -f docker-compose.images.yml config | Select-String "build:"
```

## Kiểm thử backend

Cài dependencies local nếu cần chạy test ngoài Docker:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest
```

`pytest.ini` đã cấu hình `pythonpath = backend`.

## Kubernetes

Thư mục `k8s/` chứa manifests theo Kustomize:

- `k8s/base`: backend, worker, 3 frontend, service, ingress template.
- `k8s/overlays/local`: overlay local kèm Redis/MinIO/Qdrant.
- `k8s/overlays/ingress-nginx-local`: overlay dùng ingress-nginx local.

Chạy local:

```powershell
kubectl apply -k k8s/overlays/local
kubectl get pods -n deepface
```

Chi tiết xem [k8s/README.md](k8s/README.md).

## Backup

Service `backup` tạo snapshot vào `./backups`:

- `mysql.sql`
- `minio_data.tar.gz`
- `qdrant_data.tar.gz`

Mặc định giữ 7 ngày qua `RETENTION_DAYS`.

## Troubleshooting

Backend startup lâu:

- Lần đầu TensorFlow/DeepFace/ArcFace có thể tải hoặc khởi tạo model chậm.
- Xem log: `docker compose logs -f backend`.

Không truy cập được camera:

- Trình duyệt thường yêu cầu `localhost` hoặc HTTPS.
- Dùng http://localhost:8080/user/ khi demo local.

Không match nhân viên:

- Kiểm tra ảnh nhân viên chỉ có một mặt, rõ, đủ sáng.
- Chờ worker xử lý embedding.
- Dùng `reindex-all` hoặc `qdrant/reset` nếu Qdrant chứa vector cũ.

Docker build quá nặng:

- Backend ML có TensorFlow, PyTorch, DeepFace và OpenCV nên image lớn là bình thường.
- `.dockerignore` đã loại `.env`, `.venv`, `model_cache`, backup và cache test khỏi build context.

## Thành viên phát triển

| Vai trò | Nhiệm vụ |
| --- | --- |
| Backend | API, DB schema, auth, AI pipeline |
| Frontend Admin | Quản trị nhân viên, log, settings |
| Frontend User | Camera scan, hiển thị kết quả |
| DevOps | Docker Compose, gateway, Kubernetes, backup |

## Bảo mật

- `.env` đã bị ignore, không commit credential thật.
- Admin password được hash PBKDF2-HMAC-SHA256 kèm salt.
- API quản trị yêu cầu Bearer token.
- Snapshot và ảnh gốc lưu trong MinIO, truy xuất qua backend endpoint.

## License

Dự án phục vụ mục đích học tập và nghiên cứu tại UET.
