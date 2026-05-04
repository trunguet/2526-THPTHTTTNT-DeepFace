# API Endpoints Required for Frontend

## 📌 Overview

Frontend DeepFace yêu cầu các API endpoints sau từ Backend. Các endpoint này phải được triển khai để hệ thống hoạt động đầy đủ.

---

## 🔐 Authentication

### Login (Admin & User)
```
POST /api/auth/login
Content-Type: application/json

Request:
{
  "username": "string",
  "password": "string"
}

Response (200):
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_id": "integer",
  "role": "admin|user"
}

Response (401):
{
  "detail": "Invalid credentials"
}
```

---

## 👥 Employee Management (Admin Panel)

### 1. Add Employee - Upload Image
```
POST /api/employees/upload-image
Authorization: Bearer {token}
Content-Type: multipart/form-data

Request:
- file: <binary image file>
- employee_id: "string"

Response (200):
{
  "image_url": "https://minio.../employees/emp001.jpg",
  "url": "https://minio.../employees/emp001.jpg",
  "status": "uploaded"
}

Response (400):
{
  "detail": "File size exceeds 5MB"
}
```

### 2. Create Employee
```
POST /api/employees
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "full_name": "Nguyễn Văn A",
  "employee_id": "EMP001",
  "email": "employee@company.com",
  "department": "IT",
  "image_url": "https://minio.../employees/emp001.jpg"
}

Response (201):
{
  "id": 1,
  "full_name": "Nguyễn Văn A",
  "employee_id": "EMP001",
  "email": "employee@company.com",
  "department": "IT",
  "image_url": "https://minio.../employees/emp001.jpg",
  "created_at": "2026-05-04T10:30:00Z",
  "updated_at": "2026-05-04T10:30:00Z"
}

Response (400):
{
  "detail": "Employee with this ID already exists"
}
```

### 3. Extract Embedding & Index to Qdrant
```
POST /api/employees/{employee_id}/extract-embedding
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "image_url": "https://minio.../employees/emp001.jpg"
}

Response (200):
{
  "status": "success",
  "embedding_id": "uuid",
  "employee_id": "EMP001",
  "vector_dimension": 512,
  "indexed_to_qdrant": true,
  "confidence": 0.98
}

Response (400):
{
  "detail": "Failed to extract embedding from image"
}

Response (500):
{
  "detail": "Failed to index to Qdrant"
}
```

### 4. Get All Employees
```
GET /api/employees
Authorization: Bearer {token}
Query Params (optional):
- skip: integer (default: 0)
- limit: integer (default: 100)
- department: string

Response (200):
[
  {
    "id": 1,
    "full_name": "Nguyễn Văn A",
    "employee_id": "EMP001",
    "email": "employee@company.com",
    "department": "IT",
    "image_url": "https://minio.../employees/emp001.jpg",
    "created_at": "2026-05-04T10:30:00Z",
    "updated_at": "2026-05-04T10:30:00Z"
  },
  ...
]
```

### 5. Get Employee Details
```
GET /api/employees/{employee_id}
Authorization: Bearer {token}

Response (200):
{
  "id": 1,
  "full_name": "Nguyễn Văn A",
  "employee_id": "EMP001",
  "email": "employee@company.com",
  "department": "IT",
  "image_url": "https://minio.../employees/emp001.jpg",
  "created_at": "2026-05-04T10:30:00Z",
  "updated_at": "2026-05-04T10:30:00Z"
}

Response (404):
{
  "detail": "Employee not found"
}
```

### 6. Update Employee
```
PUT /api/employees/{employee_id}
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "full_name": "Nguyễn Văn A",
  "email": "newemail@company.com",
  "department": "IT"
}

Response (200):
{
  "id": 1,
  "full_name": "Nguyễn Văn A",
  "employee_id": "EMP001",
  "email": "newemail@company.com",
  "department": "IT",
  "updated_at": "2026-05-04T11:00:00Z"
}
```

### 7. Delete Employee
```
DELETE /api/employees/{employee_id}
Authorization: Bearer {token}

Response (200):
{
  "status": "deleted",
  "message": "Employee EMP001 deleted successfully"
}

Response (404):
{
  "detail": "Employee not found"
}
```

---

## 📋 Access Logs & Alerts (Admin Panel)

### 1. Get Access Logs
```
GET /api/access-logs
Authorization: Bearer {token}
Query Params (optional):
- skip: integer (default: 0)
- limit: integer (default: 100)
- date_from: datetime
- date_to: datetime
- status: "allowed" | "denied"
- camera_id: integer

Response (200):
[
  {
    "id": 1,
    "employee_id": 1,
    "employee_name": "Nguyễn Văn A",
    "camera_location": "Cửa chính lầu 1",
    "timestamp": "2026-05-04T09:15:30Z",
    "status": "allowed",
    "confidence": 0.95,
    "image_url": "https://minio.../logs/log_1.jpg"
  },
  {
    "id": 2,
    "employee_id": null,
    "employee_name": "Unknown",
    "camera_location": "Cửa chính lầu 1",
    "timestamp": "2026-05-04T09:30:00Z",
    "status": "denied",
    "confidence": 0.45
  }
]
```

### 2. Get Stranger Alerts
```
GET /api/access-logs/alerts
Authorization: Bearer {token}
Query Params (optional):
- skip: integer (default: 0)
- limit: integer (default: 50)
- dismissed: boolean

Response (200):
[
  {
    "id": 1,
    "camera_id": 1,
    "camera_location": "Cửa chính lầu 1",
    "timestamp": "2026-05-04T09:30:00Z",
    "confidence": 0.72,
    "image_url": "https://minio.../alerts/alert_1.jpg",
    "status": "active",
    "dismissed_at": null
  }
]
```

### 3. Dismiss Alert
```
POST /api/access-logs/alerts/{alert_id}/dismiss
Authorization: Bearer {token}

Response (200):
{
  "status": "dismissed",
  "alert_id": 1,
  "dismissed_at": "2026-05-04T10:00:00Z"
}

Response (404):
{
  "detail": "Alert not found"
}
```

---

## 👤 Face Verification (User Panel)

### 1. Verify Face - Check-in/Check-out
```
POST /api/access/verify-face
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "image": "data:image/jpeg;base64,...",
  "camera_id": 1 (optional)
}

Response (200) - Employee Found:
{
  "status": "allowed",
  "employee_id": 1,
  "employee_name": "Nguyễn Văn A",
  "access_type": "check_in",
  "confidence": 0.95,
  "message": "Xác thực thành công"
}

Response (200) - No Match:
{
  "status": "denied",
  "confidence": 0.45,
  "message": "Khuôn mặt không khớp"
}

Response (200) - Stranger:
{
  "status": "stranger",
  "confidence": 0.72,
  "message": "Phát hiện người lạ"
}

Response (400):
{
  "detail": "No face detected in image"
}

Response (401):
{
  "detail": "Unauthorized"
}
```

---

## 📊 Access History (User Panel)

### 1. Get Employee Access History
```
GET /api/employees/{employee_id}/access-history
Authorization: Bearer {token}
Query Params (optional):
- skip: integer (default: 0)
- limit: integer (default: 100)
- date_from: datetime
- date_to: datetime

Response (200):
[
  {
    "id": 1,
    "employee_id": 1,
    "timestamp": "2026-05-04T08:00:00Z",
    "access_type": "check_in",
    "camera_id": 1,
    "camera_location": "Cửa chính lầu 1",
    "status": "allowed",
    "confidence": 0.95
  },
  {
    "id": 2,
    "employee_id": 1,
    "timestamp": "2026-05-04T17:30:00Z",
    "access_type": "check_out",
    "camera_id": 1,
    "camera_location": "Cửa chính lầu 1",
    "status": "allowed",
    "confidence": 0.92
  }
]
```

### 2. Get Current Employee's History (Self)
```
GET /api/me/access-history
Authorization: Bearer {token}

Response (200):
[
  {
    "id": 1,
    "timestamp": "2026-05-04T08:00:00Z",
    "access_type": "check_in",
    "camera_location": "Cửa chính lầu 1",
    "status": "allowed",
    "confidence": 0.95
  }
]
```

---

## 🔄 Dashboard Stats (Admin)

### 1. Get Today's Statistics
```
GET /api/stats/today
Authorization: Bearer {token}

Response (200):
{
  "total_checkins": 24,
  "total_checkouts": 23,
  "present_employees": 23,
  "absent_employees": 2,
  "stranger_alerts": 1,
  "access_denied": 2,
  "timestamp": "2026-05-04T10:00:00Z"
}
```

---

## 🎬 Camera Management

### 1. Get All Cameras
```
GET /api/cameras
Authorization: Bearer {token}

Response (200):
[
  {
    "id": 1,
    "name": "Camera 01",
    "location": "Cửa chính lầu 1",
    "ip_address": "192.168.1.100",
    "status": "active",
    "last_heartbeat": "2026-05-04T10:00:00Z"
  }
]
```

---

## ⚠️ Error Responses

### Standard Error Response
```json
{
  "detail": "Error message",
  "status_code": 400,
  "timestamp": "2026-05-04T10:00:00Z"
}
```

### Common HTTP Status Codes
| Code | Meaning | Common Cause |
|------|---------|--------------|
| 200  | OK | Request successful |
| 201  | Created | Resource created |
| 400  | Bad Request | Invalid input |
| 401  | Unauthorized | Missing/invalid token |
| 403  | Forbidden | Insufficient permissions |
| 404  | Not Found | Resource not found |
| 409  | Conflict | Resource already exists |
| 500  | Internal Error | Server error |

---

## 🔒 Authentication Header

Tất cả protected endpoints yêu cầu:

```
Authorization: Bearer <JWT_TOKEN>
```

Token được cấp từ endpoint `/api/auth/login`.

---

## 📝 Notes for Backend Team

1. **CORS Configuration**: Enable CORS cho frontend URLs (3001, 3002)
2. **Image Upload**: Handle file uploads tới MinIO
3. **Vector Extraction**: Integrate với ML pipeline để trích embedding
4. **Qdrant Integration**: Index vectors vào Qdrant vector database
5. **Real-time Updates**: Để frontend auto-refresh được, cân nhắc WebSocket
6. **Error Handling**: Return consistent error format
7. **Validation**: Validate image format, size trước khi upload
8. **Rate Limiting**: Protect endpoints khỏi spam

---

## 🧪 Testing Endpoints

### Using cURL

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Get Employees
curl -X GET http://localhost:8000/api/employees \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create Employee
curl -X POST http://localhost:8000/api/employees \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Test User", "employee_id": "EMP999", "email": "test@test.com"}'
```

### Using Postman
1. Import collection từ backend docs
2. Set environment variable: `{{base_url}}` = `http://localhost:8000`
3. Get token từ login endpoint
4. Set `Authorization` header với token
5. Test endpoints

---

## 📞 Integration Checklist

- [ ] ✅ Implement all required endpoints
- [ ] ✅ Setup CORS for frontend URLs
- [ ] ✅ Implement JWT authentication
- [ ] ✅ Setup MinIO for image upload
- [ ] ✅ Setup Qdrant for vector indexing
- [ ] ✅ Implement face verification logic
- [ ] ✅ Setup database models
- [ ] ✅ Test all endpoints with frontend
- [ ] ✅ Error handling & validation
- [ ] ✅ Logging & monitoring

---

**Phiên bản**: 1.0  
**Cập nhật**: May 4, 2026  
**Team**: UET - DeepFace Project

Để kết nối frontend với backend, hãy đảm bảo tất cả endpoints này được triển khai và kiểm tra.
