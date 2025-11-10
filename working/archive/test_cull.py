#!/usr/bin/env python3
"""
test_cull.py - Test BRISQUE Quality Assessment Engine

Tests the v8.0 quality assessment on your sample photos.
Run this to validate BRISQUE correctly identifies keepers vs duds.

Author: Claude (Anthropic) + Nick (∞vision crew)
"""

from pathlib import Path
import sys
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

# BRISQUE thresholds (tune these based on results)
KEEPER_THRESHOLD = 35.0  # Below this = definite keeper
AMBIGUOUS_THRESHOLD = 50.0  # Above this = likely dud

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.rw2', '.cr2', '.nef', '.arw', '.dng'}

# Number of images to test (set to None for all)
MAX_TEST_IMAGES = 20  # Start with 20 for quick testing

# ==============================================================================
# TEST SCRIPT
# ==============================================================================

def main():
    print("=" * 70)
    print("PhotoSort v8.0 - Quality Assessment Test")
    print("=" * 70)
    
    # Check directory exists
    if not TEST_DIR.exists():
        print(f"\n❌ Error: Test directory not found: {TEST_DIR}")
        print("   Please check the path and try again")
        sys.exit(1)
    
    print(f"\n📁 Test Directory: {TEST_DIR}")
    
    # Check dependencies
    deps = cull_engine.check_dependencies()
    print("\n📦 Dependencies:")
    print(f"  BRISQUE: {'✓' if deps['brisque_available'] else '✗'}")
    print(f"  Laplacian: {'✓' if deps['laplacian_available'] else '✗'}")
    print(f"  PIL: {'✓' if deps['pil_available'] else '✗'}")
    
    if not deps['any_method_available']:
        print("\n❌ No quality assessment method available. Cannot proceed.")
        print("   Run: python setup_photosort.py --install")
        sys.exit(1)
    
    method = deps.get('recommended_method', 'unknown')
    print(f"\n⚙️  Using method: {method}")
    
    # Get image files
    print(f"\n🔍 Scanning for images...")
    image_files = []
    for ext in SUPPORTED_EXTENSIONS:
        image_files.extend(list(TEST_DIR.glob(f"*{ext}")))
        image_files.extend(list(TEST_DIR.glob(f"*{ext.upper()}")))
    
    if not image_files:
        print(f"❌ No images found in {TEST_DIR}")
        print(f"   Looking for: {', '.join(SUPPORTED_EXTENSIONS)}")
        sys.exit(1)
    
    image_files.sort(key=lambda p: p.name)
    
    # Limit test set if specified
    if MAX_TEST_IMAGES and len(image_files) > MAX_TEST_IMAGES:
        print(f"   Found {len(image_files)} images (testing first {MAX_TEST_IMAGES})")
        image_files = image_files[:MAX_TEST_IMAGES]
    else:
        print(f"   Found {len(image_files)} images")
    
    # Test parameters
    print(f"\n⚙️  Test Parameters:")
    print(f"   Keeper threshold: < {KEEPER_THRESHOLD}")
    print(f"   Ambiguous range: {KEEPER_THRESHOLD}-{AMBIGUOUS_THRESHOLD}")
    print(f"   Dud threshold: > {AMBIGUOUS_THRESHOLD}")
    
    # Run quality assessment
    print("\n" + "=" * 70)
    print("Running Quality Assessment...")
    print("=" * 70)
    
    results = {
        'keeper': [],
        'ambiguous': [],
        'dud': []
    }
    
    start_time = time.time()
    
    for i, img_path in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] {img_path.name}")
        
        # Assess quality
        if deps['brisque_available']:
            result = cull_engine.assess_with_brisque(img_path)
        elif deps['laplacian_available']:
            result = cull_engine.assess_with_laplacian_patch(img_path)
        else:
            continue
        
        if result:
            score = result['score']
            verdict = result['verdict']
            method_used = result['method']
            
            print(f"  Score: {score:.1f} → {verdict.upper()}")
            
            # Categorize
            results[verdict].append({
                'path': img_path,
                'score': score,
                'method': method_used
            })
        else:
            print(f"  ⚠️  Assessment failed")
    
    elapsed = time.time() - start_time
    
    # Display results
    print("\n" + "=" * 70)
    print("Results Summary:")
    print("=" * 70)
    
    print(f"\n📊 Statistics:")
    print(f"   Total images: {len(image_files)}")
    print(f"   Keepers: {len(results['keeper'])} ({len(results['keeper'])/len(image_files)*100:.1f}%)")
    print(f"   Ambiguous: {len(results['ambiguous'])} ({len(results['ambiguous'])/len(image_files)*100:.1f}%)")
    print(f"   Duds: {len(results['dud'])} ({len(results['dud'])/len(image_files)*100:.1f}%)")
    print(f"   Processing time: {elapsed:.2f}s ({elapsed/len(image_files)*1000:.1f}ms per image)")
    
    # Show detailed breakdown
    if results['keeper']:
        print(f"\n✅ KEEPERS ({len(results['keeper'])} images):")
        print("   (Low score = good quality)")
        for item in sorted(results['keeper'], key=lambda x: x['score'])[:10]:
            print(f"   {item['score']:5.1f} - {item['path'].name}")
        if len(results['keeper']) > 10:
            print(f"   ... and {len(results['keeper']) - 10} more")
    
    if results['ambiguous']:
        print(f"\n⚠️  AMBIGUOUS ({len(results['ambiguous'])} images):")
        print("   (These would be sent to VLM for analysis)")
        for item in sorted(results['ambiguous'], key=lambda x: x['score'])[:10]:
            print(f"   {item['score']:5.1f} - {item['path'].name}")
        if len(results['ambiguous']) > 10:
            print(f"   ... and {len(results['ambiguous']) - 10} more")
    
    if results['dud']:
        print(f"\n❌ DUDS ({len(results['dud'])} images):")
        print("   (High score = poor quality)")
        for item in sorted(results['dud'], key=lambda x: x['score'], reverse=True)[:10]:
            print(f"   {item['score']:5.1f} - {item['path'].name}")
        if len(results['dud']) > 10:
            print(f"   ... and {len(results['dud']) - 10} more")
    
    # Validation guidance
    print("\n" + "=" * 70)
    print("✅ Quality assessment complete!")
    print("\nValidation checklist:")
    print("  ☐ Bokeh portraits in KEEPERS? (not falsely marked as duds)")
    print("  ☐ Blurry/out-of-focus shots in DUDS?")
    print("  ☐ Edge cases in AMBIGUOUS? (will go to VLM)")
    print("  ☐ Score distribution makes sense?")
    
    print("\n💡 Tuning tips:")
    if len(results['dud']) > len(results['keeper']):
        print("  ⚠️  Too many duds! Thresholds might be too strict")
        print("  → Try increasing keeper_threshold to 40-45")
    elif len(results['keeper']) > len(image_files) * 0.8:
        print("  ⚠️  Almost everything is a keeper. Too lenient?")
        print("  → Try decreasing keeper_threshold to 30-32")
    else:
        print("  ✓ Distribution looks reasonable!")
    
    if len(results['ambiguous']) > len(image_files) * 0.5:
        print("\n  ⚠️  Many ambiguous cases (VLM will be busy)")
        print("  → Adjust thresholds to reduce VLM workload")
    
    # Next steps
    print("\n📋 Next Steps:")
    print("  1. Review the categorization above")
    print("  2. Check if bokeh photos are correctly kept")
    print("  3. Verify blurry photos are duds")
    print("  4. If needed, adjust thresholds in test script")
    print("  5. Run test_vlm.py to test VLM consolidation")
    
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
