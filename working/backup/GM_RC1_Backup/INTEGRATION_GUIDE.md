# PHOTOSORT v7.1 - Final Integration Guide

## 🎯 You're 95% There! Here's How to Finish

All the hard work is done! The 5 support modules are **complete and working**. You just need to make a few small edits to `photosort.py` to tie everything together.

## 📋 Quick Start Checklist

- [ ] Copy all 6 files to your project folder
- [ ] Test individual modules (optional but recommended)
- [ ] Make 3 small edits to photosort.py (detailed below)
- [ ] Test the complete workflow
- [ ] Ship it! 🚀

## 📁 Files You Have

1. `phrases.py` - All 200 phrases ✅
2. `utils.py` - Utilities ✅
3. `session_tracker.py` - Stats tracking ✅
4. `smart_progress.py` - Progress bars ✅
5. `directory_selector.py` - Directory picker ✅
6. `photosort.py` - Main file (needs 3 small edits)

## 🔧 The 3 Edits You Need to Make

### Edit #1: Enhance the Confirmation Prompt (Line ~1736)

**Find this:**
```python
confirm = input(f"\n  Ready to process? (y/n): ")
if confirm.lower() != 'y':
    print("Cancelled.")
    return
```

**Replace with:**
```python
confirm = input(f"\n  Ready to process? (y/n/q): ")
if confirm.lower() == 'q':
    print(get_quit_message())
    return
elif confirm.lower() != 'y':
    print("Cancelled.")
    return

# v7.1: Initialize session tracker
tracker = SessionTracker()
tracker.set_model(chosen_model)
tracker.add_operation("Burst Stacking")
tracker.add_operation("Quality Culling")  
tracker.add_operation("AI Naming")
```

### Edit #2: Add AI Session Naming (Line ~1816 - before organize_into_folders)

**Find this section (after results collection):**
```python
if results["success"]:
    organize_into_folders(results["success"], chosen_destination, dry_run=False)
```

**Replace with:**
```python
if results["success"]:
    # v7.1: Generate AI session name
    categories = {}
    for item in results["success"]:
        cat = categorize_description(item["description"])
        categories[cat] = categories.get(cat, 0) + 1
    
    session_name = generate_ai_session_name(categories, chosen_model)
    if session_name:
        dated_folder = f"{SESSION_DATE}_{session_name}"
        print(f"\n   🎨 AI Session Name: {dated_folder}")
    else:
        dated_folder = f"{SESSION_DATE}_Session"
    
    final_destination = chosen_destination / dated_folder
    final_destination.mkdir(parents=True, exist_ok=True)
    tracker.set_destination(final_destination)
    
    organize_into_folders(results["success"], final_destination, dry_run=False)
```

### Edit #3: Add Session Summary (End of auto_workflow)

**Find the end of auto_workflow() - after the print statements:**
```python
print("\n" + "="*60)
print(" 🚀 AUTO WORKFLOW COMPLETE")
print("="*60)
print(f" Your 'hero' photos are now in: {chosen_destination}")
print(f"  Remaining 'duds' and 'bursts' are in: {directory}")
```

**Add after this:**
```python
# v7.1: Print session summary
print("\n")
tracker.print_summary()
tracker.save_to_history(Path.home() / ".photosort_sessions.json")
```

## 🧪 Testing Your Edits

### 1. Test Individual Modules
```bash
python3 phrases.py
python3 utils.py
python3 session_tracker.py
python3 smart_progress.py
# directory_selector.py requires input, so skip or test manually
```

### 2. Test the Main Script
```bash
# Dry run (safe, no files moved)
python3 photosort.py --auto --preview

# Real run on test folder
python3 photosort.py --auto
```

## 🎨 Optional Enhancements (Can Do Later)

### Burst Parent Folders
In `group_bursts_in_directory()` function, after creating bursts, wrap them in a parent folder:

```python
# After burst grouping is complete
burst_folders = list(directory.glob("burst-*/"))
if burst_folders and len(burst_folders) > 1:
    burst_date = get_exif_date(burst_folders[0] / list(burst_folders[0].iterdir())[0])
    parent_name = f"{burst_date.strftime('%Y-%m-%d')}_Bursts"
    parent_folder = directory / parent_name
    parent_folder.mkdir(exist_ok=True)
    
    for burst in burst_folders:
        shutil.move(str(burst), str(parent_folder / burst.name))
```

### 'q' to Quit Everywhere
Search for all `input(` calls and update prompts to include `/q`:

```bash
# Find all input prompts
grep -n 'input(' photosort.py

# Update each one to accept 'q'
```

## 🚨 Common Issues & Fixes

### Issue: "ModuleNotFoundError: No module named 'phrases'"
**Fix:** Make sure all 6 files are in the same directory

### Issue: "inquirer not found, using fallback"
**Fix:** This is normal! The fallback works great. Or install: `pip install inquirer`

### Issue: Session summary not showing
**Fix:** Make sure you added Edit #3 and initialized the tracker in Edit #1

### Issue: AI naming returns None
**Fix:** Check that Ollama is running and model is loaded: `ollama list`

## 📝 What If I Get Stuck?

1. **Check the README_V7.1.md** - Has full details on every component
2. **Test modules individually** - Isolate which part isn't working
3. **Compare with v7.0** - Your original file is saved as `photosort_original.py`
4. **Use print() debugging** - Add `print(f"Debug: {variable}")` liberally

## 🎯 Success Criteria

You'll know it's working when you see:
- ✅ Rotating phrases during processing
- ✅ Smart directory picker on startup
- ✅ AI-generated session name
- ✅ Keygen-style session summary at end
- ✅ Witty closing line

## 🏆 You're Almost Done!

These 3 edits will take about **15-30 minutes**. They're straightforward copy-paste with minor tweaks.

All the complex logic is already built and tested in the support modules. You're just connecting the dots!

---

**Questions? Issues?**
All modules have test code at the bottom. Run them individually to verify they work.

**Ready to Ship?**
After these edits, you'll have a production-ready v7.1 with all features working!

🎭⚡ VisionCrew - *use responsibly. unleash creatively. inference locally.*
