#!/usr/bin/env python3
"""
PhotoSort v9 Test Harness - Phase 1.5: Batch Stress Test

Tests the "Native JSON" model (qwen2.5vl:3b) under a concurrent load
to see if it bottlenecks, as the minicpm model did. This script
simulates the ThreadPoolExecutor load from the main photosort.py script.
"""

import os
import base64
import requests
import json
from pathlib import Path
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple, Optional, List

# --- CONFIGURATION ---
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5vl:3b" # Our winning model
TEST_IMAGE_DIR = Path.home() / "Downloads/photosortproject/Testing/staging"
MAX_WORKERS = 5 # Let's use the same number as photosort.py
REQUEST_TIMEOUT = 120 # Give each image 2 minutes

AI_NAMING_PROMPT = """You are an expert file-naming AI.
Analyze this image and generate a concise, descriptive filename and three relevant tags.
You MUST return ONLY a single, valid JSON object, formatted *exactly* like this:
{
  "filename": "<a-concise-and-descriptive-filename>",
  "tags": ["<tag1>", "<tag2>", "<tag3>"]
}
"""
# --- END CONFIGURATION ---

def encode_image(image_path: Path) -> Optional[str]:
    """Encodes a single image to base64. Returns None on failure."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"[Encoder] Error encoding {image_path.name}: {e}", file=sys.stderr)
        return None

def get_all_test_images(directory: Path) -> List[Path]:
    """Gets all supported images from the test directory."""
    supported_ext = ['.jpg', '.jpeg', '.png', '.rw2']
    images = [
        p for p in directory.glob("**/*") 
        if p.is_file() and p.suffix.lower() in supported_ext
    ]
    if not images:
        print(f"FATAL: No images found in {directory}", file=sys.stderr)
        sys.exit(1)
    return images

def process_single_image(image_path: Path) -> Tuple[str, str]:
    """
    Worker function: hits the Ollama API for a single image.
    Returns a tuple of (image_name, status_message)
    """
    base64_image = encode_image(image_path)
    if not base64_image:
        return image_path.name, "FAIL: Could not encode image"

    payload = {
        "model": MODEL_NAME,
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
        response = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        content = response.json()['message']['content']
        
        # Test if the output is valid JSON
        try:
            json.loads(content)
            # We got valid JSON. This is a success.
            return image_path.name, f"✅ SUCCESS: {content.strip()}"
        except json.JSONDecodeError:
            return image_path.name, f"❌ FAIL: Model returned invalid JSON: {content}"

    except requests.exceptions.Timeout:
        return image_path.name, "❌ FAIL: Request timed out"
    except requests.exceptions.HTTPError as e:
        return image_path.name, f"❌ FAIL: HTTP Error {e}"
    except Exception as e:
        return image_path.name, f"❌ FAIL: Unexpected error {e}"

if __name__ == "__main__":
    if not TEST_IMAGE_DIR.exists():
        print(f"FATAL: Test image directory not found at: {TEST_IMAGE_DIR}", file=sys.stderr)
        sys.exit(1)
        
    print("--- Testing Phase 1.5: Batch Stress Test ---")
    print(f"Model: {MODEL_NAME}")
    print(f"Test Directory: {TEST_IMAGE_DIR}")
    print(f"Max Workers: {MAX_WORKERS}\n")

    images_to_process = get_all_test_images(TEST_IMAGE_DIR)
    print(f"Found {len(images_to_process)} images to process...")
    
    start_time = time.time()
    results = {"success": 0, "fail": 0}
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Create all the future tasks
        future_to_image = {
            executor.submit(process_single_image, img_path): img_path 
            for img_path in images_to_process
        }
        
        # Process them as they complete
        for future in as_completed(future_to_image):
            image_name, message = future.result()
            print(f"[{image_name}] {message}")
            
            if "SUCCESS" in message:
                results["success"] += 1
            else:
                results["fail"] += 1

    end_time = time.time()
    total_time = end_time - start_time

    print("\n--- BATCH TEST COMPLETE ---")
    print(f"Total Images: {len(images_to_process)}")
    print(f"✅ Successes:  {results['success']}")
    print(f"❌ Failures:   {results['fail']}")
    print(f"\nTotal Time Taken: {total_time:.2f} seconds")
    avg_time = total_time / len(images_to_process)
    print(f"Average Time per Image: {avg_time:.2f} seconds")