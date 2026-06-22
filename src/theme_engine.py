"""
theme_engine.py — Win32 dark-theme enforcement.

Uses:
  - DwmSetWindowAttribute  to flip the immersive-dark-mode flag on a window's
    title bar, and (on Windows 11) to set custom caption / border / text colours.
  - SetWindowTheme (UxTheme) to redirect the visual-style of common controls to
    one of Windows' built-in dark-mode sub-themes.
  - EnumWindows + psutil to locate all top-level windows belonging to a given
    process name.
"""

import ctypes
import ctypes.wintypes
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import win32gui
    import win32process

    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False
    logger.warning("pywin32 not available — window enumeration disabled.")

try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False
    logger.warning("psutil not available — process lookup disabled.")

# ---------------------------------------------------------------------------
# DWM attribute IDs
# ---------------------------------------------------------------------------
_DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19  # Windows 10 before 20H1
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20      # Windows 10 20H1+
_DWMWA_BORDER_COLOR = 34                 # Windows 11+
_DWMWA_CAPTION_COLOR = 35               # Windows 11+
_DWMWA_TEXT_COLOR = 36                  # Windows 11+

# Sentinel that resets a DWM colour attribute to its system default
_DWMWA_COLOR_DEFAULT = 0xFFFFFFFF

# Messages used to force controls to re-evaluate theme colours
_WM_THEMECHANGED = 0x031A
_WM_SETTINGCHANGE = 0x001A
_SMTO_ABORTIFHUNG = 0x0002

# Undocumented uxtheme preferred app mode values
_PREFERRED_APP_MODE_ALLOW_DARK = 1


def _hex_to_colorref(hex_color: str) -> int:
    """Convert *#RRGGBB* hex string to a Windows COLORREF (0x00BBGGRR)."""
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return (b << 16) | (g << 8) | r


class ThemeEngine:
    """Applies and removes dark-mode attributes on Win32 windows."""

    def __init__(self) -> None:
        self._dwmapi: Optional[ctypes.WinDLL] = None
        self._uxtheme: Optional[ctypes.WinDLL] = None
        self._user32: Optional[ctypes.WinDLL] = None
        self._allow_dark_mode_for_window: Optional[Callable[[int, bool], bool]] = None
        self._set_preferred_app_mode: Optional[Callable[[int], int]] = None
        self._flush_menu_themes: Optional[Callable[[], None]] = None
        self._load_libraries()

    # ------------------------------------------------------------------
    # Library loading
    # ------------------------------------------------------------------

    def _load_libraries(self) -> None:
        try:
            self._dwmapi = ctypes.windll.dwmapi
            self._uxtheme = ctypes.windll.uxtheme
            self._user32 = ctypes.windll.user32
            self._load_undocumented_uxtheme_apis()
        except (OSError, AttributeError) as exc:
            logger.warning("Could not load Windows DLLs: %s", exc)

    def _load_undocumented_uxtheme_apis(self) -> None:
        if self._uxtheme is None:
            return
        try:
            kernel32 = ctypes.windll.kernel32
            get_proc = kernel32.GetProcAddress
            get_proc.argtypes = [ctypes.wintypes.HMODULE, ctypes.c_char_p]
            get_proc.restype = ctypes.c_void_p

            def _load_ordinal(name: bytes, prototype: Any) -> Optional[Callable]:
                addr = get_proc(self._uxtheme._handle, name)
                if not addr:
                    return None
                return prototype(addr)

            allow_proto = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.wintypes.HWND,
                ctypes.c_bool,
            )
            app_mode_proto = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int)
            flush_proto = ctypes.WINFUNCTYPE(None)

            self._allow_dark_mode_for_window = _load_ordinal(b"#133", allow_proto)
            self._set_preferred_app_mode = _load_ordinal(b"#135", app_mode_proto)
            self._flush_menu_themes = _load_ordinal(b"#136", flush_proto)

            if self._set_preferred_app_mode is not None:
                self._set_preferred_app_mode(_PREFERRED_APP_MODE_ALLOW_DARK)
                if self._flush_menu_themes is not None:
                    self._flush_menu_themes()
        except Exception as exc:
            logger.debug("Could not load undocumented uxtheme APIs: %s", exc)

    # ------------------------------------------------------------------
    # Low-level DWM helpers
    # ------------------------------------------------------------------

    def _dwm_set_int(self, hwnd: int, attribute: int, value: int) -> bool:
        if self._dwmapi is None:
            return False
        try:
            c_val = ctypes.c_int(value)
            hr = self._dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(c_val), ctypes.sizeof(c_val)
            )
            return hr == 0
        except OSError as exc:
            logger.debug("DwmSetWindowAttribute(%d, %d) failed: %s", hwnd, attribute, exc)
            return False

    def _ux_set_theme(self, hwnd: int, sub_app_name: str) -> bool:
        if self._uxtheme is None:
            return False
        try:
            hr = self._uxtheme.SetWindowTheme(hwnd, sub_app_name, None)
            return hr == 0
        except OSError as exc:
            logger.debug("SetWindowTheme(%d, %r) failed: %s", hwnd, sub_app_name, exc)
            return False

    def _allow_window_dark_mode(self, hwnd: int) -> bool:
        if self._allow_dark_mode_for_window is None:
            return False
        try:
            return bool(self._allow_dark_mode_for_window(hwnd, True))
        except Exception as exc:
            logger.debug("AllowDarkModeForWindow(%d) failed: %s", hwnd, exc)
            return False

    def _notify_theme_change(self, hwnd: int) -> None:
        if self._user32 is None:
            return
        try:
            self._user32.SendMessageTimeoutW(
                hwnd,
                _WM_THEMECHANGED,
                0,
                0,
                _SMTO_ABORTIFHUNG,
                100,
                None,
            )
            self._user32.SendMessageTimeoutW(
                hwnd,
                _WM_SETTINGCHANGE,
                0,
                0,
                _SMTO_ABORTIFHUNG,
                100,
                None,
            )
            self._user32.RedrawWindow(hwnd, None, None, 0x0001 | 0x0004 | 0x0400)
        except Exception as exc:
            logger.debug("Theme refresh failed for hwnd %d: %s", hwnd, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_dark_theme(self, hwnd: int, app_config: Dict[str, Any]) -> bool:
        """
        Apply dark-mode attributes to *hwnd* according to *app_config*.

        Returns ``True`` if at least one attribute was applied successfully.
        """
        applied = False

        # 1. Immersive dark title bar
        if app_config.get("dark_title_bar", True):
            ok = self._dwm_set_int(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, 1)
            if not ok:
                self._dwm_set_int(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, 1)
            applied = True

        descendants = self._list_child_windows(hwnd)

        # 2. Hint controls to opt in to dark rendering when supported
        if self._allow_window_dark_mode(hwnd):
            applied = True
        for child in descendants:
            self._allow_window_dark_mode(child)

        # 3. UxTheme sub-app name for common controls
        window_theme: str = app_config.get("window_theme", "DarkMode_Explorer") or ""
        if window_theme:
            self._ux_set_theme(hwnd, window_theme)
            for child in descendants:
                self._ux_set_theme(child, window_theme)
            applied = True

        # 4. Windows-11-only caption / border / text colours
        title_bar_color: Optional[str] = app_config.get("title_bar_color")
        if title_bar_color:
            self._dwm_set_int(hwnd, _DWMWA_CAPTION_COLOR, _hex_to_colorref(title_bar_color))

        border_color: Optional[str] = app_config.get("border_color")
        if border_color:
            self._dwm_set_int(hwnd, _DWMWA_BORDER_COLOR, _hex_to_colorref(border_color))

        text_color: Optional[str] = app_config.get("text_color")
        if text_color:
            self._dwm_set_int(hwnd, _DWMWA_TEXT_COLOR, _hex_to_colorref(text_color))

        # Force controls to re-fetch theme brushes/colours.
        self._notify_theme_change(hwnd)
        for child in descendants:
            self._notify_theme_change(child)

        return applied

    def restore_default_theme(self, hwnd: int) -> None:
        """Remove all dark-mode overrides from *hwnd*."""
        self._dwm_set_int(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, 0)
        self._dwm_set_int(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, 0)
        self._dwm_set_int(hwnd, _DWMWA_CAPTION_COLOR, _DWMWA_COLOR_DEFAULT)
        self._dwm_set_int(hwnd, _DWMWA_BORDER_COLOR, _DWMWA_COLOR_DEFAULT)
        self._dwm_set_int(hwnd, _DWMWA_TEXT_COLOR, _DWMWA_COLOR_DEFAULT)
        self._ux_set_theme(hwnd, "")

    def find_windows_by_process(self, process_name: str) -> List[int]:
        """Return all visible top-level window handles for *process_name*."""
        if not _WIN32_AVAILABLE or not _PSUTIL_AVAILABLE:
            return []

        target = process_name.lower()
        matching_pids: set = set()

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == target:
                    matching_pids.add(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not matching_pids:
            return []

        result: List[int] = []

        def _callback(hwnd: int, _: Any) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid in matching_pids:
                    result.append(hwnd)
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(_callback, None)
        except Exception as exc:
            logger.debug("EnumWindows error: %s", exc)

        return result

    def apply_to_process(
        self, process_name: str, app_config: Dict[str, Any]
    ) -> int:
        """
        Apply dark theme to every top-level window owned by *process_name*.

        Returns the number of windows successfully patched.
        """
        if not app_config.get("enabled", True):
            return 0

        windows = self.find_windows_by_process(process_name)
        count = 0
        for hwnd in windows:
            try:
                if self.apply_dark_theme(hwnd, app_config):
                    count += 1
            except Exception as exc:
                logger.debug("Failed to apply theme to hwnd %d: %s", hwnd, exc)
        return count

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _list_child_windows(self, hwnd: int) -> List[int]:
        """Return all child windows of *hwnd* via EnumChildWindows."""
        if not _WIN32_AVAILABLE:
            return []
        children: List[int] = []
        try:
            win32gui.EnumChildWindows(
                hwnd,
                lambda child, _: children.append(child) or True,
                None,
            )
        except Exception:
            return []
        return children
