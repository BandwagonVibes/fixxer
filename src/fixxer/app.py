#!/usr/bin/env python3
"""
FIXXER ✞ TUI (v1.0) - Professional-Grade Edition

- NEW (v1.0): Hash verification with SHA256 integrity checking
- NEW (v1.0): JSON sidecar files for audit trail
- NEW (v1.0): FIXXER ✞ branding - "CHAOS PATCHED // LOGIC INJECTED"
- CORE: BRISQUE and CLIP engine verification checks
- UI: Animated block spinner with rotating motivational phrases
- STYLE: External CSS theming via fixxer_warez.css
- AESTHETIC: Warez-inspired red/white/black color scheme
"""

from __future__ import annotations

import importlib.resources
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
    from .phrases import get_phrase_by_duration, get_model_loading_phrase, get_quit_message
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
    from .engine import (
        auto_workflow,
        simple_sort_workflow,  # NEW: Simple legacy mode workflow
        group_bursts_in_directory,
        cull_images_in_directory,
        show_exif_insights,
        load_app_config,
        save_app_config,  # NEW: Save config changes
        check_rawpy,  # v10.0: Python-native RAW support (replaces check_dcraw)
        check_ollama_connection,  # v1.0.0: Llama connection check with dad joke
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
    
    def auto_workflow(log_callback, app_config, tracker=None, stop_event=None):
        log_callback(f"🚀 [Test Mode] Engine import failed: {ENGINE_IMPORT_ERROR}")
        import time
        time.sleep(1)
        return {}
    
    def simple_sort_workflow(log_callback, app_config, stop_event=None):
        log_callback(f"🚀 [Test Mode] Engine import failed: {ENGINE_IMPORT_ERROR}")
        import time
        time.sleep(1)
        return {}
    
    def group_bursts_in_directory(log_callback, app_config, simulated=False, tracker=None, directory_override=None, stop_event=None):
        log_callback(f"🚀 [Test Mode] Engine import failed: {ENGINE_IMPORT_ERROR}")
        import time
        time.sleep(1)
    
    def cull_images_in_directory(log_callback, app_config, simulated=False, tracker=None, directory_override=None, stop_event=None):
        log_callback(f"🚀 [Test Mode] Engine import failed: {ENGINE_IMPORT_ERROR}")
        import time
        time.sleep(1)
    
    def show_exif_insights(log_callback, app_config, simulated=False, directory_override=None, stop_event=None):
        log_callback(f"🚀 [Test Mode] Engine import failed: {ENGINE_IMPORT_ERROR}")
        import time
        time.sleep(1)
    
    def check_rawpy(log_callback):
        log_callback("🚀 [Test Mode] rawpy check skipped.")
    
    def check_ollama_connection(log_callback, all_systems_go=True):
        log_callback("🚀 [Test Mode] Ollama check skipped.")
        return False
    
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
        background: rgba(0, 0, 0, 0.85);
    }
    
    #model-dialog {
        width: 60%;
        height: 60%;
        border: solid #333333;
        background: #000000;
        padding: 1;
    }
    
    #model-title {
        padding: 1;
        text-style: bold;
    }
    
    #model-list {
        height: 1fr;
        border: solid #222222;
        margin: 1 0;
        background: #0a0a0a;
        padding: 1;
    }
    
    #current-model {
        height: 3;
        margin-bottom: 1;
        padding: 1;
        background: #111111;
        border: solid #222222;
    }
    
    #model-button-row {
        height: auto;
        align: center middle;
        padding-top: 1;
    }
    
    #model-button-row Button {
        margin: 0 2;
    }
    
    .model-option {
        margin: 0 0 1 0;
        width: 100%;
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
        border: solid $surface;
        /* Changed from thick $primary to solid $surface - thinner and darker */
        background: $surface;
        padding: 1;
    }
    
    #tree-container {
        height: 1fr;
        border: solid $surface;
        /* Changed from solid $primary 50% to solid $surface */
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
                # Use FilteredDirectoryTree to hide dotfiles
                yield FilteredDirectoryTree(str(Path.home()), id="dir-tree")
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


class DryRunSelectScreen(ModalScreen[Optional[str]]):
    """Modal screen for selecting which workflow to preview."""

    CSS = """
    DryRunSelectScreen {
        align: center middle;
    }

    #dryrun-dialog {
        width: 50;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #dryrun-dialog Label {
        text-align: center;
        margin-bottom: 1;
    }

    #dryrun-dialog Button {
        width: 100%;
        margin: 0 0 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dryrun-dialog"):
            yield Label("[bold yellow]Dry Run - Select Workflow[/bold yellow]")
            yield Label("[dim]Preview operations without moving files[/dim]")
            yield Button("[A] Auto Workflow", id="dry-auto", variant="primary")
            yield Button("[B] Burst Detection", id="dry-burst", variant="default")
            yield Button("[C] Quality Culling", id="dry-cull", variant="default")
            yield Button("Cancel", id="dry-cancel", variant="error")

    @on(Button.Pressed, "#dry-auto")
    def on_auto(self) -> None:
        self.dismiss("auto")

    @on(Button.Pressed, "#dry-burst")
    def on_burst(self) -> None:
        self.dismiss("burst")

    @on(Button.Pressed, "#dry-cull")
    def on_cull(self) -> None:
        self.dismiss("cull")

    @on(Button.Pressed, "#dry-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)


# ==============================================================================
# Widget Components
# ==============================================================================

class PreviewStatusWidget(Container):
    """Shows cache status with action buttons after dry run."""

    def compose(self) -> ComposeResult:
        with Horizontal(id="preview-status-bar"):
            yield Static("[bold green]✓[/bold green] Preview cached ([cyan]5 AI names[/cyan] ready)", id="preview-status-text")
            yield Button("Execute Now", id="btn-execute-cached", variant="primary")
            yield Button("Forget & Redo", id="btn-forget-preview", variant="warning")

    def update_status(self, count: int) -> None:
        """Update the status text with cache count."""
        text = self.query_one("#preview-status-text", Static)
        text.update(f"[bold green]✓[/bold green] Preview cached ([cyan]{count} AI names[/cyan] ready)")

    def show_widget(self) -> None:
        """Show the widget."""
        self.display = True
        self.refresh(layout=True)

    def hide_widget(self) -> None:
        """Hide the widget."""
        self.display = False
        self.refresh(layout=True)


# ==============================================================================
# Widget Components
# ==============================================================================

class RAMMonitor(Container):
    """Real-time RAM monitor with sparkline graph."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ram_data = [0.0] * 20  # Reduced points for footer
        self.update_timer: Optional[Timer] = None
    
    def compose(self) -> ComposeResult:
        if not PSUTIL_AVAILABLE:
            yield Static("RAM: N/A", classes="sysmon-error")
            return
        
        with Horizontal(classes="sysmon-row"):
            yield Static("RAM", classes="sysmon-label")
            yield Sparkline(self.ram_data, id="ram-sparkline", classes="sysmon-sparkline")
            yield Static("0%", id="ram-value", classes="sysmon-value")
    
    def on_mount(self) -> None:
        if PSUTIL_AVAILABLE:
            self.update_timer = self.set_interval(2.0, self.update_stats)
            self.set_timer(0.5, self.update_stats)
    
    def on_unmount(self) -> None:
        if self.update_timer:
            self.update_timer.stop()
    
    def update_stats(self) -> None:
        if not PSUTIL_AVAILABLE:
            return
        try:
            ram = psutil.virtual_memory()
            ram_percent = ram.percent
            self.ram_data.append(ram_percent)
            self.ram_data.pop(0)
            
            try:
                sparkline = self.query_one("#ram-sparkline", Sparkline)
                sparkline.data = list(self.ram_data)
                sparkline.refresh()
                
                value = self.query_one("#ram-value", Static)
                color = "red" if ram_percent > 85 else "white"
                value.update(f"[{color}]{ram_percent:.0f}%[/{color}]")
            except Exception:
                pass
        except Exception:
            pass

class CPUMonitor(Container):
    """Real-time CPU monitor with sparkline graph."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cpu_data = [0.0] * 20  # Reduced points for footer
        self.update_timer: Optional[Timer] = None
    
    def compose(self) -> ComposeResult:
        if not PSUTIL_AVAILABLE:
            yield Static("CPU: N/A", classes="sysmon-error")
            return
        
        with Horizontal(classes="sysmon-row"):
            yield Static("CPU", classes="sysmon-label")
            yield Sparkline(self.cpu_data, id="cpu-sparkline", classes="sysmon-sparkline")
            yield Static("0%", id="cpu-value", classes="sysmon-value")
    
    def on_mount(self) -> None:
        if PSUTIL_AVAILABLE:
            self.update_timer = self.set_interval(2.0, self.update_stats)
            self.set_timer(0.5, self.update_stats)
    
    def on_unmount(self) -> None:
        if self.update_timer:
            self.update_timer.stop()
    
    def update_stats(self) -> None:
        if not PSUTIL_AVAILABLE:
            return
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_data.append(cpu_percent)
            self.cpu_data.pop(0)
            
            try:
                sparkline = self.query_one("#cpu-sparkline", Sparkline)
                sparkline.data = list(self.cpu_data)
                sparkline.refresh()
                
                value = self.query_one("#cpu-value", Static)
                color = "red" if cpu_percent > 80 else "white"
                value.update(f"[{color}]{cpu_percent:.0f}%[/{color}]")
            except Exception:
                pass
        except Exception:
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
        """Filter out hidden files/directories and system roots."""
        excluded_roots = {'/bin', '/sbin', '/usr', '/var', '/private', '/System', '/Library', '/dev', '/proc', '/sys', '/tmp', '/run', '/boot', '/etc', '/opt', '/net', '/home', '/Volumes', '/cores'}
        return [
            path
            for path in paths
            if not path.name.startswith(".") 
            and str(path) not in excluded_roots
        ]


class MilestoneHUD(Container):
    """
    Heads-Up Display for real-time workflow statistics.
    
    Displays 5 key metrics in tactical dashboard boxes:
    - BURSTS: Number of burst groups detected
    - TIER A/B/C: Quality culling distribution  
    - HEROES: Files selected for archiving
    - ARCHIVED: Successfully archived files
    - TIME: Workflow duration
    
    Pro Mode exclusive feature.
    """
    
    def compose(self) -> ComposeResult:
        """Build the HUD layout with 5 stat boxes."""
        with Horizontal(id="hud-layout"):
            # Box 1: BURSTS
            with Vertical(classes="hud-box", id="hud-bursts"):
                yield Label("BURSTS", classes="hud-label")
                yield Label("--", id="stat-bursts", classes="hud-value")
            
            # Box 2: TIER A/B/C (color-coded)
            with Vertical(classes="hud-box", id="hud-tiers"):
                yield Label("TIER A / B / C", classes="hud-label")
                with Horizontal(classes="hud-multi-val"):
                    yield Label("-", id="stat-tier-a", classes="hud-val-a")
                    yield Label("/", classes="hud-sep")
                    yield Label("-", id="stat-tier-b", classes="hud-val-b")
                    yield Label("/", classes="hud-sep")
                    yield Label("-", id="stat-tier-c", classes="hud-val-c")
            
            # Box 3: HEROES
            with Vertical(classes="hud-box", id="hud-heroes"):
                yield Label("HEROES", classes="hud-label")
                yield Label("--", id="stat-heroes", classes="hud-value")
            
            # Box 4: ARCHIVED
            with Vertical(classes="hud-box", id="hud-archived"):
                yield Label("ARCHIVED", classes="hud-label")
                yield Label("--", id="stat-archived", classes="hud-value")
            
            # Box 5: TIME
            with Vertical(classes="hud-box", id="hud-time"):
                yield Label("TIME", classes="hud-label")
                yield Label("--", id="stat-time", classes="hud-value")
    
    def update_stat(self, category: str, value: Any) -> None:
        """
        Update a specific stat display.
        
        Args:
            category: Stat identifier ('bursts', 'tier_a', 'heroes', 'archived', 'time')
            value: New value to display (int, str, or tuple for tiers)
        """
        try:
            if category == "bursts":
                self.query_one("#stat-bursts", Label).update(str(value))
            
            elif category == "tier_a":
                self.query_one("#stat-tier-a", Label).update(str(value))
            elif category == "tier_b":
                self.query_one("#stat-tier-b", Label).update(str(value))
            elif category == "tier_c":
                self.query_one("#stat-tier-c", Label).update(str(value))
            
            elif category == "heroes":
                self.query_one("#stat-heroes", Label).update(str(value))
            
            elif category == "archived":
                self.query_one("#stat-archived", Label).update(str(value))
            
            elif category == "time":
                self.query_one("#stat-time", Label).update(str(value))
        
        except Exception:
            # Fail silently if widget isn't mounted yet
            pass
    
    def reset(self) -> None:
        """Reset all stats to dashes (idle state)."""
        self.update_stat("bursts", "--")
        self.update_stat("tier_a", "-")
        self.update_stat("tier_b", "-")
        self.update_stat("tier_c", "-")
        self.update_stat("heroes", "--")
        self.update_stat("archived", "--")
        self.update_stat("time", "--")


# ==============================================================================
# Main Application
# ==============================================================================

class FixxerTUI(App):
    """The main TUI application for FIXXER."""

    # v10.0: CSS is now loaded dynamically based on pro_mode config
    # We'll load CSS content in __init__ instead of using CSS_PATH
    CSS = ""  # Will be populated in __init__

    # Terminal window title (appears in title bar)
    TITLE = "FIXXER"

    # Add a border title to the main app screen
    BORDER_TITLE = "V.C.S. INTERFACE"
    
    BINDINGS = [
        Binding("q", "quit", "Quit (q)", show=False),
        Binding("r", "refresh_config", "Refresh (r)", show=False),
        Binding("1", "set_source", "Source (1)", show=False),
        Binding("2", "set_dest", "Dest (2)", show=False),
        Binding("m", "select_model", "Model (m)", show=False),
        Binding("f12", "toggle_pro_mode", "Pro Mode (F12)", show=False),
        Binding("ctrl+c", "quit", "Quit", show=False),
        # Workflow Shortcuts
        Binding("a", "run_auto", "Auto (a)", show=False),
        Binding("d", "run_dryrun", "Dry Run (d)", show=False),
        Binding("b", "run_bursts", "Bursts (b)", show=False),
        Binding("c", "run_cull", "Cull (c)", show=False),
        Binding("s", "run_stats", "Stats (s)", show=False),
        Binding("k", "run_critique", "Critique (k)", show=False),
        Binding("escape", "stop", "Stop (Esc)", show=False),
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
        # Load config FIRST to determine CSS
        temp_config = load_app_config()
        pro_mode = temp_config.get('pro_mode', False)

        # Load appropriate CSS file using importlib.resources
        from . import themes
        css_filename = "pro.css" if pro_mode else "warez.css"
        try:
            ref = importlib.resources.files(themes) / css_filename
            with ref.open("r", encoding="utf-8") as f:
                FixxerTUI.CSS = f.read()
        except Exception as e:
            # Fallback to default if file not found
            print(f"Warning: Could not load theme {css_filename}: {e}")
            FixxerTUI.CSS = ""
        
        super().__init__(**kwargs)
        self.app_config = temp_config
        self.current_thread: Optional[threading.Thread] = None
        self.workflow_active = False
        self.stop_event = threading.Event()

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
        self.progress_container: Optional[Container] = None  # For compact/expanded state
        self.milestone_hud: Optional[MilestoneHUD] = None  # HUD reference (Pro Mode only)

        # Dry-run preview feature (NEW)
        self.ai_cache: Dict[str, Dict] = {}  # Model-aware AI result cache
        self.cache_lock = threading.Lock()  # Thread-safe cache access
        self.preview_log_buffer: list = []  # Preview log accumulator
        self.preview_log_path: Optional[Path] = None  # Current preview log file
        self.preview_status: Optional[PreviewStatusWidget] = None  # Preview status widget
    
    def get_fixxer_logo(self) -> str:
        """UI: Returns the FIXXER logo - adapts to pro_mode."""
        
        if self.app_config.get('pro_mode', False):
            # PRO MODE: Compact single-line header with F12 indicator
            logo = """[bold white]F I X X E R  / /  P R O[/bold white]                                                      [dim white][ F12 ][/dim white]
[#666666]V I S U A L[/#666666] [dim white]I N T E L L I G E N C E[/dim white]  [#666666]/ /[/#666666]  [dim white]L O C A L[/dim white] [#666666]C O M P U T E[/#666666]"""
        else:
            # STANDARD MODE: Warez Edition
            logo = """[bold white]███████ ██[/bold white]   [bold white]██   ██ ██   ██[/bold white]   [bold red]███████ ██████ [/bold red]     [bold red]██[/bold red]
[bold white]██      ██[/bold white]   [bold white] ██ ██   ██ ██ [/bold white]   [bold red]██      ██   ██[/bold red]     [bold red]██[/bold red]
[bold white]█████   ██[/bold white]   [bold white]  ███     ███  [/bold white]   [bold red]█████   ██████ [/bold red]  [bold red]████████[/bold red]
[bold white]██      ██[/bold white]   [bold white] ██ ██   ██ ██ [/bold white]   [bold red]██      ██   ██[/bold red]     [bold red]██[/bold red]
[bold white]██      ██[/bold white]   [bold white]██   ██ ██   ██[/bold white]   [bold red]███████ ██   ██[/bold red]     [bold red]██[/bold red]

[bold red]CHAOS PATCHED // LOGIC INJECTED[/bold red]"""
        
        return logo

    def compose(self) -> ComposeResult:
        # No Header
        # The app title is now part of the logo/header area
        # Layout: [LOGO] [Easy Archive] [HUD boxes] - aligned left, not pushed right
        with Horizontal(id="header-row"):
            # Left: Logo block
            yield Static(self.get_fixxer_logo(), id="logo")
            
            # Easy Archive button - after logo
            yield Button("Easy", id="btn-easy", classes="easy-btn")
            
            # HUD boxes (Pro Mode only) - right after Easy button
            if self.app_config.get('pro_mode', False):
                self.milestone_hud = MilestoneHUD(id="milestone-hud")
                yield self.milestone_hud
        
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
                
                # === MODE-SPECIFIC WIDGETS ===
                if not self.app_config.get('pro_mode', False):
                    # Standard Mode only: System Monitor with red sparklines in panel
                    with Container(id="system-monitor"):
                        yield RAMMonitor()
                        yield CPUMonitor()
                # Pro Mode: HUD is now in header, no system monitor here
                # =====================================

                self.status_bar = Static(id="status-bar")
                yield self.status_bar

                # Preview status widget (dry-run feature) - hidden by default
                self.preview_status = PreviewStatusWidget(id="preview-status")
                self.preview_status.display = False
                yield self.preview_status

                # Progress indicator - compact when idle, expands when active
                self.progress_container = Container(id="progress-container")
                with self.progress_container:
                    self.spinner_display = Static("", id="spinner-display")
                    yield self.spinner_display
                    with Horizontal(id="progress-inner"):
                        self.progress_phrase = Static("Ready", id="progress-phrase")
                        yield self.progress_phrase
                        self.progress_timer_display = Static("", id="progress-timer")
                        yield self.progress_timer_display
                
                self.log_panel = LogPanel(id="log-panel")
                yield self.log_panel
        
        with Horizontal(id="button-bar"):
            # Pro Mode Only: RAM monitor in footer (left bookend)
            if self.app_config.get('pro_mode', False):
                self.ram_monitor = RAMMonitor(id="ram-monitor")
                yield self.ram_monitor

            # Center Stage: Controls (always visible in both modes)
            with Horizontal(id="controls-container"):
                # Group 1: Setup
                with Horizontal(classes="btn-group"):
                    yield Button("[1] Source", id="btn-source", variant="warning", classes="path-btn", tooltip="Keyboard: 1")
                    yield Button("[2] Dest", id="btn-dest", variant="warning", classes="path-btn", tooltip="Keyboard: 2")
                    yield Button("[D] Dry Run", id="btn-dryrun", variant="default", classes="workflow-btn", tooltip="Keyboard: D - Preview without moving files")
                    yield Button("[M] Model", id="btn-model", variant="default", classes="path-btn", tooltip="Keyboard: M")

                # Group 2: Tactical
                with Horizontal(classes="btn-group"):
                    yield Button("[A] Auto", id="btn-auto", variant="primary", classes="workflow-btn", tooltip="Keyboard: A")
                    yield Button("[B] Bursts", id="btn-burst", variant="default", classes="workflow-btn", tooltip="Keyboard: B")
                    yield Button("[C] Cull", id="btn-cull", variant="default", classes="workflow-btn", tooltip="Keyboard: C")
                    yield Button("[S] Stats", id="btn-stats", variant="default", classes="workflow-btn", tooltip="Keyboard: S")
                
                # Group 3: System
                with Horizontal(classes="btn-group"):
                    yield Button("[K] Critique", id="btn-critique", variant="default", classes="workflow-btn", tooltip="Keyboard: K")
                    yield Button("[Esc] STOP", id="btn-stop", variant="error", classes="control-btn", disabled=True)
                    yield Button("[Q] Quit", id="btn-quit", variant="error", classes="control-btn")
            
            # Pro Mode Only: CPU monitor in footer (right bookend)
            if self.app_config.get('pro_mode', False):
                self.cpu_monitor = CPUMonitor(id="cpu-monitor")
                yield self.cpu_monitor
        # No Footer
    
    def on_mount(self) -> None:
        # Set terminal window title using ANSI escape sequence
        # Works with most terminal emulators (xterm, iTerm2, Terminal.app, etc.)
        import sys
        sys.stdout.write("\033]0;FIXXER\007")
        sys.stdout.flush()

        self.write_to_log("[bold red]VisionCrew Fixxer v1.0.0[/bold red] - System Online")
        self.write_to_log("[dim]────────────────────────────────────────────[/dim]")
        
        if not ENGINE_AVAILABLE:
            self.write_to_log(f"[bold red]✗ FATAL: fixxer_engine.py not found.[/bold red]")
            self.write_to_log(f"[dim]   Error: {ENGINE_IMPORT_ERROR}[/dim]")
            self.toggle_workflow_buttons(disabled=True, force=True)
            return
        
        # Track if all critical systems are ready (for FULL VISION status)
        all_systems_ready = True
        
        # Log supported extensions for debugging
        if SUPPORTED_EXTENSIONS:
            raw_exts = [ext for ext in SUPPORTED_EXTENSIONS if ext.upper() in ['.RW2', '.ARW', '.CR2', '.CR3', '.NEF', '.DNG', '.RAF', '.ORF', '.PEF', '.SRW']]
            self.write_to_log(f"✓ Supported extensions: {len(SUPPORTED_EXTENSIONS)} types")
            if raw_exts:
                self.write_to_log(f"  Added RAW formats: {', '.join(sorted(set([e.lower() for e in raw_exts])))}")
        
        try:
            check_rawpy(self.write_to_log)
        except Exception as e:
            self.write_to_log(f"[red]Error during rawpy check: {e}[/red]")
            all_systems_ready = False
        
        # NEW: Check BRISQUE engine availability (using pre-checked flags)
        self._check_brisque_engine()
        if BRISQUE_STATUS == "fallback":
            all_systems_ready = False
        
        # NEW: Check CLIP engine availability (using pre-checked flags)
        self._check_clip_engine()
        if CLIP_STATUS == "fallback":
            all_systems_ready = False

        if self.app_config.get('config_file_found'):
            self.write_to_log(f"✓ Config loaded from ~/.photosort.conf")
        else:
            self.write_to_log("[yellow]No config file found, using defaults[/yellow]")
        
        # THE LLAMA CHECK (with system status) 🦙💨
        ollama_ready = check_ollama_connection(self.write_to_log, all_systems_ready)
        if not ollama_ready:
            # Ollama down doesn't break the system, but note it
            pass
        
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
            if self.app_config.get('pro_mode', False):
                # PRO MODE: Professional, time-based status messages
                elapsed = time.time() - self.workflow_start_time
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                if minutes > 0:
                    phrase = f"Processing active... [{minutes}m {seconds}s elapsed]"
                else:
                    phrase = f"Processing active... [{seconds}s elapsed]"
            else:
                # STANDARD MODE: Warez phrases
                elapsed = time.time() - self.workflow_start_time
                phrase = get_phrase_by_duration(elapsed, use_meta=True)
        else:
            # Ready state
            phrase = "System Ready" if self.app_config.get('pro_mode', False) else "Ready to process"
        
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

    @on(Button.Pressed, "#btn-stop")
    def on_stop_button(self) -> None:
        self.action_stop()

    def action_stop(self) -> None:
        """Emergency stop - terminate active workflow thread."""
        if not self.workflow_active:
            self.write_to_log("[yellow]No workflow running to stop[/yellow]")
            return
        
        if self.current_thread and self.current_thread.is_alive():
            self.write_to_log("🛑 [bold yellow]STOP requested by user...[/bold yellow]")
            self.write_to_log("   [yellow]Warning: Thread termination is not instant[/yellow]")
            self.write_to_log("   [yellow]Current operation will complete, then halt[/yellow]")
            
            # Signal thread to stop
            self.workflow_active = False
            self.stop_event.set()
            
            # Reset UI immediately
            self.stop_progress_tracking()
            self.toggle_workflow_buttons(disabled=False)
            self.toggle_workflow_buttons(disabled=False)
            self.update_status("Stopped by user", {})

    # --- Keyboard Shortcut Actions ---
    
    def action_run_auto(self) -> None:
        self.query_one("#btn-auto", Button).press()

    def action_run_dryrun(self) -> None:
        self.write_to_log("[bold magenta]🔑 'D' key pressed - triggering dry run button...[/bold magenta]")
        self.query_one("#btn-dryrun", Button).press()

    def action_run_bursts(self) -> None:
        self.query_one("#btn-burst", Button).press()

    def action_run_cull(self) -> None:
        self.query_one("#btn-cull", Button).press()

    def action_run_stats(self) -> None:
        self.query_one("#btn-stats", Button).press()

    def action_run_critique(self) -> None:
        self.query_one("#btn-critique", Button).press()

    @on(DirectoryTree.NodeSelected)
    def on_browser_node_selected(self, event: DirectoryTree.NodeSelected) -> None:
        """Handle double-click on a file or directory."""
        # Currently just a hook, can be expanded for specific double-click actions
        pass

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

            # Log selection for critique context
            self.write_to_log(f"   Target: {path.name}")

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
                from .engine import get_available_models
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
    
    def action_toggle_pro_mode(self) -> None:
        """Toggle between Warez and Pro (Phantom Redline) aesthetics."""
        if self.workflow_active:
            self.write_to_log("[yellow]Cannot toggle pro mode while workflow is running[/yellow]")
            return
        
        # Toggle the setting
        current = self.app_config.get('pro_mode', False)
        self.app_config['pro_mode'] = not current
        
        # Save to config
        if ENGINE_AVAILABLE and save_app_config(self.app_config):
            mode_name = "Pro Mode (Phantom Redline)" if not current else "Standard Mode (Warez)"
            self.write_to_log(f"✓ Switched to: {mode_name}")
            self.write_to_log(f"   [dim]Restart FIXXER to apply new theme[/dim]")
        else:
            self.write_to_log("[red]Failed to save pro_mode setting[/red]")
    
    # --- HUD Stats Callbacks ---
    
    def on_stats_update(self, key: str, value: Any) -> None:
        """
        Callback from engine (runs on background thread).
        CRITICAL: Must use call_from_thread for thread safety!
        """
        self.call_from_thread(self._update_hud_ui, key, value)
    
    def _update_hud_ui(self, key: str, value: Any) -> None:
        """
        Thread-safe UI update (runs on main thread).
        """
        if self.milestone_hud:
            self.milestone_hud.update_stat(key, value)
    
    # --- Workflow Handling ---
    
    @on(Button.Pressed, ".workflow-btn")
    def handle_workflow_button(self, event: Button.Pressed) -> None:
        if self.workflow_active:
            self.write_to_log("[red]A workflow is already running![/red]")
            return
            
        if not self.check_paths_configured():
            return
            
        # Reset HUD before new run
        if self.milestone_hud:
            self.milestone_hud.reset()

        # Special handling for dry run - don't disable buttons yet (modal needs them)
        if event.button.id == "btn-dryrun":
            self.write_to_log("[bold yellow]🔍 DRY RUN button pressed - opening workflow selector...[/bold yellow]")

            # Show modal to select which workflow to preview
            def handle_workflow_selection(workflow: Optional[str]):
                if workflow:
                    self.write_to_log(f"[bold yellow]📋 PREVIEW MODE selected: {workflow.upper()}[/bold yellow]")
                    self.run_workflow_in_preview_mode(workflow)
                else:
                    self.write_to_log("[dim]Dry run cancelled[/dim]")

            self.push_screen(DryRunSelectScreen(), handle_workflow_selection)
            return  # Exit early - don't disable buttons

        # For all other workflows, disable buttons before starting
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

    @on(Button.Pressed, "#btn-execute-cached")
    def handle_execute_cached(self, event: Button.Pressed) -> None:
        """Execute auto workflow using cached AI names from preview."""
        if self.workflow_active:
            self.write_to_log("[red]A workflow is already running![/red]")
            return

        if not self.check_paths_configured():
            return

        # Log cache usage
        cache_count = len(self.ai_cache)
        self.write_to_log("=" * 50)
        self.write_to_log(f"[cyan]⚡ Executing with {cache_count} cached AI names...[/cyan]")

        # Debug: Show cache keys
        if self.ai_cache:
            self.write_to_log("[dim]Debug: Cache keys:[/dim]")
            for key in list(self.ai_cache.keys())[:3]:  # Show first 3
                self.write_to_log(f"[dim]  - {key}[/dim]")

        self.toggle_workflow_buttons(disabled=True)
        self.start_progress_tracking()
        self.run_in_thread(self.run_auto_workflow_thread, "AutoWorkflow")

    @on(Button.Pressed, "#btn-forget-preview")
    def handle_forget_preview(self, event: Button.Pressed) -> None:
        """Clear cache and hide preview status widget."""
        count = len(self.ai_cache)
        with self.cache_lock:
            self.ai_cache.clear()

        if self.preview_status:
            self.preview_status.hide_widget()

        self.write_to_log(f"[yellow]✓ Forgot {count} preview names[/yellow]")
        self.write_to_log("[dim]Next run will generate fresh AI names[/dim]")
    
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
            elif btn.id == "btn-stop":
                # STOP button inverse logic - enabled ONLY during workflows
                btn.disabled = not disabled
            elif btn.id != "btn-quit":
                btn.disabled = disabled
    
    def on_workflow_complete(self) -> None:
        self.stop_progress_tracking()
        self.toggle_workflow_buttons(disabled=False)
        self.refresh_config_display() # Refresh directory tree on complete
    
    def run_in_thread(self, target, name: str) -> None:
        self.current_thread = threading.Thread(target=target, name=name, daemon=True)
        self.current_thread.start()

    # --- Dry Run / Preview Mode Methods ---

    def start_preview_logging(self) -> Path:
        """Initialize preview log file for dry run."""
        log_dir = Path.home() / ".fixxer" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        log_path = log_dir / f"preview_{timestamp}.txt"

        # Write header
        with open(log_path, 'w') as f:
            f.write("FIXXER DRY RUN LOG\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source: {self.app_config.get('last_source_path', 'N/A')}\n")
            f.write(f"Destination: {self.app_config.get('last_destination_path', 'N/A')}\n")
            f.write(f"Model: {self.app_config.get('default_model', 'N/A')}\n")
            f.write("=" * 70 + "\n\n")

        self.preview_log_path = log_path
        self.preview_log_buffer = []
        return log_path

    def write_to_preview_log(self, message: str) -> None:
        """Write to both TUI and preview log file."""
        self.write_to_log(message)
        if self.preview_log_path:
            self.preview_log_buffer.append(message)

    def finalize_preview_log(self) -> None:
        """Flush preview log to file."""
        if not self.preview_log_path or not self.preview_log_buffer:
            return

        import re

        # Strip Rich markup
        clean_buffer = []
        for line in self.preview_log_buffer:
            clean_line = re.sub(r'\[/?[a-z]+[^\]]*\]', '', line)
            clean_buffer.append(clean_line)

        # Append to file
        with open(self.preview_log_path, 'a') as f:
            f.write('\n'.join(clean_buffer))
            f.write('\n\n' + '=' * 70 + '\n')
            f.write(f"Preview completed at {datetime.now().strftime('%H:%M:%S')}\n")

        self.write_to_log(f"\n[dim]📄 Preview log saved: {self.preview_log_path.name}[/dim]")

        self.preview_log_buffer = []
        self.preview_log_path = None

    def run_workflow_in_preview_mode(self, workflow: str) -> None:
        """Execute selected workflow in preview mode."""
        if self.workflow_active:
            self.write_to_log("[red]A workflow is already running![/red]")
            return

        if not self.check_paths_configured():
            return

        self.toggle_workflow_buttons(disabled=True)
        self.write_to_log("=" * 50)
        self.write_to_log("[bold yellow]🚫 PREVIEW MODE ENABLED 🚫[/bold yellow]")
        self.write_to_log(f"[bold yellow]Starting DRY RUN: {workflow.upper()}[/bold yellow]")
        self.write_to_log("[dim yellow]No files will be moved - preview only[/dim yellow]")
        self.write_to_log("=" * 50)
        self.start_progress_tracking()

        if workflow == "auto":
            self.run_in_thread(self.run_dryrun_auto_thread, "DryRunAuto")
        elif workflow == "burst":
            self.run_in_thread(self.run_dryrun_burst_thread, "DryRunBurst")
        elif workflow == "cull":
            self.run_in_thread(self.run_dryrun_cull_thread, "DryRunCull")

    # --- Workflow Thread Targets ---
    
    def run_auto_workflow_thread(self) -> None:
        try:
            self.update_status("🚀 Running Auto...", {})

            # === CREATE STATS TRACKER WITH CALLBACK ===
            from .engine import StatsTracker
            tracker = StatsTracker(callback=self.on_stats_update)
            # ==========================================

            self.stop_event.clear()
            result = auto_workflow(
                log_callback=self.write_to_log,
                app_config=self.app_config,
                tracker=tracker,
                stop_event=self.stop_event,
                preview_mode=False,
                ai_cache=self.ai_cache,
                cache_lock=self.cache_lock
            )

            # Clear cache and hide widget after successful execution
            with self.cache_lock:
                self.ai_cache.clear()
            if self.preview_status:
                self.call_from_thread(self.preview_status.hide_widget)

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
            
            # === CREATE STATS TRACKER WITH CALLBACK ===
            from .engine import StatsTracker
            tracker = StatsTracker(callback=self.on_stats_update)
            # ==========================================
            
            self.stop_event.clear()
            group_bursts_in_directory(
                log_callback=self.write_to_log,
                app_config=self.app_config,
                simulated=False,
                tracker=tracker,
                stop_event=self.stop_event
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
            
            # === CREATE STATS TRACKER WITH CALLBACK ===
            from .engine import StatsTracker
            tracker = StatsTracker(callback=self.on_stats_update)
            # ==========================================
            
            self.stop_event.clear()
            cull_images_in_directory(
                log_callback=self.write_to_log,
                app_config=self.app_config,
                simulated=False,
                tracker=tracker,
                stop_event=self.stop_event
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
            self.stop_event.clear()
            show_exif_insights(
                log_callback=self.write_to_log,
                app_config=self.app_config,
                simulated=False,
                stop_event=self.stop_event
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
                from .engine import critique_single_image
                import json
                
                # Get first image from source directory for critique
                # OR use the currently selected file in the browser if it's an image
                image_file = None
                
                if self.file_browser and self.file_browser.cursor_node:
                    node = self.file_browser.cursor_node
                    if node.data and node.data.path.is_file():
                        if node.data.path.suffix.lower() in SUPPORTED_EXTENSIONS:
                            image_file = node.data.path
                
                if not image_file:
                    source_path = self.app_config.get('last_source_path')
                    if not source_path or not Path(source_path).is_dir():
                        self.write_to_log("[red]✗ No source directory set.[/red]")
                        return
                    
                    # Find first image file
                    p = Path(source_path)
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
                self.write_to_log("[dim]Add critique_single_image() to fixxer_engine.py[/dim]")
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
            self.stop_event.clear()
            result = simple_sort_workflow(
                log_callback=self.write_to_log,
                app_config=self.app_config,
                stop_event=self.stop_event,
                preview_mode=False,
                ai_cache=self.ai_cache,
                cache_lock=self.cache_lock
            )
            self.write_to_log("[bold green]✓ Easy Archive complete![/bold green]")
            self.update_status("✅ Archive Complete", result if isinstance(result, dict) else {})
        except Exception as e:
            self.write_to_log(f"[bold red]✗ Easy Archive failed: {e}[/bold red]")
            self.update_status("❌ Error", {})
        finally:
            self.call_from_thread(self.on_workflow_complete)

    # --- Dry Run / Preview Workflow Threads ---

    def run_dryrun_auto_thread(self) -> None:
        """Dry run auto workflow with persistent logging."""
        try:
            # Start logging
            log_path = self.start_preview_logging()

            from .engine import StatsTracker
            tracker = StatsTracker(callback=self.on_stats_update)

            self.stop_event.clear()
            result = auto_workflow(
                log_callback=self.write_to_preview_log,
                app_config=self.app_config,
                tracker=tracker,
                stop_event=self.stop_event,
                preview_mode=True,
                ai_cache=self.ai_cache,
                cache_lock=self.cache_lock
            )

            # Finalize log
            self.finalize_preview_log()

            # Show cache status
            cache_count = len(self.ai_cache)
            self.write_to_log(f"[dim]Debug: Cache has {cache_count} entries[/dim]")

            if self.ai_cache:
                if self.preview_status:
                    self.write_to_log("[dim]Debug: Showing preview status widget...[/dim]")
                    self.call_from_thread(self.preview_status.update_status, cache_count)
                    self.call_from_thread(self.preview_status.show_widget)
                else:
                    self.write_to_log("[dim]Debug: preview_status is None[/dim]")
            else:
                self.write_to_log("[dim]Debug: Cache is empty, not showing widget[/dim]")

            self.write_to_log("[bold green]✓ Dry run complete![/bold green]")
            self.update_status("✅ Preview Complete", result if isinstance(result, dict) else {})

        except Exception as e:
            self.write_to_log(f"[bold red]✗ Dry run failed: {e}[/bold red]")
            self.finalize_preview_log()
            self.update_status("❌ Error", {})

        finally:
            self.call_from_thread(self.on_workflow_complete)

    def run_dryrun_burst_thread(self) -> None:
        """Dry run burst workflow with persistent logging."""
        try:
            log_path = self.start_preview_logging()

            from .engine import StatsTracker
            tracker = StatsTracker(callback=self.on_stats_update)

            self.stop_event.clear()
            group_bursts_in_directory(
                log_callback=self.write_to_preview_log,
                app_config=self.app_config,
                tracker=tracker,
                stop_event=self.stop_event,
                preview_mode=True,
                ai_cache=self.ai_cache,
                cache_lock=self.cache_lock
            )

            self.finalize_preview_log()
            self.write_to_log("[bold green]✓ Dry run burst complete![/bold green]")
            self.update_status("✅ Preview Complete", {})

        except Exception as e:
            self.write_to_log(f"[bold red]✗ Dry run burst failed: {e}[/bold red]")
            self.finalize_preview_log()
            self.update_status("❌ Error", {})

        finally:
            self.call_from_thread(self.on_workflow_complete)

    def run_dryrun_cull_thread(self) -> None:
        """Dry run cull workflow with persistent logging."""
        try:
            log_path = self.start_preview_logging()

            from .engine import StatsTracker
            tracker = StatsTracker(callback=self.on_stats_update)

            self.stop_event.clear()
            cull_images_in_directory(
                log_callback=self.write_to_preview_log,
                app_config=self.app_config,
                tracker=tracker,
                stop_event=self.stop_event,
                preview_mode=True
            )

            self.finalize_preview_log()
            self.write_to_log("[bold green]✓ Dry run cull complete![/bold green]")
            self.update_status("✅ Preview Complete", {})

        except Exception as e:
            self.write_to_log(f"[bold red]✗ Dry run cull failed: {e}[/bold red]")
            self.finalize_preview_log()
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
    app = FixxerTUI()
    app.run()


if __name__ == "__main__":
    main()