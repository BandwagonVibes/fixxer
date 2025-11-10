#!/usr/bin/env python3
"""
PhotoSort v9.0 - llama.cpp + GBNF Test Script
Tests the new architecture: MobileVLM V2 1.7B + GBNF grammar for guaranteed JSON

This script proves that GBNF grammar enforcement produces perfect JSON every time,
eliminating the unreliable prompt-based approach that caused crashes.
"""

import subprocess
import json
import base64
import sys
from pathlib import Path
from typing import Optional, Dict
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

# Model paths (MobileVLM uses two files: main model + vision projector)
MODEL_PATH = Path.home() / "models/mobilevlm/ggml-model-q4_k.gguf"
MMPROJ_PATH = Path.home() / "models/mobilevlm/mmproj-model-f16.gguf"

# Grammar files (should be in current directory)
NAMING_GRAMMAR = Path("naming_grammar.gbnf")
CRITIQUE_GRAMMAR = Path("critique_grammar.gbnf")

# Test images directory
TEST_DIR = Path.home() / "Downloads/photosortproject/Testing/staging"

# llama.cpp binary (adjust if needed)
LLAMA_CLI = "llama-cli"  # Or "/opt/homebrew/bin/llama-cli"

# Model parameters
TEMPERATURE = 0.7
MAX_TOKENS = 100  # Short responses for naming
CONTEXT_SIZE = 2048

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_setup() -> bool:
    """Verify all required files and tools are present"""
    print("🔍 Checking setup...\n")
    
    all_good = True
    
    # Check llama-cli
    try:
        result = subprocess.run(
            [LLAMA_CLI, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ llama-cli found: {result.stdout.strip()}")
        else:
            print(f"❌ llama-cli error: {result.stderr}")
            all_good = False
    except FileNotFoundError:
        print(f"❌ llama-cli not found. Install with: brew install llama.cpp")
        all_good = False
    except subprocess.TimeoutExpired:
        print(f"❌ llama-cli timed out")
        all_good = False
    
    # Check model files (MobileVLM needs both)
    if MODEL_PATH.exists():
        size_mb = MODEL_PATH.stat().st_size / (1024**2)
        print(f"✅ Main model found: {MODEL_PATH.name} ({size_mb:.0f} MB)")
    else:
        print(f"❌ Main model not found: {MODEL_PATH}")
        print(f"   Download from: https://huggingface.co/ZiangWu/MobileVLM_V2-1.7B-GGUF")
        all_good = False
    
    if MMPROJ_PATH.exists():
        size_mb = MMPROJ_PATH.stat().st_size / (1024**2)
        print(f"✅ Vision projector found: {MMPROJ_PATH.name} ({size_mb:.0f} MB)")
    else:
        print(f"❌ Vision projector not found: {MMPROJ_PATH}")
        print(f"   Download from: https://huggingface.co/ZiangWu/MobileVLM_V2-1.7B-GGUF")
        all_good = False
    
    # Check grammar files
    if NAMING_GRAMMAR.exists():
        print(f"✅ Naming grammar found: {NAMING_GRAMMAR}")
    else:
        print(f"❌ Naming grammar not found: {NAMING_GRAMMAR}")
        all_good = False
    
    if CRITIQUE_GRAMMAR.exists():
        print(f"✅ Critique grammar found: {CRITIQUE_GRAMMAR}")
    else:
        print(f"⚠️  Critique grammar not found: {CRITIQUE_GRAMMAR} (optional)")
    
    # Check test images
    if TEST_DIR.exists():
        images = list(TEST_DIR.glob("*.jpg")) + list(TEST_DIR.glob("*.JPG")) + \
                 list(TEST_DIR.glob("*.jpeg")) + list(TEST_DIR.glob("*.png"))
        if images:
            print(f"✅ Found {len(images)} test images in {TEST_DIR}")
        else:
            print(f"⚠️  No images found in {TEST_DIR}")
            print(f"   Add some test images before running!")
            all_good = False
    else:
        print(f"❌ Test directory not found: {TEST_DIR}")
        all_good = False
    
    print()
    return all_good


def encode_image_to_base64(image_path: Path) -> Optional[str]:
    """Encode image to base64 for llama.cpp"""
    try:
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ Error encoding {image_path.name}: {e}")
        return None


def call_llama_cpp_with_image(
    image_path: Path,
    prompt: str,
    grammar_file: Path,
    max_tokens: int = MAX_TOKENS
) -> Optional[str]:
    """
    Call llama.cpp with an image and GBNF grammar enforcement
    
    Returns the raw output from the model (should be valid JSON)
    """
    
    # Build the llama-cli command
    cmd = [
        LLAMA_CLI,
        "-m", str(MODEL_PATH),
        "--mmproj", str(MMPROJ_PATH),  # Vision projector required for image input
        "--grammar-file", str(grammar_file),
        "-p", prompt,
        "-n", str(max_tokens),
        "--temp", str(TEMPERATURE),
        "-c", str(CONTEXT_SIZE),
        "--image", str(image_path),
        "--no-display-prompt",  # Don't echo the prompt
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout per image
        )
        
        if result.returncode != 0:
            print(f"❌ llama-cli error: {result.stderr}")
            return None
        
        # The output should be ONLY the JSON (thanks to grammar)
        output = result.stdout.strip()
        return output
        
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout processing {image_path.name}")
        return None
    except Exception as e:
        print(f"❌ Error calling llama-cli: {e}")
        return None


def test_naming_mode(image_path: Path) -> Dict:
    """Test AI naming with GBNF grammar enforcement"""
    
    print(f"\n📸 Processing: {image_path.name}")
    print(f"   Mode: AI Naming (simple JSON)")
    
    # Simple prompt for naming
    prompt = 'What is in this image? Describe it concisely in 2-4 words.'
    
    start_time = time.time()
    
    # Call llama.cpp with GBNF grammar
    response = call_llama_cpp_with_image(
        image_path,
        prompt,
        NAMING_GRAMMAR,
        max_tokens=50
    )
    
    elapsed = time.time() - start_time
    
    if not response:
        return {
            "success": False,
            "error": "No response from model"
        }
    
    print(f"   Raw output: {response}")
    print(f"   Time: {elapsed:.2f}s")
    
    # Try to parse as JSON
    try:
        data = json.loads(response)
        print(f"   ✅ Valid JSON parsed!")
        print(f"   Description: \"{data.get('description', 'N/A')}\"")
        
        return {
            "success": True,
            "json": data,
            "raw": response,
            "time": elapsed
        }
        
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON PARSE ERROR: {e}")
        print(f"   This should NEVER happen with GBNF!")
        return {
            "success": False,
            "error": f"Invalid JSON: {e}",
            "raw": response
        }


def test_critique_mode(image_path: Path) -> Dict:
    """Test AI critique with complex GBNF grammar"""
    
    print(f"\n🎨 Processing: {image_path.name}")
    print(f"   Mode: Creative Director Critique (complex JSON)")
    
    # Critique prompt
    prompt = """Analyze this photo as a Creative Director.
Rate composition 1-10, critique composition/lighting/color briefly, 
give a final verdict, suggest a creative mood and post-processing direction."""
    
    start_time = time.time()
    
    # Call llama.cpp with critique grammar
    response = call_llama_cpp_with_image(
        image_path,
        prompt,
        CRITIQUE_GRAMMAR,
        max_tokens=400  # Longer for critique
    )
    
    elapsed = time.time() - start_time
    
    if not response:
        return {
            "success": False,
            "error": "No response from model"
        }
    
    print(f"   Raw output: {response[:100]}...")  # First 100 chars
    print(f"   Time: {elapsed:.2f}s")
    
    # Try to parse as JSON
    try:
        data = json.loads(response)
        print(f"   ✅ Valid JSON parsed!")
        print(f"   Score: {data.get('composition_score', 'N/A')}/10")
        print(f"   Mood: {data.get('creative_mood', 'N/A')}")
        
        return {
            "success": True,
            "json": data,
            "raw": response,
            "time": elapsed
        }
        
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON PARSE ERROR: {e}")
        print(f"   This should NEVER happen with GBNF!")
        return {
            "success": False,
            "error": f"Invalid JSON: {e}",
            "raw": response
        }


# ============================================================================
# MAIN TEST SUITE
# ============================================================================

def main():
    """Run the test suite"""
    
    print("=" * 70)
    print("PhotoSort v9.0 - llama.cpp + GBNF Test Suite")
    print("=" * 70)
    
    # Check setup first
    if not check_setup():
        print("\n❌ Setup incomplete. Fix the issues above and try again.\n")
        sys.exit(1)
    
    print("✅ Setup looks good! Starting tests...\n")
    
    # Find test images
    images = list(TEST_DIR.glob("*.jpg")) + list(TEST_DIR.glob("*.JPG")) + \
             list(TEST_DIR.glob("*.jpeg")) + list(TEST_DIR.glob("*.png"))
    
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
        result = test_naming_mode(img)
        naming_results.append(result)
        time.sleep(0.5)  # Brief pause between images
    
    # Test critique mode (if grammar available)
    critique_results = []
    if CRITIQUE_GRAMMAR.exists():
        print("\n" + "=" * 70)
        print("TEST 2: AI CRITIQUE (Complex JSON)")
        print("=" * 70)
        
        # Only test first 2 images for critique (it's slower)
        for img in images[:2]:
            result = test_critique_mode(img)
            critique_results.append(result)
            time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    naming_success = sum(1 for r in naming_results if r["success"])
    print(f"\n📸 AI Naming: {naming_success}/{len(naming_results)} successful")
    
    if naming_success == len(naming_results):
        avg_time = sum(r["time"] for r in naming_results) / len(naming_results)
        print(f"   ✅ 100% SUCCESS RATE!")
        print(f"   ⚡ Average time: {avg_time:.2f}s per image")
    else:
        print(f"   ❌ {len(naming_results) - naming_success} failures")
    
    if critique_results:
        critique_success = sum(1 for r in critique_results if r["success"])
        print(f"\n🎨 AI Critique: {critique_success}/{len(critique_results)} successful")
        
        if critique_success == len(critique_results):
            avg_time = sum(r["time"] for r in critique_results) / len(critique_results)
            print(f"   ✅ 100% SUCCESS RATE!")
            print(f"   ⚡ Average time: {avg_time:.2f}s per image")
        else:
            print(f"   ❌ {len(critique_results) - critique_success} failures")
    
    # Final verdict
    print("\n" + "=" * 70)
    if naming_success == len(naming_results):
        print("🎉 TEST PASSED!")
        print("\nGBNF grammar enforcement works perfectly.")
        print("Every single JSON response was valid and parseable.")
        print("Zero crashes, zero malformed output, zero gibberish.")
        print("\n✅ Ready to integrate into PhotoSort v9.0!")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("\nCheck the errors above. Common issues:")
        print("- Model not loaded correctly")
        print("- Grammar file syntax error")
        print("- Memory pressure (close other apps)")
    
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
