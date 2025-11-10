"""
Smart Progress Bars for PHOTOSORT v7.1
=======================================
Time-aware progress bars with rotating contextual phrases.
"""

import time
from typing import Optional
from phrases import get_phrase_by_duration, get_model_loading_phrase

try:
    from tqdm import tqdm as _tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class SmartProgressBar:
    """
    Progress bar that rotates phrases based on elapsed time.
    
    Features:
    - Automatic phrase rotation every 15-30 seconds
    - Time-aware phrase selection (early vs marathon)
    - Optional VisionCrew meta phrases during long operations
    """
    
    def __init__(self, 
                 total: int,
                 desc: str = "Processing",
                 unit: str = "img",
                 include_meta: bool = False):
        """
        Initialize smart progress bar.
        
        Args:
            total: Total number of items to process
            desc: Initial description
            unit: Unit name (e.g., "img", "file")
            include_meta: Include VisionCrew meta phrases
        """
        self.total = total
        self.initial_desc = desc
        self.unit = unit
        self.include_meta = include_meta
        
        self.start_time = time.time()
        self.last_phrase_change = time.time()
        self.phrase_rotation_interval = 20  # seconds
        
        # Initialize tqdm if available
        if TQDM_AVAILABLE:
            self.pbar = _tqdm(
                total=total,
                desc=f" {desc}",
                unit=unit,
                ncols=80,
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}'
            )
        else:
            self.pbar = None
            self.current = 0
            print(f"\n{desc}: 0/{total}")
    
    def update(self, n: int = 1):
        """
        Update progress bar.
        
        Args:
            n: Number of items to increment
        """
        elapsed = time.time() - self.start_time
        
        # Check if we should rotate phrase
        if time.time() - self.last_phrase_change > self.phrase_rotation_interval:
            new_phrase = get_phrase_by_duration(elapsed, use_meta=self.include_meta)
            self.set_description(new_phrase)
            self.last_phrase_change = time.time()
        
        # Update progress
        if self.pbar:
            self.pbar.update(n)
        else:
            self.current += n
            if self.current % max(1, self.total // 10) == 0:
                print(f"{self.initial_desc}: {self.current}/{self.total}")
    
    def set_description(self, desc: str):
        """Update the description/phrase."""
        if self.pbar:
            self.pbar.set_description(f" {desc}")
    
    def write(self, message: str):
        """Write a message without disrupting the progress bar."""
        if self.pbar:
            self.pbar.write(message)
        else:
            print(message)
    
    def close(self):
        """Close the progress bar."""
        if self.pbar:
            self.pbar.close()
        else:
            print(f"{self.initial_desc}: Complete!")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, *args):
        """Context manager exit."""
        self.close()


class ModelLoadingProgress:
    """
    Progress indicator for model loading with rotating messages.
    
    Displays reassuring messages every 5 seconds during the model load wait.
    """
    
    def __init__(self):
        """Initialize model loading progress."""
        self.phrases = [get_model_loading_phrase() for _ in range(3)]
        self.current_phrase_idx = 0
        self.start_time = None
        self.last_update = None
        self.update_interval = 5  # seconds
    
    def start(self):
        """Start the loading progress."""
        self.start_time = time.time()
        self.last_update = time.time()
        print(f"\n🤖 {self.phrases[0]}", end='', flush=True)
    
    def update(self) -> bool:
        """
        Update the loading message if enough time has passed.
        
        Returns:
            True if message was updated, False otherwise
        """
        if not self.start_time:
            return False
        
        elapsed = time.time() - self.last_update
        
        if elapsed >= self.update_interval:
            self.current_phrase_idx = (self.current_phrase_idx + 1) % len(self.phrases)
            print(f"\r🤖 {self.phrases[self.current_phrase_idx]}" + " " * 20, 
                  end='', flush=True)
            self.last_update = time.time()
            return True
        
        return False
    
    def finish(self):
        """Finish the loading progress."""
        print("\r✓ Model loaded! Let's roll." + " " * 40)


def create_simple_progress(total: int, desc: str = "Processing") -> Optional[SmartProgressBar]:
    """
    Factory function to create a progress bar if tqdm is available.
    
    Args:
        total: Total number of items
        desc: Description text
    
    Returns:
        SmartProgressBar or None if tqdm not available
    """
    if TQDM_AVAILABLE:
        return SmartProgressBar(total, desc=desc)
    return None


def show_model_loading_feedback(check_loaded_func, timeout: float = 60.0):
    """
    Show rotating messages during model loading.
    
    Args:
        check_loaded_func: Function that returns True when model is loaded
        timeout: Maximum time to wait in seconds
    """
    progress = ModelLoadingProgress()
    progress.start()
    
    start_time = time.time()
    
    while not check_loaded_func():
        progress.update()
        time.sleep(0.5)
        
        # Timeout check
        if time.time() - start_time > timeout:
            print("\n⚠️  Model loading timeout. Please check Ollama status.")
            return False
    
    progress.finish()
    return True


# ============================================================================
# SIMPLE FALLBACK PROGRESS (no tqdm)
# ============================================================================

class SimpleFallbackProgress:
    """
    Simple progress indicator for when tqdm is not available.
    Shows periodic updates without fancy bars.
    """
    
    def __init__(self, total: int, desc: str = "Processing"):
        """Initialize simple progress."""
        self.total = total
        self.desc = desc
        self.current = 0
        self.last_print = 0
        self.print_interval = max(1, total // 20)  # Print ~20 updates
        
        print(f"\n{desc}: Starting...")
    
    def update(self, n: int = 1):
        """Update progress."""
        self.current += n
        
        if self.current - self.last_print >= self.print_interval or self.current >= self.total:
            percent = (self.current / self.total) * 100
            print(f"{self.desc}: {self.current}/{self.total} ({percent:.0f}%)")
            self.last_print = self.current
    
    def close(self):
        """Close progress."""
        print(f"{self.desc}: Complete! ✓")
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


if __name__ == "__main__":
    # Test smart progress bar
    print("🧪 Testing SmartProgressBar:")
    
    if TQDM_AVAILABLE:
        print("✓ tqdm available - testing full features")
        
        with SmartProgressBar(100, desc="🎨 Testing phrases", unit="item") as pbar:
            for i in range(100):
                time.sleep(0.1)  # Simulate work
                pbar.update(1)
                
                if i == 50:
                    pbar.write("   Halfway there!")
    else:
        print("⚠️  tqdm not available - testing fallback")
        
        with SimpleFallbackProgress(100, "Testing fallback") as pbar:
            for i in range(100):
                time.sleep(0.05)
                pbar.update(1)
    
    print("\n✓ Progress bar test complete!")
