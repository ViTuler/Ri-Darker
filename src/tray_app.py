"""
tray_app.py — System-tray entry point for Ri-Darker.

Keeps the app alive in the background and periodically re-applies dark themes
to any running processes listed in the configuration.
"""

import logging
from typing import Optional

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from src.config_manager import ConfigManager
from src.theme_engine import ThemeEngine

logger = logging.getLogger(__name__)


def _make_tray_icon() -> QIcon:
    """Draw a simple crescent-moon icon programmatically."""
    size = 32
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Full circle (moon body)
    painter.setBrush(QColor(180, 180, 255))
    painter.setPen(QColor(0, 0, 0, 0))
    painter.drawEllipse(4, 4, 24, 24)

    # Cutout to form crescent
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    painter.drawEllipse(10, 2, 22, 22)

    painter.end()
    return QIcon(pixmap)


class TrayApp(QObject):
    """Manages the system-tray icon, context menu, and monitoring timer."""

    def __init__(self, app: QApplication, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._app = app
        self.config_manager = ConfigManager()
        self.theme_engine = ThemeEngine()
        self._main_window = None

        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(_make_tray_icon())
        self._tray.setToolTip("Ri-Darker — Dark Theme Enforcer")
        self._build_menu()
        self._tray.activated.connect(self._on_activated)

        interval_ms = (
            self.config_manager.get_settings().get("monitor_interval", 2) * 1000
        )
        self._timer = QTimer(self)
        self._timer.setInterval(int(interval_ms))
        self._timer.timeout.connect(self._scan_and_apply)
        self._timer.start()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def show(self) -> None:
        self._tray.show()
        if not self.config_manager.get_settings().get("start_minimized", True):
            self._open_controller()

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu = QMenu()

        act_open = menu.addAction("Open Controller")
        act_open.triggered.connect(self._open_controller)

        menu.addSeparator()

        act_apply = menu.addAction("Apply Now")
        act_apply.triggered.connect(self._scan_and_apply)

        menu.addSeparator()

        act_quit = menu.addAction("Exit")
        act_quit.triggered.connect(self._quit)

        self._tray.setContextMenu(menu)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._open_controller()

    def _open_controller(self) -> None:
        # Import here to avoid circular dependencies
        from src.ui.main_window import MainWindow

        if self._main_window is None:
            self._main_window = MainWindow(self.config_manager, self.theme_engine)
            self._main_window.destroyed.connect(self._on_window_destroyed)
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def _on_window_destroyed(self) -> None:
        self._main_window = None

    def _scan_and_apply(self) -> None:
        apps = self.config_manager.get_apps()
        for process_name, app_config in apps.items():
            if not app_config.get("enabled", True):
                continue
            try:
                count = self.theme_engine.apply_to_process(process_name, app_config)
                if count:
                    logger.debug(
                        "Dark theme applied to %d window(s) of '%s'", count, process_name
                    )
            except Exception as exc:
                logger.error("Error processing '%s': %s", process_name, exc)

    def _quit(self) -> None:
        self._timer.stop()
        self._tray.hide()
        self._app.quit()
