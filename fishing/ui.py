# fishing/ui.py
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple, List

from fishing.folder_utils import scan_baits
from fishing.screen import WindowScreen
from fishing.winutil import list_windows, bring_to_foreground
from fishing.worker import Worker

logger = logging.getLogger(__name__)

class App:
    def __init__(self, root: tk.Tk):
        self.worker = None
        root.title("AutoFishing — Window Picker")
        self.root = root

        # --- состояние ---
        self.status = tk.StringVar(value="Выбери окно игры, наживку и жми Старт.")
       # self.worker: Optional[Worker] = None

        # выбор целевого окна
        self._win_choices: List[Tuple[str, int]] = []  # (display_title, hwnd)
        self._selected_win = tk.StringVar(value="")

        # параметры рыбалки
        self.change_rod = tk.BooleanVar(value=False)
        self.auto_buy_rod = tk.BooleanVar(value=False)
        self.bait_type = tk.StringVar(value="")
        self._bait_name_to_path: dict[str, str] = {}

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
            values=[],
            state="readonly",
            width=28
        )
        self.bait_cmb.grid(row=1, column=1, sticky="ew", padx=6, pady=(6, 0))
        self.bait_cmb.bind("<<ComboboxSelected>>", lambda e: None)

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
        self.refresh_windows()
        self.rescan_baits()

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
        self.worker = Worker(self.screen, self.change_rod.get(), self.auto_buy_rod.get())
        self.worker.start()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")

    def rescan_baits(self):
        try:
            items = scan_baits()
        except Exception as e:
            items = []
            print(f"[baits] scan error: {e}")

        self._bait_name_to_path = {name: path for name, path in items}
        names = list(self._bait_name_to_path.keys())

        self.bait_cmb["values"] = names

        current = self.bait_type.get()
        if current in names:
            pass
        else:
            if names:
                self.bait_type.set(names[0])
            else:
                self.bait_type.set("")

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

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status.set("Остановлено.")
