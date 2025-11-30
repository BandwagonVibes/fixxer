#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIXXER ✞ Engine (v1.0) - Professional-Grade with Hash Verification

NEW IN v1.0:
- SHA256 hash verification for ALL file move operations
- JSON sidecar files for audit trail (.fixxer.json)
- Halt-on-mismatch integrity protection
- "CHAOS PATCHED // LOGIC INJECTED"

v10.8 (Cross-Platform Migration):
- REMOVED macOS-only sips dependency completely
- convert_raw_to_jpeg() now uses Pillow for PPM→JPEG conversion
- 100% cross-platform (Linux, macOS, Windows with dcraw)
- Zero temp files created (pure in-memory operation via BytesIO)
- 5x smaller output files (689KB vs 3.7MB from sips)

v10.7 FIXES:
- convert_raw_to_jpeg() tries embedded thumbnail first (-e flag)
- Falls back to full demosaic only if embedded thumbnail fails
- Added timeouts to prevent hanging on problematic RAW files
"""

from __future__ import annotations

import os
import json
import hashlib  # NEW v1.0: SHA256 hash verification
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
CONFIG_FILE_PATH = Path.home() / ".fixxer.conf"

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
# III.5 STATS TRACKER (FIXXER v10.0 - HUD SUPPORT)
# ==============================================================================

class StatsTracker:
    """
    Real-time statistics tracker for workflow progress.
    Designed for thread-safe callback communication between engine and TUI.
    
    Usage:
        tracker = StatsTracker(callback=my_callback_function)
        tracker.start_timer()
        tracker.update('bursts', 42)
        tracker.stop_timer()
    """
    
    def __init__(self, callback: Optional[Callable[[str, Any], None]] = None):
        """
        Args:
            callback: Function to call when stats update (receives key, value)
        """
        self.callback = callback
        self._stats = {
            'bursts': 0,
            'tier_a': 0,
            'tier_b': 0,
            'tier_c': 0,
            'heroes': 0,
            'archived': 0,
            'time': '--'
        }
        self._start_time = None
    
    def update(self, key: str, value: Any) -> None:
        """
        Update a stat and trigger callback.
        
        Args:
            key: Stat identifier (e.g., 'bursts', 'tier_a', 'archived')
            value: New value for the stat
        """
        self._stats[key] = value
        if self.callback:
            self.callback(key, value)
    
    def start_timer(self) -> None:
        """Start the workflow timer."""
        self._start_time = datetime.now()
        self.update('time', 'Running...')
    
    def stop_timer(self) -> None:
        """Stop the timer and calculate human-readable duration."""
        if self._start_time:
            duration = datetime.now() - self._start_time
            total_seconds = int(duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            
            # Format: "2m 34s" (human-readable for quick glances)
            if minutes > 0:
                time_str = f"{minutes}m {seconds}s"
            else:
                time_str = f"{seconds}s"
            
            self.update('time', time_str)
    
    def reset(self) -> None:
        """Reset all stats to default values."""
        for key in self._stats.keys():
            if key == 'time':
                self._stats[key] = '--'
            else:
                self._stats[key] = 0
        self._start_time = None


# ==============================================================================
# IV. HASH VERIFICATION (FIXXER v1.0)
# ==============================================================================

def read_existing_sidecar(file_path: Path, log_callback: Callable[[str], None] = None) -> Optional[Dict[str, Any]]:
    """
    Read existing sidecar file if it exists at the source location.
    
    Args:
        file_path: Path to the image file (sidecar will be <file_path>.fixxer.json)
        log_callback: Optional logging function
    
    Returns:
        Dictionary with sidecar data if found, None otherwise
    """
    try:
        sidecar_path = file_path.parent / f"{file_path.name}.fixxer.json"
        
        if not sidecar_path.exists():
            return None
        
        with open(sidecar_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    
    except Exception as e:
        if log_callback:
            log_callback(f"   [yellow]⚠️[/yellow] Could not read existing sidecar: {e}")
        return None


def calculate_sha256(file_path: Path, log_callback: Callable[[str], None] = None) -> Optional[str]:
    """
    Calculate SHA256 hash of a file.
    
    Args:
        file_path: Path to file to hash
        log_callback: Optional logging function
    
    Returns:
        SHA256 hash as hex string, or None on error
    """
    try:
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    except Exception as e:
        if log_callback:
            log_callback(f"   [red]✗[/red] Hash calculation failed: {e}")
        return None


def verify_file_move_with_hash(
    source_path: Path,
    destination_path: Path,
    log_callback: Callable[[str], None] = None,
    generate_sidecar: bool = True
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Move file with SHA256 integrity verification.
    
    Workflow:
    1. Calculate hash of source file
    2. Move file to destination
    3. Calculate hash of destination file
    4. Compare hashes
    5. Optionally generate JSON sidecar
    6. Return success status
    
    Args:
        source_path: Source file path
        destination_path: Destination file path
        log_callback: Optional logging function
        generate_sidecar: If True, create .fixxer.json sidecar file
    
    Returns:
        Tuple of (success: bool, source_hash: str, dest_hash: str)
        On failure, raises RuntimeError to halt workflow
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
    
    try:
        # Step 0: Read existing sidecar (if any) before moving
        existing_sidecar = read_existing_sidecar(source_path, log_callback)
        existing_history = []
        if existing_sidecar and 'move_history' in existing_sidecar:
            existing_history = existing_sidecar['move_history']
        
        # Step 1: Calculate source hash
        log(f"   → Computing integrity hash...")
        source_hash = calculate_sha256(source_path, log_callback)
        
        if not source_hash:
            error_msg = f"Failed to calculate source hash for {source_path.name}"
            log(f"   [red]✗[/red] {error_msg}")
            raise RuntimeError(error_msg)
        
        # Show shortened hash in logs
        short_hash = f"{source_hash[:16]}..."
        log(f"   → SHA256: [cyan]{short_hash}[/cyan]")
        
        # Step 2: Move the file
        log(f"   → Moving to {destination_path.parent.name}/")
        shutil.move(str(source_path), str(destination_path))
        
        # Step 3: Calculate destination hash
        log(f"   → Verifying integrity...")
        dest_hash = calculate_sha256(destination_path, log_callback)
        
        if not dest_hash:
            error_msg = f"Failed to calculate destination hash for {destination_path.name}"
            log(f"   [red]✗[/red] {error_msg}")
            raise RuntimeError(error_msg)
        
        # Step 4: Compare hashes
        if source_hash == dest_hash:
            log(f"   [green]✓[/green] Hash verified: MATCH")
            
            # Step 5: Generate sidecar if requested
            if generate_sidecar:
                sidecar_success = write_sidecar_file(
                    destination_path,
                    source_path,
                    source_hash,
                    verified=True,
                    existing_history=existing_history,
                    log_callback=log_callback
                )
                if not sidecar_success:
                    log(f"   [yellow]⚠️[/yellow] Sidecar write failed (non-critical)")
                
                # Step 6: Clean up old sidecar at source location (if it existed)
                if existing_sidecar:
                    old_sidecar_path = source_path.parent / f"{source_path.name}.fixxer.json"
                    try:
                        if old_sidecar_path.exists():
                            old_sidecar_path.unlink()
                    except Exception as e:
                        # Non-critical - just log the warning
                        log(f"   [yellow]⚠️[/yellow] Could not remove old sidecar (non-critical): {e}")
            
            return True, source_hash, dest_hash
        
        else:
            # CRITICAL: Hash mismatch detected - HALT WORKFLOW
            log(f"   [red]✗ CRITICAL: Hash verified: MISMATCH[/red]")
            log(f"   [red]✗ Source:      {source_hash[:32]}...[/red]")
            log(f"   [red]✗ Destination: {dest_hash[:32]}...[/red]")
            log(f"   [red]✗ FILE CORRUPTION DETECTED[/red]")
            
            # Write sidecar with corruption flag
            if generate_sidecar:
                write_sidecar_file(
                    destination_path,
                    source_path,
                    source_hash,
                    verified=False,
                    dest_hash=dest_hash,
                    existing_history=existing_history,
                    log_callback=log_callback
                )
            
            # HALT: Raise exception to stop workflow
            error_msg = f"Hash mismatch detected for {destination_path.name} - workflow halted for safety"
            raise RuntimeError(error_msg)
    
    except RuntimeError:
        # Re-raise RuntimeError (our controlled halt)
        raise
    except Exception as e:
        error_msg = f"File move failed: {e}"
        log(f"   [red]✗[/red] {error_msg}")
        raise RuntimeError(error_msg)


def write_sidecar_file(
    destination_path: Path,
    original_path: Path,
    source_hash: str,
    verified: bool,
    dest_hash: Optional[str] = None,
    existing_history: Optional[List[Dict[str, str]]] = None,
    log_callback: Callable[[str], None] = None
) -> bool:
    """
    Write a JSON sidecar file with hash verification metadata and move history.
    
    Sidecar filename: <original_filename>.fixxer.json
    Example: photo.jpg -> photo.jpg.fixxer.json
    
    Args:
        destination_path: Where the file ended up
        original_path: Where the file came from
        source_hash: SHA256 of source
        verified: True if hashes matched
        dest_hash: Optional SHA256 of destination (for mismatch debugging)
        existing_history: List of previous moves (from old sidecar)
        log_callback: Optional logging function
    
    Returns:
        True on success, False on error
    """
    try:
        sidecar_path = destination_path.parent / f"{destination_path.name}.fixxer.json"
        
        # Build move history by appending current move to existing history
        move_history = existing_history if existing_history else []
        
        current_move = {
            "timestamp": datetime.now().isoformat(),
            "from": str(original_path),
            "to": str(destination_path),
            "operation": "file_move"
        }
        move_history.append(current_move)
        
        metadata = {
            "fixxer_version": "1.0",
            "filename": destination_path.name,
            "sha256_source": source_hash,
            "verified": verified,
            "move_history": move_history
        }
        
        # Add destination hash if provided (for mismatch cases)
        if dest_hash and dest_hash != source_hash:
            metadata["sha256_destination"] = dest_hash
            metadata["corruption_detected"] = True
        
        with open(sidecar_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        return True
    
    except Exception as e:
        if log_callback:
            log_callback(f"   [yellow]⚠️[/yellow] Sidecar write error: {e}")
        return False


# ==============================================================================
# V. CORE UTILITIES
# ==============================================================================

def no_op_logger(message: str) -> None:
    """A dummy logger that does nothing, for when no callback is provided."""
    pass

def check_rawpy(log_callback: Callable[[str], None] = no_op_logger):
    """Check if rawpy is available and update RAW support"""
    global RAW_SUPPORT
    global SUPPORTED_EXTENSIONS
    try:
        import rawpy
        RAW_SUPPORT = True
        # Add ALL common RAW formats that rawpy supports
        # rawpy uses libraw which supports 100+ RAW formats
        raw_extensions = {'.rw2', '.arw', '.cr2', '.cr3', '.nef', '.dng', '.raf', '.orf', '.pef', '.srw',
                         '.3fr', '.ari', '.bay', '.crw', '.cs1', '.dc2', '.dcr', '.drf', '.eip', '.erf',
                         '.fff', '.iiq', '.k25', '.kdc', '.mdc', '.mef', '.mos', '.mrw', '.nrw', '.obm',
                         '.ptx', '.pxn', '.r3d', '.raw', '.rwl', '.rw1', '.rwz', '.sr2', '.srf', '.sti', '.x3f'}
        SUPPORTED_EXTENSIONS.update(raw_extensions)
        log_callback(f"✓ [green]rawpy found.[/green] RAW support enabled.")
        log_callback(f"  Common formats: RW2, CR2, CR3, NEF, ARW, DNG, RAF, ORF, PEF, SRW + 40 more")
    except ImportError:
        RAW_SUPPORT = False
        log_callback("✗ [yellow]rawpy not found.[/yellow] RAW support disabled.")
        log_callback("  Install with: pip install rawpy")
    except Exception as e:
        RAW_SUPPORT = False
        log_callback(f"✗ [red]rawpy check failed:[/red] {e}")

# DEPRECATED: Use check_rawpy() instead
def check_dcraw(log_callback: Callable[[str], None] = no_op_logger):
    """DEPRECATED: dcraw is no longer used. Call check_rawpy() instead."""
    log_callback("[yellow]Warning: check_dcraw() is deprecated. Using rawpy now.[/yellow]")
    check_rawpy(log_callback)

def check_ollama_connection(
    log_callback: Callable[[str], None] = no_op_logger,
    all_systems_go: bool = True
) -> bool:
    """
    Check if Ollama is running and accessible with 3-line llama narrative.
    
    Features a bilingual dad joke:
    - Line 1: "Looking for llamas 🔎🦙"
    - Line 2: Connection status
    - Line 3: "¿Cómo se Llama? Se llama 'Speed' 🦙🦙💨" + system status
    
    Args:
        log_callback: Logging function
        all_systems_go: True if all critical dependencies (rawpy, BRISQUE, CLIP) are ready
    
    Returns:
        True if Ollama is accessible, False otherwise
    """
    try:
        # Line 1: The Search
        log_callback("   [grey]Looking for llamas 🔎🦙[/grey]")
        
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            model_count = len(models)
            
            # Line 2: The Discovery
            log_callback(f"   [green]✓ Ollama connected[/green] ({model_count} models)")
            
            # Line 3: The Punchline + System Status
            if all_systems_go:
                status = "[green]✅ (FULL VISION)[/green]"
            else:
                status = "[yellow]⚠️  (limited features)[/yellow]"
            
            log_callback(
                f"   [bold cyan]¿Cómo se Llama?[/bold cyan] "
                f"[bold white]Se llama 'Speed'[/bold white] 🦙🦙💨    {status}"
            )
            
            return True
        else:
            log_callback("   [yellow]⚠️ Ollama responded but status unclear[/yellow]")
            return False
            
    except requests.exceptions.ConnectionError:
        log_callback("   [grey]Looking for llamas 🔎🦙[/grey]")
        log_callback("   [red]✗ Ollama not running[/red]")
        log_callback("   [dim]No llamas found. Start with: [cyan]ollama serve[/cyan][/dim]")
        return False
        
    except requests.exceptions.Timeout:
        log_callback("   [grey]Looking for llamas 🔎🦙[/grey]")
        log_callback("   [yellow]⚠️ Ollama connection timeout[/yellow]")
        log_callback("   [dim]Llamas are hiding. Try again?[/dim]")
        return False
        
    except Exception as e:
        log_callback("   [grey]Looking for llamas 🔎🦙[/grey]")
        log_callback(f"   [yellow]⚠️ Ollama check failed: {e}[/yellow]")
        return False

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
    """Convert RAW file to JPEG bytes using rawpy (Python-native, cross-platform).
    
    v10.0 Migration: rawpy replaces dcraw subprocess calls
    
    Method 1: Embedded Thumbnail Extraction (Fast)
    - Extracts embedded JPEG thumbnail using rawpy
    - Typical size: 500-1000KB
    - Quality: Perfect for CLIP embeddings and BRISQUE scoring
    
    Method 2: Quick Demosaic Fallback (Slower)
    - Uses half-size demosaic for speed
    - Only if thumbnail extraction fails
    
    Benefits vs dcraw:
    - 100% Python-native (no subprocess, no system dependency)
    - Faster (C++ library called directly)
    - Supports 100+ RAW formats via libraw
    - Cross-platform (Linux, macOS, Windows)
    - No temp files (pure memory operation)
    """
    if not RAW_SUPPORT:
        return None
    
    try:
        import rawpy
    except ImportError:
        log_callback(f"   [red]rawpy not available for RAW conversion[/red]")
        return None
    
    # Method 1: Extract embedded thumbnail (fast, works for most modern cameras)
    try:
        with rawpy.imread(str(raw_path)) as raw:
            # Try to extract embedded thumbnail
            try:
                thumb = raw.extract_thumb()
                if thumb.format == rawpy.ThumbFormat.JPEG:
                    # Perfect! Camera provided JPEG thumbnail
                    return thumb.data
                elif thumb.format == rawpy.ThumbFormat.BITMAP:
                    # Got a bitmap thumbnail, convert to JPEG via Pillow
                    from PIL import Image
                    img = Image.frombytes('RGB', (thumb.width, thumb.height), thumb.data)
                    jpeg_buffer = BytesIO()
                    img.save(jpeg_buffer, format='JPEG', quality=95)
                    jpeg_buffer.seek(0)
                    return jpeg_buffer.read()
            except rawpy.LibRawNoThumbnailError:
                # No embedded thumbnail, fall through to Method 2
                pass
            except Exception as thumb_error:
                # Thumbnail extraction failed for some reason, fall through
                log_callback(f"   [dim]Thumbnail extraction failed for {raw_path.name}, using demosaic[/dim]")
            
            # Method 2: Quick demosaic fallback (half-size for speed)
            try:
                rgb = raw.postprocess(
                    use_camera_wb=True,    # Use camera white balance
                    half_size=True,        # Half resolution for speed (still plenty for AI)
                    no_auto_bright=True,   # Don't auto-brighten
                    output_bps=8           # 8-bit output
                )
                
                # Convert numpy array to JPEG via Pillow in-memory
                from PIL import Image
                img = Image.fromarray(rgb)
                jpeg_buffer = BytesIO()
                img.save(jpeg_buffer, format='JPEG', quality=95)
                jpeg_buffer.seek(0)
                return jpeg_buffer.read()
                
            except Exception as demosaic_error:
                log_callback(f"   [red]Demosaic failed for {raw_path.name}:[/red] {demosaic_error}")
                return None
    
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

def get_unique_filename_simulated(base_name: str, extension: str, destination: Path, simulated_paths: set) -> Path:
    """
    Generate unique filename for preview mode using simulated_paths set.

    This is critical for accurate collision detection in dry-run mode where
    files don't actually exist yet but we need to simulate naming conflicts.

    Args:
        base_name: Base filename without extension
        extension: File extension (including dot)
        destination: Destination directory path
        simulated_paths: Set of Path objects representing files that will exist

    Returns:
        Path object with collision-free filename
    """
    filename = destination / f"{base_name}{extension}"
    if filename not in simulated_paths:
        return filename
    counter = 1
    while True:
        filename = destination / f"{base_name}-{counter:02d}{extension}"
        if filename not in simulated_paths:
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
        header = f"# FIXXER AI Rename Log - {SESSION_TIMESTAMP}\n"
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
    (V7.0) Loads settings from ~/.fixxer.conf
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
    # v1.1: Burst auto-naming toggle (default: false for speed)
    config['burst_auto_name'] = parser.getboolean(
        'burst', 'burst_auto_name',
        fallback=False
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
    
    # v10.0: Pro Mode toggle (Phantom Redline aesthetic)
    config['pro_mode'] = parser.getboolean(
        'behavior', 'pro_mode', fallback=False
    )

    return config


def save_app_config(config: Dict[str, Any]) -> bool:
    """
    (V10.7) Save specific settings back to ~/.fixxer.conf
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
    
    # v10.0: Save pro_mode toggle
    if 'pro_mode' in config:
        parser.set('behavior', 'pro_mode', 'true' if config['pro_mode'] else 'false')
    
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

def get_ai_name_with_cache(
    img_path: Path,
    model: str,
    cache: Optional[Dict[str, Dict]],
    cache_lock: Optional[threading.Lock],
    log_callback: Callable[[str], None] = no_op_logger
) -> Tuple[Optional[str], Optional[List[str]]]:
    """
    Get AI name/tags, using cache if valid (dry-run preview feature).

    Thread-safe caching with validation:
    - Checks file modification time (mtime) to detect changes
    - Checks cache age (10 min expiry)
    - Model-aware cache keys: f"{model}:{path}"
    - Protected by threading.Lock for concurrent access

    Args:
        img_path: Image file path
        model: Ollama model name
        cache: Optional cache dict (None = always run AI)
        cache_lock: Optional threading.Lock for thread-safe cache access
        log_callback: Logging function

    Returns:
        Tuple of (filename: str, tags: List[str]) or (None, None) on failure
    """
    if cache is None:
        # No cache provided, always run AI
        return get_ai_description(img_path, model, log_callback)

    # Model-aware cache key (critical: different models = different results)
    cache_key = f"{model}:{str(img_path.absolute())}"
    current_mtime = img_path.stat().st_mtime

    # Thread-safe cache read
    cached_entry = None
    if cache_lock:
        with cache_lock:
            cached_entry = cache.get(cache_key)
    else:
        cached_entry = cache.get(cache_key)

    # Check cache validity
    if cached_entry:
        # Validate: file unchanged + cache fresh (<10 min)
        age = time.time() - cached_entry['cached_at']
        if cached_entry['mtime'] == current_mtime and age < 600:
            log_callback(f"   [dim]⚡ Using cached AI result[/dim]")
            return cached_entry['filename'], cached_entry['tags']
        else:
            # Cache invalid (file changed or expired)
            if cached_entry['mtime'] != current_mtime:
                log_callback(f"   [yellow]File changed, re-running AI[/yellow]")
            else:
                log_callback(f"   [dim]Cache expired ({age/60:.1f}m old), re-running AI[/dim]")

    # Cache miss or invalid - run AI
    log_callback(f"   [grey]🤖 Generating AI name...[/grey]")
    filename, tags = get_ai_description(img_path, model, log_callback)

    if filename and tags:
        # Thread-safe cache write
        entry = {
            'filename': filename,
            'tags': tags,
            'mtime': current_mtime,
            'cached_at': time.time()
        }
        if cache_lock:
            with cache_lock:
                cache[cache_key] = entry
        else:
            cache[cache_key] = entry

    return filename, tags

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
    
    # NEW: Use your existing rawpy helper instead of dcraw subprocess!
    # This handles ARW, CR2, NEF, etc. purely in memory.
    try:
        raw_formats = {'.rw2', '.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.pef', '.srw'}
        if image_path.suffix.lower() in raw_formats:
            jpeg_bytes = convert_raw_to_jpeg(image_path, log_callback)
            if jpeg_bytes:
                img = Image.open(BytesIO(jpeg_bytes))
                return image_path, imagehash.phash(img)
            else:
                return image_path, None
           
        # Standard images (JPG, PNG, etc.)
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
    log_callback: Callable[[str], None] = no_op_logger,
    preview_mode: bool = False,
    ai_cache: Optional[Dict[str, Dict]] = None,
    cache_lock: Optional[threading.Lock] = None,
    simulated_paths: Optional[set] = None
) -> Tuple[Path, bool, str, str]:
    """
    (V9.3) Process one image: get AI name/tags, rename, move to temp location.

    New in dry-run feature:
        preview_mode: If True, simulate operations without moving files
        ai_cache: Optional cache dict for AI results
        cache_lock: Optional threading.Lock for thread-safe cache access
        simulated_paths: Set of paths for collision detection in preview mode
    """
    try:
        if is_already_ai_named(image_path.name):
            extension = image_path.suffix.lower()
            base_name = image_path.stem
            clean_base = base_name[:-5] if base_name.endswith('_PICK') else base_name

            if preview_mode and simulated_paths is not None:
                new_path = get_unique_filename_simulated(clean_base, extension, destination_base, simulated_paths)
                simulated_paths.add(new_path)
                log_callback(f"   [cyan]WOULD MOVE:[/cyan] {image_path.name} → {new_path.name}")
            else:
                new_path = get_unique_filename(clean_base, extension, destination_base)
                # FIXXER v1.0: Hash-verified move
                verify_file_move_with_hash(image_path, new_path, log_callback, generate_sidecar=True)

            if rename_log_path:
                write_rename_log(rename_log_path, image_path.name, new_path.name, destination_base)
            description_for_categorization = clean_base.replace('-', ' ')
            return image_path, True, new_path.name, description_for_categorization

        # Use cache-aware AI naming
        ai_filename, ai_tags = get_ai_name_with_cache(
            image_path, model_name, ai_cache, cache_lock, log_callback
        )
        if not ai_filename or not ai_tags:
            return image_path, False, "Failed to get valid AI JSON response", ""

        description_for_categorization = " ".join(ai_tags)
        clean_name = Path(ai_filename).stem
        extension = image_path.suffix.lower()

        if preview_mode and simulated_paths is not None:
            new_path = get_unique_filename_simulated(clean_name, extension, destination_base, simulated_paths)
            simulated_paths.add(new_path)
            log_callback(f"   [cyan]WOULD MOVE:[/cyan] {image_path.name} → {new_path.name}")
        else:
            new_path = get_unique_filename(clean_name, extension, destination_base)
            # FIXXER v1.0: Hash-verified move
            verify_file_move_with_hash(image_path, new_path, log_callback, generate_sidecar=True)

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
                # FIXXER v1.0: Hash-verified move
                log_callback(f"     Processing {src.name}...")
                verify_file_move_with_hash(src, dst, log_callback, generate_sidecar=True)
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

# --- Simple Sort Workflow (Legacy Mode) ---

def simple_sort_workflow(
    log_callback: Callable[[str], None] = no_op_logger,
    app_config: Optional[Dict[str, Any]] = None,
    stop_event: Optional[threading.Event] = None,
    preview_mode: bool = False,
    ai_cache: Optional[Dict[str, Dict]] = None,
    cache_lock: Optional[threading.Lock] = None
) -> Dict[str, Any]:
    """
    Simple workflow: AI name + organize by keyword into folders.
    No burst detection, no culling - just straightforward naming and sorting.
    Perfect for home users who want a simple "point and organize" experience.

    This is the "legacy mode" from the original CLI photosort.py that just:
    1. AI names all images
    2. Groups them into folders by keyword
    That's it. Powerful for the home user who just needs to organize photos.

    New in dry-run feature:
        preview_mode: If True, simulate operations without moving files
        ai_cache: Optional cache dict for AI results
        cache_lock: Optional threading.Lock for thread-safe cache access
    """
    start_time = datetime.now()
    
    if app_config is None:
        app_config = load_app_config()
    
    source_str = app_config.get('last_source_path')
    dest_str = app_config.get('last_destination_path')
    chosen_model = app_config.get('default_model', DEFAULT_MODEL_NAME)
    
    if not source_str or not dest_str:
        log_callback("[bold red]✗ FATAL: Source or Destination not set in config.[/bold red]")
        return {}
    
    directory = Path(source_str)
    chosen_destination = Path(dest_str)
    
    if not directory.is_dir():
        log_callback(f"[bold red]✗ FATAL: Source directory not found:[/bold red] {directory}")
        return {}

    if not preview_mode:
        try:
            chosen_destination.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log_callback(f"[bold red]✗ FATAL: Could not create destination:[/bold red] {e}")
            return {}

    # Create temp staging area for renamed files
    temp_staging = chosen_destination / "_staging"
    if not preview_mode:
        temp_staging.mkdir(exist_ok=True)

    log_callback(f"\n[bold cyan]📁 Simple Sort: AI Naming + Keyword Folders[/bold cyan]")
    if preview_mode:
        log_callback(f"   [yellow]MODE: DRY RUN (No files will be moved)[/yellow]")
    log_callback(f"   Source:      {directory}")
    log_callback(f"   Destination: {chosen_destination}")
    log_callback(f"   Model:       {chosen_model}")
    
    check_dcraw(log_callback)
    
    # Get all image files
    image_files = []
    for ext in SUPPORTED_EXTENSIONS:
        image_files.extend(directory.glob(f"*{ext}"))
    
    if not image_files:
        log_callback("[yellow]No image files found in source directory.[/yellow]")
        return {}
    
    log_callback(f"\n   Found {len(image_files)} images to process")
    
    # Process images: AI naming
    log_callback("\n[bold]🤖 AI Naming Images...[/bold]")
    processed_files = []
    success_count = 0

    # Track simulated paths to prevent collisions in preview
    simulated_paths = set() if preview_mode else None

    for idx, img in enumerate(image_files, 1):
        if stop_event and stop_event.is_set():
            log_callback("\n[yellow]🛑 Workflow stopped by user.[/yellow]")
            return {}

        log_callback(f"   [{idx}/{len(image_files)}] {img.name}")
        original_path, success, new_name, description = process_single_image(
            img, temp_staging, chosen_model,
            log_callback=log_callback,
            preview_mode=preview_mode,
            ai_cache=ai_cache,
            cache_lock=cache_lock,
            simulated_paths=simulated_paths
        )
        
        if success:
            processed_files.append({
                'original': original_path.name,
                'new_name': new_name,
                'description': description
            })
            success_count += 1
        else:
            log_callback(f"     [red]Failed: {new_name}[/red]")
    
    log_callback(f"\n   [green]✓[/green] Successfully named {success_count}/{len(image_files)} images")
    
    if not processed_files:
        log_callback("[yellow]No files were successfully processed.[/yellow]")
        try:
            temp_staging.rmdir()
        except:
            pass
        return {}
    
    # Organize into keyword folders
    log_callback("\n[bold]📂 Organizing into Keyword Folders...[/bold]")
    if preview_mode:
        # In preview mode, simulate organization based on descriptions
        categories = defaultdict(list)
        for file_info in processed_files:
            cat = categorize_description(file_info['description'])
            categories[cat].append(file_info['new_name'])

        for cat, files in categories.items():
            log_callback(f"   [dim]Preview: Would move {len(files)} files to[/dim] [cyan]{cat}/[/cyan]")
    else:
        organize_into_folders(processed_files, temp_staging, chosen_destination, log_callback)

        # Clean up staging directory
        try:
            temp_staging.rmdir()
        except:
            pass
    
    duration = datetime.now() - start_time
    log_callback(f"\n[bold green]✓ Simple Sort Complete![/bold green]")
    log_callback(f"   Duration: {format_duration(duration)}")
    log_callback(f"   {success_count} images organized into folders")
    
    return {
        'total_images': len(image_files),
        'success_count': success_count,
        'duration': str(duration)
    }


# --- Auto Workflow ---

def auto_workflow(
    log_callback: Callable[[str], None] = no_op_logger,
    app_config: Optional[Dict[str, Any]] = None,
    tracker: Optional[StatsTracker] = None,
    stop_event: Optional[threading.Event] = None,
    preview_mode: bool = False,
    ai_cache: Optional[Dict[str, Dict]] = None,
    cache_lock: Optional[threading.Lock] = None
) -> Dict[str, Any]:
    """
    (V9.3) Complete automated workflow: Stack → Cull → AI-Name → Archive.

    New in dry-run feature:
        preview_mode: If True, simulate operations without moving files
        ai_cache: Optional cache dict for AI results (model-aware)
        cache_lock: Optional threading.Lock for thread-safe cache access
    """

    # --- PREVIEW MODE BANNER ---
    if preview_mode:
        log_callback("\n[bold yellow]═══ DRY RUN MODE ═══[/bold yellow]")
        log_callback("[dim]No files will be moved. Preview only.[/dim]\n")

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

    if not preview_mode:
        try:
            chosen_destination.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log_callback(f"[bold red]✗ FATAL: Could not create destination:[/bold red] {e}")
            return {}

    chosen_model = app_config['default_model']
    log_callback(f"   Source:      {directory}")
    log_callback(f"   Destination: {chosen_destination}")
    log_callback(f"   Model:       {chosen_model}")
    if preview_mode:
        log_callback(f"   [yellow]Mode:        DRY RUN (preview only)[/yellow]")
    
    # Check for critical libs
    if not V5_LIBS_AVAILABLE or not V6_CULL_LIBS_AVAILABLE or not V6_4_EXIF_LIBS_AVAILABLE:
        log_callback("[bold red]✗ FATAL: Missing required libraries.[/bold red]")
        log_callback("   Please run: pip install imagehash opencv-python numpy exifread")
        return {}
    
    session_tracker = SessionTracker()
    session_tracker.set_model(chosen_model)
    session_tracker.add_operation("Burst Stacking")
    session_tracker.add_operation("Quality Culling")
    session_tracker.add_operation("AI Naming")
    # check_dcraw removed - we use rawpy now (Python-native RAW support)
    
    # Start HUD timer
    if tracker:
        tracker.start_timer()
    
    # --- 2. STATS PREVIEW ---
    log_callback("\n[bold]Step 2/5: Analyzing session (read-only)...[/bold]")
    try:
        if stop_event and stop_event.is_set(): return {}
        show_exif_insights(log_callback, app_config, simulated=True, directory_override=directory, stop_event=stop_event)
    except Exception as e:
        log_callback(f"     [yellow]Could not run EXIF analysis: {e}[/yellow]")

    # --- 3. GROUP BURSTS ---
    if stop_event and stop_event.is_set(): return {}
    log_callback("\n[bold]Step 3/5: Stacking burst shots (with AI naming)...[/bold]")
    if preview_mode:
        log_callback("[dim yellow]PREVIEW MODE: No files will be moved[/dim yellow]")
    # v1.1: Auto workflow ALWAYS does AI naming, regardless of burst_auto_name config
    auto_config = app_config.copy()
    auto_config['burst_auto_name'] = True

    # [FIX] Capture returned picks (dry-run feature)
    burst_picks = group_bursts_in_directory(log_callback, auto_config, directory_override=directory, tracker=tracker, stop_event=stop_event, preview_mode=preview_mode, ai_cache=ai_cache, cache_lock=cache_lock)

    # --- 4. CULL SINGLES ---
    if stop_event and stop_event.is_set(): return {}
    log_callback("\n[bold]Step 4/5: Culling single shots...[/bold]")
    if preview_mode:
        log_callback("[dim yellow]PREVIEW MODE: No files will be moved[/dim yellow]")

    # [FIX] Capture returned Tier A files (dry-run feature)
    tier_a_files = cull_images_in_directory(log_callback, app_config, directory_override=directory, tracker=tracker, stop_event=stop_event, preview_mode=preview_mode)
    tier_a_dir = directory / TIER_A_FOLDER
    
    # --- 5. FIND & ARCHIVE HEROES ---
    log_callback("\n[bold]Step 5/5: Finding and archiving 'hero' files...[/bold]")

    hero_files = []

    if preview_mode:
        # [CRITICAL FIX] In Dry Run, folders don't exist. Use the returned lists!
        # Combine lists and remove duplicates (if any file appeared in both)
        if burst_picks:
            hero_files.extend(burst_picks)
        if tier_a_files:
            # Only add Tier A files that aren't already in burst picks
            picks_set = set(burst_picks) if burst_picks else set()
            for f in tier_a_files:
                if f not in picks_set:
                    hero_files.append(f)
        log_callback(f"   [dim]Preview: Found {len(hero_files)} hero files from returned lists[/dim]")
    else:
        # [REAL RUN] Use existing filesystem scanning logic
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
    
    # Update HUD: Heroes count
    if tracker:
        tracker.update('heroes', len(hero_files))
    
    results = {"success": [], "failed": []}

    # [LOGIC PATCH] Only create the physical rename log if this is a REAL run
    if preview_mode:
        rename_log_path = None
    else:
        rename_log_path = chosen_destination / f"_ai_rename_log_{SESSION_TIMESTAMP}.txt"
        initialize_rename_log(rename_log_path)

    # Preview mode: track simulated paths for collision detection
    simulated_paths = set() if preview_mode else None

    log_callback(f"\n   [grey]Archiving {len(hero_files)} files...[/grey]")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(
                process_single_image,
                img_path,
                chosen_destination,
                chosen_model,
                rename_log_path,
                log_callback,
                preview_mode,
                ai_cache,
                cache_lock,
                simulated_paths
            ): img_path
            for img_path in hero_files
        }

        for i, future in enumerate(as_completed(future_to_file)):
            if stop_event and stop_event.is_set():
                log_callback("\n[yellow]🛑 Workflow stopped by user.[/yellow]")
                executor.shutdown(wait=False, cancel_futures=True)
                return {}

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
    
    # Update HUD: Archived count
    if tracker:
        tracker.update('archived', len(results['success']))
    
    summary = {
        "archived": len(results['success']),
        "failed": len(results['failed']),
    }

    if results["success"]:
        categories = {}
        for item in results["success"]:
            cat = categorize_description(item["description"])
            categories[cat] = categories.get(cat, 0) + 1

        # In preview mode, skip file organization (files not actually moved)
        if preview_mode:
            log_callback(f"\n[dim]Preview: Would organize into {len(categories)} categories:[/dim]")
            for cat, count in categories.items():
                log_callback(f"   [dim]• {cat}: {count} files[/dim]")
            summary["categories"] = len(categories)
            summary["preview_categories"] = categories
        else:
            # (V10.7) Pass sample images for vision-based session naming
            # [FIX] Select up to 3 diverse hero files as samples
            sample_images = []
            for item in results["success"]:
                if len(sample_images) >= 3:
                    break

                # [LOGIC PATCH] In Dry Run, file is at SOURCE. In Real Run, it's at DESTINATION.
                if preview_mode:
                    # File is still in source directory
                    current_path = directory / item["original"]
                else:
                    # File has been moved to destination
                    current_path = chosen_destination / item["new_name"]

                if current_path.exists():
                    # Quick test: try to encode it to ensure it's readable
                    test_encode = encode_image(current_path, no_op_logger)
                    if test_encode:
                        sample_images.append(current_path)

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
            if not preview_mode:
                final_destination.mkdir(parents=True, exist_ok=True)
            session_tracker.set_destination(final_destination)

            organize_into_folders(results["success"], chosen_destination, final_destination, log_callback)
            summary["final_destination"] = str(final_destination.name)
            summary["categories"] = len(categories)

    # Stop HUD timer
    if tracker:
        tracker.stop_timer()

    # Different completion messages for preview vs real mode
    if preview_mode:
        log_callback("\n[bold green]✓ Dry Run Complete[/bold green]")
        log_callback(f"   [dim]Preview generated {len(results['success'])} AI names[/dim]")
        if ai_cache:
            log_callback(f"   [cyan]⚡ Cached {len(ai_cache)} AI results for instant execution[/cyan]")
    else:
        log_callback("\n[bold green]🚀 AUTO WORKFLOW COMPLETE[/bold green]")
        log_callback(f"   Your 'hero' photos are now in: {chosen_destination}")
        if rename_log_path:
            log_callback(f"   Rename log saved: {rename_log_path.name}")

    return summary

# --- Burst Workflow ---

def group_bursts_in_directory(
    log_callback: Callable[[str], None] = no_op_logger,
    app_config: Optional[Dict[str, Any]] = None,
    simulated: bool = False,
    directory_override: Optional[Path] = None,
    tracker: Optional[StatsTracker] = None,
    stop_event: Optional[threading.Event] = None,
    preview_mode: bool = False,
    ai_cache: Optional[Dict[str, Dict]] = None,
    cache_lock: Optional[threading.Lock] = None
) -> List[Path]:
    """
    (V1.2) Finds and stacks burst groups, optionally AI-naming the best pick.

    Returns:
        List of 'Pick' files (best images from each burst group)

    By default (burst_auto_name=false), uses fast numeric naming.
    Set burst_auto_name=true in config to enable AI naming (slower).
    Auto workflow always uses AI naming regardless of this setting.

    New in dry-run feature:
        preview_mode: If True, simulate operations without moving files
    """
    
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
            if stop_event and stop_event.is_set():
                log_callback("\n[yellow]🛑 Workflow stopped by user.[/yellow]")
                executor.shutdown(wait=False, cancel_futures=True)
                return
                
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
        return []
        
    log_callback(f"   [green]✓ Found {len(all_burst_groups)} burst groups.[/green] Analyzing for best pick...")

    # Update HUD: Bursts count
    if tracker:
        tracker.update('bursts', len(all_burst_groups))

    # Track burst picks for return value (dry-run feature)
    burst_picks: List[Path] = []

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
        if not preview_mode:
            bursts_parent.mkdir(exist_ok=True)
    
    # v1.1: Check if AI naming is enabled for burst workflow
    burst_auto_name = app_config.get('burst_auto_name', False)

    if burst_auto_name:
        # [LOGIC PATCH] Only create the physical rename log if this is a REAL run
        if preview_mode:
            rename_log_path = None
        else:
            rename_log_path = directory / f"_ai_rename_log_{SESSION_TIMESTAMP}.txt"
            initialize_rename_log(rename_log_path)
        ai_model = app_config.get('default_model', DEFAULT_MODEL_NAME)
        log_callback("   [grey]AI naming enabled for bursts...[/grey]")

    for i, group in enumerate(all_burst_groups):
        winner_data = best_picks.get(i)
        sample_image = winner_data[0] if winner_data else group[0]

        # Add the winner to our return list (for dry-run feature)
        burst_picks.append(sample_image)

        # Only run AI naming if enabled
        if burst_auto_name:
            log_callback(f"   [grey]Burst {i+1}/{len(all_burst_groups)}: Naming...[/grey]")

            # Use cache-aware AI naming (for dry-run feature)
            ai_filename, ai_tags = get_ai_name_with_cache(
                sample_image, ai_model, ai_cache, cache_lock, log_callback
            )

            if ai_filename and ai_tags:
                base_name = Path(ai_filename).stem  # Extract base name without extension
                folder_name = f"{base_name}_burst"
                log_callback(f"     [green]✓ AI named:[/green] {base_name}")
            else:
                base_name = f"burst-{i+1:03d}"
                folder_name = base_name
                log_callback(f"     [yellow]⚠️ AI naming failed, using:[/yellow] {base_name}")
        else:
            # Fast mode: Just use numeric naming
            base_name = f"burst-{i+1:03d}"
            folder_name = base_name
            log_callback(f"   [grey]Burst {i+1}/{len(all_burst_groups)}: {folder_name} ({len(group)} files)[/grey]")
        
        folder_path = bursts_parent / folder_name
        if folder_path.exists():
            counter = 2
            original_name = folder_name
            while folder_path.exists():
                folder_name = f"{original_name}-{counter}"
                folder_path = bursts_parent / folder_name
                counter += 1
        
        log_callback(f"     [grey]📁 Moving {len(group)} files to {folder_path.relative_to(directory)}/...[/grey]")
        if not preview_mode:
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
                if preview_mode:
                    log_callback(f"     [cyan]WOULD MOVE:[/cyan] {file_path.name} → {folder_path.name}/{new_name}")
                else:
                    # FIXXER v1.0: Hash-verified move
                    verify_file_move_with_hash(file_path, new_file_path, log_callback, generate_sidecar=True)
                if burst_auto_name:
                    write_rename_log(rename_log_path, file_path.name, new_name, folder_path)
            except Exception as e:
                log_callback(f"     [red]FAILED to move {file_path.name}: {e}[/red]")

    if burst_auto_name and rename_log_path:
        log_callback(f"   Rename log saved: {rename_log_path.name}")

    return burst_picks  # Return the winners for dry-run feature

# --- Cull Workflow ---

def cull_images_in_directory(
    log_callback: Callable[[str], None] = no_op_logger,
    app_config: Optional[Dict[str, Any]] = None,
    simulated: bool = False,
    directory_override: Optional[Path] = None,
    tracker: Optional[StatsTracker] = None,
    stop_event: Optional[threading.Event] = None,
    preview_mode: bool = False
) -> List[Path]:
    """
    (V9.4) Finds and groups images by technical quality using Tier A/B/C naming.

    Returns:
        List of 'Tier A' files (best quality images)

    New in dry-run feature:
        preview_mode: If True, simulate operations without moving files
    """
    
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
            if stop_event and stop_event.is_set():
                log_callback("\n[yellow]🛑 Workflow stopped by user.[/yellow]")
                executor.shutdown(wait=False, cancel_futures=True)
                return

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
    
    # Update HUD: Tier A/B/C counts
    if tracker:
        tracker.update('tier_a', len(tiers['Tier_A']))
        tracker.update('tier_b', len(tiers['Tier_B']))
        tracker.update('tier_c', len(tiers['Tier_C']))
    
    folder_map = {
        "Tier_A": directory / TIER_A_FOLDER,
        "Tier_B": directory / TIER_B_FOLDER,
        "Tier_C": directory / TIER_C_FOLDER
    }
    
    for tier, paths in tiers.items():
        if not paths: continue
        folder_path = folder_map[tier]
        log_callback(f"   [grey]Moving {len(paths)} files to {folder_path.name}/...[/grey]")
        if not preview_mode:
            folder_path.mkdir(exist_ok=True)
            
        for file_path in paths:
            new_file_path = folder_path / file_path.name
            try:
                if preview_mode:
                    log_callback(f"     [cyan]WOULD MOVE:[/cyan] {file_path.name} → {folder_path.name}/{file_path.name}")
                else:
                    # FIXXER v1.0: Hash-verified move
                    verify_file_move_with_hash(file_path, new_file_path, log_callback, generate_sidecar=True)
            except Exception as e:
                log_callback(f"     [red]FAILED to move {file_path.name}: {e}[/red]")

    log_callback("   Culling complete!")

    return tiers["Tier_A"]  # Return Tier A files for dry-run feature

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
    directory_override: Optional[Path] = None,
    stop_event: Optional[threading.Event] = None
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
            if stop_event and stop_event.is_set():
                log_callback("\n[yellow]🛑 Workflow stopped by user.[/yellow]")
                executor.shutdown(wait=False, cancel_futures=True)
                return

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
