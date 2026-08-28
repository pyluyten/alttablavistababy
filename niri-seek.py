#!/usr/bin/env python3
import json
import subprocess
import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")

from gi.repository import Adw, Gio, Gtk, Gdk, GLib


def get_niri_windows():
    """Fetch active window list from Niri compositor IPC."""
    try:
        result = subprocess.run(
            ["niri", "msg", "--json", "windows"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error communicating with Niri: {e}", file=sys.stderr)
        return []


def focus_niri_window(window_id):
    """Focus the target window by ID using Niri CLI."""
    try:
        subprocess.run(
            ["niri", "msg", "action", "focus-window", "--id", str(window_id)],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to focus window {window_id}: {e}", file=sys.stderr)


def get_app_icon_name(app_id):
    """Find the best icon name using desktop app info."""
    if not app_id:
        return "application-x-executable"
    
    # Try direct desktop file lookup
    desktop_id = f"{app_id}.desktop" if not app_id.endswith(".desktop") else app_id
    app_info = Gio.DesktopAppInfo.new(desktop_id)
    
    if app_info:
        icon = app_info.get_icon()
        if icon:
            return icon.to_string()
            
    # Fallback to lowercased app_id string
    return app_id.lower()


class WindowRow(Gtk.ListBoxRow):
    """Custom ListBox row representing a single Niri window."""
    def __init__(self, win_data):
        super().__init__()
        self.win_id = win_data.get("id")
        self.title = win_data.get("title") or "Untitled Window"
        self.app_id = win_data.get("app_id") or "Unknown"
        self.workspace = win_data.get("workspace_id", "")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # App Icon
        icon_name = get_app_icon_name(self.app_id)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(32)
        box.append(icon)

        # Labels (Title + App ID)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        title_label = Gtk.Label(label=self.title, xalign=0)
        title_label.set_ellipsize(3) # pango.EllipsizeMode.END
        title_label.add_css_class("title")
        
        app_label = Gtk.Label(label=f"{self.app_id}", xalign=0)
        app_label.add_css_class("subtitle")
        app_label.add_css_class("dim-label")
        
        vbox.append(title_label)
        vbox.append(app_label)
        
        box.append(vbox)
        self.set_child(box)

    def matches(self, query):
        """Filter helper for search text."""
        q = query.lower()
        return q in self.title.lower() or q in self.app_id.lower()


class NiriSeekWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NiriSeek")
        self.set_default_size(600, 400)
        self.set_resizable(False)

        # Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)

        # Search Entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search open windows...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("activate", self.on_activate_selected)
        
        # Add escape key listener directly to the search box
        search_key_controller = Gtk.EventControllerKey()
        search_key_controller.connect("key-pressed", self.on_key_pressed)
        self.search_entry.add_controller(search_key_controller)
        
        main_box.append(self.search_entry)

        # Scrolled Window for List
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-activated", self.on_row_activated)
        self.list_box.set_filter_func(self.filter_func)
        
        scrolled.set_child(self.list_box)
        main_box.append(scrolled)

        self.set_content(main_box)

        # Keyboard Navigation Shortcut Handler
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

        self.populate_windows()

    def populate_windows(self):
        """Fetch windows from Niri, sort by MRU, and populate list."""
        windows = get_niri_windows()

        def extract_timestamp(w):
            """Extract comparable numeric timestamp from Niri IPC data."""
            ts = w.get("focus_timestamp") or w.get("focused_at")
            if isinstance(ts, dict):
                # Niri returns timestamps like {"secs_since_epoch": 12345, "nanos": 6789}
                return ts.get("secs_since_epoch", 0) + (ts.get("nanos", 0) / 1e9)
            elif isinstance(ts, (int, float)):
                return ts
            return 0

        # Sort windows: focused state first, then most recently focused
        windows.sort(
            key=lambda w: (
                not w.get("is_focused", False),
                -extract_timestamp(w)
            )
        )

        # Move current focused window to the second spot (or end) for quick Alt-Tab behavior
        if len(windows) > 1 and windows[0].get("is_focused"):
            windows.append(windows.pop(0))

        for win in windows:
            row = WindowRow(win)
            self.list_box.append(row)

        # Select first row by default
        first_row = self.list_box.get_row_at_index(0)
        if first_row:
            self.list_box.select_row(first_row)

    def filter_func(self, row):
        query = self.search_entry.get_text().strip()
        if not query:
            return True
        return row.matches(query)

    def on_search_changed(self, entry):
        self.list_box.invalidate_filter()
        
        # Auto-select the first visible row after search
        first_visible = None
        idx = 0
        while True:
            row = self.list_box.get_row_at_index(idx)
            if not row:
                break
            if row.get_child_visible() and row.is_visible():
                first_visible = row
                break
            idx += 1
            
        if first_visible:
            self.list_box.select_row(first_visible)

    def on_activate_selected(self, entry):
        selected_row = self.list_box.get_selected_row()
        if selected_row:
            self.on_row_activated(self.list_box, selected_row)

    def on_row_activated(self, listbox, row):
        if row and hasattr(row, "win_id"):
            focus_niri_window(row.win_id)
            self.close()

    def on_key_pressed(self, controller, keyval, keycode, state):
        # Escape key closes window
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        
        # Down arrow moves selection
        elif keyval == Gdk.KEY_Down:
            selected = self.list_box.get_selected_row()
            if selected:
                next_row = self.list_box.get_row_at_index(selected.get_index() + 1)
                if next_row:
                    self.list_box.select_row(next_row)
            return True
            
        # Up arrow moves selection
        elif keyval == Gdk.KEY_Up:
            selected = self.list_box.get_selected_row()
            if selected and selected.get_index() > 0:
                prev_row = self.list_box.get_row_at_index(selected.get_index() - 1)
                if prev_row:
                    self.list_box.select_row(prev_row)
            return True

        return False


class NiriSeekApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.niriseek.py")

    def do_activate(self):
        win = NiriSeekWindow(self)
        win.present()


if __name__ == "__main__":
    app = NiriSeekApp()
    app.run(sys.argv)
