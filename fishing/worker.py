# autogather/worker.py
import threading

class Worker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)

        self._stop = threading.Event()
        self.state = "idle"

    # ---- helpers ----
    def stop(self):
        self._stop.set()

    # ---- main loop ----
    def run(self):
        b = 1
