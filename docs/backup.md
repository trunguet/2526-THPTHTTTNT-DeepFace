# Sao Lưu Và Khôi Phục Dữ Liệu

Tài liệu này mô tả cơ chế backup hiện tại của DeepFace Access Control. Mục tiêu là giúp người đọc hiểu hệ thống backup những gì, backup đi đâu, chạy bằng cách nào, kiểm tra ra sao và khôi phục như thế nào.

Các lệnh bên dưới mặc định chạy trên Windows PowerShell.

---

## 1. Tổng Quan

Repo hiện có 3 hướng backup:

| Cách backup | File/service | Mục đích |
|---|---|---|
| Backup local | `scripts/backup.ps1` | Dump PostgreSQL ra thư mục `backup/`, đồng thời zip `data/` nếu có. |
| Backup S3 từ host | `scripts/backup-s3.ps1` | Dump PostgreSQL rồi upload lên AWS S3/MinIO/S3-compatible storage. |
| Backup tự động trong Docker | `cron-backup` | Container chạy cron 5 ngày/lần, dump PostgreSQL và upload vào MinIO/S3. |

Trong Docker Compose, backup tự động dùng MinIO local làm S3-compatible storage.

```text
PostgreSQL
  -> pg_dump
  -> postgres.sql
  -> MinIO/S3 bucket
```

---

## 2. Backup Những Gì?

### 2.1. Được backup

| Thành phần | Có backup không | Ghi chú |
|---|---|---|
| PostgreSQL | Có | Chứa users, employees, cameras, face_embeddings, access_logs. |
| `data/` local | Có khi dùng `scripts/backup.ps1` | Script local zip thư mục `data/` nếu tồn tại. |
| Manifest | Có | Ghi metadata backup và gợi ý restore. |

### 2.2. Chưa backup đầy đủ

| Thành phần | Trạng thái |
|---|---|
| MinIO bucket ảnh | Chưa mirror toàn bộ bucket tự động. |
| Qdrant vector index | Chưa snapshot tự động. |
| Redis queue | Không backup, vì queue chỉ là dữ liệu tạm thời. |
| Grafana/Prometheus volume | Không nằm trong backup chính. |

Phạm vi backup hiện tại:

- PostgreSQL là dữ liệu nghiệp vụ chính.
- Qdrant là index vector, có thể rebuild từ embedding/source image nếu bổ sung reindex.
- Redis queue là hàng đợi tạm.
- Ảnh trong MinIO nên có chiến lược backup riêng khi triển khai môi trường vận hành thật.

---

## 3. Backup Local Bằng `scripts/backup.ps1`

### 3.1. Mục đích

Dùng khi muốn tạo bản backup nhanh trên máy local.

Script làm 3 việc:

1. tạo thư mục theo timestamp;
2. dump PostgreSQL từ container `database`;
3. zip thư mục `data/` nếu có;
4. tạo `manifest.txt`;
5. xóa backup cũ theo retention.

### 3.2. Chạy backup

```powershell
.\scripts\backup.ps1
```

### 3.3. Output

```text
backup/<yyyyMMdd-HHmmss>/
  postgres.sql
  data.zip
  manifest.txt
```

Ví dụ:

```text
backup/20260521-153000/postgres.sql
backup/20260521-153000/data.zip
backup/20260521-153000/manifest.txt
```

### 3.4. Retention

Mặc định giữ 10 bản backup local gần nhất.

Đổi số bản giữ lại:

```powershell
.\scripts\backup.ps1 -Keep 20
```

### 3.5. Điều kiện cần

Database container phải đang chạy:

```powershell
docker compose up -d database
```

Kiểm tra:

```powershell
docker compose ps database
```

---

## 4. Backup Lên S3/MinIO Bằng `scripts/backup-s3.ps1`

### 4.1. Mục đích

Dùng khi muốn backup PostgreSQL lên một storage ngoài máy local:

- AWS S3;
- MinIO;
- Cloudflare R2;
- hoặc S3-compatible storage khác.

### 4.2. Luồng hoạt động

```text
PowerShell script
  -> docker compose exec database pg_dump
  -> tạo postgres.sql
  -> tạo manifest.txt
  -> aws s3 cp lên bucket
  -> xóa hoặc giữ bản local tùy KeepLocal
```

### 4.3. Biến môi trường quan trọng

Có thể set trực tiếp trong terminal hoặc tạo file:

```text
scripts/backup-s3.env
```

Các biến chính:

```text
S3_BUCKET=
S3_PREFIX=deepface-db-backups
S3_ENDPOINT_URL=
S3_USE_DOCKER_CLI=
AWS_REGION=us-east-1
AWS_PROFILE=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
S3_LOG_PATH=
```

Ý nghĩa:

| Biến | Ý nghĩa |
|---|---|
| `S3_BUCKET` | Bucket đích. Bắt buộc. |
| `S3_PREFIX` | Folder/prefix trong bucket. Default `deepface-db-backups`. |
| `S3_ENDPOINT_URL` | Endpoint custom, ví dụ MinIO `http://localhost:9000`. |
| `S3_USE_DOCKER_CLI` | Dùng AWS CLI trong Docker nếu máy chưa cài AWS CLI. |
| `AWS_REGION` | Region. |
| `AWS_PROFILE` | Profile AWS local nếu dùng. |
| `AWS_ACCESS_KEY_ID` | Access key. |
| `AWS_SECRET_ACCESS_KEY` | Secret key. |
| `S3_LOG_PATH` | File log nếu muốn ghi log. |

### 4.4. Chạy backup

```powershell
.\scripts\backup-s3.ps1
```

Ép dùng AWS CLI qua Docker:

```powershell
.\scripts\backup-s3.ps1 -UseDockerAwsCli
```

Giữ lại 5 bản local sau khi upload:

```powershell
.\scripts\backup-s3.ps1 -KeepLocal 5
```

Ghi log:

```powershell
.\scripts\backup-s3.ps1 -LogPath logs\backup-s3.log
```

### 4.5. Output trên S3/MinIO

```text
s3://<bucket>/<prefix>/<yyyyMMdd-HHmmss>/postgres.sql
s3://<bucket>/<prefix>/<yyyyMMdd-HHmmss>/manifest.txt
```

---

## 5. Backup Tự Động Trong Docker Compose

### 5.1. Service `cron-backup`

Docker Compose có service:

```text
cron-backup
```

Source nằm ở:

```text
backup/cron/
  Dockerfile
  backup.sh
  backup.cron
```

`Dockerfile` cài:

- `postgresql-client` để chạy `pg_dump`;
- `aws-cli` để upload S3/MinIO;
- `supercronic` để chạy cron ổn định trong container.

### 5.2. Lịch backup

File:

```text
backup/cron/backup.cron
```

Nội dung:

```text
0 0 */5 * * /usr/local/bin/backup.sh
```

Nghĩa là:

```text
Chạy lúc 00:00, mỗi 5 ngày một lần.
```

Timezone là timezone trong container, thường là UTC nếu không cấu hình thêm.

### 5.3. Biến môi trường từ Docker Compose

`docker-compose.yml` inject các biến:

```text
S3_BUCKET=${MINIO_BUCKET:-deepface-images}
S3_ENDPOINT_URL=${S3_ENDPOINT_URL:-http://minio:9000}
AWS_ACCESS_KEY_ID=${MINIO_ROOT_USER:-minioadmin}
AWS_SECRET_ACCESS_KEY=${MINIO_ROOT_PASSWORD:-minioadmin}
AWS_REGION=${AWS_REGION:-us-east-1}
S3_PREFIX=${S3_PREFIX:-deepface-db-backups}

POSTGRES_HOST=${POSTGRES_HOST:-database}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-deepface_access}
POSTGRES_USER=${POSTGRES_USER:-deepface}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-deepface}
```

Trong local Docker, upload đi tới MinIO nội bộ:

```text
http://minio:9000
```

Bucket default:

```text
deepface-images
```

Prefix default:

```text
deepface-db-backups
```

### 5.4. Khởi động backup service

Nếu chạy toàn bộ hệ thống:

```powershell
docker compose up --build -d
```

Nếu chỉ chạy service backup sau khi database đã sẵn sàng:

```powershell
docker compose up --build -d cron-backup
```

Kiểm tra:

```powershell
docker compose ps cron-backup
docker compose logs --no-color --tail=50 cron-backup
```

Log tốt thường có:

```text
read crontab: /etc/supercronic/backup.cron
```

---

## 6. Chạy Backup Ngay Lập Tức

Không cần chờ cron 5 ngày/lần. Có thể chạy thủ công:

```powershell
docker compose exec cron-backup /usr/local/bin/backup.sh
```

Nếu thành công sẽ thấy log dạng:

```text
Creating PostgreSQL dump...
Uploading to s3://deepface-images/deepface-db-backups/<timestamp>...
Backup uploaded to s3://deepface-images/deepface-db-backups/<timestamp>
```

Kiểm tra object đã có trong MinIO:

```powershell
docker compose exec cron-backup aws s3 ls s3://deepface-images/deepface-db-backups/ --endpoint-url http://minio:9000
```

Kiểm tra một bản cụ thể:

```powershell
docker compose exec cron-backup aws s3 ls s3://deepface-images/deepface-db-backups/<timestamp>/ --endpoint-url http://minio:9000
```

Kết quả mong đợi:

```text
postgres.sql
manifest.txt
```

---

## 7. Tạo Bucket MinIO/S3

### 7.1. MinIO trong Docker Compose

Thông tin default:

```text
URL Console: http://localhost:9001
Username: minioadmin
Password: minioadmin
Bucket: deepface-images
```

Nếu bucket chưa tồn tại, có thể tạo bằng MinIO Console hoặc `mc`.

Dùng `mc`:

```powershell
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/deepface-images
```

### 7.2. AWS S3 thật

```powershell
aws s3 mb s3://<bucket-name>
```

Sau đó set:

```powershell
$env:S3_BUCKET="<bucket-name>"
$env:AWS_REGION="<region>"
$env:AWS_ACCESS_KEY_ID="<access-key>"
$env:AWS_SECRET_ACCESS_KEY="<secret-key>"
```

---

## 8. Restore PostgreSQL Từ Local Backup

### 8.1. Chuẩn bị

Đảm bảo database container đang chạy:

```powershell
docker compose up -d database
```

### 8.2. Restore

```powershell
Get-Content backup\<timestamp>\postgres.sql | docker compose exec -T database sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Ví dụ:

```powershell
Get-Content backup\20260521-153000\postgres.sql | docker compose exec -T database sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Lưu ý:

- Restore ghi dữ liệu vào database hiện tại.
- Nếu DB đã có dữ liệu trùng, có thể phát sinh conflict tùy nội dung dump.
- Khi trình bày/kiểm thử restore, nên dùng môi trường sạch để kết quả dễ kiểm chứng.

---

## 9. Restore PostgreSQL Từ S3/MinIO

### 9.1. Từ AWS S3

```powershell
aws s3 cp s3://<bucket>/<prefix>/<timestamp>/postgres.sql - | docker compose exec -T database sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### 9.2. Từ MinIO local

Nếu chạy từ máy host:

```powershell
aws s3 cp s3://deepface-images/deepface-db-backups/<timestamp>/postgres.sql - --endpoint-url http://localhost:9000 | docker compose exec -T database sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Nếu chạy trong container có network Docker, endpoint là:

```text
http://minio:9000
```

---

## 10. Restore `data/`

Nếu dùng `scripts/backup.ps1`, script có thể tạo:

```text
data.zip
```

Restore:

```powershell
Expand-Archive backup\<timestamp>\data.zip -DestinationPath data -Force
```

Lưu ý: ảnh upload thật hiện đi qua MinIO volume, không nhất thiết nằm trong `data/`.

---

## 11. Cách Test Backup Cho Demo

### 11.1. Test Docker backup

```powershell
docker compose up --build -d
docker compose ps cron-backup
docker compose exec cron-backup /usr/local/bin/backup.sh
docker compose exec cron-backup aws s3 ls s3://deepface-images/deepface-db-backups/ --endpoint-url http://minio:9000
```

Pass khi:

- `cron-backup` đang `Up`;
- lệnh `backup.sh` không lỗi;
- MinIO có folder timestamp mới.

### 11.2. Test kiểu bạn khác pull repo về

Sau khi commit/push các file:

```text
backup/cron/Dockerfile
backup/cron/backup.sh
backup/cron/backup.cron
docker-compose.yml
```

Bạn khác chỉ cần:

```powershell
git pull
docker compose up --build -d
docker compose exec cron-backup /usr/local/bin/backup.sh
```

Nếu thấy upload thành công vào MinIO thì backup hoạt động.

---

## 12. Windows Scheduled Task

Ngoài cron container, repo còn có script tạo lịch backup trên Windows:

```text
scripts/schedule-backup-s3.ps1
```

Tạo task chạy 5 ngày/lần lúc 02:00:

```powershell
.\scripts\schedule-backup-s3.ps1 -StartTime 02:00 -LogPath logs\backup-s3.log
```

Tạo task và chạy ngay:

```powershell
.\scripts\schedule-backup-s3.ps1 -StartTime 02:00 -LogPath logs\backup-s3.log -RunNow
```

Kiểm tra task:

```powershell
schtasks /Query /TN DeepFaceBackupS3 /V /FO LIST | Select-String "Next Run Time|Last Run Time|Last Result|Status"
```

Xem log:

```powershell
Get-Content logs\backup-s3.log -Tail 50
```

Trong Docker Compose, `cron-backup` dễ kiểm chứng vì chạy cùng stack.

---

## 13. Troubleshooting

| Lỗi | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `path "./backup/cron" not found` | Thiếu thư mục `backup/cron` | Commit/pull đủ `Dockerfile`, `backup.sh`, `backup.cron`. |
| `S3_BUCKET is required` | Chưa set bucket | Set `S3_BUCKET` hoặc dùng default `MINIO_BUCKET=deepface-images` trong Compose. |
| `PostgreSQL env is required` | Thiếu DB env trong cron container | Kiểm tra `docker-compose.yml` phần `cron-backup.environment`. |
| `Could not connect to server` | Database chưa chạy/healthy | `docker compose ps database`, chờ healthy rồi chạy lại. |
| `AccessDenied` | Sai MinIO/S3 credentials | Kiểm tra `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`. |
| `NoSuchBucket` | Bucket chưa tồn tại | Tạo bucket `deepface-images`. |
| `aws: command not found` | Host chưa có AWS CLI khi dùng script host | Dùng `-UseDockerAwsCli` hoặc cài AWS CLI. |
| Cron không chạy | Container `cron-backup` dừng | `docker compose ps cron-backup`, xem logs. |

---

## 14. Phạm Vi Hiện Tại Và Hướng Mở Rộng

Backup hiện tại tập trung vào PostgreSQL, là dữ liệu nghiệp vụ quan trọng nhất của hệ thống.

Các hướng mở rộng:

- Mirror toàn bộ MinIO bucket ảnh.
- Bổ sung Qdrant snapshot hoặc reindex job.
- Bổ sung retention tự động cho backup trong MinIO/S3.
- Bổ sung mã hóa backup ở application level nếu cần.
- Bổ sung restore script một lệnh.

Nếu triển khai vận hành dài hạn, nên bổ sung:

- backup/mirror MinIO bucket;
- Qdrant snapshot hoặc reindex job rõ ràng;
- retention policy theo ngày/tuần/tháng;
- kiểm tra restore định kỳ;
- lưu backup ở storage ngoài server chính.

---

## 15. Tóm Tắt Ngắn

Backup hiện tại có 2 lớp chính:

```text
Local: scripts/backup.ps1 -> backup/<timestamp>/
Docker: cron-backup -> pg_dump -> MinIO/S3
```

Khi trình bày, cách kiểm chứng quan trọng nhất là:

```powershell
docker compose exec cron-backup /usr/local/bin/backup.sh
docker compose exec cron-backup aws s3 ls s3://deepface-images/deepface-db-backups/ --endpoint-url http://minio:9000
```

Nếu thấy folder timestamp mới chứa `postgres.sql` và `manifest.txt`, phần backup PostgreSQL đã hoạt động.
