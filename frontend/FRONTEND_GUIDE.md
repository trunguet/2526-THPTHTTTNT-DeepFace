# Frontend DeepFace - Hướng Dẫn Cấu Trúc & Triển Khai

## 📋 Tổng Quan Dự Án

Dự án Frontend được tổ chức theo kiến trúc **modular** với các thành phần độc lập, dễ bảo trì và mở rộng.

### ✨ Tính Năng Chính

1. **Giao Diện Admin**:
   - ➕ Thêm nhân viên mới (upload ảnh → MinIO → trích vector → Qdrant)
   - 👥 Quản lý danh sách nhân viên (CRUD)
   - 📋 Xem nhật ký ra vào và cảnh báo người lạ
   - 📊 Dashboard thống kê

2. **Giao Diện User**:
   - 👤 Xác thực khuôn mặt real-time (webcam → backend → kết quả)
   - 📋 Tra cứu lịch sử check-in/check-out
   - 📊 Thống kê cá nhân

3. **Hiệu Ứng Nhân Tố** (Mesh Gradient):
   - 7 vòng tròn với blur 50px
   - Chuyển động mượt mà
   - Thay đổi kích thước liên tục

---

## 📁 Cấu Trúc Thư Mục

```
frontend/
├── shared/                    # Các file dùng chung
│   ├── background.css         # CSS Mesh Gradient
│   └── background.js          # JS khởi tạo background
│
├── admin/                     # Giao diện quản trị
│   ├── index.html             # Dashboard chính
│   ├── add_employee.html      # Form thêm nhân viên
│   ├── manage_list.html       # Danh sách nhân viên
│   ├── view_logs.html         # Xem nhật ký
│   ├── add_employee.js        # Module: Thêm nhân viên
│   ├── manage_list.js         # Module: Quản lý danh sách
│   ├── view_logs.js           # Module: Xem nhật ký
│   └── styles.css             # CSS Admin
│
└── user/                      # Giao diện nhân viên
    ├── index.html             # Dashboard chính
    ├── face_scan.html         # Xác thực khuôn mặt
    ├── check_history.html     # Lịch sử check-in
    ├── face_scan.js           # Module: Xác thực
    ├── check_history.js       # Module: Lịch sử
    └── style.css              # CSS User
```

---

## 🎨 Backend Mesh Gradient

### Tệp: `frontend/shared/background.css` & `frontend/shared/background.js`

**Đặc điểm**:
- 7 vòng tròn SVG với màu sắc gradient
- Blur 50px
- Chuyển động tuyến tính (linear movement)
- Thay đổi kích thước (linear scaling)

**Màu sắc**:
```
#007069  (Teal)
#10637D  (Blue-Slate)
#2097BC  (Sky Blue)
#24937F  (Green-Blue)
#2C88A6  (Ocean Blue)
#5CB0B0  (Cyan)
#7CC4ED  (Light Blue)
```

**Sử dụng**:
```html
<link rel="stylesheet" href="../shared/background.css">
<script src="../shared/background.js"></script>
```

---

## 📱 Module Admin

### 1️⃣ add_employee.js

**Chức Năng**:
- Form thêm nhân viên
- Upload ảnh lên MinIO
- Gọi API tạo nhân viên
- Kích hoạt trích vector embedding

**API Cần Thiết**:
```
POST /api/employees/upload-image
  Tham số: file (image), employee_id
  Phản hồi: { image_url, url }

POST /api/employees
  Body: { full_name, employee_id, email, department, image_url }
  Headers: Authorization: Bearer {token}
  Phản hồi: { id, full_name, ... }

POST /api/employees/{id}/extract-embedding
  Body: { image_url }
  Headers: Authorization: Bearer {token}
  Phản hồi: { embedding_id, status }
```

**Lớp**: `AddEmployeeModule`
**HTML**: `frontend/admin/add_employee.html`

---

### 2️⃣ manage_list.js

**Chức Năng**:
- Hiển thị danh sách nhân viên
- Tìm kiếm/lọc
- Sửa nhân viên
- Xóa nhân viên

**API Cần Thiết**:
```
GET /api/employees
  Headers: Authorization: Bearer {token}
  Phản hồi: [{ id, full_name, employee_id, email, department }, ...]

DELETE /api/employees/{id}
  Headers: Authorization: Bearer {token}
  Phản hồi: { status: "deleted" }
```

**Lớp**: `ManageEmployeeListModule`
**HTML**: `frontend/admin/manage_list.html`

---

### 3️⃣ view_logs.js

**Chức Năng**:
- Xem nhật ký ra vào
- Hiển thị cảnh báo người lạ
- Lọc theo ngày/trạng thái
- Tự động cập nhật

**API Cần Thiết**:
```
GET /api/access-logs
  Headers: Authorization: Bearer {token}
  Phản hồi: [{ id, employee_name, employee_id, camera_location, timestamp, status }, ...]

GET /api/access-logs/alerts
  Headers: Authorization: Bearer {token}
  Phản hồi: [{ id, camera_location, confidence, image_url, timestamp }, ...]

POST /api/access-logs/alerts/{id}/dismiss
  Headers: Authorization: Bearer {token}
  Phản hồi: { status: "dismissed" }
```

**Lớp**: `ViewLogsModule`
**HTML**: `frontend/admin/view_logs.html`

---

## 📱 Module User

### 1️⃣ face_scan.js

**Chức Năng**:
- Khởi động webcam
- Capture frame
- Gửi frame tới backend xác thực
- Hiển thị kết quả (Welcome/Denied/Stranger Alert)

**API Cần Thiết**:
```
POST /api/access/verify-face
  Body: { image: "base64-encoded-image" }
  Headers: Authorization: Bearer {token}
  Phản hồi: {
    status: "allowed" | "denied" | "stranger",
    employee_name: string,
    confidence: number (0-1),
    message: string
  }
```

**Lớp**: `FaceScanModule`
**HTML**: `frontend/user/face_scan.html`

**Tính Năng**:
- Real-time webcam stream
- Frame capture & encode to Base64
- Status messages
- Result display dengan animation

---

### 2️⃣ check_history.js

**Chức Năng**:
- Fetch lịch sử check-in/check-out
- Lọc theo ngày/tháng
- Tính toán thống kê
- Xuất CSV

**API Cần Thiết**:
```
GET /api/employees/{employee_id}/access-history
  Headers: Authorization: Bearer {token}
  Phản hồi: [{
    id,
    timestamp,
    access_type: "check_in" | "check_out",
    camera_location,
    status: "allowed" | "denied"
  }, ...]
```

**Lớp**: `CheckHistoryModule`
**HTML**: `frontend/user/check_history.html`

---

## 🎯 Biến Môi Trường & Cấu Hình

### localStorage Keys
```javascript
localStorage.getItem('auth_token')           // JWT token
localStorage.getItem('employee_id')          // ID nhân viên
localStorage.getItem('employee_name')        // Tên nhân viên
```

### API Base URL
```javascript
process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000'
```

---

## 🚀 Triển Khai Docker

### Build Admin Docker Image
```dockerfile
# frontend/admin/Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY . .
EXPOSE 80
CMD ["python", "-m", "http.server", "80"]
```

### Build User Docker Image
```dockerfile
# frontend/user/Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY . .
EXPOSE 80
CMD ["python", "-m", "http.server", "80"]
```

### Docker Compose Integration
```yaml
services:
  admin:
    build: ./frontend/admin
    ports:
      - "3001:80"
    environment:
      - REACT_APP_API_BASE_URL=http://backend:8000

  user:
    build: ./frontend/user
    ports:
      - "3002:80"
    environment:
      - REACT_APP_API_BASE_URL=http://backend:8000
```

---

## 📋 Checklist Backend API Cần Triển Khai

### Admin Endpoints
- [ ] `POST /api/employees/upload-image` - Upload ảnh
- [ ] `POST /api/employees` - Tạo nhân viên
- [ ] `POST /api/employees/{id}/extract-embedding` - Trích vector
- [ ] `GET /api/employees` - Danh sách nhân viên
- [ ] `DELETE /api/employees/{id}` - Xóa nhân viên
- [ ] `GET /api/access-logs` - Danh sách nhật ký
- [ ] `GET /api/access-logs/alerts` - Cảnh báo người lạ
- [ ] `POST /api/access-logs/alerts/{id}/dismiss` - Bỏ qua cảnh báo

### User Endpoints
- [ ] `POST /api/access/verify-face` - Xác thực khuôn mặt
- [ ] `GET /api/employees/{id}/access-history` - Lịch sử check-in

---

## 💡 Hướng Dẫn Sử Dụng

### Admin
1. Truy cập: `http://localhost:3001`
2. Đăng nhập
3. Dashboard hiển thị thống kê
4. Thêm nhân viên → Upload ảnh → Hệ thống tự động xử lý
5. Quản lý danh sách, xem nhật ký

### User
1. Truy cập: `http://localhost:3002`
2. Đăng nhập
3. Nhấn "Xác Thực" → Chụp ảnh khuôn mặt
4. Xem lịch sử check-in → Xuất CSV

---

## 🔧 Công Nghệ Sử Dụng

- **HTML5**: Cấu trúc
- **CSS3**: Styling & Animation (Mesh Gradient)
- **Vanilla JavaScript**: Logic & Interactivity
- **Fetch API**: HTTP requests
- **LocalStorage**: Session management
- **Canvas API**: Image capture
- **MediaDevices API**: Webcam access

---

## 📝 Lưu Ý Triển Khai

1. **CORS**: Backend phải enable CORS cho frontend URLs
2. **Authentication**: Tất cả request cần header `Authorization: Bearer {token}`
3. **Image Size**: Giới hạn upload ảnh 5MB
4. **Webcam Permission**: Yêu cầu quyền truy cập camera
5. **HTTPS**: Production phải sử dụng HTTPS

---

## 📚 Tham Khảo Thêm

- Backend API: Xem `docs/api.md`
- Database Schema: Xem `docs/db-schema.md`
- Setup Guide: Xem `docs/setup.md`

---

**Phiên bản**: 1.0  
**Cập nhật**: May 4, 2026  
**Team**: UET - DeepFace Project
