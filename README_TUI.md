# FIXXER ✞ TUI (v1.0) - Professional-Grade Edition

## Terminal User Interface with Hash Verification

FIXXER now includes a full-featured TUI (Terminal User Interface) with SHA256 integrity verification for every file operation.

**"CHAOS PATCHED // LOGIC INJECTED"**

### Quick Start

```bash
# After installing with pip install -e .
fixxer

# Or run directly from source
python fixxer_tui.py
```

### Features

- **SHA256 hash verification** - Every file move cryptographically verified
- **JSON audit trail** - .fixxer.json sidecar files for integrity tracking
- **Halt-on-corruption** - Workflow stops immediately if hash mismatch detected
- **Visual file browser** - Navigate directories with mouse or keyboard
- **Real-time log panel** - Watch hash calculations and operations in real-time
- **Animated progress indicator** - Block spinner with rotating motivational phrases
- **Engine status checks** - BRISQUE and CLIP detection at startup
- **Persistent config** - Settings auto-save to `~/.photosort.conf`
- **Dual UI modes** - Toggle between Warez and Pro (Phantom Redline) with F12
- **Milestone HUD** - Real-time stats dashboard in Pro Mode (BURSTS, TIER A/B/C, TIME)
- **Tooltip hints** - Hover over buttons to see keyboard shortcuts

### Files

- `fixxer_tui.py` - Main TUI application (v1.0)
- `fixxer_warez.css` - Standard Mode theme (Warez aesthetic)
- `fixxer_pro.css` - Pro Mode theme (Phantom Redline)
- `fixxer_engine.py` - Backend engine with hash verification (v1.0)
- `phrases.py` - Rotating progress messages

### Dependencies

All dependencies are now included by default:

```bash
# One command installs everything (CLIP, BRISQUE, TUI, Engine)
pip install -e .
```

This installs the complete professional suite with no optional add-ons needed.

### System Requirements

- Python 3.8+
- Terminal with mouse support (iTerm2, Ghostty, or similar)
- Ollama running locally (for AI features)
- dcraw (for RAW file support)
- exiftool (for EXIF metadata)

### Interface Overview

```
┌─────────────────────────────────────────────────────────────┐
│ VISIONCREW LOGO                                             │
├─────────────────────────────────────────────────────────────┤
│ Source Browser          │ Status & Logs                    │
│ [File Tree]             │ [Status Bar]                     │
│                         │ [Spinner: ■ □ □]                 │
│                         │ [Log Output]                     │
├─────────────────────────────────────────────────────────────┤
│ [Auto] [Bursts] [Cull] [Stats] [Critique] [Source] [Dest]  │
└─────────────────────────────────────────────────────────────┘
```

### Button Functions

- **Auto** - Full AI-powered workflow (burst → cull → rename → organize)
- **Bursts** - Group similar images into burst folders
- **Cull** - Sort images by quality (Tier A/B/C)
- **Stats** - Show EXIF insights and session statistics
- **Critique** - AI critique of individual images
- **Set Source (1)** - Set source directory from browser selection
- **Dest (2)** - Open destination directory selector
- **Model** - Choose Ollama model

### Keyboard Shortcuts

**Navigation & Setup:**
- `1` - Set Source directory (from browser selection)
- `2` - Set Destination directory (opens selector)
- `M` - Select Ollama Model
- `F12` - Toggle Pro Mode (Warez ↔ Phantom Redline aesthetic)

**Workflows:**
- `A` - Auto Workflow (complete pipeline)
- `B` - Bursts (group similar shots)
- `C` - Cull (quality analysis into Tier A/B/C)
- `S` - Stats (EXIF insights and session analytics)
- `K` - Critique (AI creative feedback on selected image)

**System:**
- `Q` - Quit application
- `R` - Refresh config (reload ~/.photosort.conf)
- `Esc` - Stop current workflow
- `Ctrl+C` - Force quit

**Mouse:**
- Click buttons or use keyboard shortcuts
- Navigate file browser with arrow keys or mouse
- Hover over buttons to see tooltips with keyboard hints

### Engine Detection

At startup, the TUI checks for:
- ✓ dcraw - RAW file conversion
- ✓ BRISQUE engine - Image quality assessment
- ✓ CLIP engine - Semantic burst detection

Missing engines will show fallback warnings but won't prevent operation.

### Config File

Settings are saved to `~/.photosort.conf`:

```ini
[behavior]
last_source_path = /path/to/source
last_destination_path = /path/to/destination

[ingest]
default_model = qwen2.5vl:3b
```

The TUI automatically saves changes when you modify source, destination, or model settings.

---

## Version History

### FIXXER v1.0 (2025-01-20)
**"CHAOS PATCHED // LOGIC INJECTED"**
- SHA256 hash verification for all file operations
- JSON sidecar audit trail (.fixxer.json files)  
- Halt-on-mismatch corruption detection
- Complete rebrand to FIXXER ✞
- Real-time hash verification logging in TUI
- Professional-grade integrity protection

### TUI v12.1 (2025-11-16)
- Fixed mouse event leakage (imports at module load time)
- Added BRISQUE and CLIP engine detection at startup
- Added animated block spinner during workflows
- Config auto-saves when changing settings
- Left-aligned logo, red scrollbars

### Engine v10.7 (2025-11-16)
- Fixed session naming (uses destination paths after move)
- Pre-tests image encoding before selecting samples
- Added `save_app_config()` for persistent settings
- RAW conversion tries embedded thumbnail first
