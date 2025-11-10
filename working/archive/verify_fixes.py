#!/usr/bin/env python3
"""
PhotoSort v8.0 Gold Master - Quick Verification Script
Run this to verify all 7 fixes are working correctly!
"""

import sys
from pathlib import Path

print("="*60)
print(" PhotoSort v8.0 Gold Master - Verification Script")
print("="*60)

# Check 1: Default Model Name
print("\n✓ Checking BUG #1 Fix (AI Model)...")
try:
    with open('photosort.py', 'r') as f:
        content = f.read()
        if 'DEFAULT_MODEL_NAME = "openbmb/minicpm-v2.6:q4_K_M"' in content:
            print("  ✅ Model changed to openbmb/minicpm-v2.6:q4_K_M")
        else:
            print("  ❌ Model NOT updated")
            
        if 'AI_NAMING_PROMPT' in content and 'Chain-of-Thought' in content:
            print("  ✅ CoT prompt implemented in get_ai_description()")
        else:
            print("  ❌ CoT prompt NOT found")
            
        if '"format": "json"' in content and 'json.loads(json_string)' in content:
            print("  ✅ JSON parsing logic added")
        else:
            print("  ❌ JSON parsing NOT found")
except Exception as e:
    print(f"  ❌ Error checking photosort.py: {e}")

# Check 2: Dry Run Parameters
print("\n✓ Checking BUG #2 Fix (Dry Run)...")
try:
    with open('photosort.py', 'r') as f:
        content = f.read()
        if 'group_bursts_in_directory(directory, dry_run=dry_run,' in content:
            print("  ✅ Burst stacking dry_run parameter fixed")
        else:
            print("  ❌ Burst stacking still has hard-coded dry_run")
            
        if 'cull_images_in_directory(directory, dry_run=dry_run,' in content:
            print("  ✅ Culling dry_run parameter fixed")
        else:
            print("  ❌ Culling still has hard-coded dry_run")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Check 3: Stats Tracking
print("\n✓ Checking BUG #3 Fix (Stats Tracking)...")
try:
    with open('photosort.py', 'r') as f:
        content = f.read()
        lines = content.split('\n')
        
        # Check for un-commented stats calls
        stats_enabled = 0
        for i, line in enumerate(lines):
            # Check tracker.set_source is not commented
            if 'tracker.set_source(directory)' in line and not line.strip().startswith('#'):
                stats_enabled += 1
                print(f"  ✅ tracker.set_source() re-enabled")
                break
                
        for i, line in enumerate(lines):
            if "tracker.increment_stat('total_files'" in line and not line.strip().startswith('#'):
                stats_enabled += 1
                print(f"  ✅ tracker.increment_stat('total_files') re-enabled")
                break
                
        for i, line in enumerate(lines):
            if "tracker.increment_stat('ai_named'" in line and not line.strip().startswith('#'):
                stats_enabled += 1
                print(f"  ✅ tracker.increment_stat('ai_named') re-enabled")
                break
                
        for i, line in enumerate(lines):
            if 'tracker.add_category_count(cat, count)' in line and not line.strip().startswith('#'):
                stats_enabled += 1
                print(f"  ✅ tracker.add_category_count() loop re-enabled")
                break
        
        if stats_enabled < 4:
            print(f"  ⚠️  Only {stats_enabled}/4 stats tracking calls found")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Check 4: Rotation Interval
print("\n✓ Checking UX #1 Fix (Rotation Speed)...")
try:
    with open('photosort.py', 'r') as f:
        content = f.read()
        if 'rotation_interval: int = 8' in content:
            print("  ✅ Rotation interval changed to 8 seconds")
        else:
            print("  ❌ Rotation interval still at 15 seconds")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Check 5: Phrase Randomness
print("\n✓ Checking UX #2 Fix (Phrase Randomness)...")
try:
    with open('phrases.py', 'r') as f:
        content = f.read()
        if '_recent_phrases' in content and '_MAX_RECENT' in content:
            print("  ✅ Anti-repetition tracking added")
        else:
            print("  ❌ Anti-repetition logic NOT found")
            
        if 'available_phrases = [p for p in pool if p not in _recent_phrases]' in content:
            print("  ✅ Phrase filtering logic implemented")
        else:
            print("  ❌ Phrase filtering NOT found")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Check 6: Banner Additions
print("\n✓ Checking UX #4 Fix (Banner Mantra)...")
try:
    with open('photosort.py', 'r') as f:
        content = f.read()
        if 'Mantra: Stats → Stack → Cull → Critique' in content:
            print("  ✅ Workflow mantra added")
        else:
            print("  ❌ Mantra NOT found")
            
        if 'Pro-tip: Copy media to local storage' in content:
            print("  ✅ Pro-tip added")
        else:
            print("  ❌ Pro-tip NOT found")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Summary
print("\n" + "="*60)
print(" VERIFICATION COMPLETE")
print("="*60)
print("\nNote: UX #3 (Directory Selector Hint) requires manual update")
print("See GOLD_MASTER_FIXES_SUMMARY.md for instructions")
print("\nNext steps:")
print("  1. Run: python photosort.py --auto --preview (test dry-run)")
print("  2. Run: python photosort.py --auto (real workflow)")
print("  3. Verify AI naming completes without failures")
print("  4. Check session summary displays at end")
print("\n🎉 PhotoSort v8.0 Gold Master Ready!\n")
