# Monitoring

Tài liệu này mô tả hệ thống monitoring hiện tại của DeepFace Access Control. Monitoring dùng backend health/metrics, Docker healthcheck, Prometheus, Alertmanager và Grafana.

---

## 1. Tổng Quan

Mục tiêu monitoring:

- biết backend còn sống không;
- biết backend có kết nối được PostgreSQL và Redis không;
- theo dõi độ dài Redis queue;
- theo dõi access logs theo trạng thái;
- cảnh báo khi dependency lỗi hoặc queue bị backlog;
- có dashboard Grafana để kiểm tra và trình bày nhanh.

Sơ đồ:

```text
Backend /metrics
      ^
      |
Prometheus
  |       |
  v       v
Grafana  Alertmanager
```

---

## 2. Các Thành Phần

| Thành phần | Service | Port | Vai trò |
|---|---|---|---|
| Backend health | `backend` | `8000` | Endpoint `/health`. |
| Backend metrics | `backend` | `8000` | Endpoint `/metrics`. |
| Prometheus | `prometheus` | `9090` | Scrape metrics và evaluate alert rules. |
| Grafana | `grafana` | `3000` | Dashboard hiển thị metrics. |
| Alertmanager | `alertmanager` | `9093` | Nhận alert từ Prometheus. |
| Docker healthcheck | nhiều service | internal | Kiểm tra trạng thái container. |

Qua Nginx:

```text
http://localhost:8080/health
http://localhost:8080/metrics
```

Trực tiếp backend:

```text
http://localhost:8000/health
http://localhost:8000/metrics
```

---

## 3. Backend Health

Endpoint:

```text
GET /health
```

Không cần token.

Khi ổn:

```json
{
  "status": "ok",
  "service": "backend",
  "environment": "dev",
  "database": "ok",
  "redis": "ok"
}
```

Khi PostgreSQL hoặc Redis lỗi:

```json
{
  "status": "error",
  "service": "backend",
  "environment": "dev",
  "database": "error",
  "database_error": "OperationalError",
  "redis": "ok",
  "redis_error": null
}
```

Nếu dependency lỗi, HTTP status là:

```text
503 Service Unavailable
```

Endpoint này dùng cho:

- Docker healthcheck của backend;
- Nginx health proxy;
- kiểm tra nhanh khi trình bày/vận hành;
- Kubernetes readiness/liveness nếu triển khai sau.

---

## 4. Backend Metrics

Endpoint:

```text
GET /metrics
```

Không cần token.

Format:

```text
Prometheus text format
```

Metric hiện có:

| Metric | Kiểu | Ý nghĩa |
|---|---|---|
| `deepface_backend_up` | gauge | Backend process còn chạy. |
| `deepface_database_up` | gauge | Backend kết nối PostgreSQL được hay không. |
| `deepface_redis_up` | gauge | Backend kết nối Redis được hay không. |
| `deepface_queue_length{queue="embedding_jobs"}` | gauge | Số embedding jobs đang chờ. |
| `deepface_queue_length{queue="access_jobs"}` | gauge | Số access jobs đang chờ. |
| `deepface_access_logs_total{status="..."}` | gauge | Số access logs theo status. |
| `deepface_access_logs_metric_error` | gauge | Lỗi khi query access_logs để sinh metric. |

Ví dụ output:

```text
# HELP deepface_backend_up Backend process health.
# TYPE deepface_backend_up gauge
deepface_backend_up 1
# HELP deepface_database_up PostgreSQL connectivity from backend.
# TYPE deepface_database_up gauge
deepface_database_up 1
# HELP deepface_redis_up Redis connectivity from backend.
# TYPE deepface_redis_up gauge
deepface_redis_up 1
# HELP deepface_queue_length Redis queue length.
# TYPE deepface_queue_length gauge
deepface_queue_length{queue="embedding_jobs"} 0
deepface_queue_length{queue="access_jobs"} 0
```

Ý nghĩa giá trị:

| Giá trị | Ý nghĩa |
|---|---|
| `1` | Up/OK. |
| `0` | Down/Error. |

---

## 5. Prometheus

Config:

```text
monitoring/prometheus/prometheus.yml
```

Rule file:

```text
monitoring/prometheus/rules/deepface-alerts.yml
```

Prometheus scrape:

```yaml
scrape_configs:
  - job_name: deepface-backend
    metrics_path: /metrics
    static_configs:
      - targets:
          - backend:8000
```

Default interval:

```text
scrape_interval: 15s
evaluation_interval: 15s
```

Chạy:

```powershell
docker compose up -d prometheus
```

Mở UI:

```text
http://localhost:9090
```

Kiểm tra target:

```text
Status -> Targets
```

Target tốt khi:

```text
deepface-backend = UP
```

---

## 6. Alert Rules

Rule group:

```text
deepface-access
```

Các alert hiện có:

| Alert | Điều kiện | Mức | Ý nghĩa |
|---|---|---|---|
| `BackendMetricsDown` | `up{job="deepface-backend"} == 0` trong 1 phút | critical | Prometheus không scrape được backend. |
| `DatabaseUnavailable` | `deepface_database_up == 0` trong 1 phút | critical | Backend không kết nối được PostgreSQL. |
| `RedisUnavailable` | `deepface_redis_up == 0` trong 1 phút | critical | Backend không kết nối được Redis. |
| `QueueBacklogHigh` | `sum(deepface_queue_length) > 20` trong 5 phút | warning | Tổng queue Redis đang quá cao. |
| `AccessProcessingBacklog` | `deepface_access_logs_total{status="processing"} > 10` trong 5 phút | warning | Nhiều access log bị kẹt processing. |
| `AccessErrorsPresent` | `deepface_access_logs_total{status="error"} > 0` trong 2 phút | warning | Có access log lỗi. |

Lưu ý quan trọng:

- `AccessErrorsPresent` firing không đồng nghĩa với lỗi hệ thống nghiêm trọng.
- Nó cho biết trong database đang có ít nhất một log `error`.
- Nếu bạn vừa test ảnh không có mặt/nhiều mặt, alert này có thể firing là bình thường.

Muốn kiểm tra alert:

```text
http://localhost:9090/alerts
```

Trạng thái:

| Trạng thái | Ý nghĩa |
|---|---|
| `inactive` | Điều kiện alert không đúng. |
| `pending` | Điều kiện đúng nhưng chưa đủ thời gian `for`. |
| `firing` | Alert đang kích hoạt. |

---

## 7. Alertmanager

Config:

```text
monitoring/alertmanager/alertmanager.yml
```

Chạy:

```powershell
docker compose up -d alertmanager prometheus
```

Mở UI:

```text
http://localhost:9093
```

Cấu hình hiện tại:

```yaml
receivers:
  - name: local-dashboard
```

Ý nghĩa:

- Alertmanager nhận alert từ Prometheus;
- hiển thị trong UI local;
- dùng local receiver trong phạm vi hiện tại.

Phạm vi hiện tại:

```text
Alertmanager hiện là local receiver.
```

Nếu triển khai môi trường vận hành thật, nên thêm:

- email receiver;
- Slack receiver;
- webhook receiver;
- routing theo severity/service.

---

## 8. Grafana

Service:

```text
grafana
```

Chạy:

```powershell
docker compose up -d grafana
```

Mở UI:

```text
http://localhost:3000
```

Tài khoản mặc định:

```text
admin / admin
```

Có thể đổi bằng env:

```text
GRAFANA_ADMIN_USER
GRAFANA_ADMIN_PASSWORD
GRAFANA_PORT
```

Datasource được provision tự động:

```text
monitoring/grafana/provisioning/datasources/prometheus.yml
```

Datasource:

```text
Prometheus -> http://prometheus:9090
```

Dashboard provider:

```text
monitoring/grafana/provisioning/dashboards/dashboards.yml
```

Dashboard file:

```text
monitoring/grafana/dashboards/deepface-access-overview.json
```

Dashboard mặc định:

```text
DeepFace Access Overview
```

Các panel hiện có:

| Panel | Ý nghĩa |
|---|---|
| `Backend` | Trạng thái backend. |
| `Database` | Trạng thái PostgreSQL. |
| `Redis` | Trạng thái Redis. |
| `Redis Queue Length` | Queue length theo thời gian. |
| `Access Logs By Status` | Số access logs theo status. |
| `Total Queued Jobs` | Tổng số job đang chờ. |
| `Total Access Logs` | Tổng số access logs. |
| `Critical Dependencies` | Tình trạng dependency quan trọng. |

---

## 9. Docker Healthcheck

Docker Compose có healthcheck cho nhiều service.

| Service | Healthcheck |
|---|---|
| `database` | `pg_isready` |
| `redis` | `redis-cli ping` |
| `backend` | gọi `http://127.0.0.1:8000/health` |
| `frontend-user` | `wget http://127.0.0.1/` |
| `frontend-admin` | `wget http://127.0.0.1/admin/` |
| `frontend-home` | `wget http://127.0.0.1/` |
| `worker` | ping Redis |
| `nginx` | gọi `http://127.0.0.1/health` |
| `minio` | `mc ready local` |

Kiểm tra:

```powershell
docker compose ps
```

Xem service nào unhealthy:

```powershell
docker compose ps --format json
```

---

## 10. Logging

Backend và worker log ra stdout/stderr.

Xem log backend:

```powershell
docker compose logs -f backend
```

Xem log worker:

```powershell
docker compose logs -f worker
```

Xem log Nginx:

```powershell
docker compose logs -f nginx
```

Xem log cron backup:

```powershell
docker compose logs -f cron-backup
```

Worker logs thường hữu ích khi debug:

- trạng thái nhận job;
- `job_id`;
- `employee_id`;
- `log_id`;
- access status;
- score;
- lỗi DeepFace/MinIO/Qdrant.

Không nên log:

- password;
- token;
- secret;
- ảnh raw/base64;
- Docker Hub token.

---

## 11. Cách Test Monitoring Nhanh

### 11.1. Chạy stack

```powershell
docker compose up --build -d
```

### 11.2. Kiểm tra health

```powershell
curl http://localhost:8080/health
```

Hoặc:

```powershell
Invoke-WebRequest http://localhost:8080/health
```

### 11.3. Kiểm tra metrics

```powershell
curl http://localhost:8080/metrics
```

Tìm các metric:

```text
deepface_backend_up
deepface_database_up
deepface_redis_up
deepface_queue_length
deepface_access_logs_total
```

### 11.4. Kiểm tra Prometheus target

Mở:

```text
http://localhost:9090/targets
```

Pass khi:

```text
deepface-backend = UP
```

### 11.5. Kiểm tra alert

Mở:

```text
http://localhost:9090/alerts
```

Nếu thấy `AccessErrorsPresent` firing sau khi test ảnh lỗi, đó là đúng logic alert.

### 11.6. Kiểm tra Grafana

Mở:

```text
http://localhost:3000
```

Đăng nhập:

```text
admin / admin
```

Vào dashboard:

```text
DeepFace Access Overview
```

---

## 12. Khi Nào Cần Lo?

| Hiện tượng | Có nghiêm trọng không | Cách hiểu |
|---|---|---|
| `BackendMetricsDown` firing | Có | Backend hoặc network scrape có vấn đề. |
| `DatabaseUnavailable` firing | Có | Backend không làm việc được với PostgreSQL. |
| `RedisUnavailable` firing | Có | Không queue/access job được. |
| `QueueBacklogHigh` firing | Có thể | Worker chậm hoặc quá nhiều job. |
| `AccessProcessingBacklog` firing | Có thể | Access jobs đang kẹt xử lý. |
| `AccessErrorsPresent` firing | Chưa chắc nghiêm trọng | Có log error, có thể do test ảnh no-face/multi-face. |

---

## 13. Phạm Vi Hiện Tại Và Hướng Mở Rộng

Monitoring hiện tại đáp ứng nhu cầu quan sát vận hành cơ bản của hệ thống.

Các hướng mở rộng:

- Bổ sung worker `/metrics` riêng.
- Bổ sung latency histogram cho access/embedding.
- Bổ sung metric riêng cho MinIO/Qdrant từ backend.
- Bổ sung Slack/email/webhook receiver cho Alertmanager.
- Mở rộng Grafana dashboard theo từng pipeline.
- Bổ sung log aggregation như Loki/ELK.
- Bổ sung trace như OpenTelemetry.

Hướng nâng cấp:

- thêm worker metrics;
- thêm latency metric cho access pipeline;
- thêm Qdrant/MinIO health metric;
- thêm Slack/email receiver;
- thêm Loki để xem logs tập trung;
- thêm dashboard riêng cho AI pipeline latency/accuracy.

---

## 14. Tóm Tắt Ngắn

Monitoring hiện tại gồm:

```text
Backend /health
Backend /metrics
Prometheus
Alertmanager
Grafana
Docker healthcheck
Docker logs
```

Điểm quan trọng:

- `/health` cho biết backend, PostgreSQL, Redis có ổn không.
- `/metrics` cung cấp số liệu cho Prometheus.
- Grafana hiển thị dashboard.
- Alertmanager nhận alert local.
- Nếu `AccessErrorsPresent` firing, hãy xem access logs trước, vì có thể chỉ là ảnh test lỗi.
