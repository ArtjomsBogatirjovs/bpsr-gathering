import time, threading
import cv2
from .config import (
    ROI_RIGHT_FRACTION, SCALES, MATCH_THRESHOLD,
    ACTION_COOLDOWN, AFTER_F_SLEEP, ALIGN_TOLERANCE,
    SCROLL_DELAY, SCROLL_UNIT, MAX_SCROLL_STEPS
)
from .templates import TemplateSet
from .input_sim import press_key, scroll_once

class Worker(threading.Thread):
    """Поток: читает экран, находит Focused/Gathering/[F] и жмёт F по правилам."""
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

    @staticmethod
    def _y_center(box):
        (x1,y1),(x2,y2) = box
        return (y1+y2)//2

    def _roi(self, gray):
        h, w = gray.shape[:2]
        x0 = int(w * (1.0 - ROI_RIGHT_FRACTION))
        return gray[:, x0:], x0

    def _selector_on_gathering(self, hit_f, hit_g, hit_s):
        """True, если [F] ближе к Gathering, чем к Focused (с допуском)."""
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
        """Блокирующая пауза после нажатия F (учитывает Stop)."""
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

            hit_f = self.ts_focus.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_focus.tmps else None
            hit_g = self.ts_gath.best_match(roi,  SCALES, MATCH_THRESHOLD) if self.ts_gath.tmps  else None
            hit_s = self.ts_sel.best_match(roi,   SCALES, MATCH_THRESHOLD) if self.ts_sel.tmps   else None

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

            # Нужно именно Gathering — подгоняем [F]
            steps = 0
            aligned = self._selector_on_gathering(hit_f, hit_g, hit_s)
            while not aligned and steps < MAX_SCROLL_STEPS and not self._stop.is_set():
                self.state = "scroll…"
                scroll_once(SCROLL_UNIT)
                time.sleep(SCROLL_DELAY)
                # заново матчим
                frame = self.screen.grab_bgr()
                gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                roi, x0 = self._roi(gray)
                hit_f = self.ts_focus.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_focus.tmps else None
                hit_g = self.ts_gath.best_match(roi,  SCALES, MATCH_THRESHOLD) if self.ts_gath.tmps  else None
                hit_s = self.ts_sel.best_match(roi,   SCALES, MATCH_THRESHOLD) if self.ts_sel.tmps   else None
                aligned = self._selector_on_gathering(hit_f, hit_g, hit_s)
                steps += 1

            if aligned:
                self.state = "press F (Gathering)"
                press_key('f')
                self.hold_after_press()
            else:
                self.state = "not aligned"
                time.sleep(0.10)
