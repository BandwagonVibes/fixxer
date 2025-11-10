# 📸 PhotoSort v9.1

**AI-Powered Photography Workflow Automation**

Professional-grade command-line tool that automates photography post-processing using local AI inference. Built for photographers who shoot hundreds of photos per session.

> Created by Nick (∞vision crew)  
> Engineered with Claude (Anthropic) + Gemini (Google)

---

## ✨ What It Does

**Complete hands-off workflow:**
1. **Groups burst shots** with AI-named folders ("golden-retriever-playing")
2. **Assesses quality** using professional BRISQUE metrics
3. **AI names files** with consistent, descriptive names
4. **Organizes content** into semantic folders
5. **Archives hero shots** ready for editing

**All running locally on your machine. No cloud. No subscriptions.**

---

## 🔥 v9.1 Features

- **AI Burst Naming** - "sunset-over-ocean" not "burst-001"
- **Organized Structure** - Clean `_Bursts/` parent folder
- **Deterministic** - Same photo = same name every time (qwen2.5vl:3b)
- **Professional Engines** - CLIP semantic detection + BRISQUE quality
- **Runs on MacBook Air** - Tested on fanless M1, 8GB RAM

---

## 🚀 Quick Start

```bash
# Clone repo
git clone https://github.com/yourusername/photosort.git
cd photosort

# Install dependencies
pip install -r requirements.txt

# Install system tools (macOS)
brew install exiftool dcraw

# Install Ollama + model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5vl:3b

# Run auto workflow
python photosort.py --auto
```

---

## 📊 Before & After

### Before
```
session/
├── IMG_4501.jpg
├── IMG_4502.jpg
├── IMG_4503.jpg
└── ... (200+ files)
```

### After (2 minutes)
```
session/
├── _Bursts/
│   ├── golden-retriever-playing/
│   │   ├── _PICK_IMG_4501.jpg    ← Sharpest
│   │   └── IMG_4502.jpg
│   └── sunset-over-ocean/
│       └── _PICK_IMG_4510.jpg
├── _Keepers/                      ← Quality picks
├── _Review_Maybe/                 ← Borderline shots
└── old-desktop-archive/           ← Hero shots
    ├── Architecture/
    └── Street-Scenes/
```

---

## 🎯 Key Features

### 🤖 **AI-Powered Everything**
- **Semantic burst detection** (CLIP) - understands content
- **Quality assessment** (BRISQUE) - distinguishes bokeh from blur
- **Consistent naming** (qwen2.5vl) - deterministic across runs
- **Content organization** - automatic smart folders

### ⚡ **Fast & Local**
- Runs on **fanless MacBook Air**
- No cloud uploads
- ~2 minutes for 200 images
- First run downloads CLIP model (~600MB, one-time)

### 🎨 **Professional Results**
- Industry-standard quality metrics
- Artistic critique mode (optional)
- EXIF analytics
- RAW format support

---

## 📦 What's Included

### Core Files
- `photosort.py` - Main application (v9.1)
- `burst_engine.py` - CLIP semantic detection
- `cull_engine.py` - BRISQUE quality assessment
- `directory_selector_v2.py` - Fixed file picker
- `phrases.py` - Progress bar messages
- `utils.py` - Helper functions
- `session_tracker.py` - Analytics

### Configuration
- `photosort.conf` - Configuration template
- `.gitignore` - Comprehensive ignore rules
- `requirements.txt` - Python dependencies

### Documentation
- `README.md` - This file
- `V8_ENGINE_INSTALLATION.md` - Engine setup
- `PHOTOSORT_V9.1_GUIDE.md` - Feature walkthrough
- `V9.1_ARTIST_FRIENDLY_README.txt` - Non-technical guide

### Testing
- `test_critique_prompt.py` - Test AI prompts

---

## ⚙️ Configuration

Edit `~/.photosort.conf`:

```ini
[models]
default_model = qwen2.5vl:3b

[burst]
burst_algorithm = clip         # CLIP or legacy
burst_parent_folder = true     # _Bursts/ organization

[cull]
cull_algorithm = brisque       # BRISQUE or legacy
keeper_threshold = 35.0        # Quality threshold
```

---

## 🔧 Commands

```bash
# Complete workflow
python photosort.py --auto

# Individual operations
python photosort.py --group-bursts    # Burst detection only
python photosort.py --cull            # Quality assessment only
python photosort.py --ai-name         # AI naming only
python photosort.py --ai-critique     # Creative feedback
python photosort.py --exif-stats      # EXIF analytics

# Dry run (preview)
python photosort.py --preview --auto
```

---

## 📊 Performance

**MacBook Air M1, 8GB RAM:**
- 200 images → ~2 minutes total
- Burst detection: 4 seconds (CLIP)
- Quality culling: 2 seconds (BRISQUE)
- AI naming: 2 seconds per image

---

## 🛠️ Tech Stack

- **Python 3.8+**
- **Ollama** - Local AI inference
- **qwen2.5vl:3b** - Vision model (3B params)
- **CLIP** - Semantic embeddings
- **BRISQUE** - Quality metrics
- **exiftool** - EXIF reading
- **dcraw** - RAW support

---

## 🎯 Requirements

- macOS (tested), Linux (should work)
- Python 3.8+
- ~1GB disk space (CLIP model)
- Ollama running locally
- exiftool, dcraw (system tools)

---

## 🐛 Troubleshooting

**"CLIP not available"**
```bash
pip install sentence-transformers scikit-learn
```

**"BRISQUE not available"**
```bash
pip install image-quality opencv-python
```

**"Connection refused to Ollama"**
```bash
ollama serve
```

See full troubleshooting in docs.

---

## 📖 Documentation

- Installation: `V8_ENGINE_INSTALLATION.md`
- Features: `PHOTOSORT_V9.1_GUIDE.md`
- Artist Guide: `V9.1_ARTIST_FRIENDLY_README.txt`
- Quick Start: `QUICK_START.md`

---

## 🎨 Version History

- **v9.1** - AI burst naming, organized structure (current)
- **v9.0** - qwen2.5vl integration
- **v8.0** - CLIP + BRISQUE engines
- **v7.1** - Session tracking, 200 phrases
- **v7.0** - AI critique, config system
- **v6.0** - Quality culling
- **v5.0** - Burst stacking

---

## 📝 License

[Your choice - MIT recommended]

---

## 🙏 Credits

- **Anthropic** - Claude for engineering
- **Google** - Gemini for guidance
- **Alibaba** - qwen2.5vl model
- **Ollama** - Local AI platform
- **Photography Community** - Feedback & testing

---

## ⭐ Support

If PhotoSort saves you hours, star the repo! ⭐

Issues, suggestions, and feedback welcome.

---

**Built by a photographer tired of manual sorting** 🔥
