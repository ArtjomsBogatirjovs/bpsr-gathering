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

        # new: gathering speed level
        self.gathering_speed = tk.StringVar(value=GatheringSpeedLevel.FAST.name)

        # new: run back to start after gathering
        self.run_back_to_start = tk.BooleanVar(value=False)

        # --- UI ---
        frm = ttk.Frame(root, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # ============================
        # TOP BLOCK: Main settings
        main_frame = ttk.LabelFrame(frm, text="Main settings", padding=10)
        main_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Label(main_frame, text="Resource:").grid(row=0, column=0, sticky="w")
        self.cmb = ttk.Combobox(main_frame, textvariable=self._selected_name, values=[], state="readonly", width=32)
        self.cmb.grid(row=0, column=1, columnspan=2, sticky="ew", padx=6)

        ttk.Label(main_frame, text="Target window:").grid(row=1, column=0, sticky="w")
        self.win_cmb = ttk.Combobox(main_frame, textvariable=self._selected_win, values=[], state="readonly", width=40)
        self.win_cmb.grid(row=1, column=1, sticky="ew", padx=6)
        ttk.Button(main_frame, text="Refresh windows", command=self.refresh_windows).grid(row=1, column=2, padx=4)

        # new: gathering speed combobox (row=2)
        ttk.Label(main_frame, text="Gathering speed:").grid(row=2, column=0, sticky="w")
        self.speed_cmb = ttk.Combobox(
            main_frame,
            state="readonly",
            width=12,
            textvariable=self.gathering_speed,
            values=[level.name for level in GatheringSpeedLevel],  # shows SLOW / NORMAL / FAST
        )
        self.speed_cmb.grid(row=2, column=1, sticky="w", padx=6)

        # --- Resource params (row=6..7) ---
        ttk.Label(main_frame, text="mult_x:").grid(row=6, column=0, sticky="w")
        ttk.Spinbox(main_frame, from_=0.0, to=10.0, increment=0.1,
                    textvariable=self.mult_x, width=8).grid(row=6, column=1, sticky="w", padx=6)

        ttk.Label(main_frame, text="mult_y:").grid(row=6, column=2, sticky="w")
        ttk.Spinbox(main_frame, from_=0.0, to=10.0, increment=0.1,
                    textvariable=self.mult_y, width=8).grid(row=6, column=3, sticky="w", padx=6)

        ttk.Label(main_frame, text="tol_x:").grid(row=7, column=0, sticky="w")
        ttk.Spinbox(main_frame, from_=0, to=500, increment=1,
                    textvariable=self.tol_x, width=8).grid(row=7, column=1, sticky="w", padx=6)

        ttk.Label(main_frame, text="tol_y:").grid(row=7, column=2, sticky="w")
        ttk.Spinbox(main_frame, from_=0, to=500, increment=1,
                    textvariable=self.tol_y, width=8).grid(row=7, column=3, sticky="w", padx=6)

        self.cmb.bind("<<ComboboxSelected>>", self._on_resource_selected)

        ttk.Checkbutton(
            main_frame,
            text="No-stamina mode → press only “Gathering”",
            variable=self.want_gathering
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(6, 2))

        self.btn_start = ttk.Button(main_frame, text="▶ Start", command=self.start)
        self.btn_start.grid(row=4, column=0, pady=(10, 4))
        self.btn_stop = ttk.Button(main_frame, text="■ Stop", command=self.stop, state="disabled")
        self.btn_stop.grid(row=4, column=1, pady=(10, 4))

        ttk.Label(main_frame, textvariable=self.status, foreground="#666") \
            .grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))

        # ============================
        # LOWER BLOCKS
        roi_frame = ttk.LabelFrame(frm, text="ROI setup (prompt [F])", padding=10)
        roi_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        ttk.Label(roi_frame, text="Aspect ratio:").grid(row=2, column=0, sticky="w")
        aspect_cb = ttk.Combobox(
            roi_frame,
            textvariable=self.aspect_ratio,
            values=[str(r) for r in AspectRatio],
            state="readonly",
            width=6
        )
        aspect_cb.grid(row=2, column=1, sticky="w")

        # Advanced
        extra_frame = ttk.LabelFrame(frm, text="Advanced", padding=10)
        extra_frame.grid(row=1, column=1, sticky="nsew")

        # new: run back to start checkbox
        ttk.Checkbutton(
            extra_frame,
            text="Run back to start after gathering",
            variable=self.run_back_to_start
        ).grid(row=0, column=0, sticky="w")

        frm.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)

        # ============================
        # Initialization
        self.rescan()
        self.refresh_windows()
        self._tick()

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
            self.status.set(f"Нашёл окон: {len(arr)}")
        else:
            self._selected_win.set("")
            self.status.set("Окна не найдены. Открой игру в окне/borderless.")

    def _selected_hwnd(self) -> Optional[int]:
        disp = self._selected_win.get().strip()
        for t, h in self._win_choices:
            if t == disp:
                return h
        return None

    # -------- старт/стоп --------
    def start(self):
        if self.worker and self.worker.is_alive():
            return

        name = self._selected_name.get().strip()
        if not name or name not in self._name_to_res:
            messagebox.showerror("Нет ресурса", "Выбери ресурс из списка.")
            return
        resource_enum = self._name_to_res[name]
        try:
            self.ts_f, self.ts_g, self.ts_s, self.ts_r = load_resource_dir(resource_enum.folder_name, resource_enum)
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", str(e))
            return
        if not (self.ts_g.tmps and self.ts_s.tmps) or (not self.ts_f.tmps and resource_enum.is_focus_needed):
            messagebox.showerror("Нет шаблонов", "В одной из подпапок нет изображений.")
            return

        hwnd = self._selected_hwnd()
        if not hwnd:
            messagebox.showerror("Нет окна", "Выбери целевое окно игры из списка.")
            return

        try:
            bring_to_foreground(hwnd)
        except Exception:
            pass

        try:
            self.screen = WindowScreen(hwnd)
        except Exception as e:
            messagebox.showerror("Error screen loading", str(e))
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
        self.status.set(f"Запущено: {name} | окно: {self._selected_win.get()}")

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
