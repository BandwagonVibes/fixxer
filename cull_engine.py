#!/usr/bin/env python3
"""
cull_engine.py - PhotoSort v8.0 Quality Assessment Engine

Two-stage quality assessment:
1. Fast BRISQUE screening (all images)
2. VLM analysis for ambiguous cases (consolidated: cull + name + critique)

Author: Claude (Anthropic) + Nick (∞vision crew)
"""

import json
import base64
import requests
from pathlib import Path
from typing import Optional, Dict, Tuple, Any
from io import BytesIO
import subprocess
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# ==============================================================================
# I. DEPENDENCY CHECKS
# ==============================================================================

BRISQUE_AVAILABLE = False
PIL_AVAILABLE = False
CV2_AVAILABLE = False

try:
    from image_quality import brisque
    BRISQUE_AVAILABLE = True
except ImportError:
    pass

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    pass

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    pass

# ==============================================================================
# II. CONFIGURATION
# ==============================================================================

# BRISQUE thresholds (lower score = better quality)
# These are starting points - calibrate based on your camera/style
DEFAULT_BRISQUE_KEEPER_THRESHOLD = 35.0  # Below this = definite keeper
DEFAULT_BRISQUE_AMBIGUOUS_THRESHOLD = 50.0  # Above this = likely dud

# VLM configuration
DEFAULT_VLM_MODEL = "openbmb/minicpm-v2.6:q4_K_M"  # Nick's perfect JSON model
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_VLM_TIMEOUT = 60  # seconds

# RAW file extensions
RAW_EXTENSIONS = {'.rw2', '.cr2', '.nef', '.arw', '.dng', '.orf', '.raf'}

# Patch-based Laplacian configuration (legacy fallback)
DEFAULT_LAPLACIAN_THRESHOLD = 40.0
DEFAULT_PATCH_SIZE = 256

# ==============================================================================
# III. CONSOLIDATED VLM PROMPT
# ==============================================================================

VLM_CONSOLIDATED_PROMPT = """You are a professional photo editor analyzing this image for a photographer's workflow.

Provide a JSON response with THREE sections:

1. TECHNICAL ASSESSMENT (for culling decision):
   - is_keeper: Is this technically sound enough to keep? (true/false)
   - is_dud: Should this be culled/discarded? (true/false)
   - dud_reason: If dud, explain WHY in one sentence (blur type, exposure issue, etc.)
   - technical_notes: Brief technical observations about sharpness, exposure, noise

2. FILE NAMING (for organization):
   - suggested_filename: Descriptive filename using 2-4 words, lowercase, hyphens (e.g., "golden-hour-beach-portrait")
   - subject: Main subject/content (e.g., "Portrait", "Landscape", "Action")
   - location_type: Type of location if relevant (e.g., "Beach", "Studio", "Urban")
   - time_of_day: Time of day if relevant (e.g., "Golden hour", "Blue hour", "Midday")

3. CREATIVE CRITIQUE (for improvement):
   - overall_score: Rate 1-10 for overall quality
   - composition: Analysis of framing, rule of thirds, leading lines, balance
   - lighting: Quality and direction of light, shadows, highlights
   - technical_quality: Sharpness, focus, exposure, noise level
   - strengths: List 2-3 things that work well
   - improvements: List 2-3 actionable suggestions
   - mood: Overall emotional tone/feeling of the image

CRITICAL DISTINCTIONS (avoid false positives):
- Artistic motion blur vs camera shake blur
- Intentional bokeh/shallow DOF vs misfocus
- Creative underexposure vs technical failure
- High ISO grain (acceptable) vs unsharp blur (reject)
- Intentional vignetting vs lens problems

OUTPUT FORMAT:
Respond with ONLY valid JSON. No markdown, no code blocks, no explanation.

Example structure:
{
  "technical": {
    "is_keeper": true,
    "is_dud": false,
    "dud_reason": null,
    "technical_notes": "Sharp focus on eyes, well exposed, minimal noise"
  },
  "naming": {
    "suggested_filename": "sunset-silhouette-beach",
    "subject": "Silhouette",
    "location_type": "Beach",
    "time_of_day": "Sunset"
  },
  "critique": {
    "overall_score": 8,
    "composition": "Strong rule of thirds, horizon well placed",
    "lighting": "Beautiful golden hour backlight",
    "technical_quality": "Sharp, good exposure, low noise",
    "strengths": ["Dramatic silhouette", "Beautiful colors", "Strong composition"],
    "improvements": ["Could crop tighter", "Slightly blown highlights"],
    "mood": "Peaceful, contemplative, warm"
  }
}"""

# ==============================================================================
# IV. IMAGE LOADING UTILITIES
# ==============================================================================

def load_image_for_brisque(image_path: Path) -> Optional[Any]:
    """
    Load image for BRISQUE analysis (needs PIL Image).
    
    Args:
        image_path: Path to image file
        
    Returns:
        PIL Image or None
    """
    if not PIL_AVAILABLE:
        return None
    
    try:
        # Handle RAW files
        if image_path.suffix.lower() in RAW_EXTENSIONS:
            try:
                result = subprocess.run(
                    ['dcraw', '-e', '-c', str(image_path)],
                    capture_output=True,
                    check=True,
                    timeout=5
                )
                img = Image.open(BytesIO(result.stdout))
                return img
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                return None
        
        # Regular image
        img = Image.open(image_path)
        return img
        
    except Exception:
        return None

def load_image_for_laplacian(image_path: Path) -> Optional[np.ndarray]:
    """
    Load image for Laplacian analysis (needs OpenCV).
    
    Args:
        image_path: Path to image file
        
    Returns:
        OpenCV image (numpy array) or None
    """
    if not CV2_AVAILABLE:
        return None
    
    try:
        # Handle RAW files
        if image_path.suffix.lower() in RAW_EXTENSIONS:
            try:
                result = subprocess.run(
                    ['dcraw', '-e', '-c', str(image_path)],
                    capture_output=True,
                    check=True,
                    timeout=5
                )
                img_array = np.frombuffer(result.stdout, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                return img
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                return None
        
        # Regular image
        img = cv2.imread(str(image_path))
        return img
        
    except Exception:
        return None

def encode_image_for_vlm(image_path: Path) -> Optional[str]:
    """
    Encode image to base64 for VLM API.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Base64 encoded string or None
    """
    try:
        # Handle RAW files
        if image_path.suffix.lower() in RAW_EXTENSIONS:
            try:
                result = subprocess.run(
                    ['dcraw', '-e', '-c', str(image_path)],
                    capture_output=True,
                    check=True,
                    timeout=5
                )
                return base64.b64encode(result.stdout).decode('utf-8')
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                return None
        
        # Regular image
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
            
    except Exception:
        return None

# ==============================================================================
# V. BRISQUE QUALITY ASSESSMENT
# ==============================================================================

def assess_with_brisque(image_path: Path) -> Optional[Dict[str, Any]]:
    """
    Assess image quality using BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator).
    
    BRISQUE is a no-reference image quality metric that:
    - Detects blur, noise, compression artifacts
    - Works on natural scene statistics
    - Fast (~20-30ms per image)
    - Score range: 0-100 (lower = better quality)
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dictionary with:
        - score: BRISQUE score (float)
        - verdict: 'keeper' | 'ambiguous' | 'dud'
        - method: 'brisque'
    """
    if not BRISQUE_AVAILABLE:
        return None
    
    img = load_image_for_brisque(image_path)
    if img is None:
        return None
    
    try:
        # Calculate BRISQUE score
        score = brisque.score(img)
        
        # Determine verdict based on thresholds
        if score < DEFAULT_BRISQUE_KEEPER_THRESHOLD:
            verdict = 'keeper'
        elif score < DEFAULT_BRISQUE_AMBIGUOUS_THRESHOLD:
            verdict = 'ambiguous'
        else:
            verdict = 'dud'
        
        return {
            'score': float(score),
            'verdict': verdict,
            'method': 'brisque'
        }
        
    except Exception:
        return None

# ==============================================================================
# VI. PATCH-BASED LAPLACIAN (Legacy Fallback)
# ==============================================================================

def assess_with_laplacian_patch(image_path: Path,
                               patch_size: int = DEFAULT_PATCH_SIZE,
                               threshold: float = DEFAULT_LAPLACIAN_THRESHOLD) -> Optional[Dict[str, Any]]:
    """
    Assess sharpness using patch-based Laplacian variance (v1.5 improvement).
    
    This fixes the "bokeh killer" problem by finding the SHARPEST region
    instead of using a global average.
    
    Args:
        image_path: Path to image file
        patch_size: Size of patches to analyze
        threshold: Variance threshold for sharpness
        
    Returns:
        Dictionary with:
        - score: Maximum Laplacian variance found
        - verdict: 'keeper' | 'dud'
        - method: 'laplacian_patch'
    """
    if not CV2_AVAILABLE:
        return None
    
    img = load_image_for_laplacian(image_path)
    if img is None:
        return None
    
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        max_variance = 0.0
        stride_x = patch_size // 2
        stride_y = patch_size // 2
        
        # Scan image with overlapping patches
        for y in range(0, h - patch_size, stride_y):
            for x in range(0, w - patch_size, stride_x):
                patch = gray[y:y + patch_size, x:x + patch_size]
                variance = cv2.Laplacian(patch, cv2.CV_64F).var()
                max_variance = max(max_variance, variance)
        
        # Determine verdict
        verdict = 'keeper' if max_variance >= threshold else 'dud'
        
        return {
            'score': float(max_variance),
            'verdict': verdict,
            'method': 'laplacian_patch'
        }
        
    except Exception:
        return None

# ==============================================================================
# VII. VLM ANALYSIS (Consolidated)
# ==============================================================================

def get_vlm_analysis(image_path: Path,
                    model_name: str = DEFAULT_VLM_MODEL,
                    ollama_url: str = DEFAULT_OLLAMA_URL,
                    timeout: int = DEFAULT_VLM_TIMEOUT) -> Optional[Dict[str, Any]]:
    """
    Get consolidated VLM analysis: culling + naming + critique in ONE call.
    
    Uses MiniCPM-V 2.6 which returns perfect structured JSON.
    
    Args:
        image_path: Path to image file
        model_name: Ollama model name
        ollama_url: Ollama API endpoint
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with three sections:
        - technical: {is_keeper, is_dud, dud_reason, technical_notes}
        - naming: {suggested_filename, subject, location_type, time_of_day}
        - critique: {overall_score, composition, lighting, technical_quality, strengths, improvements, mood}
    """
    base64_image = encode_image_for_vlm(image_path)
    if not base64_image:
        return None
    
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": VLM_CONSOLIDATED_PROMPT,
                "images": [base64_image]
            }
        ],
        "stream": False,
        "format": "json"  # Force JSON output
    }
    
    try:
        response = requests.post(ollama_url, json=payload, timeout=timeout)
        response.raise_for_status()
        
        result = response.json()
        json_string = result['message']['content'].strip()
        
        # Parse JSON response
        analysis = json.loads(json_string)
        
        # Validate structure (basic check)
        required_keys = {'technical', 'naming', 'critique'}
        if not required_keys.issubset(analysis.keys()):
            return None
        
        return analysis
        
    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.RequestException:
        return None
    except json.JSONDecodeError:
        return None
    except Exception:
        return None

# ==============================================================================
# VIII. TWO-STAGE CASCADE
# ==============================================================================

def assess_image_quality(image_path: Path,
                        use_brisque: bool = True,
                        use_vlm: bool = True,
                        force_vlm: bool = False,
                        vlm_model: str = DEFAULT_VLM_MODEL,
                        ollama_url: str = DEFAULT_OLLAMA_URL) -> Dict[str, Any]:
    """
    Two-stage quality assessment cascade.
    
    Stage 1: Fast BRISQUE screening
    - keeper → skip VLM, mark as keep
    - ambiguous → send to VLM
    - dud → send to VLM for confirmation
    
    Stage 2: VLM analysis (only for ambiguous/dud cases)
    - Full analysis with culling decision + naming + critique
    
    Args:
        image_path: Path to image file
        use_brisque: Use BRISQUE for stage 1 (falls back to Laplacian if unavailable)
        use_vlm: Use VLM for stage 2
        force_vlm: Force VLM analysis even if BRISQUE says keeper
        vlm_model: VLM model name
        ollama_url: Ollama API URL
        
    Returns:
        Dictionary with:
        - stage1_result: BRISQUE/Laplacian result
        - stage2_result: VLM result (if applicable)
        - final_verdict: 'keeper' | 'dud'
        - needs_review: bool (for ambiguous cases)
        - naming: filename suggestion (if available)
        - critique: critique data (if available)
    """
    result = {
        'stage1_result': None,
        'stage2_result': None,
        'final_verdict': 'keeper',  # Default to keeper
        'needs_review': False,
        'naming': None,
        'critique': None,
        'error': None
    }
    
    # Stage 1: Fast screening
    if use_brisque and BRISQUE_AVAILABLE:
        stage1 = assess_with_brisque(image_path)
    elif CV2_AVAILABLE:
        stage1 = assess_with_laplacian_patch(image_path)
    else:
        result['error'] = 'No quality assessment method available'
        return result
    
    if stage1 is None:
        result['error'] = 'Stage 1 assessment failed'
        return result
    
    result['stage1_result'] = stage1
    
    # Determine if VLM is needed
    needs_vlm = force_vlm or (stage1['verdict'] in ['ambiguous', 'dud'])
    
    if needs_vlm and use_vlm:
        # Stage 2: VLM analysis
        stage2 = get_vlm_analysis(image_path, vlm_model, ollama_url)
        
        if stage2:
            result['stage2_result'] = stage2
            
            # Extract data from VLM response
            technical = stage2.get('technical', {})
            result['final_verdict'] = 'dud' if technical.get('is_dud', False) else 'keeper'
            result['needs_review'] = not technical.get('is_keeper', True) and not technical.get('is_dud', False)
            
            # Store naming and critique
            result['naming'] = stage2.get('naming')
            result['critique'] = stage2.get('critique')
        else:
            # VLM failed, fall back to stage 1 verdict
            result['final_verdict'] = 'keeper' if stage1['verdict'] == 'keeper' else 'dud'
            result['needs_review'] = stage1['verdict'] == 'ambiguous'
    else:
        # No VLM needed, use stage 1 verdict
        result['final_verdict'] = 'keeper' if stage1['verdict'] == 'keeper' else 'dud'
        result['needs_review'] = stage1['verdict'] == 'ambiguous'
    
    return result

# ==============================================================================
# IX. BATCH PROCESSING
# ==============================================================================

def assess_images_batch(image_paths: list[Path],
                       use_brisque: bool = True,
                       use_vlm: bool = True,
                       force_vlm_for_keepers: bool = False,
                       vlm_model: str = DEFAULT_VLM_MODEL,
                       progress_callback=None) -> Dict[Path, Dict[str, Any]]:
    """
    Assess multiple images with the two-stage cascade.
    
    Args:
        image_paths: List of image paths
        use_brisque: Use BRISQUE for stage 1
        use_vlm: Use VLM for stage 2
        force_vlm_for_keepers: Force VLM even for definite keepers
        vlm_model: VLM model name
        progress_callback: Optional callback(current, total, stage)
        
    Returns:
        Dictionary mapping Path -> assessment result
    """
    results = {}
    
    for i, image_path in enumerate(image_paths):
        result = assess_image_quality(
            image_path,
            use_brisque=use_brisque,
            use_vlm=use_vlm,
            force_vlm=force_vlm_for_keepers,
            vlm_model=vlm_model
        )
        
        results[image_path] = result
        
        if progress_callback:
            progress_callback(i + 1, len(image_paths), result)
    
    return results

# ==============================================================================
# X. HIGH-LEVEL API
# ==============================================================================

def check_dependencies() -> Dict[str, bool]:
    """
    Check if required dependencies are available.
    
    Returns:
        Dictionary of dependency status
    """
    return {
        'brisque_available': BRISQUE_AVAILABLE,
        'laplacian_available': CV2_AVAILABLE,
        'pil_available': PIL_AVAILABLE,
        'any_method_available': BRISQUE_AVAILABLE or CV2_AVAILABLE
    }

def get_recommended_thresholds() -> Dict[str, float]:
    """
    Get recommended BRISQUE thresholds (can be calibrated per-camera).
    
    Returns:
        Dictionary with threshold values
    """
    return {
        'keeper_threshold': DEFAULT_BRISQUE_KEEPER_THRESHOLD,
        'ambiguous_threshold': DEFAULT_BRISQUE_AMBIGUOUS_THRESHOLD,
        'laplacian_threshold': DEFAULT_LAPLACIAN_THRESHOLD
    }

# ==============================================================================
# XI. TESTING & DEBUG
# ==============================================================================

if __name__ == "__main__":
    """Basic test of cull engine functionality."""
    
    print("=" * 60)
    print("PhotoSort v8.0 - Cull Engine Test")
    print("=" * 60)
    
    # Check dependencies
    deps = check_dependencies()
    print("\n📦 Dependencies:")
    print(f"  BRISQUE (image-quality): {'✓' if deps['brisque_available'] else '✗'}")
    print(f"  Laplacian (OpenCV): {'✓' if deps['laplacian_available'] else '✗'}")
    print(f"  PIL (Pillow): {'✓' if deps['pil_available'] else '✗'}")
    
    if not deps['any_method_available']:
        print("\n⚠️  No quality assessment method available. Install with:")
        print("  pip install image-quality opencv-python Pillow")
        exit(1)
    
    # Show thresholds
    print("\n⚙️  Recommended Thresholds:")
    thresholds = get_recommended_thresholds()
    for key, value in thresholds.items():
        print(f"  {key}: {value}")
    
    print("\n✓ Cull engine module loaded successfully!")
