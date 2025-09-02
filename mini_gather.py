# multi_gather_ui.py
# Выбор руды из resources/, дружественные имена папок, много шаблонов.
# Логика сбора та же: если "Без стамины" включено — плавно скроллим, пока [F] ближе к Gathering, потом жмём F.
# После F — ждём AFTER_F_SLEEP секунд (копка).

import os, re, time, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np, cv2
from mss import mss

# ===== Ввод =====
try:
    import pydirectinput as pdi   # DirectInput — игры видят нажатия
except Exception:
    pdi = None
import pyautogui as pag          # скролл колёсика
pag.PAUSE = 0
pag.FAILSAFE = True

def press_key(k: str):
    if pdi: pdi.press(k)
    else:   pag.press(k)

# ===== Константы / настройки =====
RESOURCES_ROOT_DEFAULT = "resources"

# "enum"-маппинг: название папки (нижним регистром) -> красивое имя
RESOURCE_NAME_MAP = {
    "luna_ore": "Luna Ore",
    # добавляй сюда свои соответствия при необходимости
}

AFTER_F_SLEEP     = 6.0    # сек. пауза после F
ACTION_COOLDOWN   = 0.8    # минимальная пауза между попытками

ROI_RIGHT_FRACTION = 0.50  # правая часть экрана, где живут подсказки
MATCH_THRESHOLD    = 0.56
SCALES             = [0.70,0.80,0.90,1.00,1.12,1.25,1.40]

SCROLL_UNIT        = -120  # одно деление колеса (Windows обычно 120), минус = вниз
SCROLL_DELAY       = 0.25  # пауза между шагами прокрутки
MAX_SCROLL_STEPS   = 10
ALIGN_TOLERANCE    = 16    # допуск (px) при сравнении вертикальных расстояний

IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")

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
        s = self._sct(); m = self._mon()
        return np.array(s.grab(m))[:, :, :3]
    def dims(self):
        m = self._mon()
        return m["width"], m["height"]

# ===== Набор шаблонов (много файлов) =====
class TemplateSet:
    def __init__(self, directory: str):
        """Загружает ВСЕ картинки из указанной папки."""
        self.tmps = []
        if os.path.isdir(directory):
            for n in os.listdir(directory):
                if n.lower().endswith(IMG_EXTS):
                    p = os.path.join(directory, n)
                    g = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
                    if g is not None and g.size > 0:
                        self.tmps.append(g)

    def best_match(self, gray_roi):
        """Лучшее совпадение: {'score', 'box':((x1,y1),(x2,y2))} или None"""
        best = None
        H, W = gray_roi.shape[:2]
        for g in self.tmps:
            for s in SCALES:
                tw, th = int(g.shape[1]*s), int(g.shape[0]*s)
                if tw < 12 or th < 12 or tw >= W or th >= H:
                    continue
                t = cv2.resize(g, (tw, th), interpolation=cv2.INTER_AREA)
                res = cv2.matchTemplate(gray_roi, t, cv2.TM_CCOEFF_NORMED)
                _, mx, _, ml = cv2.minMaxLoc(res)
                if mx >= MATCH_THRESHOLD:
                    tl = (ml[0], ml[1])
                    br = (tl[0]+tw, tl[1]+th)
                    cand = {"score": float(mx), "box": (tl, br)}
                    if not best or cand["score"] > best["score"]:
                        best = cand
        return best

# ===== Проверка структуры папки ресурса =====
def _pick_subdir(resource_dir: str, *alts):
    """возвращает путь к подпапке, если нашлась (по именам без регистра)"""
    names = {n.lower(): os.path.join(resource_dir, n) for n in os.listdir(resource_dir) if os.path.isdir(os.path.join(resource_dir, n))}
    for a in alts:
        if a in names:
            return names[a]
    return None

def resource_has_required_folders(resource_dir: str):
    if not os.path.isdir(resource_dir): return False
    dir_f = _pick_subdir(resource_dir, "focused","focus","f")
    dir_g = _pick_subdir(resource_dir, "gathering","gather","g")
    dir_s = _pick_subdir(resource_dir, "selector","select","sel","f_key","fkey","f-icon","ficon")
    return all([dir_f, dir_g, dir_s])

def load_resource_dir(resource_dir: str):
    if not os.path.isdir(resource_dir):
        raise FileNotFoundError(f"Папка ресурса не найдена: {resource_dir}")
    dir_f = _pick_subdir(resource_dir, "focused","focus","f")
    dir_g = _pick_subdir(resource_dir, "gathering","gather","g")
    dir_s = _pick_subdir(resource_dir, "selector","select","sel","f_key","fkey","f-icon","ficon")
    missing = []
    if not dir_f: missing.append("focused/")
    if not dir_g: missing.append("gathering/")
    if not dir_s: missing.append("selector/")
    if missing:
        raise FileNotFoundError(f"В {resource_dir} нет подпапок: {', '.join(missing)}")
    return TemplateSet(dir_f), TemplateSet(dir_g), TemplateSet(dir_s)

# ===== Поиск ресурсов в корне =====
def prettify_folder_name(name: str) -> str:
    # если есть явное имя — берём его
    key = name.lower()
    if key in RESOURCE_NAME_MAP:
        return RESOURCE_NAME_MAP[key]
    # иначе: snake/kebab -> Title Case
    s = re.sub(r'[_\-]+', ' ', name)
    parts = [p for p in s.split(' ') if p]
    return ' '.join(p.capitalize() for p in parts) if parts else name

def scan_resources(root_dir: str):
    """Возвращает список (display_name, absolute_path)."""
    results = []
    if not os.path.isdir(root_dir):
        return results
    for entry in os.listdir(root_dir):
        path = os.path.join(root_dir, entry)
        if os.path.isdir(path) and resource_has_required_folders(path):
            display = prettify_folder_name(entry)
            results.append((display, path))
    # сортируем по имени
    results.sort(key=lambda x: x[0].lower())
    # если имена одинаковые — добавим хвост с именем папки
    seen = {}
    deduped = []
    for name, path in results:
        base = os.path.basename(path)
        if name.lower() in seen:
            name = f"{name} ({base})"
        seen[name.lower()] = True
        deduped.append((name, path))
    return deduped

# ===== Рабочий поток =====
class Worker(threading.Thread):
    def __init__(self, screen, ts_focus: TemplateSet, ts_gath: TemplateSet, ts_sel: TemplateSet, want_gathering: bool):
        super().__init__(daemon=True)
        self.screen = screen
        self.ts_focus = ts_focus
        self.ts_gath  = ts_gath
        self.ts_sel   = ts_sel
        self.want_gathering = want_gathering
        self._stop = threading.Event()
        self.state = "idle"
        self._last_action = 0.0

    def stop(self): self._stop.set()
    def cooldown_ok(self): return (time.time() - self._last_action) > ACTION_COOLDOWN

    def _roi(self, gray):
        h, w = gray.shape[:2]
        x0 = int(w * (1.0 - ROI_RIGHT_FRACTION))
        return gray[:, x0:], x0

    @staticmethod
    def _y_center(box):
        (x1,y1),(x2,y2) = box
        return (y1+y2)//2

    def _selector_on_gathering(self, hit_f, hit_g, hit_s):
        if not (hit_g and hit_s): return False
        ys = self._y_center(hit_s["box"])
        yg = self._y_center(hit_g["box"])
        df = 10**9
        if hit_f:
            yf = self._y_center(hit_f["box"])
            df = abs(ys - yf)
        dg = abs(ys - yg)
        return dg + ALIGN_TOLERANCE < df

    def hold_after_press(self, seconds: float = AFTER_F_SLEEP):
        self._last_action = time.time()
        end = self._last_action + seconds
        while not self._stop.is_set():
            left = end - time.time()
            if left <= 0: break
            self.state = f"mining… {left:.1f}s"
            time.sleep(min(0.2, left))

    def run(self):
        while not self._stop.is_set():
            frame = self.screen.grab_bgr()
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            roi, x0 = self._roi(gray)

            hit_f = self.ts_focus.best_match(roi) if self.ts_focus.tmps else None
            hit_g = self.ts_gath.best_match(roi)  if self.ts_gath.tmps  else None
            hit_s = self.ts_sel.best_match(roi)   if self.ts_sel.tmps   else None

            if not (hit_f or hit_g):
                self.state = "wait"
                time.sleep(0.10)
                continue

            if not self.cooldown_ok():
                self.state = "cooldown"
                time.sleep(0.05)
                continue

            if not self.want_gathering:
                self.state = "press F (any)"
                press_key('f')
                self.hold_after_press()
                continue

            # хотим именно Gathering
            steps = 0
            aligned = self._selector_on_gathering(hit_f, hit_g, hit_s)
            while not aligned and steps < MAX_SCROLL_STEPS and not self._stop.is_set():
                self.state = "scroll…"
                pag.scroll(SCROLL_UNIT)  # одно "деление" вниз
                time.sleep(SCROLL_DELAY)
                frame = self.screen.grab_bgr()
                gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                roi, x0 = self._roi(gray)
                hit_f = self.ts_focus.best_match(roi) if self.ts_focus.tmps else None
                hit_g = self.ts_gath.best_match(roi)  if self.ts_gath.tmps  else None
                hit_s = self.ts_sel.best_match(roi)   if self.ts_sel.tmps   else None
                aligned = self._selector_on_gathering(hit_f, hit_g, hit_s)
                steps += 1

            if aligned:
                self.state = "press F (Gathering)"
                press_key('f')
                self.hold_after_press()
            else:
                self.state = "not aligned"
                time.sleep(0.10)

# ===== UI =====
class App:
    def __init__(self, root):
        root.title("Multi Gather — ресурсы из папки resources/")
        self.monitor = tk.IntVar(value=1)
        self.want_gathering = tk.BooleanVar(value=True)
        self.resources_root = tk.StringVar(value=RESOURCES_ROOT_DEFAULT)
        self.status = tk.StringVar(value="Укажи корневую папку ресурсов и выбери руду.")
        self._resources = []     # список (display_name, path)
        self._name_to_path = {}  # отображаемое имя -> путь
        self._selected_name = tk.StringVar(value="")

        frm = ttk.Frame(root, padding=12); frm.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1); root.rowconfigure(0, weight=1)

        # Корневой каталог ресурсов
        ttk.Label(frm, text="Папка resources:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.resources_root).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(frm, text="Обзор…", command=self.pick_root).grid(row=0, column=2, sticky="w")
        ttk.Button(frm, text="Обновить список", command=self.rescan).grid(row=0, column=3, sticky="w", padx=(6,0))

        # Выбор руды
        ttk.Label(frm, text="Руда/ресурс:").grid(row=1, column=0, sticky="w", pady=(6,0))
        self.cmb = ttk.Combobox(frm, textvariable=self._selected_name, values=[], state="readonly", width=32)
        self.cmb.grid(row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=(6,0))

        ttk.Checkbutton(frm, text="Без стамины → нажимать только Gathering", variable=self.want_gathering) \
            .grid(row=2, column=0, columnspan=4, sticky="w", pady=(6,2))

        ttk.Label(frm, text="Монитор (mss index):").grid(row=3, column=0, sticky="w")
        tk.Spinbox(frm, from_=1, to=6, textvariable=self.monitor, width=6).grid(row=3, column=1, sticky="w", padx=6)

        self.btn_start = ttk.Button(frm, text="▶ Старт", command=self.start); self.btn_start.grid(row=4, column=0, sticky="ew", pady=(10,4))
        self.btn_stop  = ttk.Button(frm, text="■ Стоп", command=self.stop, state="disabled"); self.btn_stop.grid(row=4, column=1, sticky="ew", pady=(10,4))
        ttk.Button(frm, text="Debug-снимок → debug_prompt.png", command=self.debug_snap).grid(row=4, column=2, columnspan=2, sticky="ew", pady=(10,4))

        ttk.Label(frm, textvariable=self.status, foreground="#666").grid(row=5, column=0, columnspan=4, sticky="w", pady=(8,0))
        for c in range(1,4):
            frm.columnconfigure(c, weight=1)

        self.screen = None; self.worker = None
        self.ts_f = self.ts_g = self.ts_s = None

        # Первый скан
        self.rescan()
        self._tick(root)

    def pick_root(self):
        d = filedialog.askdirectory(title="Выбери папку resources", initialdir=self.resources_root.get() if os.path.isdir(self.resources_root.get()) else ".")
        if d:
            self.resources_root.set(d)
            self.rescan()

    def rescan(self):
        root_dir = self.resources_root.get().strip()
        self._resources = scan_resources(root_dir)
        self._name_to_path = {name: path for name, path in self._resources}
        names = [name for name, _ in self._resources]
        self.cmb["values"] = names
        if names:
            # если ранее выбранного нет — выбрать первый
            if self._selected_name.get() not in names:
                self._selected_name.set(names[0])
            self.status.set(f"Нашёл {len(names)} ресурс(а).")
        else:
            self._selected_name.set("")
            self.status.set("В корне нет валидных ресурсов. Ожидаю подпапки с focused/gathering/selector.")

    def start(self):
        if self.worker and self.worker.is_alive(): return
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

        self.screen = Screen(monitor_index=self.monitor.get())
        self.worker = Worker(self.screen, self.ts_f, self.ts_g, self.ts_s, self.want_gathering.get())
        self.worker.start()
        self.btn_start.configure(state="disabled"); self.btn_stop.configure(state="normal")
        self.status.set(f"Запущено: {name}. Перейди в игру (Borderless/Windowed).")

    def stop(self):
        if self.worker: self.worker.stop(); self.worker = None
        self.btn_start.configure(state="normal"); self.btn_stop.configure(state="disabled")
        self.status.set("Остановлено.")

    def debug_snap(self):
        name = self._selected_name.get().strip()
        if not name or name not in self._name_to_path:
            messagebox.showerror("Нет ресурса", "Выбери ресурс из списка.")
            return
        resource_dir = self._name_to_path[name]
        try:
            ts_f, ts_g, ts_s = load_resource_dir(resource_dir)
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", str(e)); return

        sc = self.screen or Screen(monitor_index=self.monitor.get())
        frame = sc.grab_bgr()
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        x0 = int(w * (1.0 - ROI_RIGHT_FRACTION))
        roi = gray[:, x0:]

        def draw(ts, color):
            hit = ts.best_match(roi)
            if hit:
                (x1,y1),(x2,y2) = hit["box"]
                cv2.rectangle(frame, (x0+x1, y1), (x0+x2, y2), color, 2)
            return hit

        hf = draw(ts_f, (0,255,0))      # Focused — зелёный
        hg = draw(ts_g, (255,0,0))      # Gathering — красный
        hs = draw(ts_s, (0,255,255))    # [F] — жёлтый
        cv2.rectangle(frame, (x0,0), (w,h), (200,200,0), 2)  # ROI

        cv2.imwrite("debug_prompt.png", frame)
        msg = ["debug_prompt.png сохранён.",
               f"Focused: {'ok' if hf else '—'}",
               f"Gathering: {'ok' if hg else '—'}",
               f"[F]: {'ok' if hs else '—'}"]
        messagebox.showinfo("Debug", "\n".join(msg))

    def _tick(self, root):
        if self.worker: self.status.set(f"Состояние: {self.worker.state}")
        root.after(150, lambda: self._tick(root))

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
