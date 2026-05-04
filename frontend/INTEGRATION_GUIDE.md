# Frontend Integration Guide - Mesh Gradient Background

> Hướng dẫn chi tiết để tích hợp Animated Mesh Gradient Background vào các trang HTML

---

## 📋 Tổng Quan

### File Core

| File | Mô Tả | Vị Trí |
|------|-------|--------|
| `background.css` | Định nghĩa kiểu CSS cho Mesh Gradient và Glassmorphism | `frontend/shared/background.css` |
| `background.js` | Logic JavaScript để tạo SVG Mesh Gradient | `frontend/shared/background.js` |

### Features Chính

✅ **Mesh Gradient Background**
- Nền đen tuyệt đối (#000000)
- 7 khối màu với các code: #007069, #10637D, #2097BC, #24937F, #2C88A6, #5CB0B0, #7CC4ED
- Blur 80px cho hiệu ứng cực mạnh
- Linear animations mượt mà

✅ **Glassmorphism UI Components**
- `.glass-panel` - Bảng pan lớn (padding 20px)
- `.glass-panel-lg` - Bảng pan cực lớn (padding 30px)
- `.glass-panel-sm` - Bảng pan nhỏ (padding 15px)
- `backdrop-filter: blur(10px)` cho hiệu ứng kính mờ
- `rgba(255, 255, 255, 0.05)` nền trắng trong suốt

---

## 🔧 Cách Tích Hợp (3 Bước)

### Bước 1️⃣: Nhúng CSS & JS vào HTML

**Trong thẻ `<head>`:**
```html
<!-- Mesh Gradient Background Styles -->
<link rel="stylesheet" href="../shared/background.css">
```

**Trước `</body>`:**
```html
<!-- Mesh Gradient Background Animation -->
<script src="../shared/background.js"></script>
```

### Bước 2️⃣: Tạo Wrapper Container

**Trong thẻ `<body>`:**
```html
<body>
  <!-- Nền sẽ được tạo tự động bởi JS (MeshGradientBackground class) -->
  
  <!-- Nội dung chính của trang -->
  <div id="app">
    <!-- Các thẻ HTML khác ở đây -->
  </div>
</body>
```

### Bước 3️⃣: Sử Dụng Glass Panel Class

**Bọc nội dung bằng `.glass-panel`:**
```html
<div class="glass-panel">
  <!-- Nội dung của form, bảng dữ liệu, v.v. -->
</div>
```

---

## 📝 Ví Dụ Thực Tế

### Ví Dụ 1: Admin - Add Employee Page

**File: `frontend/admin/add_employee.html`**

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Thêm Nhân Viên - DeepFace Admin</title>
  
  <!-- 1️⃣ NHÚNG BACKGROUND CSS -->
  <link rel="stylesheet" href="../shared/background.css">
  
  <!-- Thêm admin styles -->
  <link rel="stylesheet" href="styles.css">
  
  <style>
    /* Thêm CSS riêng cho page này nếu cần */
    .form-container {
      max-width: 600px;
      margin: 50px auto;
    }
    
    .form-section {
      margin-bottom: 30px;
    }
  </style>
</head>
<body>
  <!-- Nền sẽ được tạo tự động bởi background.js -->
  
  <!-- Nội dung chính -->
  <div id="app">
    <!-- Header -->
    <div class="glass-panel-lg" style="margin: 20px auto; max-width: 600px;">
      <h1>➕ Thêm Nhân Viên Mới</h1>
      <p style="color: #aaa; margin-top: 10px;">Điền thông tin nhân viên để đăng ký vào hệ thống</p>
    </div>
    
    <!-- Form Container -->
    <div class="form-container">
      <!-- Form Section với Glass Panel -->
      <div class="glass-panel-lg">
        <form id="addEmployeeForm">
          <div class="form-section">
            <label>Tên Nhân Viên</label>
            <input type="text" id="fullName" placeholder="Nguyễn Văn A" required>
          </div>
          
          <div class="form-section">
            <label>Mã Nhân Viên</label>
            <input type="text" id="employeeId" placeholder="EMP001" required>
          </div>
          
          <div class="form-section">
            <label>Email</label>
            <input type="email" id="email" placeholder="employee@company.com" required>
          </div>
          
          <div class="form-section">
            <label>Ảnh Khuôn Mặt</label>
            <input type="file" id="faceImage" accept="image/*" required>
            <div id="imagePreview" style="margin-top: 10px;">
              <!-- Preview sẽ được hiển thị ở đây -->
            </div>
          </div>
          
          <button type="submit" class="btn-primary">✅ Thêm Nhân Viên</button>
        </form>
        
        <!-- Status Message -->
        <div id="statusMessage" style="margin-top: 20px; padding: 15px; border-radius: 8px; display: none;">
          <!-- Thông báo status sẽ được hiển thị ở đây -->
        </div>
      </div>
    </div>
  </div>
  
  <!-- 2️⃣ NHÚNG BACKGROUND JS -->
  <script src="../shared/background.js"></script>
  
  <!-- Thêm module JS -->
  <script src="add_employee.js"></script>
</body>
</html>
```

---

### Ví Dụ 2: Admin - Dashboard Page

**File: `frontend/admin/index.html`**

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Admin Dashboard - DeepFace</title>
  
  <!-- 1️⃣ NHÚNG BACKGROUND CSS -->
  <link rel="stylesheet" href="../shared/background.css">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <!-- Nền sẽ được tạo tự động bởi background.js -->
  
  <div id="app">
    <!-- Sidebar Navigation -->
    <div class="sidebar glass-panel">
      <div class="logo">
        <h2>🔒 Admin Panel</h2>
      </div>
      <nav>
        <ul>
          <li><a href="index.html" class="active">📊 Dashboard</a></li>
          <li><a href="add_employee.html">➕ Thêm Nhân Viên</a></li>
          <li><a href="manage_list.html">👥 Quản Lý DS</a></li>
          <li><a href="view_logs.html">📋 Xem Logs</a></li>
        </ul>
      </nav>
    </div>
    
    <!-- Main Content -->
    <div class="main-content">
      <!-- Header -->
      <div class="header glass-panel-lg">
        <h1>📊 Dashboard</h1>
        <button id="logoutBtn">Đăng Xuất</button>
      </div>
      
      <!-- Stats Cards Container -->
      <div class="stats-container">
        <div class="stat-card glass-panel">
          <h3>👥 Tổng Nhân Viên</h3>
          <p class="stat-value">48</p>
        </div>
        
        <div class="stat-card glass-panel">
          <h3>🚪 Check-in Hôm Nay</h3>
          <p class="stat-value">45</p>
        </div>
        
        <div class="stat-card glass-panel">
          <h3>🚨 Cảnh Báo</h3>
          <p class="stat-value">2</p>
        </div>
        
        <div class="stat-card glass-panel">
          <h3>✅ Độ Chính Xác</h3>
          <p class="stat-value">97.5%</p>
        </div>
      </div>
      
      <!-- Activity Feed -->
      <div class="activity-section glass-panel-lg" style="margin-top: 30px;">
        <h2>📈 Hoạt Động Gần Đây</h2>
        <table>
          <thead>
            <tr>
              <th>Thời Gian</th>
              <th>Nhân Viên</th>
              <th>Hành Động</th>
              <th>Kết Quả</th>
            </tr>
          </thead>
          <tbody id="activityFeed">
            <!-- Dữ liệu sẽ được load bằng JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>
  
  <!-- 2️⃣ NHÚNG BACKGROUND JS -->
  <script src="../shared/background.js"></script>
  <script src="admin_dashboard.js"></script>
</body>
</html>
```

---

### Ví Dụ 3: User - Face Scan Page

**File: `frontend/user/face_scan.html`**

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Face Scan - DeepFace User</title>
  
  <!-- 1️⃣ NHÚNG BACKGROUND CSS -->
  <link rel="stylesheet" href="../shared/background.css">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <!-- Nền sẽ được tạo tự động bởi background.js -->
  
  <div id="app">
    <!-- Header -->
    <div class="header glass-panel-lg">
      <h1>👤 Face Recognition System</h1>
      <div class="user-info glass-panel-sm">
        <span id="userName">Đang tải...</span>
        <button id="logoutBtn">🚪 Logout</button>
      </div>
    </div>
    
    <!-- Main Container -->
    <div class="main-container">
      <!-- Camera Section -->
      <div class="camera-section glass-panel-lg">
        <h2>📷 Khởi Động Camera</h2>
        
        <div class="video-container">
          <video id="cameraStream" autoplay playsinline></video>
          <div class="capture-overlay"></div>
        </div>
        
        <div class="controls">
          <button id="startCameraBtn" class="btn-primary">▶️ Khởi Động Camera</button>
          <button id="captureBtn" class="btn-success" disabled>📸 Chụp & Xác Thực</button>
          <button id="stopCameraBtn" class="btn-danger" disabled>⏹️ Dừng</button>
        </div>
      </div>
      
      <!-- Result Section -->
      <div id="resultSection" style="display: none; margin-top: 30px;">
        <div class="result-card glass-panel-lg" id="resultCard">
          <!-- Kết quả sẽ được hiển thị ở đây -->
        </div>
      </div>
      
      <!-- Loading Spinner -->
      <div id="loadingSpinner" class="glass-panel" style="display: none; text-align: center; margin-top: 20px;">
        <p>⏳ Đang xử lý...</p>
      </div>
    </div>
  </div>
  
  <!-- 2️⃣ NHÚNG BACKGROUND JS -->
  <script src="../shared/background.js"></script>
  <script src="face_scan.js"></script>
</body>
</html>
```

---

### Ví Dụ 4: User - Check History Page

**File: `frontend/user/check_history.html`**

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Check History - DeepFace User</title>
  
  <!-- 1️⃣ NHÚNG BACKGROUND CSS -->
  <link rel="stylesheet" href="../shared/background.css">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <!-- Nền sẽ được tạo tự động bởi background.js -->
  
  <div id="app">
    <!-- Header -->
    <div class="header glass-panel-lg">
      <h1>📋 Check-in/Check-out History</h1>
      <button id="logoutBtn">🚪 Logout</button>
    </div>
    
    <!-- Stats Section -->
    <div class="stats-container">
      <div class="stat-card glass-panel">
        <h3>🟢 Check-in</h3>
        <p class="stat-value" id="checkInCount">--</p>
      </div>
      
      <div class="stat-card glass-panel">
        <h3>🔴 Check-out</h3>
        <p class="stat-value" id="checkOutCount">--</p>
      </div>
      
      <div class="stat-card glass-panel">
        <h3>📊 Tổng</h3>
        <p class="stat-value" id="totalCount">--</p>
      </div>
      
      <div class="stat-card glass-panel">
        <h3>📅 Hôm Nay</h3>
        <p class="stat-value" id="todayCount">--</p>
      </div>
    </div>
    
    <!-- Filters -->
    <div class="filters-section glass-panel-lg" style="margin-top: 30px;">
      <h2>🔍 Lọc Dữ Liệu</h2>
      
      <div class="filter-group">
        <label>Chọn Ngày</label>
        <input type="date" id="filterDate">
      </div>
      
      <div class="filter-group">
        <label>Chọn Tháng</label>
        <input type="month" id="filterMonth">
      </div>
      
      <button id="resetFilterBtn" class="btn-secondary">↻ Đặt Lại</button>
      <button id="exportCsvBtn" class="btn-primary">💾 Tải CSV</button>
    </div>
    
    <!-- History Table -->
    <div class="history-section glass-panel-lg" style="margin-top: 30px;">
      <h2>📝 Lịch Sử Chi Tiết</h2>
      
      <table id="historyTable">
        <thead>
          <tr>
            <th>Thời Gian</th>
            <th>Loại</th>
            <th>Độ Chính Xác</th>
            <th>Ghi Chú</th>
          </tr>
        </thead>
        <tbody>
          <!-- Dữ liệu sẽ được load bằng JS -->
        </tbody>
      </table>
    </div>
  </div>
  
  <!-- 2️⃣ NHÚNG BACKGROUND JS -->
  <script src="../shared/background.js"></script>
  <script src="check_history.js"></script>
</body>
</html>
```

---

## 🎨 Glass Panel Variations

### Standard Glass Panel (`.glass-panel`)
```html
<div class="glass-panel">
  📝 Nội dung bình thường
</div>
```

### Large Glass Panel (`.glass-panel-lg`)
```html
<div class="glass-panel-lg">
  📋 Nội dung lớn hơn, padding 30px
</div>
```

### Small Glass Panel (`.glass-panel-sm`)
```html
<div class="glass-panel-sm">
  🏷️ Nội dung nhỏ gọn
</div>
```

---

## 📦 Đường Dẫn Tương Đối (Relative Paths)

### Từ thư mục `admin/`

```html
<!-- CSS nằm ở: ../shared/background.css -->
<link rel="stylesheet" href="../shared/background.css">

<!-- JS nằm ở: ../shared/background.js -->
<script src="../shared/background.js"></script>
```

### Từ thư mục `user/`

```html
<!-- CSS nằm ở: ../shared/background.css -->
<link rel="stylesheet" href="../shared/background.css">

<!-- JS nằm ở: ../shared/background.js -->
<script src="../shared/background.js"></script>
```

### Folder Structure

```
frontend/
├── shared/
│   ├── background.css    ← Định nghĩa Mesh Gradient & Glass Panel
│   └── background.js     ← Tạo SVG Mesh Gradient
├── admin/
│   ├── index.html        ← ../shared/background.css
│   ├── add_employee.html ← ../shared/background.css
│   ├── manage_list.html  ← ../shared/background.css
│   ├── view_logs.html    ← ../shared/background.css
│   └── styles.css
└── user/
    ├── index.html        ← ../shared/background.css
    ├── face_scan.html    ← ../shared/background.css
    ├── check_history.html ← ../shared/background.css
    └── style.css
```

---

## ⚡ Performance Tips

1. **CSS-driven Animations**: Tất cả animations được chạy bằng CSS (không JS), nên mượt mà 60fps
2. **GPU Acceleration**: Sử dụng `will-change: transform, opacity` để kích hoạt GPU
3. **Fixed Background**: Background được set `position: fixed` nên không ảnh hưởng scroll
4. **Z-index Management**: Background nằm ở `z-index: -1`, nội dung ở `z-index: 1`

---

## 🐛 Debugging

### Kiểm tra Background Đã Load

```javascript
// Mở Browser Console (F12)
console.log(document.getElementById('mesh-gradient-container'));
// Nếu không null = Background đã load thành công
```

### Kiểm tra Glass Panel CSS

```css
/* Inspect element (F12) và kiểm tra .glass-panel styles */
/* Nên thấy: backdrop-filter: blur(10px) */
```

### Xem Animation Performance

```javascript
// Chrome DevTools → Performance tab → Record
// Kiểm tra FPS chart → Nên luôn ở 60fps
```

---

## ✅ Checklist Tích Hợp

- [ ] ✅ Thêm `<link>` tới `../shared/background.css` trong `<head>`
- [ ] ✅ Thêm `<script>` tới `../shared/background.js` trước `</body>`
- [ ] ✅ Bọc nội dung bằng `<div id="app">...</div>`
- [ ] ✅ Sử dụng `.glass-panel` cho UI components
- [ ] ✅ Test trên Chrome, Firefox, Edge
- [ ] ✅ Kiểm tra FPS = 60fps smooth
- [ ] ✅ Xóa console.log debug code

---

**Version**: 1.0  
**Updated**: May 4, 2026  
**Team**: UET - DeepFace Project
