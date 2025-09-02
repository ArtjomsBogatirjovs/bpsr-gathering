# autoscan.py — v3 (run-forward scanning, multiscale prompt, debug, DirectInput)

import os
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import cv2
from mss import mss

# ==== ВВОД: DirectInput, чтобы игра видела нажатия ====
try:
    import pydirectinput as pyautogui  # type: ignore
except Exception:
    import pyautogui                   # fallback

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True

def move_rel_i(x, y, duration=0.0, clamp=220):
    """
    Безопасный relative move: pydirectinput требует int, ограничиваем рывки.
    """
    if clamp is not None:
        x = max(-clamp, min(clamp, x))
        y = max(-clamp, min(clamp, y))
    xi = int(round(x))
    yi = int(round(y))
    if xi == 0 and abs(x) >= 0.5:
        xi = 1 if x > 0 else -1
    if yi == 0 and abs(y) >= 0.5:
        yi = 1 if y > 0 else -1
    pyautogui.moveRel(xi, yi, duration=duration)

# ==== НАСТРОЙКИ ====
RESOURCE_SETS = {
    "Лунная руда": "templates/lunar_ore",
}
PROMPTS_DIR_DEFAULT = "templates/prompts"

INTERACT_KEY_DEFAULT = "f"      # подсказка в игре [F]
SPRINT_KEY_DEFAULT   = "shift"  # стамина
RUN_KEY              = "w"

# Скан/поиск
TURN_STEP_PIXELS = 70
SCAN_PAUSE = 0.22
DETECT_INTERVAL = 0.06

# ORB (руда)
CONFIDENCE_MIN_MATCHES = 8
APPROACH_PIXELS = 140
TEMPLATE_DOWNSCALE = 1.0

# Подсказка [F] (template matching)
PROMPT_THRESHOLD = 0.55   # порог совпадения
PROMPT_ROI_X     = 0.40   # правая часть экрана (0..1), где обычно подсказка
SCALES = [0.60, 0.70, 0.80, 0.90, 1.00, 1.10, 1.25, 1.40, 1.55]  # мульти-скейл

INTERACT_COOLDOWN = 0.80  # пауза между нажатиями F

# ===== СКРИН (thread-local mss) =====
class Screen:
    def __init__(self, monitor_index=1):
        self.monitor_index = int(monitor_index)
        self._tls = threading.local()

    def _get_sct(self):
        if not hasattr(self._tls, "sct"):
            self._tls.sct = mss()
        return self._tls.sct

    def _get_monitor(self):
        sct = self._get_sct()
        return sct.monitors[self.monitor_index] if len(sct.monitors) > self.monitor_index else sct.monitors[0]

    def dims(self):
        mon = self._get_monitor()
        return mon["width"], mon["height"]

    def grab_bgr(self):
        sct = self._get_sct()
        mon = self._get_monitor()
        img = sct.grab(mon)              # BGRA
        frame = np.array(img)[:, :, :3]  # BGR
        return frame

# ===== ORB детектор руды =====
class Detector:
    def __init__(self, template_dir):
        self.orb = cv2.ORB_create(nfeatures=1000)
        self.bf  = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        self.templates = []
        self._load_templates(template_dir)

    def _load_templates(self, template_dir):
        self.templates.clear()
        if not os.path.isdir(template_dir):
            return
        for name in os.listdir(template_dir):
            p = os.path.join(template_dir, name)
            if not os.path.isfile(p):
                continue
            img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            if TEMPLATE_DOWNSCALE != 1.0:
                img = cv2.resize(img, None, fx=1/TEMPLATE_DOWNSCALE, fy=1/TEMPLATE_DOWNSCALE)
            kps, des = self.orb.detectAndCompute(img, None)
            if des is not None and len(kps) >= 8:
                self.templates.append((img, kps, des))

    def find_target(self, frame_bgr):
        if not self.templates:
            return None
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        kps_f, des_f = self.orb.detectAndCompute(gray, None)
        if des_f is None or len(kps_f) < 8:
            return None
        best = None
        for (_, kps_t, des_t) in self.templates:
            matches = self.bf.knnMatch(des_t, des_f, k=2)
            good = [m for m, n in matches if m.distance < 0.75 * n.distance]
            if len(good) >= CONFIDENCE_MIN_MATCHES:
                src_pts = np.float32([kps_t[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
                dst_pts = np.float32([kps_f[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
                H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                if H is not None:
                    dst = cv2.perspectiveTransform(np.float32([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]]), H)
                    cx = float(np.mean(dst[:, 0, 0]))
                    cy = float(np.mean(dst[:, 0, 1]))
                    score = len(good)
                    if best is None or score > best["score"]:
                        best = {"x": cx, "y": cy, "score": score}
        return best

# ===== Мульти-скейл детектор подсказки [F] =====
class PromptDetector:
    def __init__(self, templates=None):
        self.tmps_gray = []
        self.tmps_edge = []
        if templates:
            self.add_templates(templates)

    def add_templates(self, templates):
        for p in templates:
            if os.path.isfile(p):
                g = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
                if g is None:
                    continue
                e = cv2.Canny(g, 60, 160)
                self.tmps_gray.append(g)
                self.tmps_edge.append(e)

    def load_dir(self, directory):
        self.tmps_gray.clear()
        self.tmps_edge.clear()
        if os.path.isdir(directory):
            for name in os.listdir(directory):
                if not name.lower().endswith((".png", ".jpg", ".jpeg")):
                    continue
                self.add_templates([os.path.join(directory, name)])

    def find(self, frame_bgr, return_debug=False):
        if not self.tmps_gray:
            return (None, None) if return_debug else None

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        x0 = int(w * PROMPT_ROI_X)
        roi = gray[:, x0:]
        roi_blur = cv2.GaussianBlur(roi, (3, 3), 0)
        roi_edge = cv2.Canny(roi_blur, 60, 160)

        best = None
        best_box = None

        for g_t, e_t in zip(self.tmps_gray, self.tmps_edge):
            for s in SCALES:
                tg_w = int(g_t.shape[1] * s)
                tg_h = int(g_t.shape[0] * s)
                if tg_w < 10 or tg_h < 10:
                    continue
                if tg_w >= roi.shape[1] or tg_h >= roi.shape[0]:
                    continue

                tg = cv2.resize(g_t, (tg_w, tg_h), interpolation=cv2.INTER_AREA)
                te = cv2.resize(e_t, (tg_w, tg_h), interpolation=cv2.INTER_AREA)

                # Сырая картинка и по краям — берём лучший результат
                r1 = cv2.matchTemplate(roi_blur, tg, cv2.TM_CCOEFF_NORMED)
                r2 = cv2.matchTemplate(roi_edge, te, cv2.TM_CCOEFF_NORMED)

                for res in (r1, r2):
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    if max_val >= PROMPT_THRESHOLD:
                        top_left = (x0 + max_loc[0], max_loc[1])
                        bottom_right = (top_left[0] + tg_w, top_left[1] + tg_h)
                        cx = top_left[0] + tg_w // 2
                        cy = top_left[1] + tg_h // 2
                        cand = {"x": cx, "y": cy, "score": float(max_val)}
                        if best is None or cand["score"] > best["score"]:
                            best = cand
                            best_box = (top_left, bottom_right)

        if return_debug:
            dbg = frame_bgr.copy()
            cv2.rectangle(dbg, (x0, 0), (w, h), (0, 255, 255), 2)  # ROI справа
            if best and best_box:
                cv2.rectangle(dbg, best_box[0], best_box[1], (0, 255, 0), 2)
                cv2.putText(
                    dbg, f"score={best['score']:.2f}",
                    (best_box[0][0], max(20, best_box[0][1] - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA
                )
            return best, dbg
        else:
            return best

# ===== РАННЕР =====
class Runner(threading.Thread):
    def __init__(self, detector, screen, interact_key, use_stamina, interact_prompt=None):
        super().__init__(daemon=True)
        self.detector = detector
        self.screen = screen
        self.interact_key = interact_key.strip().lower()
        self.use_stamina = bool(use_stamina)
        self._stop = threading.Event()
        self.interact_prompt = interact_prompt
        self.state = "idle"
        self.run_until = 0.0       # держим W до этого времени
        self.scan_toggle = False   # чередуем A/D при скане

    def stop(self):
        self._stop.set()

    def near_center(self, x, y):
        w, h = self.screen.dims()
        cx, cy = w / 2, h / 2
        return abs(x - cx) < APPROACH_PIXELS and abs(y - cy) < APPROACH_PIXELS

    def slight_scan(self):
        move_rel_i(TURN_STEP_PIXELS, 0, duration=0.08)
        time.sleep(SCAN_PAUSE)
        move_rel_i(-2 * TURN_STEP_PIXELS, 0, duration=0.16)
        time.sleep(SCAN_PAUSE)
        move_rel_i(TURN_STEP_PIXELS, 0, duration=0.08)

    def hold_run(self, hold=True):
        if hold:
            if self.use_stamina:
                pyautogui.keyDown(SPRINT_KEY_DEFAULT)
            pyautogui.keyDown(RUN_KEY)
        else:
            pyautogui.keyUp(RUN_KEY)
            if self.use_stamina:
                pyautogui.keyUp(SPRINT_KEY_DEFAULT)

    def keep_run(self):
        # Поддерживаем движение вперёд между итерациями
        if time.time() < self.run_until:
            if self.use_stamina:
                pyautogui.keyDown(SPRINT_KEY_DEFAULT)
            # некоторые клиенты плохо держат долгий keyDown — подтапываем
            pyautogui.keyDown(RUN_KEY)
            time.sleep(0.02)
            pyautogui.keyUp(RUN_KEY)
            if self.use_stamina:
                pyautogui.keyUp(SPRINT_KEY_DEFAULT)
        else:
            self.hold_run(False)

    def approach(self, target_x, target_y):
        w, h = self.screen.dims()
        cx, cy = w / 2, h / 2
        dx = target_x - cx
        dy = target_y - cy
        # мягко довернуть камеру к цели
        move_rel_i(dx * 0.10, dy * 0.06, duration=0.08)
        # бежим вперёд ближайшие 0.6 сек
        self.run_until = max(self.run_until, time.time() + 0.6)
        self.keep_run()

    def press_interact(self):
        if self.use_stamina:
            pyautogui.keyDown(SPRINT_KEY_DEFAULT)
        pyautogui.press(self.interact_key)
        if self.use_stamina:
            pyautogui.keyUp(SPRINT_KEY_DEFAULT)

    def run(self):
        last_interact = 0.0
        while not self._stop.is_set():
            frame = self.screen.grab_bgr()

            # Поддерживать движение вперёд, если недавно инициировано
            self.keep_run()

            # 1) Подсказка [F] — главный триггер сбора
            if self.interact_prompt:
                p = self.interact_prompt.find(frame)
                if p and (time.time() - last_interact) > INTERACT_COOLDOWN:
                    self.state = f"prompt {p['score']:.2f} -> interact"
                    self.hold_run(False)
                    self.run_until = 0.0
                    self.press_interact()
                    last_interact = time.time()
                    time.sleep(0.85)
                    continue

            # 2) Fallback: геометрия руды (если подсказки нет)
            found = self.detector.find_target(frame) if self.detector else None
            if found:
                self.state = f"ore score={found['score']}"
                if not self.near_center(found["x"], found["y"]):
                    self.approach(found["x"], found["y"])
                else:
                    self.hold_run(False)
                    if (time.time() - last_interact) > INTERACT_COOLDOWN:
                        self.press_interact()
                        last_interact = time.time()
                        time.sleep(0.8)
            else:
                # 3) Скан с движением вперёд и лёгким кружением
                self.state = "scan-move"
                self.run_until = max(self.run_until, time.time() + 0.5)  # полсекунды бежать
                strafe = 'a' if self.scan_toggle else 'd'
                self.scan_toggle = not self.scan_toggle
                pyautogui.keyDown(strafe)
                self.slight_scan()
                time.sleep(0.25)
                pyautogui.keyUp(strafe)

            time.sleep(DETECT_INTERVAL)

# ===== UI =====
class App:
    def __init__(self, root):
        self.root = root
        root.title("AutoGather — Blue Protocol: Star Resonance")

        self.resource_var = tk.StringVar(value="Лунная руда")
        self.interact_key_var = tk.StringVar(value=INTERACT_KEY_DEFAULT)
        self.stamina_var = tk.BooleanVar(value=False)
        self.monitor_var = tk.IntVar(value=1)
        self.status_var = tk.StringVar(value="Ожидание…")
        self.prompts_dir_var = tk.StringVar(value=PROMPTS_DIR_DEFAULT)

        frm = ttk.Frame(root, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0,  weight=1)

        ttk.Label(frm, text="Тип ресурса:").grid(row=0, column=0, sticky="w")
        self.cmb = ttk.Combobox(frm, textvariable=self.resource_var, values=list(RESOURCE_SETS.keys()), state="readonly")
        self.cmb.grid(row=0, column=1, sticky="ew", padx=6)

        ttk.Label(frm, text="Папка шаблонов руды:").grid(row=1, column=0, sticky="w")
        ttk.Button(frm, text="Выбрать…", command=self.open_templates_dir).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Папка подсказок [F]:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.prompts_dir_var).grid(row=2, column=1, sticky="ew", padx=(6,0))
        ttk.Button(frm, text="Обзор…", command=self.open_prompts_dir).grid(row=2, column=2, sticky="w", padx=(6,0))

        ttk.Label(frm, text="Клавиша взаимодействия:").grid(row=3, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.interact_key_var, width=8).grid(row=3, column=1, sticky="w", padx=6)

        ttk.Checkbutton(frm, text="Использовать стамину (Shift)", variable=self.stamina_var).grid(row=4, column=0, columnspan=2, sticky="w")

        ttk.Label(frm, text="Монитор (mss index):").grid(row=5, column=0, sticky="w")
        tk.Spinbox(frm, from_=1, to=6, textvariable=self.monitor_var, width=6).grid(row=5, column=1, sticky="w", padx=6)

        self.btn_start = ttk.Button(frm, text="▶ Старт (F8)", command=self.start)
        self.btn_start.grid(row=6, column=0, sticky="ew", pady=(8,4))
        self.btn_stop = ttk.Button(frm, text="■ Стоп (F9)", command=self.stop, state="disabled")
        self.btn_stop.grid(row=6, column=1, sticky="ew", pady=(8,4))

        ttk.Button(frm, text="Тест: нажать взаимодействие", command=self.test_press).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(4,2))
        ttk.Button(frm, text="Debug-снимок подсказки → debug_prompt.png", command=self.debug_snapshot).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(2,4))

        ttk.Label(frm, textvariable=self.status_var, foreground="#666").grid(row=9, column=0, columnspan=3, sticky="w", pady=(8,0))

        for c in range(1,3):
            frm.columnconfigure(c, weight=1)

        root.bind("<F8>", lambda e: self.start())
        root.bind("<F9>", lambda e: self.stop())

        self.screen = None
        self.detector = None
        self.prompt_detector = None
        self.runner = None

        self.update_status_loop()

    def open_templates_dir(self):
        res = self.resource_var.get()
        d0 = RESOURCE_SETS.get(res, ".")
        d = filedialog.askdirectory(title=f"Папка шаблонов для «{res}»", initialdir=d0 if os.path.isdir(d0) else ".")
        if d:
            RESOURCE_SETS[res] = d
            messagebox.showinfo("OK", f"Шаблоны для «{res}» обновлены:\n{d}")

    def open_prompts_dir(self):
        d = filedialog.askdirectory(
            title="Папка подсказок [F] (png/jpg)",
            initialdir=self.prompts_dir_var.get() if os.path.isdir(self.prompts_dir_var.get()) else "."
        )
        if d:
            self.prompts_dir_var.set(d)

    def start(self):
        if self.runner and self.runner.is_alive():
            return

        self.screen = Screen(monitor_index=self.monitor_var.get())

        res = self.resource_var.get()
        tpl_dir = RESOURCE_SETS.get(res)
        if not tpl_dir or not os.path.isdir(tpl_dir):
            messagebox.showerror("Нет шаблонов руды", f"Укажи папку для «{res}».")
            return
        self.detector = Detector(tpl_dir)

        self.prompt_detector = PromptDetector()
        prompts_dir = self.prompts_dir_var.get()
        if os.path.isdir(prompts_dir):
            self.prompt_detector.load_dir(prompts_dir)
        else:
            self.prompt_detector.add_templates([
                os.path.join(PROMPTS_DIR_DEFAULT, "focused.png"),
                os.path.join(PROMPTS_DIR_DEFAULT, "gathering.png"),
            ])

        if not self.prompt_detector.tmps_gray and not self.detector.templates:
            messagebox.showerror("Нет шаблонов", "Добавь хотя бы шаблоны подсказок [F].")
            return

        self.runner = Runner(
            detector=self.detector,
            screen=self.screen,
            interact_key=self.interact_key_var.get(),
            use_stamina=self.stamina_var.get(),
            interact_prompt=self.prompt_detector
        )
        self.runner.start()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_var.set("Запущено… Перейди в игру (Borderless/Windowed).")

    def stop(self):
        if self.runner:
            self.runner.stop()
            self.runner = None
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status_var.set("Остановлено.")

    def test_press(self):
        key = self.interact_key_var.get().strip().lower()
        self.status_var.set(f"Жму {key} через 1.5 сек — переключись в игру!")
        self.root.after(1500, lambda: pyautogui.press(key))

    def debug_snapshot(self):
        # Сохраняем скрин с подсветкой ROI и лучшего совпадения
        try:
            if not self.screen:
                self.screen = Screen(monitor_index=self.monitor_var.get())
            frame = self.screen.grab_bgr()
            if not self.prompt_detector:
                self.prompt_detector = PromptDetector()
                pd = self.prompts_dir_var.get()
                if os.path.isdir(pd):
                    self.prompt_detector.load_dir(pd)
            best, dbg = self.prompt_detector.find(frame, return_debug=True)
            out = "debug_prompt.png"
            cv2.imwrite(out, dbg if dbg is not None else frame)
            if best:
                messagebox.showinfo("Debug", f"Готово: {out}\nНайдено, score={best['score']:.2f}")
            else:
                messagebox.showinfo("Debug", f"Готово: {out}\nСовпадений не найдено (добавь/перекрой шаблоны).")
        except Exception as e:
            messagebox.showerror("Debug error", str(e))

    def update_status_loop(self):
        if self.runner:
            self.status_var.set(f"Состояние: {self.runner.state}")
        self.root.after(200, self.update_status_loop)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        App(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))
