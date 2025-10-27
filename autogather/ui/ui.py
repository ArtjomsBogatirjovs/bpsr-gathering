# autogather/ui.py
import json
import logging
import os
import time
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox
from typing import Optional, Tuple, List

from autogather.config import PROMPT_ROI, PRESET_ASPECT_RATIO, PRESET_SPEED, PRESET_DONT_MOVE, PRESET_WANT_GATHERING, \
    PRESET_TOL_X, PRESET_MULT_Y, PRESET_MULT_X, PRESET_TOL_Y, PRESET_MOVE_BACK_TO_START, PRESET_ADJUST_DIRECTION, \
    PRESET_ADJUST_EVERY_CYCLE
from autogather.debug import save_selector_debug
from autogather.enums.aspect_ratio import AspectRatio
from autogather.enums.direction import Direction
from autogather.enums.gathering_speed import GatheringSpeedLevel
from autogather.enums.resource import Resource
from autogather.folder_utils import scan_resources, load_resource_dir, _presets_path
from autogather.model.resource_model import ResourceObject
from autogather.model.worker import Worker
from autogather.screen import WindowScreen, _get_selector_rectangle
from autogather.ui.ui_utils import _apply_style, _card, _github_icon, _palette
from autogather.winutil import list_windows, bring_to_foreground

logger = logging.getLogger(__name__)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Blue Protocol: Star Resonance - Auto gathering")
        self.root.geometry("1400x800")

        base_dir = os.path.dirname(__file__)
        icon_path = os.path.join(base_dir, "assets", "app_icon.png")
        self._app_icon = tk.PhotoImage(file=icon_path)
        self.root.iconphoto(True, self._app_icon)
        self.dark_mode = tk.BooleanVar(value=False)

        self.want_gathering = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Select the 'resources' folder, choose a resource, and pick the game window.")

        self.resource = None
        self._name_to_res: dict[str, Resource] = {}
        self._selected_name = tk.StringVar(value="")

        self._win_choices: List[Tuple[str, int]] = []
        self._selected_win = tk.StringVar(value="")

        self.screen = None
        self.worker: Optional[Worker] = None
        self.ts_f = self.ts_g = self.ts_s = self.ts_r = None

        self.mult_x = tk.DoubleVar(value=1.0)
        self.mult_y = tk.DoubleVar(value=1.0)
        self.tol_x = tk.IntVar(value=0)
        self.tol_y = tk.IntVar(value=0)
        self._updating_fields = False

        self.aspect_ratio = tk.StringVar(value=str(AspectRatio.from_preset()))
        self.gathering_speed = tk.StringVar(value=GatheringSpeedLevel.FAST.name)
        self.move_back_to_start = tk.BooleanVar(value=False)
        self.dont_move = tk.BooleanVar(value=False)
        self.adjust_every_cycle = tk.BooleanVar(value=False)
        self.adjust_dir = tk.StringVar(value=Direction.NONE.name)

        self._build_ui()

        self.cmb.bind("<<ComboboxSelected>>", self._on_resource_selected)

        self.rescan()
        self.refresh_windows()
        self._tick()

    def _build_ui(self):
        PAD, GUT = 14, 10
        dark = getattr(self, "dark_mode", tk.BooleanVar(value=False)).get()
        _apply_style(self.root, dark)

        # ===== Root grid =====
        shell = ttk.Frame(self.root, padding=PAD)
        shell.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        shell.columnconfigure(0, weight=1)
        shell.columnconfigure(1, weight=1)

        # ===== Header (title + toolbar) =====
        header = ttk.Frame(shell, style="Header.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, GUT))
        header.columnconfigure(0, weight=1)  # left grows
        header.columnconfigure(1, weight=0)

        # right: toolbar (theme, GitHub, Start/Stop)
        right = ttk.Frame(header, style="Header.TFrame")
        right.grid(row=0, column=1, sticky="e")
        for i in range(6):
            right.columnconfigure(i, weight=0)

        # theme toggle
        if not hasattr(self, "dark_mode"):
            self.dark_mode = tk.BooleanVar(value=dark)
        theme_lbl = ttk.Label(right, style="Subtitle.TLabel", cursor="hand2")
        theme_lbl.grid(row=0, column=0, padx=(0, 12), sticky="e")

        # GitHub icon
        pal_bg = _palette(dark)["BG"]
        self._gh_img = _github_icon(dark)
        gh_btn = tk.Label(right, image=self._gh_img, bg=pal_bg, cursor="hand2")
        gh_btn.grid(row=0, column=1, padx=(0, 16), sticky="e")
        gh_btn.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/ArtjomsBogatirjovs"))
        gh_btn.image = self._gh_img

        def _refresh_header():
            theme_lbl.configure(text="🌙 Dark theme" if not self.dark_mode.get() else "☀️ Light theme")
            self._gh_img = _github_icon(self.dark_mode.get())
            pal2 = _palette(self.dark_mode.get())["BG"]
            gh_btn.configure(image=self._gh_img, bg=pal2)
            gh_btn.image = self._gh_img

        def _toggle_theme(*_):
            _apply_style(self.root, self.dark_mode.get())
            _refresh_header()

        theme_lbl.bind("<Button-1>", lambda e: (self.dark_mode.set(not self.dark_mode.get()), _toggle_theme()))
        _refresh_header()

        # ===== LEFT column =====
        resource_card = _card(shell, row=1, column=0, sticky="nsew", padx=(0, GUT))
        ttk.Label(resource_card, text="Resource", style="Card.Section.TLabel") \
            .grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.cmb = ttk.Combobox(resource_card, style="Drop.TCombobox",
                                textvariable=self._selected_name, state="readonly", width=28, values=[])
        self.cmb.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=(0, 6))

        ttk.Checkbutton(resource_card, style="Card.TCheckbutton",
                        text='No-stamina mode (press only “Normal”)',
                        variable=self.want_gathering) \
            .grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 0))
        ttk.Checkbutton(resource_card, style="Card.TCheckbutton",
                        text="Don’t move. Stay in one spot.",
                        variable=self.dont_move) \
            .grid(row=2, column=0, columnspan=4, sticky="w", pady=(2, 0))
        ttk.Checkbutton(resource_card, style="Card.TCheckbutton",
                        text="Run back to start after gathering",
                        variable=self.move_back_to_start) \
            .grid(row=3, column=0, columnspan=4, sticky="w", pady=(2, 0))

        # Adjust every cycle (visible only if move_back_to_start)
        self.chk_adjust = ttk.Checkbutton(
            resource_card, style="Card.TCheckbutton",
            text="Adjust every cycle", variable=self.adjust_every_cycle
        )
        self.chk_adjust.grid(row=4, column=0, sticky="w", pady=(2, 0))

        self.lbl_dir = ttk.Label(resource_card, text="Direction:", style="Card.TLabel")
        self.lbl_dir.grid(row=4, column=1, sticky="w", padx=(8, 4), pady=(2, 0))

        self.dir_cmb = ttk.Combobox(
            resource_card, style="Drop.TCombobox",
            state="readonly", width=8, textvariable=self.adjust_dir,
            values=[Direction.NONE.name, Direction.UP.name, Direction.DOWN.name, Direction.LEFT.name,
                    Direction.RIGHT.name]
        )
        self.dir_cmb.grid(row=4, column=2, sticky="w", pady=(2, 0))

        def _sync_adjust_ui():
            if self.move_back_to_start.get():
                self.chk_adjust.grid()
                self.lbl_dir.grid()
                self.dir_cmb.grid()
            else:
                self.chk_adjust.grid_remove()
                self.lbl_dir.grid_remove()
                self.dir_cmb.grid_remove()

        self.move_back_to_start.trace_add("write", lambda *_: _sync_adjust_ui())
        _sync_adjust_ui()

        # params
        params_card = _card(shell, row=2, column=0, sticky="nsew", pady=(GUT, 0), padx=(0, GUT))
        ttk.Label(params_card, text="X multiplier", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(params_card, style="Num.TSpinbox", from_=0.0, to=10.0, increment=0.1, width=10,
                    textvariable=self.mult_x).grid(row=0, column=1, sticky="w", padx=(8, 12))
        ttk.Label(params_card, text="Y multiplier", style="Card.TLabel").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(params_card, style="Num.TSpinbox", from_=0.0, to=10.0, increment=0.1, width=10,
                    textvariable=self.mult_y).grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(params_card, text="X tolerance", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(params_card, style="Num.TSpinbox", from_=0, to=1000, increment=1, width=10,
                    textvariable=self.tol_x).grid(row=1, column=1, sticky="w", padx=(8, 12), pady=(8, 0))
        ttk.Label(params_card, text="Y tolerance", style="Card.TLabel").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Spinbox(params_card, style="Num.TSpinbox", from_=0, to=1000, increment=1, width=10,
                    textvariable=self.tol_y).grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(8, 0))

        ttk.Label(params_card, text="Gathering speed", style="Card.TLabel").grid(row=2, column=0, sticky="w",
                                                                                 pady=(10, 0))
        self.speed_cmb = ttk.Combobox(params_card, style="Drop.TCombobox", state="readonly", width=16,
                                      textvariable=self.gathering_speed,
                                      values=[level.name for level in GatheringSpeedLevel])
        self.speed_cmb.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(10, 0))

        # ===== RIGHT column =====
        window_card = _card(shell, row=1, column=1, sticky="nsew")
        ttk.Label(window_card, text="Target window", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        self.win_cmb = ttk.Combobox(window_card, style="Drop.TCombobox",
                                    textvariable=self._selected_win, state="readonly", width=36, values=[])
        self.win_cmb.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Button(window_card, text="↻ Refresh", command=self.refresh_windows).grid(row=0, column=2, sticky="e",
                                                                                     padx=(8, 0))

        ttk.Label(window_card, text="Aspect ratio", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 0))
        aspect_cb = ttk.Combobox(window_card, style="Drop.TCombobox", textvariable=self.aspect_ratio,
                                 values=[str(r) for r in AspectRatio], state="readonly", width=12)
        aspect_cb.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(10, 0))

        # ===== DEBUG SECTION =====
        actions_card = _card(shell, row=2, column=1, sticky="nsew", pady=(GUT, 0))
        ttk.Label(actions_card, text="Debug", style="Card.Section.TLabel") \
            .grid(row=0, column=0, sticky="w", pady=(0, 6))

        ttk.Button(
            actions_card,
            text="Debug selector menu",
            command=self._debug_selector_menu
        ).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(0, 6))

        # ===== Footer status bar =====
        footer = ttk.Frame(shell, padding=(8, 6))
        footer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(GUT, 0))

        footer.columnconfigure(0, weight=0)
        footer.columnconfigure(1, weight=0)
        footer.columnconfigure(2, weight=1)

        # start/stop
        self.btn_start = ttk.Button(footer, text="▶ Start", command=self.start, style="Primary.TButton", width=12)
        self.btn_start.grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.btn_stop = ttk.Button(footer, text="■ Stop", command=self.stop, state="disabled", width=10)
        self.btn_stop.grid(row=0, column=1, sticky="w", padx=(0, 12))

        self.btn_save = ttk.Button(footer, text="💾 Save preset", command=self._save_preset, width=14)
        self.btn_save.grid(row=0, column=2, sticky="w")

        # Status
        ttk.Label(footer, textvariable=self.status, style="Status.TLabel") \
            .grid(row=0, column=2, sticky="e")

        # expand
        shell.rowconfigure(1, weight=1)
        shell.rowconfigure(2, weight=1)
        shell.rowconfigure(3, weight=0)
        shell.columnconfigure(0, weight=1)
        shell.columnconfigure(1, weight=1)

    def _debug_selector_menu(self):
        if not self.screen:
            hwnd = self._selected_hwnd()
            if not hwnd:
                messagebox.showerror("No window", "Select target window from the list.")
                return
            self.screen = WindowScreen(hwnd)

        roi_val = PROMPT_ROI
        roi, roi_tuple = _get_selector_rectangle(self.screen, self.get_selected_aspect_ratio(), roi_val)
        save_selector_debug(self.screen.grab_bgr(), roi_tuple)
        self.status.set("Selector debug saved (roi_debug.png)")

    def get_gathering_speed(self) -> GatheringSpeedLevel:
        return GatheringSpeedLevel[self.gathering_speed.get()]

    def get_direction(self) -> Direction:
        return Direction[self.adjust_dir.get()]

    def get_selected_aspect_ratio(self) -> AspectRatio:
        return AspectRatio.get_ratio(self.aspect_ratio.get())

    def rescan(self):
        _resources = scan_resources()
        self._name_to_res = {res.display_name: res for res in _resources}

        names = sorted(self._name_to_res.keys(), key=str.lower)
        self.cmb["values"] = tuple(names)

        if names:
            cur = self._selected_name.get()
            if cur not in names:
                self._selected_name.set(names[0])
            self.status.set(f"Found {len(names)} resources.")
            self._on_resource_selected()
        else:
            self._selected_name.set("")
            self.cmb.set("")
            self.status.set("No valid resources found (folders must contain focused/gathering/selector).")

    def refresh_windows(self):
        wins = list_windows()  # [(hwnd, title)]
        arr: List[Tuple[str, int]] = []
        for hwnd, title in wins:
            display = f"{title}  [0x{int(hwnd):08X}]"
            arr.append((display, int(hwnd)))

        self._win_choices = arr
        self.win_cmb["values"] = [t for t, _ in arr]
        if arr:
            if self._selected_win.get() not in [t for t, _ in arr]:
                self._selected_win.set(arr[0][0])
            self.status.set(f"Found applications: {len(arr)}")
        else:
            self._selected_win.set("")
            self.status.set("Game not found. Please open the game window.")

    def _selected_hwnd(self) -> Optional[int]:
        disp = self._selected_win.get().strip()
        for t, h in self._win_choices:
            if t == disp:
                return h
        return None

    def start(self):
        if self.worker and self.worker.is_alive():
            return

        name = self._selected_name.get().strip()
        if not name or name not in self._name_to_res:
            messagebox.showerror("No resource", "Select a resource from the list.")
            return

        resource_enum = self._name_to_res[name]
        try:
            self.ts_f, self.ts_g, self.ts_s, self.ts_r = load_resource_dir(resource_enum.folder_name, resource_enum)
        except Exception as e:
            messagebox.showerror("Loading error", str(e))
            return

        if not (self.ts_g.tmps and self.ts_s.tmps) or (not self.ts_f.tmps and resource_enum.is_focus_needed):
            messagebox.showerror("No templates", "One or more required template folders are empty.")
            return

        hwnd = self._selected_hwnd()
        if not hwnd:
            messagebox.showerror("No window", "Select a game window from the list.")
            return

        try:
            bring_to_foreground(hwnd)
        except Exception:
            pass

        try:
            self.screen = WindowScreen(hwnd)
        except Exception as e:
            messagebox.showerror("Screen error", str(e))
            return

        # Create main loop
        self.worker = Worker(
            self.screen,
            self.ts_f, self.ts_g, self.ts_s, self.ts_r,
            self.want_gathering.get(),
            self.get_selected_aspect_ratio(),
            self.get_gathering_speed(),
            self.create_resource(),
            self.move_back_to_start.get(),
            self.dont_move.get()
        )
        self.worker.start()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status.set(f"Started: {name} | Window: {self._selected_win.get()}")

    def create_resource(self):
        return ResourceObject(self.resource.folder_name, self.mult_x.get(), self.mult_y.get(), self.tol_x.get(),
                              self.tol_y.get(), self.resource.is_focus_needed, self.adjust_every_cycle.get(),
                              self.get_direction())

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status.set("Stopped.")

    def _tick(self):
        if self.worker:
            self.status.set(f"Status: {self.worker.state}")
        self.root.after(150, self._tick)

    def _on_resource_selected(self, *_):
        name = self._selected_name.get()
        res = self._name_to_res.get(name)
        self.resource = res
        if not res:
            return
        preset_path = _presets_path()
        resource_dict = None
        try:
            if os.path.exists(preset_path):
                with open(preset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    resource_dict = data.get(res.folder_name)
            if not resource_dict:
                self.mult_x.set(res.get_mult_x())
                self.mult_y.set(res.get_mult_y())
                self.tol_x.set(res.get_tol_x())
                self.tol_y.set(res.get_tol_y())
            else:
                adjust_dir = resource_dict.get(PRESET_ADJUST_DIRECTION, Direction.NONE.name)
                self.mult_x.set(resource_dict.get(PRESET_MULT_X, res.get_mult_x()))
                self.mult_y.set(resource_dict.get(PRESET_MULT_Y, res.get_mult_y()))
                self.tol_x.set(resource_dict.get(PRESET_TOL_X, res.get_tol_x()))
                self.tol_y.set(resource_dict.get(PRESET_TOL_Y, res.get_tol_y()))
                self.want_gathering.set(resource_dict.get(PRESET_WANT_GATHERING, res.is_focus_needed))
                self.gathering_speed.set(resource_dict.get(PRESET_SPEED, GatheringSpeedLevel.FAST.name))
                self.move_back_to_start.set(resource_dict.get(PRESET_MOVE_BACK_TO_START, False))
                self.dont_move.set(resource_dict.get(PRESET_DONT_MOVE, False))
                self.adjust_dir.set(adjust_dir)
                self.adjust_every_cycle.set(resource_dict.get(PRESET_ADJUST_EVERY_CYCLE, False))
        except Exception as e:
            print(f"Error: {e}")

    def _resource_key(self):
        name = self._selected_name.get().strip()
        res: Resource = self._name_to_res.get(name)
        if res is None:
            return None
        return res.folder_name

    def _collect_current_settings(self) -> dict:
        return {
            PRESET_MULT_X: float(self.mult_x.get()),
            PRESET_MULT_Y: float(self.mult_y.get()),
            PRESET_TOL_X: int(self.tol_x.get()),
            PRESET_TOL_Y: int(self.tol_y.get()),
            PRESET_WANT_GATHERING: bool(self.want_gathering.get()),
            PRESET_DONT_MOVE: bool(self.dont_move.get()),
            PRESET_MOVE_BACK_TO_START: bool(self.move_back_to_start.get()),
            PRESET_SPEED: self.gathering_speed.get(),
            PRESET_ADJUST_DIRECTION: self.adjust_dir.get(),
            PRESET_ADJUST_EVERY_CYCLE: self.adjust_every_cycle.get(),
        }

    def _save_preset(self):
        key = self._resource_key()
        if not key:
            messagebox.showerror("No resource", "Select a resource first.")
            return

        path = _presets_path()
        data = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            except Exception:
                data = {}
        else:
            for res in Resource:
                data[res.folder_name] = res.to_json()

        data[key] = self._collect_current_settings()

        data[PRESET_ASPECT_RATIO] = self.aspect_ratio.get()
        data["_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.status.set(f"Preset saved for '{key}' → {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Save error", str(e))
