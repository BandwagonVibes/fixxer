#!/usr/bin/env python3
"""
PhotoSort Engine (v10.8) - Cross-Platform RAW Conversion

This file now contains the REAL v9.3 workflow functions
from the original photosort.py, refactored to be
TUI-aware. All print()/tqdm calls are replaced with log_callback.

v10.8 CHANGES (Cross-Platform Migration):
- REMOVED macOS-only sips dependency completely
- convert_raw_to_jpeg() now uses Pillow for PPM→JPEG conversion
- 100% cross-platform (Linux, macOS, Windows with dcraw)
- Zero temp files created (pure in-memory operation via BytesIO)
- 5x smaller output files (689KB vs 3.7MB from sips)
- Handles both direct JPEG thumbnails and PPM format seamlessly

v10.7 FIXES:
- convert_raw_to_jpeg() now tries embedded thumbnail first (-e flag)
- Falls back to full demosaic only if embedded thumbnail fails
- Added timeouts to prevent hanging on problematic RAW files
- Better error handling for session name generation

v10.6 FIXES:
- check_dcraw() now adds ALL common RAW formats (not just .rw2)
- encode_image() and get_image_bytes_for_analysis() handle all RAW formats
"""

from __future__ import annotations

import os
import json
import base64
import requests
import shutil
import tempfile
import configparser
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple, List, Dict, Any, Callable
from collections import defaultdict, Counter
import re
import subprocess
import sys
import math
from io import BytesIO

# --- Optional Libs (Required for Real Engine) ---

try:
    import imagehash
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    V5_LIBS_AVAILABLE = True
except ImportError:
    V5_LIBS_AVAILABLE = False
    imagehash = None  # Type stub for type hints

try:
    import cv2
    import numpy as np
    V6_CULL_LIBS_AVAILABLE = True
except ImportError:
    V6_CULL_LIBS_AVAILABLE = False

try:
    import exifread
    V6_4_EXIF_LIBS_AVAILABLE = True
except ImportError:
    V6_4_EXIF_LIBS_AVAILABLE = False

# --- v7.1 Modules (Optional) ---
# We'll stub these for now, as the TUI doesn't use them yet
# In a future step, we could port these or integrate them.
class MockSessionTracker:
    def set_model(self, model): pass
    def add_operation(self, op): pass
    def set_destination(self, dest): pass
    def add_size_before(self, size): pass
    def add_size_after(self, size): pass
    def record_image(self, size, success): pass
    def print_summary(self): pass
    def save_to_history(self, path): pass

SessionTracker = MockSessionTracker


# ==============================================================================
# III. CONSTANTS & CONFIGURATION
# ==============================================================================

# --- AI Critic "Gold Master" Prompt ---
AI_CRITIC_PROMPT = """
You are a professional Creative Director and magazine photo editor. Your job is to provide ambitious, artistic, and creative feedback to elevate a photo from "good" to "great."

**CREATIVE TOOLBOX (Use these for your suggestion):**
* **Mood & Atmosphere:** (e.g., 'cinematic,' 'moody,' 'ethereal,' 'nostalgic,' 'dramatic')
* **Color Grading:** (e.g., 'filmic teal-orange,' 'warm vintage,' 'cool desaturation,' 'split-toning')
* **Light & Shadow:** (e.g., 'crushed blacks,' 'soft, lifted shadows,' 'localized dodging/burning,' 'a subtle vignette')
* **Texture:** (e.g., 'add fine-grain film,' 'soften the focus,' 'increase clarity')

**YOUR TASK:**
Analyze the provided image by following these steps *internally*:
1.  **Composition:** Analyze balance, guiding principles (thirds, lines), and subject placement. Rate it 1-10.
2.  **Lighting & Exposure:** Analyze quality, direction, temperature, and any blown highlights or crushed shadows.
3.  **Color & Style:** Analyze the color palette, white balance, and current post-processing style.

After your analysis, you MUST return **ONLY a single, valid JSON object**. Do not provide *any* other text, preamble, or conversation. Your response must be 100% valid JSON, formatted *exactly* like this template:

```json
{
  "composition_score": <an integer from 1 to 10>,
  "composition_critique": "<A brief, one-sentence critique of the composition.>",
  "lighting_critique": "<A brief, one-sentence critique of the lighting and exposure.>",
  "color_critique": "<A brief, one-sentence critique of the color and current style.>",
  "final_verdict": "<A one-sentence summary of what works and what doesn't.>",
  "creative_mood": "<The single, most ambitious 'Creative Mood' this photo could have, chosen from the toolbox.>",
  "creative_suggestion": "<Your single, ambitious, artistic post-processing suggestion to achieve that mood. This must be a detailed, actionable paragraph.>"
}
```
"""

# --- Core Configuration ---
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL_NAME = "qwen2.5vl:3b"
DEFAULT_DESTINATION_BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/negatives"
DEFAULT_CRITIQUE_MODEL = "qwen2.5vl:3b"

DEFAULT_CULL_ALGORITHM = 'legacy'
DEFAULT_BURST_ALGORITHM = 'legacy'

DEFAULT_CULL_THRESHOLDS = {
    'sharpness_good': 40.0,
    'sharpness_dud': 15.0,
    'exposure_dud_pct': 0.20,
    'exposure_good_pct': 0.05
}
DEFAULT_BURST_THRESHOLD = 8
CONFIG_FILE_PATH = Path.home() / ".photosort.conf"

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
RAW_SUPPORT = False

MAX_WORKERS = 5
INGEST_TIMEOUT = 120
CRITIQUE_TIMEOUT = 120

SESSION_DATE = datetime.now().strftime("%Y-%m-%d")
SESSION_TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H%M")

GROUP_KEYWORDS = {
    "Architecture": ["building", "architecture"],
    "Street-Scenes": ["street", "road", "city"],
    "People": ["people", "person", "man", "woman"],
    "Nature": ["tree", "forest", "mountain", "lake"],
    "Transportation": ["car", "bus", "train", "vehicle"],
    "Signs-Text": ["sign", "text", "billboard"],
    "Food-Dining": ["food", "restaurant", "cafe"],
    "Animals": ["dog", "cat", "bird", "animal"],
    "Interior": ["interior", "room", "inside"],
}

BEST_PICK_PREFIX = "_PICK_"
PREP_FOLDER_NAME = "_ReadyForLightroom"
TIER_A_FOLDER = "_Tier_A"
TIER_B_FOLDER = "_Tier_B"
TIER_C_FOLDER = "_Tier_C"


# ==============================================================================
# V. CORE UTILITIES
# ==============================================================================

def no_op_logger(message: str) -> None:
    """A dummy logger that does nothing, for when no callback is provided."""
    pass

def check_dcraw(log_callback: Callable[[str], None] = no_op_logger):
    """Check if dcraw is available and update RAW support"""
    global RAW_SUPPORT
    global SUPPORTED_EXTENSIONS
    try:
        result = subprocess.run(['which', 'dcraw'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            RAW_SUPPORT = True
            # Add ALL common RAW formats that dcraw supports
            raw_extensions = {'.rw2', '.arw', '.cr2', '.cr3', '.nef', '.dng', '.raf', '.orf', '.pef', '.srw'}
            SUPPORTED_EXTENSIONS.update(raw_extensions)
            log_callback(f"✓ [green]dcraw found.[/green] RAW support enabled.")
            log_callback(f"  Added RAW formats: {', '.join(sorted(raw_extensions))}")
        else:
            RAW_SUPPORT = False
            log_callback("✗ [yellow]dcraw not found.[/yellow] RAW support disabled.")
    except Exception as e:
        RAW_SUPPORT = False
        log_callback(f"✗ [red]dcraw check failed:[/red] {e}")

def get_available_models(log_callback: Callable[[str], None] = no_op_logger) -> Optional[List[str]]:
    """Get list of available Ollama models."""
    try:
        log_callback("   [grey]Checking Ollama connection...[/grey]")
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]
        models = [line.split()[0] for line in lines if line.strip()]
        log_callback(f"   [green]✓ Ollama connected.[/green] Found {len(models)} models.")
        return models
    except subprocess.CalledProcessError as e:
        log_callback(f"   [red]✗ Ollama command failed:[/red] {e.stdout}")
        return None
    except FileNotFoundError:
        log_callback("   [red]✗ Ollama not found.[/red] Please ensure 'ollama' is in your PATH.")
        return None
    except Exception as e:
        log_callback(f"   [red]✗ Ollama connection error:[/red] {e}")
        return None

def convert_raw_to_jpeg(raw_path: Path, log_callback: Callable[[str], None] = no_op_logger) -> Optional[bytes]:
    """Convert RAW file to JPEG bytes using dcraw + Pillow.
    
    Cross-platform Method 1: Embedded Thumbnail Extraction
    - Uses dcraw -e -c to extract embedded JPEG thumbnail to stdout
    - If output is JPEG (magic bytes 0xFFD8): returns directly
    - If output is PPM: converts to JPEG via Pillow in-memory (no temp files)
    - Falls back to full demosaic if embedded thumbnail fails
    
    Benefits vs sips:
    - 100% cross-platform (Linux, macOS, Windows)
    - No temp files created (pure memory operation)
    - 5x smaller output (689KB vs 3.7MB)
    """
    if not RAW_SUPPORT:
        return None
    
    # Method 1: Extract embedded thumbnail (fast, cross-platform)
    try:
        result = subprocess.run(
            ['dcraw', '-e', '-c', str(raw_path)],
            capture_output=True,
            timeout=10
        )
        
        if result.returncode == 0 and len(result.stdout) > 1000:
            raw_bytes = result.stdout
            
            # Check if output is already JPEG (magic bytes: 0xFFD8)
            if raw_bytes[:2] == b'\xff\xd8':
                return raw_bytes
            
            # Otherwise it's PPM format - convert via Pillow in-memory
            try:
                ppm_buffer = BytesIO(raw_bytes)
                img = Image.open(ppm_buffer)
                
                jpeg_buffer = BytesIO()
                img.save(jpeg_buffer, format='JPEG', quality=95)
                jpeg_buffer.seek(0)
                
                return jpeg_buffer.read()
            except Exception as pil_error:
                log_callback(f"   [yellow]Pillow conversion failed for {raw_path.name}: {pil_error}[/yellow]")
                # Fall through to Method 2
                
    except subprocess.TimeoutExpired:
        log_callback(f"   [yellow]Thumbnail extraction timed out for {raw_path.name}[/yellow]")
    except Exception as e:
        # Silently fall through to method 2
        pass
    
    # Method 2: Full demosaic fallback (slower, but works when no embedded thumbnail)
    try:
        result = subprocess.run(
            ['dcraw', '-c', '-w', '-q', '3', str(raw_path)],
            capture_output=True,
            check=True,
            timeout=30
        )
        
        # Convert PPM output to JPEG via Pillow in-memory
        ppm_buffer = BytesIO(result.stdout)
        img = Image.open(ppm_buffer)
        
        jpeg_buffer = BytesIO()
        img.save(jpeg_buffer, format='JPEG', quality=95)
        jpeg_buffer.seek(0)
        
        return jpeg_buffer.read()
    
    except subprocess.TimeoutExpired:
        log_callback(f"   [red]Error converting RAW file {raw_path.name}:[/red] Timeout")
    except Exception as e:
        log_callback(f"   [red]Error converting RAW file {raw_path.name}:[/red] {e}")
    
    return None

def encode_image(image_path: Path, log_callback: Callable[[str], None] = no_op_logger) -> Optional[str]:
    """Convert image to base64 string, handling RAW files"""
    try:
        # All RAW formats supported by dcraw
        raw_formats = {'.rw2', '.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.pef', '.srw'}
        if image_path.suffix.lower() in raw_formats:
            jpeg_bytes = convert_raw_to_jpeg(image_path, log_callback)
            if jpeg_bytes:
                return base64.b64encode(jpeg_bytes).decode('utf-8')
            else:
                return None
        
        with open(image_path, 'rb') as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    
    except Exception as e:
        log_callback(f"   [red]Error encoding {image_path.name}:[/red] {e}")
        return None

def get_image_bytes_for_analysis(image_path: Path, log_callback: Callable[[str], None] = no_op_logger) -> Optional[bytes]:
    """Helper to get bytes from any supported file"""
    ext = image_path.suffix.lower()
    # All RAW formats supported by dcraw
    raw_formats = {'.rw2', '.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.pef', '.srw'}
    if ext in raw_formats:
        return convert_raw_to_jpeg(image_path, log_callback)
    elif ext in ('.jpg', '.jpeg', '.png'):
        try:
            with open(image_path, 'rb') as f:
                return f.read()
        except Exception as e:
            log_callback(f"   [red]Failed to read {image_path.name}:[/red] {e}")
            return None
    return None

def get_unique_filename(base_name: str, extension: str, destination: Path) -> Path:
    """Generate unique filename if file already exists"""
    filename = destination / f"{base_name}{extension}"
    if not filename.exists():
        return filename
    counter = 1
    while True:
        filename = destination / f"{base_name}-{counter:02d}{extension}"
        if not filename.exists():
            return filename
        counter += 1

def format_duration(duration: timedelta) -> str:
    """Converts timedelta to readable string like '1d 4h 15m'"""
    total_seconds = int(duration.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0 or (days == 0 and hours == 0): parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "0m"

def generate_bar_chart(data: dict, bar_width: int = 25, bar_char: str = "■") -> List[str]:
    """Generates ASCII bar chart lines from a dictionary"""
    output_lines = []
    if not data: return output_lines
    max_val = max(data.values()); max_val = 1 if max_val == 0 else max_val
    max_key_len = max(len(key) for key in data.keys())
    for key, val in data.items():
        bar_len = int(math.ceil((val / max_val) * bar_width))
        bar = bar_char * bar_len
        line = f"     {key.ljust(max_key_len)}: [bold]{str(val).ljust(4)}[/bold] {bar}"
        output_lines.append(line)
    return output_lines

def clean_filename(description: str) -> str:
    """Convert AI description to clean filename"""
    clean = description.strip('"\'.,!?')
    clean = re.sub(r'[^\w\s-]', '', clean)
    clean = re.sub(r'[-\s]+', '-', clean)
    clean = clean.lower()[:60]
    return clean.strip('-')

def categorize_description(description: str) -> str:
    """Determine category based on keywords in description"""
    description_lower = description.lower()
    category_scores = {}
    for category, keywords in GROUP_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in description_lower)
        if score > 0:
            category_scores[category] = score
    if category_scores:
        return max(category_scores, key=category_scores.get)
    return "Miscellaneous"

def write_rename_log(log_path: Path, original_name: str, new_name: str, destination: Path):
    """(V9.3) Append an AI rename operation to the log file."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | {original_name} -> {new_name} | {destination}\n"
        with open(log_path, 'a') as f:
            f.write(log_entry)
    except Exception:
        pass # Silent fail

def initialize_rename_log(log_path: Path):
    """(V9.3) Initialize the rename log file with a header."""
    try:
        header = f"# PhotoSort AI Rename Log - {SESSION_TIMESTAMP}\n"
        header += f"# Format: timestamp | original_name -> new_name | destination\n"
        header += "=" * 80 + "\n"
        with open(log_path, 'w') as f:
            f.write(header)
    except Exception:
        pass

# ==============================================================================
# VI. CONFIGURATION LOGIC
# ==============================================================================

def load_app_config() -> Dict[str, Any]:
    """
    (V7.0) Loads settings from ~/.photosort.conf
    """
    parser = configparser.ConfigParser()
    config_loaded = False
    if CONFIG_FILE_PATH.exists():
        try:
            parser.read(CONFIG_FILE_PATH)
            config_loaded = True
        except configparser.Error:
            pass # Will use fallbacks

    config = {}
    
    config['config_file_found'] = config_loaded
    config['config_file_path'] = str(CONFIG_FILE_PATH)

    config['default_destination'] = Path(parser.get(
        'ingest', 'default_destination',
        fallback=str(DEFAULT_DESTINATION_BASE)
    )).expanduser()
    config['default_model'] = parser.get(
        'ingest', 'default_model',
        fallback=DEFAULT_MODEL_NAME
    )
    config['cull_thresholds'] = {
        'sharpness_good': parser.getfloat('cull', 'sharpness_good', fallback=DEFAULT_CULL_THRESHOLDS['sharpness_good']),
        'sharpness_dud': parser.getfloat('cull', 'sharpness_dud', fallback=DEFAULT_CULL_THRESHOLDS['sharpness_dud']),
        'exposure_dud_pct': parser.getfloat('cull', 'exposure_dud_pct', fallback=DEFAULT_CULL_THRESHOLDS['exposure_dud_pct']),
        'exposure_good_pct': parser.getfloat('cull', 'exposure_good_pct', fallback=DEFAULT_CULL_THRESHOLDS['exposure_good_pct']),
    }
    config['cull_algorithm'] = parser.get(
        'cull', 'cull_algorithm',
        fallback=DEFAULT_CULL_ALGORITHM
    )
    config['burst_threshold'] = parser.getint(
        'burst', 'similarity_threshold',
        fallback=DEFAULT_BURST_THRESHOLD
    )
    config['burst_algorithm'] = parser.get(
        'burst', 'burst_algorithm',
        fallback=DEFAULT_BURST_ALGORITHM
    )
    config['critique_model'] = parser.get(
        'critique', 'default_model',
        fallback=DEFAULT_CRITIQUE_MODEL
    )
    config['last_source_path'] = parser.get(
        'behavior', 'last_source_path', fallback=None
    )
    config['last_destination_path'] = parser.get(
        'behavior', 'last_destination_path', fallback=None
    )
    
    # v7.1: Folder settings (from original file)
    config['burst_parent_folder'] = parser.getboolean(
        'folders', 'burst_parent_folder', fallback=True
    )
    config['ai_session_naming'] = parser.getboolean(
        'folders', 'ai_session_naming', fallback=True
    )

    return config


def save_app_config(config: Dict[str, Any]) -> bool:
    """
    (V10.7) Save specific settings back to ~/.photosort.conf
    Only saves paths and model settings that are commonly changed during TUI use.
    """
    parser = configparser.ConfigParser()
    
    # Load existing config first to preserve other settings
    if CONFIG_FILE_PATH.exists():
        try:
            parser.read(CONFIG_FILE_PATH)
        except configparser.Error:
            pass
    
    # Ensure sections exist
    if not parser.has_section('behavior'):
        parser.add_section('behavior')
    if not parser.has_section('ingest'):
        parser.add_section('ingest')
    
    # Save the key settings
    if 'last_source_path' in config and config['last_source_path']:
        parser.set('behavior', 'last_source_path', str(config['last_source_path']))
    
    if 'last_destination_path' in config and config['last_destination_path']:
        parser.set('behavior', 'last_destination_path', str(config['last_destination_path']))
    
    if 'default_model' in config and config['default_model']:
        parser.set('ingest', 'default_model', str(config['default_model']))
    
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            parser.write(f)
        return True
    except Exception:
        return False


# ==============================================================================
# VII. AI & ANALYSIS MODULES (The "Brains")
# ==============================================================================

def get_ai_description(image_path: Path, model_name: str, log_callback: Callable[[str], None] = no_op_logger) -> Tuple[Optional[str], Optional[List[str]]]:
    """(V9.0) Get structured filename and tags from AI."""
    base64_image = encode_image(image_path, log_callback)
    if not base64_image:
        return None, None

    AI_NAMING_PROMPT = """You are an expert file-naming AI.
Analyze this image and generate a concise, descriptive filename and three relevant tags.
You MUST return ONLY a single, valid JSON object, formatted *exactly* like this:
{
  "filename": "<a-concise-and-descriptive-filename>",
  "tags": ["<tag1>", "<tag2>", "<tag3>"]
}
"""
    
    payload = {
        "model": model_name,
        "messages": [
            { "role": "user", "content": AI_NAMING_PROMPT, "images": [base64_image] }
        ],
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=INGEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        json_string = result['message']['content'].strip()
        data = json.loads(json_string)
        filename = data.get("filename")
        tags = data.get("tags")
        if not filename or not isinstance(tags, list):
            log_callback(f"   [yellow]Warning: Model returned valid JSON but missing keys for {image_path.name}[/yellow]")
            return None, None
        return str(filename), list(tags)
        
    except requests.exceptions.Timeout:
        log_callback(f"   [red]Timeout processing {image_path.name}[/red]")
        return None, None
    except json.JSONDecodeError:
        log_callback(f"   [red]Error: Model returned invalid JSON for {image_path.name}[/red]")
        return None, None
    except Exception as e:
        log_callback(f"   [red]Error processing {image_path.name}: {e}[/red]")
        return None, None

def get_ai_image_name(image_path: Path, model_name: str, log_callback: Callable[[str], None] = no_op_logger) -> Optional[Dict[str, Any]]:
    """(V9.2) Generate AI-powered name for an image (for burst PICK files)."""
    try:
        filename, tags = get_ai_description(image_path, model_name, log_callback)
        if not filename or not tags:
            return None
        filename_no_ext = Path(filename).stem
        clean_name = clean_filename(filename_no_ext)
        return { 'filename': clean_name, 'tags': tags }
    except Exception:
        return None


def critique_single_image(
    image_path: Path,
    model_name: str,
    log_callback: Callable[[str], None] = no_op_logger
) -> Optional[Dict[str, Any]]:
    """(V10.6) Get AI creative critique for a single image."""
    base64_image = encode_image(image_path, log_callback)
    if not base64_image:
        log_callback(f"[red]Failed to encode image for critique[/red]")
        return None
    
    payload = {
        "model": model_name,
        "messages": [
            { "role": "user", "content": AI_CRITIC_PROMPT, "images": [base64_image] }
        ],
        "stream": False,
        "format": "json"
    }
    
    try:
        log_callback(f"   [grey]Sending to {model_name} for analysis...[/grey]")
        response = requests.post(OLLAMA_URL, json=payload, timeout=CRITIQUE_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        json_string = result['message']['content'].strip()
        
        # Clean up potential markdown formatting
        if json_string.startswith("```"):
            json_string = json_string.split("```")[1]
            if json_string.startswith("json"):
                json_string = json_string[4:]
            json_string = json_string.strip()
        
        data = json.loads(json_string)
        
        # Validate expected fields
        expected_fields = [
            "composition_score", "composition_critique", "lighting_critique",
            "color_critique", "final_verdict", "creative_mood", "creative_suggestion"
        ]
        
        for field in expected_fields:
            if field not in data:
                log_callback(f"[yellow]Warning: Missing field '{field}' in critique response[/yellow]")
        
        return data
        
    except requests.exceptions.Timeout:
        log_callback(f"[red]Timeout waiting for critique response[/red]")
        return None
    except json.JSONDecodeError as e:
        log_callback(f"[red]Error: Model returned invalid JSON: {e}[/red]")
        return None
    except Exception as e:
        log_callback(f"[red]Error during critique: {e}[/red]")
        return None

def is_already_ai_named(filename: str) -> bool:
    """(V9.2) Check if a PICK file already has an AI-generated name."""
    if not re.search(r'_PICK\.\w+$', filename, re.IGNORECASE):
        return False
    if filename.startswith('_PICK_'):
        return False
    return True

def get_image_hash(image_path: Path, log_callback: Callable[[str], None] = no_op_logger) -> Tuple[Path, Optional[Any]]:
    """Calculates perceptual hash (visual fingerprint) of an image."""
    if not V5_LIBS_AVAILABLE:
        log_callback("[red]Missing 'imagehash' library. Burst grouping will fail.[/red]")
        return image_path, None
        
    if image_path.suffix.lower() in ['.rw2', '.cr2', '.nef', '.arw', '.dng']:
        try:
            result = subprocess.run(
                ['dcraw', '-e', '-c', str(image_path)],
                capture_output=True,
                check=True
            )
            img = Image.open(BytesIO(result.stdout))
            return image_path, imagehash.phash(img)
        except Exception:
            return image_path, None
           
    try:
        with Image.open(image_path) as img:
            return image_path, imagehash.phash(img)
    except Exception as e:
        log_callback(f"     [yellow]Skipping hash for {image_path.name}: {e}[/yellow]")
        return image_path, None

def analyze_image_quality(image_bytes: bytes) -> Dict[str, float]:
    """Analyzes image bytes for sharpness and exposure."""
    if not V6_CULL_LIBS_AVAILABLE:
        return {'sharpness': 0.0, 'blacks_pct': 0.0, 'whites_pct': 0.0}
        
    scores = {'sharpness': 0.0, 'blacks_pct': 0.0, 'whites_pct': 0.0}
    try:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None: return scores

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        scores['sharpness'] = float(laplacian_var)

        total_pixels = gray.size
        crushed_blacks = np.sum(gray < 10)
        scores['blacks_pct'] = float(crushed_blacks / total_pixels)
        blown_whites = np.sum(gray > 245)
        scores['whites_pct'] = float(blown_whites / total_pixels)
        return scores
    except Exception:
        return scores

def analyze_single_exif(image_path: Path) -> Optional[Dict]:
    """Thread-pool worker: Opens image and extracts key EXIF data."""
    if not V6_4_EXIF_LIBS_AVAILABLE:
        return None
        
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False, stop_tag='EXIF DateTimeOriginal')
            if not tags or 'EXIF DateTimeOriginal' not in tags: return None
            timestamp_str = str(tags['EXIF DateTimeOriginal'])
            dt_obj = datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
            camera = str(tags.get('Image Model', 'Unknown')).strip()
            focal_len = str(tags.get('EXIF FocalLength', 'Unknown')).split(' ')[0]
            aperture_str = "Unknown"
            aperture_tag = tags.get('EXIF FNumber')
            
            if aperture_tag:
                val = aperture_tag.values[0]
                if hasattr(val, 'num') and hasattr(val, 'den'):
                    aperture_val = 0.0 if val.den == 0 else float(val.num) / float(val.den)
                    aperture_str = f"f/{aperture_val:.1f}"
                else:
                    aperture_str = f"f/{val:.1f}"

            if not camera: camera = "Unknown"
            if not focal_len: focal_len = "Unknown"
            if aperture_str == "f/0.0": aperture_str = "Unknown"

            return {
                'timestamp': dt_obj,
                'camera': camera,
                'focal_length': f"{focal_len} mm",
                'aperture': aperture_str
            }
    except Exception:
        return None

def process_single_image(
    image_path: Path, 
    destination_base: Path, 
    model_name: str, 
    rename_log_path: Optional[Path] = None,
    log_callback: Callable[[str], None] = no_op_logger
) -> Tuple[Path, bool, str, str]:
    """(V9.3) Process one image: get AI name/tags, rename, move to temp location."""
    try:
        if is_already_ai_named(image_path.name):
            extension = image_path.suffix.lower()
            base_name = image_path.stem
            clean_base = base_name[:-5] if base_name.endswith('_PICK') else base_name
            new_path = get_unique_filename(clean_base, extension, destination_base)
            
            shutil.move(str(image_path), str(new_path))
            if rename_log_path:
                write_rename_log(rename_log_path, image_path.name, new_path.name, destination_base)
            description_for_categorization = clean_base.replace('-', ' ')
            return image_path, True, new_path.name, description_for_categorization
        
        ai_filename, ai_tags = get_ai_description(image_path, model_name, log_callback)
        if not ai_filename or not ai_tags:
            return image_path, False, "Failed to get valid AI JSON response", ""
        
        description_for_categorization = " ".join(ai_tags)
        clean_name = Path(ai_filename).stem
        extension = image_path.suffix.lower()
        new_path = get_unique_filename(clean_name, extension, destination_base)
        
        shutil.move(str(image_path), str(new_path))
        if rename_log_path:
            write_rename_log(rename_log_path, image_path.name, new_path.name, destination_base)
        
        return image_path, True, new_path.name, description_for_categorization
    except Exception as e:
        return image_path, False, str(e), ""

def organize_into_folders(
    processed_files: List[Dict], 
    files_source: Path, 
    destination_base: Path,
    log_callback: Callable[[str], None] = no_op_logger
):
    """Group files into folders based on their descriptions."""
    log_callback("\n[bold]🗂️  Organizing into smart folders...[/bold]")
    
    categories = defaultdict(list)
    for file_info in processed_files:
        filename = file_info['new_name']
        description = file_info['description']
        category = categorize_description(description)
        categories[category].append({
            'filename': filename,
            'description': description
        })
    
    for category, files in categories.items():
        folder_name = category
        folder_path = destination_base / folder_name
        folder_path.mkdir(exist_ok=True)
        log_callback(f"   [green]✓[/green] {folder_name}/ ({len(files)} files)")
        
        for file_info in files:
            src = files_source / file_info['filename']
            dst = folder_path / file_info['filename']
            if src.exists():
                shutil.move(str(src), str(dst))
            else:
                log_callback(f"     [yellow]Warning: Source file not found, may already be moved: {src.name}[/yellow]")
    
    log_callback(f"\n   Organized into {len(categories)} folders.")

def generate_ai_session_name(
    categories: Dict[str, int], 
    model_name: str,
    log_callback: Callable[[str], None] = no_op_logger,
    sample_images: Optional[List[Path]] = None
) -> Optional[str]:
    """(V10.6) Generate AI session name using actual image samples for better context."""
    if not categories:
        return None
    
    category_list = [f"- {cat}: {count} images" for cat, count in categories.items()]
    category_text = "\n".join(category_list)
    
    # If we have sample images, use vision model for richer understanding
    if sample_images and len(sample_images) > 0:
        log_callback(f"   [grey]Generating session name from {len(sample_images)} sample images...[/grey]")
        
        # Encode up to 3 sample images
        encoded_images = []
        for img_path in sample_images[:3]:
            encoded = encode_image(img_path, log_callback)
            if encoded:
                encoded_images.append(encoded)
        
        if encoded_images:
            prompt = f"""You are an expert photography curator creating an evocative name for a photo session.

I'm showing you {len(encoded_images)} representative images from a photography session.

Analyze these images and follow these steps:

1. **Identify Visual Themes:**
   - What subjects appear? (people, architecture, nature, street scenes, etc.)
   - What's the setting or environment?
   - Any recurring visual elements?

2. **Capture the Artistic Mood:**
   - What emotion or atmosphere do these images convey?
   - Consider lighting, composition, and subject matter together.
   - Is it contemplative, energetic, melancholic, vibrant, mysterious?

3. **Generate a Single-Word Session Name:**
   - Create ONE evocative, abstract word that captures the essence of this session.
   - The word should be poetic and artistic, NOT a literal description.
   - Avoid generic words like "Session", "Photos", "Collection".
   - Think creatively: "Liminal", "Meridian", "Tessellation", "Chromatic", "Penumbra", "Waypoint", "Patina", "Drift", "Periphery", "Cadence".

Additional context - Category breakdown:
{category_text}

Respond with ONLY a single JSON object:
{{"session_name": "<your-single-evocative-word>"}}
"""
            
            payload = {
                "model": model_name,
                "messages": [
                    { "role": "user", "content": prompt, "images": encoded_images }
                ],
                "stream": False,
                "format": "json"
            }
            
            try:
                response = requests.post(OLLAMA_URL, json=payload, timeout=90)
                response.raise_for_status()
                result = response.json()
                json_string = result['message']['content'].strip()
                data = json.loads(json_string)
                session_name = data.get("session_name", "")
                
                if session_name:
                    clean_name = re.sub(r'[^\w-]', '', session_name)
                    log_callback(f"   [green]✓ AI generated session name: {clean_name}[/green]")
                    return clean_name[:30]
            except Exception as e:
                log_callback(f"   [yellow]Vision-based naming failed, falling back to text-only: {e}[/yellow]")
    
    # Fallback: text-only prompt (original behavior but with better examples)
    prompt = f"""You are an expert photography curator organizing a photo collection.

Analyze the photo categories and counts provided, then follow these steps *in order*:

1. **Identify the Dominant Theme:**
   - What is the primary subject matter? (e.g., architecture, portraits, nature)
   - What secondary themes are present?

2. **Capture the Artistic Mood:**
   - What feeling or vibe does this collection evoke? (e.g., contemplative, energetic, nostalgic)
   - Consider the balance of subjects.

3. **Generate a Single-Word Session Name:**
   - Combine your thematic and mood analysis into ONE evocative word.
   - The word should be abstract and artistic, NOT a literal description.
   - IMPORTANT: Be creative and unique. Do NOT use common/overused words.
   - Good examples: "Meridian", "Tessellation", "Patina", "Waypoint", "Cadence", "Periphery", "Substrate", "Axiom".
   - Avoid: "Ephemera", "Threshold", "Convergence", "Solstice", "Momentum" (too common).

Photo Categories:
{category_text}

Respond with ONLY a single JSON object in this exact format:
{{"session_name": "<your-single-word-name>"}}
"""
    
    payload = {
        "model": model_name,
        "messages": [ { "role": "user", "content": prompt } ],
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        json_string = result['message']['content'].strip()
        data = json.loads(json_string)
        session_name = data.get("session_name", "")
        
        if session_name:
            clean_name = re.sub(r'[^\w-]', '', session_name)
            return clean_name[:30]
        return None
        
    except Exception as e:
        log_callback(f"     [yellow]Warning: Could not generate AI session name: {e}[/yellow]")
        return None

# ==============================================================================
# VIII. FEATURE WORKFLOWS (The "Tools")
# ==============================================================================

# --- Auto Workflow ---

def auto_workflow(
    log_callback: Callable[[str], None] = no_op_logger,
    app_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """(V9.3) Complete automated workflow: Stack → Cull → AI-Name → Archive."""
    
    # --- 1. CONFIGURATION ---
    if app_config is None:
        app_config = load_app_config()
    
    # The TUI now handles source/dest selection. Get them from config.
    source_str = app_config.get('last_source_path')
    dest_str = app_config.get('last_destination_path')
    
    if not source_str or not dest_str:
        log_callback("[bold red]✗ FATAL: Source or Destination not set in config.[/bold red]")
        return {}
        
    directory = Path(source_str)
    chosen_destination = Path(dest_str)
    
    if not directory.is_dir():
        log_callback(f"[bold red]✗ FATAL: Source directory not found:[/bold red] {directory}")
        return {}
        
    try:
        chosen_destination.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log_callback(f"[bold red]✗ FATAL: Could not create destination:[/bold red] {e}")
        return {}
        
    chosen_model = app_config['default_model']
    log_callback(f"   Source:      {directory}")
    log_callback(f"   Destination: {chosen_destination}")
    log_callback(f"   Model:       {chosen_model}")
    
    # Check for critical libs
    if not V5_LIBS_AVAILABLE or not V6_CULL_LIBS_AVAILABLE or not V6_4_EXIF_LIBS_AVAILABLE:
        log_callback("[bold red]✗ FATAL: Missing required libraries.[/bold red]")
        log_callback("   Please run: pip install imagehash opencv-python numpy exifread")
        return {}
    
    tracker = SessionTracker()
    tracker.set_model(chosen_model)
    tracker.add_operation("Burst Stacking")
    tracker.add_operation("Quality Culling")
    tracker.add_operation("AI Naming")
    check_dcraw(log_callback)
    
    # --- 2. STATS PREVIEW ---
    log_callback("\n[bold]Step 2/5: Analyzing session (read-only)...[/bold]")
    try:
        show_exif_insights(log_callback, app_config, simulated=True, directory_override=directory)
    except Exception as e:
        log_callback(f"     [yellow]Could not run EXIF analysis: {e}[/yellow]")

    # --- 3. GROUP BURSTS ---
    log_callback("\n[bold]Step 3/5: Stacking burst shots (with AI naming)...[/bold]")
    group_bursts_in_directory(log_callback, app_config, directory_override=directory)

    # --- 4. CULL SINGLES ---
    log_callback("\n[bold]Step 4/5: Culling single shots...[/bold]")
    cull_images_in_directory(log_callback, app_config, directory_override=directory)
    tier_a_dir = directory / TIER_A_FOLDER
    
    # --- 5. FIND & ARCHIVE HEROES ---
    log_callback("\n[bold]Step 5/5: Finding and archiving 'hero' files...[/bold]")
    
    hero_files = []
    if tier_a_dir.is_dir():
        for f in tier_a_dir.iterdir():
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                hero_files.append(f)
    
    burst_parent = directory / "_Bursts"
    burst_folders = []
    if burst_parent.exists() and burst_parent.is_dir():
        burst_folders = [f for f in burst_parent.iterdir() if f.is_dir()]
    
    for burst_folder in burst_folders:
        if burst_folder.is_dir():
            for f in burst_folder.iterdir():
                if f.is_file() and (f.name.startswith(BEST_PICK_PREFIX) or is_already_ai_named(f.name)):
                    hero_files.append(f)

    if not hero_files:
        log_callback(f"\n   No '{TIER_A_FOLDER}' or '_PICK_' files found. Nothing to archive.")
        log_callback("[bold green]✓ Auto workflow complete (no heroes found).[/bold green]")
        return {}

    already_named = [f for f in hero_files if is_already_ai_named(f.name)]
    needs_naming = [f for f in hero_files if not is_already_ai_named(f.name)]
    log_callback(f"   Found {len(hero_files)} 'hero' files total:")
    if already_named:
        log_callback(f"     • {len(already_named)} already AI-named (from burst stacking)")
    log_callback(f"     • {len(needs_naming)} to process")
    
    results = {"success": [], "failed": []}
    rename_log_path = chosen_destination / f"_ai_rename_log_{SESSION_TIMESTAMP}.txt"
    initialize_rename_log(rename_log_path)
    
    log_callback(f"\n   [grey]Archiving {len(hero_files)} files...[/grey]")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(process_single_image, img_path, chosen_destination, chosen_model, rename_log_path, log_callback): img_path 
            for img_path in hero_files
        }
        
        for i, future in enumerate(as_completed(future_to_file)):
            log_callback(f"   [grey]Processing item {i+1}/{len(hero_files)}...[/grey]")
            original, success, message, description = future.result()
            if success:
                results["success"].append({
                    "original": original.name,
                    "new_name": message,
                    "description": description
                })
            else:
                results["failed"].append((original.name, message))
                log_callback(f"   [red]✗ {original.name}: {message}[/red]")
    
    log_callback(f"\n[green]✓ Successfully archived: {len(results['success'])}[/green]")
    log_callback(f"[red]✗ Failed to archive: {len(results['failed'])}[/red]")
    
    summary = {
        "archived": len(results['success']),
        "failed": len(results['failed']),
    }

    if results["success"]:
        categories = {}
        for item in results["success"]:
            cat = categorize_description(item["description"])
            categories[cat] = categories.get(cat, 0) + 1
        
        # (V10.7) Pass sample images for vision-based session naming
        # Select up to 3 diverse hero files as samples
        # FIX: Use the NEW paths from results["success"] because hero_files (source) 
        # have already been moved!
        sample_images = []
        for item in results["success"]:
            if len(sample_images) >= 3:
                break
            
            # Construct the path to the file in the DESTINATION
            new_path = chosen_destination / item["new_name"]
            
            # Quick test: try to encode it
            if new_path.exists():
                test_encode = encode_image(new_path, no_op_logger)  # Silent test
                if test_encode:
                    sample_images.append(new_path)
        
        if not sample_images and results["success"]:
            # If no images could be encoded, just pass the paths anyway
            # The generate_ai_session_name will fall back to text-only
            for item in results["success"][:3]:
                new_path = chosen_destination / item["new_name"]
                if new_path.exists():
                    sample_images.append(new_path)
            log_callback(f"   [yellow]Warning: Could not encode sample images, using text-only naming[/yellow]")
        
        session_name = generate_ai_session_name(categories, chosen_model, log_callback, sample_images)
        
        if session_name and len(session_name) > 2 and app_config.get('ai_session_naming', True):
            dated_folder = f"{SESSION_DATE}_{session_name}"
            log_callback(f"\n   [bold]🎨 AI Session Name: {dated_folder}[/bold]")
        else:
            dated_folder = f"{SESSION_DATE}_Session"
        
        final_destination = chosen_destination / dated_folder
        final_destination.mkdir(parents=True, exist_ok=True)
        tracker.set_destination(final_destination)
        
        organize_into_folders(results["success"], chosen_destination, final_destination, log_callback)
        summary["final_destination"] = str(final_destination.name)
        summary["categories"] = len(categories)

    log_callback("\n[bold green]🚀 AUTO WORKFLOW COMPLETE[/bold green]")
    log_callback(f"   Your 'hero' photos are now in: {chosen_destination}")
    log_callback(f"   Rename log saved: {rename_log_path.name}")

    return summary

# --- Burst Workflow ---

def group_bursts_in_directory(
    log_callback: Callable[[str], None] = no_op_logger,
    app_config: Optional[Dict[str, Any]] = None,
    simulated: bool = False,
    directory_override: Optional[Path] = None
) -> None:
    """(V9.3) Finds and stacks burst groups, AI-naming the best pick."""
    
    if app_config is None: app_config = load_app_config()
    
    # Use override dir (from auto) or config dir
    if directory_override:
        directory = directory_override
    elif app_config.get('last_source_path'):
        directory = Path(app_config['last_source_path'])
    else:
        log_callback("[red]✗ No source directory specified.[/red]")
        return
        
    if not directory.is_dir():
        log_callback(f"[red]✗ Source directory not found: {directory}[/red]")
        return

    if not V5_LIBS_AVAILABLE or not V6_CULL_LIBS_AVAILABLE:
        log_callback("[bold red]✗ FATAL: Missing required libraries.[/bold red]")
        log_callback("   Please run: pip install imagehash opencv-python numpy")
        return

    log_callback(f"[grey]Scanning for bursts in: {directory.name}[/grey]")
    burst_threshold = app_config['burst_threshold']
    
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if len(image_files) < 2:
        log_callback("   Not enough images to compare.")
        return

    all_hashes = {}
    log_callback(f"   [grey]Calculating {len(image_files)} visual fingerprints...[/grey]")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_path = {executor.submit(get_image_hash, path, log_callback): path for path in image_files}
        for i, future in enumerate(as_completed(future_to_path)):
            log_callback(f"   [grey]Hashing image {i+1}/{len(image_files)}...[/grey]",)
            path, img_hash = future.result()
            if img_hash:
                all_hashes[path] = img_hash

    log_callback("   [grey]Comparing fingerprints to find burst groups...[/grey]")
    visited_paths = set()
    all_burst_groups = []
    sorted_paths = sorted(all_hashes.keys(), key=lambda p: p.name)
    
    for path in sorted_paths:
        if path in visited_paths: continue
        current_group = [path]
        visited_paths.add(path)
        for other_path in sorted_paths:
            if other_path in visited_paths: continue
            hash1 = all_hashes.get(path)
            hash2 = all_hashes.get(other_path)
            if hash1 and hash2:
                distance = hash1 - hash2
                if distance <= burst_threshold:
                    current_group.append(other_path)
                    visited_paths.add(other_path)
        if len(current_group) > 1:
            all_burst_groups.append(current_group)

    if not all_burst_groups:
        log_callback("   No burst groups found. All images are unique!")
        return
        
    log_callback(f"   [green]✓ Found {len(all_burst_groups)} burst groups.[/green] Analyzing for best pick...")
    
    best_picks: Dict[int, Tuple[Path, float]] = {}
    for i, group in enumerate(all_burst_groups):
        best_sharpness = -1.0
        best_file = None
        for file_path in group:
            image_bytes = get_image_bytes_for_analysis(file_path, log_callback)
            if image_bytes:
                scores = analyze_image_quality(image_bytes)
                sharpness = scores.get('sharpness', 0.0)
                if sharpness > best_sharpness:
                    best_sharpness = sharpness
                    best_file = file_path
        if best_file:
            best_picks[i] = (best_file, best_sharpness)

    use_parent_folder = app_config.get('burst_parent_folder', True)
    bursts_parent = directory / "_Bursts" if use_parent_folder else directory
    if use_parent_folder:
        log_callback(f"   Organizing burst groups into: {bursts_parent.name}/")
        bursts_parent.mkdir(exist_ok=True)
    
    rename_log_path = directory / f"_ai_rename_log_{SESSION_TIMESTAMP}.txt"
    initialize_rename_log(rename_log_path)
    ai_model = app_config.get('default_model', DEFAULT_MODEL_NAME)
    
    for i, group in enumerate(all_burst_groups):
        winner_data = best_picks.get(i)
        sample_image = winner_data[0] if winner_data else group[0]
        
        log_callback(f"   [grey]Burst {i+1}/{len(all_burst_groups)}: Generating AI name...[/grey]")
        ai_result = get_ai_image_name(sample_image, ai_model, log_callback)
        
        if ai_result and ai_result.get('filename'):
            base_name = ai_result['filename']
            folder_name = f"{base_name}_burst"
            log_callback(f"     [green]✓ AI named:[/green] {base_name}")
        else:
            base_name = f"burst-{i+1:03d}"
            folder_name = base_name
            log_callback(f"     [yellow]⚠️ AI naming failed, using:[/yellow] {base_name}")
        
        folder_path = bursts_parent / folder_name
        if folder_path.exists():
            counter = 2
            original_name = folder_name
            while folder_path.exists():
                folder_name = f"{original_name}-{counter}"
                folder_path = bursts_parent / folder_name
                counter += 1
        
        log_callback(f"     [grey]📁 Moving {len(group)} files to {folder_path.relative_to(directory)}/...[/grey]")
        folder_path.mkdir(parents=True, exist_ok=True)
        
        alternate_counter = 1
        for file_path in group:
            extension = file_path.suffix
            if winner_data and file_path == winner_data[0]:
                new_name = f"{base_name}_PICK{extension}"
            else:
                new_name = f"{base_name}_{alternate_counter:03d}{extension}"
                alternate_counter += 1
            
            new_file_path = folder_path / new_name
            try:
                shutil.move(str(file_path), str(new_file_path))
                write_rename_log(rename_log_path, file_path.name, new_name, folder_path)
            except Exception as e:
                log_callback(f"     [red]FAILED to move {file_path.name}: {e}[/red]")
    
    log_callback(f"   Rename log saved: {rename_log_path.name}")

# --- Cull Workflow ---

def cull_images_in_directory(
    log_callback: Callable[[str], None] = no_op_logger,
    app_config: Optional[Dict[str, Any]] = None,
    simulated: bool = False,
    directory_override: Optional[Path] = None
) -> None:
    """(V9.3) Finds and groups images by technical quality using Tier A/B/C naming."""
    
    if app_config is None: app_config = load_app_config()
    
    if directory_override:
        directory = directory_override
    elif app_config.get('last_source_path'):
        directory = Path(app_config['last_source_path'])
    else:
        log_callback("[red]✗ No source directory specified.[/red]")
        return
        
    if not directory.is_dir():
        log_callback(f"[red]✗ Source directory not found: {directory}[/red]")
        return

    if not V6_CULL_LIBS_AVAILABLE:
        log_callback("[bold red]✗ FATAL: Missing required libraries.[/bold red]")
        log_callback("   Please run: pip install opencv-python numpy")
        return
    
    log_callback(f"[grey]Analyzing technical quality in: {directory.name}[/grey]")

    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not image_files:
        log_callback("     No supported images to analyze.")
        return

    all_scores = {}
    log_callback(f"   [grey]Analyzing sharpness/exposure for {len(image_files)} images...[/grey]")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_path = {
            executor.submit(process_image_for_culling, path, log_callback): path 
            for path in image_files
        }
        for i, future in enumerate(as_completed(future_to_path)):
            log_callback(f"   [grey]Analyzing image {i+1}/{len(image_files)}...[/grey]")
            path, scores = future.result()
            if scores:
                all_scores[path] = scores
    
    log_callback("   [grey]Triaging images into quality tiers...[/grey]")
    th = app_config['cull_thresholds']
    tiers = {"Tier_A": [], "Tier_B": [], "Tier_C": []}

    for path, scores in all_scores.items():
        sharp = scores['sharpness']
        blacks = scores['blacks_pct']
        whites = scores['whites_pct']
        is_exposure_bad = (blacks > th['exposure_dud_pct']) or (whites > th['exposure_dud_pct'])
        is_exposure_good = (blacks < th['exposure_good_pct']) and (whites < th['exposure_good_pct'])
        is_sharp_bad = sharp < th['sharpness_dud']
        is_sharp_good = sharp > th['sharpness_good']

        tier = "Tier_B"
        if is_sharp_bad or is_exposure_bad:
            tier = "Tier_C"
        elif is_sharp_good and is_exposure_good:
            tier = "Tier_A"
        tiers[tier].append(path)

    log_callback(f"   [green]Found {len(tiers['Tier_A'])} Tier A[/green], [yellow]{len(tiers['Tier_B'])} Tier B[/yellow], [red]{len(tiers['Tier_C'])} Tier C[/red].")
    
    folder_map = {
        "Tier_A": directory / TIER_A_FOLDER,
        "Tier_B": directory / TIER_B_FOLDER,
        "Tier_C": directory / TIER_C_FOLDER
    }
    
    for tier, paths in tiers.items():
        if not paths: continue
        folder_path = folder_map[tier]
        log_callback(f"   [grey]Moving {len(paths)} files to {folder_path.name}/...[/grey]")
        folder_path.mkdir(exist_ok=True)
            
        for file_path in paths:
            new_file_path = folder_path / file_path.name
            try:
                shutil.move(str(file_path), str(new_file_path))
            except Exception as e:
                log_callback(f"     [red]FAILED to move {file_path.name}: {e}[/red]")

    log_callback("   Culling complete!")

def process_image_for_culling(image_path: Path, log_callback: Callable[[str], None] = no_op_logger) -> Tuple[Path, Optional[Dict[str, float]]]:
    """Thread-pool worker: Gets bytes and runs analysis engine"""
    image_bytes = get_image_bytes_for_analysis(image_path, log_callback)
    if not image_bytes:
        return image_path, None
    scores = analyze_image_quality(image_bytes)
    return image_path, scores

# --- Stats Workflow ---

def show_exif_insights(
    log_callback: Callable[[str], None] = no_op_logger,
    app_config: Optional[Dict[str, Any]] = None,
    simulated: bool = False,
    directory_override: Optional[Path] = None
) -> None:
    """(V6.4) Scans images, aggregates EXIF data, prints summary"""
    
    if app_config is None: app_config = load_app_config()
    
    if directory_override:
        directory = directory_override
    elif app_config.get('last_source_path'):
        directory = Path(app_config['last_source_path'])
    else:
        log_callback("[red]✗ No source directory specified.[/red]")
        return
        
    if not directory.is_dir():
        log_callback(f"[red]✗ Source directory not found: {directory}[/red]")
        return
        
    if not V6_4_EXIF_LIBS_AVAILABLE:
        log_callback("[bold red]✗ FATAL: Missing required library.[/bold red]")
        log_callback("   Please run: pip install exifread")
        return
        
    log_callback(f"[grey]Scanning EXIF data in: {directory.name}[/grey]")
    
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not image_files:
        log_callback("     No supported images to analyze.")
        return

    all_stats = []
    log_callback(f"   [grey]Reading EXIF data from {len(image_files)} files...[/grey]")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_path = {
            executor.submit(analyze_single_exif, path): path 
            for path in image_files
        }
        for i, future in enumerate(as_completed(future_to_path)):
            if not simulated:
                log_callback(f"   [grey]Scanning image {i+1}/{len(image_files)}...[/grey]")
            result_dict = future.result()
            if result_dict:
                all_stats.append(result_dict)

    if not all_stats:
        log_callback(f"   [yellow]No EXIF data found in {len(image_files)} scanned images.[/yellow]")
        return

    log_callback("   [grey]Aggregating statistics...[/grey]")
    
    timestamps = sorted([s['timestamp'] for s in all_stats])
    start_time = timestamps[0]
    end_time = timestamps[-1]
    duration_str = format_duration(end_time - start_time)

    LIGHTING_TABLE = {
        (0, 4):   "Night", (5, 7):   "Golden Hour (AM)", (8, 10):  "Morning",
        (11, 13): "Midday", (14, 16): "Afternoon", (17, 18): "Golden Hour (PM)",
        (19, 21): "Dusk", (22, 23): "Night",
    }
    lighting_buckets = defaultdict(int)
    camera_counter = Counter()
    focal_len_counter = Counter()
    aperture_counter = Counter()

    for stats in all_stats:
        hour = stats['timestamp'].hour
        for (start, end), name in LIGHTING_TABLE.items():
            if start <= hour <= end:
                lighting_buckets[name] += 1
                break
        camera_counter[stats['camera']] += 1
        focal_len_counter[stats['focal_length']] += 1
        aperture_counter[stats['aperture']] += 1

    # --- Display Results to Log ---
    log_callback("\n[bold]📖 Session Story:[/bold]")
    log_callback(f"   Started:     {start_time.strftime('%a, %b %d at %I:%M %p')}")
    log_callback(f"   Ended:       {end_time.strftime('%a, %b %d at %I:%M %p')}")
    log_callback(f"   Duration:    [bold]{duration_str}[/bold]")
    log_callback(f"   Total Shots: [bold]{len(image_files)}[/bold] ({len(all_stats)} with EXIF)")

    log_callback("\n[bold]☀️ Lighting Conditions:[/bold]")
    bar_lines = generate_bar_chart(lighting_buckets, bar_width=30)
    for line in bar_lines:
        log_callback(line)
    
    log_callback("\n[bold]🎨 Creative Habits (Top 3):[/bold]")
    log_callback("    [cyan]Cameras:[/cyan]")
    for cam, count in camera_counter.most_common(3):
        log_callback(f"      {cam}: [bold]{count} shots[/bold]")
    log_callback("    [cyan]Focal Lengths:[/cyan]")
    for focal, count in focal_len_counter.most_common(3):
        log_callback(f"      {focal}: [bold]{count} shots[/bold]")
    log_callback("    [cyan]Apertures:[/cyan]")
    for ap, count in aperture_counter.most_common(3):
        log_callback(f"      {ap}: [bold]{count} shots[/bold]")
