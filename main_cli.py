import argparse as arg
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import sys
from .utils import load_shortcuts
from .gui.window import MainWindow
from .drawing import tools
import logging
import logging.config
from pathlib import Path
from .drawing.drawing_controller import DrawingController
from .utils import lazy_import, load_shortcuts, config


logging.config.dictConfig(config = config['vector-graphics-logging-config'])
logger = logging.getLogger(__name__)

global_parser = arg.ArgumentParser(prog="vector-graphics", description="vector graphics drawing gui")
global_parser.add_argument("-f", "--file", nargs=1, action="store")

def main():
    args = global_parser.parse_args()

    app = QApplication([])

    window = MainWindow()
    window.add_shortcut(Qt.Key.Key_T, lambda: print("hello"), "teset" )
    cont = DrawingController()
    # remove scene probably
#    shortcuts_module = lazy_import("user_shortcuts", config["user-shortcuts-path"], "VectorGraphics.shortcuts")
#    print(shortcuts_module, "m")
#    if shortcuts_module:
#        print("successfully loaded")
#        shortcuts = load_shortcuts(shortcuts_module)
#        shortcut_manager.add_shortcut(shortcuts)

    handler = tools.NullDrawingHandler(cont.handler_signal)
    cont.setHandler(handler)
    window.setController(cont)
    file_args = args.file
    if file_args and str(file_args[0]).endswith(".svg") and Path(file_args[0]).is_file():
        window.open_with_svg(file_args[0])

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
