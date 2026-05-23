# Team Roles

Tài liệu này gợi ý cách chia việc trong nhóm khi phát triển và bảo vệ DeepFace Access Control.

---

## 1. Backend/API

Phụ trách:

- FastAPI routes;
- auth và role;
- employee/camera/log/access API;
- upload ảnh;
- health/metrics;
- test backend.

---

## 2. AI/Worker

Phụ trách:

- Redis queue;
- DeepFace detector/embedding;
- Qdrant vector search;
- threshold tuning;
- smoke test với bộ ảnh kiểm thử;
- xử lý lỗi `granted`, `denied`, `error`.

---

## 3. Frontend

Phụ trách:

- User UI;
- Admin UI;
- webcam capture;
- history/session;
- employee/users/settings UI;
- trạng thái loading/error/result.

---

## 4. DevOps/Deployment

Phụ trách:

- Docker Compose;
- Nginx gateway;
- Docker Hub CI;
- monitoring Prometheus/Grafana;
- backup;
- Helm chart.

---

## 5. QA/Documentation

Phụ trách:

- chuẩn bị bộ ảnh kiểm thử;
- kiểm tra flow end-to-end;
- ghi demo checklist;
- cập nhật docs;
- chuẩn bị câu trả lời khi bảo vệ.

Bộ ảnh nên có:

- cùng người;
- khác người;
- no-face;
- nhiều mặt;
- thiếu sáng;
- nghiêng mặt;
- đeo kính.
