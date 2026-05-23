# Demo Checklist

Tài liệu này là checklist ngắn để giảng viên hoặc thành viên nhóm test nhanh DeepFace Access Control. Các mục bên dưới tập trung vào những flow tốt nhất nên trình bày.

---

## 1. Khởi Động Stack

Chạy tại root repo:

```powershell
docker compose up --build -d
```

Kiểm tra baseline:

```powershell
docker compose ps
Invoke-WebRequest http://localhost:8080/health
```

Kết quả mong đợi:

- các service chính ở trạng thái running/healthy;
- Gateway, User UI, Admin UI, MinIO, Qdrant, Prometheus và Grafana mở được;
- `/health` trả `status=ok`.

---

## 2. Các URL Cần Mở

| Thành phần | URL |
|---|---|
| Home | `http://localhost:8080` |
| User UI | `http://localhost:8080/user/` |
| Admin UI | `http://localhost:8080/admin/` |
| Swagger | `http://localhost:8080/docs` |
| MinIO | `http://localhost:9001` |
| Qdrant | `http://localhost:6333/dashboard` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |

---

## 3. Login

Admin:

```text
admin / admin123
```

User:

```text
user / user123
```

Grafana:

```text
admin / admin
```

MinIO:

```text
minioadmin / minioadmin
```

---

## 4. Admin Flow: Quản Lý Employee

Vào:

```text
http://localhost:8080/admin/
```

Các bước:

1. Đăng nhập bằng `admin / admin123`.
2. Mở mục Employees.
3. Tạo employee mới với code, name, department.
4. Upload ảnh khuôn mặt cho employee.
5. Kiểm tra cột Embedding chuyển sang `pending`, sau đó `success`.

Kết quả mong đợi:

- employee mới nằm trong Employee list;
- face image được queue xử lý embedding;
- admin thao tác được trên UI, không cần dùng Swagger.

---

## 5. User Flow: Check Access

Vào:

```text
http://localhost:8080/user/
```

Các bước:

1. Đăng nhập bằng `user / user123`.
2. Mở tab Access.
3. Bấm Start camera.
4. Đứng một người trong khung hình.
5. Dùng khuôn mặt đã đăng ký để quét.
6. Xem result card và History.

Kết quả mong đợi:

- khi match employee active: result là `granted`, score hiển thị trên UI;
- khi không match hoặc frame lỗi: result là `denied` hoặc `error`, UI hiển thị thông báo rõ;
- snapshot được upload và access log được cập nhật sau khi worker xử lý.

---

## 6. Smoke Test AI

Chạy smoke test DeepFace trong worker container:

```powershell
.\scripts\smoke-deepface.ps1
```

Kết quả mong đợi:

- worker import và chạy được DeepFace trong Docker;
- embedding được tạo bằng DeepFace;
- Qdrant search được vector;
- PostgreSQL access log được cập nhật đúng status;
- test có các case `granted`, `denied`, `error`.

---

## 7. MinIO

Mở:

```text
http://localhost:9001
```

Kiểm tra:

- đăng nhập `minioadmin / minioadmin`;
- bucket `deepface-images` tồn tại;
- có object ảnh employee hoặc access snapshot sau khi upload/check access.

---

## 8. Qdrant

Mở:

```text
http://localhost:6333/dashboard
```

Kiểm tra:

- collection `deepface_embeddings`;
- collection có vector sau khi employee embedding `success`.

---

## 9. Monitoring

Kiểm tra metrics:

```powershell
Invoke-WebRequest http://localhost:8080/metrics
```

Cần thấy:

```text
deepface_backend_up
deepface_database_up
deepface_redis_up
deepface_queue_length
deepface_access_logs_total
```

Prometheus:

```text
http://localhost:9090/targets
```

Grafana:

```text
http://localhost:3000
```

Dashboard:

```text
DeepFace Access Overview
```

---

## 10. CI/Docker Hub

Kiểm tra workflow:

```text
GitHub -> Actions -> CI
```

Kiểm tra Docker Hub local config trước khi push:

```powershell
.\scripts\check-dockerhub-readiness.ps1 -Namespace <dockerhub-username> -ImageTag latest -SkipRemote
```

Sau khi image đã được publish:

```powershell
.\scripts\check-dockerhub-readiness.ps1 -Namespace <dockerhub-username> -ImageTag latest
```

---

## 11. Helm

Kiểm tra chart:

```powershell
helm lint helm/deepface-access
helm template deepface-access helm/deepface-access
```

Render với Docker Hub namespace:

```powershell
helm template deepface-access helm/deepface-access `
  --set global.imageRegistry=<dockerhub-username> `
  --set global.imageTag=latest
```

Kết quả mong đợi:

- Helm chart render được manifest Kubernetes;
- image repository/tag đúng namespace.

---

## 12. Backup

Chạy backup ngay:

```powershell
docker compose exec cron-backup /usr/local/bin/backup.sh
```

Kiểm tra backup trong MinIO:

```powershell
docker compose exec cron-backup aws s3 ls s3://deepface-images/deepface-db-backups/ --endpoint-url http://minio:9000
```

Kết quả mong đợi:

- có folder timestamp mới;
- trong folder có `postgres.sql`;
- có `manifest.txt` để biết backup được tạo lúc nào.

---

## 13. Luồng Trình Bày Gợi Ý

1. Mở Home.
2. Mở Admin UI, tạo employee.
3. Upload face image và chờ embedding `success`.
4. Mở User UI.
5. Start camera.
6. Quét mặt đúng người -> `granted`.
7. Quét sai/nhiều mặt/không có mặt -> `denied` hoặc `error`.
8. Mở History/Admin Logs để xem log.
9. Mở Grafana/Prometheus/MinIO/Qdrant nếu được hỏi về service vận hành.
10. Chạy backup hoặc smoke test nếu cần chứng minh runtime.
