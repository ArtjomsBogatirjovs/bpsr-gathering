# fishing/ui.py
import logging
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple, List

from fishing.AspectRatio import AspectRatio
from fishing.screen import WindowScreen
from fishing.winutil import get_window_rect, list_windows, bring_to_foreground
from fishing.worker import Worker

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
        root.title("AutoFishing — Window Picker")
        self.root = root

        # --- состояние ---
        self.status = tk.StringVar(value="Выбери окно игры, наживку и жми Старт.")
       # self.worker: Optional[Worker] = None

        # выбор целевого окна
        self._win_choices: List[Tuple[str, int]] = []  # (display_title, hwnd)
        self._selected_win = tk.StringVar(value="")

        # параметры рыбалки
        self.change_rod = tk.BooleanVar(value=False)        # Менять удочку автоматически
        self.auto_buy_rod = tk.BooleanVar(value=False)      # Покупать удочку при необходимости
        self.bait_type = tk.StringVar(value="Червь")        # Вид наживки

        # --- UI-каркас ---
        frm = ttk.Frame(root, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # ============================
        # ГЛАВНЫЙ БЛОК: Управление рыбалкой
        fish_frame = ttk.LabelFrame(frm, text="Рыбалка — управление", padding=10)
        fish_frame.grid(row=0, column=0, sticky="nsew")

        # строка 0: выбор окна
        ttk.Label(fish_frame, text="Целевое окно (игра):").grid(row=0, column=0, sticky="w")
        self.win_cmb = ttk.Combobox(
            fish_frame, textvariable=self._selected_win, values=[], state="readonly", width=40
        )
        self.win_cmb.grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(fish_frame, text="Обновить окна", command=self.refresh_windows).grid(row=0, column=2, padx=4)

        # строка 1: вид наживки
        ttk.Label(fish_frame, text="Вид наживки:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.bait_cmb = ttk.Combobox(
            fish_frame,
            textvariable=self.bait_type,
            values=["Червь", "Мотыль", "Кукуруза", "Муха", "Тесто", "Случайная"],
            state="readonly",
            width=20
        )
        self.bait_cmb.grid(row=1, column=1, sticky="w", padx=6, pady=(6, 0))

        # строка 2: чекбоксы
        ttk.Checkbutton(
            fish_frame,
            text="Менять удочку автоматически",
            variable=self.change_rod
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))

        ttk.Checkbutton(
            fish_frame,
            text="Покупать удочку при необходимости",
            variable=self.auto_buy_rod
        ).grid(row=3, column=0, columnspan=3, sticky="w")

        # строка 3: кнопки старт/стоп
        self.btn_start = ttk.Button(fish_frame, text="▶ Старт", command=self.start)
        self.btn_start.grid(row=4, column=0, pady=(10, 4), sticky="w")

        self.btn_stop = ttk.Button(fish_frame, text="■ Стоп", command=self.stop, state="disabled")
        self.btn_stop.grid(row=4, column=1, pady=(10, 4), sticky="w")

        # строка 4: статус
        ttk.Label(fish_frame, textvariable=self.status, foreground="#666").grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

        # растяжение колонок
        fish_frame.columnconfigure(1, weight=1)
        frm.columnconfigure(0, weight=1)

        # ============================
        # Инициализация
        self.refresh_windows()   # заполнит комбобокс окнами
        # если у тебя есть периодический тик — оставь:
        if hasattr(self, "_tick"):
            self._tick()

    def get_selected_aspect_ratio(self) -> AspectRatio:
        value = self.aspect_ratio.get()
        for ratio in AspectRatio:
            if str(ratio) == value:
                return ratio
        raise ValueError(f"Unknown aspect ratio: {value}")

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
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", str(e))
            return

        # Запуск воркера
        self.worker = Worker(
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
