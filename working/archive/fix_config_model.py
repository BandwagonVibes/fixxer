#!/usr/bin/env python3
"""
PhotoSort v8.0 GM - Config File Updater
Fixes the model name in your ~/.photosort.conf file
"""

from pathlib import Path
import configparser

CONFIG_FILE = Path.home() / ".photosort.conf"
NEW_MODEL = "openbmb/minicpm-v2.6:q4_K_M"

print("="*60)
print(" PhotoSort v8.0 - Config Model Updater")
print("="*60)

if not CONFIG_FILE.exists():
    print(f"\n✅ No config file found at {CONFIG_FILE}")
    print("   PhotoSort will create one with the correct model on first run.")
else:
    print(f"\n📝 Found config file: {CONFIG_FILE}")
    
    # Read existing config
    parser = configparser.ConfigParser()
    parser.read(CONFIG_FILE)
    
    # Check current model
    current_model = parser.get('ingest', 'default_model', fallback='(not set)')
    print(f"\n   Current model: {current_model}")
    
    if current_model == NEW_MODEL:
        print(f"   ✅ Already set to {NEW_MODEL}!")
    else:
        # Update the model
        if not parser.has_section('ingest'):
            parser.add_section('ingest')
        
        parser.set('ingest', 'default_model', NEW_MODEL)
        
        # Write back to file
        with open(CONFIG_FILE, 'w') as f:
            parser.write(f)
        
        print(f"   ✅ Updated to: {NEW_MODEL}")
        print(f"\n🎉 Config file updated successfully!")

print("\n" + "="*60)
print(" Next Steps:")
print("="*60)
print("  1. Run: python photosort.py --auto --preview")
print("  2. Verify model shows as: openbmb/minicpm-v2.6:q4_K_M")
print("  3. If correct, run for real: python photosort.py --auto")
print("\n✨ PhotoSort is ready!\n")
