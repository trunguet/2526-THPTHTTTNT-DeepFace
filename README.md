# DeepFace Docker Run Guide

## Requirements

- Docker Desktop is installed and running.
- Docker Desktop is using the Linux engine.

## Run

From the repository root:

```bash
docker compose up --build -d
```

Open:

- Admin UI: http://localhost:3001
- User UI: http://localhost:3002
- Backend health: http://localhost:18000/health
- MinIO console: http://localhost:19001
- Qdrant dashboard: http://localhost:16333/dashboard
- PostgreSQL: localhost:15432
- Redis: localhost:16379

MinIO login:

- Username: `admin`
- Password: `password123`

## Stop

```bash
docker compose down
```

To remove runtime data stored in Docker volumes:

```bash
docker compose down -v
```

## Frontend Scope

This repository currently includes improved static frontends for:

- Admin: dashboard, employee list, add employee form, access logs, settings, demo login.
- User: camera scan, access history, CSV export, demo login.

Detailed frontend review and next-step checklist: [docs/frontend-review.md](docs/frontend-review.md).

## Backend Scope

The backend now includes an end-to-end MVP for the face access-control use case:

- FastAPI REST API.
- PostgreSQL for employees and access logs.
- MinIO for employee images and verification snapshots.
- Qdrant for face/image vectors.
- Redis queue plus `worker` service for background embedding jobs.
- Lightweight image embedding based on Pillow/Numpy so the project can run quickly in Docker.

Core flow:

1. Admin uploads an employee face image.
2. Backend stores the image in MinIO.
3. Admin creates the employee record.
4. Backend queues an embedding job.
5. Worker reads the image, builds the vector, and indexes it into Qdrant.
6. User captures a camera frame.
7. Backend saves the snapshot in MinIO, searches Qdrant, writes an access log, and returns `allowed` or `stranger`.

Important API endpoints:

- `POST /api/employees/upload-image`
- `POST /api/employees`
- `POST /api/employees/{id}/extract-embedding`
- `GET /api/employees`
- `DELETE /api/employees/{id}`
- `POST /api/access/verify-face`
- `GET /api/access-logs`
- `GET /api/access-logs/alerts`
- `POST /api/access-logs/alerts/{id}/dismiss`
- `GET /api/employees/{employee_id}/access-history`

## Notes

This is a functional Docker MVP for the course project. The recognition pipeline uses a lightweight embedding method, not a production-grade DeepFace model. For a higher accuracy submission, replace `backend/app/ai.py` with a real face detector/embedding model while keeping the same API contract.
