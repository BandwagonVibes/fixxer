# FIXXER ✞ PRO
### Professional-Grade Photography Workflow Automation

![Version](https://img.shields.io/badge/version-1.0-red.svg)
![Python](https://img.shields.io/badge/python-3.10--3.12-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**"CHAOS PATCHED // LOGIC INJECTED"**
![warez_dry_run_sped_up_original30](https://github.com/user-attachments/assets/daba32a1-7797-4b2c-9f4b-99866e9b6007)

---

## 🎯 What is FIXXER?

FIXXER is a professional photography workflow automation tool that combines **AI vision models**, **cryptographic integrity verification**, and **intelligent quality analysis** to streamline your post-processing pipeline.

Built for photographers who demand both **speed** and **safety** in their digital asset management.

---

## ✨ Key Features

### 🔐 **Hash-Verified File Operations**
- **SHA256 integrity checking** on every file move
- **Halt-on-mismatch** protection prevents corruption
- **JSON sidecar files** (.fixxer.json) create audit trails
- Production-tested: 120+ files, zero corruption

### 🤖 **AI-Powered Workflows**
- **Vision-based naming** using Ollama models (qwen2.5vl, llava, etc.)
- **Semantic burst detection** with CLIP embeddings
- **AI session naming** from visual analysis
- **Creative critique mode** for artistic feedback
- **Dry-run preview mode** with intelligent AI caching (50%+ speed boost on execution)

### 📊 **Quality Analysis Pipeline**
- **BRISQUE quality scoring** for sharpness assessment
- **Exposure analysis** (crushed blacks, blown highlights)
- **CLIP-based burst grouping** (semantic similarity, not just timestamps)
- **Automated culling** into Tier A/B/C folders

### 🎨 **Two UI Modes**
- **Standard Mode**: Warez-inspired red/white/black aesthetic
- **Pro Mode**: Phantom Redline - tactical precision dashboard
- **Toggle with F12** - Switch between modes on-the-fly
- Real-time **system monitoring** (RAM, CPU sparklines)
- **Milestone HUD** for workflow progress tracking (Pro Mode)

### 📷 **RAW File Support**
- **120+ RAW formats** via rawpy/libraw
- Cross-platform: Linux, macOS, Windows
- Supports: RW2, CR2, CR3, NEF, ARW, DNG, RAF, ORF, PEF, SRW, and more
- Zero temp files - pure in-memory processing

---

## 🚀 Quick Start

**Zero friction. Full power.**

### Prerequisites
- **macOS** (Homebrew installation) or **Python 3.10-3.12** for manual install
- **Ollama** (for AI vision features) - [https://ollama.ai](https://ollama.ai)
- Supported OS: macOS, Linux, Windows (WSL recommended)

### 1. Install via Homebrew (Recommended - macOS)

```bash
# Add the FIXXER tap
brew tap bandwagonvibes/fixxer

# Install FIXXER
brew install fixxer
```

That's it! Homebrew handles all dependencies automatically.

### 2. Launch

```bash
fixxer
```

**Note:** On first launch, FIXXER will auto-download the CLIP vision model (~300MB). This happens only once.

### 3. Optional: Install Ollama Vision Model

For AI naming and creative critique features:

```bash
# Install Ollama from https://ollama.ai
# Then pull a vision model:
ollama pull qwen2.5vl:3b
```

**Recommended model:** `qwen2.5vl:3b` (fast, accurate, 2.2GB)

---

### 🔰 New to Terminals?

If you've never opened a terminal before, check out our [**Beginner's Guide**](BEGINNERS_GUIDE.md) - a gentle introduction that teaches you everything you need to know.

---

### 🔧 Development Installation (From Source)

For development or if you're on Linux/Windows, you can install from source:

```bash
git clone https://github.com/BandwagonVibes/fixxer.git
cd fixxer

# Create a virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install FIXXER + All Dependencies (CLIP, BRISQUE, Engine)
# This also installs the 'fixxer' command globally in this venv
pip install -e .
```

**Launch:** Since you installed in editable mode (`-e .`), just type `fixxer` after activating your venv.

**Note:** Python 3.13+ is not currently supported due to dependency constraints.

---

### 🔧 Advanced: Manual Alias Setup

If you prefer running from source without installing the package, you can set up a shell alias:

**macOS / Linux (zsh or bash)**

Add this to your `~/.zshrc` or `~/.bashrc`:

```bash
# FIXXER ✞ PRO Launcher
# Adjust path to match where you cloned the repo
alias fixxer='source ~/fixxer/venv/bin/activate && python3 -m fixxer'
```

Reload shell: `source ~/.zshrc`

**Windows (PowerShell)**

Open your profile: `notepad $PROFILE`

Paste this function at the bottom:

```powershell
function fixxer {
    # Adjust path to match where you cloned the repo
    $FixxerPath = "$HOME\fixxer"

    # Activate Venv and Run
    & "$FixxerPath\venv\Scripts\Activate.ps1"
    python -m fixxer
}
```

Reload profile: `. $PROFILE`

---

## 🤖 Why Qwen2.5-vl:3b?

FIXXER is designed to work like an **appliance** - reliable, consistent, and predictable. After extensive research and testing, we chose **Qwen2.5-vl:3b** as the recommended model for specific reasons:

### Proven Reliability
- **Tested on 150+ photos** across dozens of sessions
- **Consistent naming** - produces the same results run after run
- **Rock-solid JSON output** - only one parsing issue in all testing (99.9%+ reliability)
- **Production-ready** - not experimental, it just works

### Technical Advantages
- **Spatial awareness** - Critical for composition critique and understanding scene layout
- **Structured output** - Reliably generates valid JSON for deterministic parsing
- **Speed/quality balance** - Fast enough for real-time workflows, accurate enough for professional use
- **Efficient footprint** - 2.2GB model runs smoothly on MacBook Air hardware

### Model Compatibility Note
While you **can** swap models using the Model selector (press `M`), results may vary:
- **Larger models** (7B+) - Potentially better quality, but slower and more memory-intensive
- **Smaller models** (1B-2B) - Faster, but may lose spatial understanding and JSON reliability
- **Alternative vision models** - Not all are suitable for photography workflows (some lack spatial reasoning, others produce inconsistent output)

**Our recommendation:** Start with `qwen2.5vl:3b`. It's been battle-tested for this exact use case.

---

## ⌨️ Keyboard Shortcuts

FIXXER is fully keyboard-driven. All buttons have hotkeys:

### Navigation & Setup
- **1** - Set Source directory (from file browser selection)
- **2** - Set Destination directory (opens selector)
- **D** - Dry Run (preview workflow without moving files)
- **M** - Select Ollama Model
- **F12** - Toggle Pro Mode (Warez ↔ Phantom Redline)

### Workflows
- **A** - Auto Workflow (complete pipeline)
- **B** - Bursts (group similar shots)
- **C** - Cull (quality analysis)
- **S** - Stats (EXIF insights)
- **K** - Critique (AI creative feedback)

### System
- **Q** - Quit
- **R** - Refresh Config
- **Esc** - Stop current workflow
- **Ctrl+C** - Force quit

**Tip:** Hover over any button to see its keyboard shortcut in the tooltip!

---

## 🔍 Dry Run Preview Mode

**Try before you commit.** The dry-run feature lets you preview any workflow without moving a single file.

### How It Works

1. Press **D** to open the dry-run modal
2. Select which workflow to preview: **Auto**, **Burst**, or **Cull**
3. FIXXER simulates the entire workflow:
   - Calculates all file operations
   - Generates AI names (cached for later)
   - Shows collision-aware filename resolution
   - Displays full preview log with "WOULD MOVE:" entries
4. Review the preview log - **zero files moved**
5. Choose what to do next:
   - **Execute Now** - Run the real workflow using cached AI results (50%+ faster)
   - **Forget & Redo** - Clear cache and start fresh

### Key Features

- **Zero footprint** - No folders created, no files moved, no logs written
- **Intelligent AI caching** - AI results cached with model-aware keys and mtime validation
- **Thread-safe** - Cache safely shared across concurrent operations
- **10-minute TTL** - Cache expires after 10 minutes for freshness
- **Collision-aware** - Preview shows exact final filenames including duplicates
- **Full workflow simulation** - Burst grouping, quality culling, AI naming - everything runs in preview mode

### Why Use It?

- **Verify AI names** before committing to file operations
- **Check collision handling** when duplicate names would occur
- **Test workflow settings** without risk
- **Speed up execution** with cached AI results (no re-inference needed)

---

## 📖 Workflow Overview

### **Auto Workflow** (Recommended)
Complete end-to-end processing:

1. **Analyze Session** - EXIF statistics and insights
2. **Stack Bursts** - CLIP-based semantic grouping + AI naming
3. **Cull Singles** - Quality analysis → Tier A/B/C
4. **Archive Heroes** - Move best shots to organized folders
5. **Verify Integrity** - SHA256 hash checking throughout

### **Individual Workflows**

- **Bursts**: Group similar shots, pick the best frame (fast, no AI naming by default - see config)
- **Cull**: Analyze sharpness/exposure, sort by quality (Tier A/B/C)
- **Stats**: EXIF insights (cameras, focal lengths, lighting conditions)
- **Critique**: Select a photo in the browser → Press `K` - Get AI creative feedback (composition, mood, technical quality, suggestions)
  - **Saves critique JSON** alongside the photo for future reference
  - Great for learning what makes your best shots work
  - Use it to understand technical issues or get creative direction
- **Easy Archive**: Simple AI naming + keyword folder organization (no culling, just organize)

---

## 🎛️ Configuration

Configuration is stored in `~/.fixxer.conf`:

### Understanding `burst_auto_name`

The **Burst** workflow can operate in two modes:

- **Fast Mode (default)**: `burst_auto_name = false`
  - Groups bursts, picks the best frame, uses numeric naming (`burst-001`, `burst-002`)
  - **Much faster** - no AI naming overhead
  - Great for quick organization - you can run Easy Archive later for AI naming

- **AI Naming Mode**: `burst_auto_name = true`
  - Groups bursts, picks the best frame, **AND** generates descriptive AI names
  - Slower (depends on Ollama model speed)
  - Useful if you want burst folders named immediately

**Note:** The **Auto Workflow** always uses AI naming regardless of this setting (it's designed for complete end-to-end processing).

```ini
[ingest]
default_model = qwen2.5vl:3b
default_destination = ~/Pictures/Sorted

[cull]
cull_algorithm = legacy
sharpness_good = 40.0
sharpness_dud = 15.0
exposure_dud_pct = 0.20
exposure_good_pct = 0.05

[burst]
burst_algorithm = legacy
similarity_threshold = 8
burst_auto_name = false        # Set to 'true' to enable AI naming in Burst workflow (slower)

[folders]
burst_parent_folder = true
ai_session_naming = true

[behavior]
pro_mode = false
last_source_path = 
last_destination_path = 
```

---

## 🔧 Technical Architecture

### **Hash Verification Pipeline**
```
Source File
    ↓ Calculate SHA256
    ↓ Move to Destination
    ↓ Recalculate SHA256
    ↓ Compare Hashes
    ├─ MATCH → Generate .fixxer.json sidecar
    └─ MISMATCH → HALT WORKFLOW (RuntimeError)
```

### **AI Vision Integration**
- **Ollama API**: Local LLM inference (no cloud, no privacy concerns)
- **JSON-structured responses**: Deterministic parsing
- **Base64 image encoding**: Direct vision model analysis
- **Fallback chains**: Graceful degradation on timeouts

### **Quality Scoring**
- **BRISQUE** (Blind/Referenceless Image Spatial Quality Evaluator)
- **OpenCV Laplacian variance** (sharpness fallback)
- **Histogram analysis** (exposure distribution)
- **CLIP embeddings** (semantic similarity for bursts)

---

## 📂 Project Structure

```
fixxer/
├── src/
│   └── fixxer/
│       ├── __init__.py          # Package initialization
│       ├── __main__.py          # Module entry point (python -m fixxer)
│       ├── app.py               # Textual TUI application
│       ├── engine.py            # Core workflow logic + hash verification
│       ├── phrases.py           # Motivational progress phrases
│       └── themes/
│           ├── __init__.py      # Theme package marker
│           ├── pro.css          # Pro Mode styling (Phantom Redline)
│           └── warez.css        # Standard Mode styling (Warez)
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Packaging metadata (PyPI ready)
├── README.md                    # Main documentation
├── BEGINNERS_GUIDE.md           # Terminal beginner's guide
├── README_TUI.md                # TUI-specific documentation
└── .gitignore                   # Git exclusions
```

---

## 🔐 Sidecar File Format

Example `.fixxer.json`:

```json
{
  "fixxer_version": "1.0",
  "filename": "golden-hour-cityscape.jpg",
  "original_path": "/source/IMG_1234.jpg",
  "final_path": "/archive/2024-11-20_Urban/Architecture/golden-hour-cityscape.jpg",
  "sha256_source": "a1b2c3d4...",
  "verified": true,
  "timestamp": "2024-11-20T14:35:22.123456"
}
```

If corruption is detected:
```json
{
  "sha256_source": "a1b2c3d4...",
  "sha256_destination": "e5f6g7h8...",
  "verified": false,
  "corruption_detected": true
}
```

---

## 🎨 UI Modes Comparison

Press **F12** to toggle between modes at any time (except during active workflows):

| Feature | Standard Mode | Pro Mode |
|---------|---------------|----------|
| **Aesthetic** | Warez (red/white/black) | Phantom Redline (tactical black) |
| **Logo** | ASCII art + tagline | Clean typography + F12 indicator |
| **System Monitor** | Cyan sparklines | Red "redline" sparklines |
| **Progress Phrases** | "Applying physics hacks..." | "Processing active... [2m 34s]" |
| **Milestone HUD** | ❌ Hidden | ✅ Real-time stats (BURSTS, TIER A/B/C, HEROES, ARCHIVED, TIME) |
| **Button Styles** | High contrast | Minimal, subtle borders |
| **Toggle Key** | **F12** | **F12** |

---

## 🧪 Testing

Hash verification stress test (included):

```bash
# Test with 120+ mixed RAW/JPEG files
python3 test_hash_verification.py

# Expected output:
# ✅ 120 files processed
# ✅ 120 hashes verified
# ✅ 0 corruption events
# ✅ 120 sidecar files generated
```

---

## 🤝 Contributing

Contributions welcome! Areas of interest:

- Additional RAW format testing
- Alternative AI vision models
- Quality scoring algorithm improvements
- Cross-platform testing (Windows native)
- Performance optimizations

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Ollama** - Local LLM inference
- **rawpy/libraw** - RAW file processing
- **CLIP** (OpenAI) - Semantic burst detection
- **BRISQUE** - Image quality assessment
- **Textual** - Modern TUI framework

---

## 📧 Contact

Issues and feature requests: [GitHub Issues](https://github.com/BandwagonVibes/fixxer/issues)

---

**Built with precision. Secured with cryptography. Powered by AI.**

✞ **FIXXER PRO** - "CHAOS PATCHED // LOGIC INJECTED"
