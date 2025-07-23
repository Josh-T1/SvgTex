import argparse as arg
import sys
import logging
import logging.config
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from .drawing.drawing_controller import DrawingController
from .utils import config
from .utils import load_shortcuts
from .gui.window import MainWindow
from .drawing import tools


logging.config.dictConfig(config = config['vector-graphics-logging-config'])
logger = logging.getLogger(__name__)

global_parser = arg.ArgumentParser(prog="vector-graphics", description="vector graphics drawing gui")
global_parser.add_argument("-f", "--file", nargs=1, action="store")
global_parser.add_argument('-d', "--dir", nargs=1, action="store")
global_parser.add_argument("--height", nargs=1, action="store", type=int, default=[781])
global_parser.add_argument("--width", nargs=1, action="store", type=int, default=[561])

def main():
    args = global_parser.parse_args()

    app = QApplication([])

    height = args.height[0]
    width = args.width[0]
    window = MainWindow(height=height, width=width)
    cont = DrawingController()

    handler = tools.NullDrawingHandler(cont.handler_signal)
    cont.setHandler(handler)
    window.setController(cont)
    file_args = args.file
    if file_args and str(file_args[0]).endswith(".svg"):
        file = Path(file_args[0])
        if not file.is_file():
            file.touch()
        window.open_with_svg(file_args[0], args.dir)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
