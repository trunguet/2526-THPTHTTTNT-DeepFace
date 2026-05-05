import cv2
import os
import sys
import numpy as np
from pathlib import Path

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
minifas_path = os.path.join(current_dir, "minifas_core")
sys.path.insert(0, minifas_path)

from src.anti_spoof_predict import AntiSpoofPredict

def test_antispoof_pipeline():
    try:
        print("="*60)
        print("MiniFASNet Anti-Spoofing Test Pipeline")
        print("="*60)
        
        # 1. Initialize predictor
        print("\n[1] Khởi tạo AntiSpoofPredict...")
        predictor = AntiSpoofPredict(0)  # 0=CPU
        print("✅ AntiSpoofPredict loaded!")
        
        # 2. Load test image
        test_image_path = r"D:\DEEPFACE\2526-THPTHTTTNT-DeepFace\models\detection\test.jpg"
        print(f"\n[2] Tải ảnh test từ: {test_image_path}")
        
        if not os.path.exists(test_image_path):
            print(f"❌ Không tìm thấy ảnh tại: {test_image_path}")
            return
        
        img = cv2.imread(test_image_path)
        print(f"✅ Ảnh loaded: {img.shape}")
        
        # 3. Detect faces using built-in detector
        print("\n[3] Detect khuôn mặt...")
        bbox = predictor.get_bbox(img)
        
        if bbox is None:
            print("❌ Không phát hiện được mặt trong ảnh")
            return
        
        print(f"✅ Phát hiện mặt tại: {bbox}")
        x, y, w, h = bbox
        
        # 4. Run anti-spoofing check
        print("\n[4] Kiểm tra giả mạo...")
        
        # Get all models in the resources folder
        model_dir = os.path.join(minifas_path, "resources", "anti_spoof_models")
        model_files = [f for f in os.listdir(model_dir) if f.endswith('.pth')]
        
        print(f"Các model sẵn có: {model_files}\n")
        
        results_summary = []
        
        for model_file in model_files:
            model_path = os.path.join(model_dir, model_file)
            try:
                print(f"  Testing với model: {model_file}")
                result = predictor.predict(img, model_path)
                
                # result = [spoof_prob, real_prob]
                spoof_score = result[0][0]
                real_score = result[0][1]
                is_real = real_score > spoof_score
                
                print(f"    - Spoof Score: {spoof_score:.4f}")
                print(f"    - Real Score:  {real_score:.4f}")
                print(f"    - Kết luận: {'✅ REAL FACE' if is_real else '❌ SPOOF/ATTACK'}")
                
                results_summary.append({
                    'model': model_file,
                    'is_real': is_real,
                    'real_score': real_score,
                    'spoof_score': spoof_score
                })
            except Exception as e:
                print(f"    ❌ Error với model {model_file}: {e}")
        
        # 5. Visualize results
        print("\n[5] Vẽ kết quả lên ảnh...")
        img_result = img.copy()
        
        # Draw bbox
        cv2.rectangle(img_result, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # Draw overall result
        avg_real_score = np.mean([r['real_score'] for r in results_summary])
        is_real_overall = avg_real_score > 0.5
        
        label = f"REAL (Conf: {avg_real_score:.2f})" if is_real_overall else f"SPOOF (Conf: {1-avg_real_score:.2f})"
        color = (0, 255, 0) if is_real_overall else (0, 0, 255)
        
        cv2.putText(img_result, label, (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        output_path = os.path.join(current_dir, "result_antispoof_test.jpg")
        cv2.imwrite(output_path, img_result)
        print(f"✅ Kết quả lưu tại: {output_path}")
        
        # 6. Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Kết luận chung: {'✅ REAL FACE' if is_real_overall else '❌ SPOOF/ATTACK'}")
        print(f"Confidence: {max(avg_real_score, 1-avg_real_score):.4f}")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_antispoof_pipeline()
