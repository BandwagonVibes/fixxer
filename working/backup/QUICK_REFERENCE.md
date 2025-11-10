# 📸 PhotoSort v7.0 - Quick Reference Card

## 🚀 Most Common Commands

```bash
# THE ONE-BUTTON WORKFLOW (start here!)
cd /Volumes/LUMIX/DCIM/112_PANA
photosort --auto

# Get creative feedback on your portfolio
cd ~/Photos/Portfolio
photosort --critique

# See session statistics
photosort --stats

# Preview what would happen (dry-run)
photosort --auto --preview
```

---

## 📁 What Goes Where

```
SD Card/
├── burst-001/           ← Grouped burst shots
├── _Keepers/            ← Good quality (sharp + well-exposed)
├── _Review_Maybe/       ← Borderline quality
├── _Review_Duds/        ← Blurry or badly exposed
└── _cull_log_*.json     ← Quality analysis data

iCloud Archive/
├── 2024-11-05_Architecture/
├── 2024-11-05_Street-Scenes/
├── 2024-11-05_Nature/
└── _import_log_*.json   ← Rename history

Photos with Critique/
├── photo.jpg
├── photo.json           ← AI critique sidecar
```

---

## 🎛️ Config File

**Location:** `~/.photosort.conf`

**Quick edit:**
```bash
nano ~/.photosort.conf
```

**Key settings:**
- `default_destination` - Where to archive
- `default_model` - AI model for naming
- `sharpness_good` / `sharpness_dud` - Cull thresholds
- `critique.default_model` - AI model for critiques

---

## 🔧 Troubleshooting One-Liners

```bash
# Ollama not responding
ollama serve

# Model not found
ollama pull bakllava

# Check what models you have
ollama list

# RAW support not working
brew install dcraw

# Progress bars not showing
pip3 install --break-system-packages tqdm

# ASCII art not animating
pip3 install --break-system-packages colorama
```

---

## ⚡ Power User Tips

**Adjust cull thresholds for your camera:**
```bash
# Run cull on test batch
photosort --cull

# Check actual scores
cat _cull_log_*.json | grep "sharpness"

# Edit config to match
nano ~/.photosort.conf
# Update sharpness_good / sharpness_dud
```

**Override critique model:**
```bash
photosort --critique --model llava
```

**Chain commands manually:**
```bash
photosort --group-bursts
photosort --cull
cd _Keepers && photosort
```

---

## 📊 Typical Speeds (M4 MacBook Air)

- Burst stacking: **~0.2s per image**
- Quality culling: **~0.5s per image**
- AI naming: **~4s per image**
- AI critique: **~25s per image**
- EXIF stats: **~0.1s per image**

---

## 🎯 Workflow Decision Tree

```
Got photos on SD card?
│
├─ Trust AI to pick keepers? → photosort --auto
│
├─ Want manual control?
│  ├─ Step 1: photosort --group-bursts
│  ├─ Step 2: photosort --cull
│  ├─ Step 3: Review _Review_Maybe/
│  └─ Step 4: cd _Keepers && photosort
│
├─ Just want stats? → photosort --stats
│
└─ Want creative feedback? → photosort --critique
```

---

## 📞 Quick Support

**Problem:** Config not loading  
**Fix:** Check `~/.photosort.conf` exists and is valid INI format

**Problem:** No keepers found  
**Fix:** Lower `sharpness_good` threshold in config

**Problem:** Model too slow  
**Fix:** Use smaller model like `llava:7b` instead of `bakllava`

**Problem:** Out of space  
**Fix:** Clean up `_Review_Duds/` folders from previous imports

---

## 🎨 Philosophy

> "Less noise, more signal."

This tool gets out of your way so you can focus on creating art.

- **Auto mode:** Hands-off automation
- **Manual tools:** Surgical control
- **AI critique:** Creative inspiration

Pick the workflow that matches your mood. 📸

---

**Keep this card handy for quick lookups!**

*∞vision crew | v7.0 Gold Master*
