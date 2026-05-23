# Deployment

Tài liệu này mô tả cách chạy và triển khai DeepFace Access Control trong môi trường local/prod-like.

---

## 1. Chạy Local Bằng Docker Compose

Chạy toàn bộ stack:

```powershell
docker compose up --build -d
```

Docker Compose sẽ tự chạy service `db-seed` một lần để:

- tạo bảng;
- seed tài khoản mặc định;
- seed dữ liệu mẫu tối thiểu.

Nếu cần chạy seed lại thủ công:

```powershell
docker compose run --rm backend python -m app.db.seed
```

Hoặc dùng script dev:

```powershell
.\scripts\dev.ps1
```

---

## 2. URL Sau Khi Chạy

| Thành phần | URL |
|---|---|
| Home/Gateway | `http://localhost:8080` |
| User UI | `http://localhost:8080/user/` |
| Admin UI | `http://localhost:8080/admin/` |
| Backend API | `http://localhost:8080/api/...` |
| Swagger | `http://localhost:8080/docs` |
| Health | `http://localhost:8080/health` |
| Metrics | `http://localhost:8080/metrics` |
| MinIO Console | `http://localhost:9001` |
| Qdrant | `http://localhost:6333/dashboard` |
| Prometheus | `http://localhost:9090` |
| Alertmanager | `http://localhost:9093` |
| Grafana | `http://localhost:3000` |

---

## 3. Tài Khoản Mặc Định

Ứng dụng:

```text
admin / admin123
user  / user123
```

Grafana:

```text
admin / admin
```

MinIO:

```text
minioadmin / minioadmin
```

Nên đổi các tài khoản này khi triển khai môi trường dùng chung.

---

## 4. Kiểm Tra Stack

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

Xem log:

```powershell
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f nginx
```

Lưu ý: worker healthcheck hiện ping Redis; worker chưa cần HTTP health endpoint riêng trong phạm vi hiện tại.

---

## 5. Nginx Gateway

Nginx route:

| Route | Đi tới |
|---|---|
| `/` | `frontend-home` |
| `/user/` | `frontend-user` |
| `/admin/` | `frontend-admin` |
| `/api/` | backend |
| `/docs` | backend Swagger |
| `/health` | backend health |
| `/metrics` | backend metrics |

Frontend Docker image build static asset bằng Vite rồi serve bằng Nginx.

`VITE_API_BASE_URL` và `VITE_BASE_PATH` là build-time config, được truyền qua Docker build args trong Docker Compose/CI.

Khi muốn đi toàn bộ qua Nginx, đặt:

```text
VITE_API_BASE_URL=/api
VITE_USER_BASE_PATH=/user/
VITE_ADMIN_BASE_PATH=/admin/
```

---

## 6. Biến Môi Trường

Copy `.env.example` thành `.env` nếu muốn tùy biến:

```powershell
Copy-Item .env.example .env
```

Secret production không nên commit vào repo.

Các biến nên đổi khi triển khai môi trường thật:

```text
AUTH_SECRET_KEY
POSTGRES_PASSWORD
MINIO_ROOT_USER
MINIO_ROOT_PASSWORD
GRAFANA_ADMIN_PASSWORD
DOCKERHUB_NAMESPACE
IMAGE_TAG
NGINX_PORT
```

---

## 7. Docker Hub Images

Docker Compose dùng image theo format:

```text
${DOCKERHUB_NAMESPACE}/<image-name>:${IMAGE_TAG}
```

Ví dụ:

```powershell
$env:DOCKERHUB_NAMESPACE="duclm2006"
$env:IMAGE_TAG="latest"
docker compose config --images
```

Kiểm tra readiness:

```powershell
.\scripts\check-dockerhub-readiness.ps1 -Namespace <dockerhub-username> -ImageTag latest
```

---

## 8. Helm/Kubernetes

Chart nằm ở:

```text
helm/deepface-access
```

Kiểm tra chart:

```powershell
helm lint helm/deepface-access
helm template deepface-access helm/deepface-access
```

Deploy:

```powershell
helm upgrade --install deepface-access helm/deepface-access `
  --set global.imageRegistry=<dockerhub-username> `
  --set global.imageTag=<commit-sha>
```

Nếu image private, tạo image pull secret:

```powershell
kubectl create secret docker-registry dockerhub-pull `
  --docker-server=https://index.docker.io/v1/ `
  --docker-username=<dockerhub-username> `
  --docker-password=<dockerhub-token>
```

Rồi truyền vào Helm:

```powershell
helm upgrade --install deepface-access helm/deepface-access `
  --set global.imageRegistry=<dockerhub-username> `
  --set global.imageTag=<commit-sha> `
  --set global.imagePullSecrets[0].name=dockerhub-pull
```

---

## 9. Kubernetes Secrets

Chart hiện tham chiếu secret có sẵn:

```text
deepface-access-secrets
```

Secret này dùng cho backend, worker, PostgreSQL và MinIO.

Nếu secret chưa tồn tại, chart vẫn render được nhưng pod có thể thiếu biến môi trường quan trọng lúc start.

Ví dụ tạo secret:

```powershell
kubectl create secret generic deepface-access-secrets `
  --from-literal=POSTGRES_PASSWORD=deepface `
  --from-literal=AUTH_SECRET_KEY=change-me `
  --from-literal=MINIO_ROOT_PASSWORD=minioadmin
```

---

## 10. Phạm Vi Hiện Tại

- Helm chart là baseline để render/deploy và có thể kiểm thử thêm trên cluster thật.
- Database/Redis/MinIO/Qdrant trong chart phù hợp dev/staging nhỏ; vận hành dài hạn nên cân nhắc managed service.
- Cột database `image_path` tạm thời lưu MinIO object key để giữ tương thích schema hiện tại; có thể đổi rõ thành `image_key`/`object_key` ở migration sau.

---

## 11. Tóm Tắt

Triển khai local chính:

```powershell
docker compose up --build -d
```

Kiểm tra:

```powershell
docker compose ps
Invoke-WebRequest http://localhost:8080/health
```

Triển khai Kubernetes dùng:

```powershell
helm upgrade --install deepface-access helm/deepface-access
```
