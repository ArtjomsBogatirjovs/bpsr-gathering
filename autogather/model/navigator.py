# autogather/navigator.py
import logging
import time

from autogather.config import (
    APPROACH_PAUSE
)
from autogather.input_sim import hold_key_ms
from autogather.model.resource_model import ResourceObject

logger = logging.getLogger(__name__)


def run(is_x: bool, axis_value: int):
    ms_run = abs(axis_value)
    if is_x:
        button = 'a' if axis_value < 0 else 'd'
    else:
        button = 'w' if axis_value < 0 else 's'
    hold_key_ms(button, ms_run)
    time.sleep(APPROACH_PAUSE)


class Navigator:
    def __init__(self, resource: ResourceObject):
        self.resource = resource
        self.pos_x = 0
        self.pos_y = 0

    def _apply_step(self, dx_step: int, dy_step: int):
        self.pos_x += int(dx_step)
        self.pos_y += int(dy_step)
        logger.debug(f"DY POSITION={self.pos_y} and DX POSITION={self.pos_x}")

    def _calc_adjustment_x(self, value: float) -> float:
        a = abs(value)
        if a > 2500: return value * 0.73
        if a > 2250: return value * 0.70
        if a > 1750: return value * 0.64
        if a > 1500: return value * 0.6
        if a > 1250: return value * 0.73
        if a > 1000: return value * 0.8
        if a > 750:  return value * 0.74
        if a > 500:  return value * 0.7
        if a > 250:  return value * 0.7
        return value * -0.9

    def _calc_adjustment_y(self, value: float) -> float:
        a = abs(value)
        if a > 2500: return value * 0.72
        if a > 2250: return value * 0.70
        if a > 1750: return value * 0.64
        if a > 1500: return value * 0.6
        if a > 1250: return value * 0.72
        if a > 1000: return value * 0.8
        if a > 750:  return value * 0.7
        if a > 500:  return value * 0.7
        if a > 250:  return value * 0.7
        return value * -0.7

    def get_dx_dy(self, dx, dy):
        dx_adj = self._calc_adjustment_x(dx)
        dy_adj = self._calc_adjustment_y(dy)

        if dx != 0:
            logger.debug(f"1dx={dx} and full dx_adj={dx_adj}")
            logger.debug(f"1dy={dy} and full dx_adj={dy_adj}")

        return (dx + dx_adj) * self.resource.mult_x, (dy + dy_adj) * self.resource.mult_y

    def approach_by_distance(self, dx: int, dy: int, tolerated: bool = True):
        if dx == 0 and dy == 0:
            return
        if not tolerated:
            dx = dx - self.resource.get_tol_x() if dx > 0 else dx + self.resource.get_tol_x()
            dy = dy - self.resource.get_tol_y() if dy > 0 else dy + self.resource.get_tol_y()

        dy_step = 0
        dx_step = 0

        dx_in_ms, dy_in_ms = self.get_dx_dy(dx, dy)
        # Y axis
        if abs(dy) > self.resource.get_tol_y():
            run(False, dy_in_ms)
            dy_step = dy

        # X axis
        if abs(dx) > self.resource.get_tol_x():
            run(True, dx_in_ms)
            dx_step = dx

        self._apply_step(dx_step, dy_step)

    def is_start_position(self):
        return self.pos_x == 0 and self.pos_y == 0
