// - Hiển thị CameraView
// - Chụp frame từ video mỗi 1 giây
// - Gửi frame lên backend
// - Nhận kết quả
// - Hiển thị ResultCard
// - Có thể hiển thị recent history

// pipeline: Start Camera
// → set interval 1 giây
// → capture frame
// → recognitionApi.recognizeFrame(blob)
// → setResult(response)
// → ResultCard update

// điểm quan trọng :
// Không gửi request mới nếu request trước chưa xong.