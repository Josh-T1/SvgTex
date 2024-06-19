from PyQt6.QtWidgets import QApplication
import sys
from .window import MainWindow
from . import tools

def main():
    app = QApplication([])
    window = MainWindow()
    handler = tools.LineDrawingHandler()
    window.graphics_view.setDrawingHandler(handler)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

