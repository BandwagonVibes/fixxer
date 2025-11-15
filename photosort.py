#!/usr/bin/env python3
from __future__ import annotations
"""
PhotoSort v9.3 - AI-Powered Photography Workflow Automation (LOGGING & UX UPDATE)

Created by: Nick (∞vision crew)
Engineered by: Claude (Anthropic) + Gemini (Google)

Features:
- Auto Mode: Complete automated workflow (Stack → Cull → AI-Name → Archive)
- AI Critique: Creative Director analysis with JSON sidecars
- Burst Stacking: v8.0 CLIP semantic grouping (deterministic, robust)
- Quality Culling: v8.0 BRISQUE+VLM cascade (bokeh-aware)
- EXIF Insights: Session analytics dashboard
- Smart Prep: Copy keepers to Lightroom folder

v9.3 ENHANCEMENTS:
- AI Rename Logging: Track all AI renames with timestamps and destinations
- Clear Progress Messaging: Show breakdown of already-named vs needs-processing
- Tier A/B/C Culling: Positive selection psychology (no more "duds")

v9.2 OPTIMIZATIONS:
- Single AI Call per Burst: PICK files get AI-named during stacking
- Smart Skip Detection: Cull stage skips already-named PICKs
- Consistent Naming: Folder name matches PICK filename
- 79% Faster: Eliminates duplicate AI analysis on burst PICKs

Tech Stack:
- Local AI via Ollama (qwen2.5vl:3b for structured JSON)
- CLIP embeddings (sentence-transformers)
- BRISQUE quality assessment (image-quality)
- DBSCAN clustering (scikit-learn)
- RAW support via dcraw (macOS)
- Config file: ~/.photosort.conf

Version History:
V9.3 - AI rename logging, progress messaging clarity, Tier A/B/C culling
V9.2 - Burst naming optimization (single AI call per burst)
V9.1 - AI burst naming, organized parent directory for bursts
V9.0 - qwen2.5vl:3b integration, structured JSON (filename/tags) AI naming
V8.0 - CLIP burst stacking, BRISQUE+VLM cascade, consolidated analysis, de-branded
V7.1 (GM 3.2) - Patched stats tracking
V7.1 - 200 phrases, directory selector, session tracking
V7.0 - AI Critic feature, config file system
V6.0 - Quality culling engine
V5.0 - Burst stacker
V4.0 - Vision model integration
"""

import os
import json
import base64
import requests
import shutil
import tempfile
import configparser
import time
import threading
from threading import Event
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple, List, Dict, Any
from collections import defaultdict, Counter
import re
import subprocess
import sys
import math
from io import BytesIO

# v7.1: Import new modules
try:
    from phrases import get_phrase_by_duration, get_model_loading_phrase, get_quit_message
    from utils import (sanitize_filename as util_sanitize, get_file_size_mb, format_size, 
                       format_duration, get_exif_date, get_exif_camera_info, generate_session_id)
    from session_tracker import SessionTracker
    from directory_selector import get_source_and_destination, update_config_paths, INQUIRER_AVAILABLE
    V71_MODULES_OK = True
except ImportError as e:
    print(f"⚠️  v7.1 module import error: {e}")
    print("   Make sure all v7.1 module files are in the same directory!")
    sys.exit(1)

# ==============================================================================
# v8.0 IMPORTS - AI-Powered Engines
# ==============================================================================

V8_AVAILABLE = False
try:
    import burst_engine
    import cull_engine
    V8_AVAILABLE = True
    print(" ✓ v8.0 engines loaded (CLIP + BRISQUE)")
except ImportError:
    print(" ⚠️  v8.0 engines not available, using legacy algorithms")
    V8_AVAILABLE = False


# ==============================================================================
# I. OPTIONAL IMPORTS (Graceful degradation)
# ==============================================================================

# --- Colorama for ASCII Art (Optional) ---
COLORAMA_AVAILABLE = False
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    # Create mock objects for graceful fallback
    class MockStyle:
        RESET_ALL = ""
        BRIGHT = ""
    class MockFore:
        RED = ""
        GREEN = ""
        CYAN = ""
        YELLOW = ""
        WHITE = ""
    Fore = MockFore()
    Style = MockStyle()

# --- V5.0: Burst Stacker Imports ---
V5_LIBS_MSG = " FATAL: '--group-bursts' requires the 'imagehash' library.\n   Please run: pip install imagehash"
try:
    import imagehash
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    V5_LIBS_AVAILABLE = True
except ImportError:
    V5_LIBS_AVAILABLE = False

# --- V6.0: Cull Mode Imports ---
V6_LIBS_MSG = " FATAL: '--cull' or '--prep' requires 'opencv-python' and 'numpy'.\n   Please run: pip install opencv-python numpy"
try:
    import cv2
    import numpy as np
    V6_CULL_LIBS_AVAILABLE = True
except ImportError:
    V6_CULL_LIBS_AVAILABLE = False

# --- V6.4: EXIF Stats Imports ---
V6_4_LIBS_MSG = " FATAL: '--stats' requires the 'exifread' library.\n   Please run: pip install exifread"
try:
    import exifread
    V6_4_EXIF_LIBS_AVAILABLE = True
except ImportError:
    V6_4_EXIF_LIBS_AVAILABLE = False

# --- Progress Bar (Optional but recommended) ---
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # Create a mock tqdm class if not available
    class tqdm:
        def __init__(self, *args, **kwargs):
            self.total = kwargs.get('total', 0)
            self.n = 0
        def update(self, n=1):
            self.n += n
            sys.stdout.write(f"\rProcessing... {self.n}/{self.total}")
            sys.stdout.flush()
        def close(self):
            sys.stdout.write("\n")
        def set_description(self, desc):
            pass # No-op
        def write(self, s):
            print(s)

# ==============================================================================
# II. v7.1 GM 3.0: IN-LINED SMART PROGRESS BAR
# ==============================================================================

# v7.1 GM 3.0: In-lined SmartProgressBar with threading
class SmartProgressBar(tqdm):
    """
    tqdm wrapper with an independent, threaded phrase rotator.
    Rotates phrases every 8 seconds in bright red.
    """
    def __init__(self, *args, rotation_interval: int = 8, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()
        self.current_phrase = "Initializing..."
        self._rotation_interval = rotation_interval
        self._stop_event = Event()
        
        self._rotation_thread = threading.Thread(
            target=self._rotation_worker, daemon=True
        )
        self._rotation_thread.start()

    def _rotation_worker(self):
        """Worker thread to rotate phrases every X seconds."""
        while not self._stop_event.wait(self._rotation_interval):
            elapsed = time.time() - self.start_time
            phrase = get_phrase_by_duration(elapsed)
            
            # v7.1 GM 3.0: Apply RED font
            if COLORAMA_AVAILABLE:
                self.current_phrase = f"{Fore.RED}{Style.BRIGHT}{phrase}{Style.RESET_ALL}"
            else:
                self.current_phrase = phrase
            
            self.set_description(self.current_phrase)

    def update(self, n=1):
        """Override update to also refresh the description."""
        self.set_description(self.current_phrase)
        super().update(n)

    def close(self):
        """Signal the thread to stop and join it."""
        self._stop_event.set()
        self._rotation_thread.join(timeout=0.5)
        super().close()

# v7.1 GM 3.0: Model Loading Progress Bar (also threaded)
class ModelLoadingProgress:
    """
    A simple threaded spinner for model loading.
    Rotates phrases every 5 seconds in bright red.
    """
    def __init__(self, message="Loading model..."):
        self.message = message
        self._stop_event = Event()
        self._thread = threading.Thread(target=self._spinner, daemon=True)
        self.start_time = 0.0
    
    def _spinner(self):
        spinner = ['⠇', '⠏', '⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧']
        i = 0
        last_phrase_time = 0
        
        while not self._stop_event.wait(0.1): # 0.1s spin cycle
            elapsed = time.time() - self.start_time
            
            # Rotate model loading phrase every 5 seconds
            if (elapsed - last_phrase_time) > 5.0:
                 self.message = get_model_loading_phrase()
                 last_phrase_time = elapsed
            
            spin_char = spinner[i % len(spinner)]
            
            if COLORAMA_AVAILABLE:
                phrase = f"{Fore.RED}{Style.BRIGHT}{self.message}{Style.RESET_ALL}"
            else:
                phrase = self.message
                
            sys.stdout.write(f'\r {spin_char} {phrase}  ')
            sys.stdout.flush()
            i += 1
    
    def start(self):
        self.start_time = time.time()
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=0.5)
        sys.stdout.write('\r' + ' ' * (len(self.message) + 40) + '\r') # Clear line
        sys.stdout.flush()

# ==============================================================================
# III. ASCII ART & BANNER SYSTEM - VISIONCREW WAREZ EDITION
# ==============================================================================

def clear_console():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_terminal_width(default=80):
    """Helper to get terminal width safely."""
    try:
        width = shutil.get_terminal_size((default, 20)).columns
        return width
    except:
        return default

def print_visioncrew_animated():
    """
    Animated VISIONCREW banner with 90's warez aesthetics.
    """
    
    width = get_terminal_width()
    
    vision_crew_art = [
        "██    ██ ██ ███████ ██  ██████  ███    ██   ██████ ██████  ███████ ██    ██ ",
        "██    ██ ██ ██      ██ ██    ██ ████   ██  ██      ██   ██ ██      ██    ██ ",
        "██    ██ ██ ███████ ██ ██    ██ ██ ██  ██  ██      ██████  █████   ██ █  ██ ",
        " ██  ██  ██      ██ ██ ██    ██ ██  ██ ██  ██      ██   ██ ██      ████  ██ ",
        "  ████   ██ ███████ ██  ██████  ██   ████   ██████ ██   ██ ███████ ██ ██ ██ "
    ]
    
    split_point = 40
    
    text_lines = [
        "PHOTOSORT v9.3 - LOGGING & UX UPDATE",
        "cracked by vision crew | serial: 1989-IMG",
        "",
        "use responsibly.",
        "unleash creatively.",
        "inference locally."
    ]
    
    clear_console()
    
    if COLORAMA_AVAILABLE:
        for line in vision_crew_art:
            vision_part = line[:split_point]
            crew_part = line[split_point:]
            
            colored_line = f"{Fore.WHITE}{Style.BRIGHT}{vision_part}{Fore.RED}{Style.BRIGHT}{crew_part}{Style.RESET_ALL}"
            print(colored_line.center(width))
            time.sleep(0.08)
        
        print()
        
        left_pad = (width - 40) // 2
        for i, line in enumerate(text_lines):
            if line == "":
                print()
            elif i < 2:
                print(f"{Fore.RED}{Style.BRIGHT}{line}{Style.RESET_ALL}".center(width))
            else:
                print(f"{' ' * left_pad}{Fore.RED}{Style.BRIGHT}{line}{Style.RESET_ALL}")
                time.sleep(0.15)
        
    else:
        for line in vision_crew_art:
            print(line.center(width))
        
        print()
        
        left_pad = (width - 40) // 2
        for i, line in enumerate(text_lines):
            if line == "":
                print()
            elif i < 2:
                print(line.center(width))
            else:
                print(f"{' ' * left_pad}{line}")
    
    print()

def print_static_banner():
    """
    Static VISIONCREW banner (no animation)
    """
    width = get_terminal_width()
    
    vision_crew_art = [
        "██    ██ ██ ███████ ██  ██████  ███    ██   ██████ ██████  ███████ ██    ██ ",
        "██    ██ ██ ██      ██ ██    ██ ████   ██  ██      ██   ██ ██      ██    ██ ",
        "██    ██ ██ ███████ ██ ██    ██ ██ ██  ██  ██      ██████  █████   ██ █  ██ ",
        " ██  ██  ██      ██ ██ ██    ██ ██  ██ ██  ██      ██   ██ ██      ████  ██ ",
        "  ████   ██ ███████ ██  ██████  ██   ████   ██████ ██   ██ ███████ ██ ██ ██ "
    ]
    
    split_point = 40
    
    text_lines = [
        "PHOTOSORT v9.3 - LOGGING & UX UPDATE",
        "cracked by vision crew | serial: 1989-IMG",
        "",
        "use responsibly.",
        "unleash creatively.",
        "inference locally."
    ]
    
    clear_console()
    
    if COLORAMA_AVAILABLE:
        for line in vision_crew_art:
            vision_part = line[:split_point]
            crew_part = line[split_point:]
            colored_line = f"{Fore.WHITE}{Style.BRIGHT}{vision_part}{Fore.RED}{Style.BRIGHT}{crew_part}{Style.RESET_ALL}"
            print(colored_line.center(width))
        
        print()
        
        left_pad = (width - 40) // 2
        for i, line in enumerate(text_lines):
            if line == "":
                print()
            elif i < 2:
                print(f"{Fore.RED}{Style.BRIGHT}{line}{Style.RESET_ALL}".center(width))
            else:
                print(f"{' ' * left_pad}{Fore.RED}{Style.BRIGHT}{line}{Style.RESET_ALL}")
    else:
        for line in vision_crew_art:
            print(line.center(width))
        
        print()
        
        left_pad = (width - 40) // 2
        for i, line in enumerate(text_lines):
            if line == "":
                print()
            elif i < 2:
                print(line.center(width))
            else:
                print(f"{' ' * left_pad}{line}")
    
    print()

def show_banner(mode="animated"):
    """
    Smart banner display based on command type.
    """
    if mode == "animated" and COLORAMA_AVAILABLE:
        try:
            print_visioncrew_animated()
        except Exception as e:
            print(f"--- PHOTOSORT v9.3 --- (Animation failed: {e})")
            print_static_banner()
    else:
        print_static_banner()


# ==============================================================================
# IV. CONSTANTS & CONFIGURATION
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

# ==============================================================================
# v8.0 ALGORITHM CONFIGURATION  
# ==============================================================================

DEFAULT_BURST_ALGORITHM = 'clip' if V8_AVAILABLE else 'legacy'
DEFAULT_CULL_ALGORITHM = 'brisque' if V8_AVAILABLE else 'legacy'
DEFAULT_CLIP_EPS = 0.15
DEFAULT_CLIP_MIN_SAMPLES = 2
DEFAULT_BRISQUE_KEEPER = 35.0
DEFAULT_BRISQUE_AMBIGUOUS = 50.0
DEFAULT_VLM_MODEL = "openbmb/minicpm-v2.6:q4_K_M"

DEFAULT_DESTINATION_BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/negatives"
DEFAULT_CRITIQUE_MODEL = "qwen2.5vl:3b"

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
    "Architecture": ["building", "architecture", "structure", "facade", "construction", "tower", "bridge", "monument"],
    "Street-Scenes": ["street", "road", "sidewalk", "crosswalk", "traffic", "urban", "city"],
    "People": ["people", "person", "man", "woman", "child", "crowd", "pedestrian", "walking"],
    "Nature": ["tree", "forest", "mountain", "lake", "river", "ocean", "beach", "sunset", "sunrise", "sky", "cloud"],
    "Transportation": ["car", "bus", "train", "trolley", "vehicle", "bicycle", "scooter", "motorcycle"],
    "Signs-Text": ["sign", "text", "billboard", "poster", "graffiti", "writing"],
    "Food-Dining": ["food", "restaurant", "cafe", "produce", "market", "vendor", "stand"],
    "Animals": ["dog", "cat", "bird", "animal", "pet"],
    "Interior": ["interior", "room", "inside", "indoor"],
}

BEST_PICK_PREFIX = "_PICK_"
PREP_FOLDER_NAME = "_ReadyForLightroom"

# v9.3: Tier-based cull folder names (positive selection psychology)
TIER_A_FOLDER = "_Tier_A"  # Best quality (was _Keepers)
TIER_B_FOLDER = "_Tier_B"  # Review needed (was _Review_Maybe)
TIER_C_FOLDER = "_Tier_C"  # Archive/low priority (was _Review_Duds)


# ==============================================================================
# V. CORE UTILITIES
# ==============================================================================

def check_dcraw():
    """Check if dcraw is available and update RAW support"""
    global RAW_SUPPORT
    global SUPPORTED_EXTENSIONS
    try:
        result = subprocess.run(['which', 'dcraw'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            RAW_SUPPORT = True
            SUPPORTED_EXTENSIONS.add('.rw2')
    except Exception:
        RAW_SUPPORT = False

def get_available_models() -> Optional[List[str]]:
    """
    Get list of available Ollama models.
    """
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]
        models = [line.split()[0] for line in lines if line.strip()]
        return models
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        return None
    except Exception:
        return None

def parse_model_override() -> Optional[str]:
    """
    V7.0 GOLD: Extract --model argument from CLI if present
    """
    try:
        if "--model" in sys.argv:
            model_index = sys.argv.index("--model") + 1
            if model_index < len(sys.argv):
                return sys.argv[model_index]
    except Exception:
        pass
    return None

def convert_raw_to_jpeg(raw_path: Path) -> Optional[bytes]:
    """Convert RAW file to JPEG bytes using dcraw and sips"""
    if not RAW_SUPPORT:
        return None
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_jpg = tmp.name
        
        result = subprocess.run(
            ['dcraw', '-c', '-w', '-q', '3', str(raw_path)],
            capture_output=True,
            check=True
        )
        
        with tempfile.NamedTemporaryFile(suffix='.ppm', delete=False) as ppm_tmp:
            ppm_tmp.write(result.stdout)
            ppm_file = ppm_tmp.name
        
        subprocess.run(
            ['sips', '-s', 'format', 'jpeg', ppm_file, '--out', tmp_jpg],
            capture_output=True,
            check=True
        )
        
        with open(tmp_jpg, 'rb') as f:
            jpeg_bytes = f.read()
        
        os.unlink(ppm_file)
        os.unlink(tmp_jpg)
        
        return jpeg_bytes
    
    except Exception as e:
        print(f" Error converting RAW file: {e}")
        try:
            if 'ppm_file' in locals():
                os.unlink(ppm_file)
            if 'tmp_jpg' in locals() and os.path.exists(tmp_jpg):
                os.unlink(tmp_jpg)
        except:
            pass
        return None

def encode_image(image_path: Path) -> Optional[str]:
    """Convert image to base64 string, handling RAW files"""
    try:
        if image_path.suffix.lower() in ('.rw2', '.cr2', '.nef', '.arw', '.dng'):
            jpeg_bytes = convert_raw_to_jpeg(image_path)
            if jpeg_bytes:
                return base64.b64encode(jpeg_bytes).decode('utf-8')
            else:
                return None
        
        with open(image_path, 'rb') as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    
    except Exception as e:
        print(f" Error encoding {image_path.name}: {e}")
        return None

def get_image_bytes_for_analysis(image_path: Path) -> Optional[bytes]:
    """Helper to get bytes from any supported file"""
    ext = image_path.suffix.lower()
    if ext in ('.rw2', '.cr2', '.nef', '.arw', '.dng'):
        return convert_raw_to_jpeg(image_path)
    elif ext in ('.jpg', '.jpeg', '.png'):
        try:
            with open(image_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"    Failed to read {image_path.name}: {e}")
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
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or (days == 0 and hours == 0):
        parts.append(f"{minutes}m")
        
    return " ".join(parts) if parts else "0m"

def generate_bar_chart(data: dict, bar_width: int = 25, bar_char: str = "■") -> List[str]:
    """Generates ASCII bar chart lines from a dictionary"""
    output_lines = []
    if not data:
        return output_lines
        
    max_val = max(data.values())
    if max_val == 0:
        max_val = 1
        
    max_key_len = max(len(key) for key in data.keys())
    
    for key, val in data.items():
        bar_len = int(math.ceil((val / max_val) * bar_width))
        bar = bar_char * bar_len
        line = f"   {key.ljust(max_key_len)}: {str(val).ljust(4)} {bar}"
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

# ==============================================================================
# v9.3: AI RENAME LOGGING
# ==============================================================================

def write_rename_log(log_path: Path, original_name: str, new_name: str, destination: Path):
    """
    (V9.3) Append an AI rename operation to the log file.
    
    Format: timestamp | original_name -> new_name | destination_path
    
    This creates a helpful reference for users who back up their entire card
    and need to track what was renamed and where it went.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | {original_name} -> {new_name} | {destination}\n"
        
        with open(log_path, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        # Silent fail - don't interrupt workflow for logging issues
        pass

def initialize_rename_log(log_path: Path):
    """
    (V9.3) Initialize the rename log file with a header.
    """
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
    V7.0: Loads settings from ~/.photosort.conf
    """
    parser = configparser.ConfigParser()
    if CONFIG_FILE_PATH.exists():
        parser.read(CONFIG_FILE_PATH)
        print(f" ⓘ Loaded config from: {CONFIG_FILE_PATH}")

    config = {}

    # Ingest settings
    config['default_destination'] = Path(parser.get(
        'ingest', 'default_destination',
        fallback=str(DEFAULT_DESTINATION_BASE)
    )).expanduser()
    config['default_model'] = parser.get(
        'ingest', 'default_model',
        fallback=DEFAULT_MODEL_NAME
    )

    # Cull thresholds
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

    # Burst threshold
    config['burst_threshold'] = parser.getint(
        'burst', 'similarity_threshold',
        fallback=DEFAULT_BURST_THRESHOLD
    )

    config['burst_algorithm'] = parser.get(
        'burst', 'burst_algorithm',
        fallback=DEFAULT_BURST_ALGORITHM
    )

    # V7.0 Critique settings
    config['critique_model'] = parser.get(
        'critique', 'default_model',
        fallback=DEFAULT_CRITIQUE_MODEL
    )

    # v7.1: Folder settings
    config['burst_parent_folder'] = parser.getboolean(
        'folders', 'burst_parent_folder', fallback=True
    )
    config['ai_session_naming'] = parser.getboolean(
        'folders', 'ai_session_naming', fallback=True
    )

    # v7.1: Session settings
    config['save_history'] = parser.getboolean(
        'session', 'save_history', fallback=True
    )
    config['history_path'] = Path(parser.get(
        'session', 'history_path', fallback=str(Path.home() / ".photosort_sessions.json")
    )).expanduser()
    config['show_summary'] = parser.getboolean(
        'session', 'show_summary', fallback=True
    )

    # v7.1: Behavior settings
    config['last_source_path'] = parser.get(
        'behavior', 'last_source_path', fallback=None
    )
    config['last_destination_path'] = parser.get(
        'behavior', 'last_destination_path', fallback=None
    )

    return config


# ==============================================================================
# VII. AI & ANALYSIS MODULES (The "Brains")
# ==============================================================================

def get_ai_description(image_path: Path, model_name: str) -> Tuple[Optional[str], Optional[List[str]]]:
    """
    (V9.0) Get structured filename and tags from AI.
    """
    base64_image = encode_image(image_path)
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
            {
                "role": "user",
                "content": AI_NAMING_PROMPT,
                "images": [base64_image]
            }
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
            print(f"  Warning: Model returned valid JSON but missing keys for {image_path.name}")
            return None, None

        return str(filename), list(tags)
        
    except requests.exceptions.Timeout:
        print(f"  Timeout processing {image_path.name}")
        return None, None
    except json.JSONDecodeError:
        print(f"  Error: Model returned invalid JSON for {image_path.name}")
        return None, None
    except Exception as e:
        print(f"  Error processing {image_path.name}: {e}")
        return None, None

def get_ai_critique(image_path: Path, model_name: str) -> Optional[str]:
    """(V7.0) Get AI "Creative Director" critique as a JSON string"""
    base64_image = encode_image(image_path)
    if not base64_image:
        return None
    
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": AI_CRITIC_PROMPT,
                "images": [base64_image]
            }
        ],
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=CRITIQUE_TIMEOUT)
        response.raise_for_status()
        
        result = response.json()
        json_string = result['message']['content'].strip()
        
        return json_string
        
    except requests.exceptions.Timeout:
        print(f"  Timeout getting critique for {image_path.name}")
        return None
    except Exception as e:
        print(f" Error getting critique for {image_path.name}: {e}")
        return None

def get_ai_image_name(image_path: Path, model_name: str) -> Optional[Dict[str, Any]]:
    """
    (V9.2) Generate AI-powered name for an image (for burst PICK files).
    """
    try:
        filename, tags = get_ai_description(image_path, model_name)
        
        if not filename or not tags:
            return None
        
        filename_no_ext = Path(filename).stem
        clean_name = clean_filename(filename_no_ext)
        
        return {
            'filename': clean_name,
            'tags': tags
        }
        
    except Exception:
        return None

def is_already_ai_named(filename: str) -> bool:
    """
    (V9.2) Check if a PICK file already has an AI-generated name.
    """
    if not re.search(r'_PICK\.\w+$', filename, re.IGNORECASE):
        return False
    
    if filename.startswith('_PICK_'):
        return False
    
    return True

def get_image_hash(image_path: Path) -> Optional[tuple[Path, imagehash.ImageHash]]:
    """
    Calculates perceptual hash (visual fingerprint) of an image.
    """
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
        print(f"     Skipping hash for {image_path.name}: {e}")
        return image_path, None

def analyze_image_quality(image_bytes: bytes) -> Dict[str, float]:
    """
    Analyzes image bytes for sharpness and exposure.
    """
    scores = {
        'sharpness': 0.0,
        'blacks_pct': 0.0,
        'whites_pct': 0.0
    }
    try:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is None:
            return scores

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
    """
    Thread-pool worker: Opens image and extracts key EXIF data.
    """
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False, stop_tag='EXIF DateTimeOriginal')

            if not tags or 'EXIF DateTimeOriginal' not in tags:
                return None

            timestamp_str = str(tags['EXIF DateTimeOriginal'])
            dt_obj = datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')

            camera = str(tags.get('Image Model', 'Unknown')).strip()
            focal_len = str(tags.get('EXIF FocalLength', 'Unknown')).split(' ')[0]
            
            aperture_str = "Unknown"
            aperture_tag = tags.get('EXIF FNumber')
            
            if aperture_tag:
                val = aperture_tag.values[0]
                
                if hasattr(val, 'num') and hasattr(val, 'den'):
                    if val.den == 0:
                        aperture_val = 0.0
                    else:
                        aperture_val = float(val.num) / float(val.den)
                    aperture_str = f"f/{aperture_val:.1f}"
                else:
                    aperture_str = f"f/{val:.1f}"

            if not camera:
                camera = "Unknown"
            if not focal_len:
                focal_len = "Unknown"
            if aperture_str == "f/0.0":
                aperture_str = "Unknown"

            return {
                'timestamp': dt_obj,
                'camera': camera,
                'focal_length': f"{focal_len} mm",
                'aperture': aperture_str
            }
            
    except Exception:
        return None


# ==============================================================================
# VIII. FEATURE WORKFLOWS (The "Tools")
# ==============================================================================

# --- Ingest & Auto-Workflow Helpers ---

def get_ingest_config(APP_CONFIG: dict) -> Tuple[Path, str]:
    """
    (DEPRECATED by v7.1)
    """
    default_dest = APP_CONFIG['default_destination']
    default_model = APP_CONFIG['default_model']

    print(f"\n 🗂️  Default archive destination: {default_dest}")
    new_dest_path = input("   Press ENTER to use default, or type a new path: ").strip()
    
    chosen_destination: Path
    if not new_dest_path:
        chosen_destination = default_dest
        print(f"    Using default destination.")
    else:
        chosen_destination = Path(new_dest_path).expanduser()
        print(f"    Using: {chosen_destination}")
    
    try:
        chosen_destination.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f" ❌ Error creating destination folder: {e}")
        print("   Please check the path and permissions. Exiting.")
        sys.exit(1)
    
    print(f"\n 🤖 Default model: {default_model}")
    
    loader = ModelLoadingProgress(message="Checking Ollama connection...")
    loader.start()
    available_models = get_available_models()
    loader.stop()
    
    if available_models is None:
        print("\n ❌ FATAL: Could not connect to Ollama server.")
        print("   Please ensure Ollama is running.")
        sys.exit(1)
    
    if available_models:
        print(f"   Available models: {', '.join(available_models)}")
    else:
        print("     No models found. Run 'ollama pull minicpm-v2.6' to install one.")
    
    new_model = input("   Press ENTER to use default, or type a model name: ").strip()
    
    chosen_model: str
    if not new_model:
        chosen_model = default_model
        print(f"    Using default model.")
    else:
        if available_models and new_model not in available_models:
            print(f"     Warning: '{new_model}' not found in available models.")
            print(f"   Available: {', '.join(available_models)}")
            confirm = input("   Continue anyway? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Cancelled.")
                sys.exit(0)
        chosen_model = new_model
        print(f"    Using model: {chosen_model}")
    
    return chosen_destination, chosen_model

def process_single_image(image_path: Path, destination_base: Path, model_name: str, dry_run: bool, rename_log_path: Optional[Path] = None) -> Tuple[Path, bool, str, str]:
    """
    (V9.3) Process one image: get AI name/tags, rename, move to temp location.
    
    V9.3 ENHANCEMENT: Now accepts optional rename_log_path to track all renames.
    V9.2 OPTIMIZATION: Skip AI naming if file already has AI-generated name.
    
    Returns: (original_path, success_bool, new_filename_str, description_for_categorization)
    """
    try:
        # V9.2: Check if this is already an AI-named PICK file
        if is_already_ai_named(image_path.name):
            extension = image_path.suffix.lower()
            base_name = image_path.stem
            
            if base_name.endswith('_PICK'):
                clean_base = base_name[:-5]
            else:
                clean_base = base_name
            
            new_path = get_unique_filename(clean_base, extension, destination_base)
            
            if not dry_run:
                shutil.move(str(image_path), str(new_path))
                # v9.3: Log the rename
                if rename_log_path:
                    write_rename_log(rename_log_path, image_path.name, new_path.name, destination_base)
            
            description_for_categorization = clean_base.replace('-', ' ')
            
            return image_path, True, new_path.name, description_for_categorization
        
        # Original flow: Not pre-named, so get AI description
        ai_filename, ai_tags = get_ai_description(image_path, model_name)
        
        if not ai_filename or not ai_tags:
            return image_path, False, "Failed to get valid AI JSON response", ""
        
        description_for_categorization = " ".join(ai_tags)

        clean_name = Path(ai_filename).stem
        extension = image_path.suffix.lower()
        new_path = get_unique_filename(clean_name, extension, destination_base)
        
        if not dry_run:
            shutil.move(str(image_path), str(new_path))
            # v9.3: Log the rename
            if rename_log_path:
                write_rename_log(rename_log_path, image_path.name, new_path.name, destination_base)
        
        return image_path, True, new_path.name, description_for_categorization
        
    except Exception as e:
        return image_path, False, str(e), ""

def organize_into_folders(processed_files: List[Dict], files_source: Path, destination_base: Path, dry_run: bool):
    """
    Group files into folders based on their descriptions.
    """
    print(f"\n{'='*60}")
    print(" 🗂️  Organizing into smart folders...")
    print(f"{'='*60}\n")
    
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
        
        if not dry_run:
            folder_path.mkdir(exist_ok=True)
        
        print(f" {folder_name}/ ({len(files)} files)")
        
        for file_info in files:
            src = files_source / file_info['filename']
            dst = folder_path / file_info['filename']
            
            if not dry_run:
                if src.exists():
                    shutil.move(str(src), str(dst))
                else:
                    print(f"   [WARN] Source file not found: {src}")
            else:
                print(f"   [PREVIEW] Would move {file_info['filename']} here")
    
    print(f"\n Organized into {len(categories)} folders")

def generate_ai_session_name(categories: Dict[str, int], model_name: str) -> Optional[str]:
    """
    v7.1: Generate AI-powered session name based on image categories.
    """
    if not categories:
        return None
    
    category_list = [f"- {cat}: {count} images" for cat, count in categories.items()]
    category_text = "\n".join(category_list)
    
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
   - Think of names like "Convergence", "Threshold", "Ephemera", "Solstice", "Momentum".

Photo Categories:
{category_text}

Respond with ONLY a single JSON object in this exact format:
{{"session_name": "<your-single-word-name>"}}
"""
    
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
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
        print(f"  Warning: Could not generate AI session name: {e}")
        return None

def process_directory(directory: Path, destination_base: Path, model_name: str, dry_run: bool):
    """
    (V4.0+) Main processing loop - AI-describes and organizes images.
    """
    print(f"\n{'='*60}")
    print(f" 📁 Processing: {directory}")
    print(f" 📂 Destination: {destination_base}")
    print(f"{'='*60}")
    
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if not image_files:
        print("   No supported images found in this directory.")
        return
    
    print(f"\n Found {len(image_files)} images to process.")
    
    # v9.3: Initialize rename log
    rename_log_path = destination_base / f"_ai_rename_log_{SESSION_TIMESTAMP}.txt"
    if not dry_run:
        initialize_rename_log(rename_log_path)
    
    results = {"success": [], "failed": []}
    
    pbar = None
    if TQDM_AVAILABLE:
        pbar = SmartProgressBar(total=len(image_files), desc=" 🤖 AI Processing", unit="img")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(process_single_image, img_path, destination_base, model_name, dry_run, rename_log_path): img_path 
            for img_path in image_files
        }
        
        for future in as_completed(future_to_file):
            original, success, message, description = future.result()
            
            if success:
                results["success"].append({
                    "original": original.name,
                    "new_name": message,
                    "description": description
                })
            else:
                results["failed"].append((original.name, message))
                if pbar:
                    pbar.write(f" ❌ {original.name}: {message}")
            
            if pbar:
                pbar.update()
    
    if pbar:
        pbar.close()
    
    print(f"\n{'='*60}")
    print(f" ✅ Successfully processed: {len(results['success'])}")
    print(f" ❌ Failed: {len(results['failed'])}")
    
    if results["failed"]:
        print("\n  Failed files:")
        for orig, reason in results["failed"]:
            print(f"   • {orig}: {reason}")
    
    if results["success"]:
        categories = {}
        for item in results["success"]:
            cat = categorize_description(item["description"])
            categories[cat] = categories.get(cat, 0) + 1
        
        session_name = generate_ai_session_name(categories, model_name)
        
        if session_name and len(session_name) > 2:
            dated_folder = f"{SESSION_DATE}_{session_name}"
            print(f"\n   🎨 AI Session Name: {dated_folder}")
        else:
            dated_folder = f"{SESSION_DATE}_Session"
        
        final_destination = destination_base / dated_folder
        final_destination.mkdir(parents=True, exist_ok=True)
        
        organize_into_folders(results["success"], destination_base, final_destination, dry_run=False)
    
    log_file = destination_base / f"_import_log_{SESSION_TIMESTAMP}.json"
    
    if not dry_run:
        with open(log_file, 'w') as f:
            json.dump({
                "session_date": SESSION_TIMESTAMP,
                "source_directory": str(directory),
                "destination_directory": str(destination_base),
                "model_used": model_name,
                "total_files": len(image_files),
                "successful": results["success"],
                "failed": [{"original": o, "reason": r} for o, r in results["failed"]],
            }, f, indent=2)
        
        print(f"\n Log saved: {log_file.name}")
        print(f" 📝 Rename log saved: {rename_log_path.name}")
    else:
        print(f"\n[PREVIEW] Would save log file to: {log_file.name}")

# --- Burst Workflow ---

def group_bursts_in_directory(directory: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """
    (V9.3) Finds and stacks burst groups, AI-naming the best pick.
    
    V9.3: Now logs all AI renames to a dedicated log file.
    """
    
    print(f"\n{'='*60}")
    print(f" 📸 PhotoSort --- (Burst Stacker Mode)")
    print(f"{'='*60}")
    print(f" Scanning for visually similar images in: {directory}")
    
    burst_threshold = APP_CONFIG['burst_threshold']
    print(f"   (Similarity threshold: {burst_threshold})")
    print(f"   (Sharpest image will be prefixed: {BEST_PICK_PREFIX})")
    

    algorithm = APP_CONFIG.get('burst_algorithm', 'legacy')
    
    if algorithm == 'clip' and V8_AVAILABLE:
        print(f" ✓ Using v8.0 CLIP semantic grouping (eps={APP_CONFIG.get('burst_clip_eps', 0.15)})")
    elif algorithm == 'clip' and not V8_AVAILABLE:
        print(f" ⚠️  CLIP not available, using legacy imagehash")
        algorithm = 'legacy'
    else:
        print(f" Using legacy imagehash grouping")

    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if len(image_files) < 2:
        print("     Not enough images to compare. Exiting.")
        return

    all_hashes = {}
    print("\n Calculating visual fingerprints...")
    
    pbar = None
    if TQDM_AVAILABLE:
        pbar = SmartProgressBar(total=len(image_files), desc="   Hashing", unit="img")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(get_image_hash, path): path for path in image_files}
        
        iterable = as_completed(future_to_path)
        
        for future in iterable:
            path, img_hash = future.result()
            if img_hash:
                all_hashes[path] = img_hash
            if pbar:
                pbar.update()

    if pbar:
        pbar.close()

    print("\n Comparing fingerprints to find burst groups...")
    
    visited_paths = set()
    all_burst_groups = []
    
    sorted_paths = sorted(all_hashes.keys(), key=lambda p: p.name)
    
    for path in sorted_paths:
        if path in visited_paths:
            continue
            
        current_group = [path]
        visited_paths.add(path)
        
        for other_path in sorted_paths:
            if other_path in visited_paths:
                continue
                
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
        print("\n No burst groups found. All images are unique!")
        return
        
    print(f"\n Found {len(all_burst_groups)} burst groups. Analyzing for best pick...")
    
    best_picks: Dict[int, Tuple[Path, float]] = {}
    
    pbar_burst = None
    if TQDM_AVAILABLE:
        pbar_burst = SmartProgressBar(total=len(all_burst_groups), desc="   Analyzing bursts", unit="burst")

    for i, group in enumerate(all_burst_groups):
        best_sharpness = -1.0
        best_file = None
        
        for file_path in group:
            image_bytes = get_image_bytes_for_analysis(file_path)
            if image_bytes:
                scores = analyze_image_quality(image_bytes)
                sharpness = scores.get('sharpness', 0.0)
                
                if sharpness > best_sharpness:
                    best_sharpness = sharpness
                    best_file = file_path
        
        if best_file:
            best_picks[i] = (best_file, best_sharpness)
        
        if pbar_burst:
            pbar_burst.update()

    if pbar_burst:
        pbar_burst.close()


    # === v9.3 ENHANCED: AI naming + parent directory + logging ===
    
    use_parent_folder = APP_CONFIG.get('burst_parent_folder', True)
    
    if use_parent_folder:
        bursts_parent = directory / "_Bursts"
        print(f"\n Organizing burst groups into: {bursts_parent.name}/")
        if not dry_run:
            bursts_parent.mkdir(exist_ok=True)
    else:
        bursts_parent = directory
    
    print(f"\n Stacking {len(all_burst_groups)} burst groups...")
    
    # v9.3: Initialize rename log for burst operations
    rename_log_path = directory / f"_ai_rename_log_{SESSION_TIMESTAMP}.txt"
    if not dry_run:
        initialize_rename_log(rename_log_path)
    
    ai_model = APP_CONFIG.get('default_model', DEFAULT_MODEL_NAME)
    
    for i, group in enumerate(all_burst_groups):
        winner_data = best_picks.get(i)
        sample_image = winner_data[0] if winner_data else group[0]
        
        print(f"\n Burst {i+1}/{len(all_burst_groups)}: Generating AI name for PICK...")
        ai_result = get_ai_image_name(sample_image, ai_model)
        
        if ai_result and ai_result.get('filename'):
            base_name = ai_result['filename']
            folder_name = f"{base_name}_burst"
            print(f"   ✓ AI named: {base_name}")
        else:
            base_name = f"burst-{i+1:03d}"
            folder_name = base_name
            print(f"   ⚠️  AI naming failed, using: {base_name}")
        
        folder_path = bursts_parent / folder_name
        
        if folder_path.exists():
            counter = 2
            original_name = folder_name
            while folder_path.exists():
                folder_name = f"{original_name}-{counter}"
                folder_path = bursts_parent / folder_name
                counter += 1
        
        print(f"   📁 {folder_path.relative_to(directory)}/ ({len(group)} files)")
        
        if not dry_run:
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
            
            if not dry_run:
                try:
                    shutil.move(str(file_path), str(new_file_path))
                    print(f"      Moved {file_path.name} → {new_name}")
                    # v9.3: Log the rename
                    write_rename_log(rename_log_path, file_path.name, new_name, folder_path)
                except Exception as e:
                    print(f"      FAILED to move {file_path.name}: {e}")
            else:
                print(f"     [PREVIEW] Would move {file_path.name} → {new_name}")
    
    print("\n Burst stacking complete!")
    if use_parent_folder:
        print(f" All burst groups organized in: {bursts_parent}")
    if not dry_run:
        print(f" 📝 Rename log saved: {rename_log_path.name}")


# --- Cull Workflow ---

def process_image_for_culling(image_path: Path) -> Tuple[Path, Optional[Dict[str, float]]]:
    """Thread-pool worker: Gets bytes and runs analysis engine"""
    image_bytes = get_image_bytes_for_analysis(image_path)
    if not image_bytes:
        return image_path, None
    
    scores = analyze_image_quality(image_bytes)
    return image_path, scores

def cull_images_in_directory(directory: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """
    (V9.3) Finds and groups images by technical quality using Tier A/B/C naming.
    
    V9.3 ENHANCEMENT: Uses positive selection psychology with tier-based naming:
    - Tier A: Best quality (was "Keepers")
    - Tier B: Review needed (was "Maybe")
    - Tier C: Archive/low priority (was "Duds")
    """
    
    print(f"\n{'='*60}")
    print(f" 🗑️  PhotoSort --- (Cull Mode)")
    print(f"{'='*60}")
    print(f" Analyzing technical quality in: {directory}")

    algorithm = APP_CONFIG.get('cull_algorithm', 'legacy')
    
    if algorithm == 'brisque' and V8_AVAILABLE:
        print(f" ✓ Using v8.0 BRISQUE+VLM cascade")
        print(f"   Tier A: <{APP_CONFIG.get('cull_brisque_keeper', 35.0)}, Tier C: >{APP_CONFIG.get('cull_brisque_ambiguous', 50.0)}")
    elif algorithm == 'brisque' and not V8_AVAILABLE:
        print(f" ⚠️  BRISQUE not available, using legacy Laplacian")
        algorithm = 'legacy'
    else:
        print(f" Using legacy Laplacian variance")

    
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if not image_files:
        print("     No supported images to analyze. Exiting.")
        return

    all_scores = {}
    print("\n  Analyzing sharpness and exposure...")
    
    pbar = None
    if TQDM_AVAILABLE:
        pbar = SmartProgressBar(total=len(image_files), desc="   Analyzing", unit="img")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(process_image_for_culling, path): path 
            for path in image_files
        }
        
        iterable = as_completed(future_to_path)

        for future in iterable:
            path, scores = future.result()
            if scores:
                all_scores[path] = scores
            if pbar:
                pbar.update()
    
    if pbar:
        pbar.close()

    print("\n  Triaging images into quality tiers...")
    
    th = APP_CONFIG['cull_thresholds']
    # v9.3: Using tier-based naming internally
    tiers = {"Tier_A": [], "Tier_B": [], "Tier_C": []}
    log_data = []

    for path, scores in all_scores.items():
        sharp = scores['sharpness']
        blacks = scores['blacks_pct']
        whites = scores['whites_pct']
        
        is_exposure_bad = (blacks > th['exposure_dud_pct']) or (whites > th['exposure_dud_pct'])
        is_exposure_good = (blacks < th['exposure_good_pct']) and (whites < th['exposure_good_pct'])
        is_sharp_bad = sharp < th['sharpness_dud']
        is_sharp_good = sharp > th['sharpness_good']

        tier = "Tier_B"  # Default to middle tier
        if is_sharp_bad or is_exposure_bad:
            tier = "Tier_C"
        elif is_sharp_good and is_exposure_good:
            tier = "Tier_A"
        
        tiers[tier].append(path)
        log_data.append({
            'file': path.name,
            'tier': tier,
            'sharpness': round(sharp, 2),
            'blacks_pct': round(blacks, 4),
            'whites_pct': round(whites, 4)
        })

    # v9.3: Updated messaging with tier names
    print(f"\n Found {len(tiers['Tier_A'])} Tier A, {len(tiers['Tier_B'])} Tier B, and {len(tiers['Tier_C'])} Tier C.")
    
    # v9.3: Using tier-based folder names
    folder_map = {
        "Tier_A": directory / TIER_A_FOLDER,
        "Tier_B": directory / TIER_B_FOLDER,
        "Tier_C": directory / TIER_C_FOLDER
    }
    
    for tier, paths in tiers.items():
        if not paths:
            continue
            
        folder_path = folder_map[tier]
        print(f"\n {folder_path.name}/ ({len(paths)} files)")
        
        if not dry_run:
            folder_path.mkdir(exist_ok=True)
            
        for file_path in paths:
            new_file_path = folder_path / file_path.name
            if not dry_run:
                try:
                    shutil.move(str(file_path), str(new_file_path))
                    print(f"    Moved {file_path.name}")
                except Exception as e:
                    print(f"    FAILED to move {file_path.name}: {e}")
            else:
                print(f"   [PREVIEW] Would move {file_path.name} to {folder_path.name}/")

    log_file = directory / f"_cull_log_{SESSION_TIMESTAMP}.json"
    
    try:
        with open(log_file, 'w') as f:
            json.dump({
                "session_date": SESSION_TIMESTAMP,
                "source_directory": str(directory),
                "thresholds_used": th,
                "tier_mapping": {
                    "Tier_A": "Best quality (high sharpness, good exposure)",
                    "Tier_B": "Review needed (moderate quality)",
                    "Tier_C": "Archive/low priority (low sharpness or bad exposure)"
                },
                "analysis": sorted(log_data, key=lambda x: x['sharpness'])
            }, f, indent=2)
        
        if dry_run:
            print(f"\n [PREVIEW] Calibration log saved: {log_file.name}")
        else:
            print(f"\n Cull log saved: {log_file.name}")
            
    except Exception as e:
        print(f"\n FAILED to save log file: {e}")

    print("\n Culling complete!")

# --- Prep Workflow ---

def prep_smart_export(directory: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """(V6.3) Finds all "Good" tier images and COPIES them to prep folder"""
    
    print(f"\n{'='*60}")
    print(f" ✨ PhotoSort --- (Smart Prep Mode)")
    print(f"{'='*60}")
    print(f" Finding 'Tier A' to copy to: {PREP_FOLDER_NAME}/")
    
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if not image_files:
        print("     No supported images to analyze. Exiting.")
        return

    all_scores = {}
    print("\n  Analyzing technical quality...")
    
    pbar = None
    if TQDM_AVAILABLE:
        pbar = SmartProgressBar(total=len(image_files), desc="   Analyzing", unit="img")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(process_image_for_culling, path): path 
            for path in image_files
        }
        
        iterable = as_completed(future_to_path)

        for future in iterable:
            path, scores = future.result()
            if scores:
                all_scores[path] = scores
            if pbar:
                pbar.update()
    
    if pbar:
        pbar.close()

    print("\n  Finding 'Tier A' images...")
    
    th = APP_CONFIG['cull_thresholds']
    good_files = []

    for path, scores in all_scores.items():
        sharp = scores['sharpness']
        blacks = scores['blacks_pct']
        whites = scores['whites_pct']
        
        is_exposure_good = (blacks < th['exposure_good_pct']) and (whites < th['exposure_good_pct'])
        is_sharp_good = sharp > th['sharpness_good']

        if is_sharp_good and is_exposure_good:
            good_files.append(path)

    if not good_files:
        print("\n No 'Tier A' found that meet the quality criteria.")
        print("   (Try adjusting CULL_THRESHOLDS in ~/.photosort.conf if this seems wrong)")
        return

    print(f"\n Found {len(good_files)} 'Tier A' to copy.")
    
    folder_path = directory / PREP_FOLDER_NAME
    
    if not dry_run:
        folder_path.mkdir(exist_ok=True)
            
    for file_path in good_files:
        new_file_path = folder_path / file_path.name
        if not dry_run:
            try:
                shutil.copy2(str(file_path), str(new_file_path))
                print(f"    Copied {file_path.name}")
            except Exception as e:
                print(f"    FAILED to copy {file_path.name}: {e}")
        else:
            print(f"   [PREVIEW] Would copy {file_path.name} to {folder_path.name}/")

    print("\n Smart Prep complete!")

# --- Stats Workflow ---

def show_exif_insights(directory: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """(V6.4) Scans images, aggregates EXIF data, prints summary"""
    
    print(f"\n{'='*60}")
    print(f" 📊 PhotoSort --- (EXIF Stats Mode)")
    print(f"{'='*60}")
    print(f" Scanning EXIF data in: {directory}")
    
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if not image_files:
        print("     No supported images to analyze. Exiting.")
        return

    all_stats = []
    print("\n  Reading EXIF data...")
    
    pbar = None
    if TQDM_AVAILABLE:
        pbar = SmartProgressBar(total=len(image_files), desc="   Scanning", unit="img")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(analyze_single_exif, path): path 
            for path in image_files
        }
        
        iterable = as_completed(future_to_path)

        for future in iterable:
            result_dict = future.result()
            if result_dict:
                all_stats.append(result_dict)
            if pbar:
                pbar.update()

    if pbar:
        pbar.close()

    if not all_stats:
        print(f"\n  No EXIF data found in {len(image_files)} scanned images.")
        print("   (Files may be JPEGs with stripped metadata)")
        return

    print(" Aggregating statistics...")
    
    timestamps = sorted([s['timestamp'] for s in all_stats])
    start_time = timestamps[0]
    end_time = timestamps[-1]
    duration = end_time - start_time
    duration_str = format_duration(duration)

    LIGHTING_TABLE = {
        (0, 4):   "Night",
        (5, 7):   "Golden Hour (AM)",
        (8, 10):  "Morning",
        (11, 13): "Midday",
        (14, 16): "Afternoon",
        (17, 18): "Golden Hour (PM)",
        (19, 21): "Dusk",
        (22, 23): "Night",
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

    log_file_path = directory / f"_exif_summary_{SESSION_TIMESTAMP}.json"
    
    json_report = {
        "session_story": {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_str": duration_str,
            "total_images_scanned": len(image_files),
            "images_with_exif": len(all_stats)
        },
        "lighting_distribution": dict(lighting_buckets),
        "gear_used": {
            "cameras": dict(camera_counter),
        },
        "habits": {
            "focal_lengths": dict(focal_len_counter),
            "apertures": dict(aperture_counter),
        }
    }
    
    try:
        with open(log_file_path, 'w') as f:
            json.dump(json_report, f, indent=2)
    except Exception as e:
        print(f"\n  Warning: Could not save JSON log: {e}")

    header = f"EXIF INSIGHTS: {directory.name}"
    print(f"\n{'='*60}")
    print(f"{header:^60}")
    print(f"{'='*60}")
    
    print(" 📖 Session Story:")
    print(f"   Started:     {start_time.strftime('%a, %b %d %Y at %I:%M %p')}")
    print(f"   Ended:       {end_time.strftime('%a, %b %d %Y at %I:%M %p')}")
    print(f"   Duration:    {duration_str}")
    print(f"   Total Shots: {len(image_files)} ({len(all_stats)} with EXIF data)")
    print(f"{'-'*60}")

    print(" ☀️ Lighting Conditions:")
    bar_lines = generate_bar_chart(lighting_buckets, bar_width=30)
    for line in bar_lines:
        print(line)
    
    print("\n 🎨 Creative Habits (Top 3):")
        
    print("\n    Cameras:")
    for cam, count in camera_counter.most_common(3):
        print(f"      {cam}: {count} shots")

    print("\n    Focal Lengths:")
    for focal, count in focal_len_counter.most_common(3):
        print(f"      {focal}: {count} shots")

    print("\n    Apertures:")
    for ap, count in aperture_counter.most_common(3):
        print(f"      {ap}: {count} shots")

    print(f"\n{'='*60}")
    if not dry_run:
        print(f" Log saved: {log_file_path.name}")


# --- Critique Workflow ---

def critique_images_in_directory(directory: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """(V7.0) Runs AI "Creative Director" critique on all images"""
    
    print(f"\n{'='*60}")
    print(f" 🎨 PhotoSort --- (AI Critique Mode)")
    print(f"{'='*60}")
    print(f" Running AI Creative Director on: {directory}")
    
    cli_model = parse_model_override()
    if cli_model:
        chosen_model = cli_model
        print(f" ⚠️  Model override via CLI: {chosen_model}")
    else:
        chosen_model = APP_CONFIG.get('critique_model', DEFAULT_CRITIQUE_MODEL)
        print(f" 🤖 Using model: {chosen_model}")
    
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if not image_files:
        print("     No supported images to critique. Exiting.")
        return

    print(f"\n Found {len(image_files)} images to critique.")
    
    if not dry_run:
        confirm = input(f"   Continue? (y/n): ").strip().lower()
        if confirm != 'y':
            print("   Cancelled.")
            return
    
    results = {"success": 0, "failed": 0}
    
    pbar = None
    if TQDM_AVAILABLE:
        pbar = SmartProgressBar(total=len(image_files), desc=" 🎨 Critiquing", unit="img")
    
    for img_path in image_files:
        critique_json = get_ai_critique(img_path, chosen_model)
        
        if critique_json:
            json_filename = img_path.stem + ".json"
            json_path = directory / json_filename
            
            if not dry_run:
                try:
                    with open(json_path, 'w') as f:
                        f.write(critique_json)
                    results["success"] += 1
                except Exception as e:
                    if pbar:
                        pbar.write(f" ❌ Failed to save {json_filename}: {e}")
                    results["failed"] += 1
            else:
                results["success"] += 1
        else:
            results["failed"] += 1
        
        if pbar:
            pbar.update()
    
    if pbar:
        pbar.close()
    
    print(f"\n{'='*60}")
    print(f" ✅ Successfully critiqued: {results['success']}")
    print(f" ❌ Failed: {results['failed']}")
    
    if not dry_run:
        print(f"\n JSON sidecar files saved alongside images.")
    else:
        print(f"\n [PREVIEW] Would save JSON sidecar files alongside images.")


# --- Auto Workflow ---

def auto_workflow(directory: Path, chosen_destination: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """
    (V9.3) Complete automated workflow: Stack → Cull → AI-Name → Archive.
    
    V9.3 ENHANCEMENTS:
    - Clear progress messaging showing already-named vs needs-processing breakdown
    - AI rename logging for all operations
    - Uses Tier A/B/C cull folder naming
    """
    
    print("\n" + "="*60)
    print(" 🚀 PhotoSort --- (Auto Mode)")
    print("="*60)
    print("This will automatically Stack, Cull, AI-Name, and Archive")
    print("all 'hero' photos from this session.")
    
    chosen_model = APP_CONFIG['default_model']
    
    while True:
        print("\n" + "-"*60)
        print(f" ⓘ  Source:      {directory}")
        print(f" ⓘ  Destination: {chosen_destination}")
        print(f" ⓘ  Model:       {chosen_model}")
        
        print("\n Step 1/5: Configuration")
        print(f" 🤖 Current model: {chosen_model}")
        
        loader = ModelLoadingProgress(message="Checking Ollama connection...")
        loader.start()
        available_models = get_available_models()
        loader.stop()
        
        if available_models is None:
            print("\n ❌ FATAL: Could not connect to Ollama server.")
            print("   Please ensure Ollama is running.")
            return

        if available_models:
            print(f"    Available models: {', '.join(available_models)}")

        new_model = input("   Press ENTER to use default, or type a new model name: ").strip()
        if new_model:
            chosen_model = new_model
        print(f"     Using model: {chosen_model}")
        
        print("\n" + "-"*60)
        print(f"   Source:      {directory.name}")
        print(f"   Destination: {chosen_destination.name}")
        print(f"   Model:       {chosen_model}")
        confirm = input(f"\n  Ready to process? (y/n/q): ")
        
        if confirm.lower() == 'q':
            print(get_quit_message())
            return
        elif confirm.lower() == 'y':
            break
    
    tracker = SessionTracker()
    tracker.set_model(chosen_model)
    tracker.add_operation("Burst Stacking")
    tracker.add_operation("Quality Culling")
    tracker.add_operation("AI Naming")

    # Step 2: Stats Preview (read-only)
    print("\n Step 2/5: Analyzing session (read-only)...")
    try:
        show_exif_insights(directory, dry_run=True, APP_CONFIG=APP_CONFIG, max_workers=max_workers)
    except Exception as e:
        print(f"     Could not run EXIF analysis: {e}")

    # Step 3: Group Bursts (V9.2: Now AI-names PICK files!)
    print("\n Step 3/5: Stacking burst shots (with AI naming)...")
    group_bursts_in_directory(directory, dry_run=dry_run, APP_CONFIG=APP_CONFIG, max_workers=max_workers)

    # Step 4: Cull Singles (V9.3: Now uses Tier A/B/C naming)
    print("\n Step 4/5: Culling single shots...")
    cull_images_in_directory(directory, dry_run=dry_run, APP_CONFIG=APP_CONFIG, max_workers=max_workers)

    # V9.3: Check for Tier A folder (was _Keepers)
    tier_a_dir = directory / TIER_A_FOLDER
    if not tier_a_dir.is_dir() or not any(tier_a_dir.iterdir()):
        print(f"\n  Warning: No '{TIER_A_FOLDER}' folder found or it's empty.")
        print("   Cull may have failed or all images were lower tiers.")

    # Step 5: Find and AI-name hero files (V9.3: Enhanced messaging!)
    print("\n Step 5/5: Finding and archiving 'hero' files...")
    
    hero_files = []
    
    # Get Tier A files (was keepers)
    if tier_a_dir.is_dir():
        for f in tier_a_dir.iterdir():
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                hero_files.append(f)
    
    # Get picks from bursts
    burst_parent = directory / "_Bursts"
    if burst_parent.exists() and burst_parent.is_dir():
        burst_folders = [f for f in burst_parent.iterdir() if f.is_dir()]
    else:
        burst_folders = list(directory.glob("burst-*/"))
    
    for burst_folder in burst_folders:
        if burst_folder.is_dir():
            for f in burst_folder.iterdir():
                if f.is_file() and (f.name.startswith(BEST_PICK_PREFIX) or is_already_ai_named(f.name)):
                    hero_files.append(f)

    if not hero_files:
        print(f"\n  No '{TIER_A_FOLDER}' or '_PICK_' files found. Nothing to archive.")
        print("   Auto workflow complete.")
        return

    # === V9.3: ENHANCED PROGRESS MESSAGING ===
    already_named = [f for f in hero_files if is_already_ai_named(f.name)]
    needs_naming = [f for f in hero_files if not is_already_ai_named(f.name)]
    
    print(f"   Found {len(hero_files)} 'hero' files total:")
    if already_named:
        print(f"     • {len(already_named)} already AI-named (from burst stacking)")
    print(f"     • {len(needs_naming)} to process")
    # === END V9.3 ENHANCEMENT ===
    
    total_size_before = 0
    for f in hero_files:
        try:
            total_size_before += f.stat().st_size
        except Exception:
            pass
    tracker.add_size_before(total_size_before)
    
    results = {"success": [], "failed": []}
    
    # v9.3: Initialize rename log
    rename_log_path = chosen_destination / f"_ai_rename_log_{SESSION_TIMESTAMP}.txt"
    if not dry_run:
        initialize_rename_log(rename_log_path)
    
    pbar = None
    if TQDM_AVAILABLE:
        pbar = SmartProgressBar(total=len(hero_files), desc=" 🤖 Archiving", unit="img")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_image, img_path, chosen_destination, chosen_model, dry_run, rename_log_path): img_path 
            for img_path in hero_files
        }
        
        for future in as_completed(future_to_file):
            original, success, message, description = future.result()
            
            if success:
                results["success"].append({
                    "original": original.name,
                    "new_name": message,
                    "description": description
                })
                try:
                    file_size = original.stat().st_size
                    tracker.record_image(file_size, success=True)
                    tracker.add_size_after(file_size)
                except Exception:
                    pass
            else:
                results["failed"].append((original.name, message))
                tracker.record_image(0, success=False)
                if pbar:
                    pbar.write(f" ❌ {original.name}: {message}")
            
            if pbar:
                pbar.update()
    
    if pbar:
        pbar.close()
        
    print(f"\n{'='*60}")
    print(f" ✅ Successfully archived: {len(results['success'])}")
    print(f" ❌ Failed to archive: {len(results['failed'])}")

    if results["success"]:
        categories = {}
        for item in results["success"]:
            cat = categorize_description(item["description"])
            categories[cat] = categories.get(cat, 0) + 1
        
        session_name = generate_ai_session_name(categories, chosen_model)
        
        if session_name and len(session_name) > 2:
            dated_folder = f"{SESSION_DATE}_{session_name}"
            print(f"\n   🎨 AI Session Name: {dated_folder}")
        else:
            dated_folder = f"{SESSION_DATE}_Session"
        
        final_destination = chosen_destination / dated_folder
        final_destination.mkdir(parents=True, exist_ok=True)
        tracker.set_destination(final_destination)
        
        organize_into_folders(results["success"], chosen_destination, final_destination, dry_run=False)

    print("\n" + "="*60)
    print(" 🚀 AUTO WORKFLOW COMPLETE")
    print("="*60)
    print(f" Your 'hero' photos are now in: {chosen_destination}")
    print(f"  Remaining files are in: {directory}")
    if not dry_run:
        print(f" 📝 Rename log saved: {rename_log_path.name}")

    # v7.1: Print session summary
    print("\n")
    tracker.print_summary()
    tracker.save_to_history(APP_CONFIG['history_path'])

# --- Legacy Ingest Workflow ---

def run_default_ingest(current_dir: Path, dry_run: bool, APP_CONFIG: dict):
    """(V7.1) Runs the original V4.1 AI-powered ingest process"""
    
    print(f"\n{'='*60}")
    print(f" 🤖 PhotoSort --- (Legacy Ingest Mode)")
    print(f"{'='*60}")
    
    print(" ⓘ  Legacy mode selected. Please choose source and destination.")
    source, destination = get_source_and_destination(APP_CONFIG)
    if not source or not destination:
        print(get_quit_message())
        return
    
    update_config_paths(APP_CONFIG, CONFIG_FILE_PATH, str(source), str(destination))

    print(f"\n 🤖 Default model: {APP_CONFIG['default_model']}")
    
    loader = ModelLoadingProgress(message="Checking Ollama connection...")
    loader.start()
    available_models = get_available_models()
    loader.stop()

    if available_models:
        print(f"   Available models: {', '.join(available_models)}")

    new_model = input("   Press ENTER to use default, or type a model name: ").strip()
    chosen_model = new_model if new_model else APP_CONFIG['default_model']
    
    print(f"\n Source: {source}")
    print(f" Destination: {destination}")
    print(f" Model: {chosen_model}")
    response = input(f"\n  Ready to process {source.name}? (y/n/q): ")
    
    if response.lower() == 'q':
        print(get_quit_message())
        return
    elif response.lower() != 'y':
        print("Cancelled.")
        return
    
    process_directory(source, destination, chosen_model, dry_run)


# ==============================================================================
# IX. MAIN ENTRY POINT
# ==============================================================================

def main():
    """Main entry point with smart banner system"""
    
    check_dcraw()
    
    APP_CONFIG = load_app_config()

    current_dir = Path.cwd()
    args = set(sys.argv[1:])
    
    dry_run = "--preview" in args or "-p" in args
    
    DISPATCH_TABLE = {
        '--auto': (auto_workflow, V5_LIBS_AVAILABLE and V6_CULL_LIBS_AVAILABLE, V5_LIBS_MSG if not V5_LIBS_AVAILABLE else V6_LIBS_MSG, "animated"),
        '--group-bursts': (group_bursts_in_directory, V5_LIBS_AVAILABLE, V5_LIBS_MSG, "animated"),
        '-b': (group_bursts_in_directory, V5_LIBS_AVAILABLE, V5_LIBS_MSG, "animated"),
        '--cull': (cull_images_in_directory, V6_CULL_LIBS_AVAILABLE, V6_LIBS_MSG, "animated"),
        '-c': (cull_images_in_directory, V6_CULL_LIBS_AVAILABLE, V6_LIBS_MSG, "animated"),
        '--prep': (prep_smart_export, V6_CULL_LIBS_AVAILABLE, V6_LIBS_MSG, "animated"),
        '--pe': (prep_smart_export, V6_CULL_LIBS_AVAILABLE, V6_LIBS_MSG, "animated"),
        '--stats': (show_exif_insights, V6_4_EXIF_LIBS_AVAILABLE, V6_4_LIBS_MSG, "animated"),
        '--exif': (show_exif_insights, V6_4_EXIF_LIBS_AVAILABLE, V6_4_LIBS_MSG, "animated"),
        '--critique': (critique_images_in_directory, V5_LIBS_AVAILABLE, V5_LIBS_MSG, "animated"),
        '--art': (critique_images_in_directory, V5_LIBS_AVAILABLE, V5_LIBS_MSG, "animated"),
    }
    
    cli_model = parse_model_override()
    clean_args = args - {"--preview", "-p", "--model"}
    if cli_model:
        clean_args = clean_args - {cli_model}
    
    command_to_run = None
    for flag in clean_args:
        if flag in DISPATCH_TABLE:
            command_to_run = flag
            break
    
    if command_to_run == '--auto':
        show_banner("animated")
        
        if COLORAMA_AVAILABLE:
            print(f"{Fore.CYAN}{Style.BRIGHT}  Mantra: Stats → Stack → Cull → Critique{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  💡 Pro-tip: Copy media to local storage before running for best performance{Style.RESET_ALL}\n")
        else:
            print("  Mantra: Stats → Stack → Cull → Critique")
            print("  💡 Pro-Loop: Copy media to local storage before running for best performance\n")
        
        if dry_run:
            print("="*60)
            if COLORAMA_AVAILABLE:
                print(f"{Fore.YELLOW}{Style.BRIGHT}  🔍 DRY RUN: AUTO WORKFLOW PREVIEW MODE{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}  NO FILES WILL BE MOVED/COPIED/WRITTEN{Style.RESET_ALL}")
            else:
                print("  🔍 DRY RUN: AUTO WORKFLOW PREVIEW MODE")
                print("  NO FILES WILL BE MOVED/COPIED/WRITTEN")
            print("="*60 + "\n")
        
        source, destination = get_source_and_destination(APP_CONFIG)
        if not source or not destination:
            print(get_quit_message())
            return
        
        update_config_paths(APP_CONFIG, CONFIG_FILE_PATH, str(source), str(destination))
        
        auto_workflow(source, destination, dry_run, APP_CONFIG)

    elif command_to_run:
        (func_to_call, libs_ok, lib_msg, banner_mode) = DISPATCH_TABLE[command_to_run]
        
        show_banner(banner_mode)
        
        if not libs_ok:
            print(lib_msg)
            return
            
        if dry_run:
            print("\n" + "="*60)
            print(f"  DRY RUN: {command_to_run.upper()} PREVIEW MODE")
            print(" NO FILES WILL BE MOVED/COPIED/WRITTEN")
            print("="*60)
        
        func_to_call(current_dir, dry_run, APP_CONFIG)

    else:
        if "--help" in args or "-h" in args:
            show_banner("animated")
            print("\n 🖼️  PhotoSort - Usage")
            print(f"\n Config file loaded from: {CONFIG_FILE_PATH} (if it exists)")
            print("\nCommands:")
            print("  --auto           : (RECOMMENDED) Full automated workflow: Stack → Cull → AI-Archive")
            print("  <no command>     : (Legacy) AI Ingest on ALL files in selected directory")
            print("\nManual Tools:")
            print("  --critique, --art: (V7.0) Run AI 'Creative Director' on a folder, save .json sidecars")
            print("  --stats, --exif  : Display EXIF insights dashboard")
            print("  --group-bursts, -b : Stack visually similar burst shots, mark best pick")
            print("  --cull, -c       : Sort images into _Tier_A, _Tier_B, _Tier_C")
            print("  --prep, --pe     : Find 'Tier A' images and copy to _ReadyForLightroom")
            print("\nOptions:")
            print("  --preview, -p    : Dry run mode (no files moved/copied/written)")
            print("  --model <n>   : Override config model (for --critique only)")
            print("  --help, -h       : Show this help message")
            
            if not TQDM_AVAILABLE:
                print("\n Tip: Install tqdm for progress bars: pip3 install tqdm")
            if not COLORAMA_AVAILABLE:
                print("\n Tip: Install colorama for animated banner: pip3 install colorama")
            return

        show_banner("animated")
        
        if dry_run:
            print("\n" + "="*60)
            print(" DRY RUN: LEGACY INGEST PREVIEW MODE")
            print(" NO FILES WILL BE MOVED")
            print("="*60)
        
        run_default_ingest(current_dir, dry_run, APP_CONFIG)
    
    if dry_run and command_to_run not in ('--auto',):
        print("\n" + "="*60)
        print(" DRY RUN COMPLETE - NO FILES WERE MOVED/COPIED/WRITTEN")
        print("="*60)
    else:
        print("\n Done!\n")


if __name__ == "__main__":
    main()
