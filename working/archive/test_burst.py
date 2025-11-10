#!/usr/bin/env python3
"""
test_burst.py - Test CLIP Burst Detection Engine

Tests the v8.0 burst detection on your sample photos.
Run this to validate CLIP semantic grouping works correctly.

Author: Claude (Anthropic) + Nick (∞vision crew)
"""

from pathlib import Path
import sys
import time

# Import the burst engine
try:
    import burst_engine
except ImportError:
    print("❌ Error: burst_engine.py not found in current directory")
    print("   Make sure all v8.0 files are in the same folder as this script")
    sys.exit(1)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Your test photo directory
TEST_DIR = Path("~/Downloads/photosortproject/Testing/staging").expanduser()

# CLIP clustering parameters (tune these based on results)
CLIP_EPS = 0.15  # Lower = stricter grouping (0.10-0.25)
MIN_BURST_SIZE = 2  # Minimum images to form a burst

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.rw2', '.cr2', '.nef', '.arw', '.dng'}

# ==============================================================================
# TEST SCRIPT
# ==============================================================================

def main():
    print("=" * 70)
    print("PhotoSort v8.0 - Burst Detection Test")
    print("=" * 70)
    
    # Check directory exists
    if not TEST_DIR.exists():
        print(f"\n❌ Error: Test directory not found: {TEST_DIR}")
        print("   Please check the path and try again")
        sys.exit(1)
    
    print(f"\n📁 Test Directory: {TEST_DIR}")
    
    # Check dependencies
    deps = burst_engine.check_dependencies()
    print("\n📦 Dependencies:")
    print(f"  CLIP: {'✓' if deps['clip_available'] else '✗'}")
    print(f"  DBSCAN: {'✓' if deps['dbscan_available'] else '✗'}")
    print(f"  PIL: {'✓' if deps['pil_available'] else '✗'}")
    
    if not deps['all_available']:
        print("\n❌ Missing dependencies. Cannot proceed.")
        print("   Run: python setup_photosort.py --install")
        sys.exit(1)
    
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
    print(f"   Found {len(image_files)} images")
    
    # List files
    print("\n📋 Files to analyze:")
    for i, img in enumerate(image_files[:20], 1):  # Show first 20
        print(f"   {i:2d}. {img.name}")
    if len(image_files) > 20:
        print(f"   ... and {len(image_files) - 20} more")
    
    # Test parameters
    print(f"\n⚙️  Test Parameters:")
    print(f"   CLIP eps: {CLIP_EPS} (clustering threshold)")
    print(f"   Min burst size: {MIN_BURST_SIZE}")
    
    # Progress callback
    def progress_callback(current, total, is_cache_hit):
        if current == 1:
            print(f"\n⚡ Processing {total} images...")
        
        if is_cache_hit is not None:
            status = "cached" if is_cache_hit else "new"
            if current % 10 == 0 or current == total:
                print(f"   [{current}/{total}] {status}")
    
    # Run burst detection
    print("\n" + "=" * 70)
    print("Running CLIP Burst Detection...")
    print("=" * 70)
    
    start_time = time.time()
    
    burst_groups, stats = burst_engine.find_burst_groups(
        image_files,
        eps=CLIP_EPS,
        min_samples=MIN_BURST_SIZE,
        progress_callback=progress_callback
    )
    
    elapsed = time.time() - start_time
    
    # Display results
    print("\n" + "=" * 70)
    print("Results:")
    print("=" * 70)
    
    print(f"\n📊 Statistics:")
    print(f"   Total images: {stats['total_images']}")
    print(f"   Embeddings generated: {stats['embeddings_generated']}")
    print(f"   Burst groups found: {stats['burst_groups_found']}")
    print(f"   Images in bursts: {stats['images_in_bursts']}")
    print(f"   Singleton images: {stats['total_images'] - stats['images_in_bursts']}")
    print(f"   Processing time: {elapsed:.2f}s ({elapsed/len(image_files)*1000:.1f}ms per image)")
    
    if stats['burst_groups_found'] == 0:
        print("\n✨ No burst groups found - all images are unique!")
        print("\nThis could mean:")
        print("  • Your images are genuinely all different")
        print("  • CLIP eps threshold is too strict (try increasing to 0.20)")
        print("  • Images are from different subjects/scenes")
        
    else:
        print(f"\n📸 Burst Groups Detected:")
        print("=" * 70)
        
        for i, group in enumerate(burst_groups, 1):
            print(f"\nBurst {i} ({len(group)} images):")
            for img in group:
                print(f"  • {img.name}")
        
        print("\n" + "=" * 70)
        print("✅ Burst detection complete!")
        print("\nValidation checklist:")
        print("  ☐ Similar shots grouped together?")
        print("  ☐ Different subjects in separate groups?")
        print("  ☐ Group sizes look reasonable?")
        print("  ☐ No obvious false positives/negatives?")
        
        print("\n💡 Tuning tips:")
        print("  • Too many groups (over-splitting)?")
        print("    → Increase eps to 0.18-0.20")
        print("  • Groups too large (false positives)?")
        print("    → Decrease eps to 0.12-0.14")
    
    # Cache info
    cache_info = burst_engine.get_cache_info()
    print(f"\n💾 Cache Status:")
    print(f"   Location: {cache_info['cache_location']}")
    print(f"   Entries: {cache_info['total_entries']}")
    print(f"   Size: {cache_info['total_size_mb']:.2f} MB")
    
    print("\n🔄 Next run will use cached embeddings (instant!)")
    print("   Try running this script again to see the speedup!")
    
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
