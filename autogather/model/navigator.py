# autogather/navigator.py
import logging
import time

from autogather.config import (
    APPROACH_PAUSE
)
from autogather.enums.resource import DEFAULT_TOLERANCE_Y, DEFAULT_TOLERANCE_X
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
        self.y_teach = 1.3

    def _apply_step(self, dx_step: int, dy_step: int):
        self.pos_x += int(dx_step)
        self.pos_y += int(dy_step)

    def get_dx_dy(self, dx, dy):
        if abs(dx) > 2500:
            dx_adj = dx * 0.75
        elif abs(dx) > 2250:
            dx_adj = dx * 0.7
        elif abs(dx) > 1750:
            dx_adj = dx * 0.64
        elif abs(dx) > 1500:
            dx_adj = dx * 0.57
        elif abs(dx) > 1250:
            dx_adj = dx * 0.72
        elif abs(dx) > 1000:
            dx_adj = dx * 0.74
        elif abs(dx) > 750:
            dx_adj = dx * 0.76
        elif abs(dx) > 500:
            dx_adj = dx * 0.73
        # elif abs(dx) > 250:
        # dx_adj = dx * 0.6
        elif abs(dx) > 250:
            dx_adj = dx * 0.5
        else:
            dx_adj = dx * 0
        dy_taught = dy * self.y_teach

        if dx != 0:
            logger.debug(f"1dx={dx}  and full dx_adj={dx_adj}")
            logger.debug(f"NAUCHIL={self.y_teach}")
        return dx + dx_adj, dy_taught

    def approach_by_distance(self, dx: int, dy: int):
        dx_step = 0
        dy_step = 0
        dx_in_ms, dy_in_ms = self.get_dx_dy(dx, dy)
        # Y axis
        if abs(dy) > DEFAULT_TOLERANCE_Y:
            run(False, dy_in_ms)
            dy_step = dy

        # X axis
        if abs(dx) > DEFAULT_TOLERANCE_X:
            run(True, dx_in_ms)
            dx_step = dx

        self._apply_step(dx_step, dy_step)
