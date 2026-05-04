# Frontend Setup & Run Guide

## 🚀 Bắt Đầu Nhanh (Quick Start)

### Yêu Cầu
- Python 3.8+ (để chạy HTTP server)
- Trình duyệt web hiện đại (Chrome, Firefox, Edge)
- Backend DeepFace đang chạy trên `http://localhost:8000`

### 1. Chạy Admin Interface

```bash
# Bước 1: Mở terminal tại thư mục project
cd d:\DEEPFACE\2526-THPTHTTTNT-DeepFace

# Bước 2: Chạy Python HTTP server cho Admin
cd frontend/admin
python -m http.server 3001

# Bước 3: Truy cập trên trình duyệt
# http://localhost:3001
```

### 2. Chạy User Interface (Terminal riêng)

```bash
# Bước 1: Mở terminal mới
cd d:\DEEPFACE\2526-THPTHTTTNT-DeepFace

# Bước 2: Chạy Python HTTP server cho User
cd frontend/user
python -m http.server 3002

# Bước 3: Truy cập trên trình duyệt
# http://localhost:3002
```

---

## 🐳 Chạy với Docker

### Build Docker Images

```bash
# Admin Image
cd frontend/admin
docker build -t deepface-admin:1.0 .

# User Image
cd frontend/user
docker build -t deepface-user:1.0 .
```

### Chạy Containers

```bash
# Admin Container
docker run -d -p 3001:80 --name deepface-admin deepface-admin:1.0

# User Container (terminal riêng)
docker run -d -p 3002:80 --name deepface-user deepface-user:1.0
```

### Docker Compose (Recommended)

```bash
# Từ thư mục project root
docker-compose up frontend-admin frontend-user

# Hoặc chạy cùng backend
docker-compose up
```

---

## 🔐 Authentication Setup

### LocalStorage Configuration

Hệ thống sử dụng `localStorage` để lưu token xác thực. Bạn cần:

1. **Đăng nhập qua API** để lấy token:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

2. **Lưu token vào localStorage**:
```javascript
localStorage.setItem('auth_token', 'your-jwt-token-here');
localStorage.setItem('employee_id', 'emp001');
localStorage.setItem('employee_name', 'Admin User');
```

3. **Hoặc bạn có thể chỉnh sửa modules để bỏ qua auth** (Development only):
```javascript
// Trong file .js module, thay:
getAuthToken() {
  return localStorage.getItem('auth_token') || '';
}

// Thành:
getAuthToken() {
  return localStorage.getItem('auth_token') || 'dev-token';
}
```

---

## ⚙️ Cấu Hình API URL

### Method 1: Environment Variable
```bash
# Trước khi chạy server
set REACT_APP_API_BASE_URL=http://localhost:8000

# Hoặc
export REACT_APP_API_BASE_URL=http://localhost:8000

python -m http.server 3001
```

### Method 2: Chỉnh sửa code trực tiếp

Mở file module (ví dụ: `add_employee.js`):

```javascript
// Thay:
getApiBaseURL() {
  return process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
}

// Thành:
getApiBaseURL() {
  return 'http://localhost:8000'; // Hoặc IP của server
}
```

### Method 3: Sửa Backend CORS
```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🔍 Troubleshooting

### ❌ Lỗi: "Cannot connect to Backend"

**Giải pháp**:
1. Kiểm tra backend đang chạy: `http://localhost:8000/docs`
2. Kiểm tra CORS configuration
3. Kiểm tra API URL trong console browser

### ❌ Lỗi: "Camera Permission Denied"

**Giải pháp**:
1. Kiểm tra quyền camera trong trình duyệt
   - Chrome: Settings → Privacy → Site permissions → Camera
2. Sử dụng HTTPS (hoặc localhost)
3. Cấp lại quyền camera

### ❌ Lỗi: "CORS Error"

**Giải pháp**:
```python
# Backend CORS Configuration
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (dev only)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### ❌ Lỗi: "CSV Export Không Hoạt Động"

**Giải pháp**:
- Kiểm tra browser console để xem lỗi cụ thể
- Đảm bảo dữ liệu history tồn tại
- Thử download lại

---

## 🧪 Testing Locally

### 1. Test Admin Add Employee Flow

```bash
# 1. Mở Admin
http://localhost:3001/add_employee.html

# 2. Điền form:
# - Tên: Nguyễn Văn A
# - Mã NV: EMP001
# - Email: employee@company.com
# - Ảnh: Chọn file ảnh

# 3. Click "Thêm Nhân Viên"
# 4. Kiểm tra backend logs
```

### 2. Test User Face Scan

```bash
# 1. Mở User
http://localhost:3002/face_scan.html

# 2. Cấp quyền camera
# 3. Click "Khởi Động Camera"
# 4. Đối mặt camera
# 5. Click "Chụp & Xác Thực"
# 6. Kiểm tra kết quả
```

### 3. Test History Check-in

```bash
# 1. Mở History
http://localhost:3002/check_history.html

# 2. Kiểm tra danh sách check-in
# 3. Thử lọc theo ngày/tháng
# 4. Tải CSV
```

---

## 📊 Development Console

Để debug, mở browser console (F12) và kiểm tra:

```javascript
// Kiểm tra auth token
localStorage.getItem('auth_token')

// Kiểm tra employee info
localStorage.getItem('employee_id')
localStorage.getItem('employee_name')

// Kiểm tra module instances
window.faceScanModule
window.checkHistoryModule
window.manageModule
window.logsModule
```

---

## 🎯 Common API Responses

### Successful Employee Add
```json
{
  "id": 1,
  "full_name": "Nguyễn Văn A",
  "employee_id": "EMP001",
  "email": "employee@company.com",
  "department": "IT",
  "image_url": "https://minio.../employee_1.jpg",
  "created_at": "2026-05-04T10:30:00Z"
}
```

### Face Verification Success
```json
{
  "status": "allowed",
  "employee_name": "Nguyễn Văn A",
  "employee_id": "EMP001",
  "confidence": 0.95,
  "message": "Xác thực thành công"
}
```

### Face Verification Failed
```json
{
  "status": "denied",
  "confidence": 0.45,
  "message": "Khuôn mặt không khớp"
}
```

### Stranger Detection
```json
{
  "status": "stranger",
  "confidence": 0.72,
  "message": "Phát hiện người lạ"
}
```

---

## 📱 Browser Compatibility

| Browser | Support |
|---------|---------|
| Chrome  | ✅ Yes  |
| Firefox | ✅ Yes  |
| Safari  | ✅ Yes  |
| Edge    | ✅ Yes  |
| IE 11   | ❌ No   |

**Đề xuất**: Chrome hoặc Edge cho webcam support tốt nhất.

---

## 🎨 Customization

### Thay đổi Mesh Gradient Colors

Mở `frontend/shared/background.css`:

```css
.blob:nth-child(1) {
  fill: #YOUR_HEX_COLOR;
}
```

### Thay đổi Brand Colors

Mở `frontend/admin/styles.css` hoặc `frontend/user/style.css`:

```css
/* Search for existing colors */
#7cc4ed   /* Light Blue - Primary */
#2097bc   /* Sky Blue - Primary Dark */
#10b981   /* Green - Success */
#f87171   /* Red - Danger */
```

---

## 📚 File Structure Reference

```
frontend/
├── FRONTEND_GUIDE.md              ← Bạn đang xem
├── SETUP_RUN_GUIDE.md             ← Hướng dẫn này
├── shared/
│   ├── background.js
│   └── background.css
├── admin/
│   ├── index.html
│   ├── add_employee.html
│   ├── manage_list.html
│   ├── view_logs.html
│   ├── add_employee.js
│   ├── manage_list.js
│   ├── view_logs.js
│   └── styles.css
└── user/
    ├── index.html
    ├── face_scan.html
    ├── check_history.html
    ├── face_scan.js
    ├── check_history.js
    └── style.css
```

---

## 🚨 Production Checklist

- [ ] ✅ Cấu hình Backend CORS đúng
- [ ] ✅ API URLs trỏ tới production server
- [ ] ✅ HTTPS được enable
- [ ] ✅ Xóa console.log (debug code)
- [ ] ✅ Test tất cả flows
- [ ] ✅ Mobile responsive test
- [ ] ✅ Camera permission test
- [ ] ✅ CSV export test
- [ ] ✅ Auth token handling

---

## 📞 Support & Debugging

### Enable Debug Mode

Thêm vào HTML file trước `</head>`:

```html
<script>
  // Enable verbose logging
  const DEBUG = true;
  const originalFetch = window.fetch;
  window.fetch = function(...args) {
    if (DEBUG) console.log('🔵 Fetch:', args[0], args[1]);
    return originalFetch.apply(this, args).then(res => {
      if (DEBUG) console.log('🟢 Response:', res.status, res.url);
      return res;
    });
  };
</script>
```

### Check Backend Connection

```bash
# Test backend
curl -X GET http://localhost:8000/api/employees \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test CORS
curl -X OPTIONS http://localhost:8000/api/employees \
  -H "Origin: http://localhost:3001"
```

---

**Phiên bản**: 1.0  
**Cập nhật**: May 4, 2026  
**Team**: UET - DeepFace Project

Có bất kỳ vấn đề? Kiểm tra backend logs và browser console.
