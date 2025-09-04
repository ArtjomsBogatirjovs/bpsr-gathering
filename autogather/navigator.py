# autogather/navigator.py
import time

from .config import (
    APPROACH_TOLERANCE, APPROACH_PAUSE
)
from .input_sim import hold_key_ms


class Navigator:
    """
    Мини-навигация: рывок по X/Y на длительность, пропорциональную расстоянию (в пикселях).
    Возвращаем ФАКТИЧЕСКИЙ шаг, который мы запланировали (px), чтобы воркер обновил координаты.
    """

    def approach_by_distance(self, dx: int, dy: int, ignore_toller: bool = False) -> tuple[int, int]:
        """
            dx < 0 → 'A' ; dx > 0 → 'D'
            dy < 0 → 'W' ; dy > 0 → 'S'
            Возвращает (dx_step, dy_step) — сколько пикселей мы планово сместились.
        """
        dx_step = 0
        dy_step = 0

        # Y ось
        if abs(dy) > APPROACH_TOLERANCE or ignore_toller:
            ms_y = abs(dy)
            hold_key_ms('w' if dy < 0 else 's', ms_y)
            dy_step = dy
            time.sleep(APPROACH_PAUSE)

        # X ось
        if abs(dx) > APPROACH_TOLERANCE or ignore_toller:
            ms_x = abs(dx)
            hold_key_ms('a' if dx < 0 else 'd', ms_x)
            dx_step = dx
            time.sleep(APPROACH_PAUSE)

        return dx_step, dy_step
