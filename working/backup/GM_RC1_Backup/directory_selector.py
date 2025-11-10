"""
Directory Selector for PHOTOSORT v7.1
======================================
Interactive directory picker with auto-detection of drives.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, List

try:
    import inquirer
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False

from utils import get_free_space_gb, is_external_drive, get_volume_name, SYSTEM_VOLUMES


def get_available_volumes() -> List[Tuple[str, Path, Optional[float]]]:
    """
    Get list of available volumes with free space info.
    
    Returns:
        List of tuples: (display_name, path, free_space_gb)
    """
    volumes = []
    
    # Check /Volumes/ for external drives (macOS)
    if Path('/Volumes').exists():
        for volume_path in Path('/Volumes').iterdir():
            if not volume_path.is_dir():
                continue
            
            # Skip system volumes
            volume_name = volume_path.name
            if volume_name in SYSTEM_VOLUMES:
                continue
            
            # Get free space
            free_space = get_free_space_gb(volume_path)
            
            # Create display name with free space
            if free_space:
                display = f"📀 {volume_name} ({free_space:.1f} GB free)"
            else:
                display = f"📀 {volume_name}"
            
            volumes.append((display, volume_path, free_space))
    
    # Add common user directories
    home = Path.home()
    
    common_dirs = [
        ("📸 ~/Pictures", home / "Pictures"),
        ("🖥️  ~/Desktop", home / "Desktop"),
        ("📥 ~/Downloads", home / "Downloads"),
        ("🏠 ~/Documents", home / "Documents"),
    ]
    
    for display, path in common_dirs:
        if path.exists():
            volumes.append((display, path, None))
    
    return volumes


def select_directory_interactive(prompt: str, 
                                 allow_custom: bool = True,
                                 default_path: Optional[Path] = None) -> Optional[Path]:
    """
    Interactive directory selection with inquirer.
    
    Args:
        prompt: Prompt message to display
        allow_custom: Allow user to enter custom path
        default_path: Default path to suggest
    
    Returns:
        Selected Path or None if cancelled
    """
    if not INQUIRER_AVAILABLE:
        # Fall back to simple text input
        return select_directory_fallback(prompt, default_path)
    
    try:
        # Build choices list
        volumes = get_available_volumes()
        choices = []
        
        # Add detected volumes
        for display, path, _ in volumes:
            choices.append((display, str(path)))
        
        # Add custom path option
        if allow_custom:
            choices.append(("⌨️  Custom path... (type manually)", "CUSTOM"))
        
        # Add quit option
        choices.append(("❌ Quit", "QUIT"))
        
        # Create inquirer list
        questions = [
            inquirer.List(
                'path',
                message=prompt,
                choices=choices,
                default=str(default_path) if default_path else None
            )
        ]
        
        answers = inquirer.prompt(questions)
        
        if not answers:
            return None
        
        selected = answers['path']
        
        # Handle quit
        if selected == "QUIT":
            return None
        
        # Handle custom path
        if selected == "CUSTOM":
            custom_path = input("\n  Enter custom path: ").strip()
            if not custom_path:
                return None
            
            path = Path(custom_path).expanduser()
            
            # Validate path
            if not path.exists():
                create = input(f"  Path doesn't exist. Create it? (y/n): ").lower()
                if create == 'y':
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        print(f"  ✓ Created: {path}")
                    except Exception as e:
                        print(f"  ❌ Error creating path: {e}")
                        return None
                else:
                    return None
            
            return path
        
        # Return selected path
        return Path(selected)
    
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return None
    except Exception as e:
        print(f"\n⚠️  Error with interactive selection: {e}")
        return select_directory_fallback(prompt, default_path)


def select_directory_fallback(prompt: str, 
                              default_path: Optional[Path] = None) -> Optional[Path]:
    """
    Fallback directory selection using simple text input.
    
    Args:
        prompt: Prompt message
        default_path: Default path suggestion
    
    Returns:
        Selected Path or None if cancelled
    """
    print(f"\n{prompt}")
    print("━" * 60)
    
    # Show available volumes
    volumes = get_available_volumes()
    if volumes:
        print("\n📦 Available volumes:")
        for display, path, free_space in volumes:
            emoji = display.split()[0]
            name = ' '.join(display.split()[1:])
            print(f"   {emoji} {path}")
            if free_space:
                print(f"      ({free_space:.1f} GB free)")
    
    # Show default if provided
    if default_path:
        print(f"\n💡 Default: {default_path}")
    
    # Get user input
    print("\n   Enter path (or 'q' to quit):", end=' ')
    user_input = input().strip()
    
    # Handle quit
    if user_input.lower() == 'q':
        return None
    
    # Use default if empty
    if not user_input and default_path:
        return default_path
    
    # Validate and return path
    if not user_input:
        print("  ❌ No path entered.")
        return None
    
    path = Path(user_input).expanduser().resolve()
    
    # Check if exists
    if not path.exists():
        create = input(f"  Path doesn't exist. Create it? (y/n): ").lower()
        if create == 'y':
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"  ✓ Created: {path}")
            except Exception as e:
                print(f"  ❌ Error creating path: {e}")
                return None
        else:
            return None
    
    return path


def get_source_and_destination(config: dict) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Get both source and destination paths with smart defaults from config.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Tuple of (source_path, destination_path) or (None, None) if cancelled
    """
    # Get last used paths from config
    remember_source = config.get('behavior', {}).get('remember_last_source', True)
    remember_dest = config.get('behavior', {}).get('remember_last_destination', True)
    
    last_source = None
    last_dest = None
    
    if remember_source:
        last_source_str = config.get('behavior', {}).get('last_source_path', '')
        if last_source_str:
            last_source = Path(last_source_str).expanduser()
    
    if remember_dest:
        last_dest_str = config.get('behavior', {}).get('last_destination_path', '')
        if last_dest_str:
            last_dest = Path(last_dest_str).expanduser()
    
    # Select source
    print("\n" + "=" * 60)
    print("📸 PHOTOSORT SETUP")
    print("=" * 60)
    
    source = select_directory_interactive(
        "📁 Where are your photos?",
        allow_custom=True,
        default_path=last_source or Path.cwd()
    )
    
    if not source:
        return None, None
    
    # Select destination
    destination = select_directory_interactive(
        "📦 Where should organized photos go?",
        allow_custom=True,
        default_path=last_dest
    )
    
    if not destination:
        return None, None
    
    return source, destination


def update_config_paths(config: dict, config_path: Path, 
                       source: Optional[Path], 
                       destination: Optional[Path]):
    """
    Update config file with last used paths.
    
    Args:
        config: Configuration dict
        config_path: Path to config file
        source: Source path to save
        destination: Destination path to save
    """
    try:
        import configparser
        
        if 'behavior' not in config:
            config['behavior'] = {}
        
        if source:
            config['behavior']['last_source_path'] = str(source)
        
        if destination:
            config['behavior']['last_destination_path'] = str(destination)
        
        # Write back to config file
        parser = configparser.ConfigParser()
        
        # Convert dict to ConfigParser format
        for section, values in config.items():
            if not parser.has_section(section) and section != 'DEFAULT':
                parser.add_section(section)
            
            for key, value in values.items():
                if section == 'DEFAULT':
                    parser.set('DEFAULT', key, str(value))
                else:
                    parser.set(section, key, str(value))
        
        with open(config_path, 'w') as f:
            parser.write(f)
    
    except Exception as e:
        # Silent fail - not critical
        pass


if __name__ == "__main__":
    # Test directory selector
    print("🧪 Testing Directory Selector:")
    
    if INQUIRER_AVAILABLE:
        print("✓ inquirer available - testing interactive mode")
    else:
        print("⚠️  inquirer not available - testing fallback mode")
    
    # Test volume detection
    volumes = get_available_volumes()
    print(f"\n📦 Detected {len(volumes)} volumes:")
    for display, path, free_space in volumes:
        print(f"   {display} -> {path}")
    
    # Test directory selection
    # test_path = select_directory_interactive("Test: Select a directory")
    # print(f"\n✓ Selected: {test_path}")
