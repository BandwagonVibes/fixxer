#!/usr/bin/env python3
"""
PhotoSort TUI (v12.1) - VisionCrew Edition

- NEW (Startup): BRISQUE and CLIP engine verification checks
- NEW (Progress): Animated block spinner instead of progress bar
- FIX (Browser): File browser hides dotfiles with FilteredDirectoryTree
- FIX (Logo): Proper VISIONCREW ASCII block art
- FIX (Status): Removed confusing source/dest display from status bar
- FIX (Timers): Proper cleanup of phrase and timer threads
- NEW (Style): External CSS theming via photosort_visioncrew.css
- NEW (Progress): Rotating phrases from phrases.py during workflows
- UI: "warez" aesthetic with red/white/black color scheme
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Label, Static, DirectoryTree, Sparkline
from textual.message import Message
from textual.timer import Timer

# System monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Import phrases
try:
    from phrases import get_phrase_by_duration, get_model_loading_phrase, get_quit_message
    PHRASES_AVAILABLE = True
except ImportError:
    PHRASES_AVAILABLE = False
    def get_phrase_by_duration(elapsed_seconds: float, use_meta: bool = False) -> str:
        return "Processing..."
    def get_model_loading_phrase() -> str:
        return "Loading..."
    def get_quit_message() -> str:
        return "Goodbye!"

# Import the engine functions
try:
    from photosort_engine import (
        auto_workflow,
        simple_sort_workflow,  # NEW: Simple legacy mode workflow
        group_bursts_in_directory,
        cull_images_in_directory,
        show_exif_insights,
        load_app_config,
        save_app_config,  # NEW: Save config changes
        check_dcraw,
        SUPPORTED_EXTENSIONS  # Import to check what's supported
    )
    ENGINE_AVAILABLE = True
except ImportError as e:
    ENGINE_AVAILABLE = False
    ENGINE_IMPORT_ERROR = str(e)
    SUPPORTED_EXTENSIONS = []
    
    # Fallback for testing without the engine
    def load_app_config():
        return {
            'config_file_found': False,
            'last_source_path': str(Path.home() / 'Pictures'),
            'last_destination_path': str(Path.home() / 'Pictures/Sorted'),
            'default_model': 'qwen2.5vl:3b'
        }
    
    def auto_workflow(log_callback, app_config):
        log_callback(f"🚀 [Test Mode] Engine import failed: {ENGINE_IMPORT_ERROR}")
        import time
        time.sleep(1)
        return {}
    
    def simple_sort_workflow(log_callback, app_config):
        log_callback(f"🚀 [Test Mode] Engine import failed: {ENGINE_IMPORT_ERROR}")
        import time
        time.sleep(1)
        return {}
    
    def group_bursts_in_directory(log_callback, app_config, simulated=False):
        log_callback(f"🚀 [Test Mode] Engine import failed: {ENGINE_IMPORT_ERROR}")
        import time
        time.sleep(1)
    
    def cull_images_in_directory(log_callback, app_config, simulated=False):
        log_callback(f"🚀 [Test Mode] Engine import failed: {ENGINE_IMPORT_ERROR}")
        import time
        time.sleep(1)
    
    def show_exif_insights(log_callback, app_config, simulated=False):
        log_callback(f"🚀 [Test Mode] Engine import failed: {ENGINE_IMPORT_ERROR}")
        import time
        time.sleep(1)
    
    def check_dcraw(log_callback):
        log_callback("🚀 [Test Mode] dcraw check skipped.")
    
    def save_app_config(config):
        return False  # Can't save in test mode


# ==============================================================================
# Pre-check BRISQUE and CLIP availability (before Textual starts)
# ==============================================================================

# Check BRISQUE availability
BRISQUE_STATUS = "not_checked"
BRISQUE_ERROR = None
try:
    from imquality import brisque
    BRISQUE_STATUS = "imquality"
except ImportError as e:
    BRISQUE_ERROR = str(e)
    try:
        from image_quality import brisque
        BRISQUE_STATUS = "image_quality"
    except ImportError:
        # Check cull_engine module
        try:
            from cull_engine import BRISQUE_AVAILABLE
            if BRISQUE_AVAILABLE:
                BRISQUE_STATUS = "cull_engine"
            else:
                BRISQUE_STATUS = "fallback"
        except ImportError:
            BRISQUE_STATUS = "fallback"

# Check CLIP availability
CLIP_STATUS = "not_checked"
try:
    from burst_engine import V8_BURST_READY
    if V8_BURST_READY:
        CLIP_STATUS = "burst_engine"
    else:
        CLIP_STATUS = "fallback"
except ImportError:
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.cluster import DBSCAN
        CLIP_STATUS = "direct"
    except ImportError:
        CLIP_STATUS = "fallback"


# ==============================================================================
# Directory Selection Screen (FOR DESTINATION ONLY)
# ==============================================================================

class ModelSelectScreen(ModalScreen[Optional[str]]):
    """Modal screen for selecting an Ollama model."""
    
    CSS = """
    ModelSelectScreen {
        align: center middle;
    }
    
    #model-dialog {
        width: 60%;
        height: 60%;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }
    
    #model-list {
        height: 1fr;
        border: solid $primary 50%;
        margin: 1 0;
        background: $surface;
        padding: 1;
    }
    
    #current-model {
        height: 3;
        margin-bottom: 1;
        padding: 1;
        background: $surface;
        border: solid $primary 20%;
    }
    
    #model-button-row {
        height: auto;
        align: center middle;
        padding-top: 1;
    }
    
    #model-button-row Button {
        margin: 0 2;
    }
    """
    
    def __init__(self, current_model: str = "qwen2.5vl:3b", available_models: Optional[list] = None):
        super().__init__()
        self.current_model = current_model
        self.selected_model = current_model
        self.available_models = available_models or ["qwen2.5vl:3b", "llama3.1:8b", "llava:latest"]
    
    def compose(self) -> ComposeResult:
        with Container(id="model-dialog"):
            yield Label("[bold]Select AI Model[/bold]", id="model-title")
            yield Static(f"Current: {self.current_model}", id="current-model")
            with ScrollableContainer(id="model-list"):
                for i, model in enumerate(self.available_models):
                    # Use simple numeric IDs to avoid invalid characters
                    variant = "primary" if model == self.current_model else "default"
                    yield Button(model, id=f"model-opt-{i}", variant=variant, classes="model-option")
            with Horizontal(id="model-button-row"):
                yield Button("Select", variant="primary", id="btn-model-select")
                yield Button("Cancel", variant="default", id="btn-model-cancel")
    
    @on(Button.Pressed, ".model-option")
    def on_model_option(self, event: Button.Pressed) -> None:
        # Extract model name from button label
        self.selected_model = event.button.label.plain
        self.query_one("#current-model", Static).update(f"Selected: {self.selected_model}")
        # Update button variants
        for btn in self.query(".model-option"):
            btn.variant = "primary" if btn.label.plain == self.selected_model else "default"
    
    @on(Button.Pressed, "#btn-model-select")
    def on_select(self) -> None:
        self.dismiss(self.selected_model)
    
    @on(Button.Pressed, "#btn-model-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)


class DirectorySelectScreen(ModalScreen[Optional[Path]]):
    """Modal screen for selecting a directory."""
    
    # This modal screen will pick up the main app's CSS
    # or you can define specific CSS here if needed.
    
    CSS = """
    DirectorySelectScreen {
        align: center middle;
    }
    
    #dialog {
        width: 80%;
        height: 80%;
        border: thick $primary;
        background: $surface; /* Use var from main CSS */
        padding: 1;
    }
    
    #tree-container {
        height: 1fr;
        border: solid $primary 50%;
        margin: 1 0;
        background: $surface;
    }
    
    #path-display {
        height: 3;
        margin-bottom: 1;
        padding: 1;
        background: $surface;
        border: solid $primary 20%;
    }
    
    #button-row {
        height: auto;
        align: center middle;
        padding-top: 1;
    }
    
    #button-row Button {
        margin: 0 2;
    }
    """
    
    def __init__(self, title: str = "Select Directory", start_path: Optional[Path] = None):
        super().__init__()
        self.title_text = title
        self.start_path = start_path or Path.home()
        self.selected_path: Optional[Path] = None
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(f"[bold]{self.title_text}[/bold]", id="dialog-title")
            yield Static(f"Current: {self.start_path}", id="path-display")
            with ScrollableContainer(id="tree-container"):
                # Always start at Home for full context
                yield DirectoryTree(str(Path.home()), id="dir-tree")
            with Horizontal(id="button-row"):
                yield Button("Select", variant="primary", id="btn-select")
                yield Button("Cancel", variant="default", id="btn-cancel")
    
    def on_mount(self) -> None:
        tree = self.query_one("#dir-tree", DirectoryTree)
        tree.show_root = True
        tree.show_guides = True
        self.selected_path = self.start_path
        
        # Try to expand to the start_path
        if self.start_path and self.start_path.is_dir():
            self._expand_to_path(tree, self.start_path)
    
    def _expand_to_path(self, tree: DirectoryTree, target_path: Path) -> None:
        """Expand the tree to show the target path."""
        # This is a best-effort expansion - the tree may not be fully loaded yet
        try:
            tree.select_node(tree.root)
        except Exception:
            pass
    
    @on(DirectoryTree.NodeSelected)
    def on_directory_selected(self, event: DirectoryTree.NodeSelected) -> None:
        if event.node.data and hasattr(event.node.data, 'path'):
            path = event.node.data.path
            if path.is_dir():
                self.selected_path = path
                self.query_one("#path-display", Static).update(f"Selected: {path}")
    
    @on(Button.Pressed, "#btn-select")
    def on_select(self) -> None:
        # Get the currently selected path from the tree
        try:
            tree = self.query_one("#dir-tree", DirectoryTree)
            if tree.cursor_node and tree.cursor_node.data and hasattr(tree.cursor_node.data, 'path'):
                selected = tree.cursor_node.data.path
                if selected.is_dir():
                    self.selected_path = selected
        except Exception:
            pass
        
        # Dismiss with the selected path
        self.dismiss(self.selected_path)
    
    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)


# ==============================================================================
# Widget Components
# ==============================================================================

class SystemMonitor(Container):
    """Real-time system resource monitor with sparkline graphs - RAM & CPU only."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ram_data = [0.0] * 50  # 50 points for sparkline (100 seconds of history)
        self.cpu_data = [0.0] * 50
        self.update_timer: Optional[Timer] = None
    
    def compose(self) -> ComposeResult:
        if not PSUTIL_AVAILABLE:
            yield Static("[dim]System monitoring unavailable (psutil not installed)[/dim]", id="sysmon-error")
            return
        
        with Horizontal(id="sysmon-row-1"):
            yield Static("RAM:", classes="sysmon-label")
            yield Sparkline(self.ram_data, id="ram-sparkline", classes="sysmon-sparkline")
            yield Static("0%", id="ram-value", classes="sysmon-value")
        
        with Horizontal(id="sysmon-row-2"):
            yield Static("CPU:", classes="sysmon-label")
            yield Sparkline(self.cpu_data, id="cpu-sparkline", classes="sysmon-sparkline")
            yield Static("0%", id="cpu-value", classes="sysmon-value")
    
    def on_mount(self) -> None:
        """Start the monitoring timer when mounted."""
        if PSUTIL_AVAILABLE:
            self.update_timer = self.set_interval(2.0, self.update_stats)
            # Force initial update after a brief delay
            self.set_timer(0.5, self.update_stats)
    
    def on_unmount(self) -> None:
        """Stop the monitoring timer when unmounted."""
        if self.update_timer:
            self.update_timer.stop()
    
    def update_stats(self) -> None:
        """Update system statistics and sparklines."""
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Get RAM usage
            ram = psutil.virtual_memory()
            ram_percent = ram.percent
            
            # Update data arrays (FIFO)
            self.cpu_data.append(cpu_percent)
            self.cpu_data.pop(0)
            self.ram_data.append(ram_percent)
            self.ram_data.pop(0)
            
            # Update RAM sparkline and value
            try:
                ram_sparkline = self.query_one("#ram-sparkline", Sparkline)
                # Create new list to ensure Textual detects the change
                ram_sparkline.data = list(self.ram_data)
                # Force refresh
                ram_sparkline.refresh()
                
                ram_value = self.query_one("#ram-value", Static)
                ram_color = "red" if ram_percent > 85 else "white"
                ram_value.update(f"[{ram_color}]{ram_percent:.0f}%[/{ram_color}]")
            except Exception:
                pass
            
            # Update CPU sparkline and value
            try:
                cpu_sparkline = self.query_one("#cpu-sparkline", Sparkline)
                # Create new list to ensure Textual detects the change
                cpu_sparkline.data = list(self.cpu_data)
                # Force refresh
                cpu_sparkline.refresh()
                
                cpu_value = self.query_one("#cpu-value", Static)
                cpu_color = "red" if cpu_percent > 80 else "white"
                cpu_value.update(f"[{cpu_color}]{cpu_percent:.0f}%[/{cpu_color}]")
            except Exception:
                pass
                
        except Exception:
            # Silently fail - don't disrupt the app
            pass


class LogPanel(Container):
    """A widget to display scrollable logs with rich formatting."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logs = []
        self.max_logs = 1000
        self.lock = threading.Lock()
    
    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static(id="log-content"),
            id="log-container"
        )
    
    def add_log(self, message: str) -> None:
        """Add a log message with timestamp. Thread-safe."""
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.logs.append(f"[dim]{timestamp}[/dim] {message}")
            
            if len(self.logs) > self.max_logs:
                self.logs.pop(0)
        
        self._schedule_display_update()
    
    def _schedule_display_update(self) -> None:
        try:
            self.app.post_message(self.UpdateLogDisplay())
        except Exception:
            pass 
    
    class UpdateLogDisplay(Message):
        """Message to signal a log update."""
        pass
    
    def update_display_from_app(self) -> None:
        """The actual UI update, called by the app thread."""
        try:
            log_content = self.query_one("#log-content", Static)
            with self.lock:
                log_text = "\n".join(self.logs)
            
            log_content.update(log_text)
            container = self.query_one("#log-container", ScrollableContainer)
            container.scroll_end(animate=False)
        except Exception:
            pass


class FilteredDirectoryTree(DirectoryTree):
    """A DirectoryTree that filters out hidden files and directories."""
    
    def filter_paths(self, paths: list[Path]) -> list[Path]:
        """Filter out hidden files/directories (starting with a dot)."""
        return [
            path
            for path in paths
            if not path.name.startswith(".")
        ]


# ==============================================================================
# Main Application
# ==============================================================================

class PhotoSortTUI(App):
    """The main TUI application for PhotoSort."""
    
    # Load the external CSS file instead of using the inline CSS variable
    CSS_PATH = "photosort_visioncrew.css"
    
    # Add a border title to the main app screen
    BORDER_TITLE = "V.C.S. INTERFACE"
    
    BINDINGS = [
        Binding("q", "quit", "Quit (q)", show=False),
        Binding("r", "refresh_config", "Refresh (r)", show=False),
        Binding("1", "set_source", "Source (1)", show=False),
        Binding("2", "set_dest", "Dest (2)", show=False),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]
    
    # Block spinner frames - square block animation
    BLOCK_SPINNER_FRAMES = [
        "■ □ □",
        "□ ■ □", 
        "□ □ ■",
        "□ ■ □",
    ]
    
    class UpdateStatusBar(Message):
        """Message to signal a status bar update."""
        pass
    
    class UpdateSpinner(Message):
        """Message to signal spinner frame update."""
        pass
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app_config = load_app_config()
        self.current_thread: Optional[threading.Thread] = None
        self.workflow_active = False
        
        self.status_lock = threading.Lock()
        self.current_status = "Ready"
        self.current_stats = {}
        
        # Progress tracking (with spinner instead of bar)
        self.workflow_start_time: Optional[float] = None
        self.phrase_timer: Optional[Timer] = None
        self.timer_update_timer: Optional[Timer] = None
        self.spinner_timer: Optional[Timer] = None
        self.spinner_frame_index = 0
        
        self.log_panel: Optional[LogPanel] = None
        self.file_browser: Optional[DirectoryTree] = None
        self.status_bar: Optional[Static] = None
        self.spinner_display: Optional[Static] = None
        self.progress_phrase: Optional[Static] = None
        self.progress_timer_display: Optional[Static] = None
    
    def get_vision_crew_logo(self) -> str:
        """UI: Returns the VISIONCREW ASCII logo with scanlines and red CREW."""
        # Logo matching the uploaded image style - VISION in white, CREW in red
        # With scanline effect underneath
        logo = """[bold white]██    ██ ██ ███████ ██  ██████  ███    ██ [/bold white][bold red]  ██████ ██████  ███████ ██    ██ [/bold red]
[bold white]██    ██ ██ ██      ██ ██    ██ ████   ██ [/bold white][bold red] ██      ██   ██ ██      ██    ██ [/bold red]
[bold white]██    ██ ██ ███████ ██ ██    ██ ██ ██  ██ [/bold white][bold red] ██      ██████  █████   ██ █  ██ [/bold red]
[bold white] ██  ██  ██      ██ ██ ██    ██ ██  ██ ██ [/bold white][bold red] ██      ██   ██ ██      ████  ██ [/bold red]
[bold white]  ████   ██ ███████ ██  ██████  ██   ████ [/bold white][bold red]  ██████ ██   ██ ███████ ██ ██ ██ [/bold red]

[dim white]▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀[/dim white]
[dim white]▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄[/dim white]

[white]cracked by vision crew[/white]
[bold red]SYSTEM OVERRIDE INITIATED | ACCESS GRANTED[/bold red]"""
        return logo

    def compose(self) -> ComposeResult:
        # No Header
        # The app title is now part of the logo/header area
        # NEW: Add horizontal container for logo + Easy Archive button
        with Horizontal(id="header-row"):
            yield Static(self.get_vision_crew_logo(), id="logo")
            yield Button("Easy Archive", id="btn-easy", variant="default", classes="easy-btn")
        
        with Horizontal(id="main-layout"):
            with Vertical(id="left-panel"):
                yield Static("[bold]Source Browser[/bold]", classes="panel-title")
                with ScrollableContainer(id="file-browser-container"):
                    # FIX: Always start at Home for full navigation context
                    # USE FilteredDirectoryTree to hide dotfiles
                    self.file_browser = FilteredDirectoryTree(
                        str(Path.home()),
                        id="file-browser"
                    )
                    yield self.file_browser
            
            with Vertical(id="right-panel"):
                yield Static("[bold]Status & Logs[/bold]", classes="panel-title")
                
                # System Monitor - GPU, RAM, CPU sparklines
                self.system_monitor = SystemMonitor(id="system-monitor")
                yield self.system_monitor
                
                self.status_bar = Static(id="status-bar")
                yield self.status_bar
                
                # Progress spinner with rotating phrases (replaces progress bar)
                with Container(id="progress-container"):
                    self.spinner_display = Static("", id="spinner-display")
                    yield self.spinner_display
                    with Horizontal():
                        self.progress_phrase = Static("Ready to process", id="progress-phrase")
                        yield self.progress_phrase
                        self.progress_timer_display = Static("", id="progress-timer")
                        yield self.progress_timer_display
                
                self.log_panel = LogPanel(id="log-panel")
                yield self.log_panel
        
        with Horizontal(id="button-bar"):
            # Updated button text (removed emojis)
            yield Button("Auto", id="btn-auto", variant="primary", classes="workflow-btn")
            yield Button("Bursts", id="btn-burst", variant="default", classes="workflow-btn")
            yield Button("Cull", id="btn-cull", variant="default", classes="workflow-btn")
            yield Button("Stats", id="btn-stats", variant="default", classes="workflow-btn")
            yield Button("Critique", id="btn-critique", variant="default", classes="workflow-btn")
            yield Button("Set Source (1)", id="btn-source", variant="warning", classes="path-btn")
            yield Button("Dest (2)", id="btn-dest", variant="warning", classes="path-btn")
            yield Button("Model", id="btn-model", variant="default", classes="path-btn")
            # Updated Quit button text
            yield Button("LOGOUT (q)", id="btn-quit", variant="error", classes="path-btn")
        # No Footer
    
    def on_mount(self) -> None:
        self.write_to_log("[bold red]VisionCrew PhotoSort v12.1[/bold red] - System Online")
        self.write_to_log("[dim]────────────────────────────────────────────[/dim]")
        
        if not ENGINE_AVAILABLE:
            self.write_to_log(f"[bold red]✗ FATAL: photosort_engine.py not found.[/bold red]")
            self.write_to_log(f"[dim]   Error: {ENGINE_IMPORT_ERROR}[/dim]")
            self.toggle_workflow_buttons(disabled=True, force=True)
            return
        
        # Log supported extensions for debugging
        if SUPPORTED_EXTENSIONS:
            raw_exts = [ext for ext in SUPPORTED_EXTENSIONS if ext.upper() in ['.RW2', '.ARW', '.CR2', '.CR3', '.NEF', '.DNG', '.RAF', '.ORF', '.PEF', '.SRW']]
            self.write_to_log(f"✓ Supported extensions: {len(SUPPORTED_EXTENSIONS)} types")
            if raw_exts:
                self.write_to_log(f"  Added RAW formats: {', '.join(sorted(set([e.lower() for e in raw_exts])))}")
        
        try:
            check_dcraw(self.write_to_log)
        except Exception as e:
            self.write_to_log(f"[red]Error during dcraw check: {e}[/red]")
        
        # NEW: Check BRISQUE engine availability (using pre-checked flags)
        self._check_brisque_engine()
        
        # NEW: Check CLIP engine availability (using pre-checked flags)
        self._check_clip_engine()

        if self.app_config.get('config_file_found'):
            self.write_to_log(f"✓ Config loaded from ~/.photosort.conf")
        else:
            self.write_to_log("[yellow]No config file found, using defaults[/yellow]")
        
        self._update_status_bar_display()
        
        # FIX: Don't change browser root - just log what we have configured
        source_path = self.app_config.get('last_source_path')
        if source_path and Path(source_path).is_dir():
            self.write_to_log(f"✓ Last source path: {source_path}")
            # Scan the source path to show what's there
            self._scan_source_directory(source_path)
        else:
            self.write_to_log(f"✓ Source browser started at Home (~/).")
            
        if not self.app_config.get('last_destination_path'):
            self.write_to_log("[red]⚠️  Destination path not set. Click 'Dest (2)' to configure.[/red]")
        
        self.write_to_log("")
        self.write_to_log("[dim]Navigate to a folder in the browser, then press 'Set Source (1)' to begin.[/dim]")
    
    def _scan_source_directory(self, path: str) -> None:
        """Scan the source directory and log what files are found."""
        try:
            p = Path(path)
            if not p.is_dir():
                return
            
            # Count files by type
            all_files = list(p.glob("*"))
            image_files = []
            raw_files = []
            
            for f in all_files:
                if f.is_file():
                    ext = f.suffix.lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp']:
                        image_files.append(f)
                    elif ext in ['.rw2', '.arw', '.cr2', '.cr3', '.nef', '.dng', '.raf', '.orf', '.pef', '.srw']:
                        raw_files.append(f)
            
            if raw_files:
                self.write_to_log(f"  Found {len(raw_files)} RAW files ({raw_files[0].suffix})")
            if image_files:
                self.write_to_log(f"  Found {len(image_files)} standard image files")
            if not raw_files and not image_files:
                self.write_to_log(f"  [yellow]No image files found in {p.name}[/yellow]")
                
        except Exception as e:
            self.write_to_log(f"[dim]Could not scan directory: {e}[/dim]")
    
    def _check_brisque_engine(self) -> None:
        """Check if BRISQUE quality assessment is available (using pre-checked flags)."""
        if BRISQUE_STATUS == "imquality":
            self.write_to_log("[green]✓ BRISQUE engine:[/green] imquality.brisque detected")
        elif BRISQUE_STATUS == "image_quality":
            self.write_to_log("[green]✓ BRISQUE engine:[/green] image_quality.brisque detected")
        elif BRISQUE_STATUS == "cull_engine":
            self.write_to_log("[green]✓ BRISQUE engine:[/green] cull_engine BRISQUE available")
        else:
            self.write_to_log("[yellow]⚠️  BRISQUE engine:[/yellow] Using OpenCV Laplacian fallback")
            if BRISQUE_ERROR:
                self.write_to_log(f"   [dim]BRISQUE error: {BRISQUE_ERROR}[/dim]")
    
    def _check_clip_engine(self) -> None:
        """Check if CLIP semantic burst detection is available (using pre-checked flags)."""
        if CLIP_STATUS == "burst_engine":
            self.write_to_log("[green]✓ CLIP engine:[/green] sentence-transformers + DBSCAN clustering")
        elif CLIP_STATUS == "direct":
            self.write_to_log("[green]✓ CLIP engine:[/green] sentence-transformers + sklearn detected")
        else:
            self.write_to_log("[yellow]⚠️  CLIP engine:[/yellow] Using imagehash pHash fallback")
            self.write_to_log("   [dim]Install: pip install sentence-transformers scikit-learn[/dim]")
    
    # --- Thread-Safe UI Update Handlers ---
    
    @on(LogPanel.UpdateLogDisplay)
    def on_update_log_display(self, event: LogPanel.UpdateLogDisplay) -> None:
        if self.log_panel:
            self.log_panel.update_display_from_app()
    
    @on(UpdateStatusBar)
    def on_update_status_bar(self, event: UpdateStatusBar) -> None:
        self._update_status_bar_display()
    
    # --- Core UI Methods ---
    
    def write_to_log(self, message: str) -> None:
        if self.log_panel:
            self.log_panel.add_log(message)
    
    def update_progress_from_thread(self, current: int, total: Optional[int] = None) -> None:
        """Thread-safe progress update."""
        try:
            self.call_from_thread(self.update_progress, current, total)
        except Exception:
            pass
    
    def update_status(self, status: str, stats: Optional[Dict] = None) -> None:
        with self.status_lock:
            self.current_status = status
            if stats is not None:
                self.current_stats = stats
        
        try:
            self.post_message(self.UpdateStatusBar())
        except Exception:
            pass 
    
    def _update_status_bar_display(self) -> None:
        if not self.status_bar:
            return
            
        with self.status_lock:
            status = self.current_status
            stats = self.current_stats.copy()

        table = Table(show_header=False, box=None, padding=0, expand=True)
        table.add_column("Key", style="cyan", no_wrap=True, width=12)
        table.add_column("Value", style="white", overflow="fold")
        
        # Updated status colors
        status_color = "#00FFFF" # Bright Cyan (from CSS var $status-ok)
        if status == "Ready": status_color = "#00FFFF" # Bright Cyan
        elif "Running" in status or "..." in status: status_color = "yellow"
        elif "Error" in status or "Failed" in status or "Complete" in status: 
            if "Complete" in status:
                status_color = "#00FF00"  # Green for complete
            else:
                status_color = "#FF0000" # Bright Red for errors
        
        table.add_row("Status:", f"[bold {status_color}]{status}[/bold {status_color}]")
        
        # Only show additional stats if provided (from workflow results)
        if stats:
            for key, value in stats.items():
                table.add_row(f"{key}:", str(value))
        
        self.status_bar.update(table)
    
    def start_progress_tracking(self) -> None:
        """Start the spinner animation and phrase rotation."""
        self.workflow_start_time = time.time()
        self.spinner_frame_index = 0
        
        # Start spinner animation (fast - every 200ms)
        self.spinner_timer = self.set_interval(0.2, self._trigger_spinner_update)
        self._advance_spinner_frame()  # Show first frame immediately
        
        # Start phrase rotation timer (every 8 seconds)
        self.phrase_timer = self.set_interval(8, self._rotate_phrase)
        self._rotate_phrase()  # Show first phrase immediately
        self._update_timer_display()
        
        # Start timer update (every second) and track it
        self.timer_update_timer = self.set_interval(1, self._update_timer_display)
    
    def _trigger_spinner_update(self) -> None:
        """Trigger a spinner update via message."""
        try:
            self.post_message(self.UpdateSpinner())
        except Exception:
            pass
    
    def _advance_spinner_frame(self) -> None:
        """Advance to the next spinner frame."""
        if not self.spinner_display:
            return
        
        # Use block spinner for that cool retro look
        frame = self.BLOCK_SPINNER_FRAMES[self.spinner_frame_index % len(self.BLOCK_SPINNER_FRAMES)]
        self.spinner_display.update(f"[bold red]{frame}[/bold red]")
        self.spinner_frame_index += 1
    
    @on(UpdateSpinner)
    def on_update_spinner(self, event: UpdateSpinner) -> None:
        self._advance_spinner_frame()
    
    def _rotate_phrase(self) -> None:
        """Rotate to a new phrase based on elapsed time."""
        if not self.progress_phrase:
            return
        
        # Only rotate if workflow is active
        if self.workflow_start_time:
            elapsed = time.time() - self.workflow_start_time
            phrase = get_phrase_by_duration(elapsed, use_meta=True)
        else:
            phrase = "Ready to process"
        
        # Force refresh the widget
        self.progress_phrase.update(phrase)
        self.progress_phrase.refresh()
    
    def _update_timer_display(self) -> None:
        """Update the elapsed time display."""
        if not self.progress_timer_display or not self.workflow_start_time:
            return
        
        elapsed = time.time() - self.workflow_start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        
        if minutes > 0:
            time_str = f"[{minutes}m {seconds:02d}s]"
        else:
            time_str = f"[{seconds}s]"
        
        self.progress_timer_display.update(time_str)
    
    def stop_progress_tracking(self) -> None:
        """Stop the spinner and show completion."""
        # Stop all timers
        if self.spinner_timer:
            self.spinner_timer.stop()
            self.spinner_timer = None
        if self.phrase_timer:
            self.phrase_timer.stop()
            self.phrase_timer = None
        if self.timer_update_timer:
            self.timer_update_timer.stop()
            self.timer_update_timer = None
        
        if self.workflow_start_time:
            elapsed = time.time() - self.workflow_start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            
            if minutes > 0:
                time_str = f"{minutes}m {seconds:02d}s"
            else:
                time_str = f"{seconds}s"
            
            if self.spinner_display:
                self.spinner_display.update("[bold green]✓[/bold green]")
            if self.progress_phrase:
                self.progress_phrase.update(f"✅ Completed in {time_str}")
            if self.progress_timer_display:
                self.progress_timer_display.update("")
        
        self.workflow_start_time = None
    
    def reset_progress(self) -> None:
        """Reset spinner to ready state."""
        if self.spinner_display:
            self.spinner_display.update("")
        if self.progress_phrase:
            self.progress_phrase.update("Ready to process")
        if self.progress_timer_display:
            self.progress_timer_display.update("")
    
    def refresh_config_display(self) -> None:
        """Updates the status bar and reloads the file browser."""
        # FIX: Don't change browser root, just reload current view
        if self.file_browser:
            try:
                self.file_browser.reload()
            except Exception:
                pass
        
        self._update_status_bar_display()
    
    # --- Path Selection ---
    
    @on(Button.Pressed, "#btn-source")
    def on_source_button(self) -> None:
        self.action_set_source()
    
    @on(Button.Pressed, "#btn-dest")
    def on_dest_button(self) -> None:
        self.action_set_dest()
        
    @on(Button.Pressed, "#btn-model")
    def on_model_button(self) -> None:
        self.action_select_model()

    @on(Button.Pressed, "#btn-quit")
    def on_quit_button(self) -> None:
        self.action_quit()

    def action_set_source(self) -> None:
        """Set source from the currently selected directory in the browser."""
        if not self.file_browser:
            return
            
        try:
            # Get the currently highlighted path
            selected_node = self.file_browser.cursor_node
            if selected_node and selected_node.data:
                # DirEntry object - access path directly
                path = selected_node.data.path
                if not path.is_dir():
                    self.write_to_log("[red]Selected item is not a directory.[/red]")
                    return
            else:
                self.write_to_log("[red]No directory selected in browser.[/red]")
                return

            self.app_config['last_source_path'] = str(path)
            self.write_to_log(f"✓ Source set to: {path}")
            
            # Scan to show what files are in the new source
            self._scan_source_directory(str(path))
            
            self.refresh_config_display()
            
            # Save to config file
            if ENGINE_AVAILABLE and save_app_config(self.app_config):
                self.write_to_log(f"   [dim]Config saved to ~/.photosort.conf[/dim]")
            
        except Exception as e:
            self.write_to_log(f"[red]Error setting source path: {e}[/red]")
    
    def action_set_dest(self) -> None:
        """Uses modal popup for destination selection."""
        current = self.app_config.get('last_destination_path')
        start = Path(current) if current and Path(current).is_dir() else Path.home()
        
        def handle_result(path: Optional[Path]) -> None:
            if path:
                self.app_config['last_destination_path'] = str(path)
                self.write_to_log(f"✓ Destination set to: {path}")
                self.refresh_config_display()
                # Save to config file
                if ENGINE_AVAILABLE and save_app_config(self.app_config):
                    self.write_to_log(f"   [dim]Config saved to ~/.photosort.conf[/dim]")
        
        self.push_screen(DirectorySelectScreen("Select Destination Directory", start), handle_result)
    
    def action_select_model(self) -> None:
        """Open model selection dialog."""
        current = self.app_config.get('default_model', 'qwen2.5vl:3b')
        
        # Try to get available models from Ollama
        available = None
        if ENGINE_AVAILABLE:
            try:
                from photosort_engine import get_available_models
                models = get_available_models(self.write_to_log)
                if models:
                    available = models
            except Exception:
                pass
        
        # Default list if we can't query Ollama
        if not available:
            available = ["qwen2.5vl:3b", "llama3.1:8b", "llava:latest", "bakllava:latest"]
        
        def handle_result(model: Optional[str]) -> None:
            if model:
                self.app_config['default_model'] = model
                self.write_to_log(f"✓ Model set to: {model}")
                # Save to config file
                if ENGINE_AVAILABLE and save_app_config(self.app_config):
                    self.write_to_log(f"   [dim]Config saved to ~/.photosort.conf[/dim]")
        
        self.push_screen(ModelSelectScreen(current, available), handle_result)
    
    # --- Workflow Handling ---
    
    @on(Button.Pressed, ".workflow-btn")
    def handle_workflow_button(self, event: Button.Pressed) -> None:
        if self.workflow_active:
            self.write_to_log("[red]A workflow is already running![/red]")
            return
            
        if not self.check_paths_configured():
            return
            
        self.toggle_workflow_buttons(disabled=True)
        
        if event.button.id == "btn-auto":
            self.write_to_log("=" * 50)
            self.write_to_log("[bold cyan]Starting AUTO WORKFLOW[/bold cyan]")
            self.start_progress_tracking()
            self.run_in_thread(self.run_auto_workflow_thread, "AutoWorkflow")
        
        elif event.button.id == "btn-burst":
            self.write_to_log("=" * 50)
            self.write_to_log("[bold blue]Starting BURST GROUPING[/bold blue]")
            self.start_progress_tracking()
            self.run_in_thread(self.run_burst_workflow_thread, "BurstWorkflow")
        
        elif event.button.id == "btn-cull":
            self.write_to_log("=" * 50)
            self.write_to_log("[bold yellow]Starting CULL WORKFLOW[/bold yellow]")
            self.start_progress_tracking()
            self.run_in_thread(self.run_cull_workflow_thread, "CullWorkflow")
        
        elif event.button.id == "btn-stats":
            self.write_to_log("=" * 50)
            self.write_to_log("[bold magenta]Starting STATS ANALYSIS[/bold magenta]")
            self.start_progress_tracking()
            self.run_in_thread(self.run_stats_workflow_thread, "StatsWorkflow")
        
        elif event.button.id == "btn-critique":
            self.write_to_log("=" * 50)
            self.write_to_log("[bold cyan]Starting AI CRITIQUE[/bold cyan]")
            self.start_progress_tracking()
            self.run_in_thread(self.run_critique_workflow_thread, "CritiqueWorkflow")
    
    @on(Button.Pressed, "#btn-easy")
    def handle_easy_button(self, event: Button.Pressed) -> None:
        """Handle Easy Archive button - Simple sort workflow (legacy mode)"""
        if self.workflow_active:
            self.write_to_log("[red]A workflow is already running![/red]")
            return
            
        if not self.check_paths_configured():
            return
            
        self.toggle_workflow_buttons(disabled=True)
        self.write_to_log("=" * 50)
        self.write_to_log("[bold green]Starting EASY ARCHIVE[/bold green]")
        self.write_to_log("[dim]Simple AI naming + keyword folder organization[/dim]")
        self.start_progress_tracking()
        self.run_in_thread(self.run_easy_workflow_thread, "EasyWorkflow")
    
    def check_paths_configured(self) -> bool:
        if not self.app_config.get('last_source_path') or not Path(self.app_config['last_source_path']).is_dir():
            self.write_to_log("[red]✗ Source path not set or invalid. Use 'Set Source (1)' button first.[/red]")
            return False
        if not self.app_config.get('last_destination_path'):
            self.write_to_log("[red]✗ Destination path not set. Use 'Dest (2)' button first.[/red]")
            return False
        return True
    
    def toggle_workflow_buttons(self, disabled: bool, force: bool = False) -> None:
        """
        Disable or enable all buttons.
        If force=True, disable all buttons including quit (used on fatal error).
        """
        self.workflow_active = disabled
        for btn in self.query("Button"):
            if force:
                btn.disabled = True
            elif btn.id != "btn-quit":
                btn.disabled = disabled
    
    def on_workflow_complete(self) -> None:
        self.stop_progress_tracking()
        self.toggle_workflow_buttons(disabled=False)
        self.refresh_config_display() # Refresh directory tree on complete
    
    def run_in_thread(self, target, name: str) -> None:
        self.current_thread = threading.Thread(target=target, name=name, daemon=True)
        self.current_thread.start()
    
    # --- Workflow Thread Targets ---
    
    def run_auto_workflow_thread(self) -> None:
        try:
            self.update_status("🚀 Running Auto...", {})
            result = auto_workflow(
                log_callback=self.write_to_log,
                app_config=self.app_config
            )
            self.write_to_log("[bold green]✓ Auto workflow completed![/bold green]")
            self.update_status("✅ Auto Complete", result if isinstance(result, dict) else {})
        except Exception as e:
            self.write_to_log(f"[bold red]✗ Auto workflow failed: {e}[/bold red]")
            self.update_status("❌ Error", {})
        finally:
            self.call_from_thread(self.on_workflow_complete)
    
    def run_burst_workflow_thread(self) -> None:
        try:
            self.update_status("📦 Grouping Bursts...", {})
            group_bursts_in_directory(
                log_callback=self.write_to_log,
                app_config=self.app_config,
                simulated=False
            )
            self.write_to_log("[bold green]✓ Burst grouping completed![/bold green]")
            self.update_status("✅ Bursts Complete", {})
        except Exception as e:
            self.write_to_log(f"[bold red]✗ Burst grouping failed: {e}[/bold red]")
            self.update_status("❌ Error", {})
        finally:
            self.call_from_thread(self.on_workflow_complete)
    
    def run_cull_workflow_thread(self) -> None:
        try:
            self.update_status("✂️ Culling Images...", {})
            cull_images_in_directory(
                log_callback=self.write_to_log,
                app_config=self.app_config,
                simulated=False
            )
            self.write_to_log("[bold green]✓ Culling completed![/bold green]")
            self.update_status("✅ Cull Complete", {})
        except Exception as e:
            self.write_to_log(f"[bold red]✗ Culling failed: {e}[/bold red]")
            self.update_status("❌ Error", {})
        finally:
            self.call_from_thread(self.on_workflow_complete)
    
    def run_stats_workflow_thread(self) -> None:
        try:
            self.update_status("📊 Analyzing Stats...", {})
            show_exif_insights(
                log_callback=self.write_to_log,
                app_config=self.app_config,
                simulated=False
            )
            self.write_to_log("[bold green]✓ Stats analysis completed![/bold green]")
            self.update_status("✅ Stats Complete", {})
        except Exception as e:
            self.write_to_log(f"[bold red]✗ Stats analysis failed: {e}[/bold red]")
            self.update_status("❌ Error", {})
        finally:
            self.call_from_thread(self.on_workflow_complete)
    
    def run_critique_workflow_thread(self) -> None:
        try:
            self.update_status("🎨 Running AI Critique...", {})
            # Check if critique function exists in engine
            try:
                from photosort_engine import critique_single_image
                import json
                
                # Get first image from source directory for critique
                source_path = self.app_config.get('last_source_path')
                if not source_path or not Path(source_path).is_dir():
                    self.write_to_log("[red]✗ No source directory set.[/red]")
                    return
                
                # Find first image file
                p = Path(source_path)
                image_file = None
                for f in p.iterdir():
                    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                        image_file = f
                        break
                
                if not image_file:
                    self.write_to_log("[red]✗ No images found in source directory.[/red]")
                    return
                
                self.write_to_log(f"   Critiquing: {image_file.name}")
                model = self.app_config.get('critique_model', self.app_config.get('default_model', 'qwen2.5vl:3b'))
                
                result = critique_single_image(image_file, model, self.write_to_log)
                if result:
                    self.write_to_log("\n[bold]📝 AI Critique Results:[/bold]")
                    for key, value in result.items():
                        self.write_to_log(f"   [cyan]{key}:[/cyan] {value}")
                    
                    # Save JSON file alongside the image
                    json_path = image_file.with_suffix('.json')
                    try:
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(result, f, indent=2, ensure_ascii=False)
                        self.write_to_log(f"   [dim]Saved critique to: {json_path.name}[/dim]")
                    except Exception as e:
                        self.write_to_log(f"[yellow]Warning: Could not save JSON: {e}[/yellow]")
                
                self.write_to_log("[bold green]✓ Critique completed![/bold green]")
                self.update_status("✅ Critique Complete", {})
            except ImportError:
                self.write_to_log("[yellow]Critique function not available in engine.[/yellow]")
                self.write_to_log("[dim]Add critique_single_image() to photosort_engine.py[/dim]")
                self.update_status("⚠️ Not Available", {})
        except Exception as e:
            self.write_to_log(f"[bold red]✗ Critique failed: {e}[/bold red]")
            self.update_status("❌ Error", {})
        finally:
            self.call_from_thread(self.on_workflow_complete)
    
    def run_easy_workflow_thread(self) -> None:
        """Run the simple sort workflow (legacy mode)"""
        try:
            self.update_status("🗂️ Easy Archive Running...", {})
            result = simple_sort_workflow(
                log_callback=self.write_to_log,
                app_config=self.app_config
            )
            self.write_to_log("[bold green]✓ Easy Archive complete![/bold green]")
            self.update_status("✅ Archive Complete", result if isinstance(result, dict) else {})
        except Exception as e:
            self.write_to_log(f"[bold red]✗ Easy Archive failed: {e}[/bold red]")
            self.update_status("❌ Error", {})
        finally:
            self.call_from_thread(self.on_workflow_complete)
    
    def run_refresh_config_thread(self) -> None:
        try:
            self.update_status("🔄 Refreshing Config...", {})
            self.app_config = load_app_config()
            self.write_to_log("✓ Configuration refreshed from disk")
            self.update_status("Ready", {"Config": "Refreshed"})
            self.call_from_thread(self.refresh_config_display)
        except Exception as e:
            self.write_to_log(f"[red]Error refreshing config: {e}[/red]")
            self.update_status("❌ Config Error", {})
        finally:
            self.call_from_thread(self.on_workflow_complete)
    
    def action_refresh_config(self) -> None:
        if self.workflow_active:
            self.write_to_log("[red]A workflow is already running![/red]")
            return
            
        self.toggle_workflow_buttons(disabled=True)
        self.run_in_thread(self.run_refresh_config_thread, "RefreshConfig")


def main():
    app = PhotoSortTUI()
    app.run()


if __name__ == "__main__":
    main()