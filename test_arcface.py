import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
os.environ["DEEPFACE_HOME"] = str(PROJECT_ROOT)

print("DEEPFACE_HOME =", os.environ["DEEPFACE_HOME"])

weight_path = PROJECT_ROOT / ".deepface" / "weights" / "arcface_weights.h5"
print("ArcFace weight path:", weight_path)
print("Exists:", weight_path.exists())

from deepface import DeepFace

print("DeepFace imported successfully.")

model = DeepFace.build_model("ArcFace")

print("Loaded ArcFace successfully!")
print(type(model))
