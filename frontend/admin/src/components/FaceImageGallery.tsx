// - Hiển thị ảnh mặt đã upload
// - Hiển thị trạng thái xử lý
// - Nếu lỗi thì hiện error_message

// ví dụ face_1.jpg     processed
// face_2.jpg     failed - No face detected
// face_3.jpg     pending

// polling: Upload ảnh xong
// → gọi GET /employees/{id}/face-images
// → nếu còn ảnh pending/processing
// → sau 2 giây gọi lại
// → khi tất cả processed/failed thì dừng