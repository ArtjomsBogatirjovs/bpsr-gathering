# Минимальные утилиты WinAPI: перечисление окон, титулы, геометрия, поднять в фокус
import ctypes as ct
import logging
from ctypes import wintypes as wt

user32 = ct.WinDLL("user32", use_last_error=True)

EnumWindowsProc = ct.WINFUNCTYPE(ct.c_bool, wt.HWND, wt.LPARAM)

user32.EnumWindows.argtypes = [EnumWindowsProc, wt.LPARAM]
user32.EnumWindows.restype = ct.c_bool

user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = ct.c_bool

user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.restype = ct.c_int

user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ct.c_int]
user32.GetWindowTextW.restype = ct.c_int

user32.GetWindowRect.argtypes = [wt.HWND, ct.POINTER(wt.RECT)]
user32.GetWindowRect.restype = ct.c_bool

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wt.HWND

user32.ShowWindow.argtypes = [wt.HWND, ct.c_int]
user32.ShowWindow.restype = ct.c_bool

user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.SetForegroundWindow.restype = ct.c_bool

user32.SetFocus.argtypes = [wt.HWND]
user32.SetFocus.restype = wt.HWND

user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ct.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD

user32.AttachThreadInput.argtypes = [wt.DWORD, wt.DWORD, ct.c_bool]
user32.AttachThreadInput.restype = ct.c_bool

SW_RESTORE = 9

from .config import GAME_TITLE_KEYWORDS


def list_windows():
    out = []

    @EnumWindowsProc
    def _enum(hwnd, lParam):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n <= 0:
            return True
        buf = ct.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        title = buf.value.strip()
        if not title:
            return True

        if any(k in title for k in GAME_TITLE_KEYWORDS):
            out.append((int(hwnd), title))
        return True

    user32.EnumWindows(_enum, 0)
    return out


def get_window_rect(hwnd: int):
    r = wt.RECT()
    if not user32.GetWindowRect(hwnd, ct.byref(r)):
        raise OSError("GetWindowRect failed")
    return (r.left, r.top, r.right, r.bottom)


def bring_to_foreground(hwnd: int):
    """Восстановить (если свернуто) и поднять окно в фореграунд."""
    user32.ShowWindow(hwnd, SW_RESTORE)
    fg = user32.GetForegroundWindow()
    if fg == hwnd:
        return
    pid_fg = wt.DWORD(0);
    pid_hw = wt.DWORD(0)
    tid_fg = user32.GetWindowThreadProcessId(fg, ct.byref(pid_fg)) if fg else 0
    tid_hw = user32.GetWindowThreadProcessId(hwnd, ct.byref(pid_hw))
    if tid_fg and tid_hw:
        user32.AttachThreadInput(tid_fg, tid_hw, True)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(tid_fg, tid_hw, False)
    else:
        user32.SetForegroundWindow(hwnd)
    user32.SetFocus(hwnd)

logger = logging.getLogger(__name__)

def enable_dpi_awareness() -> str:
    """
    Включает DPI-awareness процесса. Возвращает строку с тем, какой способ сработал.
    Пишет подробные логи, чтобы было видно, на каком шаге что-то пошло не так.
    """
    # Попытка 1: Win10+ Per-Monitor v2
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        ctx = ct.c_void_p(-4 & 0xFFFFFFFFFFFFFFFF)  # безопасно для 64/32 бит
        res = user32.SetProcessDpiAwarenessContext(ctx)
        if res:  # non-zero == success
            logger.info("DPI: SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2) — OK")
            return "PerMonitorV2"
        else:
            # иногда возвращает 0 при уже включённом DPI-aware; логируем код ошибки
            err = ct.GetLastError()
            logger.debug(f"DPI: SetProcessDpiAwarenessContext returned 0 (GetLastError={err})")
    except Exception as e:
        logger.debug(f"DPI: SetProcessDpiAwarenessContext not available: {e!r}")

    # Попытка 2: Win 8.1+ Per-Monitor
    try:
        shcore = ct.windll.shcore
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        hr = shcore.SetProcessDpiAwareness(2)
        if hr == 0:  # S_OK
            logger.info("DPI: SetProcessDpiAwareness(PER_MONITOR) — OK")
            return "PerMonitor"
        else:
            logger.debug(f"DPI: SetProcessDpiAwareness returned HR=0x{hr:08X}")
    except Exception as e:
        logger.debug(f"DPI: SetProcessDpiAwareness not available: {e!r}")

    # Попытка 3: Старый способ (System DPI)
    try:
        ok = user32.SetProcessDPIAware()
        logger.info(f"DPI: SetProcessDPIAware(System) — {'OK' if ok else 'already set?'}")
        return "System"
    except Exception as e:
        logger.warning(f"DPI: SetProcessDPIAware failed: {e!r}")
        return "None"         # System DPI (fallback)