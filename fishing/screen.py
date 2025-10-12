import threading

import cv2
import numpy as np
from mss import mss

from .AspectRatio import AspectRatio
from .winutil import get_window_rect


class WindowScreen:
    """Захват прямоугольника конкретного окна."""

    def __init__(self, hwnd: int):
        self.hwnd = int(hwnd)
        self._tls = threading.local()

    def _sct(self):
        if not hasattr(self._tls, "sct"):
            self._tls.sct = mss()
        return self._tls.sct

    def grab_bgr(self):
        left, top, right, bottom = get_window_rect(self.hwnd)
        w, h = right - left, bottom - top
        if w <= 1 or h <= 1:
            return None
        mon = {"left": left, "top": top, "width": w, "height": h}
        img = self._sct().grab(mon)
        return np.array(img)[:, :, :3]

    def dims(self):
        left, top, right, bottom = get_window_rect(self.hwnd)
        return (right - left), (bottom - top)


def roi_convert(roi: tuple[float, float, float, float], x_ratio: int, y_ratio: int) -> tuple[
    float, float, float, float]:
    """
    Конвертирует ROI из 16:9 в новый аспект (например, 21:9).
    Сохраняем прямоугольник по центру экрана: добавленные поля по бокам
    равномерно распределяются.
    """
    x1, y1, x2, y2 = roi

    w_from, h_from = 16, 9
    w_to, h_to = x_ratio, y_ratio

    # абсолютные "условные" координаты
    X1 = x1 * w_from
    X2 = x2 * w_from

    # смещение (добавленное пространство слева)
    offset = (w_to - w_from) / 2

    # нормализация в новую ширину
    x1_new = (X1 + offset) / w_to
    x2_new = (X2 + offset) / w_to

    # высота: если одинаковая, не меняем
    if h_from == h_to:
        y1_new, y2_new = y1, y2
    else:
        y1_new = (y1 * h_from) / h_to
        y2_new = (y2 * h_from) / h_to

    return x1_new, y1_new, x2_new, y2_new