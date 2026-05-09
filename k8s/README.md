# Kubernetes (Cách 1: app-only, dùng dịch vụ managed)

Thư mục này deploy **chỉ phần ứng dụng** lên Kubernetes:
- `backend` (FastAPI)
- `worker` (background worker)
- `frontend-home` (Nginx static)
- `frontend-user` (Nginx static)
- `frontend-admin` (Nginx static)

Các dịch vụ stateful như **MySQL/TiDB**, **Redis**, **MinIO/S3-compatible**, **Qdrant** nên dùng managed service bên ngoài cluster.

## 1) Chuẩn bị image

Push các image lên registry của bạn (Docker Hub/GHCR…):
- `deepface_backend` (dùng cho cả backend + worker)
- `frontend-home`
- `frontend-user`
- `frontend-admin`

Sau đó bạn có thể sửa image bằng cách tạo overlay riêng hoặc chỉnh trực tiếp trường `image:` trong các file `k8s/base/*deployment.yaml`.

## 2) Tạo Secret/ConfigMap cho môi trường

Tạo `Secret` (khuyến nghị qua file riêng không commit):

```bash
kubectl -n deepface create secret generic deepface-secrets \
  --from-literal=ADMIN_AUTH_SECRET='change-me' \
  --from-literal=DATABASE_URL='mysql+pymysql://USER:PASSWORD@HOST:PORT/DB?charset=utf8mb4' \
  --from-literal=MINIO_ACCESS_KEY='...' \
  --from-literal=MINIO_SECRET_KEY='...' \
  --dry-run=client -o yaml | kubectl apply -f -
```

Sửa `k8s/base/configmap.yaml` theo endpoint managed của bạn:
- `REDIS_URL`
- `MINIO_ENDPOINT`, `MINIO_BUCKET`
- `QDRANT_URL`, `QDRANT_COLLECTION`
- `PUBLIC_API_BASE_URL` (thường là `https://api.yourdomain`)

Nếu bạn muốn tạo secret thành file để apply:

```bash
kubectl -n deepface create secret generic deepface-secrets \
  --from-literal=ADMIN_AUTH_SECRET='change-me' \
  --from-literal=DATABASE_URL='...' \
  --from-literal=MINIO_ACCESS_KEY='...' \
  --from-literal=MINIO_SECRET_KEY='...' \
  --dry-run=client -o yaml > k8s/secret.yaml
kubectl apply -f k8s/secret.yaml
```
(`k8s/secret.yaml` đã được ignore trong `k8s/.gitignore`.)

## 3) Deploy

```bash
kubectl apply -k k8s/base
```

## Chạy local (không cần registry/Ingress)

Nếu bạn chạy `minikube` hoặc `kind` và muốn **không push image lên registry**, dùng overlay local:

1) Build image vào đúng Docker daemon của cluster

- Với **minikube**:
  - `minikube start`
  - `minikube docker-env | Invoke-Expression`
  - `docker build -t deepface_backend:latest -f backend/Dockerfile .`
  - `docker build -t deepface_frontend_home:latest -f frontend/home/Dockerfile .`
  - `docker build -t deepface_frontend_user:latest -f frontend/user/Dockerfile .`
  - `docker build -t deepface_frontend_admin:latest -f frontend/admin/Dockerfile .`

- Với **kind** (build xong thì load vào cluster):
  - `kind create cluster`
  - `docker build -t deepface_backend:latest -f backend/Dockerfile .`
  - `docker build -t deepface_frontend_home:latest -f frontend/home/Dockerfile .`
  - `docker build -t deepface_frontend_user:latest -f frontend/user/Dockerfile .`
  - `docker build -t deepface_frontend_admin:latest -f frontend/admin/Dockerfile .`
  - `kind load docker-image deepface_backend:latest`
  - `kind load docker-image deepface_frontend_home:latest`
  - `kind load docker-image deepface_frontend_user:latest`
  - `kind load docker-image deepface_frontend_admin:latest`

2) Tạo secret `deepface-secrets` như mục (2) rồi deploy:
  - `kubectl apply -k k8s/overlays/local`

3) Truy cập (NodePort):
  - Home: `http://localhost:30080`
  - User: `http://localhost:30081`
  - Admin: `http://localhost:30082`
  - API: `http://localhost:31800`

Lưu ý với **Docker Desktop Kubernetes (kind)**:
- Cần bật **containerd image store** (Docker Desktop → Settings → General → bật “Use containerd for pulling and storing images”), rồi restart Docker Desktop.
- Sau khi bật, hãy `docker build ...` lại để Kubernetes nhìn thấy image local.

Overlay local đã:
- Tắt Ingress
- Set `imagePullPolicy: Never`
- Đổi Service sang NodePort cố định
 - Chạy Redis/MinIO/Qdrant ngay trong Kubernetes (đỡ lỗi network `host.docker.internal`)

## 4) Ingress / Domain

`k8s/base/ingress.yaml` đang là template. Sửa:
- `admin.yourdomain` → `frontend-admin`
- `app.yourdomain` → `frontend-user`
- `yourdomain` → `frontend-home`
- (tuỳ) `api.yourdomain` → `backend`

Ingress template đã route `/api` trên cả 3 host về `backend`, để frontend có thể gọi API theo **same-origin**.
Khi đó bạn có thể đặt API base URL trong UI là `/` (để request thành `/api/...`).

Nếu bạn chưa dùng Ingress, có thể tạm comment ingress và dùng `kubectl port-forward`.

## Ingress Nginx (local Docker Desktop) - bỏ port-forward

Overlay: `k8s/overlays/ingress-nginx-local` (host-based routing + `/api` proxy).

### 1) Cài ingress-nginx controller

Chạy 1 lần:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.3/deploy/static/provider/cloud/deploy.yaml
```

Đợi controller lên:

```bash
kubectl get pods -n ingress-nginx
```

### 2) Trỏ domain local về 127.0.0.1

Sửa file `C:\\Windows\\System32\\drivers\\etc\\hosts` (Run as Administrator) thêm:

```
127.0.0.1 deepface.local
127.0.0.1 app.deepface.local
127.0.0.1 admin.deepface.local
```

### 3) Deploy overlay Ingress

```bash
kubectl apply -k k8s/overlays/ingress-nginx-local
```

Mở:
- `http://deepface.local`
- `http://app.deepface.local`
- `http://admin.deepface.local`

Overlay này route `/api` về backend trên cùng host, nên trong UI bạn có thể đặt API base URL là `/`.

## 5) Kiểm tra

```bash
kubectl get pods -n deepface
kubectl logs -n deepface deploy/deepface-backend
kubectl logs -n deepface deploy/deepface-worker
```

Health check:
- `GET /health` trên service backend.
