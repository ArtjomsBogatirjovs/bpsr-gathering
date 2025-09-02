import threading
import numpy as np
from mss import mss

class Screen:
    """Захват экрана. MSS инстанс хранится в thread-local (безопасно для потоков)."""
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
        s = self._sct(); m = self._mon()
        img = s.grab(m)
        return np.array(img)[:, :, :3]  # BGR

    def dims(self):
        m = self._mon()
        return m["width"], m["height"]
