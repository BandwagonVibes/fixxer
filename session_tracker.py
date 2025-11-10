"""
Session Tracker for PHOTOSORT v7.1
===================================
Tracks processing statistics and generates end-of-session summaries.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import random

try:
    from colorama import Fore, Style
    COLORAMA_AVAILABLE = True
except ImportError:
    class MockFore:
        RED = ""; GREEN = ""; CYAN = ""; YELLOW = ""; WHITE = ""; MAGENTA = ""
    class MockStyle:
        RESET_ALL = ""; BRIGHT = ""
    Fore = MockFore()
    Style = MockStyle()
    COLORAMA_AVAILABLE = False

from utils import format_size, format_duration, generate_session_id


class SessionTracker:
    """
    Track processing statistics and generate session summaries.
    """
    
    def __init__(self):
        """Initialize a new session tracker."""
        self.session_id = generate_session_id()
        self.start_time = time.time()
        
        # Core statistics
        self.stats = {
            'images_processed': 0,
            'total_size_before': 0,
            'total_size_after': 0,
            'operations': [],
            'model_used': None,
            'camera_detected': None,
            'lens_detected': None,
            'success_count': 0,
            'failure_count': 0,
            'destination_path': None,
        }
    
    def record_image(self, size_bytes: float, success: bool = True):
        """Record a processed image."""
        self.stats['images_processed'] += 1
        if success:
            self.stats['success_count'] += 1
        else:
            self.stats['failure_count'] += 1
    
    def add_size_before(self, size_bytes: float):
        """Add to total size before processing."""
        self.stats['total_size_before'] += size_bytes
    
    def add_size_after(self, size_bytes: float):
        """Add to total size after processing."""
        self.stats['total_size_after'] += size_bytes
    
    def add_operation(self, operation: str):
        """Add an operation to the list (e.g., 'Burst Stacking')."""
        if operation not in self.stats['operations']:
            self.stats['operations'].append(operation)
    
    def set_model(self, model_name: str):
        """Set the AI model used."""
        self.stats['model_used'] = model_name
    
    def set_camera(self, camera: Optional[str], lens: Optional[str]):
        """Set detected camera/lens info."""
        if camera:
            self.stats['camera_detected'] = camera
        if lens:
            self.stats['lens_detected'] = lens
    
    def set_destination(self, path: Path):
        """Set the destination path."""
        self.stats['destination_path'] = str(path)
    
    def get_duration(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time
    
    def get_throughput(self) -> float:
        """Get images per minute throughput."""
        duration_minutes = self.get_duration() / 60
        if duration_minutes > 0:
            return self.stats['images_processed'] / duration_minutes
        return 0.0
    
    def get_success_rate(self) -> float:
        """Get success rate as percentage."""
        total = self.stats['success_count'] + self.stats['failure_count']
        if total > 0:
            return (self.stats['success_count'] / total) * 100
        return 0.0
    
    def get_size_reduction_percent(self) -> float:
        """Get storage reduction percentage."""
        before = self.stats['total_size_before']
        after = self.stats['total_size_after']
        if before > 0:
            reduction = before - after
            return (reduction / before) * 100
        return 0.0
    
    def print_plasma_bar(self, width: int = 60) -> str:
        """Generate keygen-style plasma gradient bar."""
        if not COLORAMA_AVAILABLE:
            return "=" * width
        
        colors = [
            Fore.CYAN,
            Fore.MAGENTA,
            Fore.YELLOW,
            Fore.CYAN,
            Fore.MAGENTA,
            Fore.YELLOW
        ]
        
        segment_size = width // len(colors)
        bar = ""
        
        for color in colors:
            bar += color + Style.BRIGHT + ("═" * segment_size)
        
        return bar + Style.RESET_ALL
    
    def get_witty_closing(self) -> str:
        """Get a random witty closing line."""
        duration_minutes = self.get_duration() / 60
        keeper_count = self.stats['success_count']
        total_count = self.stats['images_processed']
        
        if total_count > 0:
            keeper_rate = (keeper_count / total_count) * 100
        else:
            keeper_rate = 0
        
        closings = [
            f"☕ Time saved: ~{int(duration_minutes * 2)} minutes of manual sorting. Buy yourself a coffee.",
            f"🧮 Keeper rate: {keeper_rate:.0f}%. Not bad. Not great. But definitely not bad.",
            f"📸 Pro tip: Those {total_count - keeper_count} duds? We all shoot them. Delete guilt-free.",
            f"🎨 {int(duration_minutes)} minutes well spent. Now go actually edit something.",
            f"📦 Saved {format_size(self.stats['total_size_before'] - self.stats['total_size_after'])}. That's like... {int((self.stats['total_size_before'] - self.stats['total_size_after']) / (1024**2) / 5)} more burst sequences worth of space.",
            f"🚀 {keeper_count} keepers from {total_count} shots. That's the photographer's life.",
            f"⏱️ You just saved yourself hours of clicking. Use that time wisely.",
            f"🎯 {self.stats['images_processed']} images processed. Your hard drive thanks you.",
            f"🌟 Quality over quantity - you just proved it.",
            f"📊 {keeper_rate:.0f}% keeper rate. Most pros are around 30-40%. You're doing fine.",
        ]
        
        return random.choice(closings)
    
    def print_summary(self):
        """Print the full session summary with stats."""
        duration = self.get_duration()
        throughput = self.get_throughput()
        success_rate = self.get_success_rate()
        
        # Print plasma bars
        bar = self.print_plasma_bar()
        
        print(f"\n{bar}")
        
        if COLORAMA_AVAILABLE:
            print(f"{Fore.CYAN}{Style.BRIGHT}{'SESSION SUMMARY':^60}{Style.RESET_ALL}")
        else:
            print(f"{'SESSION SUMMARY':^60}")
        
        print(f"{bar}\n")
        
        # Session info
        print(f"📸 Session ID: {self.session_id}")
        print(f"⏱️  Duration: {format_duration(duration)}")
        
        print(f"\n{'─' * 60}")
        
        # Images processed
        print(f"🖼️  IMAGES PROCESSED")
        print(f"   Total: {self.stats['images_processed']} images")
        
        if self.stats['total_size_before'] > 0:
            size_before = format_size(self.stats['total_size_before'])
            size_after = format_size(self.stats['total_size_after'])
            reduction = self.get_size_reduction_percent()
            print(f"   Original Size: {size_before}")
            print(f"   After Cull: {size_after} ({reduction:.0f}% reduction)")
        
        # Operations
        if self.stats['operations']:
            print(f"\n🔧 OPERATIONS")
            for op in self.stats['operations']:
                print(f"   ✓ {op}")
        
        # Equipment
        if self.stats['camera_detected'] or self.stats['lens_detected']:
            print(f"\n📷 EQUIPMENT USED")
            if self.stats['camera_detected']:
                print(f"   Camera: {self.stats['camera_detected']}")
            if self.stats['lens_detected']:
                print(f"   Lens: {self.stats['lens_detected']}")
        
        # Performance
        print(f"\n⚙️  PERFORMANCE")
        print(f"   Throughput: {throughput:.1f} images/min")
        if self.stats['model_used']:
            print(f"   Model Used: {self.stats['model_used']}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        print(f"\n{'─' * 60}")
        
        # Destination
        if self.stats['destination_path']:
            print(f"📦 Saved to: {self.stats['destination_path']}")
        
        print(f"{'─' * 60}\n")
        
        # Witty closing
        print(self.get_witty_closing())
        
        print(f"\n{Fore.RED}{Style.BRIGHT}use responsibly. unleash creatively. inference locally.{Style.RESET_ALL}")
        print(f"{Fore.WHITE}— VisionCrew 🎭⚡{Style.RESET_ALL}\n")
        
        print(f"{'─' * 60}\n")
    
    def save_to_history(self, history_file: Path):
        """
        Save session data to history file.
        
        Args:
            history_file: Path to history JSON file
        """
        session_data = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'duration': self.get_duration(),
            'stats': self.stats,
        }
        
        try:
            # Append to history file (one JSON object per line)
            with open(history_file, 'a') as f:
                json.dump(session_data, f)
                f.write('\n')
        except Exception as e:
            print(f"⚠️  Warning: Could not save session history: {e}")
    
    def to_dict(self) -> Dict:
        """Export session data as dictionary."""
        return {
            'session_id': self.session_id,
            'start_time': self.start_time,
            'duration': self.get_duration(),
            'stats': self.stats,
        }


if __name__ == "__main__":
    # Test session tracker
    print("🧪 Testing SessionTracker:")
    
    tracker = SessionTracker()
    tracker.set_model("bakllava:latest")
    tracker.set_camera("Canon EOS R5", "RF 24-70mm f/2.8")
    tracker.add_operation("Burst Stacking")
    tracker.add_operation("Quality Culling")
    tracker.add_operation("AI Naming")
    
    # Simulate processing
    import time
    for i in range(50):
        tracker.record_image(5 * 1024 * 1024, success=(i % 10 != 0))
        tracker.add_size_before(5 * 1024 * 1024)
        if i % 10 != 0:
            tracker.add_size_after(5 * 1024 * 1024)
        time.sleep(0.01)
    
    tracker.set_destination(Path("/Volumes/Archive/2024-11-06_Urban_Geometry"))
    
    # Print summary
    tracker.print_summary()
