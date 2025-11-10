# 📸 PhotoSort v7.0 - GOLD MASTER

**AI-Powered Photography Workflow Automation**

Created by: Nick (∞vision crew)  
Engineered by: Claude (Anthropic) + Gemini (Google)

---

## 🎯 What It Does

PhotoSort is a command-line tool that automates your photography workflow using local AI models. It can:

- **Auto Mode**: Complete hands-off workflow (Stack → Cull → AI-Name → Archive)
- **AI Critique**: Get Creative Director feedback on your images
- **Burst Stacking**: Group similar shots and pick the sharpest
- **Quality Culling**: Sort images by sharpness and exposure
- **EXIF Insights**: Analytics dashboard for your shooting session
- **Smart Prep**: Copy keepers to Lightroom-ready folder

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Core dependencies
pip3 install --break-system-packages requests imagehash Pillow opencv-python numpy exifread

# Optional (for progress bars and colored output)
pip3 install --break-system-packages tqdm colorama

# RAW support (macOS with Homebrew)
brew install dcraw
```

### 2. Install Ollama + Models

```bash
# Install Ollama (https://ollama.ai)
brew install ollama

# Install vision model for AI naming
ollama pull bakllava

# Install critique model for creative feedback (optional)
ollama pull openbmb/minicpm-v2.6:q4_K_M
```

### 3. Install PhotoSort

```bash
# Create scripts directory
mkdir -p ~/scripts
cd ~/scripts

# Copy photosort.py to ~/scripts/
cp /path/to/photosort_v7_GOLD_MASTER.py ~/scripts/photosort.py
chmod +x ~/scripts/photosort.py

# Create virtual environment (recommended)
python3 -m venv ~/scripts/venv
~/scripts/venv/bin/pip install --break-system-packages requests imagehash Pillow opencv-python numpy exifread tqdm colorama

# Add alias to your shell config (~/.zshrc or ~/.bashrc)
echo 'alias photosort="~/scripts/venv/bin/python3 ~/scripts/photosort.py"' >> ~/.zshrc
source ~/.zshrc
```

### 4. Configure Defaults (Optional)

```bash
# Copy sample config to home directory
cp photosort.conf.sample ~/.photosort.conf

# Edit with your preferred destination and settings
nano ~/.photosort.conf
```

---

## 📖 Usage Guide

### The One-Button Workflow: `--auto`

**Recommended for most users.** Fully automated pipeline:

```bash
cd /Volumes/LUMIX/DCIM/112_PANA  # Your SD card
photosort --auto
```

**What it does:**
1. Shows EXIF insights (read-only preview)
2. Stacks burst shots into `burst-001/`, `burst-002/`, etc.
3. Culls singles into `_Keepers/`, `_Review_Maybe/`, `_Review_Duds/`
4. AI-names all "hero" files (keepers + burst picks)
5. Organizes into dated folders by subject
6. Archives to iCloud (or your configured destination)

**Result:** Your best shots are renamed, organized, and archived. Duds stay on the SD card for manual review.

---

### Manual Tools (Power User Mode)

#### 🎨 AI Critique (`--critique` or `--art`)

Get Creative Director feedback on your images:

```bash
cd ~/Photos/ToReview
photosort --critique
```

**What it does:**
- Analyzes composition, lighting, color
- Suggests artistic post-processing improvements
- Saves `.json` sidecar files next to each image
- Example output: `photo.jpg` → `photo.json`

**Options:**
```bash
# Use a different model
photosort --critique --model llava

# Preview what would be analyzed
photosort --critique --preview
```

**Sample JSON Output:**
```json
{
  "composition_score": 8,
  "composition_critique": "Strong use of leading lines...",
  "lighting_critique": "Golden hour light is soft and warm...",
  "color_critique": "Muted autumn palette works well...",
  "final_verdict": "Solid image with room for dramatic enhancement",
  "creative_mood": "Cinematic & Moody",
  "creative_suggestion": "To achieve a cinematic feel, apply a teal-orange grade..."
}
```

---

#### 📊 EXIF Stats (`--stats` or `--exif`)

See insights about your shooting session:

```bash
photosort --stats
```

**Shows:**
- Session timeline (start time, end time, duration)
- Lighting conditions breakdown
- Camera gear used
- Most-used focal lengths
- Aperture habits

**Example Output:**
```
EXIF INSIGHTS: 112_PANA
================================================================
📖 Session Story:
   Started:     Sat, Nov 02 2024 at 02:15 PM
   Ended:       Sat, Nov 02 2024 at 05:47 PM
   Duration:    3h 32m
   Total Shots: 247 (247 with EXIF data)
----------------------------------------------------------------
☀️ Lighting Conditions:
   Afternoon    : 89   ■■■■■■■■■■■■■■■■■■■■■■■■■
   Golden Hour  : 158  ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
```

---

#### 📸 Burst Stacking (`--group-bursts` or `-b`)

Group visually similar shots and pick the sharpest:

```bash
photosort --group-bursts
```

**What it does:**
- Calculates perceptual hashes for all images
- Groups similar shots into `burst-001/`, `burst-002/`, etc.
- Renames sharpest image with `_PICK_` prefix

**Example:**
```
burst-001/
  _PICK_P1080234.RW2  ← Sharpest
  P1080235.RW2
  P1080236.RW2
```

---

#### 🗑️ Quality Culling (`--cull` or `-c`)

Sort images by technical quality:

```bash
photosort --cull
```

**What it does:**
- Analyzes sharpness (Laplacian variance)
- Analyzes exposure (clipped highlights/shadows)
- Sorts into 3 tiers:
  - `_Keepers/` - Sharp + good exposure
  - `_Review_Maybe/` - Borderline cases
  - `_Review_Duds/` - Blurry or bad exposure

**Tuning:** Edit thresholds in `~/.photosort.conf` if defaults don't match your camera.

---

#### ✨ Smart Prep (`--prep` or `--pe`)

Copy only "Good" tier images to Lightroom folder:

```bash
photosort --prep
```

**What it does:**
- Runs quality analysis
- Copies (not moves) keepers to `_ReadyForLightroom/`
- Leaves originals untouched

**Use case:** You want to cull on the SD card, then selectively import to Lightroom.

---

### Legacy Ingest (No Command)

AI-name and organize ALL files (no culling):

```bash
photosort
```

**Prompts for:**
- Destination folder
- AI model to use

**What it does:**
- AI-describes every image
- Renames based on content
- Organizes into dated subject folders

---

## 🎛️ Configuration File

**Location:** `~/.photosort.conf`

**Structure:**
```ini
[ingest]
default_destination = ~/Photos/Archive
default_model = bakllava

[cull]
sharpness_good = 40.0
sharpness_dud = 15.0
exposure_dud_pct = 0.20
exposure_good_pct = 0.05

[burst]
similarity_threshold = 8

[critique]
default_model = openbmb/minicpm-v2.6:q4_K_M
```

**Note:** All settings are optional. Built-in defaults are used if config doesn't exist.

---

## 🔧 Command Reference

| Command | Alias | Description | Use Case |
|---------|-------|-------------|----------|
| `--auto` | - | Full automated workflow | **Start here** |
| `--critique` | `--art` | AI creative feedback | Post-processing ideas |
| `--stats` | `--exif` | Session analytics | Track your habits |
| `--group-bursts` | `-b` | Stack similar shots | Fast action shooting |
| `--cull` | `-c` | Quality sorting | Manual culling |
| `--prep` | `--pe` | Copy keepers | Lightroom import prep |
| (none) | - | Legacy AI ingest | Batch rename |

**Global Options:**
- `--preview` or `-p`: Dry-run mode (no files modified)
- `--model <name>`: Override model (for `--critique` only)
- `--help` or `-h`: Show help message

---

## 🛠️ Troubleshooting

### "Could not connect to Ollama server"

**Solution:**
```bash
# Start Ollama
ollama serve

# Verify it's running
ollama list
```

### "Model 'bakllava' not found"

**Solution:**
```bash
ollama pull bakllava
```

### "No dcraw found" (RAW support)

**Solution:**
```bash
brew install dcraw
```

### Thresholds don't match my camera

**Solution:** Edit `~/.photosort.conf` and adjust `sharpness_good`/`sharpness_dud`:
- Run `photosort --cull` on a test batch
- Check `_cull_log_*.json` for actual sharpness scores
- Adjust thresholds based on your camera's output

### Progress bars not showing

**Solution:**
```bash
pip3 install --break-system-packages tqdm
```

### ASCII art not animating

**Solution:**
```bash
pip3 install --break-system-packages colorama
```

---

## 📊 Technical Details

### Supported Formats

**Images:**
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- RAW (`.rw2` - Lumix, with dcraw)

**Notes:**
- Other RAW formats (`.cr2`, `.nef`, `.arw`, `.dng`) should work if dcraw supports them
- HEIC/HEIF not supported (convert to JPEG first)

### Performance

**Typical Speed (M4 MacBook Air, 10-core CPU):**
- AI naming: ~3-5 seconds per image
- Quality analysis: ~0.5 seconds per image
- EXIF scan: ~0.1 seconds per image
- AI critique: ~20-30 seconds per image

**Concurrency:** Default 5 workers (adjustable in code)

### Storage

**Output Folders:**
```
SD Card/
  burst-001/          # Burst groups
  burst-002/
  _Keepers/           # Good quality singles
  _Review_Maybe/      # Borderline quality
  _Review_Duds/       # Blurry/bad exposure
  _ReadyForLightroom/ # Smart prep output
  _cull_log_*.json    # Quality analysis data
  _exif_summary_*.json # Session statistics

Archive/ (iCloud)
  2024-11-02_Architecture/
  2024-11-02_Street-Scenes/
  2024-11-02_Nature/
  _import_log_*.json  # Rename history
```

---

## 🎨 Workflow Recommendations

### Scenario 1: Event Photography (Wedding, Concert, etc.)

```bash
# Step 1: Stack burst shots
photosort --group-bursts

# Step 2: Cull singles
photosort --cull

# Step 3: Review Maybe folder manually, move keepers

# Step 4: Run legacy ingest on all keepers
cd _Keepers
photosort
```

**Why:** You want manual control over which shots make it to the archive.

---

### Scenario 2: Personal/Travel Photography

```bash
# One command - let AI decide
photosort --auto
```

**Why:** You trust the quality thresholds and want hands-off automation.

---

### Scenario 3: Portfolio Review

```bash
# Get creative feedback on your best shots
cd ~/Portfolio/ToReview
photosort --critique
```

**Why:** You want AI suggestions for post-processing improvements.

---

## 📜 Version History

**V7.0 - Gold Master** (Nov 2024)
- ✨ AI Critic feature with JSON sidecars
- ✨ Config file system (`~/.photosort.conf`)
- ✨ Animated ASCII art intro
- 🐛 Crash-proof config loading
- 🐛 --model override for critique
- 🐛 Dry-run support for critique

**V6.5** (Oct 2024)
- ♻️ Auto mode refactor (workflow reordering)
- 🐛 Eliminated code duplication

**V6.4** (Oct 2024)
- ✨ EXIF insights dashboard

**V6.3** (Oct 2024)
- ✨ Smart prep mode

**V6.2** (Oct 2024)
- 🐛 Burst stacking improvements

**V6.0** (Oct 2024)
- ✨ Quality culling engine

**V5.0** (Sep 2024)
- ✨ Burst stacker

**V4.1** (Sep 2024)
- ✨ Concurrent processing

**V4.0** (Sep 2024)
- ✨ Vision model integration

---

## 🙏 Credits

**Development:**
- Nick - Product vision, testing, R&D
- Claude (Anthropic) - Code architecture, debugging
- Gemini (Google) - Feature implementation

**Open Source Libraries:**
- Ollama - Local AI inference
- imagehash - Perceptual hashing
- OpenCV - Image quality analysis
- exifread - EXIF parsing
- tqdm - Progress bars
- colorama - ASCII art colors

---

## 📄 License

Personal use only. Created for Nick's photography workflow.

---

## 🤝 Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review `_cull_log_*.json` or `_import_log_*.json` for diagnostics
3. Make sure Ollama is running: `ollama list`

**Philosophy:** "Less noise, more signal" - this tool is designed to get out of your way and let you focus on creating.

---

**✨ Ready to organize your photos? Start with:**

```bash
cd /path/to/sd-card
photosort --auto
```

**Happy shooting! 📸**
