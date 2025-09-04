# autogather/ui.py
import logging
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple, List

from .config import RESOURCES_ROOT_DEFAULT, PITCH_OFFSET_DEFAULT
from .input_sim import move_mouse_rel, move_mouse_abs
from .screen import WindowScreen, Screen
from .templates import scan_resources, load_resource_dir
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
        root.title("AutoGather — Window Picker")
        self.root = root

        # --- состояние ---
        self.want_gathering = tk.BooleanVar(value=True)  # «Без стамины»
        self.resources_root = tk.StringVar(value=RESOURCES_ROOT_DEFAULT)
        self.pitch_offset = tk.IntVar(value=PITCH_OFFSET_DEFAULT)
        self.status = tk.StringVar(value="Укажи папку resources, выбери ресурс и окно игры.")

        self._resources: List[Tuple[str, str]] = []  # (display_name, path)
        self._name_to_path: dict[str, str] = {}
        self._selected_name = tk.StringVar(value="")

        self._win_choices: List[Tuple[str, int]] = []  # (display_title, hwnd)
        self._selected_win = tk.StringVar(value="")

        self.screen = None
        self.worker: Optional[Worker] = None
        self.ts_f = self.ts_g = self.ts_s = None

        # --- UI ---
        frm = ttk.Frame(root, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # Ресурс
        ttk.Label(frm, text="Ресурс:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.cmb = ttk.Combobox(frm, textvariable=self._selected_name, values=[], state="readonly", width=32)
        self.cmb.grid(row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=(6, 0))

        # Окно игры (выбор из списка)
        ttk.Label(frm, text="Целевое окно:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.win_cmb = ttk.Combobox(frm, textvariable=self._selected_win, values=[], state="readonly", width=40)
        self.win_cmb.grid(row=2, column=1, columnspan=2, sticky="ew", padx=6, pady=(6, 0))
        ttk.Button(frm, text="Обновить окна", command=self.refresh_windows).grid(row=2, column=3, sticky="w",
                                                                                 pady=(6, 0))

        # Настройки
        ttk.Label(frm, text="Отклонение по Y (px):").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(frm, from_=0, to=8000, textvariable=self.pitch_offset, width=8) \
            .grid(row=3, column=1, sticky="w", pady=(6, 0))

        ttk.Checkbutton(frm, text="Без стамины → нажимать только Gathering", variable=self.want_gathering) \
            .grid(row=4, column=0, columnspan=4, sticky="w", pady=(6, 2))

        # Кнопки управления
        self.btn_start = ttk.Button(frm, text="▶ Старт", command=self.start)
        self.btn_start.grid(row=5, column=0, sticky="ew", pady=(10, 4))
        self.btn_stop = ttk.Button(frm, text="■ Стоп", command=self.stop, state="disabled")
        self.btn_stop.grid(row=5, column=1, sticky="ew", pady=(10, 4))

        ttk.Label(frm, textvariable=self.status, foreground="#666").grid(row=6, column=0, columnspan=4, sticky="w",
                                                                         pady=(8, 0))
        for c in range(1, 4):
            frm.columsnconfigure(c, weight=1)

        # Инициализация
        self.rescan()
        self.refresh_windows()
        self._tick()

    def rescan(self):
        root_dir = self.resources_root.get().strip()
        self._resources = scan_resources(root_dir)
        self._name_to_path = {name: path for name, path in self._resources}
        names = [name for name, _ in self._resources]
        self.cmb["values"] = names
        if names:
            if self._selected_name.get() not in names:
                self._selected_name.set(names[0])
            self.status.set(f"Нашёл {len(names)} ресурс(а).")
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

    def calibrate_pitch(self):
        """Ставим курсор в центр окна игры, затем опускаем камеру на заданное кол-во пикселей мелкими шагами."""
        try:
            hwnd = self._selected_hwnd()
            if not hwnd:
                return
            left, top, right, bottom = get_window_rect(hwnd)
            cx = (left + right) // 2
            cy = (top + bottom) // 2
            logger.debug(
                f"calibrate_pitch: hwnd={hwnd}, rect=({left},{top},{right},{bottom}), "
                f"center=({cx},{cy}), offsetY={top}"
            )

            move_mouse_abs(cx, cy)
            logger.debug(f"Moved mouse to absolute center ({cx},{cy})")
            time.sleep(5)
            move_mouse_rel(dx = 0,dy=top * 5)
            time.sleep(5)
            move_mouse_rel(dx = 0,dy=-int(self.pitch_offset.get() if hasattr(self, "pitch_offset") else PITCH_OFFSET_DEFAULT))
            logger.debug(f"Moved mouse relative by ({0},-{top/4})")
        except Exception:
            logger.debug(f"Moved mouse relative by ({0},-{Exception})")
            pass

    # -------- старт/стоп --------
    def start(self):
        if self.worker and self.worker.is_alive():
            return

        # ресурс
        name = self._selected_name.get().strip()
        if not name or name not in self._name_to_path:
            messagebox.showerror("Нет ресурса", "Выбери ресурс из списка.")
            return
        resource_dir = self._name_to_path[name]
        try:
            self.ts_f, self.ts_g, self.ts_s = load_resource_dir(resource_dir)
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", str(e))
            return
        if not (self.ts_f.tmps and self.ts_g.tmps and self.ts_s.tmps):
            messagebox.showerror("Нет шаблонов", "В одной из подпапок нет изображений.")
            return

        # целевое окно
        hwnd = self._selected_hwnd()
        if not hwnd:
            messagebox.showerror("Нет окна", "Выбери целевое окно игры из списка.")
            return

        # Поднять окно в фореграунд для стабильного захвата/ввода
        try:
            bring_to_foreground(hwnd)
        except Exception:
            pass

        # Захват именно окна (fallback — монитор, где окно)
        try:
            self.screen = WindowScreen(hwnd)
            if self.screen.grab_bgr() is None:
                mon_idx = choose_monitor_index_for_window(hwnd)
                self.screen = Screen(monitor_index=mon_idx)
        except Exception:
            mon_idx = choose_monitor_index_for_window(hwnd)
            self.screen = Screen(monitor_index=mon_idx)

        #self.calibrate_pitch()

        # Запуск воркера
        self.worker = Worker(
            self.screen,
            self.ts_f, self.ts_g, self.ts_s,
            self.want_gathering.get(),
            hwnd=hwnd,
            resource_dir=self._name_to_path[name]  # <--- ВАЖНО
        )
        self.worker.start()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status.set(f"Запущено: {name} | окно: {self._selected_win.get()}")
        #self.stop()#TODO

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
