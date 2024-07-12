import argparse as arg
from PyQt6.QtWidgets import QApplication
import sys
from .utils import load_shortcuts
from .graphics.window import MainWindow
from .drawing import tools
import logging
import logging.config
from pathlib import Path
from .control.shortcut_manager import ShortcutManager
from .control.drawing_controller import DrawingController
from .utils import lazy_import, load_shortcuts, config


logging.config.dictConfig(config = config['vector-graphics-logging-config'])
logger = logging.getLogger(__name__)

global_parser = arg.ArgumentParser(prog="vector-graphics", description="vector graphics drawing gui")
global_parser.add_argument("-f", "--file", nargs=1, action="store")

def main():
    args = global_parser.parse_args()

    app = QApplication([])
    window = MainWindow()
    cont = DrawingController()
    # remove scene probably
    shortcut_manager = ShortcutManager(window._scene, window.closeEvent)
#    shortcuts_module = lazy_import(config["user-shortcuts-path"])
#    print(shortcuts_module, "m")
#    if shortcuts_module:
#        shortcuts = load_shortcuts(shortcuts_module)
#        shortcut_manager.add_shortcut(shortcuts)

    handler = tools.NullDrawingHandler(cont.handler_signal)
    cont.setHandler(handler)
    cont.setShortcutManager(shortcut_manager)
    window.setController(cont)
    file = args.file

    if file and str(file[0]).endswith(".svg") and Path(file[0]).is_file():
        window.open_with_svg(file[0])

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
