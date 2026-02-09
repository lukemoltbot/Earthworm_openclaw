import sys
import logging

# PyQt version-agnostic imports (matching main_window.py)
try:
    from PyQt6.QtWidgets import QApplication
    PYQT_VERSION = 6
except ImportError:
    from PyQt5.QtWidgets import QApplication
    PYQT_VERSION = 5

from src.ui.main_window import MainWindow

if __name__ == "__main__":
    # Configure logging to output to console
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.StreamHandler(sys.stdout)
                        ])

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
