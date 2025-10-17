# autogather/worker.py
import threading
import time

import cv2

from autogather.enums.aspect_ratio import AspectRatio
from .config import (
    SCALES, MATCH_THRESHOLD,
    ACTION_COOLDOWN, ALIGN_TOLERANCE,
    SCROLL_UNIT, MAX_SCROLL_STEPS,
    RESOURCE_THRESHOLD, PROMPT_ROI
)
from .input_sim import press_key, scroll_once, _hide_unhide_ui
from .navigator import Navigator
from .screen import _get_roi_f
from .templates import TemplateSet
from .waypoints import WaypointDB




class Worker(threading.Thread):
    def __init__(self, screen, ts_focus: TemplateSet, ts_gath: TemplateSet,
                 ts_sel: TemplateSet, ts_res: TemplateSet, want_gathering: bool, ratio: AspectRatio, roi=PROMPT_ROI):
        super().__init__(daemon=True)
        self.screen = screen
        self.ts_focus = ts_focus
        self.ts_gath = ts_gath
        self.ts_sel = ts_sel
        self.ts_resource = ts_res
        self.want_gathering = want_gathering
        self._stop = threading.Event()
        self.state = "idle"
        self._last_action = 0.0

        # память узлов
        self.waypoints = WaypointDB()

        # навигация
        self.nav = Navigator()

        self.roi_prompt = roi
        self.ratio = ratio

    # ---- helpers ----
    def stop(self):
        self._stop.set()

    def cooldown_ok(self):
        return (time.time() - self._last_action) > ACTION_COOLDOWN

    @staticmethod
    def _y_center(box):
        (x1, y1), (x2, y2) = box
        return (y1 + y2) // 2

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

    def hold_after_press(self):
        self._last_action = time.time()
        end = self._last_action + self._gathering_seconds()
        while not self._stop.is_set():
            left = end - time.time()
            if left <= 0:
                break
            self.state = f"mining… {left:.1f}s"
            time.sleep(min(0.2, left))

    def _gathering_seconds(self):
        return 6.5
    def press_f_key(self):
        self.state = "press F"
        press_key('f')
        self.hold_after_press()
        self.waypoints.add_or_update(self.nav.pos_x, self.nav.pos_y)

    # ---- main loop ----
    def run(self):
        while not self._stop.is_set():
            if self.check_f_and_perform():
                continue
            # 0) Если есть «готовый» узел — бежим к нему напрямую (без поиска)
            wp = self.waypoints.next_available(self.nav.pos_x, self.nav.pos_y)
            if wp is not None:
                self.state = f"to waypoint → ({wp.x},{wp.y})"
                self.nav.approach_by_distance(wp.x - self.nav.pos_x, wp.y - self.nav.pos_y)

                time.sleep(1)
                roi, _ = _get_roi_f(self.screen, self.ratio, self.roi_prompt)
                if roi is None:
                    self.state = "ROI focus error"
                    continue
                if self.has_any_prompt(roi):
                    if self.want_gathering:
                        scroll_once(SCROLL_UNIT)
                    self.press_f_key()
                    continue

            # 1) ЕСЛИ подсказок НЕТ — ищем саму руду на всём кадре по отдельным шаблонам
            hit_obj, dx, dy = self._measure_resource_offset()
            if hit_obj:
                self.nav.approach_by_distance(dx, dy)
                if not self.check_f_and_perform():
                    for i in range(0, self.nav.teach_steps, 1):
                        self.state = f"approach resource dx={dx}, dy={dy}"
                        self.nav.approach_by_distance(0, dy, True, True)
                        if self.check_f_and_perform():
                            break
                time.sleep(1)

    def _measure_resource_offset(self):
        """
        Переизмерить смещение руды относительно центра кадра.
        Возвращает (found: bool, dx: int, dy: int).
        """
        if not self.ts_resource:
            return False, 0, 0
        frame = self.screen.grab_bgr()
        if frame is None:
            return False, 0, 0
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _hide_unhide_ui()
        hit = self.ts_resource.best_match(gray, SCALES, RESOURCE_THRESHOLD)
        _hide_unhide_ui()
        if not hit:
            return False, 0, 0
        (x1, y1), (x2, y2) = hit["box"]
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        H, W = gray.shape[:2]
        dx = cx - W // 2
        dy = cy - H // 2
        return True, dx, dy

    def check_f_and_perform(self) -> bool:
        any_prompt = self._has_any_prompt()
        if any_prompt[0]:
            return self._handle_prompt(any_prompt[1], any_prompt[2], any_prompt[3])
        return any_prompt[0]

    def _handle_prompt(self, hit_f, hit_g, hit_s) -> bool:
        """
        Обработка ситуации, когда подсказки (Focused/Gathering) найдены.
        Возвращает True, если мы что-то сделали (жали F / скроллили / подождали)
        и цикл run() должен сразу continue.
        """
        if not self.cooldown_ok():
            self.state = "cooldown"
            time.sleep(0.05)
            return True

        hit_button_f = (hit_g and hit_s and self._selector_on_gathering(hit_f, hit_g, hit_s)) or not self.want_gathering
        if hit_button_f:
            self.press_f_key()
            return True

        # иначе несколько мягких прокруток
        steps = 0
        aligned = hit_g and hit_s and self._selector_on_gathering(hit_f, hit_g, hit_s)
        while not aligned and steps < MAX_SCROLL_STEPS and not self._stop.is_set():
            self.state = f"scroll align {steps + 1}/{MAX_SCROLL_STEPS}"
            scroll_once(SCROLL_UNIT)
            roi, _ = _get_roi_f(self.screen, self.ratio, self.roi_prompt)
            if roi is None:
                break
            hit_f = self.get_ts_best_match(roi, self.ts_focus)
            hit_g = self.get_ts_best_match(roi, self.ts_gath)
            hit_s = self.get_ts_best_match(roi, self.ts_sel)
            aligned = hit_g and hit_s and self._selector_on_gathering(hit_f, hit_g, hit_s)
            steps += 1

        if aligned:
            self.press_f_key()
            return True
        else:
            self.state = "align failed"
            time.sleep(0.12)
            return True

    def get_ts_best_match(self, roi, template_set: TemplateSet):
        if roi is None or template_set is None:
            return None
        return template_set.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_focus.tmps else None

    def has_any_prompt(self, roi) -> bool:
        hit_f = self.get_ts_best_match(roi, self.ts_focus)
        if hit_f:
            return True
        if self.get_ts_best_match(roi, self.ts_gath):
            return True
        return False

    def _has_any_prompt(self):
        roi, _ = _get_roi_f(self.screen, self.ratio, self.roi_prompt)
        if roi is None:
            return False
        hit_f = self.get_ts_best_match(roi, self.ts_focus)
        hit_g = self.get_ts_best_match(roi, self.ts_gath)
        hit_s = self.get_ts_best_match(roi, self.ts_sel)
        any_prompt = (self.has_any_prompt(roi) or hit_f or hit_g) and hit_s
        return [any_prompt, hit_f, hit_g, hit_s]
