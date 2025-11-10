# PhotoSort v8.0 Migration Guide

## Overview

This guide shows you exactly how to integrate the v8.0 CLIP + BRISQUE engines into your existing `photosort.py` file.

**What's changing:**
- Burst stacking: imagehash → CLIP + DBSCAN
- Quality culling: Laplacian → BRISQUE + VLM cascade
- VLM consolidation: Separate calls → Single consolidated call

**What's staying the same:**
- All your UI/UX code
- Progress bars and session tracking
- File organization logic
- Config file system
- All other features (EXIF, prep, etc.)

---

## Step 1: Add New Imports

**Location:** Top of `photosort.py` (around line 43, after existing imports)

```python
# ==============================================================================
# NEW v8.0 IMPORTS
# ==============================================================================

# v8.0: AI-powered engines
try:
    import burst_engine
    import cull_engine
    import photosort_v8_integration as v8
    V8_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  v8.0 engines not available: {e}")
    print("   Run: python setup_photosort.py --install")
    V8_AVAILABLE = False
```

---

## Step 2: Update Configuration Defaults

**Location:** Around line 150-200, in the constants section

Add these new configuration options:

```python
# ==============================================================================
# v8.0 ALGORITHM CONFIGURATION
# ==============================================================================

# Algorithm selection
DEFAULT_BURST_ALGORITHM = 'clip'  # 'clip' (v8.0) or 'legacy' (imagehash)
DEFAULT_CULL_ALGORITHM = 'brisque'  # 'brisque' (v8.0) or 'legacy' (Laplacian)

# CLIP/DBSCAN parameters for burst detection
DEFAULT_CLIP_EPS = 0.15  # Cosine distance threshold (lower = stricter grouping)
DEFAULT_CLIP_MIN_SAMPLES = 2  # Minimum burst size

# BRISQUE thresholds for quality assessment
DEFAULT_BRISQUE_KEEPER = 35.0  # Below this = definite keeper (skip VLM)
DEFAULT_BRISQUE_AMBIGUOUS = 50.0  # Above this = likely dud (send to VLM)

# VLM consolidation
DEFAULT_VLM_CONSOLIDATED = True  # Use consolidated VLM (cull + name + critique in one call)
```

---

## Step 3: Update Config File Parser

**Location:** `load_config()` function (around line 250-350)

Add v8.0 config options to the default config:

```python
def load_config() -> dict:
    """Load config from ~/.photosort.conf or create default."""
    config_path = Path.home() / ".photosort.conf"
    config = configparser.ConfigParser()

    if config_path.exists():
        config.read(config_path)
    else:
        # Create default config
        config['paths'] = {
            'default_destination': str(Path.home() / 'Pictures' / 'PhotoSort_Archive'),
            'prep_folder_name': '_0_for_Lightroom',
        }
        
        config['models'] = {
            'default_model': 'bakllava',
            'critique_model': 'openbmb/minicpm-v2.6:q4_K_M',
        }
        
        # NEW v8.0 section
        config['algorithms'] = {
            'burst_algorithm': 'clip',
            'burst_clip_eps': '0.15',
            'burst_clip_min_samples': '2',
            'cull_algorithm': 'brisque',
            'cull_brisque_keeper_threshold': '35.0',
            'cull_brisque_ambiguous_threshold': '50.0',
            'vlm_consolidated_mode': 'true',
        }
        
        config['culling_thresholds'] = {
            # ... existing thresholds ...
        }
        
        # ... rest of config ...
```

Parse the v8.0 config in the return statement:

```python
    # Parse and return config
    return {
        'default_destination': Path(config.get('paths', 'default_destination')),
        'prep_folder_name': config.get('paths', 'prep_folder_name'),
        'default_model': config.get('models', 'default_model'),
        'critique_model': config.get('models', 'critique_model'),
        
        # NEW v8.0 config
        'burst_algorithm': config.get('algorithms', 'burst_algorithm', fallback='clip'),
        'burst_clip_eps': config.getfloat('algorithms', 'burst_clip_eps', fallback=0.15),
        'burst_clip_min_samples': config.getint('algorithms', 'burst_clip_min_samples', fallback=2),
        'cull_algorithm': config.get('algorithms', 'cull_algorithm', fallback='brisque'),
        'cull_brisque_keeper_threshold': config.getfloat('algorithms', 'cull_brisque_keeper_threshold', fallback=35.0),
        'cull_brisque_ambiguous_threshold': config.getfloat('algorithms', 'cull_brisque_ambiguous_threshold', fallback=50.0),
        'vlm_consolidated_mode': config.getboolean('algorithms', 'vlm_consolidated_mode', fallback=True),
        
        # ... existing config items ...
    }
```

---

## Step 4: Update `group_bursts_in_directory()`

**Location:** Around line 1260

Replace the entire function with this v8.0-aware version:

```python
def group_bursts_in_directory(directory: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """
    (V6.2) Groups similar burst photos using perceptual hashing.
    (V8.0) Now uses CLIP+DBSCAN for semantic grouping with configurable fallback.
    """
    
    print(f"\n{'='*60}")
    print(f" 📸 BakLLaVA Photo Organizer --- (Burst Stack Mode)")
    print(f"{'='*60}")
    
    algorithm = APP_CONFIG.get('burst_algorithm', 'clip')
    
    # Check if v8.0 is available and requested
    if algorithm == 'clip' and V8_AVAILABLE:
        print(f" Using v8.0 CLIP-based semantic grouping")
        print(f" Clustering threshold (eps): {APP_CONFIG.get('burst_clip_eps', 0.15)}")
    elif algorithm == 'clip' and not V8_AVAILABLE:
        print(f" ⚠️  v8.0 CLIP engine not available, falling back to legacy")
        algorithm = 'legacy'
    else:
        print(f" Using legacy imagehash grouping")
    
    print(f" Analyzing images in: {directory}")
    
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if len(image_files) < 2:
        print("     Not enough images to compare. Exiting.")
        return

    # V8.0 CLIP PATH
    if algorithm == 'clip' and V8_AVAILABLE:
        print("\n Generating CLIP embeddings...")
        
        pbar = None
        if TQDM_AVAILABLE:
            pbar = SmartProgressBar(total=len(image_files), desc="   Analyzing", unit="img")
        
        # Use v8.0 CLIP burst detection
        from photosort_v8_integration import stack_bursts_with_clip, ProgressAdapter
        
        progress_cb = ProgressAdapter(pbar, "   Analyzing") if pbar else None
        burst_groups, stats = stack_bursts_with_clip(
            image_files,
            eps=APP_CONFIG.get('burst_clip_eps', 0.15),
            min_samples=APP_CONFIG.get('burst_clip_min_samples', 2),
            progress_callback=progress_cb
        )
        
        if pbar:
            pbar.close()
        
        # Show cache stats
        if progress_cb:
            cache_stats = progress_cb.get_stats()
            if cache_stats['cache_hits'] + cache_stats['cache_misses'] > 0:
                hit_rate = (cache_stats['cache_hits'] / (cache_stats['cache_hits'] + cache_stats['cache_misses'])) * 100
                print(f"\n Cache performance: {hit_rate:.0f}% hits ({cache_stats['cache_hits']} cached, {cache_stats['cache_misses']} new)")
        
        if not burst_groups:
            print("\n No burst groups found. All images are unique!")
            return
            
        print(f"\n Found {stats['burst_groups_found']} burst groups ({stats['images_in_bursts']} images)")
    
    # LEGACY IMAGEHASH PATH
    else:
        # ... [KEEP YOUR EXISTING IMAGEHASH CODE HERE] ...
        # Lines 1310-1395 from your current photosort.py
        pass
    
    # COMMON: Analyze for best picks and organize
    # ... [KEEP YOUR EXISTING ORGANIZATION CODE HERE] ...
    # Lines 1367-1430 from your current photosort.py
```

---

## Step 5: Update `cull_images_in_directory()`

**Location:** Around line 1443

Replace with this v8.0-aware version:

```python
def cull_images_in_directory(directory: Path, dry_run: bool, APP_CONFIG: dict, max_workers: int = MAX_WORKERS):
    """
    (V6.0) Finds and groups images by technical quality.
    (V8.0) Now uses BRISQUE+VLM cascade with consolidated analysis.
    """
    
    print(f"\n{'='*60}")
    print(f" 🗑️  BakLLaVA Photo Organizer --- (Cull Mode)")
    print(f"{'='*60}")
    
    algorithm = APP_CONFIG.get('cull_algorithm', 'brisque')
    
    # Check if v8.0 is available and requested
    if algorithm == 'brisque' and V8_AVAILABLE:
        print(f" Using v8.0 BRISQUE+VLM cascade")
        print(f" Keeper threshold: {APP_CONFIG.get('cull_brisque_keeper_threshold', 35.0)}")
        print(f" Ambiguous threshold: {APP_CONFIG.get('cull_brisque_ambiguous_threshold', 50.0)}")
    elif algorithm == 'brisque' and not V8_AVAILABLE:
        print(f" ⚠️  v8.0 BRISQUE engine not available, falling back to legacy")
        algorithm = 'legacy'
    else:
        print(f" Using legacy Laplacian variance")
    
    print(f" Analyzing technical quality in: {directory}")
    
    image_files = [
        f for f in directory.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if not image_files:
        print("     No supported images to analyze. Exiting.")
        return

    # V8.0 BRISQUE PATH
    if algorithm == 'brisque' and V8_AVAILABLE:
        print("\n  Stage 1: BRISQUE quality screening...")
        
        pbar = None
        if TQDM_AVAILABLE:
            pbar = SmartProgressBar(total=len(image_files), desc="   Assessing", unit="img")
        
        # Use v8.0 BRISQUE+VLM cascade
        from photosort_v8_integration import assess_images_with_cascade, ProgressAdapter
        
        progress_cb = ProgressAdapter(pbar, "   Assessing") if pbar else None
        results = assess_images_with_cascade(
            image_files,
            keeper_threshold=APP_CONFIG.get('cull_brisque_keeper_threshold', 35.0),
            ambiguous_threshold=APP_CONFIG.get('cull_brisque_ambiguous_threshold', 50.0),
            use_vlm=True,
            vlm_model=APP_CONFIG.get('critique_model', 'openbmb/minicpm-v2.6:q4_K_M'),
            progress_callback=progress_cb
        )
        
        if pbar:
            pbar.close()
        
        # Categorize results
        keepers = []
        duds = []
        maybe = []
        naming_data = {}
        critique_data = {}
        
        vlm_count = 0
        for path, result in results.items():
            if result.get('error'):
                continue
            
            if result['final_verdict'] == 'keeper':
                keepers.append(path)
            elif result['final_verdict'] == 'dud':
                duds.append(path)
            
            if result.get('needs_review'):
                maybe.append(path)
            
            if result.get('stage2_result'):
                vlm_count += 1
                # Store consolidated naming and critique data
                if result.get('naming'):
                    naming_data[path] = result['naming']
                if result.get('critique'):
                    critique_data[path] = result['critique']
        
        print(f"\n  Stage 2: VLM analyzed {vlm_count} ambiguous images")
        print(f"\n Found {len(keepers)} Keepers, {len(maybe)} Maybes, and {len(duds)} Duds.")
        
        # Save naming and critique JSON sidecars
        if naming_data or critique_data:
            print(f"  Saving {len(naming_data)} AI naming/critique sidecars...")
            save_naming_and_critiques(naming_data, critique_data)
    
    # LEGACY LAPLACIAN PATH  
    else:
        # ... [KEEP YOUR EXISTING LAPLACIAN CODE HERE] ...
        # Lines 1460-1515 from your current photosort.py
        pass
    
    # COMMON: Organize into folders
    # ... [KEEP YOUR EXISTING ORGANIZATION CODE HERE] ...
    # Lines 1516-1564 from your current photosort.py
```

---

## Step 6: Add Helper Function for Sidecar Saving

**Location:** Add this new function near the culling functions (around line 1565)

```python
def save_naming_and_critiques(naming_data: Dict[Path, Dict], critique_data: Dict[Path, Dict]):
    """
    (V8.0) Save AI naming and critique data as JSON sidecars.
    Consolidates data from VLM cascade into single sidecar file.
    """
    import json
    
    # Combine naming and critique into single JSON sidecar
    for path in set(naming_data.keys()) | set(critique_data.keys()):
        sidecar_data = {}
        
        if path in naming_data:
            sidecar_data['naming'] = naming_data[path]
        
        if path in critique_data:
            sidecar_data['critique'] = critique_data[path]
        
        if sidecar_data:
            json_path = path.with_suffix('.json')
            try:
                with open(json_path, 'w') as f:
                    json.dump(sidecar_data, f, indent=2)
            except Exception as e:
                print(f"    Failed to save JSON for {path.name}: {e}")
```

---

## Step 7: Update Version Header

**Location:** Top of file (around line 3-30)

```python
#!/usr/bin/env python3
"""
BakLLaVA Photo Organizer - PhotoSort v8.0

AI-powered photography workflow automation tool.

Created by: Nick (∞vision crew)
Engineered by: Claude (Anthropic) + Gemini (Google)

Features:
- Auto Mode: Complete automated workflow (Stack → Cull → AI-Name → Archive)
- AI Critique: Creative Director analysis with JSON sidecars
- Burst Stacking: v8.0 CLIP semantic grouping (deterministic, robust)
- Quality Culling: v8.0 BRISQUE+VLM cascade (bokeh-aware)
- EXIF Insights: Session analytics dashboard
- Smart Prep: Copy keepers to Lightroom folder
- v8.0 NEW: CLIP embeddings, BRISQUE quality, consolidated VLM, content-based caching

Tech Stack:
- Local AI via Ollama (minicpm-v2.6 for perfect JSON)
- CLIP embeddings (sentence-transformers)
- BRISQUE quality assessment (image-quality)
- DBSCAN clustering (scikit-learn)
- RAW support via dcraw (macOS)
- Config file: ~/.photosort.conf

Version History:
V8.0 - CLIP burst stacking, BRISQUE+VLM cascade, consolidated analysis
V7.1 (GM 3.2) - Patched stats tracking in auto_workflow.
V7.1 (GM 3.1) - STABLE BUILD. Removed stats tracking calls.
V7.1 - 200 phrases, directory selector, session tracking
V7.0 - AI Critic feature, config file system
V6.5 - Auto mode refactor
V6.4 - EXIF stats dashboard
V6.0 - Quality culling engine
V5.0 - Burst stacker
"""
```

---

## Step 8: Update CLI Help Text

**Location:** `main()` function, around line 2200

Add information about the v8.0 features in the help text:

```python
def main():
    """Main entry point with CLI argument parsing."""
    
    parser = argparse.ArgumentParser(
        description='PhotoSort v8.0 - AI-powered photography workflow automation',
        epilog="""
Examples:
  python photosort.py auto             # Full auto workflow (v8.0 algorithms)
  python photosort.py stack            # Burst stacking (CLIP semantic grouping)
  python photosort.py cull             # Quality culling (BRISQUE + VLM cascade)
  python photosort.py --algorithm legacy  # Use legacy algorithms

V8.0 Features:
  - CLIP burst detection (semantic, not perceptual)
  - BRISQUE quality assessment (bokeh-aware)
  - Consolidated VLM (cull + name + critique in one call)
  - Content-based caching (survives folder moves)
        """
    )
    
    # ... rest of argument parser ...
```

---

## Step 9: Testing Plan

After making these changes:

### 1. Test Setup
```bash
# Install dependencies
python setup_photosort.py --install

# Check status
python setup_photosort.py --check
```

### 2. Test Individual Features
```bash
# Test burst stacking with CLIP
python photosort.py stack --dry-run

# Test culling with BRISQUE
python photosort.py cull --dry-run

# Test full auto workflow
python photosort.py auto --dry-run
```

### 3. Test Cache Behavior
```bash
# First run (slow - generates embeddings)
python photosort.py stack

# Second run (fast - uses cached embeddings)
python photosort.py stack

# Move folder, re-run (should still use cache!)
mv ~/test_photos ~/new_location
cd ~/new_location
python photosort.py stack
```

### 4. Test Legacy Fallback
```bash
# Edit ~/.photosort.conf:
# [algorithms]
# burst_algorithm = legacy
# cull_algorithm = legacy

python photosort.py auto
```

---

## Calibration Guide

After installation, you'll want to tune the v8.0 parameters for your photography style:

### CLIP Burst Grouping (eps parameter)
- **Default:** 0.15 (moderate grouping)
- **Tighter grouping** (fewer false positives): 0.10-0.12
- **Looser grouping** (catches more bursts): 0.18-0.25

Test by running on a known burst sequence and checking if images are grouped correctly.

### BRISQUE Thresholds
- **Keeper threshold** (default 35.0): Lower = more strict
- **Ambiguous threshold** (default 50.0): Higher = more lenient

Test on your camera's files:
1. Take some portraits with bokeh
2. Take some intentionally blurry shots
3. Run cull and verify correct categorization

---

## Troubleshooting

### "v8.0 engines not available"
- Run: `python setup_photosort.py --check`
- Install missing deps: `python setup_photosort.py --install`

### CLIP embeddings taking too long
- First run is slow (generates embeddings)
- Subsequent runs use cache (~instant)
- Check cache: `ls -lh ~/.photosort_cache/`

### VLM not returning valid JSON
- Verify model: `ollama list | grep minicpm`
- Test manually: `ollama run openbmb/minicpm-v2.6:q4_K_M`

### Good photos in duds folder
- Lower BRISQUE keeper threshold (35 → 30)
- Or force VLM for all: `vlm_force_all = true`

---

## Rollback Plan

If v8.0 causes issues, you can quickly roll back:

1. Edit `~/.photosort.conf`:
```ini
[algorithms]
burst_algorithm = legacy
cull_algorithm = legacy
```

2. Or use CLI override:
```bash
python photosort.py auto --algorithm legacy
```

This uses your existing imagehash + Laplacian code.

---

## Performance Expectations

**First Run (No Cache):**
- Burst stacking: ~50-100ms per image
- Quality culling: ~30-50ms per image (BRISQUE only)
- VLM analysis: ~500-2000ms per image (only ambiguous cases)

**Subsequent Runs (Cached):**
- Burst stacking: ~1-2ms per image (instant!)
- Quality culling: Same as first run
- Overall: 5-10x faster than first run

**VLM Usage Reduction:**
- Old: 2 VLM calls per keeper image
- New: 1 VLM call per ambiguous image only
- Reduction: ~60-80% fewer VLM calls

---

## Questions?

If you hit any issues during migration:
1. Check the v8.0 status: `python photosort_v8_integration.py`
2. Verify dependencies: `python setup_photosort.py --check`
3. Test modules individually before full integration
4. Use `--dry-run` for safe testing

Good luck with the v8.0 upgrade! 🚀
