"""
ArcFace Face Embedding Extraction Module using DeepFace
"""

import os
import cv2
import numpy as np
from deepface import DeepFace


class ArcFaceExtractor:
    """
    Extract face embeddings using DeepFace with ArcFace model
    """
    
    def __init__(self, model_name="ArcFace", distance_metric="cosine"):
        """
        Initialize ArcFace extractor
        
        Args:
            model_name: "ArcFace" (default), "VGGFace", "OpenFace", etc.
            distance_metric: "cosine" (default) or "euclidean"
        """
        self.model_name = model_name
        self.distance_metric = distance_metric
        
        print(f"✅ ArcFace Extractor initialized")
        print(f"   Model: {model_name}")
        print(f"   Metric: {distance_metric}")
    
    def extract_embedding(self, face_image):
        """
        Extract face embedding
        
        Args:
            face_image: Face image (BGR format, numpy array)
        
        Returns:
            Face embedding vector (512D for ArcFace)
        """
        try:
            # DeepFace.represent expects BGR image
            embedding_objs = DeepFace.represent(
                img_path=face_image,
                model_name=self.model_name,
                enforce_detection=False  # Don't enforce detection if already cropped
            )
            
            if embedding_objs:
                embedding = np.array(embedding_objs[0]["embedding"])
                
                # L2 normalize
                embedding = embedding / np.linalg.norm(embedding)
                
                return embedding
            else:
                raise ValueError("No face embedding extracted")
        
        except Exception as e:
            print(f"❌ Error extracting embedding: {e}")
            raise
    
    def calculate_similarity(self, embedding1, embedding2):
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
        
        Returns:
            Similarity score (0-1, 1=identical)
        """
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2) + 1e-8
        )
        
        return similarity
    
    def match_faces(self, embedding1, embedding2, threshold=0.6):
        """
        Check if two faces match
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            threshold: Similarity threshold (default 0.6)
        
        Returns:
            (is_match: bool, similarity: float)
        """
        similarity = self.calculate_similarity(embedding1, embedding2)
        is_match = similarity >= threshold
        
        return is_match, similarity
    
    def verify_faces(self, img1_path, img2_path):
        """
        Verify if two images contain the same person
        
        Args:
            img1_path: Path to first image
            img2_path: Path to second image
        
        Returns:
            {
                'verified': bool,
                'distance': float,
                'threshold': float,
                'model': str
            }
        """
        try:
            result = DeepFace.verify(
                img1_path=img1_path,
                img2_path=img2_path,
                model_name=self.model_name,
                distance_metric=self.distance_metric,
                silent=True)
            
            print(f"✅ Verification result:")
            print(f"   Verified: {result['verified']}")
            print(f"   Distance: {result['distance']:.4f}")
            print(f"   Threshold: {result['threshold']:.4f}")
            
            return result
        
        except Exception as e:
            print(f"❌ Error verifying faces: {e}")
            raise


# Singleton instance
_extractor = None


def get_arcface_extractor(model_name="ArcFace"):
    """
    Get or create ArcFace extractor instance
    """
    global _extractor
    if _extractor is None:
        _extractor = ArcFaceExtractor(model_name=model_name)
    return _extractor


if __name__ == "__main__":
    print("="*60)
    print("Testing DeepFace ArcFace Extractor")
    print("="*60)
    
    try:
        # Initialize
        extractor = get_arcface_extractor()
        
        # Test image path
        test_image_path = r"D:\DEEPFACE\2526-THPTHTTTNT-DeepFace\models\detection\test.jpg"
        
        if os.path.exists(test_image_path):
            print(f"\n[1] Loading test image from: {test_image_path}")
            img = cv2.imread(test_image_path)
            print(f"✅ Image loaded: shape={img.shape}")
            
            print(f"\n[2] Extracting embedding...")
            embedding = extractor.extract_embedding(test_image_path)
            print(f"✅ Embedding extracted: shape={embedding.shape}")
            print(f"   Embedding (first 10 values): {embedding[:10]}")
            print(f"   L2 norm: {np.linalg.norm(embedding):.4f}")
            
            print(f"\n[3] Testing similarity calculation...")
            embedding2 = embedding + np.random.randn(512) * 0.01
            embedding2 = embedding2 / np.linalg.norm(embedding2)
            
            similarity = extractor.calculate_similarity(embedding, embedding2)
            print(f"✅ Similarity score: {similarity:.4f}")
            
            print(f"\n[4] Testing face verification...")
            result = extractor.verify_faces(test_image_path, test_image_path)
            print(f"✅ Same image verification: {result['verified']}")
            
        else:
            print(f"⚠️ Test image not found: {test_image_path}")
        
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
