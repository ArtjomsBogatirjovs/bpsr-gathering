# autogather/navigator.py
import time

from .config import (
    APPROACH_TOLERANCE, APPROACH_PAUSE,
    MS_PER_PX_STRAFE, MS_PER_PX_FORWARD,
    APPROACH_MIN_MS, APPROACH_MAX_MS,
)
from .input_sim import hold_key_ms


class Navigator:
    """
    Мини-навигация: рывок по X/Y на длительность, пропорциональную расстоянию (в пикселях).
    Возвращаем ФАКТИЧЕСКИЙ шаг, который мы запланировали (px), чтобы воркер обновил координаты.
    """

    def approach_by_distance(self, dx: int, dy: int) -> tuple[int, int]:
        """
        dx<0 → 'A' ; dx>0 → 'D'
        dy<0 → 'W' ; dy>0 → 'S'
        Возвращает (dx_step, dy_step) — сколько пикселей мы «планово» сдвинулись по каждой оси.
        """
        dx_step = 0
        dy_step = 0

        # --- X ось ---
        if abs(dx) > APPROACH_TOLERANCE:
            # сколько пикселей реально возьмём за этот рывок (ограничим через MAX_MS)
            max_px_x = int(APPROACH_MAX_MS / MS_PER_PX_STRAFE)
            want_px_x = min(abs(dx), max_px_x)
            ms_x = int(max(APPROACH_MIN_MS, min(APPROACH_MAX_MS, want_px_x * MS_PER_PX_STRAFE)))
            hold_key_ms('a' if dx < 0 else 'd', ms_x)
            dx_step = -want_px_x if dx < 0 else want_px_x
            time.sleep(APPROACH_PAUSE)

        # --- Y ось ---
        if abs(dy) > APPROACH_TOLERANCE:
            max_px_y = int(APPROACH_MAX_MS / MS_PER_PX_FORWARD)
            want_px_y = min(abs(dy), max_px_y)
            ms_y = int(max(APPROACH_MIN_MS, min(APPROACH_MAX_MS, want_px_y * MS_PER_PX_FORWARD)))
            hold_key_ms('w' if dy < 0 else 's', ms_y)
            dy_step = -want_px_y if dy < 0 else want_px_y
            time.sleep(APPROACH_PAUSE)

        return dx_step, dy_step
