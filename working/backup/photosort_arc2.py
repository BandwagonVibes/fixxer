#!/usr/bin/env python3
"""
BakLLaVA Photo Organizer
Renames photos using local vision model and organizes into smart groups.
V4 Update: Choose destination folder AND model at runtime!
"""

import os
import json
import base64
import requests
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple, List, Dict
from collections import defaultdict
import re

# Try to import tqdm for progress bar
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("💡 Tip: Install tqdm for progress bars: pip3 install tqdm")

# Check if dcraw is available for RAW support
import subprocess

def check_dcraw():
    """Check if dcraw is available"""
    try:
        result = subprocess.run(['which', 'dcraw'], capture_output=True, text=True)
        return result.returncode == 0 and result.stdout.strip()
    except Exception:
        return False

RAW_SUPPORT = check_dcraw()

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL_NAME = "bakllava"
DEFAULT_DESTINATION_BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/negatives"

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
if RAW_SUPPORT:
    SUPPORTED_EXTENSIONS.add('.rw2')
MAX_WORKERS = 5
TIMEOUT = 60  # seconds per image

# Session date for organizing this batch
SESSION_DATE = datetime.now().strftime("%Y-%m-%d")
SESSION_TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H%M")

# Keywords for grouping (you can customize these!)
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


def get_available_models() -> Optional[List[str]]:
    """Get list of available Ollama models. Returns None if Ollama is unavailable."""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
        # Parse output - skip header line, extract model names
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        models = [line.split()[0] for line in lines if line.strip()]
        return models
    except subprocess.CalledProcessError:
        return None  # Ollama command failed
    except FileNotFoundError:
        return None  # Ollama not installed
    except Exception:
        return None  # Any other error


def convert_raw_to_jpeg(raw_path: Path) -> Optional[bytes]:
    """Convert RAW file to JPEG bytes using dcraw"""
    if not RAW_SUPPORT:
        return None
    
    try:
        # Create temporary file for JPEG output
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_jpg = tmp.name
        
        # Use dcraw to convert: -c writes to stdout, -w use camera white balance, -q 3 = high quality
        result = subprocess.run(
            ['dcraw', '-c', '-w', '-q', '3', str(raw_path)],
            capture_output=True,
            check=True
        )
        
        # dcraw outputs PPM to stdout, convert to JPEG using sips (built into macOS)
        with tempfile.NamedTemporaryFile(suffix='.ppm', delete=False) as ppm_tmp:
            ppm_tmp.write(result.stdout)
            ppm_file = ppm_tmp.name
        
        # Convert PPM to JPEG using sips
        subprocess.run(
            ['sips', '-s', 'format', 'jpeg', ppm_file, '--out', tmp_jpg],
            capture_output=True,
            check=True
        )
        
        # Read the JPEG
        with open(tmp_jpg, 'rb') as f:
            jpeg_bytes = f.read()
        
        # Clean up temp files
        os.unlink(ppm_file)
        os.unlink(tmp_jpg)
        
        return jpeg_bytes
    
    except Exception as e:
        print(f"❌ Error converting RAW file: {e}")
        # Clean up on error
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
        # Handle RAW files
        if image_path.suffix.lower() == '.rw2':
            jpeg_bytes = convert_raw_to_jpeg(image_path)
            if jpeg_bytes:
                return base64.b64encode(jpeg_bytes).decode('utf-8')
            else:
                return None
        
        # Handle regular image files
        with open(image_path, 'rb') as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    
    except Exception as e:
        print(f"❌ Error encoding {image_path.name}: {e}")
        return None


def get_ai_description(image_path: Path, model_name: str) -> Optional[str]:
    """Get filename suggestion from vision model"""
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
        response = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        
        result = response.json()
        description = result['message']['content'].strip()
        
        return description
        
    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout processing {image_path.name}")
        return None
    except Exception as e:
        print(f"❌ Error processing {image_path.name}: {e}")
        return None


def clean_filename(description: str) -> str:
    """Convert AI description to clean filename"""
    # Remove quotes, periods, and other punctuation
    clean = description.strip('"\'.,!?')
    
    # Replace spaces and special chars with hyphens
    clean = re.sub(r'[^\w\s-]', '', clean)
    clean = re.sub(r'[-\s]+', '-', clean)
    
    # Lowercase and limit length
    clean = clean.lower()[:60]
    
    return clean.strip('-')


def get_unique_filename(base_name: str, extension: str, destination: Path) -> Path:
    """Generate unique filename if file already exists"""
    filename = destination / f"{base_name}{extension}"
    
    if not filename.exists():
        return filename
    
    # Add counter if file exists
    counter = 1
    while True:
        filename = destination / f"{base_name}-{counter:02d}{extension}"
        if not filename.exists():
            return filename
        counter += 1


def categorize_description(description: str) -> str:
    """Determine category based on keywords in description"""
    description_lower = description.lower()
    
    # Count matches for each category
    category_scores = {}
    for category, keywords in GROUP_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in description_lower)
        if score > 0:
            category_scores[category] = score
    
    # Return category with highest score, or "Misc" if no matches
    if category_scores:
        return max(category_scores, key=category_scores.get)
    return "Miscellaneous"


def process_single_image(image_path: Path, destination_base: Path, model_name: str) -> Tuple[Path, bool, str, str]:
    """Process one image: get description, rename, move to temp location"""
    try:
        # Get AI description
        description = get_ai_description(image_path, model_name)
        if not description:
            return image_path, False, "Failed to get AI description", ""
        
        # Clean filename
        clean_name = clean_filename(description)
        if not clean_name:
            clean_name = f"image-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Get unique destination path (temporary location in negatives root)
        extension = image_path.suffix.lower()
        new_path = get_unique_filename(clean_name, extension, destination_base)
        
        # Move file to destination folder (temporary location)
        shutil.move(str(image_path), str(new_path))
        
        return image_path, True, new_path.name, description
        
    except Exception as e:
        return image_path, False, str(e), ""


def organize_into_folders(processed_files: List[Dict], destination_base: Path):
    """Group files into folders based on their descriptions"""
    print(f"\n{'='*60}")
    print("📁 Organizing into smart folders...")
    print(f"{'='*60}\n")
    
    # Categorize each file
    categories = defaultdict(list)
    for file_info in processed_files:
        filename = file_info['new_name']
        description = file_info['description']
        category = categorize_description(description)
        categories[category].append({
            'filename': filename,
            'description': description
        })
    
    # Create folders and move files
    for category, files in categories.items():
        folder_name = f"{SESSION_DATE}_{category}"
        folder_path = destination_base / folder_name
        folder_path.mkdir(exist_ok=True)
        
        print(f"📂 {folder_name}/ ({len(files)} files)")
        
        for file_info in files:
            src = destination_base / file_info['filename']
            dst = folder_path / file_info['filename']
            
            if src.exists():
                shutil.move(str(src), str(dst))
                print(f"   → {file_info['filename']}")
    
    print(f"\n✨ Organized into {len(categories)} folders")


def process_directory(directory: Path, destination_base: Path, model_name: str, max_workers: int = MAX_WORKERS):
    """Process all images in directory with concurrent workers"""
    
    # Find all supported images
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if not image_files:
        print("⚠️  No supported image files found in current directory")
        print(f"   Looking for: {', '.join(SUPPORTED_EXTENSIONS)}")
        return
    
    print(f"\n📸 Found {len(image_files)} images to process")
    print(f"🎯 Destination: {destination_base}")
    print(f"🤖 Model: {model_name}")
    print(f"⚙️  Using {max_workers} concurrent workers")
    if RAW_SUPPORT:
        print("✅ RAW support enabled (dcraw)")
    print(f"{'='*60}\n")
    
    # Phase 1: Process with thread pool (rename and move to destination root)
    results = {"success": [], "failed": []}
    
    # Create progress bar if tqdm is available
    if TQDM_AVAILABLE:
        pbar = tqdm(total=len(image_files), desc="🎨 Processing images", unit="img", ncols=80)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_image, img, destination_base, model_name): img 
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
                if TQDM_AVAILABLE:
                    pbar.write(f"❌ {original.name}: {message}")
                else:
                    print(f"❌ {original.name}: {message}")
            
            # Update progress bar
            if TQDM_AVAILABLE:
                pbar.update(1)
    
    # Close progress bar
    if TQDM_AVAILABLE:
        pbar.close()
    
    # Print processing summary
    print(f"\n{'='*60}")
    print(f"✅ Successfully processed: {len(results['success'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    
    if results["failed"]:
        print("\n⚠️  Failed files:")
        for orig, reason in results["failed"]:
            print(f"   • {orig}: {reason}")
    
    # Phase 2: Organize into folders
    if results["success"]:
        organize_into_folders(results["success"], destination_base)
    
    # Save log
    log_file = destination_base / f"_import_log_{SESSION_TIMESTAMP}.json"
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
    
    print(f"\n📝 Log saved: {log_file.name}")


def main():
    """Main entry point"""
    current_dir = Path.cwd()
    
    print("\n🎨 BakLLaVA Photo Organizer")
    print(f"📁 Current directory: {current_dir}")
    
    # Choose destination folder
    print(f"\n🎯 Default destination is: {DEFAULT_DESTINATION_BASE}")
    new_dest_path = input("   Press ENTER to use default, or type a new path: ").strip()

    chosen_destination: Path
    if not new_dest_path:
        chosen_destination = DEFAULT_DESTINATION_BASE
        print(f"   Using default destination.")
    else:
        chosen_destination = Path(new_dest_path).expanduser()
        print(f"   Using new destination: {chosen_destination}")
    
    # Ensure the chosen destination folder exists
    try:
        chosen_destination.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"❌ Error creating destination folder: {e}")
        print("   Please check the path and permissions. Exiting.")
        return
    
    # Choose model
    print(f"\n🤖 Default model is: {DEFAULT_MODEL_NAME}")
    
    # Show available models
    available_models = get_available_models()
    
    # CRITICAL: Check if Ollama is available
    if available_models is None:
        print("❌ FATAL: Could not connect to Ollama server.")
        print("   Please ensure Ollama is running with: ollama serve")
        print("   Or check if Ollama is installed: ollama --version")
        return
    
    if available_models:
        print(f"   Available models: {', '.join(available_models)}")
    else:
        print("   ⚠️  No models found. Run 'ollama pull bakllava' to install a model.")
    
    new_model = input("   Press ENTER to use default, or type a model name: ").strip()
    
    chosen_model: str
    if not new_model:
        chosen_model = DEFAULT_MODEL_NAME
        print(f"   Using default model.")
    else:
        # Validate the model exists
        if available_models and new_model not in available_models:
            print(f"⚠️  Warning: '{new_model}' not found in available models.")
            print(f"   Available: {', '.join(available_models)}")
            confirm = input("   Continue anyway? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Cancelled.")
                return
        chosen_model = new_model
        print(f"   Using model: {chosen_model}")

    # Confirm before processing
    response = input("\n▶️  Process all images in this directory? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    process_directory(current_dir, chosen_destination, chosen_model)
    print("\n✨ Done!\n")


if __name__ == "__main__":
    main()
