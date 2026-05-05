# -*- coding: utf-8 -*-
# @Time : 20-6-9 上午10:20
# @Author : zhuying
# @Company : Minivision
# @File : anti_spoof_predict.py
# @Software : PyCharm

import os
import cv2
import math
import torch
import numpy as np
import torch.nn.functional as F
from ultralytics import YOLO

from src.model_lib.MiniFASNet import MiniFASNetV1, MiniFASNetV2,MiniFASNetV1SE,MiniFASNetV2SE
from src.data_io import transform as trans
from src.utility import get_kernel, parse_model_name

MODEL_MAPPING = {
    'MiniFASNetV1': MiniFASNetV1,
    'MiniFASNetV2': MiniFASNetV2,
    'MiniFASNetV1SE':MiniFASNetV1SE,
    'MiniFASNetV2SE':MiniFASNetV2SE
}


class Detection:
    def __init__(self):
        # Lazily load YOLO only when bbox is not provided by the main pipeline.
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.yolo_path = os.path.normpath(os.path.join(current_dir, "../../../../models/detection/yolov8n-face.pt"))
        self.detector = None
        self.detector_confidence = 0.6

    def get_bbox(self, img):
        if self.detector is None:
            self.detector = YOLO(self.yolo_path)

        # Use YOLOv8 detection
        results = self.detector(img, verbose=False)
        
        if not results or len(results[0].boxes) == 0:
            return None
        
        # Get the first (highest confidence) detection
        box = results[0].boxes.xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = map(int, box)
        
        # Return bbox in format [x, y, w, h]
        bbox = [x1, y1, x2-x1, y2-y1]
        return bbox


class AntiSpoofPredict(Detection):
    def __init__(self, device_id):
        super(AntiSpoofPredict, self).__init__()
        self.device = torch.device("cuda:{}".format(device_id)
                                   if torch.cuda.is_available() else "cpu")

    def _load_model(self, model_path):
        # define model
        model_name = os.path.basename(model_path)
        h_input, w_input, model_type, _ = parse_model_name(model_name)
        self.kernel_size = get_kernel(h_input, w_input,)
        self.model = MODEL_MAPPING[model_type](conv6_kernel=self.kernel_size).to(self.device)

        # load model weight
        state_dict = torch.load(model_path, map_location=self.device)
        keys = iter(state_dict)
        first_layer_name = keys.__next__()
        if first_layer_name.find('module.') >= 0:
            from collections import OrderedDict
            new_state_dict = OrderedDict()
            for key, value in state_dict.items():
                name_key = key[7:]
                new_state_dict[name_key] = value
            self.model.load_state_dict(new_state_dict)
        else:
            self.model.load_state_dict(state_dict)
        return None

    def predict(self, img, model_path, bbox=None):
        """
        Predict if face is real or spoof.
        
        Args:
            img: Input image (numpy array)
            model_path: Path to model file
            bbox: [x, y, w, h] of face region (optional, will use detector if not provided)
        
        Returns:
            numpy array with [spoof_score, real_score]
        """
        # Get bbox if not provided
        if bbox is None:
            bbox = self.get_bbox(img)
        
        if bbox is None:
            raise ValueError("No face detected and no bbox provided")
        
        # Crop face region
        x, y, w, h = bbox
        face = img[y:y+h, x:x+w]
        
        # Resize to 80x80 (model input size)
        face_resized = cv2.resize(face, (80, 80))
        
        # Transform to tensor
        test_transform = trans.Compose([
            trans.ToTensor(),
        ])
        img_tensor = test_transform(face_resized)
        img_tensor = img_tensor.unsqueeze(0).to(self.device)
        
        # Load and run model
        self._load_model(model_path)
        self.model.eval()
        with torch.no_grad():
            result = self.model.forward(img_tensor)
            result = F.softmax(result).cpu().numpy()
        return result
    
    def predict_cv2(self, img, bbox):
        """
        Quick prediction with first model.
        
        Args:
            img: Input image
            bbox: [x, y, w, h] of face region
        
        Returns:
            (label, score) - label: 1=Real, 0=Spoof; score: confidence
        """
        model_dir = os.path.join(
            os.path.dirname(__file__),
            "../resources/anti_spoof_models"
        )
        # Use the first available model
        model_files = [f for f in os.listdir(model_dir) if f.endswith('.pth')]
        if not model_files:
            raise FileNotFoundError(f"No model files found in {model_dir}")
        
        model_path = os.path.join(model_dir, model_files[0])
        
        result = self.predict(img, model_path, bbox)
        spoof_score = result[0][0]
        real_score = result[0][1]
        
        label = 1 if real_score > spoof_score else 0
        score = max(real_score, spoof_score)
        
        return label, score











