# autogather/worker.py
import threading

from fishing.input_sim import click


class Worker(threading.Thread):
    def __init__(self,screen, change_rod: bool, buy_rod:bool):
        super().__init__(daemon=True)
        self.screen = screen
        self.change_rod = change_rod
        self.buy_rod = buy_rod
        self._stop = threading.Event()
        self.state = "idle"

    # ---- helpers ----
    def stop(self):
        self._stop.set()

    # ---- main loop ----
    def run(self):
        while not self._stop.is_set():
            self._start_fishing()


    def _start_fishing(self):
        click()
