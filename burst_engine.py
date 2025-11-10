#!/usr/bin/env python3
"""
burst_engine.py - v8.0 CLIP-Based Burst Detection
Part of PhotoSort by Nick (∞vision crew)

This module uses CLIP embeddings for semantic burst detection.
Unlike perceptual hashing (imagehash), CLIP understands the *content* of images,
not just visual similarity.

Example:
- 10 photos of "dog catching ball" with different compositions → Same burst
- 10 photos of different dogs in similar poses → Different bursts

Dependencies:
- sentence-transformers (for CLIP model)
- sklearn (for DBSCAN clustering)
- Pillow (for image loading)
"""

import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image
import io

# CLIP model from sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False

# DBSCAN for clustering
try:
    from sklearn.cluster import DBSCAN
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Check if all dependencies are available
V8_BURST_READY = CLIP_AVAILABLE and SKLEARN_AVAILABLE


class CLIPBurstDetector:
    """
    CLIP-based semantic burst detection.
    
    Uses CLIP embeddings to understand image content and DBSCAN to cluster
    semantically similar images into burst groups.
    """
    
    def __init__(self, model_name: str = "clip-ViT-B-32", eps: float = 0.15, min_samples: int = 2):
        """
        Initialize CLIP burst detector.
        
        Args:
            model_name: CLIP model to use (default: clip-ViT-B-32)
            eps: DBSCAN epsilon (maximum distance for clustering)
            min_samples: Minimum burst size (default: 2)
        """
        if not V8_BURST_READY:
            raise ImportError("CLIP burst detection requires: sentence-transformers, scikit-learn")
        
        self.model = SentenceTransformer(model_name)
        self.eps = eps
        self.min_samples = min_samples
        self.embeddings = {}
    
    def get_embedding(self, image_path: Path, image_bytes: Optional[bytes] = None) -> Optional[np.ndarray]:
        """
        Get CLIP embedding for an image.
        
        Args:
            image_path: Path to the image
            image_bytes: Optional pre-loaded image bytes
        
        Returns:
            512-dimensional embedding vector or None on failure
        """
        try:
            if image_bytes:
                img = Image.open(io.BytesIO(image_bytes))
            else:
                img = Image.open(image_path)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get CLIP embedding
            embedding = self.model.encode(img, convert_to_numpy=True)
            return embedding
            
        except Exception as e:
            print(f"    Error getting embedding for {image_path.name}: {e}")
            return None
    
    def compute_embeddings(self, image_paths: List[Path]) -> dict:
        """
        Compute embeddings for multiple images.
        
        Args:
            image_paths: List of image paths
        
        Returns:
            Dictionary mapping paths to embeddings
        """
        embeddings = {}
        
        for path in image_paths:
            embedding = self.get_embedding(path)
            if embedding is not None:
                embeddings[path] = embedding
        
        self.embeddings = embeddings
        return embeddings
    
    def detect_bursts(self, image_paths: List[Path]) -> List[List[Path]]:
        """
        Detect burst groups using CLIP + DBSCAN clustering.
        
        Args:
            image_paths: List of image paths to analyze
        
        Returns:
            List of burst groups (each group is a list of paths)
        """
        # Compute embeddings
        embeddings = self.compute_embeddings(image_paths)
        
        if len(embeddings) < 2:
            return []
        
        # Prepare data for clustering
        paths_list = list(embeddings.keys())
        embedding_matrix = np.array([embeddings[p] for p in paths_list])
        
        # Run DBSCAN clustering
        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric='cosine')
        labels = clustering.fit_predict(embedding_matrix)
        
        # Group images by cluster label
        clusters = {}
        for path, label in zip(paths_list, labels):
            if label == -1:
                # Noise points (not in any cluster)
                continue
            
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(path)
        
        # Sort each cluster by filename (chronological order)
        burst_groups = []
        for cluster_paths in clusters.values():
            sorted_paths = sorted(cluster_paths, key=lambda p: p.name)
            if len(sorted_paths) >= self.min_samples:
                burst_groups.append(sorted_paths)
        
        return burst_groups


# Convenience functions for PhotoSort integration

def detect_bursts_clip(
    image_paths: List[Path],
    eps: float = 0.15,
    min_samples: int = 2
) -> List[List[Path]]:
    """
    Detect burst groups using CLIP embeddings.
    
    This is the main entry point for PhotoSort.
    
    Args:
        image_paths: List of image paths to analyze
        eps: DBSCAN epsilon (lower = tighter clusters)
        min_samples: Minimum burst size
    
    Returns:
        List of burst groups
    """
    if not V8_BURST_READY:
        raise ImportError("CLIP burst detection not available")
    
    detector = CLIPBurstDetector(eps=eps, min_samples=min_samples)
    return detector.detect_bursts(image_paths)


def is_available() -> bool:
    """Check if CLIP burst detection is available."""
    return V8_BURST_READY


def get_status() -> str:
    """Get status message for burst engine."""
    if V8_BURST_READY:
        return "✓ CLIP burst detection available"
    
    missing = []
    if not CLIP_AVAILABLE:
        missing.append("sentence-transformers")
    if not SKLEARN_AVAILABLE:
        missing.append("scikit-learn")
    
    return f"⚠️  CLIP burst detection unavailable. Missing: {', '.join(missing)}"


# Installation helper
def print_installation_instructions():
    """Print instructions for installing dependencies."""
    print("\n" + "="*60)
    print(" CLIP Burst Detection Setup")
    print("="*60)
    print("\n To enable CLIP-based burst detection, install:")
    print("\n   pip install sentence-transformers scikit-learn")
    print("\n First run will download the CLIP model (~600MB)")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Test the module
    print("Testing burst_engine.py...")
    print(get_status())
    
    if not V8_BURST_READY:
        print_installation_instructions()