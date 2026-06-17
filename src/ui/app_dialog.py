"""
app_dialog.py — Dialog for adding or editing a target application entry.
"""

from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

_WINDOW_THEMES = [
    ("DarkMode_Explorer", "DarkMode_Explorer — standard dark controls"),
    ("DarkMode_CFD",      "DarkMode_CFD — dialog / flyout controls"),
    ("DarkMode_ItemsView","DarkMode_ItemsView — list / tree views"),
    ("",                  "(none)"),
]


class _ColorButton(QPushButton):
    """Push-button that displays and lets the user pick a hex colour."""

    def __init__(self, color: Optional[str] = None, parent=None) -> None:
        super().__init__(parent)
        self._color: Optional[str] = color
        self._refresh()
        self.clicked.connect(self._pick)

    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        if self._color:
            self.setText(self._color)
            light = self._is_light(self._color)
            fg = "#000000" if light else "#ffffff"
            self.setStyleSheet(
                f"background-color: {self._color}; color: {fg}; border: 1px solid #888;"
            )
        else:
            self.setText("(default)")
            self.setStyleSheet("")

    @staticmethod
    def _is_light(hex_color: str) -> bool:
        c = QColor(hex_color)
        return (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000 > 128

    def _pick(self) -> None:
        initial = QColor(self._color) if self._color else QColor("#1e1e1e")
        picked = QColorDialog.getColor(initial, self, "Select Colour")
        if picked.isValid():
            self._color = picked.name().lower()
            self._refresh()

    # ------------------------------------------------------------------

    def color(self) -> Optional[str]:
        return self._color

    def set_color(self, color: Optional[str]) -> None:
        self._color = color
        self._refresh()

    def clear(self) -> None:
        self._color = None
        self._refresh()


class AppDialog(QDialog):
    """Dialog for adding (or editing) a target-application entry."""

    def __init__(
        self,
        process_name: str = "",
        app_config: Optional[Dict[str, Any]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._editing = bool(process_name)
        self.setWindowTitle("Edit Application" if self._editing else "Add Application")
        self.setMinimumWidth(440)
        self._build_ui(process_name, app_config or {})

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, process_name: str, cfg: Dict[str, Any]) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ---- Basic info ----
        basic_form = QFormLayout()
        basic_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._edit_name = QLineEdit(process_name)
        self._edit_name.setPlaceholderText("e.g. notepad.exe")
        if self._editing:
            self._edit_name.setReadOnly(True)
        basic_form.addRow("Process name:", self._edit_name)

        self._chk_enabled = QCheckBox()
        self._chk_enabled.setChecked(cfg.get("enabled", True))
        basic_form.addRow("Enabled:", self._chk_enabled)

        root.addLayout(basic_form)

        # ---- DWM / title-bar group ----
        dwm_box = QGroupBox("Title Bar  (DWM)")
        dwm_form = QFormLayout(dwm_box)
        dwm_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._chk_dark_title = QCheckBox()
        self._chk_dark_title.setChecked(cfg.get("dark_title_bar", True))
        dwm_form.addRow("Dark title bar:", self._chk_dark_title)

        self._btn_caption = _ColorButton(cfg.get("title_bar_color"))
        dwm_form.addRow("Caption colour\n(Windows 11+):", self._color_row(self._btn_caption))

        self._btn_border = _ColorButton(cfg.get("border_color"))
        dwm_form.addRow("Border colour\n(Windows 11+):", self._color_row(self._btn_border))

        self._btn_text = _ColorButton(cfg.get("text_color"))
        dwm_form.addRow("Text colour\n(Windows 11+):", self._color_row(self._btn_text))

        root.addWidget(dwm_box)

        # ---- UxTheme group ----
        ux_box = QGroupBox("Controls Theme  (UxTheme / SetWindowTheme)")
        ux_form = QFormLayout(ux_box)
        ux_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._combo_theme = QComboBox()
        for value, label in _WINDOW_THEMES:
            self._combo_theme.addItem(label, value)

        current = cfg.get("window_theme", "DarkMode_Explorer")
        idx = self._combo_theme.findData(current)
        self._combo_theme.setCurrentIndex(idx if idx >= 0 else 0)
        ux_form.addRow("Sub-app theme:", self._combo_theme)

        note = QLabel(
            "Ri-Darker applies the chosen theme to the window and all its child controls.\n"
            "Most applications respond to <b>DarkMode_Explorer</b>."
        )
        note.setWordWrap(True)
        ux_form.addRow(note)

        root.addWidget(ux_box)

        # ---- Buttons ----
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _color_row(btn: _ColorButton) -> QHBoxLayout:
        clear = QPushButton("Clear")
        clear.setFixedWidth(55)
        clear.clicked.connect(btn.clear)
        row = QHBoxLayout()
        row.addWidget(btn)
        row.addWidget(clear)
        return row

    def _validate_and_accept(self) -> None:
        if not self._edit_name.text().strip():
            self._edit_name.setFocus()
            return
        self.accept()

    # ------------------------------------------------------------------
    # Public result
    # ------------------------------------------------------------------

    def get_data(self) -> Dict[str, Any]:
        """Return the dialog values as a dict suitable for ConfigManager."""
        return {
            "process_name": self._edit_name.text().strip().lower(),
            "enabled": self._chk_enabled.isChecked(),
            "dark_title_bar": self._chk_dark_title.isChecked(),
            "title_bar_color": self._btn_caption.color(),
            "border_color": self._btn_border.color(),
            "text_color": self._btn_text.color(),
            "window_theme": self._combo_theme.currentData(),
        }
