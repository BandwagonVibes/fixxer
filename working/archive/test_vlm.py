#!/usr/bin/env python3
"""
test_vlm.py - Test Consolidated VLM Analysis

Tests the v8.0 VLM consolidation (cull + name + critique in one call).
Run this to validate MiniCPM-V 2.6 returns perfect JSON.

Author: Claude (Anthropic) + Nick (∞vision crew)
"""

from pathlib import Path
import sys
import json
import time

# Import the cull engine
try:
    import cull_engine
except ImportError:
    print("❌ Error: cull_engine.py not found in current directory")
    print("   Make sure all v8.0 files are in the same folder as this script")
    sys.exit(1)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Your test photo directory
TEST_DIR = Path("~/Downloads/photosortproject/Testing/staging").expanduser()

# VLM configuration
VLM_MODEL = "openbmb/minicpm-v2.6:q4_K_M"
OLLAMA_URL = "http://localhost:11434/api/chat"

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic'}  # VLM works best with these

# Number of images to test (VLM is slow, so keep it small)
MAX_TEST_IMAGES = 3  # Start with 3 images

# ==============================================================================
# TEST SCRIPT
# ==============================================================================

def print_json_pretty(data, indent=2):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent, ensure_ascii=False))

def main():
    print("=" * 70)
    print("PhotoSort v8.0 - VLM Consolidated Analysis Test")
    print("=" * 70)
    
    # Check directory exists
    if not TEST_DIR.exists():
        print(f"\n❌ Error: Test directory not found: {TEST_DIR}")
        print("   Please check the path and try again")
        sys.exit(1)
    
    print(f"\n📁 Test Directory: {TEST_DIR}")
    
    # Check Ollama
    print(f"\n🤖 VLM Configuration:")
    print(f"   Model: {VLM_MODEL}")
    print(f"   Endpoint: {OLLAMA_URL}")
    
    import requests
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print(f"   Status: ✓ Ollama running")
        else:
            print(f"   Status: ✗ Ollama not responding")
            sys.exit(1)
    except:
        print(f"   Status: ✗ Cannot connect to Ollama")
        print("\n💡 Make sure Ollama is running:")
        print("   ollama serve")
        sys.exit(1)
    
    # Get image files
    print(f"\n🔍 Scanning for images...")
    image_files = []
    for ext in SUPPORTED_EXTENSIONS:
        image_files.extend(list(TEST_DIR.glob(f"*{ext}")))
        image_files.extend(list(TEST_DIR.glob(f"*{ext.upper()}")))
    
    if not image_files:
        print(f"❌ No supported images found in {TEST_DIR}")
        print(f"   Looking for: {', '.join(SUPPORTED_EXTENSIONS)}")
        print(f"   Note: RAW files not recommended for this test (slow)")
        sys.exit(1)
    
    image_files.sort(key=lambda p: p.name)
    
    # Limit test set
    if len(image_files) > MAX_TEST_IMAGES:
        print(f"   Found {len(image_files)} images (testing first {MAX_TEST_IMAGES})")
        print(f"   💡 This is intentionally limited - VLM analysis is slow (~1-3s per image)")
        image_files = image_files[:MAX_TEST_IMAGES]
    else:
        print(f"   Found {len(image_files)} images")
    
    # Run VLM analysis
    print("\n" + "=" * 70)
    print("Running VLM Consolidated Analysis...")
    print("=" * 70)
    print("\n⏳ This will take a while (~2-5 seconds per image)...")
    print("   Making tea is recommended ☕\n")
    
    results = []
    
    for i, img_path in enumerate(image_files, 1):
        print("=" * 70)
        print(f"[{i}/{len(image_files)}] {img_path.name}")
        print("=" * 70)
        
        start_time = time.time()
        
        # Get VLM analysis
        analysis = cull_engine.get_vlm_analysis(
            img_path,
            model_name=VLM_MODEL,
            ollama_url=OLLAMA_URL
        )
        
        elapsed = time.time() - start_time
        
        if analysis:
            print(f"✓ Analysis complete ({elapsed:.1f}s)\n")
            
            # Display technical assessment
            print("📊 TECHNICAL ASSESSMENT:")
            tech = analysis.get('technical', {})
            print(f"   Keep: {tech.get('is_keeper', 'N/A')}")
            print(f"   Dud: {tech.get('is_dud', 'N/A')}")
            if tech.get('dud_reason'):
                print(f"   Dud Reason: {tech.get('dud_reason')}")
            print(f"   Notes: {tech.get('technical_notes', 'N/A')}")
            
            # Display naming
            print("\n📝 FILE NAMING:")
            naming = analysis.get('naming', {})
            print(f"   Suggested: {naming.get('suggested_filename', 'N/A')}")
            print(f"   Subject: {naming.get('subject', 'N/A')}")
            if naming.get('location_type'):
                print(f"   Location: {naming.get('location_type')}")
            if naming.get('time_of_day'):
                print(f"   Time: {naming.get('time_of_day')}")
            
            # Display critique
            print("\n🎨 CREATIVE CRITIQUE:")
            critique = analysis.get('critique', {})
            print(f"   Score: {critique.get('overall_score', 'N/A')}/10")
            print(f"   Composition: {critique.get('composition', 'N/A')}")
            print(f"   Lighting: {critique.get('lighting', 'N/A')}")
            print(f"   Technical: {critique.get('technical_quality', 'N/A')}")
            
            if critique.get('strengths'):
                print(f"\n   ✓ Strengths:")
                for strength in critique.get('strengths', []):
                    print(f"     • {strength}")
            
            if critique.get('improvements'):
                print(f"\n   💡 Improvements:")
                for improvement in critique.get('improvements', []):
                    print(f"     • {improvement}")
            
            if critique.get('mood'):
                print(f"\n   🌟 Mood: {critique.get('mood')}")
            
            # Store result
            results.append({
                'filename': img_path.name,
                'analysis': analysis,
                'elapsed_time': elapsed
            })
            
        else:
            print(f"❌ Analysis failed ({elapsed:.1f}s)")
            print("   Possible reasons:")
            print("   • VLM timeout")
            print("   • Image encoding issue")
            print("   • Invalid JSON response")
            
            results.append({
                'filename': img_path.name,
                'analysis': None,
                'elapsed_time': elapsed
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    
    successful = [r for r in results if r['analysis']]
    failed = [r for r in results if not r['analysis']]
    
    print(f"\n📊 Statistics:")
    print(f"   Total images: {len(results)}")
    print(f"   Successful: {len(successful)}")
    print(f"   Failed: {len(failed)}")
    
    if successful:
        avg_time = sum(r['elapsed_time'] for r in successful) / len(successful)
        print(f"   Avg time: {avg_time:.1f}s per image")
    
    # Validation checklist
    print("\n✅ Validation Checklist:")
    
    if successful:
        all_have_technical = all(r['analysis'].get('technical') for r in successful)
        all_have_naming = all(r['analysis'].get('naming') for r in successful)
        all_have_critique = all(r['analysis'].get('critique') for r in successful)
        
        print(f"   {'✓' if all_have_technical else '✗'} All responses have technical assessment")
        print(f"   {'✓' if all_have_naming else '✗'} All responses have naming suggestion")
        print(f"   {'✓' if all_have_critique else '✗'} All responses have creative critique")
        
        # Check JSON structure
        valid_json = True
        for r in successful:
            tech = r['analysis'].get('technical', {})
            if not isinstance(tech.get('is_keeper'), bool):
                valid_json = False
                break
            if not isinstance(tech.get('is_dud'), bool):
                valid_json = False
                break
        
        print(f"   {'✓' if valid_json else '✗'} JSON structure is valid")
        
        if all_have_technical and all_have_naming and all_have_critique and valid_json:
            print("\n🎉 VLM consolidation is working perfectly!")
        else:
            print("\n⚠️  Some issues detected - check output above")
    
    # Next steps
    print("\n📋 Next Steps:")
    if len(successful) == len(results):
        print("  ✅ VLM working correctly!")
        print("  1. Review the naming suggestions - are they good?")
        print("  2. Check critiques - are they useful?")
        print("  3. Verify cull decisions make sense")
        print("  4. Ready to integrate into photosort.py!")
    else:
        print("  ⚠️  Some VLM calls failed")
        print("  1. Check if Ollama is responding: ollama list")
        print("  2. Try testing with different images")
        print("  3. Check Ollama logs for errors")
    
    # Save full results
    output_file = Path("vlm_test_results.json")
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Full results saved to: {output_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save results: {e}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
