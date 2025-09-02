# winutil.py — вспомогалки для работы с окнами Windows (без сторонних либ)
import ctypes as ct
from ctypes import wintypes as wt

user32 = ct.WinDLL("user32", use_last_error=True)
kernel32 = ct.WinDLL("kernel32", use_last_error=True)

# константы
SW_RESTORE = 9
SW_SHOW    = 5

# сигнатуры
EnumWindowsProc = ct.WINFUNCTYPE(ct.c_bool, wt.HWND, wt.LPARAM)

# прототипы
user32.EnumWindows.argtypes = [EnumWindowsProc, wt.LPARAM]
user32.EnumWindows.restype  = ct.c_bool

user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype  = ct.c_bool

user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.restype  = ct.c_int

user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ct.c_int]
user32.GetWindowTextW.restype  = ct.c_int

user32.GetWindowRect.argtypes = [wt.HWND, ct.POINTER(wt.RECT)]
user32.GetWindowRect.restype  = ct.c_bool

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype  = wt.HWND

user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.SetForegroundWindow.restype  = ct.c_bool

user32.SetFocus.argtypes = [wt.HWND]
user32.SetFocus.restype  = wt.HWND

user32.ShowWindow.argtypes = [wt.HWND, ct.c_int]
user32.ShowWindow.restype  = ct.c_bool

user32.IsIconic.argtypes = [wt.HWND]
user32.IsIconic.restype  = ct.c_bool

user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ct.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype  = wt.DWORD

user32.AttachThreadInput.argtypes = [wt.DWORD, wt.DWORD, ct.c_bool]
user32.AttachThreadInput.restype  = ct.c_bool


def list_windows():
    """Список видимых окон: [(hwnd, title)]"""
    out = []

    @EnumWindowsProc
    def _enum(hwnd, lParam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ct.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        if title:
            out.append((hwnd, title))
        return True

    user32.EnumWindows(_enum, 0)
    return out


def get_window_title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ct.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def get_window_rect(hwnd: int):
    """(left, top, right, bottom) в экранных координатах."""
    r = wt.RECT()
    if not user32.GetWindowRect(hwnd, ct.byref(r)):
        raise OSError("GetWindowRect failed")
    return (r.left, r.top, r.right, r.bottom)


def is_minimized(hwnd: int) -> bool:
    return bool(user32.IsIconic(hwnd))


def foreground_hwnd() -> int:
    return user32.GetForegroundWindow()


def bring_to_foreground(hwnd: int):
    """Восстановить/поднять окно в фореграунд (робастно)."""
    # восстановить, если свёрнуто
    user32.ShowWindow(hwnd, SW_RESTORE)
    fg = user32.GetForegroundWindow()
    if fg == hwnd:
        return
    # иногда требуется присоединить потоки ввода
    pid_fg = wt.DWORD(0)
    pid_hw = wt.DWORD(0)
    tid_fg = user32.GetWindowThreadProcessId(fg, ct.byref(pid_fg))
    tid_hw = user32.GetWindowThreadProcessId(hwnd, ct.byref(pid_hw))
    if tid_fg and tid_hw:
        user32.AttachThreadInput(tid_fg, tid_hw, True)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(tid_fg, tid_hw, False)
    else:
        user32.SetForegroundWindow(hwnd)
    user32.SetFocus(hwnd)
