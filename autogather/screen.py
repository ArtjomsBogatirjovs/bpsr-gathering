import threading

import cv2
import numpy as np
from mss import mss

from autogather.enums.aspect_ratio import AspectRatio
from .config import PROMPT_ROI
from .winutil import get_window_rect


class WindowScreen:
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


def aspect_ration_convert_from_16_9(roi: tuple[float, float, float, float], x_ratio: int, y_ratio: int) -> tuple[
    float, float, float, float]:
    x1, y1, x2, y2 = roi

    w_from, h_from = 16, 9
    w_to, h_to = x_ratio, y_ratio

    X1 = x1 * w_from
    X2 = x2 * w_from

    offset = (w_to - w_from) / 2

    x1_new = (X1 + offset) / w_to
    x2_new = (X2 + offset) / w_to

    if h_from == h_to:
        y1_new, y2_new = y1, y2
    else:
        y1_new = (y1 * h_from) / h_to
        y2_new = (y2 * h_from) / h_to

    return x1_new, y1_new, x2_new, y2_new


def _get_selector_rectangle(screen: WindowScreen, ratio: AspectRatio, roi_promt = PROMPT_ROI):
    frame = screen.grab_bgr()
    if frame is None:
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape[:2]
    x1_k, y1_k, x2_k, y2_k = aspect_ration_convert_from_16_9((roi_promt[0], roi_promt[1], roi_promt[2], roi_promt[3]), ratio.x, ratio.y)
    x1 = int(W * x1_k)
    y1 = int(H * y1_k)
    x2 = int(W *  x2_k)
    y2 = int(H * y2_k)
    roi = gray[y1:y2, x1:x2]
    return roi, (x1, y1, x2, y2)