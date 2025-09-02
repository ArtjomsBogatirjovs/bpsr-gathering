# mini_gather.py — v2
# Поведение:
#  - Если "Без стамины" ВКЛ: крутим медленно вниз, пока [F] не будет ближе к Gathering, чем к Focused; затем жмём F.
#  - Если "Без стамины" ВЫКЛ: жмём F сразу, как только видим подсказки.

import os
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import cv2
import numpy as np
from mss import mss

# ===== Ввод: F через DirectInput; скролл — через pyautogui =====
try:
    import pydirectinput as pdi  # клавиши
except Exception:
    pdi = None
import pyautogui as pag  # скролл

pag.PAUSE = 0
pag.FAILSAFE = True


def press_key(k: str):
    if pdi:
        pdi.press(k)
    else:
        pag.press(k)


# ===== Настройки матчинга/скролла =====
PROMPTS_DIR = "templates/prompts"

ROI_RIGHT_FRACTION = 0.50  # правая половина экрана
MATCH_THRESHOLD = 0.56
SCALES = [0.70, 0.80, 0.90, 1.00, 1.12, 1.25, 1.40]

SCROLL_UNIT = -120  # одно деление колёсика (Windows обычно 120)
SCROLL_DELAY = 0.25  # пауза между шагаим скролла (медленнее)
MAX_SCROLL_STEPS = 10  # максимум шагов, чтобы не зациклиться
ALIGN_TOLERANCE = 16  # допуск по вертикали (px)
ACTION_COOLDOWN = 1.0
AFTER_F_SLEEP = 6.0  # секунд – пауза после нажатия F (копаем)


# ===== Экран (thread-local) =====
class Screen:
    def __init__(self, monitor_index=1):
        self.monitor_index = int(monitor_index)
        self._tls = threading.local()

    def _sct(self):
        if not hasattr(self._tls, "sct"):
            self._tls.sct = mss()
        return self._tls.sct

    def _mon(self):
        s = self._sct()
        return s.monitors[self.monitor_index] if len(s.monitors) > self.monitor_index else s.monitors[0]

    def grab_bgr(self):
        s = self._sct();
        m = self._mon()
        return np.array(s.grab(m))[:, :, :3]

    def dims(self):
        m = self._mon()
        return m["width"], m["height"]


# ===== Простой набор шаблонов =====
class TemplateSet:
    def __init__(self, paths):
        self.tmps = []
        for p in paths:
            if os.path.isfile(p):
                g = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
                if g is not None and g.size > 0:
                    self.tmps.append(g)

    def match(self, gray_roi):
        """Лучшее совпадение: {'score', 'box':((x1,y1),(x2,y2))} или None"""
        best = None
        H, W = gray_roi.shape[:2]
        for g in self.tmps:
            for s in SCALES:
                tw, th = int(g.shape[1] * s), int(g.shape[0] * s)
                if tw < 12 or th < 12 or tw >= W or th >= H:
                    continue
                t = cv2.resize(g, (tw, th), interpolation=cv2.INTER_AREA)
                res = cv2.matchTemplate(gray_roi, t, cv2.TM_CCOEFF_NORMED)
                _, mx, _, ml = cv2.minMaxLoc(res)
                if mx >= MATCH_THRESHOLD:
                    tl = (ml[0], ml[1]);
                    br = (tl[0] + tw, tl[1] + th)
                    cand = {"score": float(mx), "box": (tl, br)}
                    if not best or cand["score"] > best["score"]:
                        best = cand
        return best


# ===== Логика работника =====
class Worker(threading.Thread):

    def hold_after_press(self, seconds: float = AFTER_F_SLEEP):
        """
        Блокирующая пауза после нажатия F.
        Можно вызывать в любом месте, пока идёт добыча.
        Учитывает сигнал остановки и показывает обратный отсчёт в self.state.
        """
        end = time.time() + seconds
        # фиксируем момент действия, чтобы прошёл cooldown
        self._last = time.time()
        while not self._stop.is_set():
            left = end - time.time()
            if left <= 0:
                break
            self.state = f"mining… {left:.1f}s"
            time.sleep(min(0.2, left))

    def __init__(self, screen, ts_f, ts_g, ts_sel, want_gathering: bool):
        super().__init__(daemon=True)
        self.screen = screen
        self.ts_f = ts_f
        self.ts_g = ts_g
        self.ts_sel = ts_sel
        self.want_gathering = want_gathering
        self._stop = threading.Event()
        self.state = "idle"
        self._last = 0.0

    def stop(self):
        self._stop.set()

    def cooldown(self):
        return (time.time() - self._last) > ACTION_COOLDOWN

    def _roi(self, gray):
        h, w = gray.shape[:2]
        x0 = int(w * (1.0 - ROI_RIGHT_FRACTION))
        return gray[:, x0:], x0

    @staticmethod
    def _y_center(box):  # центр по вертикали
        (x1, y1), (x2, y2) = box
        return (y1 + y2) // 2

    def _aligned_to_gathering(self, roi, hit_f, hit_g, hit_sel):
        """true, если [F] ближе к строке Gathering, чем к Focused (с допуском)."""
        if not (hit_g and hit_sel):
            return False
        ys = self._y_center(hit_sel["box"])
        yg = self._y_center(hit_g["box"])
        df = 10 ** 9
        if hit_f:
            yf = self._y_center(hit_f["box"])
            df = abs(ys - yf)
        dg = abs(ys - yg)
        return dg + ALIGN_TOLERANCE < df

    def run(self):
        while not self._stop.is_set():
            frame = self.screen.grab_bgr()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            roi, x0 = self._roi(gray)

            hit_f = self.ts_f.match(roi)
            hit_g = self.ts_g.match(roi)
            hit_sel = self.ts_sel.match(roi)

            if not (hit_f or hit_g):
                self.state = "wait"
                time.sleep(0.10)
                continue

            if not self.cooldown():
                self.state = "cooldown"
                time.sleep(0.05)
                continue

            if not self.want_gathering:
                # стамина разрешена — жмём F сразу
                self.state = "press F (any)"
                press_key('f')
                self._last = time.time()
                self.hold_after_press()
                continue

            # Нужно именно Gathering: крутим пока [F] ближе к Gathering
            steps = 0
            # свежие значения уже есть
            while not self._aligned_to_gathering(roi, hit_f, hit_g, hit_sel) and steps < MAX_SCROLL_STEPS:
                self.state = "scroll…"
                pag.scroll(SCROLL_UNIT)  # один «клик» колеса вниз
                time.sleep(SCROLL_DELAY)
                # перехватываем новые совпадения
                frame = self.screen.grab_bgr()
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                roi, x0 = self._roi(gray)
                hit_f = self.ts_f.match(roi)
                hit_g = self.ts_g.match(roi)
                hit_sel = self.ts_sel.match(roi)
                steps += 1

            if self._aligned_to_gathering(roi, hit_f, hit_g, hit_sel):
                self.state = "press F (Gathering)"
                press_key('f')
                self._last = time.time()
                self.hold_after_press()
            else:
                self.state = "not aligned"
                time.sleep(0.10)


# ===== UI =====
class App:
    def __init__(self, root):
        root.title("Mini Gather — Luna Ore")
        self.monitor = tk.IntVar(value=1)
        self.no_stamina = tk.BooleanVar(value=True)  # хотим Gathering
        self.dir_var = tk.StringVar(value=PROMPTS_DIR)
        self.status = tk.StringVar(value="Ожидание…")

        frm = ttk.Frame(root, padding=12);
        frm.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1);
        root.rowconfigure(0, weight=1)

        ttk.Label(frm, text="Папка шаблонов:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.dir_var).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(frm, text="Обзор…", command=self.pick_dir).grid(row=0, column=2, sticky="w")

        ttk.Checkbutton(frm, text="Без стамины → нажимать только Gathering", variable=self.no_stamina) \
            .grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 2))

        ttk.Label(frm, text="Монитор (mss index):").grid(row=2, column=0, sticky="w")
        tk.Spinbox(frm, from_=1, to=6, textvariable=self.monitor, width=6).grid(row=2, column=1, sticky="w", padx=6)

        self.btn_start = ttk.Button(frm, text="▶ Старт", command=self.start);
        self.btn_start.grid(row=3, column=0, sticky="ew", pady=(10, 4))
        self.btn_stop = ttk.Button(frm, text="■ Стоп", command=self.stop, state="disabled");
        self.btn_stop.grid(row=3, column=1, sticky="ew", pady=(10, 4))

        ttk.Button(frm, text="Debug-снимок → debug_prompt.png", command=self.debug_snap).grid(row=4, column=0,
                                                                                              columnspan=3, sticky="ew",
                                                                                              pady=(2, 4))
        ttk.Label(frm, textvariable=self.status, foreground="#666").grid(row=5, column=0, columnspan=3, sticky="w",
                                                                         pady=(8, 0))
        frm.columnconfigure(1, weight=1)

        self.screen = None;
        self.worker = None
        self.ts_f = self.ts_g = self.ts_sel = None
        self._tick(root)

    def pick_dir(self):
        d = filedialog.askdirectory(title="Папка с шаблонами",
                                    initialdir=self.dir_var.get() if os.path.isdir(self.dir_var.get()) else ".")
        if d: self.dir_var.set(d)

    def _load_templates(self):
        d = self.dir_var.get()
        need = ["focused.png", "gathering.png", "selector.png"]
        missing = [n for n in need if not os.path.isfile(os.path.join(d, n))]
        if missing:
            messagebox.showerror("Нет шаблонов", f"В папке {d} нет файлов: {', '.join(missing)}")
            return False
        self.ts_f = TemplateSet([os.path.join(d, "focused.png")])
        self.ts_g = TemplateSet([os.path.join(d, "gathering.png")])
        self.ts_sel = TemplateSet([os.path.join(d, "selector.png")])
        return True

    def start(self):
        if self.worker and self.worker.is_alive(): return
        if not self._load_templates(): return
        self.screen = Screen(monitor_index=self.monitor.get())
        self.worker = Worker(self.screen, self.ts_f, self.ts_g, self.ts_sel, self.no_stamina.get())
        self.worker.start()
        self.btn_start.configure(state="disabled");
        self.btn_stop.configure(state="normal")
        self.status.set("Запущено. Перейди в игру (Borderless/Windowed).")

    def stop(self):
        if self.worker: self.worker.stop(); self.worker = None
        self.btn_start.configure(state="normal");
        self.btn_stop.configure(state="disabled")
        self.status.set("Остановлено.")

    def debug_snap(self):
        try:
            if not self._load_templates(): return
            sc = self.screen or Screen(monitor_index=self.monitor.get())
            frame = sc.grab_bgr()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape[:2];
            x0 = int(w * (1.0 - ROI_RIGHT_FRACTION))
            roi = gray[:, x0:]

            def draw(ts, color):
                hit = ts.match(roi)
                if hit:
                    (x1, y1), (x2, y2) = hit["box"]
                    cv2.rectangle(frame, (x0 + x1, y1), (x0 + x2, y2), color, 2)
                return hit

            hf = draw(self.ts_f, (0, 255, 0))
            hg = draw(self.ts_g, (255, 0, 0))
            hs = draw(self.ts_sel, (0, 255, 255))
            cv2.rectangle(frame, (x0, 0), (w, h), (200, 200, 0), 2)
            cv2.imwrite("debug_prompt.png", frame)
            msg = ["debug_prompt.png сохранён.",
                   f"Focused: {'ok' if hf else '—'}",
                   f"Gathering: {'ok' if hg else '—'}",
                   f"[F]: {'ok' if hs else '—'}"]
            messagebox.showinfo("Debug", "\n".join(msg))
        except Exception as e:
            messagebox.showerror("Debug error", str(e))

    def _tick(self, root):
        if self.worker: self.status.set(f"Состояние: {self.worker.state}")
        root.after(150, lambda: self._tick(root))


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
