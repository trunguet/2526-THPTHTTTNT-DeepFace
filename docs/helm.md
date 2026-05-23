# Helm Deployment

Tài liệu này mô tả cách dùng Helm chart trong repo để triển khai DeepFace Access Control lên Kubernetes.

Chart nằm ở:

```text
helm/deepface-access
```

---

## 1. Tổng Quan Chart

Helm chart hiện là baseline cho môi trường demo/staging nhỏ.

Chart có template cho:

| Thành phần | Kubernetes resource |
|---|---|
| Backend | Deployment + Service |
| Worker | Deployment |
| Frontend User | Deployment + Service |
| Frontend Admin | Deployment + Service |
| PostgreSQL | Deployment + Service + PVC |
| Redis | Deployment + Service |
| MinIO | Deployment + Service + PVC |
| Qdrant | Deployment + Service + PVC |
| Nginx/Ingress | Ingress |

Chart dùng Docker images theo format:

```text
<global.imageRegistry>/<imageRepository>:<global.imageTag>
```

---

## 2. Yêu Cầu Trước Khi Cài

Cần có:

- Kubernetes cluster;
- `kubectl`;
- Helm 3;
- Docker images đã được build/push lên Docker Hub hoặc registry khác;
- namespace/secret cần thiết nếu dùng image private.

Kiểm tra:

```powershell
kubectl version --client
helm version
kubectl get nodes
```

---

## 3. Kiểm Tra Chart

Lint:

```powershell
helm lint helm/deepface-access
```

Render manifest:

```powershell
helm template deepface-access helm/deepface-access
```

Render với Docker Hub namespace:

```powershell
helm template deepface-access helm/deepface-access `
  --set global.imageRegistry=<dockerhub-username> `
  --set global.imageTag=latest
```

---

## 4. Cấu Hình Quan Trọng

File:

```text
helm/deepface-access/values.yaml
```

Các giá trị chính:

```yaml
global:
  imageRegistry: your-dockerhub-username
  imageTag: latest
  imagePullSecrets: []

backend:
  imageRepository: deepface-backend

worker:
  imageRepository: deepface-worker

frontendUser:
  imageRepository: deepface-frontend-user

frontendAdmin:
  imageRepository: deepface-frontend-admin
```

Config ứng dụng:

```yaml
config:
  appEnv: prod
  databaseUrl: postgresql://deepface:deepface@deepface-access-database:5432/deepface_access
  redisUrl: redis://deepface-access-redis:6379/0
  corsOrigins: https://deepface.example.local
  viteApiBaseUrl: /api
  deepfaceModelName: Facenet512
  deepfaceDetectorBackend: opencv
  deepfaceMatchThreshold: "0.70"
  minioEndpoint: deepface-access-minio:9000
  qdrantUrl: http://deepface-access-qdrant:6333
```

Lưu ý: nếu Docker Compose đã đổi detector/model, nên đồng bộ lại `values.yaml`.

---

## 5. Secret

Chart tham chiếu secret:

```text
deepface-access-secrets
```

Secret này dùng cho backend, worker, PostgreSQL và MinIO.

Ví dụ tạo secret:

```powershell
kubectl create secret generic deepface-access-secrets `
  --from-literal=POSTGRES_PASSWORD=deepface `
  --from-literal=AUTH_SECRET_KEY=change-me `
  --from-literal=MINIO_ROOT_PASSWORD=minioadmin
```

Nếu dùng Docker Hub private, tạo image pull secret:

```powershell
kubectl create secret docker-registry dockerhub-pull `
  --docker-server=https://index.docker.io/v1/ `
  --docker-username=<dockerhub-username> `
  --docker-password=<dockerhub-token>
```

---

## 6. Cài Chart Nhanh

```powershell
helm upgrade --install deepface-access helm/deepface-access `
  --set global.imageRegistry=<dockerhub-username> `
  --set global.imageTag=latest
```

Nếu dùng image pull secret:

```powershell
helm upgrade --install deepface-access helm/deepface-access `
  --set global.imageRegistry=<dockerhub-username> `
  --set global.imageTag=latest `
  --set global.imagePullSecrets[0].name=dockerhub-pull
```

Kiểm tra:

```powershell
kubectl get pods
kubectl get svc
kubectl get ingress
```

---

## 7. Ingress

Bật ingress:

```powershell
helm upgrade --install deepface-access helm/deepface-access `
  --set ingress.enabled=true `
  --set ingress.host=deepface.example.local
```

Nếu test local, thêm host trên Windows bằng terminal admin:

```powershell
notepad C:\Windows\System32\drivers\etc\hosts
```

Thêm:

```text
127.0.0.1 deepface.example.local
```

Lưu ý:

- cần có ingress controller;
- chart chưa cấu hình TLS mặc định;
- có thể bổ sung cert-manager khi triển khai thật.

---

## 8. MinIO Và Qdrant

Trong `values.yaml`:

```yaml
minio:
  enabled: false

qdrant:
  enabled: false
```

Khi muốn chart tự deploy MinIO/Qdrant:

```powershell
helm upgrade --install deepface-access helm/deepface-access `
  --set minio.enabled=true `
  --set qdrant.enabled=true
```

Nếu dùng service ngoài cluster, giữ `enabled=false` và chỉnh:

```yaml
config:
  minioEndpoint: <external-minio>
  qdrantUrl: <external-qdrant>
```

---

## 9. Cập Nhật Release

Update image tag:

```powershell
helm upgrade deepface-access helm/deepface-access `
  --set global.imageRegistry=<dockerhub-username> `
  --set global.imageTag=<commit-sha>
```

Rollback:

```powershell
helm history deepface-access
helm rollback deepface-access <revision>
```

Gỡ release:

```powershell
helm uninstall deepface-access
```

Xóa PVC nếu muốn xóa cả dữ liệu:

```powershell
kubectl delete pvc -l app.kubernetes.io/instance=deepface-access
```

Nên backup trước khi xóa PVC.

---

## 10. Phạm Vi Hiện Tại

Chart hiện có thể render/deploy baseline. Các hướng mở rộng:

- thêm template cho `frontend-home`;
- thêm Job seed/migration rõ ràng;
- thêm monitoring Prometheus/Grafana vào chart;
- thêm backup CronJob;
- thêm TLS/HTTPS;
- thêm resource requests/limits;
- thêm HorizontalPodAutoscaler;
- thêm PodDisruptionBudget;
- thêm Alembic migration job.

---

## 11. Troubleshooting

| Vấn đề | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Backend không kết nối DB | Sai `config.databaseUrl` hoặc secret DB | Kiểm tra service name và password |
| Worker không xử lý job | Sai Redis URL, Qdrant/MinIO chưa bật | Kiểm tra `config.redisUrl`, `minio.enabled`, `qdrant.enabled` |
| ImagePullBackOff | Sai registry/tag hoặc image private | Kiểm tra `global.imageRegistry`, `global.imageTag`, image pull secret |
| Ingress không vào được | Chưa có ingress controller hoặc sai host | Cài ingress-nginx, kiểm tra DNS/hosts |
| Dữ liệu mất sau khi gỡ release | PVC đã bị xóa | Backup trước khi delete PVC |

---

## 12. Tóm Tắt

Kiểm tra chart:

```powershell
helm lint helm/deepface-access
helm template deepface-access helm/deepface-access
```

Deploy:

```powershell
helm upgrade --install deepface-access helm/deepface-access `
  --set global.imageRegistry=<dockerhub-username> `
  --set global.imageTag=latest
```

Chart là nền tảng Kubernetes baseline cho project, phù hợp để trình bày hướng triển khai bằng Helm.
