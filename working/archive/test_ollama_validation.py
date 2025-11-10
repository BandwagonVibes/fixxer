#!/usr/bin/env python3
"""
PhotoSort v9.0 - Ollama + JSON Validation Test
Quick validation test using your existing Ollama setup

This proves the concept of strict validation without needing llama.cpp setup.
"""

import requests
import json
import base64
import time
from pathlib import Path
from typing import Optional, Dict
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "openbmb/minicpm-v2.6:q4_K_M"  # Full model name with quantization
TEST_DIR = Path.home() / "Downloads/photosortproject/Testing/staging"
TIMEOUT = 60  # seconds per image

# JSON Schemas for validation
NAMING_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {"type": "string", "minLength": 1, "maxLength": 100}
    },
    "required": ["description"],
    "additionalProperties": False
}

CRITIQUE_SCHEMA = {
    "type": "object",
    "properties": {
        "composition_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "composition_critique": {"type": "string", "minLength": 1},
        "lighting_critique": {"type": "string", "minLength": 1},
        "color_critique": {"type": "string", "minLength": 1},
        "final_verdict": {"type": "string", "minLength": 1},
        "creative_mood": {"type": "string", "minLength": 1},
        "creative_suggestion": {"type": "string", "minLength": 1}
    },
    "required": [
        "composition_score", "composition_critique", "lighting_critique",
        "color_critique", "final_verdict", "creative_mood", "creative_suggestion"
    ],
    "additionalProperties": False
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_setup() -> bool:
    """Check if Ollama is running and model is available"""
    print("🔍 Checking setup...\n")
    
    all_good = True
    
    # Check Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]
            print(f"✅ Ollama running with {len(models)} models")
            
            # Check if our model is available (handle different name formats)
            model_check = any(
                MODEL_NAME in name or 
                name.startswith(MODEL_NAME) or
                MODEL_NAME in name.split(':')[0]
                for name in model_names
            )
            
            if model_check:
                print(f"✅ Model found: {MODEL_NAME}")
            else:
                print(f"⚠️  Model '{MODEL_NAME}' not found. Available models:")
                for name in model_names:
                    print(f"   - {name}")
                print(f"\n   Try: ollama pull minicpm-v2.6")
                all_good = False
        else:
            print(f"❌ Ollama API error: {response.status_code}")
            all_good = False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama. Is it running?")
        print("   Start it with: ollama serve")
        all_good = False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        all_good = False
    
    # Check test images
    if TEST_DIR.exists():
        images = list(TEST_DIR.glob("*.jpg")) + list(TEST_DIR.glob("*.JPG")) + \
                 list(TEST_DIR.glob("*.jpeg")) + list(TEST_DIR.glob("*.png")) + \
                 list(TEST_DIR.glob("*.RW2"))
        if images:
            print(f"✅ Found {len(images)} test images in {TEST_DIR}")
        else:
            print(f"⚠️  No images found in {TEST_DIR}")
            all_good = False
    else:
        print(f"❌ Test directory not found: {TEST_DIR}")
        all_good = False
    
    print()
    return all_good


def encode_image(image_path: Path) -> Optional[str]:
    """Encode image to base64"""
    try:
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ Error encoding {image_path.name}: {e}")
        return None


def validate_json(data: dict, schema: dict) -> tuple[bool, Optional[str]]:
    """
    Validate JSON against schema
    Returns (is_valid, error_message)
    """
    try:
        # Check type
        if not isinstance(data, dict):
            return False, f"Expected object, got {type(data).__name__}"
        
        # Check required fields
        for field in schema.get("required", []):
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Check no extra fields
        if not schema.get("additionalProperties", True):
            extra = set(data.keys()) - set(schema["properties"].keys())
            if extra:
                return False, f"Extra fields not allowed: {extra}"
        
        # Check field types and constraints
        for field, value in data.items():
            if field not in schema["properties"]:
                continue
            
            prop_schema = schema["properties"][field]
            expected_type = prop_schema.get("type")
            
            # Type check
            if expected_type == "string" and not isinstance(value, str):
                return False, f"Field '{field}' must be string, got {type(value).__name__}"
            elif expected_type == "integer" and not isinstance(value, int):
                return False, f"Field '{field}' must be integer, got {type(value).__name__}"
            
            # String constraints
            if expected_type == "string":
                min_len = prop_schema.get("minLength", 0)
                max_len = prop_schema.get("maxLength", float('inf'))
                if len(value) < min_len:
                    return False, f"Field '{field}' too short (min {min_len})"
                if len(value) > max_len:
                    return False, f"Field '{field}' too long (max {max_len})"
            
            # Integer constraints
            if expected_type == "integer":
                min_val = prop_schema.get("minimum", float('-inf'))
                max_val = prop_schema.get("maximum", float('inf'))
                if value < min_val or value > max_val:
                    return False, f"Field '{field}' out of range ({min_val}-{max_val})"
        
        return True, None
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def call_ollama(image_path: Path, prompt: str, schema: dict) -> Dict:
    """
    Call Ollama with an image and validate the JSON response
    Returns dict with success status and data/error
    """
    
    # Encode image
    base64_image = encode_image(image_path)
    if not base64_image:
        return {"success": False, "error": "Failed to encode image"}
    
    # Build request for /api/chat endpoint
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [base64_image]
            }
        ],
        "stream": False
    }
    
    start_time = time.time()
    
    try:
        # Call Ollama
        response = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        
        result = response.json()
        raw_content = result['message']['content'].strip()  # /api/chat uses 'message.content'
        
        elapsed = time.time() - start_time
        
        # Try to parse as JSON
        try:
            # Strip markdown code blocks if present
            if raw_content.startswith("```"):
                lines = raw_content.split("\n")
                raw_content = "\n".join(lines[1:-1])  # Remove first and last lines
            
            data = json.loads(raw_content)
            
            # Validate against schema
            is_valid, error_msg = validate_json(data, schema)
            
            if is_valid:
                return {
                    "success": True,
                    "data": data,
                    "raw": raw_content,
                    "time": elapsed
                }
            else:
                return {
                    "success": False,
                    "error": f"Schema validation failed: {error_msg}",
                    "data": data,
                    "raw": raw_content,
                    "time": elapsed
                }
                
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON: {str(e)}",
                "raw": raw_content,
                "time": elapsed
            }
            
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


def test_naming(image_path: Path) -> Dict:
    """Test AI naming with simple JSON schema"""
    
    print(f"\n📸 Processing: {image_path.name}")
    print(f"   Mode: AI Naming (simple JSON)")
    
    prompt = """What is in this image? Describe it concisely for a file name.
Respond ONLY with valid JSON in this exact format:
{
  "description": "your 2-4 word description"
}"""
    
    result = call_ollama(image_path, prompt, NAMING_SCHEMA)
    
    if result["success"]:
        print(f"   ✅ Valid JSON!")
        print(f"   Description: \"{result['data']['description']}\"")
        print(f"   Time: {result['time']:.2f}s")
    else:
        print(f"   ❌ FAILED: {result['error']}")
        if "raw" in result:
            print(f"   Raw output: {result['raw'][:100]}...")
        if "time" in result:
            print(f"   Time: {result['time']:.2f}s")
    
    return result


def test_critique(image_path: Path) -> Dict:
    """Test AI critique with complex JSON schema"""
    
    print(f"\n🎨 Processing: {image_path.name}")
    print(f"   Mode: Creative Director Critique (complex JSON)")
    
    prompt = """Analyze this photo as a Creative Director. Respond ONLY with valid JSON in this exact format:
{
  "composition_score": 8,
  "composition_critique": "Brief one-sentence critique",
  "lighting_critique": "Brief one-sentence critique",
  "color_critique": "Brief one-sentence critique",
  "final_verdict": "One-sentence summary",
  "creative_mood": "Single creative mood",
  "creative_suggestion": "Detailed post-processing suggestion"
}"""
    
    result = call_ollama(image_path, prompt, CRITIQUE_SCHEMA)
    
    if result["success"]:
        print(f"   ✅ Valid JSON!")
        print(f"   Score: {result['data']['composition_score']}/10")
        print(f"   Mood: {result['data']['creative_mood']}")
        print(f"   Time: {result['time']:.2f}s")
    else:
        print(f"   ❌ FAILED: {result['error']}")
        if "raw" in result:
            print(f"   Raw output: {result['raw'][:100]}...")
        if "time" in result:
            print(f"   Time: {result['time']:.2f}s")
    
    return result


# ============================================================================
# MAIN TEST SUITE
# ============================================================================

def main():
    """Run the test suite"""
    
    print("=" * 70)
    print("PhotoSort v9.0 - Ollama + JSON Validation Test")
    print("=" * 70)
    
    # Check setup
    if not check_setup():
        print("\n❌ Setup incomplete. Fix the issues above and try again.\n")
        sys.exit(1)
    
    print("✅ Setup looks good! Starting tests...\n")
    
    # Find test images
    images = list(TEST_DIR.glob("*.jpg")) + list(TEST_DIR.glob("*.JPG")) + \
             list(TEST_DIR.glob("*.jpeg")) + list(TEST_DIR.glob("*.png")) + \
             list(TEST_DIR.glob("*.RW2"))
    
    if not images:
        print("❌ No images found to test!")
        sys.exit(1)
    
    # Limit to first 5 for quick testing
    images = images[:5]
    
    print(f"🧪 Testing with {len(images)} images\n")
    print("-" * 70)
    
    # Test naming mode
    print("\n" + "=" * 70)
    print("TEST 1: AI NAMING (Simple JSON)")
    print("=" * 70)
    
    naming_results = []
    for img in images:
        result = test_naming(img)
        naming_results.append(result)
        time.sleep(0.5)
    
    # Test critique mode (just 2 images - it's slower)
    print("\n" + "=" * 70)
    print("TEST 2: AI CRITIQUE (Complex JSON)")
    print("=" * 70)
    
    critique_results = []
    for img in images[:2]:
        result = test_critique(img)
        critique_results.append(result)
        time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    naming_success = sum(1 for r in naming_results if r["success"])
    naming_total = len(naming_results)
    
    print(f"\n📸 AI Naming: {naming_success}/{naming_total} successful")
    
    if naming_success == naming_total:
        avg_time = sum(r["time"] for r in naming_results) / naming_total
        print(f"   ✅ 100% SUCCESS RATE!")
        print(f"   ⚡ Average time: {avg_time:.2f}s per image")
    else:
        print(f"   ❌ {naming_total - naming_success} failures")
        print(f"   Success rate: {naming_success/naming_total*100:.1f}%")
        
        # Show failure reasons
        failures = [r for r in naming_results if not r["success"]]
        print(f"\n   Failure reasons:")
        for r in failures:
            print(f"   - {r['error']}")
    
    if critique_results:
        critique_success = sum(1 for r in critique_results if r["success"])
        critique_total = len(critique_results)
        
        print(f"\n🎨 AI Critique: {critique_success}/{critique_total} successful")
        
        if critique_success == critique_total:
            avg_time = sum(r["time"] for r in critique_results) / critique_total
            print(f"   ✅ 100% SUCCESS RATE!")
            print(f"   ⚡ Average time: {avg_time:.2f}s per image")
        else:
            print(f"   ❌ {critique_total - critique_success} failures")
            print(f"   Success rate: {critique_success/critique_total*100:.1f}%")
    
    # Final verdict
    print("\n" + "=" * 70)
    
    if naming_success == naming_total and (not critique_results or critique_success == len(critique_results)):
        print("🎉 ALL TESTS PASSED!")
        print("\nOllama with strict JSON validation works!")
        print("Next step: Move to llama.cpp + GBNF for production.")
    elif naming_success > 0:
        print("⚠️  PARTIAL SUCCESS")
        print(f"\nSuccess rate: {naming_success/naming_total*100:.1f}%")
        print("This shows why GBNF grammar enforcement is needed.")
    else:
        print("❌ ALL TESTS FAILED")
        print("\nCheck:")
        print("- Is Ollama running? (ollama serve)")
        print("- Is the model downloaded? (ollama pull minicpm-v2.6)")
        print("- Are the images valid?")
    
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
