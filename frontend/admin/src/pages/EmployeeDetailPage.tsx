// route:
// /employees/:id
// flow : Mở trang chi tiết nhân viên
// → gọi employeeApi.getById(id)
// → gọi faceImageApi.listByEmployee(id)
// → hiển thị thông tin nhân viên
// → upload ảnh khuôn mặt
// → xem trạng thái xử lý ảnh

// UI gợi ý : Employee Detail
// ------------------------------------------------
// Mã nhân viên: EMP001
// Họ tên: Nguyễn Văn A
// Phòng ban: AI Lab
// Chức vụ: Intern
// Email: a@example.com
// Trạng thái: Active

// Face Images
// ------------------------------------------------
// [Upload images]

// Danh sách ảnh:
// Ảnh                Trạng thái       Ghi chú
// face1.jpg          processed        OK
// face2.jpg          failed           Multiple faces detected
// face3.jpg          pending          Waiting for worker
// upload ảnh → worker extract vector → Qdrant lưu embedding
