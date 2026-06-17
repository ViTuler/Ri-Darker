"""
main_window.py — Controller window for Ri-Darker.

Allows the user to:
  • View all configured target applications.
  • Add, edit, or remove entries.
  • Trigger an immediate theme-application pass.
  • Adjust general settings.
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from config_manager import ConfigManager
from theme_engine import ThemeEngine
from ui.app_dialog import AppDialog


class MainWindow(QMainWindow):
    """Main controller window."""

    def __init__(
        self,
        config_manager: ConfigManager,
        theme_engine: ThemeEngine,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self.theme_engine = theme_engine

        self.setWindowTitle("Ri-Darker — Dark Theme Controller")
        self.setMinimumSize(640, 500)
        self._build_ui()
        self._reload_list()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header
        title_label = QLabel("Ri-Darker")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        sub_label = QLabel("Force dark theme on Windows applications")
        layout.addWidget(sub_label)

        # App list
        list_box = QGroupBox("Target Applications")
        list_layout = QVBoxLayout(list_box)

        self._list = QListWidget()
        self._list.setMinimumHeight(220)
        self._list.currentRowChanged.connect(self._on_row_changed)
        self._list.itemDoubleClicked.connect(self._edit_app)
        list_layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("Add")
        self._btn_edit = QPushButton("Edit")
        self._btn_remove = QPushButton("Remove")
        self._btn_edit.setEnabled(False)
        self._btn_remove.setEnabled(False)

        self._btn_add.clicked.connect(self._add_app)
        self._btn_edit.clicked.connect(self._edit_app)
        self._btn_remove.clicked.connect(self._remove_app)

        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_edit)
        btn_row.addWidget(self._btn_remove)
        btn_row.addStretch()
        list_layout.addLayout(btn_row)

        layout.addWidget(list_box)

        # Settings
        settings_box = QGroupBox("General Settings")
        settings_layout = QVBoxLayout(settings_box)

        self._chk_minimized = QCheckBox("Start minimised to tray")
        settings = self.config_manager.get_settings()
        self._chk_minimized.setChecked(settings.get("start_minimized", True))
        self._chk_minimized.toggled.connect(self._save_settings)
        settings_layout.addWidget(self._chk_minimized)

        layout.addWidget(settings_box)

        # Bottom bar
        bottom = QHBoxLayout()
        btn_apply = QPushButton("Apply Themes Now")
        btn_apply.clicked.connect(self._apply_now)
        bottom.addWidget(btn_apply)
        bottom.addStretch()
        layout.addLayout(bottom)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def _reload_list(self) -> None:
        self._list.clear()
        for process_name, cfg in self.config_manager.get_apps().items():
            enabled = cfg.get("enabled", True)
            marker = "✓" if enabled else "✗"
            item = QListWidgetItem(f"{marker}  {process_name}")
            item.setData(Qt.ItemDataRole.UserRole, process_name)
            self._list.addItem(item)

    def _current_process(self) -> Optional[str]:
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_row_changed(self, row: int) -> None:
        has = row >= 0
        self._btn_edit.setEnabled(has)
        self._btn_remove.setEnabled(has)

    def _add_app(self) -> None:
        dlg = AppDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            name = data.pop("process_name")
            if not name:
                return
            self.config_manager.add_app(name, data)
            self._reload_list()
            self.statusBar().showMessage(f"Added '{name}'", 3000)

    def _edit_app(self, *_) -> None:
        name = self._current_process()
        if not name:
            return
        cfg = self.config_manager.get_app_config(name) or {}
        dlg = AppDialog(process_name=name, app_config=cfg, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            data.pop("process_name", None)
            self.config_manager.update_app(name, data)
            self._reload_list()
            self.statusBar().showMessage(f"Updated '{name}'", 3000)

    def _remove_app(self) -> None:
        name = self._current_process()
        if not name:
            return
        reply = QMessageBox.question(
            self,
            "Remove Application",
            f"Remove <b>{name}</b> from the list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config_manager.remove_app(name)
            self._reload_list()
            self.statusBar().showMessage(f"Removed '{name}'", 3000)

    def _save_settings(self) -> None:
        settings = self.config_manager.get_settings()
        settings["start_minimized"] = self._chk_minimized.isChecked()
        self.config_manager.update_settings(settings)

    def _apply_now(self) -> None:
        total = 0
        for process_name, cfg in self.config_manager.get_apps().items():
            if cfg.get("enabled", True):
                try:
                    total += self.theme_engine.apply_to_process(process_name, cfg)
                except Exception:
                    pass
        self.statusBar().showMessage(
            f"Dark theme applied to {total} window(s)", 3000
        )
