"""
Utility Functions for PHOTOSORT v7.1
====================================
Shared helper functions used across modules.
"""

import re
import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime


def sanitize_filename(text: str, max_length: int = 100) -> str:
    """
    Sanitize text for safe filesystem usage.
    
    Removes/replaces:
    - Special characters: / \ : * ? " < > |
    - Leading/trailing spaces and dots
    - Multiple consecutive spaces
    
    Args:
        text: Raw text to sanitize
        max_length: Maximum filename length (default 100)
    
    Returns:
        Safe filename string
    """
    # Remove special characters
    safe = re.sub(r'[/\\:*?"<>|]', '', text)
    
    # Replace multiple spaces with single space
    safe = re.sub(r'\s+', ' ', safe)
    
    # Strip leading/trailing whitespace and dots
    safe = safe.strip(' .')
    
    # Truncate if too long
    if len(safe) > max_length:
        safe = safe[:max_length].strip()
    
    # If empty after sanitization, use fallback
    if not safe:
        safe = "untitled"
    
    return safe


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes."""
    try:
        return file_path.stat().st_size / (1024 * 1024)
    except:
        return 0.0


def get_free_space_gb(path: Path) -> Optional[float]:
    """
    Get free space in gigabytes for a given path.
    
    Args:
        path: Directory or volume path
    
    Returns:
        Free space in GB, or None if unable to determine
    """
    try:
        stat = os.statvfs(path)
        free_bytes = stat.f_bavail * stat.f_frsize
        return free_bytes / (1024**3)
    except:
        return None


def format_size(size_bytes: float) -> str:
    """
    Format byte size into human-readable string.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string (e.g., "1.2 GB", "45.6 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration into human-readable string.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted string (e.g., "2h 15m", "45m 23s", "12s")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def get_exif_date(image_path: Path) -> Optional[datetime]:
    """
    Extract capture date from image EXIF data.
    
    Args:
        image_path: Path to image file
    
    Returns:
        datetime object or None if not available
    """
    try:
        import exifread
        
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, stop_tag='DateTimeOriginal', details=False)
        
        if 'EXIF DateTimeOriginal' in tags:
            date_str = str(tags['EXIF DateTimeOriginal'])
            return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        
        # Fallback to file modification time
        return datetime.fromtimestamp(image_path.stat().st_mtime)
    except:
        # Last resort: file modification time
        try:
            return datetime.fromtimestamp(image_path.stat().st_mtime)
        except:
            return None


def get_exif_camera_info(image_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract camera and lens information from EXIF.
    
    Args:
        image_path: Path to image file
    
    Returns:
        Tuple of (camera_model, lens_model) or (None, None)
    """
    try:
        import exifread
        
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        
        camera = None
        lens = None
        
        # Try to get camera model
        if 'Image Model' in tags:
            camera = str(tags['Image Model'])
        elif 'EXIF CameraModel' in tags:
            camera = str(tags['EXIF CameraModel'])
        
        # Try to get lens model
        if 'EXIF LensModel' in tags:
            lens = str(tags['EXIF LensModel'])
        elif 'MakerNote LensModel' in tags:
            lens = str(tags['MakerNote LensModel'])
        
        return (camera, lens)
    except:
        return (None, None)


def is_external_drive(path: Path) -> bool:
    """
    Check if path is on an external drive.
    
    Args:
        path: Path to check
    
    Returns:
        True if on external drive (macOS: /Volumes/*, not Macintosh HD)
    """
    path_str = str(path)
    
    # macOS external drives
    if path_str.startswith('/Volumes/') and 'Macintosh HD' not in path_str:
        return True
    
    # Could add Windows/Linux logic here
    # Windows: Check for removable drives
    # Linux: Check /media/ or /mnt/
    
    return False


def get_volume_name(path: Path) -> Optional[str]:
    """
    Get the volume/drive name for a path.
    
    Args:
        path: Path to check
    
    Returns:
        Volume name or None
    """
    try:
        path_str = str(path.resolve())
        
        # macOS: /Volumes/VolumeName/...
        if path_str.startswith('/Volumes/'):
            parts = path_str.split('/')
            if len(parts) >= 3:
                return parts[2]
        
        # Root volume
        return "Main Drive"
    except:
        return None


def validate_path_exists(path: Path, create_if_missing: bool = False) -> bool:
    """
    Validate that a path exists, optionally creating it.
    
    Args:
        path: Path to validate
        create_if_missing: If True, create directory if it doesn't exist
    
    Returns:
        True if path exists (or was created), False otherwise
    """
    try:
        if path.exists():
            return True
        
        if create_if_missing:
            path.mkdir(parents=True, exist_ok=True)
            return True
        
        return False
    except:
        return False


def count_files_by_extension(directory: Path, extensions: list) -> int:
    """
    Count files with specific extensions in a directory.
    
    Args:
        directory: Directory to search
        extensions: List of extensions to count (e.g., ['.jpg', '.raw'])
    
    Returns:
        Count of matching files
    """
    count = 0
    try:
        for item in directory.iterdir():
            if item.is_file() and item.suffix.lower() in extensions:
                count += 1
    except:
        pass
    return count


def generate_session_id() -> str:
    """
    Generate a short, unique session ID.
    
    Returns:
        13-character hex string (e.g., "a7f2d4c9-3b1a")
    """
    import uuid
    return str(uuid.uuid4())[:13]


# ============================================================================
# CONSTANTS
# ============================================================================

# Supported image extensions
SUPPORTED_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.tiff', '.tif',
    '.rw2', '.raw', '.cr2', '.cr3', '.nef', '.orf', '.arw', '.dng'
]

# System volumes to ignore (macOS)
SYSTEM_VOLUMES = [
    'Macintosh HD',
    'Preboot',
    'Recovery',
    'VM',
    'Update',
    'Data',
]


if __name__ == "__main__":
    # Test utilities
    print("🧪 Testing utilities:")
    print(f"  Sanitize: {sanitize_filename('Test/File: Name*?.jpg')}")
    print(f"  Format size: {format_size(1234567890)}")
    print(f"  Format duration: {format_duration(3725)}")
    print(f"  Session ID: {generate_session_id()}")
