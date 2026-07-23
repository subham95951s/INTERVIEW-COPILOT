"""
Windows Stealth Overlay utility for InterviewCopilot AI.
Applies SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE) to hide windows
from screen sharing tools (Zoom, Microsoft Teams, Google Meet, OBS).
"""

import ctypes
import sys
import structlog

log = structlog.get_logger()

# Windows API constants
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Windows 10 2004+


def apply_stealth_to_hwnd(hwnd: int) -> bool:
    """
    Exclude a window handle (HWND) from Windows desktop duplication & capture APIs.
    The window remains visible to the local user on their monitor, but is completely
    invisible / blacked out during Zoom, Teams, Google Meet screen share or recording.
    """
    if sys.platform != "win32":
        log.warning("SetWindowDisplayAffinity is Windows-only")
        return False

    try:
        user32 = ctypes.windll.user32
        result = user32.SetWindowDisplayAffinity(ctypes.c_void_p(hwnd), WDA_EXCLUDEFROMCAPTURE)
        if result != 0:
            log.info("Successfully applied WDA_EXCLUDEFROMCAPTURE to window", hwnd=hwnd)
            return True
        else:
            err = ctypes.GetLastError()
            log.warning("SetWindowDisplayAffinity failed", hwnd=hwnd, win32_error=err)
            return False
    except Exception as e:
        log.error("Error applying stealth to window handle", error=str(e))
        return False


def find_and_hide_window_by_title(window_title: str) -> bool:
    """
    Find open window matching title and exclude it from screen capture.
    """
    if sys.platform != "win32":
        return False

    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, window_title)
    if not hwnd:
        log.warning("Window title not found", title=window_title)
        return False

    return apply_stealth_to_hwnd(hwnd)
