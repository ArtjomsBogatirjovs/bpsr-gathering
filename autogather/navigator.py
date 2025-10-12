# autogather/navigator.py
import logging
import time

from .config import (
    APPROACH_TOLERANCE, APPROACH_PAUSE
)
from .input_sim import hold_key_ms

logger = logging.getLogger(__name__)


class Navigator:
    """
    Мини-навигация: рывок по X/Y на длительность, пропорциональную расстоянию (в пикселях).
    Возвращаем ФАКТИЧЕСКИЙ шаг, который мы запланировали (px), чтобы воркер обновил координаты.
    """

    def __init__(self):
        self.pos_x = 0
        self.pos_y = 0
        self.y_teach = 1.0
        self.step_adj = 0.2

    def _teach_y(self):
        if self.y_teach > 2:
            return
        self.y_teach = self.y_teach + self.step_adj

    def _apply_step(self, dx_step: int, dy_step: int):
        self.pos_x += int(dx_step)
        self.pos_y += int(dy_step)

    def get_dx_dy(self, dx, dy):
        if abs(dx) > 2500:
            dx_adj = dx * 0.79
        elif abs(dx) > 2250:
            dx_adj = dx * 0.7
        elif abs(dx) > 1750:
            dx_adj = dx * 0.62
        elif abs(dx) > 1500:
            dx_adj = dx * 0.58
        elif abs(dx) > 1250:
            dx_adj = dx * 0.74
        elif abs(dx) > 1000:
            dx_adj = dx * 0.77
        elif abs(dx) > 750:
            dx_adj = dx * 0.76
        elif abs(dx) > 500:
            dx_adj = dx * 0.8
        elif abs(dx) > 250:
            dx_adj = dx * 0.6
        else:
            dx_adj = dx * 0.4
        dy_taught = dy * self.y_teach

        if dx != 0:
            logger.debug(f"1dx={dx}  and full dx_adj={dx_adj}")
            logger.debug(f"NAUCHIL={self.y_teach}")
        return dx + dx_adj, dy_taught

    def approach_by_distance(self, dx: int, dy: int, ignore_toller: bool = False, y_teach: bool = False):
        """
            dx < 0 → 'A' ; dx > 0 → 'D'
            dy < 0 → 'W' ; dy > 0 → 'S'
            Возвращает (dx_step, dy_step) — сколько пикселей мы планово сместились.
        """
        dx_step = 0
        dy_step = 0
        dx_in_ms, dy_in_ms = self.get_dx_dy(dx, dy)
        # Y ось
        if abs(dy) > APPROACH_TOLERANCE * 3 or ignore_toller:
            ms_y = abs(dy_in_ms)
            dy_step = dy
            if y_teach:
                self._teach_y()
                ms_y = abs(dy * self.step_adj)
                dy_step = dy * self.step_adj
            hold_key_ms('w' if dy < 0 else 's', ms_y)
            time.sleep(APPROACH_PAUSE)

        # X ось
        if abs(dx) > APPROACH_TOLERANCE or ignore_toller:
            ms_x = abs(dx_in_ms)
            hold_key_ms('a' if dx < 0 else 'd', ms_x)
            dx_step = dx
            time.sleep(APPROACH_PAUSE)

        self._apply_step(dx_step, dy_step)
