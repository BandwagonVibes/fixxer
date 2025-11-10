#!/usr/bin/env python3
"""
setup_photosort.py - PhotoSort v8.0 Setup Wizard

Interactive setup for dependencies and models.

Author: Claude (Anthropic) + Nick (∞vision crew)
"""

import sys
import subprocess
import shutil
from pathlib import Path

# ==============================================================================
# I. DEPENDENCY CHECKS
# ==============================================================================

def check_python_version():
    """Check if Python version is sufficient (3.8+)."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_package(package_name: str, import_name: str = None) -> bool:
    """Check if a Python package is installed."""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False

def check_command(command: str) -> bool:
    """Check if a system command is available."""
    return shutil.which(command) is not None

def check_ollama() -> bool:
    """Check if Ollama is installed and running."""
    if not check_command('ollama'):
        return False
    
    # Try to connect to Ollama API
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        return response.status_code == 200
    except:
        return False

# ==============================================================================
# II. DEPENDENCY INSTALLATION
# ==============================================================================

def install_package(package_name: str, import_name: str = None) -> bool:
    """Install a Python package using pip."""
    print(f"\n📦 Installing {package_name}...")
    
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package_name],
            check=True,
            capture_output=True
        )
        
        # Verify installation
        if import_name and check_package(package_name, import_name):
            print(f"   ✓ {package_name} installed successfully")
            return True
        elif not import_name and check_package(package_name):
            print(f"   ✓ {package_name} installed successfully")
            return True
        else:
            print(f"   ⚠️ {package_name} installed but verification failed")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to install {package_name}")
        print(f"   Error: {e}")
        return False

def install_core_dependencies() -> bool:
    """Install core dependencies required for v8.0."""
    print("\n" + "=" * 60)
    print("Installing Core Dependencies")
    print("=" * 60)
    
    dependencies = [
        ('sentence-transformers', 'sentence_transformers'),
        ('scikit-learn', 'sklearn'),
        ('image-quality', 'image_quality'),
        ('opencv-python', 'cv2'),
        ('Pillow', 'PIL'),
        ('numpy', 'numpy'),
        ('requests', 'requests'),
        ('exifread', 'exifread'),
        ('imagehash', 'imagehash'),
    ]
    
    all_success = True
    
    for package_name, import_name in dependencies:
        if check_package(package_name, import_name):
            print(f"✓ {package_name} already installed")
        else:
            if not install_package(package_name, import_name):
                all_success = False
    
    return all_success

# ==============================================================================
# III. OLLAMA MODEL MANAGEMENT
# ==============================================================================

def list_ollama_models() -> list:
    """List installed Ollama models."""
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return []
        
        # Parse model list (skip header)
        models = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])
        
        return models
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

def pull_ollama_model(model_name: str) -> bool:
    """Download an Ollama model."""
    print(f"\n📥 Downloading {model_name}...")
    print("   This may take several minutes...")
    
    try:
        # Run ollama pull with real-time output
        process = subprocess.Popen(
            ['ollama', 'pull', model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output
        for line in process.stdout:
            print(f"   {line.strip()}")
        
        process.wait()
        
        if process.returncode == 0:
            print(f"   ✓ {model_name} downloaded successfully")
            return True
        else:
            print(f"   ❌ Failed to download {model_name}")
            return False
            
    except FileNotFoundError:
        print("   ❌ Ollama command not found")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def setup_ollama_models() -> bool:
    """Ensure required Ollama models are installed."""
    print("\n" + "=" * 60)
    print("Setting Up Ollama Models")
    print("=" * 60)
    
    required_model = "openbmb/minicpm-v2.6:q4_K_M"
    
    # Check if Ollama is available
    if not check_command('ollama'):
        print("\n❌ Ollama not found!")
        print("   Please install Ollama from: https://ollama.com")
        return False
    
    # Check if Ollama is running
    if not check_ollama():
        print("\n⚠️  Ollama is installed but not running")
        print("   Please start Ollama and run this setup again")
        return False
    
    print("✓ Ollama is running")
    
    # List installed models
    installed_models = list_ollama_models()
    
    if required_model in installed_models:
        print(f"✓ {required_model} already installed")
        return True
    
    # Ask user if they want to download
    print(f"\n📋 Required model: {required_model}")
    print("   Size: ~2.5 GB")
    
    response = input("\n   Download now? (y/n): ").strip().lower()
    
    if response == 'y':
        return pull_ollama_model(required_model)
    else:
        print("\n   ⚠️  Skipping model download")
        print("   You can download it later with:")
        print(f"   ollama pull {required_model}")
        return False

# ==============================================================================
# IV. DCRAW CHECK
# ==============================================================================

def check_dcraw() -> bool:
    """Check if dcraw is installed (for RAW file support)."""
    print("\n" + "=" * 60)
    print("Checking RAW File Support (dcraw)")
    print("=" * 60)
    
    if check_command('dcraw'):
        print("✓ dcraw is installed")
        print("  PhotoSort can process RAW files (.CR2, .NEF, .RW2, etc.)")
        return True
    else:
        print("⚠️  dcraw not found")
        print("   RAW file support will be limited")
        print("   Install dcraw for full RAW support:")
        print("   - macOS: brew install dcraw")
        print("   - Ubuntu: sudo apt-get install dcraw")
        return False

# ==============================================================================
# V. CACHE SETUP
# ==============================================================================

def setup_cache_directory() -> bool:
    """Create cache directory for embeddings."""
    print("\n" + "=" * 60)
    print("Setting Up Cache Directory")
    print("=" * 60)
    
    cache_dir = Path.home() / ".photosort_cache"
    
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Cache directory created: {cache_dir}")
        
        # Create subdirectories
        (cache_dir / "models").mkdir(exist_ok=True)
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create cache directory: {e}")
        return False

# ==============================================================================
# VI. MAIN SETUP WIZARD
# ==============================================================================

def run_setup_wizard():
    """Run the interactive setup wizard."""
    print("\n" + "=" * 60)
    print("PhotoSort v8.0 - Setup Wizard")
    print("=" * 60)
    print("\nThis wizard will help you install dependencies and models.")
    print("Setup typically takes 5-10 minutes.")
    
    # Check Python version
    print("\n" + "=" * 60)
    print("Checking Python Version")
    print("=" * 60)
    if not check_python_version():
        print("\n❌ Setup failed: Python version too old")
        sys.exit(1)
    
    # Install Python dependencies
    success = install_core_dependencies()
    if not success:
        print("\n⚠️  Some dependencies failed to install")
        print("   PhotoSort may not work correctly")
        response = input("\n   Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            sys.exit(1)
    
    # Setup Ollama models
    ollama_ok = setup_ollama_models()
    if not ollama_ok:
        print("\n⚠️  Ollama model not configured")
        print("   VLM features will not work")
    
    # Check dcraw
    check_dcraw()
    
    # Setup cache
    setup_cache_directory()
    
    # Final summary
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    
    print("\n✓ Core dependencies installed")
    if ollama_ok:
        print("✓ Ollama model ready")
    else:
        print("⚠️  Ollama model needs manual setup")
    
    print("\nYou can now run PhotoSort v8.0:")
    print("  python photosort.py")
    
    print("\nFor help and options:")
    print("  python photosort.py --help")

def run_quick_check():
    """Quick dependency check without installing anything."""
    print("\n" + "=" * 60)
    print("PhotoSort v8.0 - Dependency Check")
    print("=" * 60)
    
    print("\n🐍 Python:")
    check_python_version()
    
    print("\n📦 Core Packages:")
    packages = [
        ('sentence-transformers', 'sentence_transformers'),
        ('scikit-learn', 'sklearn'),
        ('image-quality', 'image_quality'),
        ('opencv-python', 'cv2'),
        ('Pillow', 'PIL'),
        ('numpy', 'numpy'),
    ]
    
    all_good = True
    for package_name, import_name in packages:
        status = "✓" if check_package(package_name, import_name) else "✗"
        print(f"  {status} {package_name}")
        if status == "✗":
            all_good = False
    
    print("\n🤖 Ollama:")
    if check_ollama():
        print("  ✓ Running")
        models = list_ollama_models()
        if "openbmb/minicpm-v2.6:q4_K_M" in models:
            print("  ✓ MiniCPM-V 2.6 installed")
        else:
            print("  ✗ MiniCPM-V 2.6 not installed")
            all_good = False
    else:
        print("  ✗ Not running or not installed")
        all_good = False
    
    print("\n🖼️  RAW Support:")
    if check_command('dcraw'):
        print("  ✓ dcraw available")
    else:
        print("  ⚠️  dcraw not found (limited RAW support)")
    
    print("\n" + "=" * 60)
    if all_good:
        print("✓ All dependencies ready!")
    else:
        print("⚠️  Some dependencies missing")
        print("\nRun setup wizard to install:")
        print("  python setup_photosort.py --install")

# ==============================================================================
# VII. MAIN ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='PhotoSort v8.0 Setup Wizard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_photosort.py --install    # Run full setup wizard
  python setup_photosort.py --check      # Just check dependencies
        """
    )
    
    parser.add_argument('--install', action='store_true',
                       help='Run full installation wizard')
    parser.add_argument('--check', action='store_true',
                       help='Check dependencies without installing')
    
    args = parser.parse_args()
    
    if args.install:
        run_setup_wizard()
    elif args.check:
        run_quick_check()
    else:
        # Default: show help
        parser.print_help()
        print("\nRun with --check to see what's installed")
        print("Run with --install to start setup wizard")
