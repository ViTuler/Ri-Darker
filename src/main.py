"""
main.py — Entry point for Ri-Darker.

Launch with:
    python -m src.main
or:
    python src/main.py
"""

import logging
import sys

from PySide6.QtWidgets import QApplication

from src.tray_app import TrayApp


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Ri-Darker")
    app.setApplicationDisplayName("Ri-Darker")
    # Keep the process alive even when all windows are closed
    app.setQuitOnLastWindowClosed(False)

    tray = TrayApp(app)
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
