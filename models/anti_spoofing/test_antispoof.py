import cv2
import os
import sys
import torch
import numpy as np
from ultralytics import YOLO

# 1. Cấu hình đường dẫn để Python tìm thấy code bên trong minifas_core
current_dir = os.path.dirname(os.path.abspath(__file__))
minifas_path = os.path.join(current_dir, "minifas_core")
sys.path.append(minifas_path)

# 2. Bây giờ mới thực hiện import từ core của tác giả
# Lưu ý: Import trực tiếp từ 'src' vì chúng ta đã add 'minifas_core' vào path
from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropGenerator

def test_integration():
    # --- CẤU HÌNH ĐƯỜNG DẪN TUYỆT ĐỐI ---
    yolo_model_path = r"D:\DEEPFACE\2526-THPTHTTTNT-DeepFace\models\detection\yolov8n-face.pt"
    image_path = r"D:\DEEPFACE\2526-THPTHTTTNT-DeepFace\models\detection\test.jpg"
    fas_model_dir = os.path.join(minifas_path, "resources", "anti_spoof_models")
    output_path = os.path.join(current_dir, "result_antispoof.jpg")

    # 1. Load Models
    print("[INFO] Đang load YOLOv8 và MiniFASNet...")
    face_detector = YOLO(yolo_model_path)
    # Khởi tạo predictor (0 là CPU, 1 là GPU nếu có)
    anti_spoof_predictor = AntiSpoofPredict(0)

    # 2. Đọc ảnh
    img = cv2.imread(image_path)
    if img is None:
        print(f"[LỖI] Không tìm thấy ảnh tại: {image_path}")
        return

    # 3. Bước 1: Phát hiện khuôn mặt bằng YOLO
    results = face_detector(img, verbose=False)
    if not results or len(results[0].boxes) == 0:
        print("[INFO] Không tìm thấy mặt.")
        return

    # Lấy khuôn mặt đầu tiên
    box = results[0].boxes.xyxy[0].cpu().numpy()
    x1, y1, x2, y2 = map(int, box)
    
    # MiniFASNet cần format: x, y, w, h
    fas_bbox = [x1, y1, x2-x1, y2-y1]

    # 4. Bước 2: Kiểm tra thật giả (Ensemble 2 models)
    print("[INFO] Đang kiểm tra Anti-Spoofing...")
    prediction = np.zeros((1, 3))
    
    # Duyệt qua các file model .pth trong resources
    model_files = [f for f in os.listdir(fas_model_dir) if f.endswith(".pth")]
    for model_name in model_files:
        model_full_path = os.path.join(fas_model_dir, model_name)
        anti_spoof_predictor._load_model(model_full_path)
        prediction += anti_spoof_predictor.predict(img, fas_bbox)

    # Giải mã kết quả
    label = np.argmax(prediction)
    value = prediction[0][label] / len(model_files)

    # 5. Vẽ kết quả
    # Label 1 là Real, các label khác là Fake
    is_real = (label == 1)
    color = (0, 255, 0) if is_real else (0, 0, 255)
    result_text = f"{'REAL' if is_real else 'FAKE'} ({value:.2f})"
    
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    cv2.putText(img, result_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    cv2.imwrite(output_path, img)
    print(f"\n[XONG] Kết quả: {result_text}")
    print(f"Đã lưu kết quả tại: {output_path}")

if __name__ == "__main__":
    test_integration()