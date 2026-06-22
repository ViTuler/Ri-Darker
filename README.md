# Ri-Darker

Force a dark theme on any Windows application — even ones that don't support it natively.

## Features

- **Win32 dark-mode enforcement** — uses `DwmSetWindowAttribute` and `SetWindowTheme` to flip the dark-mode flag on target window title bars and common controls.
- **Per-app customisation** — configure a different window theme and custom caption / border / text colours for every application (Windows 11 colour overrides).
- **System-tray controller** — a PySide6 tray icon keeps Ri-Darker running silently in the background; double-click (or right-click → Open Controller) to manage apps.
- **YAML configuration** — all settings are stored in `config.yaml` next to the executable, editable by hand or through the GUI.

## Requirements

| Package | Purpose |
|---------|---------|
| `PySide6 >= 6.5` | GUI & tray icon |
| `pywin32 >= 305` | Win32 API (DWM, UxTheme, window enumeration) |
| `psutil >= 5.9` | Map window handles to process names |
| `PyYAML >= 6.0` | Configuration file |

> **Windows only.** The Win32 APIs used here are not available on other platforms.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Run directly
python -m src.main

# Or
python src/main.py
```

The app starts minimised to the system tray. Right-click the tray icon to open the controller or exit.

## Configuration

`config.yaml` is created automatically on first launch. Example:

```yaml
settings:
  monitor_interval: 2      # seconds between scan passes
  start_minimized: true

apps:
  notepad.exe:
    enabled: true
    dark_title_bar: true
    window_theme: DarkMode_Explorer
    title_bar_color: "#1e1e1e"   # Windows 11+ only
    border_color: "#3c3c3c"      # Windows 11+ only
    text_color: "#ffffff"        # Windows 11+ title-bar text only

  mspaint.exe:
    enabled: true
    dark_title_bar: true
    window_theme: DarkMode_Explorer
```

### Window themes (`window_theme`)

| Value | Effect |
|-------|--------|
| `DarkMode_Explorer` | Standard dark mode for most controls |
| `DarkMode_CFD` | Dark mode for dialogs and flyouts |
| `DarkMode_ItemsView` | Dark mode for list/tree views |
| *(empty string)* | Reset to default system theme |

> **Note:** Ri-Darker can push Win32/DWM dark-mode hints and control themes, but applications that draw their own UI (custom renderers, game engines, many Electron/Chromium surfaces, etc.) may not follow system font/background colours.

## Project structure

```
Ri-Darker/
├── src/
│   ├── main.py            # Entry point
│   ├── tray_app.py        # System-tray icon & background monitor
│   ├── config_manager.py  # YAML config read/write
│   ├── theme_engine.py    # Win32 dark-theme engine
│   └── ui/
│       ├── main_window.py # Controller window
│       └── app_dialog.py  # Add / edit application dialog
├── config.yaml            # User configuration (auto-created)
├── requirements.txt
└── README.md
```

## License

Apache 2.0 — see [LICENSE](LICENSE).