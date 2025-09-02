import threading

import numpy as np
from mss import mss

from .winutil import get_window_rect


class Screen:
    """Захват монитора целиком (fallback)."""

    def __init__(self, monitor_index: int = 1):
        self.monitor_index = int(monitor_index)
        self._tls = threading.local()

    def _sct(self):
        if not hasattr(self._tls, "sct"):
            self._tls.sct = mss()
        return self._tls.sct

    def _mon(self):
        s = self._sct()
        return s.monitors[self.monitor_index] if len(s.monitors) > self.monitor_index else s.monitors[0]

    def grab_bgr(self):
        s = self._sct();
        m = self._mon()
        img = s.grab(m)
        return np.array(img)[:, :, :3]

    def dims(self):
        m = self._mon()
        return m["width"], m["height"]


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
