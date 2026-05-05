import sys
import os

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
minifas_path = os.path.join(current_dir, "minifas_core")
sys.path.insert(0, minifas_path)

try:
    print("[1] Khởi tạo AntiSpoofPredict...")
    from src.anti_spoof_predict import AntiSpoofPredict
    
    predictor = AntiSpoofPredict(0)  # 0=CPU
    print("✅ AntiSpoofPredict loaded!")
    
    print("\n[2] Kiểm tra model directory:")
    model_dir = os.path.join(minifas_path, "resources", "anti_spoof_models")
    models = os.listdir(model_dir)
    print(f"✅ Models found: {models}")
    
    print("\n[3] Setup thành công! Sẵn sàng dùng MiniFASNet")
    print("\nDùng như sau:")
    print("  from src.anti_spoof_predict import AntiSpoofPredict")
    print("  predictor = AntiSpoofPredict(0)")
    print("  result = predictor.predict_cv2(image, bbox)")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
