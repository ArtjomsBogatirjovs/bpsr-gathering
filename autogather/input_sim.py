try:
    import pydirectinput as pdi   # игры лучше видят этот ввод
except Exception:
    pdi = None

import pyautogui as pag          # для скролла и запасной ввод
pag.PAUSE = 0
pag.FAILSAFE = True

from .config import SCROLL_UNIT, SCROLL_DELAY

def press_key(key: str):
    if pdi:
        pdi.press(key)
    else:
        pag.press(key)

def scroll_once(unit: int = SCROLL_UNIT):
    """Одно «деление» колёсика (по умолчанию вниз)."""
    pag.scroll(unit)

def scroll_slow(steps: int = 1, unit: int = SCROLL_UNIT, delay: float = SCROLL_DELAY):
    for _ in range(max(0, steps)):
        pag.scroll(unit)
        pag.sleep(delay)
