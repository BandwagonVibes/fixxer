#!/usr/bin/env python3
"""
PhotoSort v8.0 - AI-Powered Photography Workflow Automation

Created by: Nick (∞vision crew)
Engineered by: Claude (Anthropic) + Gemini (Google)

Features:
- Auto Mode: Complete automated workflow (Stack → Cull → AI-Name → Archive)
- AI Critique: Creative Director analysis with JSON sidecars
- Burst Stacking: v8.0 CLIP semantic grouping (deterministic, robust)
- Quality Culling: v8.0 BRISQUE+VLM cascade (bokeh-aware)
- EXIF Insights: Session analytics dashboard
- Smart Prep: Copy keepers to Lightroom folder

Tech Stack:
- Local AI via Ollama (minicpm-v2.6 for perfect JSON)
- CLIP embeddings (sentence-transformers)
- BRISQUE quality assessment (image-quality)
- DBSCAN clustering (scikit-learn)
- RAW support via dcraw (macOS)
- Config file: ~/.photosort.conf

Version History:
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
from datetime import datetime
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
    # v7.1 GM 3.0: We now in-line SmartProgressBar, so this import is removed
    # from smart_progress import SmartProgressBar, ModelLoadingProgress 
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
# This replaces the external smart_progress.py module
class SmartProgressBar(tqdm):
    """
    tqdm wrapper with an independent, threaded phrase rotator.
    Rotates phrases every 15 seconds in bright red.
    """
    def __init__(self, *args, rotation_interval: int = 15, **kwargs):
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
        # Set description *before* update to avoid flicker
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
    - Scanline wipedown effect on ASCII art (like old CRT monitors)
    - Simple text fade-in (no complex flickering to avoid duplication)
    - Plays once at startup
    """
    
    width = get_terminal_width()
    
    # The ASCII art - each line as a string
    vision_crew_art = [
        "██    ██ ██ ███████ ██  ██████  ███    ██   ██████ ██████  ███████ ██    ██ ",
        "██    ██ ██ ██      ██ ██    ██ ████   ██  ██      ██   ██ ██      ██    ██ ",
        "██    ██ ██ ███████ ██ ██    ██ ██ ██  ██  ██      ██████  █████   ██ █  ██ ",
        " ██  ██  ██      ██ ██ ██    ██ ██  ██ ██  ██      ██   ██ ██      ████  ██ ",
        "  ████   ██ ███████ ██  ██████  ██   ████   ██████ ██   ██ ███████ ██ ██ ██ "
    ]
    
    # Split point to separate "VISION" from "CREW" for coloring
    split_point = 40
    
    # Text lines (no box, just text)
    text_lines = [
        "PHOTOSORT v7.1 - AI Ingestion Engine",
        "cracked by vision crew | serial: 1989-IMG",
        "",  # Empty line for spacing
        "use responsibly.",
        "unleash creatively.",
        "inference locally."
    ]
    
    clear_console()
    
    if COLORAMA_AVAILABLE:
        # =================================================================
        # SCANLINE WIPEDOWN EFFECT
        # =================================================================
        # Simulate old CRT monitor scanlines drawing the ASCII art
        
        for line in vision_crew_art:
            vision_part = line[:split_point]
            crew_part = line[split_point:]
            
            # Combine with colors: VISION=white, CREW=red
            colored_line = f"{Fore.WHITE}{Style.BRIGHT}{vision_part}{Fore.RED}{Style.BRIGHT}{crew_part}{Style.RESET_ALL}"
            print(colored_line.center(width))
            time.sleep(0.08)  # Scanline speed
        
        print()  # Space after ASCII art
        
        # =================================================================
        # TEXT FADE-IN (SIMPLE VERSION - NO FLICKER)
        # =================================================================
        # Just type out the text line by line
        
        left_pad = (width - 40) // 2
        for i, line in enumerate(text_lines):
            if line == "":
                print()
            elif i < 2:
                # First two lines: centered, bright red, instant
                print(f"{Fore.RED}{Style.BRIGHT}{line}{Style.RESET_ALL}".center(width))
            else:
                # Last three lines: left-aligned, typing effect
                print(f"{' ' * left_pad}{Fore.RED}{Style.BRIGHT}{line}{Style.RESET_ALL}")
                time.sleep(0.15)  # Pause between typed lines
        
    else:
        # =================================================================
        # FALLBACK: NO COLORAMA - STATIC DISPLAY
        # =================================================================
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
    
    print()  # Final padding

def print_static_banner():
    """
    Static VISIONCREW banner (no animation)
    Used when colorama is unavailable or for quick commands
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
        "PHOTOSORT v7.1 - AI Ingestion Engine",
        "cracked by vision crew | serial: 1989-IMG",
        "",
        "use responsibly.",
        "unleash creatively.",
        "inference locally."
    ]
    
    clear_console()
    
    if COLORAMA_AVAILABLE:
        # Static colored version (no box)
        for line in vision_crew_art:
            vision_part = line[:split_point]
            crew_part = line[split_point:]
            colored_line = f"{Fore.WHITE}{Style.BRIGHT}{vision_part}{Fore.RED}{Style.BRIGHT}{crew_part}{Style.RESET_ALL}"
            print(colored_line.center(width))
        
        print()
        
        # Print text without box
        left_pad = (width - 40) // 2
        for i, line in enumerate(text_lines):
            if line == "":
                print()
            elif i < 2:
                print(f"{Fore.RED}{Style.BRIGHT}{line}{Style.RESET_ALL}".center(width))
            else:
                print(f"{' ' * left_pad}{Fore.RED}{Style.BRIGHT}{line}{Style.RESET_ALL}")
    else:
        # Plain text fallback (no box)
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
    - mode="animated": Full warez animation (DEFAULT - for all commands!)
    - mode="quick": Static banner (legacy option, rarely used)
    """
    if mode == "animated" and COLORAMA_AVAILABLE:
        try:
            print_visioncrew_animated()
        except Exception as e:
            # If animation fails, fall back to static
            print(f"--- PHOTOSORT v7.1 --- (Animation failed: {e})")
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
DEFAULT_MODEL_NAME = "minicpm-v2.6"

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
DEFAULT_CRITIQUE_MODEL = "openbmb/minicpm-v2.6:q4_K_M"

DEFAULT_CULL_THRESHOLDS = {
    'sharpness_good': 40.0,
    'sharpness_dud': 15.0,
    'exposure_dud_pct': 0.20,
    'exposure_good_pct': 0.05
}
DEFAULT_BURST_THRESHOLD = 8
CONFIG_FILE_PATH = Path.home() / ".photosort.conf"

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
RAW_SUPPORT = False  # Will be set to True by check_dcraw()

MAX_WORKERS = 5
INGEST_TIMEOUT = 60   # seconds per image
CRITIQUE_TIMEOUT = 120  # seconds per image (V7.0)

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
    Returns None if Ollama is unavailable (fail-fast check).
    """
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
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
    Returns model name or None
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
        
        # Use dcraw to convert RAW to PPM (in memory)
        result = subprocess.run(
            ['dcraw', '-c', '-w', '-q', '3', str(raw_path)],
            capture_output=True,
            check=True
        )
        
        # Write PPM to a temp file
        with tempfile.NamedTemporaryFile(suffix='.ppm', delete=False) as ppm_tmp:
            ppm_tmp.write(result.stdout)
            ppm_file = ppm_tmp.name
        
        # Use sips to convert PPM to JPEG (macOS specific)
        subprocess.run(
            ['sips', '-s', 'format', 'jpeg', ppm_file, '--out', tmp_jpg],
            capture_output=True,
            check=True
        )
        
        with open(tmp_jpg, 'rb') as f:
            jpeg_bytes = f.read()
        
        # Clean up temp files
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

def format_duration(duration: datetime.timedelta) -> str:
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
# VI. CONFIGURATION LOGIC
# ==============================================================================

def load_app_config() -> Dict[str, Any]:
    """
    V7.0: Loads settings from ~/.photosort.conf
    Uses hardcoded defaults as fallbacks.
    GOLD: Crash-proof with .get() fallbacks for all values.
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

    # Burst threshold
    config['burst_threshold'] = parser.getint(
        'burst', 'similarity_threshold',
        fallback=DEFAULT_BURST_THRESHOLD
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

def get_ai_description(image_path: Path, model_name: str) -> Optional[str]:
    """(V4.0) Get filename suggestion from vision model"""
    base64_image = encode_image(image_path)
    if not base64_image:
        return None
    
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "What is in this image? Describe it concisely for a file name.",
                "images": [base64_image]
            }
        ],
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=INGEST_TIMEOUT)
        response.raise_for_status()
        
        result = response.json()
        description = result['message']['content'].strip()
        
        return description
        
    except requests.exceptions.Timeout:
        print(f"  Timeout processing {image_path.name}")
        return None
    except Exception as e:
        print(f" Error processing {image_path.name}: {e}")
        return None

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
        "format": "json"  # Force JSON output if model supports it
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

def get_image_hash(image_path: Path) -> Optional[tuple[Path, imagehash.ImageHash]]:
    """
    Calculates perceptual hash (visual fingerprint) of an image.
    V6.5: Simplified RAW thumbnail extraction.
    """
    if image_path.suffix.lower() in ['.rw2', '.cr2', '.nef', '.arw', '.dng']:
        try:
            # Extract embedded JPEG thumbnail directly
            result = subprocess.run(
                ['dcraw', '-e', '-c', str(image_path)],
                capture_output=True,
                check=True
            )
            # PIL can read JPEG from memory
            img = Image.open(BytesIO(result.stdout))
            return image_path, imagehash.phash(img)
        except Exception:
            return image_path, None
           
    # For regular JPG/PNG files
    try:
        with Image.open(image_path) as img:
            return image_path, imagehash.phash(img)
    except Exception as e:
        print(f"     Skipping hash for {image_path.name}: {e}")
        return image_path, None

def analyze_image_quality(image_bytes: bytes) -> Dict[str, float]:
    """
    Analyzes image bytes for sharpness and exposure.
    Core engine reused by cull, burst, and prep features.
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

        # Sharpness (Laplacian variance)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        scores['sharpness'] = float(laplacian_var)

        # Exposure (histogram for clipped pixels)
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
    V6.4.2: Intelligently calculates aperture ratios.
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
    V6.5: Helper function to get destination and model from user.
    V7.0: Reads defaults from APP_CONFIG.
    Returns (destination_path, model_name).
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
    
    # v7.1 GM 3.0: Add model loading spinner
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

def process_single_image(image_path: Path, destination_base: Path, model_name: str, dry_run: bool) -> Tuple[Path, bool, str, str]:
    """Process one image: get description, rename, move to temp location"""
    try:
        description = get_ai_description(image_path, model_name)
        if not description:
            return image_path, False, "Failed to get AI description", ""
        
        clean_name = clean_filename(description)
        if not clean_name:
            clean_name = f"image-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        extension = image_path.suffix.lower()
        new_path = get_unique_filename(clean_name, extension, destination_base)
        
        if not dry_run:
            shutil.move(str(image_path), str(new_path))
        
        return image_path, True, new_path.name, description
        
    except Exception as e:
        return image_path, False, str(e), ""

def organize_into_folders(processed_files: List[Dict], files_source: Path, destination_base: Path, dry_run: bool):
    """
    Group files into folders based on their descriptions.
    v7.1 (Patched): Accepts `files_source` to know where files *are*,
    and `destination_base` to know where they *should go*.
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
    
    # v7.1: We are now organizing into a dated_session folder,
    # so the folder_name is just the category.
    for category, files in categories.items():
        # folder_name = f"{SESSION_DATE}_{category}" # v7.0 logic
        folder_name = category # v7.1 logic
        folder_path = destination_base / folder_name
        
        if not dry_run:
            folder_path.mkdir(exist_ok=True)
        
        print(f" {folder_name}/ ({len(files)} files)")
        
        for file_info in files:
            # v7.1 (Patched): Use `files_source` for source path
            src = files_source / file_info['filename']
            dst = folder_path / file_info['filename']
            
            if not dry_run:
                if src.exists():
                    shutil.move(str(src), str(dst))
                else:
                    # This case can happen if files were processed to a temp dir
                    # that's different from the final root.
                    print(f"   [WARN] Source file not found: {src}")
            else:
                print(f"   [PREVIEW] Would move {file_info['filename']} here")
    
    print(f"\n Organized into {len(categories)} folders")

def generate_ai_session_name(categories: Dict[str, int], model_name: str) -> Optional[str]:
    """
    v7.1: Generate AI-powered session name based on image categories.
    
    Args:
        categories: Dict of category names to image counts
        model_name: AI model to use for naming
    
    Returns:
        AI-generated session name or None if failed
    """
    if not categories:
        return None
    
    # Build category breakdown for prompt
    category_list = [f"- {cat}: {count} images" for cat, count in categories.items()]
    category_text = "\n".join(category_list)
    
    prompt = f"""You are an expert photography curator organizing a photo collection.

Analyze the photo categories and counts provided, then follow these steps *in order*:

1. **Identify the Dominant Theme:**
   - What is the primary subject matter? (e.g., architecture, portraits, nature)
   - What secondary themes are present?

2. **Determine the Creative Mood:**
   - What style or atmosphere connects these images? (e.g., urban, moody, minimalist, colorful)

3. **Generate Session Title:**
   - Create a concise 2-4 word title that captures both theme and mood
   - Use descriptive, photographic language
   - Examples: "Urban Geometry Study", "Golden Hour Portraits", "Moody Street Life"

Categories in this session:
{category_text}

Respond with ONLY the final title on a single line, no explanation.
Session Title:"""
    
    try:
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        title = result['message']['content'].strip()
        
        # Clean up the title
        title = title.replace('"', '').replace("'", "")
        title = title.replace("Session Title:", "").strip()
        
        # Sanitize for filesystem
        title = util_sanitize(title, max_length=50)
        
        return title if title else None
        
    except Exception as e:
        return None

def process_directory(directory: Path, destination_base: Path, model_name: str, dry_run: bool, max_workers: int = MAX_WORKERS):
    """(DEFAULT MODE) Process all images with AI, rename, and organize"""
    
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if not image_files:
        print(f"  No supported image files found in {directory}")
        print(f"   Looking for: {', '.join(SUPPORTED_EXTENSIONS)}")
        return
    
    print(f"\n Found {len(image_files)} images to process")
    print(f" Destination: {destination_base}")
    print(f" Model: {model_name}")
    print(f"  Using {max_workers} concurrent workers")
    if RAW_SUPPORT:
        print(" 📸 RAW support enabled (dcraw)")
    print(f"{'='*60}\n")
    
    results = {"success": [], "failed": []}
    
    # v7.1 (Patched): Use SmartProgressBar
    pbar = None
    if TQDM_AVAILABLE:
        pbar = SmartProgressBar(total=len(image_files), desc=" 🤖 Processing images", unit="img")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_image, img, destination_base, model_name, dry_run): img 
            for img in image_files
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
                else:
                    print(f" ❌ {original.name}: {message}")
            
            if pbar:
                pbar.update() # Use pbar.update() to trigger phrase rotation
    
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
        # v7.1: Legacy mode also gets AI session naming
        categories = {}
        for item in results["success"]:
            cat = categorize_description(item["description"])
            categories[cat] = categories.get(cat, 0) + 1
        
        session_name = generate_ai_session_name(categories, model_name)
        
        # v7.1 (Patched): Stronger check for valid AI name
        if session_name and len(session_name) > 2:
            dated_folder = f"{SESSION_DATE}_{session_name}"
            print(f"\n   🎨 AI Session Name: {dated_folder}")
        else:
            dated_folder = f"{SESSION_DATE}_Session"
        
        final_destination = destination_base / dated_folder
        final_destination.mkdir(parents=True, exist_ok=True)
        
        # v7.1 (Patched): Pass correct source and destination paths
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
    else:
        print(f"\n[PREVIEW] Would save log file to: {log_file.name}")

# --- Burst Workflow ---

def group_bursts_in_directory(directory: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """
    (V6.2) Finds and groups visually similar images into subfolders
    and renames the sharpest file in the burst.
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


    print(f"\n Stacking {len(all_burst_groups)} burst groups...")
    
    for i, group in enumerate(all_burst_groups):
        folder_name = f"burst-{i+1:03d}"
        folder_path = directory / folder_name
        
        print(f"\n {folder_name}/ ({len(group)} files)")
        
        if not dry_run:
            folder_path.mkdir(exist_ok=True)
            
        winner_data = best_picks.get(i)
        
        for file_path in group:
            if winner_data and file_path == winner_data[0]:
                new_name = f"{BEST_PICK_PREFIX}{file_path.name}"
            else:
                new_name = file_path.name
                
            new_file_path = folder_path / new_name
            
            if not dry_run:
                try:
                    shutil.move(str(file_path), str(new_file_path))
                    print(f"    Moved {file_path.name} → {new_name}")
                except Exception as e:
                    print(f"    FAILED to move {file_path.name}: {e}")
            else:
                if winner_data and file_path == winner_data[0]:
                    print(f"   [PREVIEW] Would move and RENAME {file_path.name} to {new_name}")
                else:
                    print(f"   [PREVIEW] Would move {file_path.name} to {folder_name}/")

    print("\n Burst stacking complete!")

# --- Cull Workflow ---

def process_image_for_culling(image_path: Path) -> Tuple[Path, Optional[Dict[str, float]]]:
    """Thread-pool worker: Gets bytes and runs analysis engine"""
    image_bytes = get_image_bytes_for_analysis(image_path)
    if not image_bytes:
        return image_path, None
    
    scores = analyze_image_quality(image_bytes)
    return image_path, scores

def cull_images_in_directory(directory: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """(V6.0) Finds and groups images by technical quality"""
    
    print(f"\n{'='*60}")
    print(f" 🗑️  PhotoSort --- (Cull Mode)")
    print(f"{'='*60}")
    print(f" Analyzing technical quality in: {directory}")

    algorithm = APP_CONFIG.get('cull_algorithm', 'legacy')
    
    if algorithm == 'brisque' and V8_AVAILABLE:
        print(f" ✓ Using v8.0 BRISQUE+VLM cascade")
        print(f"   Keeper: <{APP_CONFIG.get('cull_brisque_keeper', 35.0)}, Ambiguous: >{APP_CONFIG.get('cull_brisque_ambiguous', 50.0)}")
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
    tiers = {"Good": [], "Maybe": [], "Dud": []}
    log_data = []

    for path, scores in all_scores.items():
        sharp = scores['sharpness']
        blacks = scores['blacks_pct']
        whites = scores['whites_pct']
        
        is_exposure_bad = (blacks > th['exposure_dud_pct']) or (whites > th['exposure_dud_pct'])
        is_exposure_good = (blacks < th['exposure_good_pct']) and (whites < th['exposure_good_pct'])
        is_sharp_bad = sharp < th['sharpness_dud']
        is_sharp_good = sharp > th['sharpness_good']

        tier = "Maybe"
        if is_sharp_bad or is_exposure_bad:
            tier = "Dud"
        elif is_sharp_good and is_exposure_good:
            tier = "Good"
        
        tiers[tier].append(path)
        log_data.append({
            'file': path.name,
            'tier': tier,
            'sharpness': round(sharp, 2),
            'blacks_pct': round(blacks, 4),
            'whites_pct': round(whites, 4)
        })

    print(f"\n Found {len(tiers['Good'])} Keepers, {len(tiers['Maybe'])} Maybes, and {len(tiers['Dud'])} Duds.")
    
    folder_map = {
        "Good": directory / "_Keepers",
        "Maybe": directory / "_Review_Maybe",
        "Dud": directory / "_Review_Duds"
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
    print(f" Finding 'Keepers' to copy to: {PREP_FOLDER_NAME}/")
    
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

    print("\n  Finding 'Good' tier images...")
    
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
        print("\n No 'Keepers' found that meet the 'Good' tier criteria.")
        print("   (Try adjusting CULL_THRESHOLDS in ~/.photosort.conf if this seems wrong)")
        return

    print(f"\n Found {len(good_files)} 'Keepers' to copy.")
    
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
    for camera, count in camera_counter.most_common(3):
        print(f"      • {camera}: {count}")

    print("\n    Focal Lengths (Composition):")
    for focal, count in focal_len_counter.most_common(3):
        print(f"      • {focal}: {count}")
        
    print("\n    Apertures (Depth of Field):")
    for aperture, count in aperture_counter.most_common(3):
        print(f"      • {aperture}: {count}")

    print(f"\n{'='*60}")
    print(f" Summary saved to: {log_file_path.name}")

# --- Critique Workflow (V7.0) ---

def critique_images_in_directory(directory: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """
    (V7.0) Generates artistic critiques for images.
    Saves JSON sidecar files next to each image.
    GOLD: Implemented --dry-run, --model override, and model availability check.
    """
    
    print("\n" + "="*60)
    print(" 🎨 PhotoSort --- (AI Critic Mode)")
    print("="*60)
    
    # GOLD: Use centralized CLI argument parser
    cli_model_override = parse_model_override()
    model_name = cli_model_override or APP_CONFIG['critique_model']
    
    print(f" Analyzing images in: {directory}")
    if cli_model_override:
        print(f" ⓘ  Overriding config with CLI model: {model_name}")
    else:
        print(f" Using Creative Director model: {model_name}")
    
    # Model availability check
    loader = ModelLoadingProgress(message="Checking Ollama connection...")
    loader.start()
    available_models = get_available_models()
    loader.stop()
    
    if available_models and model_name not in available_models:
        print(f"\n ⚠️  Warning: Model '{model_name}' not found in 'ollama list'.")
        print(f"   Available: {', '.join(available_models)}")
        confirm = input("   Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return
    elif available_models is None:
        print("\n ❌ FATAL: Could not connect to Ollama server.")
        print("   Please ensure Ollama is running.")
        return

    print(f" Output: .json sidecar files (e.g., photo.json)")
    
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if not image_files:
        print("     No supported images to analyze. Exiting.")
        return

    # Find files that *don't* have a .json sidecar yet
    files_to_critique = []
    for f in image_files:
        if not f.with_suffix('.json').exists():
            files_to_critique.append(f)
    
    if not files_to_critique:
        print(f"\n All {len(image_files)} images already have .json critiques. All done!")
        return

    print(f"\n Found {len(files_to_critique)} new images to critique (skipping {len(image_files) - len(files_to_critique)} already done).")
    
    # Dry-run support
    if dry_run:
        print("\n [PREVIEW] Would analyze the following files:")
        for f in files_to_critique:
            print(f"   • {f.name}")
        print("\n [PREVIEW] Dry run complete. No critiques were generated.")
        return

    results = {"success": 0, "failed": 0, "invalid_json": 0}
    
    pbar = None
    if TQDM_AVAILABLE:
        pbar = SmartProgressBar(total=len(files_to_critique), desc=" 🎨 Critiquing", unit="img")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(get_ai_critique, img_path, model_name): img_path 
            for img_path in files_to_critique
        }
        
        for future in as_completed(future_to_file):
            img_path = future_to_file[future]
            json_string = future.result()
            json_path = img_path.with_suffix('.json')

            if not json_string:
                results["failed"] += 1
                if pbar:
                    pbar.write(f" ❌ {img_path.name}: Failed (No response from model)")
                continue

            try:
                # Clean up potential markdown fences
                if json_string.startswith("```json"):
                    json_string = json_string.strip("```json\n")
                if json_string.endswith("```"):
                    json_string = json_string.strip("```\n")
                
                # Validate JSON
                data = json.loads(json_string) 
                
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                results["success"] += 1

            except json.JSONDecodeError:
                results["invalid_json"] += 1
                if pbar:
                    pbar.write(f" ❌ {img_path.name}: Failed (Model returned invalid JSON)")
                # Save the bad response for debugging
                with open(img_path.with_suffix('.bad.json'), 'w') as f:
                    f.write(json_string)
            except Exception as e:
                results["failed"] += 1
                if pbar:
                    pbar.write(f" ❌ {img_path.name}: Failed ({e})")

            if pbar:
                pbar.update()

    if pbar:
        pbar.close()

    print(f"\n{'='*60}")
    print(" 🎨 Critique Complete")
    print(f"   Successfully generated: {results['success']}")
    print(f"   Invalid JSON returned:  {results['invalid_json']}")
    print(f"   Failed (no response):   {results['failed']}")
    print("="*60)
    print(f" JSON sidecar files are saved in: {directory}")

# --- Auto-Workflow (The "One-Button" Tool) ---

def auto_workflow(directory: Path, chosen_destination: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """
    (V6.5) Fully automated workflow: Stack → Cull → AI-Name → Archive.
    (V7.1) Refactored to accept destination path, use SessionTracker
    (V7.1 GM 3.1) Patched UX loop, phrase bars, and stats tracking
    """
    
    print("\n" + "="*60)
    print(" 🚀 PhotoSort --- (Auto Mode)")
    print("="*60)
    print("This will automatically Stack, Cull, AI-Name, and Archive")
    print("all 'hero' photos from this session.")
    
    # v7.1 (Patched): New UX loop for confirmation
    chosen_model = APP_CONFIG['default_model'] # Start with default
    
    while True:
        print("\n" + "-"*60)
        print(f" ⓘ  Source:      {directory}")
        print(f" ⓘ  Destination: {chosen_destination}")
        print(f" ⓘ  Model:       {chosen_model}")
        
        print("\n Step 1/5: Configuration")
        print(f" 🤖 Current model: {chosen_model}")
        
        # v7.1 GM 3.0: Add model loading spinner
        loader = ModelLoadingProgress(message="Checking Ollama connection...")
        loader.start()
        available_models = get_available_models()
        loader.stop()
        
        if available_models is None:
            print("\n ❌ FATAL: Could not connect to Ollama server.")
            print("   Please ensure Ollama is running.")
            return # Use return, not sys.exit

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
            break # Confirmed, break loop and proceed
        # 'n' will just loop again, re-prompting for the model
    
    # Initialize session tracker (moved after loop)
    tracker = SessionTracker()
    tracker.set_model(chosen_model)
    # v7.1 GM 3.1: SURGICAL FIX - REMOVED STATS CALLS
    # tracker.set_source(directory)  # v7.1 GM 3.0: Track source
    tracker.add_operation("Burst Stacking")
    tracker.add_operation("Quality Culling")
    tracker.add_operation("AI Naming")

    # Step 2: Stats Preview (read-only)
    print("\n Step 2/5: Analyzing session (read-only)...")
    try:
        show_exif_insights(directory, dry_run=True, APP_CONFIG=APP_CONFIG, max_workers=max_workers)
    except Exception as e:
        print(f"     Could not run EXIF analysis: {e}")

    # Step 3: Group Bursts
    print("\n Step 3/5: Stacking burst shots...")
    group_bursts_in_directory(directory, dry_run=False, APP_CONFIG=APP_CONFIG, max_workers=max_workers)

    # Step 4: Cull Singles
    print("\n Step 4/5: Culling single shots...")
    cull_images_in_directory(directory, dry_run=False, APP_CONFIG=APP_CONFIG, max_workers=max_workers)

    # V6.5 VALIDATION: Check if we have any keepers
    keepers_dir = directory / "_Keepers"
    if not keepers_dir.is_dir() or not any(keepers_dir.iterdir()):
        print("\n  Warning: No '_Keepers' folder found or it's empty.")
        print("   Cull may have failed or all images were duds.")

    # Step 5: Find and AI-name hero files
    print("\n Step 5/5: Finding and archiving 'hero' files...")
    
    hero_files = []
    
    # Get keepers
    if keepers_dir.is_dir():
        for f in keepers_dir.iterdir():
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                hero_files.append(f)
    
    # Get picks from bursts
    for burst_folder in directory.glob("burst-*/"):
        if burst_folder.is_dir():
            for f in burst_folder.iterdir():
                if f.is_file() and f.name.startswith(BEST_PICK_PREFIX):
                    hero_files.append(f)

    if not hero_files:
        print("\n  No 'Keepers' or '_PICK_' files found. Nothing to archive.")
        print("   Auto workflow complete.")
        return

    print(f"   Found {len(hero_files)} 'hero' files to AI-name and archive.")
    
    # === FIX #1 START ===
    # Calculate total size before processing
    total_size_before = 0
    for f in hero_files:
        try:
            total_size_before += f.stat().st_size
        except Exception:
            pass
    tracker.add_size_before(total_size_before)
    # === FIX #1 END ===
    
    # v7.1 GM 3.1: SURGICAL FIX - REMOVED STATS CALLS
    # v7.1 GM 3.0: Track total files
    # tracker.increment_stat('total_files', len(hero_files))
    
    results = {"success": [], "failed": []}
    
    pbar = None
    if TQDM_AVAILABLE:
        pbar = SmartProgressBar(total=len(hero_files), desc=" 🤖 Archiving", unit="img")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # v7.1 (Patched): Files are processed into the ROOT destination (`chosen_destination`)
        # This is the "files_source" for the next step.
        future_to_file = {
            executor.submit(process_single_image, img_path, chosen_destination, chosen_model, dry_run=False): img_path 
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
                # === FIX #2 START ===
                # Track successful image
                try:
                    file_size = original.stat().st_size
                    tracker.record_image(file_size, success=True)
                    tracker.add_size_after(file_size)
                except Exception:
                    pass
                # === FIX #2 END ===
            else:
                results["failed"].append((original.name, message))
                # === FIX #3 START ===
                # Track failed image
                tracker.record_image(0, success=False)
                # === FIX #3 END ===
                if pbar:
                    pbar.write(f" ❌ {original.name}: {message}")
            
            if pbar:
                pbar.update()
    
    if pbar:
        pbar.close()
        
    print(f"\n{'='*60}")
    print(f" ✅ Successfully archived: {len(results['success'])}")
    print(f" ❌ Failed to archive: {len(results['failed'])}")
    
    # v7.1 GM 3.1: SURGICAL FIX - REMOVED STATS CALLS
    # v7.1 GM 3.0: Track AI naming stats
    # tracker.increment_stat('ai_named', len(results['success']))
    # tracker.increment_stat('failed', len(results['failed']))

    if results["success"]:
        # v7.1: Generate AI session name
        categories = {}
        for item in results["success"]:
            cat = categorize_description(item["description"])
            categories[cat] = categories.get(cat, 0) + 1
        
        # v7.1 GM 3.1: SURGICAL FIX - REMOVED STATS CALLS
        # v7.1 GM 3.0: Track category breakdown in stats
        # for cat, count in categories.items():
        #     tracker.add_category_count(cat, count)
        
        session_name = generate_ai_session_name(categories, chosen_model)
        
        # v7.1 (Patched): Stronger check for valid AI name
        if session_name and len(session_name) > 2:
            dated_folder = f"{SESSION_DATE}_{session_name}"
            print(f"\n   🎨 AI Session Name: {dated_folder}")
        else:
            dated_folder = f"{SESSION_DATE}_Session"
        
        # This is the *final* session folder, e.g., ".../test/2025-11-07_Vibe"
        final_destination = chosen_destination / dated_folder
        final_destination.mkdir(parents=True, exist_ok=True)
        tracker.set_destination(final_destination)
        
        # v7.1 (Patched): Pass correct source and destination paths
        # Move files from `chosen_destination` (root) into `final_destination` (session folder)
        organize_into_folders(results["success"], chosen_destination, final_destination, dry_run=False)

    print("\n" + "="*60)
    print(" 🚀 AUTO WORKFLOW COMPLETE")
    print("="*60)
    print(f" Your 'hero' photos are now in: {chosen_destination}")
    print(f"  Remaining 'duds' and 'bursts' are in: {directory}")

    # v7.1: Print session summary
    print("\n")
    tracker.print_summary()
    tracker.save_to_history(APP_CONFIG['history_path'])

# --- Legacy Ingest Workflow ---

def run_default_ingest(current_dir: Path, dry_run: bool, APP_CONFIG: dict):
    """(V7.1) Runs the original V4.1 AI-powered ingest process,
    refactored to use v7.1 directory selector."""
    
    print(f"\n{'='*60}")
    print(f" 🤖 PhotoSort --- (Legacy Ingest Mode)")
    print(f"{'='*60}")
    
    # v7.1: Use directory selector
    print(" ⓘ  Legacy mode selected. Please choose source and destination.")
    source, destination = get_source_and_destination(APP_CONFIG)
    if not source or not destination:
        print(get_quit_message())
        return
    
    # Update config with last paths
    update_config_paths(APP_CONFIG, CONFIG_FILE_PATH, str(source), str(destination))

    # v7.1: Get model (still uses old prompt, but that's ok for legacy)
    print(f"\n 🤖 Default model: {APP_CONFIG['default_model']}")
    
    # v7.1 GM 3.0: Add model loading spinner
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
    
    # Check for dcraw on startup
    check_dcraw()
    
    # V7.0: Load config from file or use defaults
    APP_CONFIG = load_app_config()

    current_dir = Path.cwd()
    args = set(sys.argv[1:])
    
    dry_run = "--preview" in args or "-p" in args
    
    # V7.0 GOLD: Updated dispatch table - ALL COMMANDS GET ANIMATED BANNER!
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
    
    # GOLD: Clean CLI args (exclude --model and its value)
    cli_model = parse_model_override()
    clean_args = args - {"--preview", "-p", "--model"}
    if cli_model:
        clean_args = clean_args - {cli_model}
    
    # Find command
    command_to_run = None
    for flag in clean_args:
        if flag in DISPATCH_TABLE:
            command_to_run = flag
            break
    
    # v7.1: Refactored main dispatcher
    if command_to_run == '--auto':
        # v7.1: Use directory selector for auto mode
        
        # === BANNER FIX ===
        # Show banner FIRST, before directory selection
        show_banner("animated")
        # === END BANNER FIX ===
        
        source, destination = get_source_and_destination(APP_CONFIG)
        if not source or not destination:
            print(get_quit_message())
            return
        
        # Update config with last paths
        update_config_paths(APP_CONFIG, CONFIG_FILE_PATH, str(source), str(destination))
        
        # Run workflow (banner is shown *after* path selection)
        # show_banner("animated") # <-- MOVED UP
        
        # Call auto_workflow with new signature
        auto_workflow(source, destination, dry_run, APP_CONFIG)

    elif command_to_run: # All other commands
        (func_to_call, libs_ok, lib_msg, banner_mode) = DISPATCH_TABLE[command_to_run]
        
        # Show banner FIRST
        show_banner(banner_mode)
        
        if not libs_ok:
            print(lib_msg)
            return
            
        if dry_run:
            print("\n" + "="*60)
            print(f"  DRY RUN: {command_to_run.upper()} PREVIEW MODE")
            print(" NO FILES WILL BE MOVED/COPIED/WRITTEN")
            print("="*60)
        
        # Call the feature function
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
            print("  --cull, -c       : Sort images into _Keepers, _Review_Maybe, _Review_Duds")
            print("  --prep, --pe     : Find 'Good' images and copy to _ReadyForLightroom")
            print("\nOptions:")
            print("  --preview, -p    : Dry run mode (no files moved/copied/written)")
            print("  --model <name>   : Override config model (for --critique only)")
            print("  --help, -h       : Show this help message")
            
            if not TQDM_AVAILABLE:
                print("\n Tip: Install tqdm for progress bars: pip3 install tqdm")
            if not COLORAMA_AVAILABLE:
                print("\n Tip: Install colorama for animated banner: pip3 install colorama")
            return

        # Default: Legacy ingest
        show_banner("animated")
        
        if dry_run:
            print("\n" + "="*60)
            print(" DRY RUN: LEGACY INGEST PREVIEW MODE")
            print(" NO FILES WILL BE MOVED")
            print("="*60)
        
        # v7.1: This function is now refactored
        run_default_ingest(current_dir, dry_run, APP_CONFIG)
    
    if dry_run and command_to_run not in ('--auto',):
        print("\n" + "="*60)
        print(" DRY RUN COMPLETE - NO FILES WERE MOVED/COPIED/WRITTEN")
        print("="*60)
    else:
        print("\n Done!\n")


if __name__ == "__main__":
    main()