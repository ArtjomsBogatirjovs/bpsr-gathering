try:
    import pydirectinput as pdi
except Exception:
    pdi = None

import time

import pyautogui as pag

pag.PAUSE = 0
pag.FAILSAFE = True

from .config import SCROLL_UNIT, SCROLL_DELAY


def press_key(key: str):
    if pdi:
        pdi.press(key)
    else:
        pag.press(key)


def key_down(key: str):
    if pdi:
        pdi.keyDown(key)
    else:
        pag.keyDown(key)


def key_up(key: str):
    if pdi:
        pdi.keyUp(key)
    else:
        pag.keyUp(key)


def hold_key_ms(key: str, ms: int):
    """Удержание клавиши на заданное кол-во миллисекунд."""
    key_down(key)
    try:
        time.sleep(max(0, ms) / 1000.0)
    finally:
        key_up(key)


def move_mouse_rel(dx: int, dy: int):
    """Плавный относительный сдвиг мыши. Только целые!"""
    if pdi:
        pdi.moveRel(int(dx), int(dy))
    else:
        pag.moveRel(int(dx), int(dy))


def scroll_once(unit: int = SCROLL_UNIT):
    pag.scroll(unit)


def scroll_slow(steps: int = 1, unit: int = SCROLL_UNIT, delay: float = SCROLL_DELAY):
    for _ in range(max(0, steps)):
        pag.scroll(unit)
        time.sleep(delay)
