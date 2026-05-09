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
pip install -r requirements.txt
```

Nếu backend có requirements riêng:

```powershell
pip install -r backend/requirements.txt
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
| Admin UI         | [http://localhost:3001](http://localhost:3001)                       |
| User UI          | [http://localhost:3002](http://localhost:3002)                       |
| Backend Health   | [http://localhost:18000/health](http://localhost:18000/health)       |
| MinIO Console    | [http://localhost:19001](http://localhost:19001)                     |
| Qdrant Dashboard | [http://localhost:16333/dashboard](http://localhost:16333/dashboard) |

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
