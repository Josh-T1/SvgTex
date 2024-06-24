from PyQt6.QtWidgets import QApplication
import sys
from .window import MainWindow
from . import tools
import logging
import logging.config
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"
def get_config():
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    return config

config = get_config()
logging.config.dictConfig(config = config['vector-graphics-logging-config'])
logger = logging.getLogger(__name__)

def main():
    app = QApplication([])
    window = MainWindow()

    cont = tools.DrawingController()
    handler = tools.NullDrawingHandler(cont.handler_signal)
    cont.setHandler(handler)
    window.setController(cont)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

