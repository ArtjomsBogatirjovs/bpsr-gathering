# autogather/ui.py
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple, List

from autogather.enums.aspect_ratio import AspectRatio
from .config import PROMPT_ROI
from .debug import save_roi_debug
from .enums.gathering_speed import GatheringSpeedLevel
from .enums.resource import Resource
from .folder_utils import scan_resources, load_resource_dir
from .screen import WindowScreen, _get_roi_f
from .winutil import list_windows, bring_to_foreground, get_window_rect
from .worker import Worker

logger = logging.getLogger(__name__)


# подобрать монитор по положению окна (fallback, если окно нельзя захватить напрямую)
def choose_monitor_index_for_window(hwnd: int) -> int:
    from mss import mss
    left, top, right, bottom = get_window_rect(hwnd)
    cx, cy = (left + right) // 2, (top + bottom) // 2
    sct = mss()
    best_idx = 1
    for idx in range(1, len(sct.monitors)):
        m = sct.monitors[idx]
        if m["left"] <= cx < m["left"] + m["width"] and m["top"] <= cy < m["top"] + m["height"]:
            best_idx = idx
            break
    return best_idx


class App:
    def __init__(self, root: tk.Tk):
        root.title("Resource AutoGather")
        self.root = root

        # --- state ---
        self.want_gathering = tk.BooleanVar(value=True)  # No-stamina mode: press only Gathering
        self.status = tk.StringVar(value="Select the 'resources' folder, choose a resource, and pick the game window.")

        self.resource = None
        self._name_to_res: dict[str, Resource] = {}
        self._selected_name = tk.StringVar(value="")

        self._win_choices: List[Tuple[str, int]] = []
        self._selected_win = tk.StringVar(value="")

        self.screen = None
        self.worker: Optional[Worker] = None
        self.ts_f = self.ts_g = self.ts_s = self.ts_r = None

        self.roi_x1 = tk.DoubleVar(value=PROMPT_ROI[0])
        self.roi_y1 = tk.DoubleVar(value=PROMPT_ROI[1])
        self.roi_x2 = tk.DoubleVar(value=PROMPT_ROI[2])
        self.roi_y2 = tk.DoubleVar(value=PROMPT_ROI[3])

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

        ttk.Label(roi_frame, text="x1:").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(roi_frame, from_=0.0, to=1.0, increment=0.01, textvariable=self.roi_x1, width=6) \
            .grid(row=0, column=1, sticky="w")

        ttk.Label(roi_frame, text="y1:").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(roi_frame, from_=0.0, to=1.0, increment=0.01, textvariable=self.roi_y1, width=6) \
            .grid(row=0, column=3, sticky="w")

        ttk.Label(roi_frame, text="x2:").grid(row=1, column=0, sticky="w")
        ttk.Spinbox(roi_frame, from_=0.0, to=1.0, increment=0.01, textvariable=self.roi_x2, width=6) \
            .grid(row=1, column=1, sticky="w")

        ttk.Label(roi_frame, text="y2:").grid(row=1, column=2, sticky="w")
        ttk.Spinbox(roi_frame, from_=0.0, to=1.0, increment=0.01, textvariable=self.roi_y2, width=6) \
            .grid(row=1, column=3, sticky="w")

        ttk.Label(roi_frame, text="Aspect ratio:").grid(row=2, column=0, sticky="w")
        aspect_cb = ttk.Combobox(
            roi_frame,
            textvariable=self.aspect_ratio,
            values=[str(r) for r in AspectRatio],
            state="readonly",
            width=6
        )
        aspect_cb.grid(row=2, column=1, sticky="w")

        ttk.Button(roi_frame, text="Capture [F] snapshot", command=self.debug_roi) \
            .grid(row=3, column=0, columnspan=4, sticky="ew", pady=(8, 0))

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

    def debug_roi(self):
        """Сохранить картинку с выделенным ROI."""
        if not self.screen:
            hwnd = self._selected_hwnd()
            if not hwnd:
                messagebox.showerror("Нет окна", "Выбери целевое окно игры из списка.")
                return
            self.screen = WindowScreen(hwnd)

        roi_val = (float(self.roi_x1.get()), float(self.roi_y1.get()), float(self.roi_x2.get()),
                   float(self.roi_y2.get()))
        roi, roi_tuple = _get_roi_f(self.screen, self.get_selected_aspect_ratio(), roi_val)
        save_roi_debug(self.screen.grab_bgr(), roi_tuple)
        self.status.set("ROI-снимок сохранён (roi_debug.png)")

    def rescan(self):
        _resources = scan_resources()
        self._name_to_res = {res.display_name: res for res in _resources}

        names = list(self._name_to_res.keys())
        self.cmb["values"] = names

        if names:
            cur = self._selected_name.get()
            if cur not in names:
                self._selected_name.set(names[0])
            self.status.set(f"Found {len(names)} resources.")
        else:
            self._selected_name.set("")
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

        # ресурс
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
            resource_enum,
            self.run_back_to_start.get()
        )
        self.worker.start()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status.set(f"Запущено: {name} | окно: {self._selected_win.get()}")

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status.set("Остановлено.")

    # -------- статус-луп --------
    def _tick(self):
        if self.worker:
            self.status.set(f"Состояние: {self.worker.state}")
        self.root.after(150, self._tick)
