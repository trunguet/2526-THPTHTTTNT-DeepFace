import cv2
import os
import urllib.request
from ultralytics import YOLO

def test_face_detection():
    model_path = r"D:\DEEPFACE\2526-THPTHTTTNT-DeepFace\models\detection\yolov8n-face.pt"
    image_path = r"D:\DEEPFACE\2526-THPTHTTTNT-DeepFace\models\detection\test.jpg"
    output_path = r"D:\DEEPFACE\2526-THPTHTTTNT-DeepFace\models\detection\result_test.jpg"
    
    print(f"[INFO] Đang load model tại:\n{model_path}")
    model = YOLO(model_path, task='pose') 

    # --- TÍNH NĂNG MỚI: TỰ ĐỘNG TẢI ẢNH NẾU CHƯA CÓ ---
    if not os.path.exists(image_path):
        print(f"\n[INFO] Chưa có ảnh test.jpg. Đang tự động tải ảnh mẫu từ Internet về...")
        url = "https://ultralytics.com/images/zidane.jpg" # Ảnh mẫu nổi tiếng của Ultralytics (có 2 người)
        urllib.request.urlretrieve(url, image_path)
        print("[INFO] Đã tải ảnh thành công!")

    print(f"\n[INFO] Đang load ảnh tại:\n{image_path}")
    img = cv2.imread(image_path)
    
    if img is None:
        print(f"\n[LỖI] Đã tải ảnh nhưng file bị lỗi không đọc được!")
        return

    print("\n[INFO] Đang chạy nhận diện...")
    results = model(img)
    result = results[0]  
    
    if result.boxes is None or len(result.boxes) == 0:
        print("\n[INFO] Không tìm thấy khuôn mặt nào.")
        return

    boxes = result.boxes.xyxy.cpu().numpy() 
    landmarks = result.keypoints.xy.cpu().numpy() if result.keypoints is not None else []

    for i in range(len(boxes)):
        x1, y1, x2, y2 = map(int, boxes[i])
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        if len(landmarks) > i:
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255)] 
            for j, pt in enumerate(landmarks[i]):
                cv2.circle(img, (int(pt[0]), int(pt[1])), 4, colors[j % len(colors)], -1)
                
    cv2.imwrite(output_path, img)
    print(f"\n[INFO] THÀNH CÔNG! Hãy mở cây thư mục bên trái, tìm file ảnh để xem kết quả:\n{output_path}")

if __name__ == "__main__":
    test_face_detection()