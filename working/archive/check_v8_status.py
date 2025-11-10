#!/usr/bin/env python3
"""
check_v8_status.py - Comprehensive v8.0 Status Checker

Run this in your actual PhotoSort environment to see what's available.

Author: Claude (Anthropic) + Nick (∞vision crew)
"""

import sys
from pathlib import Path

print("=" * 70)
print("PhotoSort v8.0 - Comprehensive Status Check")
print("=" * 70)

# ==============================================================================
# Python Environment
# ==============================================================================
print("\n🐍 Python Environment:")
print(f"  Version: {sys.version}")
print(f"  Executable: {sys.executable}")

# ==============================================================================
# Core Dependencies
# ==============================================================================
print("\n📦 Core Dependencies:")

deps_status = {}

# Test sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    deps_status['sentence-transformers'] = '✓'
    try:
        version = SentenceTransformer.__version__
        deps_status['sentence-transformers'] += f' ({version})'
    except:
        pass
except ImportError:
    deps_status['sentence-transformers'] = '✗'

# Test scikit-learn
try:
    import sklearn
    deps_status['scikit-learn'] = f'✓ ({sklearn.__version__})'
except ImportError:
    deps_status['scikit-learn'] = '✗'

# Test OpenCV
try:
    import cv2
    deps_status['opencv-python'] = f'✓ ({cv2.__version__})'
except ImportError:
    deps_status['opencv-python'] = '✗'

# Test PIL
try:
    from PIL import Image
    deps_status['Pillow'] = '✓'
    try:
        import PIL
        deps_status['Pillow'] += f' ({PIL.__version__})'
    except:
        pass
except ImportError:
    deps_status['Pillow'] = '✗'

# Test numpy
try:
    import numpy as np
    deps_status['numpy'] = f'✓ ({np.__version__})'
except ImportError:
    deps_status['numpy'] = '✗'

# Test BRISQUE (multiple import paths)
brisque_available = False
brisque_method = None
try:
    from image_quality import brisque
    brisque_available = True
    brisque_method = 'image-quality'
except ImportError:
    try:
        from imquality import brisque
        brisque_available = True
        brisque_method = 'imquality'
    except ImportError:
        try:
            import brisque
            brisque_available = True
            brisque_method = 'brisque'
        except ImportError:
            pass

if brisque_available:
    deps_status['BRISQUE'] = f'✓ (via {brisque_method})'
else:
    deps_status['BRISQUE'] = '✗ (will use Laplacian patch fallback)'

for pkg, status in deps_status.items():
    print(f"  {status:50} {pkg}")

# ==============================================================================
# v8.0 Engines
# ==============================================================================
print("\n🔧 v8.0 Engines:")

engines_available = {}

# Test burst_engine
try:
    import burst_engine
    deps = burst_engine.check_dependencies()
    if deps['all_available']:
        engines_available['burst_engine'] = '✓ CLIP burst detection ready'
    else:
        engines_available['burst_engine'] = '⚠️  Loaded but missing dependencies'
        if not deps['clip_available']:
            engines_available['burst_engine'] += ' (no CLIP)'
except ImportError:
    engines_available['burst_engine'] = '✗ Module not found'

# Test cull_engine
try:
    import cull_engine
    deps = cull_engine.check_dependencies()
    if deps['any_method_available']:
        method = deps.get('recommended_method', 'unknown')
        engines_available['cull_engine'] = f'✓ Quality assessment ready ({method})'
    else:
        engines_available['cull_engine'] = '✗ No quality assessment method available'
except ImportError:
    engines_available['cull_engine'] = '✗ Module not found'

# Test integration layer
try:
    import photosort_v8_integration as v8
    status = v8.get_v8_status()
    if status['v8_engines_available']:
        engines_available['integration'] = '✓ Integration layer ready'
    else:
        engines_available['integration'] = '✗ Integration layer loaded but engines missing'
except ImportError:
    engines_available['integration'] = '✗ Module not found'

for engine, status in engines_available.items():
    print(f"  {status}")

# ==============================================================================
# Cache System
# ==============================================================================
print("\n💾 Cache System:")

cache_available = False
try:
    import burst_engine
    cache_info = burst_engine.get_cache_info()
    cache_available = True
    print(f"  Location: {cache_info['cache_location']}")
    print(f"  Entries: {cache_info['total_entries']}")
    print(f"  Size: {cache_info['total_size_mb']:.2f} MB")
    print(f"  Model: {cache_info['model_name']} ({cache_info['model_version']})")
except:
    print("  ✗ Cache system not available")

# ==============================================================================
# Ollama
# ==============================================================================
print("\n🤖 Ollama:")

ollama_ok = False
try:
    import subprocess
    import requests
    
    # Check if ollama command exists
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("  ✓ Ollama CLI available")
        
        # Parse models
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            models = []
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    models.append(parts[0])
            
            if 'openbmb/minicpm-v2.6:q4_K_M' in models:
                print("  ✓ MiniCPM-V 2.6 installed")
                ollama_ok = True
            else:
                print("  ⚠️  MiniCPM-V 2.6 not found")
                print("  Available models:", ', '.join(models[:3]) + '...' if len(models) > 3 else ', '.join(models))
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        if response.status_code == 200:
            print("  ✓ Ollama server running")
        else:
            print("  ⚠️  Ollama server not responding correctly")
    except:
        print("  ✗ Ollama server not running")
        
except Exception as e:
    print(f"  ✗ Ollama not available: {e}")

# ==============================================================================
# RAW Support
# ==============================================================================
print("\n🖼️  RAW Support:")

try:
    import subprocess
    result = subprocess.run(['dcraw'], capture_output=True, timeout=1)
    print("  ✓ dcraw available (RAW files supported)")
except FileNotFoundError:
    print("  ⚠️  dcraw not found (limited RAW support)")
except:
    print("  ⚠️  dcraw check failed")

# ==============================================================================
# Summary
# ==============================================================================
print("\n" + "=" * 70)
print("Summary:")
print("=" * 70)

all_deps_ok = all(status.startswith('✓') for status in deps_status.values() if 'BRISQUE' not in status)
burst_ok = engines_available.get('burst_engine', '').startswith('✓')
cull_ok = engines_available.get('cull_engine', '').startswith('✓')

if burst_ok and cull_ok and ollama_ok:
    print("✅ PhotoSort v8.0 is FULLY OPERATIONAL!")
    print("\nYou can now:")
    print("  • Use CLIP burst detection (semantic grouping)")
    if brisque_available:
        print("  • Use BRISQUE quality assessment (bokeh-aware)")
    else:
        print("  • Use Laplacian patch quality assessment (bokeh-aware)")
    print("  • Use consolidated VLM analysis")
    print("\nNext steps:")
    print("  1. Test on sample photos")
    print("  2. Calibrate thresholds")
    print("  3. Integrate with photosort.py")
    
elif not burst_ok:
    print("⚠️  Burst engine not fully operational")
    if not deps_status['sentence-transformers'].startswith('✓'):
        print("\n❌ Missing: sentence-transformers")
        print("Fix: pip install sentence-transformers")
    print("\nYou can still use:")
    print("  • Legacy imagehash burst detection")
    if cull_ok:
        print("  • v8.0 quality assessment")
        
elif not cull_ok:
    print("⚠️  Cull engine not operational")
    print("Missing both BRISQUE and OpenCV")
    print("\nFix: pip install opencv-python")
    if burst_ok:
        print("\nYou can still use:")
        print("  • v8.0 CLIP burst detection")
        
elif not ollama_ok:
    print("⚠️  Ollama not fully configured")
    print("\nFix:")
    print("  1. Start Ollama: ollama serve")
    print("  2. Pull model: ollama pull openbmb/minicpm-v2.6:q4_K_M")

else:
    print("⚠️  Some components not available")
    print("\nRun setup wizard: python setup_photosort.py --install")

print("\n" + "=" * 70)

# ==============================================================================
# Detailed Recommendations
# ==============================================================================

if not all_deps_ok or not burst_ok or not cull_ok:
    print("\n📋 Detailed Installation Commands:")
    print("=" * 70)
    
    if not deps_status['sentence-transformers'].startswith('✓'):
        print("\n# Install sentence-transformers (for CLIP burst detection):")
        print("pip install sentence-transformers")
    
    if not deps_status['opencv-python'].startswith('✓'):
        print("\n# Install OpenCV (for Laplacian fallback):")
        print("pip install opencv-python")
    
    if not brisque_available:
        print("\n# Optional: Try installing BRISQUE (may not work):")
        print("pip install image-quality")
        print("# If that fails, Laplacian patch fallback will be used (works great!)")
    
    if not ollama_ok:
        print("\n# Setup Ollama:")
        print("ollama pull openbmb/minicpm-v2.6:q4_K_M")
    
    print("\n" + "=" * 70)

print("\n💡 For help:")
print("  python photosort.py --help")
print("\n🐛 For issues:")
print("  Check this output and install missing dependencies")
