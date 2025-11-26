# FIXXER ✞ TUI (v1.0) - Professional-Grade Edition

## Terminal User Interface with Hash Verification

FIXXER now includes a full-featured TUI (Terminal User Interface) with SHA256 integrity verification for every file operation.

**"CHAOS PATCHED // LOGIC INJECTED"**

### Quick Start

```bash
# Run the TUI
python photosort_tui_styled.py
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
- **Custom theme** - "Warez" aesthetic with red/white/black color scheme

### Files

- `photosort_tui_styled.py` - Main TUI application (v12.1)
- `photosort_visioncrew.css` - Theme stylesheet
- `photosort_engine.py` - Backend engine (v10.7)
- `phrases.py` - Rotating progress messages (optional)

### Dependencies

The TUI requires additional packages beyond the CLI:

```bash
pip install textual rich
```

Or install everything:

```bash
pip install -r requirements.txt
```

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

- `q` - Quit
- `1` - Set source (from browser selection)
- `2` - Set destination (opens selector)
- Arrow keys - Navigate file browser
- Mouse click - Select directories/buttons

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
