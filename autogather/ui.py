# autogather/ui.py
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple, List

from autogather.enums.aspect_ratio import AspectRatio
from autogather.model.worker import Worker
from .enums.gathering_speed import GatheringSpeedLevel
from .enums.resource import Resource, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y
from .folder_utils import scan_resources, load_resource_dir
from .model.resource_model import ResourceObject
from .screen import WindowScreen
from .winutil import list_windows, bring_to_foreground

logger = logging.getLogger(__name__)


class App:
    def __init__(self, root: tk.Tk):
        root.title("Resource AutoGather")
        self.root = root

        # --- state ---
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

        self.aspect_ratio = tk.StringVar(value=str(AspectRatio.RATIO_21_9))
        self.gathering_speed = tk.StringVar(value=GatheringSpeedLevel.FAST.name)
        self.run_back_to_start = tk.BooleanVar(value=False)

        # build UI (new)
        self._build_ui()

        # bindings
        self.cmb.bind("<<ComboboxSelected>>", self._on_resource_selected)

        # init
        self.rescan()
        self.refresh_windows()
        self._tick()

    def _build_ui(self):
        PAD, GUT = 12, 8

        # base frame
        frm = ttk.Frame(self.root, padding=PAD)
        frm.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)

        # ========== LEFT COLUMN ==========
        # Resource block
        resource_frame = ttk.LabelFrame(frm, text="Resource", padding=PAD)
        resource_frame.grid(row=0, column=0, sticky="nsew", padx=(0, GUT))
        resource_frame.columnconfigure(1, weight=1)

        ttk.Label(resource_frame, text="Resource:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.cmb = ttk.Combobox(resource_frame, textvariable=self._selected_name, state="readonly", width=28, values=[])
        self.cmb.grid(row=0, column=1, sticky="ew", padx=(6,0), pady=(0, 4))

        ttk.Checkbutton(
            resource_frame,
            text="No-stamina mode (press only “Gathering”)",
            variable=self.want_gathering
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4,0))

        ttk.Checkbutton(
            resource_frame,
            text="Run back to start after gathering",
            variable=self.run_back_to_start
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4,0))

        # Parameters block
        params_frame = ttk.LabelFrame(frm, text="Parameters", padding=PAD)
        params_frame.grid(row=1, column=0, sticky="nsew", padx=(0, GUT), pady=(GUT, 0))
        for c in range(4):
            params_frame.columnconfigure(c, weight=1)

        # row 0: multipliers
        ttk.Label(params_frame, text="X multiplier").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(params_frame, from_=0.0, to=10.0, increment=0.1, width=8,
                    textvariable=self.mult_x).grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(params_frame, text="Y multiplier").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(params_frame, from_=0.0, to=10.0, increment=0.1, width=8,
                    textvariable=self.mult_y).grid(row=0, column=3, sticky="w", padx=(6, 0))

        # row 1: tolerances
        ttk.Label(params_frame, text="X tolerance").grid(row=1, column=0, sticky="w", pady=(6,0))
        ttk.Spinbox(params_frame, from_=0, to=1000, increment=1, width=8,
                    textvariable=self.tol_x).grid(row=1, column=1, sticky="w", padx=(6, 12), pady=(6,0))
        ttk.Label(params_frame, text="Y tolerance").grid(row=1, column=2, sticky="w", pady=(6,0))
        ttk.Spinbox(params_frame, from_=0, to=1000, increment=1, width=8,
                    textvariable=self.tol_y).grid(row=1, column=3, sticky="w", padx=(6, 0), pady=(6,0))

        # row 2: speed
        ttk.Label(params_frame, text="Gathering speed").grid(row=2, column=0, sticky="w", pady=(10,0))
        self.speed_cmb = ttk.Combobox(params_frame, state="readonly", width=14,
                                      textvariable=self.gathering_speed,
                                      values=[level.name for level in GatheringSpeedLevel])
        self.speed_cmb.grid(row=2, column=1, sticky="w", padx=(6,0), pady=(10,0))

        # ========== RIGHT COLUMN ==========
        # Window block
        window_frame = ttk.LabelFrame(frm, text="Window", padding=PAD)
        window_frame.grid(row=0, column=1, sticky="nsew")
        window_frame.columnconfigure(1, weight=1)

        ttk.Label(window_frame, text="Target window").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.win_cmb = ttk.Combobox(window_frame, textvariable=self._selected_win, state="readonly", width=36, values=[])
        self.win_cmb.grid(row=0, column=1, sticky="ew", padx=(6,0), pady=(0, 4))
        ttk.Button(window_frame, text="Refresh", command=self.refresh_windows) \
            .grid(row=0, column=2, sticky="e", padx=(6,0))

        ttk.Label(window_frame, text="Aspect ratio").grid(row=1, column=0, sticky="w", pady=(8,0))
        aspect_cb = ttk.Combobox(window_frame, textvariable=self.aspect_ratio,
                                 values=[str(r) for r in AspectRatio],
                                 state="readonly", width=10)
        aspect_cb.grid(row=1, column=1, sticky="w", padx=(6,0), pady=(8,0))

        # Actions block
        actions_frame = ttk.LabelFrame(frm, text="Actions", padding=PAD)
        actions_frame.grid(row=1, column=1, sticky="nsew", pady=(GUT, 0))
        actions_frame.columnconfigure(0, weight=0)
        actions_frame.columnconfigure(1, weight=1)

        self.btn_start = ttk.Button(actions_frame, text="▶ Start", command=self.start, width=12)
        self.btn_start.grid(row=0, column=0, sticky="w")

        self.btn_stop = ttk.Button(actions_frame, text="■ Stop", command=self.stop, state="disabled", width=12)
        self.btn_stop.grid(row=0, column=1, sticky="w", padx=(8,0))

        ttk.Separator(actions_frame, orient="horizontal").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10,6))

        ttk.Label(actions_frame, textvariable=self.status, foreground="#666") \
            .grid(row=2, column=0, columnspan=2, sticky="w")


    def get_gathering_speed(self) -> GatheringSpeedLevel:
        return GatheringSpeedLevel[self.gathering_speed.get()]

    def get_selected_aspect_ratio(self) -> AspectRatio:
        value = self.aspect_ratio.get()
        for ratio in AspectRatio:
            if str(ratio) == value:
                return ratio
        raise ValueError(f"Unknown aspect ratio: {value}")

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
            self.status.set("В корне нет валидных ресурсов (нужны focused/gathering/selector).")

    # -------- окна --------
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
            self.run_back_to_start.get()
        )
        self.worker.start()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status.set(f"Started: {name} | Window: {self._selected_win.get()}")


    def create_resource(self):
        return ResourceObject(self.resource.folder_name, self.mult_x.get(), self.mult_y.get(), self.tol_x.get(),
                              self.tol_y.get(), self.resource.is_focus_needed)

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status.set("Stopped.")

    # -------- статус-луп --------
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
        try:
            self.mult_x.set(res.get_mult_x() if hasattr(res, "get_mult_x") else getattr(res, "mult_x", 1.0))
            self.mult_y.set(res.get_mult_y() if hasattr(res, "get_mult_y") else getattr(res, "mult_y", 1.0))
            self.tol_x.set(res.get_tol_x() if hasattr(res, "get_tol_x") else getattr(res, "tol_x", DEFAULT_TOLERANCE_X))
            self.tol_y.set(res.get_tol_y() if hasattr(res, "get_tol_y") else getattr(res, "tol_y", DEFAULT_TOLERANCE_Y))
        except Exception as e:
            print(f"Error: {e}")
