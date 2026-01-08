import sys
import logging
from PyQt6.QtWidgets import QApplication
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
