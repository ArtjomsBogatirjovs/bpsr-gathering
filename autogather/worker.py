# autogather/worker.py
import threading
import time

import cv2

from .config import (
    ROI_RIGHT_FRACTION, SCALES, MATCH_THRESHOLD,
    ACTION_COOLDOWN, AFTER_F_SLEEP, ALIGN_TOLERANCE,
    SCROLL_DELAY, SCROLL_UNIT, MAX_SCROLL_STEPS,
    RESOURCE_THRESHOLD, NUDGE_MOUSE_X_PX
)
from .input_sim import press_key, scroll_once, move_mouse_rel
from .navigator import Navigator
from .templates import TemplateSet, load_resource_object_dir
from .waypoints import WaypointDB


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
                 ts_sel: TemplateSet, want_gathering: bool,
                 hwnd: int | None = None, resource_dir: str | None = None):
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

        # координаты персонажа в условных "пикселях" экрана (origin = 0,0 при старте)
        self.pos_x = 0
        self.pos_y = 0

        # память узлов
        self.waypoints = WaypointDB()

        # шаблоны для поиска САМОГО объекта ресурса
        self.ts_resource = load_resource_object_dir(resource_dir) if resource_dir else None

        # навигация
        self.nav = Navigator()

    # ---- helpers ----
    def stop(self):
        self._stop.set()

    def _apply_step(self, dx_step: int, dy_step: int):
        self.pos_x += int(dx_step)
        self.pos_y += int(dy_step)

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
            # ROI для подсказок справа
            roi, _ = self._roi(gray)

            # 0) Если есть «готовый» узел — бежим к нему напрямую (без поиска)
            wp = self.waypoints.next_available(self.pos_x, self.pos_y)
            if wp is not None:
                self.state = f"to waypoint → ({wp.x},{wp.y})"
                dx = wp.x - self.pos_x
                dy = wp.y - self.pos_y
                dx_step, dy_step = self.nav.approach_by_distance(dx, dy)
                self._apply_step(dx_step, dy_step)
                # если дошли — дальше обычная логика сама увидит подсказки и нажмёт F
                # а если подсказок нет — на след. итерации попробуем поискать объект/нуджнуть камеру
                continue

            # 1) СНАЧАЛА смотрим подсказки (добыча в приоритете, если уже рядом)
            hit_f = self.ts_focus.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_focus.tmps else None
            hit_g = self.ts_gath.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_gath.tmps else None
            hit_s = self.ts_sel.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_sel.tmps else None

            has_any_prompt = bool(hit_f or hit_g)

            if has_any_prompt:
                # ... здесь оставь твою логику:
                # - если cooldown — подождать
                # - если want_gathering выключен — жмём F сразу
                # - если включен — выравниваем [F] к Gathering (несколько легких прокруток); жмём F; hold_after_press()
                # - и continue
                # пример:
                if not self.cooldown_ok():
                    self.state = "cooldown"
                    time.sleep(0.05)
                    continue

                if not self.want_gathering:
                    self.state = "press F (any)"
                    press_key('f')
                    self.hold_after_press()
                    self.waypoints.add_or_update(self.pos_x, self.pos_y)
                    continue

                # нужен Gathering
                if hit_g and hit_s and self._selector_on_gathering(hit_f, hit_g, hit_s):
                    self.state = "press F (Gathering)"
                    press_key('f')
                    self.hold_after_press()
                    self.waypoints.add_or_update(self.pos_x, self.pos_y)
                    continue

                # иначе несколько мягких прокруток
                steps = 0
                aligned = hit_g and hit_s and self._selector_on_gathering(hit_f, hit_g, hit_s)
                while not aligned and steps < MAX_SCROLL_STEPS and not self._stop.is_set():
                    self.state = f"scroll align {steps + 1}/{MAX_SCROLL_STEPS}"
                    scroll_once(SCROLL_UNIT)
                    time.sleep(SCROLL_DELAY)
                    frame = self.screen.grab_bgr()
                    if frame is None: break
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    roi, _ = self._roi(gray)
                    hit_f = self.ts_focus.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_focus.tmps else None
                    hit_g = self.ts_gath.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_gath.tmps else None
                    hit_s = self.ts_sel.best_match(roi, SCALES, MATCH_THRESHOLD) if self.ts_sel.tmps else None
                    aligned = hit_g and hit_s and self._selector_on_gathering(hit_f, hit_g, hit_s)
                    steps += 1

                if aligned:
                    self.state = "press F (Gathering)"
                    press_key('f')
                    self.hold_after_press()
                    self.waypoints.add_or_update(self.pos_x, self.pos_y)
                    continue
                else:
                    self.state = "align failed"
                    time.sleep(0.12)
                    continue

            # 2) ЕСЛИ подсказок НЕТ — ищем саму руду на всём кадре по отдельным шаблонам
            if self.ts_resource is not None:
                hit_obj = self.ts_resource.best_match(gray, SCALES, RESOURCE_THRESHOLD)
            else:
                hit_obj = None

            if hit_obj:
                # нашли руду → двигаемся к ней
                (x1, y1), (x2, y2) = hit_obj["box"]
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                H, W = gray.shape[:2]
                dx = cx - W // 2
                dy = cy - H // 2
                self.state = f"approach resource dx={dx}, dy={dy}"
                # self.nav.move_towards_point(dx, dy)
                dx_step, dy_step = self.nav.approach_by_distance(dx, dy)
                self._apply_step(dx_step, dy_step)
                # после шага цикл заново проверит подсказки и т.п.
                continue

            # 3) Ни подсказок, ни руды — слегка "подтолкнуть" камеру по X
            self.state = "nudge"
            move_mouse_rel(NUDGE_MOUSE_X_PX, 0)
            time.sleep(0.12)
