"""
Directory Selector for PHOTOSORT v9.3
======================================
Interactive directory picker with ASCII tree browser for nested navigation.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, List

try:
    import inquirer
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False

from utils import get_free_space_gb, SYSTEM_VOLUMES


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_subdirectories(directory: Path) -> List[Path]:
    """
    Get list of subdirectories in a directory.
    Filters out hidden directories and system folders.
    """
    subdirs = []
    
    try:
        for item in directory.iterdir():
            if not item.is_dir():
                continue
            
            # Skip hidden directories
            if item.name.startswith('.'):
                continue
            
            # Skip common system/app directories
            skip_names = {
                '__pycache__', 'node_modules', '.git', '.svn',
                'Library', 'Applications', '.Trash'
            }
            if item.name in skip_names:
                continue
            
            subdirs.append(item)
    except PermissionError:
        pass
    except Exception:
        pass
    
    return sorted(subdirs, key=lambda p: p.name.lower())


def get_available_volumes() -> List[Tuple[str, Path, Optional[float]]]:
    """
    Get list of available volumes with free space info.
    Filters out Time Machine and system volumes.
    """
    volumes = []
    
    if Path('/Volumes').exists():
        for volume_path in Path('/Volumes').iterdir():
            if not volume_path.is_dir():
                continue
            
            volume_name = volume_path.name
            
            # Skip system volumes
            if volume_name in SYSTEM_VOLUMES:
                continue
            
            # Skip Time Machine volumes
            if 'timemachine' in volume_name.lower():
                continue
            if volume_name.startswith('com.apple'):
                continue
            
            # Skip hidden volumes
            if volume_name.startswith('.'):
                continue
            
            # Get free space
            free_space = get_free_space_gb(volume_path)
            
            if free_space:
                display = f"📁 {volume_name} ({free_space:.1f} GB free)"
            else:
                display = f"📁 {volume_name}"
            
            volumes.append((display, volume_path, free_space))
    
    return volumes


def print_tree_header(current_path: Path):
    """Print the current location with visual breadcrumb."""
    parts = current_path.parts
    
    # Show last 3-4 parts of path for context
    if len(parts) > 4:
        display_parts = ['...'] + list(parts[-3:])
    else:
        display_parts = list(parts)
    
    breadcrumb = '/'.join(display_parts)
    
    print("=" * 60)
    print(f"📂 Browsing: {breadcrumb}")
    print("=" * 60)


def browse_directory_ascii(start_path: Path) -> Optional[Path]:
    """
    ASCII tree browser with numbered menu for nested navigation.
    
    Args:
        start_path: Starting directory to browse
    
    Returns:
        Selected Path or None if cancelled, or "MAIN_MENU" to return to main menu
    """
    current_path = start_path
    history = []
    
    while True:
        clear_screen()
        print_tree_header(current_path)
        
        options = {}
        option_num = 0
        
        # Option to use current directory
        print(f"\n  [{option_num}] ✅ Use THIS directory")
        options[option_num] = ("USE_CURRENT", current_path)
        option_num += 1
        
        # Option to go back (if we have history)
        if history:
            print(f"  [{option_num}] ⬆️  Go back to: {history[-1].name}/")
            options[option_num] = ("GO_BACK", None)
            option_num += 1
        
        # Always show option to return to main menu
        print(f"  [{option_num}] 🏠 Return to main menu")
        options[option_num] = ("MAIN_MENU", None)
        option_num += 1
        
        print("\n  " + "─" * 40)
        
        # Get subdirectories
        subdirs = get_subdirectories(current_path)
        
        if subdirs:
            print(f"  📁 Subdirectories ({len(subdirs)}):\n")
            
            for subdir in subdirs[:15]:
                has_children = bool(get_subdirectories(subdir))
                suffix = " →" if has_children else ""
                
                print(f"  [{option_num}] 📁 {subdir.name}/{suffix}")
                options[option_num] = ("NAVIGATE", subdir)
                option_num += 1
            
            if len(subdirs) > 15:
                remaining = len(subdirs) - 15
                print(f"\n      ... and {remaining} more directories")
        else:
            print("  (no subdirectories)")
        
        print("\n  " + "─" * 40)
        print("  [q] ❌ Cancel")
        
        print("\n  Your choice: ", end="")
        user_input = input().strip().lower()
        
        if user_input == 'q':
            return None
        
        try:
            choice = int(user_input)
            
            if choice not in options:
                print(f"\n  ⚠️  Invalid option: {choice}")
                input("  Press Enter to continue...")
                continue
            
            action, data = options[choice]
            
            if action == "USE_CURRENT":
                return current_path
            
            elif action == "GO_BACK":
                if history:
                    current_path = history.pop()
            
            elif action == "MAIN_MENU":
                return "MAIN_MENU"
            
            elif action == "NAVIGATE":
                history.append(current_path)
                current_path = data
        
        except ValueError:
            print(f"\n  ⚠️  Please enter a number or 'q'")
            input("  Press Enter to continue...")
            continue


def select_directory_interactive(prompt: str, 
                                 allow_custom: bool = True,
                                 default_path: Optional[Path] = None) -> Optional[Path]:
    """
    Interactive directory selection with ASCII tree browser.
    
    Args:
        prompt: Prompt message to display
        allow_custom: Allow user to enter custom path
        default_path: Default path to suggest
    
    Returns:
        Selected Path or None if cancelled
    """
    clear_screen()
    print("=" * 60)
    print("📸 PHOTOSORT SETUP")
    print("=" * 60)
    print(f"\n  {prompt}\n")
    
    home = Path.home()
    cwd = Path.cwd()
    
    options = {}
    option_num = 0
    
    print("  Common locations:\n")
    
    # Current directory
    print(f"  [{option_num}] 📁 Current directory: {cwd.name}/")
    options[option_num] = cwd
    option_num += 1
    
    # Home
    print(f"  [{option_num}] 📁 Home (~)")
    options[option_num] = home
    option_num += 1
    
    # Pictures
    if (home / "Pictures").exists():
        print(f"  [{option_num}] 📁 ~/Pictures")
        options[option_num] = home / "Pictures"
        option_num += 1
    
    # Downloads
    if (home / "Downloads").exists():
        print(f"  [{option_num}] 📁 ~/Downloads")
        options[option_num] = home / "Downloads"
        option_num += 1
    
    # External volumes
    volumes = get_available_volumes()
    if volumes:
        print(f"\n  External volumes:\n")
        for display, path, free_space in volumes:
            if free_space:
                print(f"  [{option_num}] 📁 {path.name} ({free_space:.1f} GB free)")
            else:
                print(f"  [{option_num}] 📁 {path.name}")
            options[option_num] = path
            option_num += 1
    
    # Custom path option
    if allow_custom:
        print(f"\n  [{option_num}] ⌨️  Type custom path...")
        options[option_num] = "CUSTOM"
        option_num += 1
    
    print("\n  " + "─" * 40)
    print("  [q] ❌ Quit")
    
    print("\n  Select starting location: ", end="")
    user_input = input().strip().lower()
    
    if user_input == 'q':
        return None
    
    try:
        choice = int(user_input)
        
        if choice not in options:
            print(f"\n  ⚠️  Invalid option: {choice}")
            input("  Press Enter to try again...")
            return select_directory_interactive(prompt, allow_custom, default_path)
        
        selected = options[choice]
        
        # Handle custom path
        if selected == "CUSTOM":
            custom_path = input("\n  Enter custom path: ").strip()
            if not custom_path:
                return None
            
            path = Path(custom_path).expanduser()
            
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
        
        # Browse into selected directory
        result = browse_directory_ascii(selected)
        
        # If user chose to return to main menu, loop back
        if result == "MAIN_MENU":
            return select_directory_interactive(prompt, allow_custom, default_path)
        
        return result
    
    except ValueError:
        print(f"\n  ⚠️  Please enter a number or 'q'")
        input("  Press Enter to try again...")
        return select_directory_interactive(prompt, allow_custom, default_path)
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        return None


def select_directory_fallback(prompt: str, 
                              default_path: Optional[Path] = None) -> Optional[Path]:
    """
    Fallback directory selection using simple text input.
    Used when interactive mode fails.
    """
    print(f"\n{prompt}")
    print("─" * 60)
    
    volumes = get_available_volumes()
    if volumes:
        print("\n📁 Available volumes:")
        for display, path, free_space in volumes:
            print(f"   {path}")
            if free_space:
                print(f"      ({free_space:.1f} GB free)")
    
    home = Path.home()
    print(f"\n📁 Common directories:")
    print(f"   {Path.cwd()} (current)")
    print(f"   {home} (home)")
    if (home / "Pictures").exists():
        print(f"   {home / 'Pictures'}")
    if (home / "Downloads").exists():
        print(f"   {home / 'Downloads'}")
    
    if default_path:
        print(f"\n💡 Default: {default_path}")
    
    print("\n   Enter path (or 'q' to quit):", end=' ')
    user_input = input().strip()
    
    if user_input.lower() == 'q':
        return None
    
    if not user_input and default_path:
        return default_path
    
    if not user_input:
        print("  ❌ No path entered.")
        return None
    
    path = Path(user_input).expanduser().resolve()
    
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
    Get both source and destination paths.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Tuple of (source_path, destination_path) or (None, None) if cancelled
    """
    # Handle both nested and flat config structures
    if isinstance(config.get('behavior'), dict):
        last_source_str = config.get('behavior', {}).get('last_source_path', '')
        last_dest_str = config.get('behavior', {}).get('last_destination_path', '')
    else:
        last_source_str = config.get('last_source_path', '')
        last_dest_str = config.get('last_destination_path', '')
    
    last_source = Path(last_source_str).expanduser() if last_source_str else None
    last_dest = Path(last_dest_str).expanduser() if last_dest_str else None
    
    # Select source
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
                       source: Optional[str], 
                       destination: Optional[str]):
    """
    Update config file with last used paths.
    """
    try:
        import configparser
        
        parser = configparser.ConfigParser()
        if config_path.exists():
            parser.read(config_path)
        
        if not parser.has_section('behavior'):
            parser.add_section('behavior')
        
        if source:
            parser.set('behavior', 'last_source_path', str(source))
        
        if destination:
            parser.set('behavior', 'last_destination_path', str(destination))
        
        with open(config_path, 'w') as f:
            parser.write(f)
    
    except Exception:
        pass


if __name__ == "__main__":
    print("🧪 Testing Directory Selector v9.3 (ASCII Tree Browser):\n")
    
    test_config = {
        'last_source_path': None,
        'last_destination_path': None
    }
    
    source, dest = get_source_and_destination(test_config)
    
    if source and dest:
        print(f"\n✅ Source: {source}")
        print(f"✅ Destination: {dest}")
    else:
        print("\n❌ Selection cancelled")
