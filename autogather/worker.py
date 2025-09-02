# autogather/worker.py
import threading
import time

import cv2

from .config import (
    ROI_RIGHT_FRACTION, SCALES, MATCH_THRESHOLD,
    ACTION_COOLDOWN, AFTER_F_SLEEP, ALIGN_TOLERANCE,
    SCROLL_DELAY, SCROLL_UNIT, MAX_SCROLL_STEPS
)
from .input_sim import press_key, scroll_once
from .templates import TemplateSet


class Worker(threading.Thread):
    """
    Правила:
      • Пока на экране нет НИ одной надписи (Focused/Gathering) — просто ждём.
      • Если «Без стамины» выключено — жмём F, как только видна хотя бы одна надпись.
      • Если «Без стамины» включено — жмём F ТОЛЬКО когда [F] выровнен с Gathering.
        Если [F] не видно — делаем короткие попытки мягко прокрутить (до MAX_SCROLL_STEPS)
        и каждый раз перепроверяем. Подсказки исчезли — прекращаем попытку и ждём снова.
    """

    def __init__(self, screen, ts_focus: TemplateSet, ts_gath: TemplateSet,
                 ts_sel: TemplateSet, want_gathering: bool, hwnd: int | None = None):
        super().__init__(daemon=True)
        self.screen = screen
        self.ts_focus = ts_focus
        self.ts_gath = ts_gath
        self.ts_sel = ts_sel
        self.want_gathering = want_gathering
        self.target_hwnd = hwnd
        self._stop = threading.Event()
        self.state = "idle"
        self._last_action = 0.0

    # ---- helpers ----
    def stop(self):
        self._stop.set()

    def cooldown_ok(self):
        return (time.time() - self._last_action) > ACTION_COOLDOWN

    @staticmethod
    def _y_center(box):
        (x1, y1), (x2, y2) = box
        return (y1 + y2) // 2

    def _roi(self, gray):
        h, w = gray.shape[:2]
        x0 = int(w * (1.0 - ROI_RIGHT_FRACTION))
        return gray[:, x0:], x0

    def _selector_on_gathering(self, hit_f, hit_g, hit_s):
        """True, если [F] ближе к Gathering, чем к Focused (с допуском)."""
        if not (hit_g and hit_s):
            return False
        ys = self._y_center(hit_s["box"])
        yg = self._y_center(hit_g["box"])
        df = 10 ** 9
        if hit_f:
            yf = self._y_center(hit_f["box"])
            df = abs(ys - yf)
        dg = abs(ys - yg)
        return dg + ALIGN_TOLERANCE < df

    def hold_after_press(self, seconds: float = AFTER_F_SLEEP):
        """Блокирующая пауза после нажатия F (время на добычу)."""
        self._last_action = time.time()
        end = self._last_action + seconds
        while not self._stop.is_set():
            left = end - time.time()
            if left <= 0:
                break
            self.state = f"mining… {left:.1f}s"
            time.sleep(min(0.2, left))

    # ---- main loop ----
    def run(self):
        while not self._stop.is_set():
            frame = self.screen.grab_bgr()
            if frame is None:
                self.state = "wait frame"
                time.sleep(0.10)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            roi, _ = self._roi(gray)

            # Ищем надписи и селектор
            hit_f = self.ts_focus.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_focus.tmps else None
            hit_g = self.ts_gath.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_gath.tmps else None
            hit_s = self.ts_sel.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_sel.tmps else None

            # --- ключевое условие: нужна хотя бы ОДНА из надписей ---
            if not (hit_f or hit_g):
                self.state = "wait: no options"
                time.sleep(0.12)
                continue

            if not self.cooldown_ok():
                self.state = "cooldown"
                time.sleep(0.05)
                continue

            # Стамина разрешена — жмём F, как только видна любая надпись
            if not self.want_gathering:
                self.state = "press F (any)"
                press_key('f')
                self.hold_after_press()
                continue

            # Нужен именно Gathering
            # 1) Если видно Gathering и [F] — пробуем выровнять точно
            if hit_g and hit_s:
                aligned = self._selector_on_gathering(hit_f, hit_g, hit_s)
                steps = 0
                while not aligned and steps < MAX_SCROLL_STEPS and not self._stop.is_set():
                    self.state = f"scroll… {steps + 1}/{MAX_SCROLL_STEPS}"
                    scroll_once(SCROLL_UNIT)
                    time.sleep(SCROLL_DELAY)

                    frame = self.screen.grab_bgr()
                    if frame is None:
                        break
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    roi, _ = self._roi(gray)
                    # обновляем совпадения
                    hit_f = self.ts_focus.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_focus.tmps else None
                    hit_g = self.ts_gath.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_gath.tmps else None
                    hit_s = self.ts_sel.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_sel.tmps else None

                    # если опции пропали — прекращаем попытку
                    if not (hit_f or hit_g):
                        break

                    aligned = self._selector_on_gathering(hit_f, hit_g, hit_s)
                    steps += 1

                if aligned:
                    self.state = "press F (Gathering)"
                    press_key('f')
                    self.hold_after_press()
                    continue
                else:
                    self.state = "align failed"
                    time.sleep(0.12)
                    continue

            # 2) Если видно только Gathering (без [F]) — делаем аккуратную попытку
            if hit_g and not hit_s:
                self.state = "scroll try"
                scroll_once(SCROLL_UNIT)
                time.sleep(SCROLL_DELAY)
                # дальше пусть цикл начнёт заново и оценит ситуацию
                continue

            # 3) Если видно только Focused — покрутим чуть вниз, чтобы появился Gathering
            if hit_f and not hit_g:
                self.state = "seek gathering"
                scroll_once(SCROLL_UNIT)
                time.sleep(SCROLL_DELAY)
                continue

            # иначе — небольшой отдых
            self.state = "wait"
            time.sleep(0.10)
