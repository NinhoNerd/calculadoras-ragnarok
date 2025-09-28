# src/calc_app/__main__.py
"""
App entry point.

Run with:
    python -m calc_app
"""
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from .config import APP_NAME, ORG_NAME, APP_VERSION
from .app_state import AppState
from .gui.main_window import create_main_window
from .gui.icons import icon_for_skill


def main() -> int:

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")

    app_icon = icon_for_skill("farmacologia_avancada") or QIcon()
    app.setWindowIcon(app_icon)

    state = AppState()
    win = create_main_window(state)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
