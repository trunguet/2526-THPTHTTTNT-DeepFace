# CI/CD

Tài liệu này mô tả pipeline CI/CD hiện tại của repo DeepFace Access Control. Mục tiêu là giúp người đọc biết khi push code thì GitHub Actions làm gì, image nào được build/publish, cần cấu hình Docker Hub ra sao và phạm vi CD hiện tại đang ở mức nào.

Workflow chính nằm ở:

```text
.github/workflows/ci.yml
```

---

## 1. Tổng Quan Pipeline

Pipeline hiện tại là:

```text
push / pull_request
  -> backend tests
  -> worker tests
  -> frontend builds
  -> docker image builds
  -> publish Docker Hub nếu push vào main
```

Nói chính xác:

- repo đã có CI;
- repo đã có artifact publishing lên Docker Hub;
- phần CD hiện tập trung vào publish Docker image artifact.

Vì vậy có thể trình bày là:

```text
CI + Docker image publishing
```

Có thể mô tả phạm vi hiện tại như sau:

```text
CI/CD baseline: CI kiểm thử/build đầy đủ, CD ở mức publish Docker image artifact để sẵn sàng triển khai.
```

---

## 2. Workflow Trigger

GitHub Actions chạy khi:

```yaml
on:
  push:
  pull_request:
```

Nghĩa là:

| Sự kiện | CI có chạy không | Có push Docker Hub không |
|---|---|---|
| Pull request | Có | Không |
| Push branch bất kỳ | Có | Không |
| Push vào `main` | Có | Có, nếu có Docker Hub secrets |

Điều kiện publish image:

```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

---

## 3. GitHub Actions Jobs

Workflow có 4 job chính:

| Job | Mục đích |
|---|---|
| `backend-tests` | Cài dependency backend và chạy backend unit tests. |
| `worker-tests` | Cài dependency worker và chạy worker tests. |
| `frontend-builds` | Build user/admin frontend. |
| `docker-builds` | Build Docker images và publish Docker Hub khi push main. |

Các job này độc lập ở mức GitHub Actions. Nếu một job fail, workflow fail.

---

## 4. Job `backend-tests`

Chạy trên:

```text
ubuntu-latest
```

Dùng:

```text
Python 3.12
```

Các bước chính:

```text
checkout code
setup-python
pip install -r backend/requirements.txt
PYTHONPATH=backend python -m pytest backend/app/tests
```

Job này bắt lỗi:

- API/backend service logic;
- auth/security helper;
- database/service contract;
- image upload validation;
- health/metrics/admin operations;
- các test backend khác trong `backend/app/tests`.

---

## 5. Job `worker-tests`

Chạy trên:

```text
ubuntu-latest
```

Dùng:

```text
Python 3.12
```

Trước khi cài worker dependencies, CI cài system libs:

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends libgl1 libglib2.0-0
```

Lý do: worker dùng OpenCV/DeepFace, một số package cần thư viện hệ thống.

Các bước chính:

```text
checkout code
setup-python
install libgl1 libglib2.0-0
pip install -r worker/requirements.txt
PYTHONPATH=worker python -m pytest worker/app/tests
```

Job này bắt lỗi:

- worker queue/task logic;
- DeepFace wrapper/service contract;
- embedding/access pipeline service;
- Qdrant/vector store wrapper;
- storage/download ảnh cho worker.

---

## 6. Job `frontend-builds`

Chạy trên:

```text
ubuntu-latest
```

Dùng:

```text
Node 22
```

Build hiện tại:

```text
frontend/user
frontend/admin
```

User frontend:

```bash
cd frontend/user
npm ci
npm run build
```

Admin frontend:

```bash
cd frontend/admin
VITE_BASE_PATH=/admin/
npm ci
npm run build
```

Job này bắt lỗi:

- TypeScript build fail;
- import sai;
- component lỗi compile;
- package-lock không khớp;
- build Vite fail.

Lưu ý: `frontend-home` được build trong job Docker image; home frontend là static Nginx đơn giản nên không cần bước `npm/build` riêng.

---

## 7. Job `docker-builds`

Job này build Docker images cho các service app chính.

Images hiện được build:

```text
deepface-backend
deepface-worker
deepface-frontend-user
deepface-frontend-home
deepface-frontend-admin
```

Mỗi image được tag 3 kiểu trong lúc build:

```text
<local-name>:test
<namespace>/<image>:<commit-sha>
<namespace>/<image>:latest
```

Ví dụ:

```text
deepface-backend:test
duclm2006/deepface-backend:554e3ca...
duclm2006/deepface-backend:latest
```

`docker-builds` luôn build image khi CI chạy. Nhưng chỉ push lên Docker Hub khi push vào `main`.

---

## 8. Docker Hub Namespace

Workflow lấy namespace từ secret:

```text
DOCKERHUB_USERNAME
```

Sau đó chuyển về lowercase.

Nếu secret này rỗng, fallback là:

```text
deepface-access
```

Nhưng khi publish thật, nên set đúng Docker Hub username/namespace.

Ví dụ:

```text
duclm2006
```

---

## 9. GitHub Secrets Cần Có

Để publish image lên Docker Hub trên `main`, cần 2 secrets:

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

Ý nghĩa:

| Secret | Ý nghĩa |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub username/namespace, ví dụ `duclm2006`. |
| `DOCKERHUB_TOKEN` | Docker Hub Personal Access Token dùng để `docker login`. |

Nếu thiếu secret:

- CI vẫn có thể chạy test/build;
- bước login/push Docker Hub sẽ fail khi push main.

---

## 10. Docker Images Được Publish

Khi push vào `main`, workflow push:

```text
<dockerhub-username>/deepface-backend:<commit-sha>
<dockerhub-username>/deepface-backend:latest

<dockerhub-username>/deepface-worker:<commit-sha>
<dockerhub-username>/deepface-worker:latest

<dockerhub-username>/deepface-frontend-user:<commit-sha>
<dockerhub-username>/deepface-frontend-user:latest

<dockerhub-username>/deepface-frontend-home:<commit-sha>
<dockerhub-username>/deepface-frontend-home:latest

<dockerhub-username>/deepface-frontend-admin:<commit-sha>
<dockerhub-username>/deepface-frontend-admin:latest
```

Tag `<commit-sha>` dùng để deploy đúng version code.

Tag `latest` dùng cho môi trường dev/trình bày nhanh.

---

## 11. Image Chưa Publish Trong CI

Docker Compose hiện có thêm service:

```text
cron-backup
```

Image:

```text
<namespace>/deepface-cron-backup:<tag>
```

Service này build được local từ:

```text
backup/cron
```

Workflow `ci.yml` hiện tập trung build/push các image app chính; `deepface-cron-backup` có thể bổ sung vào pipeline ở bước mở rộng.

Ý nghĩa:

- `docker compose up --build -d` local vẫn chạy được vì Compose tự build từ `backup/cron`;
- `docker compose up --build -d` local vẫn chạy được vì Compose tự build từ `backup/cron`;
- nếu triển khai bằng image pull thuần từ Docker Hub, nên bổ sung build/push `deepface-cron-backup` vào job `docker-builds`.

---

## 12. Docker Hub Readiness Check

Repo có script:

```text
scripts/check-dockerhub-readiness.ps1
```

Script kiểm tra:

1. Docker Compose image names có đúng namespace/tag không;
2. Helm template có dùng đúng image không;
3. Docker Hub remote có tag cần tìm không, nếu không dùng `-SkipRemote`.

Kiểm tra local config trước khi image được publish:

```powershell
.\scripts\check-dockerhub-readiness.ps1 -Namespace <dockerhub-username> -ImageTag latest -SkipRemote
```

Kiểm tra sau khi CI đã push image:

```powershell
.\scripts\check-dockerhub-readiness.ps1 -Namespace <dockerhub-username> -ImageTag latest
```

Pass nghĩa là:

- Compose đang trỏ đúng image;
- Helm đang render đúng image;
- Docker Hub có tag remote thật.

Lưu ý: script hiện kiểm tra 5 image app chính:

```text
deepface-backend
deepface-worker
deepface-frontend-user
deepface-frontend-home
deepface-frontend-admin
```

---

## 13. Liên Hệ Với Docker Compose

Docker Compose dùng image theo format:

```text
${DOCKERHUB_NAMESPACE:-your-dockerhub-username}/<image-name>:${IMAGE_TAG:-latest}
```

Ví dụ:

```powershell
$env:DOCKERHUB_NAMESPACE="duclm2006"
$env:IMAGE_TAG="latest"
docker compose config --images
```

Khi chạy local:

```powershell
docker compose up --build -d
```

Compose sẽ build local từ source hiện tại và tag theo namespace/image tag.

Khi muốn pull image đã publish:

```powershell
docker compose pull
docker compose up -d
```

---

## 14. Liên Hệ Với Helm/Kubernetes

Helm chart nằm ở:

```text
helm/deepface-access
```

Deploy bằng image đã publish:

```powershell
helm upgrade --install deepface-access helm/deepface-access `
  --set global.imageRegistry=<dockerhub-username> `
  --set global.imageTag=<commit-sha>
```

Nếu dùng repo private, tạo image pull secret:

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

Lưu ý hiện tại:

- Helm chart là baseline;
- auto deploy từ GitHub Actions sang Kubernetes là hướng mở rộng tiếp theo;
- Helm values cần được đồng bộ nếu Docker Compose đổi cấu hình AI.

---

## 15. Local Check Trước Khi Push

Trước khi push, nên chạy:

```powershell
.\scripts\test.ps1
```

Build Docker các service chính:

```powershell
docker compose build backend worker frontend-user frontend-admin frontend-home
```

Nếu muốn kiểm tra full build Compose:

```powershell
docker compose up --build -d
```

Kiểm tra Docker Hub config:

```powershell
.\scripts\check-dockerhub-readiness.ps1 -Namespace <dockerhub-username> -ImageTag latest -SkipRemote
```

---

## 16. Những Gì CI Đang Bắt Lỗi Tốt

CI hiện bắt được:

- backend test fail;
- worker test fail;
- frontend TypeScript/build fail;
- Dockerfile app chính build fail;
- Docker Hub image naming sai ở một mức nhất định qua readiness script local nếu chạy thủ công.

CI giúp tránh push code hỏng vào `main`.

---

## 17. Phạm Vi Hiện Tại Và Hướng Mở Rộng

Các hướng mở rộng để pipeline hoàn thiện hơn:

- auto deploy lên VPS/server;
- auto deploy lên Kubernetes;
- smoke test Docker Compose sau khi build;
- browser E2E test bằng Playwright;
- test webcam trong môi trường E2E;
- test DeepFace model weight trong CI full stack hoặc workflow riêng;
- publish `deepface-cron-backup` image trong CI;
- Helm lint/template trong workflow chính;
- release/changelog tự động.

Đây là các phần có thể phát triển tiếp nếu muốn tăng mức CD.

---

## 18. Cách Nâng Cấp Thành CD Đúng Nghĩa

Nếu muốn biến pipeline thành CD rõ hơn, có 2 hướng hợp lý.

### 18.1. CD lên VPS

Sau khi push image lên Docker Hub:

```text
GitHub Actions SSH vào VPS
  -> git pull hoặc cập nhật .env
  -> docker compose pull
  -> docker compose up -d
  -> health check /health
```

Ưu điểm:

- dễ làm;
- phù hợp với phạm vi bài tập lớn;
- dùng lại Docker Compose hiện có.

Nhược điểm:

- cần VPS;
- cần quản lý secret SSH;
- chưa tận dụng đầy đủ cơ chế Kubernetes-native.

### 18.2. CD lên Kubernetes bằng Helm

Sau khi push image:

```text
GitHub Actions login cluster
  -> helm upgrade --install
  -> kubectl rollout status
```

Ưu điểm:

- khớp bonus Kubernetes/Helm;
- chuyên nghiệp hơn.

Nhược điểm:

- cần cluster;
- cấu hình secret/storage/ingress phức tạp hơn.

---

## 19. Cách Trình Bày

Có thể trình bày ngắn gọn:

```text
Project có CI chạy backend tests, worker tests, frontend builds và Docker image builds trên mọi push/PR.
Khi merge/push vào main, workflow login Docker Hub và publish 5 image chính với tag commit SHA và latest.
Các image này được Docker Compose và Helm chart sử dụng để triển khai.
Hiện pipeline publish image artifact lên Docker Hub; auto deploy lên VPS/Kubernetes là hướng mở rộng tiếp theo.
```

---

## 20. Tóm Tắt Ngắn

Pipeline hiện tại:

```text
backend tests
worker tests
frontend builds
Docker image builds
Docker Hub publish on main
```

Images publish:

```text
backend
worker
frontend-user
frontend-home
frontend-admin
```

Chưa publish:

```text
cron-backup
```

Chưa có:

```text
auto deploy VPS/Kubernetes
```

Kết luận: repo đã có CI tốt và publish artifact lên Docker Hub. Để thành CD đầy đủ, bước tiếp theo là tự động deploy image đã publish lên VPS hoặc Kubernetes bằng Helm.
