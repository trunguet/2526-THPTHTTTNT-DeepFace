# DeepFace UET – Face Access Control System

Hệ thống nhận diện khuôn mặt thời gian thực kết hợp anti-spoofing phục vụ bài toán:

* Điểm danh nhân viên / sinh viên
* Kiểm soát ra vào
* Quản lý lịch sử nhận diện
* Quản trị người dùng qua giao diện web

Dự án được xây dựng theo hướng triển khai thực tế với:

* FastAPI Backend
* Frontend tách riêng (Home / User / Admin)
* Redis cache
* Qdrant vector database
* MinIO object storage
* Kubernetes deployment
* Docker Compose local development

---

# 1. Kiến trúc hệ thống

```text
Camera/Input
      ↓
YOLOv8 Face Detection
      ↓
MiniFAS Anti-Spoof
      ↓
ArcFace Embedding Extraction
      ↓
Qdrant Vector Search
      ↓
FastAPI Backend
      ↓
Frontend (Admin / User / Home)
```

---

# 2. Công nghệ sử dụng

| Thành phần       | Công nghệ           |
| ---------------- | ------------------- |
| Backend API      | FastAPI             |
| Frontend         | HTML/CSS/JS + Nginx |
| Face Detection   | YOLOv8-Face         |
| Face Recognition | ArcFace             |
| Anti-Spoofing    | MiniFASNet          |
| Vector Database  | Qdrant              |
| Cache            | Redis               |
| Object Storage   | MinIO               |
| Containerization | Docker              |
| Orchestration    | Kubernetes          |

---

# 3. Cấu trúc thư mục

```text
backend/                    # FastAPI backend
frontend/                   # Frontend applications
├── admin/                  # Admin UI
├── user/                   # User UI
└── home/                   # Landing page

k8s/                        # Kubernetes manifests
├── base/
└── overlays/

models/                     # AI model weights
├── detection/
├── anti_spoof/
└── extraction/

backup_service/             # Backup service

scripts/                    # Utility scripts
```

---

# 4. Yêu cầu môi trường

## Windows

Khuyến nghị:

* Windows 10/11
* Docker Desktop
* Kubernetes enabled
* Python 3.10
* PowerShell

---

# 5. Tạo môi trường Python (venv)

## 5.1 Kiểm tra Python

```powershell
py -3.10 --version
```

## 5.2 Tạo venv

```powershell
py -3.10 -m venv .venv
```

## 5.3 Activate

```powershell
.\.venv\Scripts\Activate.ps1
```

## 5.4 Cài dependencies

```powershell
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r backend/requirements-ml.txt
```

---

# 6. Chạy bằng Docker Compose

## 6.1 Build + Run

```powershell
docker compose up --build -d
```

## 6.2 Truy cập hệ thống

| Service          | URL                                                                  |
| ---------------- | -------------------------------------------------------------------- |
| Home             | [http://localhost:3000](http://localhost:3000)                       |
| Admin UI         | [http://localhost:3001](http://localhost:3001) hoặc [http://localhost:8082](http://localhost:8082) |
| User UI          | [http://localhost:3002](http://localhost:3002) hoặc [http://localhost:8081](http://localhost:8081) |
| Backend Health   | [http://localhost:18000/health](http://localhost:18000/health)       |
| MinIO Console    | [http://localhost:19001](http://localhost:19001)                     |
| Qdrant Dashboard | [http://localhost:16333/dashboard](http://localhost:16333/dashboard) |
| Gateway Nginx    | [http://localhost:8080](http://localhost:8080)                       |

Khi chạy bằng Docker Compose, gateway khuyến nghị là `8080`. Các port `8081` và `8082` cũng được map thêm làm alias để giống luồng Kubernetes port-forward.

Gateway Nginx là điểm vào thống nhất khi chấm bài:

| Route | Dịch vụ |
| ----- | ------- |
| `/` | Home |
| `/admin/` | Admin UI |
| `/user/` | User UI |
| `/api/` | Backend API |

Nếu muốn URL ảnh snapshot trả về qua gateway, đặt trong `.env`:

```powershell
PUBLIC_API_BASE_URL=http://localhost:8080
```

Admin lần đầu có thể tạo tài khoản tại:

```text
http://localhost:8080/admin/login.html
```

Nếu chưa có admin nào, màn hình login sẽ cho phép bootstrap tài khoản admin đầu tiên.

---

## 6.3 Demo flow cho giảng viên

Sau khi chạy:

```powershell
docker compose up -d
```

Thực hiện luồng demo theo thứ tự sau:

1. Mở gateway: [http://localhost:8080](http://localhost:8080).
2. Vào Admin UI: [http://localhost:8080/admin/login.html](http://localhost:8080/admin/login.html).
3. Nếu hệ thống chưa có admin, đăng ký tài khoản admin đầu tiên ngay trên màn hình login.
4. Vào `Thêm nhân viên`, nhập mã nhân viên, họ tên, email, phòng ban và upload ảnh khuôn mặt rõ.
5. Chờ worker tạo embedding. Trong danh sách nhân viên, trạng thái nên chuyển sang `indexed`.
6. Vào User UI: [http://localhost:8080/user/face_scan.html](http://localhost:8080/user/face_scan.html).
7. Bật camera, chọn `Chụp & Xác Thực` hoặc bật quét realtime. Hệ thống sẽ trả về `allowed`, `denied` hoặc `stranger`.
8. Quay lại Admin UI, mở `Nhật ký truy cập` để xem lịch sử scan, ảnh snapshot và cảnh báo người lạ.

Các endpoint kiểm tra nhanh:

```powershell
curl http://localhost:8080/health
curl http://localhost:8080/api/health
```

---

## 6.4 Docker Hub images

Để đáp ứng yêu cầu nộp bài, build và push 4 image lên Docker Hub. Thay `your-dockerhub-user` bằng namespace Docker Hub thật của nhóm:

```powershell
$env:DOCKERHUB_NAMESPACE="your-dockerhub-user"

docker build -t "$env:DOCKERHUB_NAMESPACE/deepface-backend:latest" -f backend/Dockerfile .
docker build -t "$env:DOCKERHUB_NAMESPACE/deepface-home:latest" -f frontend/home/Dockerfile .
docker build -t "$env:DOCKERHUB_NAMESPACE/deepface-user:latest" -f frontend/user/Dockerfile .
docker build -t "$env:DOCKERHUB_NAMESPACE/deepface-admin:latest" -f frontend/admin/Dockerfile .

docker push "$env:DOCKERHUB_NAMESPACE/deepface-backend:latest"
docker push "$env:DOCKERHUB_NAMESPACE/deepface-home:latest"
docker push "$env:DOCKERHUB_NAMESPACE/deepface-user:latest"
docker push "$env:DOCKERHUB_NAMESPACE/deepface-admin:latest"
```

Backend image được build từ repo root và Dockerfile sẽ fail nếu thiếu `models/extraction/arcface_weights.h5`. Có thể kiểm tra weight đã nằm trong image bằng lệnh:

```powershell
docker run --rm "$env:DOCKERHUB_NAMESPACE/deepface-backend:latest" python -c "from pathlib import Path; p=Path('/app/models/extraction/arcface_weights.h5'); print(p.exists(), p.stat().st_size if p.exists() else 0)"
```

Khi muốn compose dùng image đã push, copy `.env.example` thành `.env` và sửa:

```text
BACKEND_IMAGE=your-dockerhub-user/deepface-backend:latest
FRONTEND_HOME_IMAGE=your-dockerhub-user/deepface-home:latest
FRONTEND_USER_IMAGE=your-dockerhub-user/deepface-user:latest
FRONTEND_ADMIN_IMAGE=your-dockerhub-user/deepface-admin:latest
```

Lưu ý: `models/extraction/arcface_weights.h5` lớn hơn giới hạn GitHub 100MB, nên không commit trực tiếp vào GitHub thường. Backend image đã push phải chứa file này, hoặc nhóm cần quản lý bằng Git LFS/link tải model riêng và mô tả rõ trong README.

---

## 6.5 Test nhanh

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m unittest discover -s backend\app\tests
```

---

# 7. Chạy bằng Kubernetes

## 7.1 Bật Kubernetes trong Docker Desktop

Docker Desktop → Settings → Kubernetes → Enable Kubernetes

Kiểm tra:

```powershell
kubectl config use-context docker-desktop
kubectl cluster-info
```

---

## 7.2 Build image local

```powershell
docker build -t deepface_backend:latest -f backend/Dockerfile .

docker build -t deepface_frontend_home:latest -f frontend/home/Dockerfile .

docker build -t deepface_frontend_user:latest -f frontend/user/Dockerfile .

docker build -t deepface_frontend_admin:latest -f frontend/admin/Dockerfile .
```

---

## 7.3 Tạo namespace

```powershell
kubectl apply -f k8s/base/namespace.yaml
```

---

## 7.4 Tạo Kubernetes Secret

```powershell
kubectl -n deepface create secret generic deepface-secrets `
  --from-literal=ADMIN_AUTH_SECRET='change-me' `
  --from-literal=DATABASE_URL='mysql+pymysql://USER:PASSWORD@HOST:PORT/DB?charset=utf8mb4' `
  --from-literal=MINIO_ACCESS_KEY='admin' `
  --from-literal=MINIO_SECRET_KEY='password123' `
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 7.5 Deploy lên Kubernetes

```powershell
kubectl apply -k k8s/overlays/local
```

Kiểm tra:

```powershell
kubectl get pods -n deepface
kubectl get svc -n deepface
```

---

## 7.6 Port Forward (Khuyến nghị trên Windows)

### Home

```powershell
kubectl -n deepface port-forward svc/deepface-frontend-home 8080:80
```

### User UI

```powershell
kubectl -n deepface port-forward svc/deepface-frontend-user 8081:80
```

### Admin UI

```powershell
kubectl -n deepface port-forward svc/deepface-frontend-admin 8082:80
```

### Backend API

```powershell
kubectl -n deepface port-forward svc/deepface-backend 18000:8000
```

---

## 7.7 URL truy cập

| Service        | URL                                                            |
| -------------- | -------------------------------------------------------------- |
| Home           | [http://127.0.0.1:8080](http://127.0.0.1:8080)                 |
| User UI        | [http://127.0.0.1:8081](http://127.0.0.1:8081)                 |
| Admin UI       | [http://127.0.0.1:8082](http://127.0.0.1:8082)                 |
| Backend Health | [http://127.0.0.1:18000/health](http://127.0.0.1:18000/health) |

---

# 8. Kiểm tra logs

## Backend

```powershell
kubectl logs -f -n deepface deploy/deepface-backend
```

## Worker

```powershell
kubectl logs -f -n deepface deploy/deepface-worker
```

---

# 9. Restart deployment

## Backend

```powershell
kubectl rollout restart deployment/deepface-backend -n deepface
```

## Frontend Admin

```powershell
kubectl rollout restart deployment/deepface-frontend-admin -n deepface
```

---

# 10. Các thành phần AI

## 10.1 Face Detection

Sử dụng YOLOv8-Face để phát hiện khuôn mặt trong ảnh/video.

## 10.2 Anti-Spoofing

Sử dụng MiniFASNet để phát hiện:

* Ảnh in
* Replay attack
* Fake camera
* Màn hình điện thoại

## 10.3 Face Recognition

Sử dụng ArcFace embedding.

Embedding được lưu trong Qdrant để truy vấn vector similarity.

## 10.4 Realtime scan UI

User UI ho tro 2 che do:

* Chup thu cong: nguoi dung bam "Chup & Xac Thuc".
* Quet realtime: nut "Bat quet realtime" tu dong gui frame moi 2.5 giay, tranh gui chong request, va hien trang thai tren khung camera.

---

# 11. Troubleshooting

## 11.1 Port không truy cập được

Kiểm tra:

```powershell
kubectl get pods -n deepface
kubectl get svc -n deepface
```

Dùng port-forward thay vì NodePort trên Windows.

---

## 11.2 Token admin bị lỗi

Mở DevTools Console:

```javascript
localStorage.removeItem('auth_token');
localStorage.removeItem('admin_username');
location.reload();
```

---

## 11.3 GitHub reject file > 100MB

Không commit model weights.

Thêm vào `.gitignore`:

```gitignore
model_cache/
models/
*.h5
*.pth
*.pt
```

---

# 12. Thành viên phát triển

| Vai trò        | Nhiệm vụ             |
| -------------- | -------------------- |
| Backend        | API + AI Pipeline    |
| Frontend Admin | Quản trị nhân viên   |
| Frontend User  | Giao diện người dùng |
| DevOps         | Docker + Kubernetes  |

---

# 13. Định hướng mở rộng

* HTTPS + Ingress NGINX
* CI/CD GitHub Actions
* GPU inference
* Multi-camera streaming
* Real-time WebSocket
* Helm deployment
* Monitoring với Prometheus + Grafana

---

# 14. License

Dự án phục vụ mục đích học tập và nghiên cứu tại UET.
