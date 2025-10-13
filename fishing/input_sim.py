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


def press_keys(*keys: str):
    for k in keys:
        key_down(k)
    for k in keys:
        key_up(k)


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
    if ms <= 0:
        return
    key_down(key)
    try:
        time.sleep(max(0, ms) / 1000.0)
    finally:
        key_up(key)


def move_mouse_abs(x: int = None, y: int = None):
    if pdi:
        pdi.moveTo(int(x), int(y))
    else:
        pag.moveTo(int(x), int(y))


def move_mouse_rel(dx: int = None, dy: int = None):
    if pdi:
        pdi.moveRel(int(dx), int(dy))
    else:
        pag.moveRel(int(dx), int(dy))


def scroll_once(unit: int = SCROLL_UNIT):
    pag.scroll(unit)
    time.sleep(SCROLL_DELAY)


def scroll_slow(steps: int = 1, unit: int = SCROLL_UNIT, delay: float = SCROLL_DELAY):
    for _ in range(max(0, steps)):
        pag.scroll(unit)
        time.sleep(delay)

def _hide_unhide_ui():
    press_keys('ctrl', '\\')

def mouse_down(button: str = "left"):
    """Нажать и удерживать кнопку мыши (без отпускания)."""
    if pdi:
        pdi.mouseDown(button=button)
    else:
        pag.mouseDown(button=button)


def mouse_up(button: str = "left"):
    """Отпустить ранее нажатую кнопку мыши."""
    if pdi:
        pdi.mouseUp(button=button)
    else:
        pag.mouseUp(button=button)


def click(
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0,
):
    """
    Клик мышью. Если переданы x/y — клик по абсолютным координатам.
    clicks>1 => серия кликов (например, 2 — двойной).
    """
    if x is not None and y is not None:
        x, y = int(x), int(y)

    if pdi:
        # pydirectinput имеет такой же сигнатурный интерфейс
        pdi.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
    else:
        pag.click(x=x, y=y, clicks=clicks, interval=interval, button=button)


def double_click(x: int | None = None, y: int | None = None, button: str = "left", interval: float = 0.0):
    """Двойной клик мышью."""
    click(x=x, y=y, button=button, clicks=2, interval=interval)


def right_click(x: int | None = None, y: int | None = None):
    """Правый клик."""
    click(x=x, y=y, button="right")


def middle_click(x: int | None = None, y: int | None = None):
    """Клик средней кнопкой (колёсиком)."""
    click(x=x, y=y, button="middle")


def click_hold_ms(
        ms: int,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
):
    """
    Клик с удержанием на ms миллисекунд.
    Если переданы x/y — предварительно переместится и нажмёт там.
    """
    if ms <= 0:
        # для нулевого времени — обычный клик
        return click(x=x, y=y, button=button, clicks=1)

    if x is not None and y is not None:
        move_mouse_abs(int(x), int(y))
    mouse_down(button=button)
    try:
        time.sleep(max(0, ms) / 1000.0)
    finally:
        mouse_up(button=button)
