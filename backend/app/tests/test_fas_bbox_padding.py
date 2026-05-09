import unittest

import numpy as np

from app.ml.detector import FaceDetection


class FasBboxPaddingTests(unittest.TestCase):
    def test_padding_clamps_to_image(self) -> None:
        # This test mirrors the padding math in MiniFASNetAntiSpoofing.predict.
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        detection = FaceDetection(bbox_xyxy=(10, 10, 60, 70), landmarks_5=None, score=0.9)
        x1, y1, x2, y2 = detection.bbox_xyxy
        h_img, w_img = img.shape[:2]
        pad_ratio = 0.15
        pad_x = int(round((x2 - x1) * pad_ratio))
        pad_y = int(round((y2 - y1) * pad_ratio))
        x1p = max(0, x1 - pad_x)
        y1p = max(0, y1 - pad_y)
        x2p = min(w_img, x2 + pad_x)
        y2p = min(h_img, y2 + pad_y)
        self.assertGreaterEqual(x1p, 0)
        self.assertGreaterEqual(y1p, 0)
        self.assertLessEqual(x2p, w_img)
        self.assertLessEqual(y2p, h_img)
        self.assertGreater(x2p - x1p, 0)
        self.assertGreater(y2p - y1p, 0)


if __name__ == "__main__":
    unittest.main()

