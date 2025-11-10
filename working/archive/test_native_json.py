#!/usr/bin/env python3
"""
PhotoSort v9 Test Harness - Phase 1: Native JSON

Tests the "Native JSON" hypothesis from the project debrief.
Uses the 'Qwen2.5-VL-3B-Instruct' model via the standard Ollama API
to see if it can reliably produce structured JSON without GBNF.
"""

import os
import base64
import requests
import json
from pathlib import Path
import random
import sys

# --- CONFIGURATION ---
OLLAMA_URL = "http://localhost:11434/api/chat"
# Path 1 Model: The "Native JSON" candidate
MODEL_NAME = "qwen2.5vl:3b" 
TEST_IMAGE_DIR = Path.home() / "Downloads/photosortproject/Testing/staging"
# The simple prompt for AI naming
AI_NAMING_PROMPT = """You are an expert file-naming AI. 
Analyze this image and generate a concise, descriptive filename and three relevant tags.
You MUST return ONLY a single, valid JSON object, formatted *exactly* like this:
{
  "filename": "<a-concise-and-descriptive-filename>",
  "tags": ["<tag1>", "<tag2>", "<tag3>"]
}
"""
# --- END CONFIGURATION ---

def encode_image(image_path: Path) -> str:
    """Encodes a single image to base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_random_test_image(directory: Path) -> Path:
    """Picks a random image from the test directory."""
    supported_ext = ['.jpg', '.jpeg', '.png', '.rw2']
    images = [
        p for p in directory.glob("**/*") 
        if p.is_file() and p.suffix.lower() in supported_ext
    ]
    if not images:
        print(f"FATAL: No images found in {directory}", file=sys.stderr)
        sys.exit(1)
    return random.choice(images)

def test_model_native_json(image_path: Path):
    """
    Hits the Ollama API with the specified model and prompt.
    """
    print(f"--- Testing Phase 1: Native JSON ---")
    print(f"Model: {MODEL_NAME}")
    print(f"Image: {image_path.name}\n")
    
    try:
        base64_image = encode_image(image_path)
    except Exception as e:
        print(f"Error encoding image: {e}")
        return

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
        "format": "json" # We'll ask for JSON format
    }

    print("Sending request to Ollama...")
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        content = result['message']['content']
        
        print("--- RAW OLLAMA RESPONSE (content field) ---")
        print(content)
        print("-------------------------------------------\n")

        # Test if the output is valid JSON
        print("Attempting to parse response as JSON...")
        try:
            parsed_json = json.loads(content)
            print("✅ SUCCESS: Response is valid JSON.")
            print(json.dumps(parsed_json, indent=2))
        except json.JSONDecodeError as e:
            print(f"❌ FAILURE: Response is NOT valid JSON.")
            print(f"   Error: {e}")

    except requests.exceptions.ConnectionError:
        print(f"❌ FATAL: ConnectionError. Is Ollama running?")
    except requests.exceptions.Timeout:
        print(f"❌ FAILURE: Request timed out.")
    except requests.exceptions.HTTPError as e:
        print(f"❌ FAILURE: HTTP Error. Does the model '{MODEL_NAME}' exist?")
        print(f"   Run: ollama pull {MODEL_NAME}")
        print(f"   Error details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if not TEST_IMAGE_DIR.exists():
        print(f"FATAL: Test image directory not found at:", file=sys.stderr)
        print(f"{TEST_IMAGE_DIR}", file=sys.stderr)
        sys.exit(1)
        
    test_image = get_random_test_image(TEST_IMAGE_DIR)
    test_model_native_json(test_image)