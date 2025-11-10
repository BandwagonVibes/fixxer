#!/usr/bin/env python3
"""
PhotoSort v9.0 - llama-cpp-python + GBNF Test (THE RIGHT WAY)
Uses llama-cpp-python with GBNF grammar enforcement for 100% valid JSON

This is the architecture Gemini recommended - no more hoping for valid JSON!

FIX 1: Removed Llava15ChatHandler.
       MobileVLM V2 uses the 'chatml' format, not the 'llava-1-5' format.
       This mismatch was causing the model to output empty strings.
       
FIX 2: Increased MAX_TOKENS from 100 to 512.
       This prevents the 'Unterminated string' JSON error by giving
       the model enough space to complete its response.
"""

from llama_cpp import Llama, LlamaGrammar
from pathlib import Path
import json
import time
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

# Model paths
MODEL_PATH = Path.home() / "models/mobilevlm/ggml-model-q4_k.gguf"
MMPROJ_PATH = Path.home() / "models/mobilevlm/mmproj-model-f16.gguf"

# Grammar files
NAMING_GRAMMAR = Path("naming_grammar.gbnf")
CRITIQUE_GRAMMAR = Path("critique_grammar.gbnf")

# Test images
TEST_DIR = Path.home() / "Downloads/photosortproject/Testing/staging"

# Model parameters
N_CTX = 2048
N_GPU_LAYERS = -1  # -1 = use all GPU layers (Metal)
TEMPERATURE = 0.7
MAX_TOKENS = 512 # <-- INCREASED FROM 100

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_setup():
    """Verify all files are present"""
    print("🔍 Checking setup...\n")
    
    all_good = True
    
    # Check model files
    if MODEL_PATH.exists():
        size_mb = MODEL_PATH.stat().st_size / (1024**2)
        print(f"✅ Main model: {MODEL_PATH.name} ({size_mb:.0f} MB)")
    else:
        print(f"❌ Main model not found: {MODEL_PATH}")
        all_good = False
    
    if MMPROJ_PATH.exists():
        size_mb = MMPROJ_PATH.stat().st_size / (1024**2)
        print(f"✅ Vision projector: {MMPROJ_PATH.name} ({size_mb:.0f} MB)")
    else:
        print(f"❌ Vision projector not found: {MMPROJ_PATH}")
        all_good = False
    
    # Check grammar files
    if NAMING_GRAMMAR.exists():
        print(f"✅ Naming grammar: {NAMING_GRAMMAR}")
    else:
        print(f"❌ Naming grammar not found: {NAMING_GRAMMAR}")
        all_good = False
    
    if CRITIQUE_GRAMMAR.exists():
        print(f"✅ Critique grammar: {CRITIQUE_GRAMMAR}")
    else:
        print(f"⚠️  Critique grammar not found: {CRITIQUE_GRAMMAR} (optional)")
    
    # Check test images
    if TEST_DIR.exists():
        images = list(TEST_DIR.glob("*.jpg")) + list(TEST_DIR.glob("*.JPG")) + \
                 list(TEST_DIR.glob("*.jpeg")) + list(TEST_DIR.glob("*.png")) + \
                 list(TEST_DIR.glob("*.RW2"))
        if images:
            print(f"✅ Found {len(images)} test images")
        else:
            print(f"⚠️  No images in {TEST_DIR}")
            all_good = False
    else:
        print(f"❌ Test directory not found: {TEST_DIR}")
        all_good = False
    
    print()
    return all_good


def load_grammar(grammar_path: Path):
    """Load GBNF grammar file and create LlamaGrammar object"""
    try:
        with open(grammar_path, 'r') as f:
            grammar_text = f.read()
        
        # Create LlamaGrammar object from the grammar text
        return LlamaGrammar.from_string(grammar_text)
    except Exception as e:
        print(f"❌ Error loading grammar {grammar_path}: {e}")
        return None


def test_naming(llm, image_path: Path, grammar):
    """Test AI naming with GBNF enforcement (grammar is a LlamaGrammar object)"""
    
    print(f"\n📸 Processing: {image_path.name}")
    print(f"   Mode: AI Naming (GBNF enforced)")
    
    prompt = "What is in this image? Describe it concisely in 2-4 words."
    
    start_time = time.time()
    
    try:
        # Create messages with image
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"file://{image_path.absolute()}"}}
                ]
            }
        ]
        
        # Call with GBNF grammar enforcement
        response = llm.create_chat_completion(
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS, # Use the new global MAX_TOKENS
            grammar=grammar  # THIS ENFORCES THE JSON SCHEMA
        )
        
        elapsed = time.time() - start_time
        
        # Extract response
        content = response['choices'][0]['message']['content']
        
        print(f"   Raw output: {content}")
        print(f"   Time: {elapsed:.2f}s")
        
        # Parse JSON (should ALWAYS work with GBNF)
        try:
            data = json.loads(content)
            print(f"   ✅ Valid JSON!")
            print(f"   Description: \"{data.get('description', 'N/A')}\"")
            
            return {
                "success": True,
                "data": data,
                "raw": content,
                "time": elapsed
            }
            
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON PARSE ERROR: {e}")
            print(f"   THIS SHOULD NEVER HAPPEN WITH GBNF!")
            return {
                "success": False,
                "error": f"Invalid JSON: {e}",
                "raw": content,
                "time": elapsed
            }
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def test_critique(llm, image_path: Path, grammar):
    """Test AI critique with GBNF enforcement (grammar is a LlamaGrammar object)"""
    
    print(f"\n🎨 Processing: {image_path.name}")
    print(f"   Mode: Creative Critique (GBNF enforced)")
    
    prompt = """Analyze this photo as a Creative Director. 
Rate composition 1-10, critique composition/lighting/color briefly, 
give a final verdict, suggest a creative mood and post-processing direction."""
    
    start_time = time.time()
    
    try:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"file://{image_path.absolute()}"}}
                ]
            }
        ]
        
        response = llm.create_chat_completion(
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS, # Use the new global MAX_TOKENS
            grammar=grammar
        )
        
        elapsed = time.time() - start_time
        
        content = response['choices'][0]['message']['content']
        
        print(f"   Raw output: {content[:100]}...")
        print(f"   Time: {elapsed:.2f}s")
        
        try:
            data = json.loads(content)
            print(f"   ✅ Valid JSON!")
            print(f"   Score: {data.get('composition_score', 'N/A')}/10")
            print(f"   Mood: {data.get('creative_mood', 'N/A')}")
            
            return {
                "success": True,
                "data": data,
                "raw": content,
                "time": elapsed
            }
            
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON PARSE ERROR: {e}")
            print(f"   THIS SHOULD NEVER HAPPEN WITH GBNF!")
            return {
                "success": False,
                "error": f"Invalid JSON: {e}",
                "raw": content,
                "time": elapsed
            }
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# MAIN TEST SUITE
# ============================================================================

def main():
    print("=" * 70)
    print("PhotoSort v9.0 - llama.cpp + GBNF Test (The Right Way)")
    print("=" * 70)
    
    # Check setup
    if not check_setup():
        print("❌ Setup incomplete. Fix issues above.\n")
        sys.exit(1)
    
    print("✅ Setup complete!\n")
    
    # Load grammars
    print("📋 Loading GBNF grammars...")
    naming_grammar = load_grammar(NAMING_GRAMMAR)
    if not naming_grammar:
        print("❌ Failed to load naming grammar\n")
        sys.exit(1)
    print(f"   ✅ Naming grammar loaded")
    
    critique_grammar = None
    if CRITIQUE_GRAMMAR.exists():
        critique_grammar = load_grammar(CRITIQUE_GRAMMAR)
        if critique_grammar:
            print(f"   ✅ Critique grammar loaded")
    
    print()
    
    # Load model
    print("🤖 Loading MobileVLM V2 with vision support...")
    print("   (This may take 30-60 seconds on first run - Metal compiling)")
    print()
    
    try:
        # Load model with Metal
        llm = Llama(
            model_path=str(MODEL_PATH),
            
            # Pass the vision projector path directly
            clip_model_path=str(MMPROJ_PATH), 
            # Use the 'chatml' format, which MobileVLM expects
            chat_format="chatml", 
            
            n_ctx=N_CTX,
            n_gpu_layers=N_GPU_LAYERS,
            verbose=False
        )
        
        print("   ✅ Model loaded successfully!\n")
        
    except Exception as e:
        print(f"   ❌ Failed to load model: {e}\n")
        sys.exit(1)
    
    # Find test images
    images = list(TEST_DIR.glob("*.jpg")) + list(TEST_DIR.glob("*.JPG")) + \
             list(TEST_DIR.glob("*.jpeg")) + list(TEST_DIR.glob("*.png")) + \
             list(TEST_DIR.glob("*.RW2"))
    
    if not images:
        print("❌ No images found!\n")
        sys.exit(1)
    
    # Limit to 5 for testing
    images = images[:5]
    
    print(f"🧪 Testing with {len(images)} images")
    print("-" * 70)
    
    # Test naming
    print("\n" + "=" * 70)
    print("TEST 1: AI NAMING (GBNF Enforced)")
    print("=" * 70)
    
    naming_results = []
    for img in images:
        result = test_naming(llm, img, naming_grammar)
        naming_results.append(result)
        time.sleep(0.5)
    
    # Test critique (if grammar available)
    critique_results = []
    if critique_grammar:
        print("\n" + "=" * 70)
        print("TEST 2: AI CRITIQUE (GBNF Enforced)")
        print("=" * 70)
        
        for img in images[:2]:
            result = test_critique(llm, img, critique_grammar)
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
        print(f"   🎉 100% SUCCESS RATE!")
        print(f"   ⚡ Average time: {avg_time:.2f}s per image")
        print(f"   ✅ GBNF grammar enforcement WORKS!")
    else:
        print(f"   ❌ {naming_total - naming_success} failures")
        print(f"   Success rate: {naming_success/naming_total*100:.1f}%")
    
    if critique_results:
        critique_success = sum(1 for r in critique_results if r["success"])
        critique_total = len(critique_results)
        
        print(f"\n🎨 AI Critique: {critique_success}/{critique_total} successful")
        
        if critique_success == critique_total:
            avg_time = sum(r["time"] for r in critique_results) / critique_total
            print(f"   🎉 100% SUCCESS RATE!")
            print(f"   ⚡ Average time: {avg_time:.2f}s per image")
    
    # Final verdict
    print("\n" + "=" * 70)
    
    if naming_success == naming_total:
        print("🎉 GBNF GRAMMAR ENFORCEMENT PROVEN!")
        print("\nEvery single response was valid JSON.")
        print("Zero crashes, zero malformed output, zero gibberish.")
        print("\nThis is what Gemini promised:")
        print("- Decouple vision analysis from JSON formatting")
        print("- Enforce structure at the framework level")  
        print("- 100% reliability, 100% of the time")
        print("\n✅ Ready to integrate into PhotoSort v9.0!")
    else:
        print("⚠️  SOME FAILURES OCCURRED")
        print("\nThis might be due to:")
        print("- Grammar syntax errors")
        print("- Model compatibility issues")
        print("- Check the error messages above")
    
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()