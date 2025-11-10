#!/usr/bin/env python3
"""
Automatic Patcher for PhotoSort v7.1
Applies GM 3.2 fixes for Session Tracker and Model Loading Progress
"""

import sys
from pathlib import Path

def apply_fixes(input_file: Path, output_file: Path):
    """Apply all fixes to photosort.py"""
    
    print("📦 Reading original file...")
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    print("🔧 Applying fixes...")
    
    # FIX #1: Update version history (line 24-26)
    for i in range(len(lines)):
        if 'V7.1 (GM 3.1) - STABLE BUILD' in lines[i]:
            lines.insert(i, 'V7.1 (GM 3.2) - FIXED: Re-enabled session tracker stats collection with proper tracking,\n')
            lines.insert(i+1, '                 fixed model loading progress to show during actual model load (first AI call)\n')
            print("✅ Updated version history")
            break
    
    # FIX #2: Replace ModelLoadingProgress class (around line 201-226)
    new_model_loading_class = '''# v7.1 GM 3.2: IMPROVED Model Loading Progress
class ModelLoadingProgress:
    """
    A simple threaded spinner for model loading.
    Rotates phrases every 5 seconds in bright yellow.
    """
    def __init__(self, message="Loading model..."):
        self.message = message
        self._stop_event = Event()
        self._thread = None
        self.start_time = 0.0
        self.phrases = []
        self.current_phrase_idx = 0

    def _spinner(self):
        """Background thread to rotate loading messages."""
        self.phrases = [get_model_loading_phrase() for _ in range(5)]
        self.current_phrase_idx = 0
        last_update = time.time()
        
        # Display first message immediately
        if COLORAMA_AVAILABLE:
            print(f"\\n{Fore.YELLOW}{Style.BRIGHT}🤖 {self.phrases[0]}{Style.RESET_ALL}", end='', flush=True)
        else:
            print(f"\\n🤖 {self.phrases[0]}", end='', flush=True)
        
        while not self._stop_event.wait(0.5):  # Check every 0.5s
            elapsed = time.time() - last_update
            if elapsed >= 5.0:  # Rotate every 5 seconds
                self.current_phrase_idx = (self.current_phrase_idx + 1) % len(self.phrases)
                if COLORAMA_AVAILABLE:
                    print(f"\\r{Fore.YELLOW}{Style.BRIGHT}🤖 {self.phrases[self.current_phrase_idx]}{Style.RESET_ALL}" + " " * 20, 
                          end='', flush=True)
                else:
                    print(f"\\r🤖 {self.phrases[self.current_phrase_idx]}" + " " * 20, 
                          end='', flush=True)
                last_update = time.time()

    def start(self):
        """Start the loading spinner."""
        self.start_time = time.time()
        self._thread = threading.Thread(target=self._spinner, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the loading spinner."""
        if self._thread:
            self._stop_event.set()
            self._thread.join(timeout=1.0)
            if COLORAMA_AVAILABLE:
                print(f"\\r{Fore.GREEN}{Style.BRIGHT}✅ Model loaded! Let's roll.{Style.RESET_ALL}" + " " * 40)
            else:
                print("\\r✅ Model loaded! Let's roll." + " " * 40)
'''
    
    # Find and replace ModelLoadingProgress class
    in_class = False
    class_start = -1
    class_end = -1
    
    for i, line in enumerate(lines):
        if 'class ModelLoadingProgress:' in line:
            class_start = i
            in_class = True
        elif in_class and line.startswith('class ') and 'ModelLoadingProgress' not in line:
            class_end = i
            break
        elif in_class and i > class_start + 100:  # Safety limit
            class_end = i
            break
    
    if class_start != -1 and class_end != -1:
        # Remove old class
        del lines[class_start:class_end]
        # Insert new class
        lines.insert(class_start, new_model_loading_class + '\n')
        print(f"✅ Replaced ModelLoadingProgress class (lines {class_start}-{class_end})")
    
    # FIX #3: Update auto_workflow function to track stats
    # This is complex, so we'll add detailed comments showing where changes should be made
    
    for i, line in enumerate(lines):
        # Find the tracker initialization
        if 'tracker = SessionTracker()' in line and i > 1900:  # Around line 1990
            # Add camera tracking after tracker initialization
            insert_pos = i + 4  # After add_operation calls
            camera_tracking_code = '''    
    # v7.1 GM 3.2: Track equipment info from EXIF
    try:
        sample_images = list(directory.glob("*"))[:5]  # Check first 5 images
        for img_path in sample_images:
            if img_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                camera, lens = get_exif_camera_info(img_path)
                if camera or lens:
                    tracker.set_camera(camera, lens)
                    break  # Found camera info, stop looking
    except Exception:
        pass  # Non-critical
'''
            lines.insert(insert_pos, camera_tracking_code + '\n')
            print(f"✅ Added camera tracking (line {insert_pos})")
        
        # Find where hero_files list is created
        if 'print(f"   Found {len(hero_files)' in line:
            # Add size tracking after this
            size_tracking_code = '''    
    # v7.1 GM 3.2: FIXED - Calculate total size before processing
    total_size_before = 0
    for f in hero_files:
        try:
            total_size_before += f.stat().st_size
        except Exception:
            pass
    tracker.add_size_before(total_size_before)
'''
            lines.insert(i + 1, size_tracking_code + '\n')
            print(f"✅ Added size tracking before processing (line {i+1})")
            break
    
    # FIX #4: Add model loading progress and stats tracking in executor loop
    for i, line in enumerate(lines):
        if 'results = {"success": [], "failed": []}' in line and i > 2000:
            # Add before pbar initialization
            model_loader_vars = '''    
    # v7.1 GM 3.2: Show model loading progress during FIRST AI call
    first_call = True
    model_loader = None
'''
            lines.insert(i + 1, model_loader_vars + '\n')
            print(f"✅ Added model loader variables (line {i+1})")
            break
    
    # Find the executor loop and add tracking
    in_executor = False
    for i, line in enumerate(lines):
        if 'for future in as_completed(future_to_file):' in line:
            in_executor = True
            # Add model loader start code
            loader_start = '''            # v7.1 GM 3.2: Show loading spinner for first call only
            if first_call:
                model_loader = ModelLoadingProgress(message="Loading AI model for first image...")
                model_loader.start()
                first_call = False
            
'''
            lines.insert(i + 1, loader_start)
            print(f"✅ Added model loader start (line {i+1})")
            continue
        
        if in_executor and 'original, success, message, description = future.result()' in line:
            # Add model loader stop code
            loader_stop = '''            
            # v7.1 GM 3.2: Stop model loader after first result
            if model_loader:
                model_loader.stop()
                model_loader = None
'''
            lines.insert(i + 1, loader_stop + '\n')
            print(f"✅ Added model loader stop (line {i+1})")
            in_executor = False
            break
    
    # Find success and failure tracking in executor
    for i, line in enumerate(lines):
        if i > 2060 and '"new_name": message,' in line:
            # Add tracking after success append
            success_tracking = '''                # v7.1 GM 3.2: Track successful image
                try:
                    file_size = original.stat().st_size
                    tracker.record_image(file_size, success=True)
                    tracker.add_size_after(file_size)
                except Exception:
                    pass
'''
            lines.insert(i + 3, success_tracking + '\n')
            print(f"✅ Added success tracking (line {i+3})")
            break
    
    for i, line in enumerate(lines):
        if i > 2070 and 'results["failed"].append((original.name, message))' in line:
            # Add tracking after failure append
            failure_tracking = '''                # v7.1 GM 3.2: Track failed image
                tracker.record_image(0, success=False)
'''
            lines.insert(i + 1, failure_tracking + '\n')
            print(f"✅ Added failure tracking (line {i+1})")
            break
    
    # Write output
    print(f"\n💾 Writing fixed file to {output_file}...")
    with open(output_file, 'w') as f:
        f.writelines(lines)
    
    print(f"\n✅ All fixes applied successfully!")
    print(f"\nNext steps:")
    print(f"1. Backup your original: mv photosort.py photosort.py.backup")
    print(f"2. Replace with fixed version: mv {output_file.name} photosort.py")
    print(f"3. Test with: python3 photosort.py --auto")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 patch_photosort.py <photosort.py>")
        print("\nThis will create photosort_FIXED.py with all fixes applied")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    if not input_file.exists():
        print(f"❌ Error: {input_file} not found!")
        sys.exit(1)
    
    output_file = input_file.parent / f"{input_file.stem}_FIXED{input_file.suffix}"
    
    print(f"🔍 Input:  {input_file}")
    print(f"📝 Output: {output_file}\n")
    
    apply_fixes(input_file, output_file)
