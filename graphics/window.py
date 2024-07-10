from collections.abc import Callable
import re
import threading
from PyQt6.QtGui import QAction, QBrush, QCloseEvent, QGuiApplication, QKeyEvent, QMouseEvent, QPen, QPainter, QTransform
from PyQt6.QtCore import QByteArray, QPointF, QRect, Qt, QRectF, pyqtSignal, QEvent, QSize
from PyQt6.QtSvg import QSvgGenerator, QSvgRenderer
from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget
from PyQt6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QGestureEvent, QGraphicsItem, QGraphicsPathItem, QGraphicsSceneMouseEvent, QLabel, QMessageBox, QPinchGesture, QPushButton, QScrollArea, QSizePolicy, QToolBar, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                             QGraphicsScene, QGraphicsLineItem, QMainWindow, QGraphicsTextItem)
from matplotlib.pyplot import text
from ..drawing.tools import ClippedTextItem, DrawingController, NullDrawingHandler, Handlers, Textbox
from .graphics_items import SelectableRectItem
from pathlib import Path
import logging
from ..shortcuts.shortcuts import ShortcutCloseEvent, ShortcutManager
import io
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

UNSAVED_NAME = "No Name **"

class ToggleMenuWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.toggle_menu_layout = QVBoxLayout()

        self.initUi()
        self.setLayout(self.toggle_menu_layout)
        self.setFixedWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def initUi(self):
        self._create_widgets()
    def _create_widgets(self):
        self.label = QLabel("Item 1")
    def _add_widgets(self):
        self.toggle_menu_layout.addWidget(self.label)


class GraphicsView(QGraphicsView):
    def __init__(self, controller: None | DrawingController = None):
        super().__init__()
        self._controller =  controller
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

    def mousePressEvent(self, event):
        if self._controller and event:
            self._controller.mousePressEvent(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._controller and event:
            self._controller.mouseMoveEvent(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._controller and event:
            self._controller.mouseReleaseEvent(event)
        super().mouseReleaseEvent(event)

    def setController(self, controller):
        self._controller = controller

    def controller(self) -> DrawingController | None:
        return self._controller

    def wheelEvent(self, event):
        if event:
            event.ignore()

    def resizeEvent(self, event):
#        self.center_scene()
        dpr = self.devicePixelRatioF()
        self.setTransform(QTransform().scale(dpr, dpr))
        super().resizeEvent(event)


class ZoomableScrollArea(QScrollArea):
    """ Very possible this class does not work.. add type hinting"""
    def __init__(self, container):
        super().__init__()
#        self.view = view
        self.container = container
        self.zoom_factor = 1.5
        self.current_zoom = 1.0
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.grabGesture(Qt.GestureType.PinchGesture)
#
    def gestureEvent(self, event: QGestureEvent):
        if gesture := event.gesture(Qt.GestureType.PinchGesture):
            self.pinchTriggered(gesture, gesture.centerPoint())
            return True
        return super().event(event)

    def pinchTriggered(self, gesture: QGestureEvent, pinch_center: QPointF):
        if gesture.state() == Qt.GestureState.GestureUpdated:
            pass

    def event(self, event: QEvent): #type: ignore
        if event.type() == QEvent.Type.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

class TexGraphicsScene(QGraphicsScene):
    def __init__(self, shortcut_manager: ShortcutManager | None = None):
        super().__init__()
        self.shortcut_manager = shortcut_manager

    def setShortcutManager(self, shortcut_manager: ShortcutManager):
        self.shortcut_manager = shortcut_manager

    def keyPressEvent(self, event: QKeyEvent | None):
        if self.shortcut_manager and event:
            self.shortcut_manager.keyPress(event)
        super().keyPressEvent(event)


    def compile_latex(self):
        for item in self.items():
            print(item)
            parent = item.parentItem()
            if not isinstance(item, Textbox) or not isinstance(parent, SelectableRectItem):
                continue

            res_item = self.attempt_compile(item.text())
#
            if res_item is not None:
                global_pos = item.mapToScene(item.boundingRect().topLeft())# - parent.pos()
                res_item.setTransform(QTransform().translate(global_pos.x(), global_pos.y()))
                parent.item = res_item

                self.removeItem(item)
                item.setParentItem(None)
                del item


    def attempt_compile(self, text):
        if not self._text_is_latex(text):
            return
        svg_bytes = self.tex2svg(text)
        svg_data = QByteArray(svg_bytes.read())
        renderer = QSvgRenderer(svg_data)
        item = QGraphicsSvgItem()
        item.setSharedRenderer(renderer)
        return item

    def tex2svg(self, equation):
        fig = plt.figure(figsize=(1, 1))
        fig.text(0, 0, fr"{equation}", fontsize=16)
        svg_data = io.BytesIO()
        fig.savefig(svg_data, format="svg", bbox_inches="tight", pad_inches=0.1)
        plt.close(fig)
        svg_data.seek(0)
        return svg_data

    def _text_is_latex(self, text: str):
        return text.count("$") == 2 and len(text) != 2


        # comminicate value to parent process
        # wait untill return value from parent process

class IntBox(QWidget):
    clicked = pyqtSignal(int)
    def __init__(self, default=2, upper_bound=10, lower_bound=0):
        super().__init__()
        self.box_layout = QHBoxLayout()
        self.value = default
        self.upper_bound = upper_bound
        self.lower_bound = lower_bound
        self.initUi()
        self.setLayout(self.box_layout)
        self.box_layout.setSpacing(0)

    def initUi(self):
        self._create_widgets()
        self._add_widgets()
        self._configure_widgets()

    def _create_widgets(self):
        self.label = QLabel(str(self.value))
        self.increment_button = QPushButton("+")
        self.decrement_button = QPushButton("-")

    def _configure_widgets(self):
        self.increment_button.clicked.connect(self.increment)
        self.decrement_button.clicked.connect(self.decrement)

    def _add_widgets(self):
        self.box_layout.addWidget(self.label)
        self.box_layout.addSpacing(4)
        self.box_layout.addWidget(self.decrement_button)
        self.box_layout.addWidget(self.increment_button)

    def increment(self):
        self.clicked.emit(self.value)
        if self.value <= self.upper_bound:
            self.value += 1
            self.label.setText(str(self.value))

    def decrement(self):
        self.clicked.emit(self.value)
        if self.value >= self.lower_bound:
            self.value -= 1
            self.label.setText(str(self.value))

class SingleCheckBox(QWidget):
    """  """
    clicked = pyqtSignal(str)
    def __init__(self, *args, fallback: None | str = None):
        super().__init__()
        self.checkbox_layout = QVBoxLayout()
        self._checkboxes = []
        self.fallback = fallback

        self.checkbox_layout.addStretch()
        for box in args:
            self.add_checkbox(box)

        self.checkbox_layout.addStretch()
        self.setLayout(self.checkbox_layout)
        self.checkbox_layout.setSpacing(10)

    def add_checkbox(self, checkbox: QCheckBox):
        self._checkboxes.append(checkbox)
        checkbox.clicked.connect(self._handle_check)
        checkbox.clicked.connect(lambda _,t=checkbox.text(): self.clicked.emit(t))
        self.checkbox_layout.addWidget(checkbox)

    def _handle_check(self):
        one_checked = False
        for box in self._checkboxes:
            if box.isChecked() and box != self.sender():
                box.setChecked(False)
                one_checked = True
            elif box.isChecked():
                one_checked = True

        if not one_checked and self.fallback is not None:
            for box in self._checkboxes:
                if box.text() == self.fallback:
                    box.setChecked(True)


    def selected(self):
        for i in self._checkboxes:
            if i.isChecked():
                return i
        return None

class VToolBar(QWidget):
    """ Contains widgets related to customizing drawing tool.
    Implements interface for retreiving these user selection """
    def __init__(self):
        super().__init__()
        self.toolbar_layout = QVBoxLayout()
        self.initUi()
        self.setLayout(self.toolbar_layout)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
#        self.toolbar_layout.setSpacing()

    def initUi(self):
        self._create_widgets()
        self._add_widgets()
        self.setFixedWidth(150)

    def _create_widgets(self):
        selector_box = QCheckBox("Selector")
        selector_box.setChecked(True)
        self.tool_checkbox = SingleCheckBox(QCheckBox(Handlers.Freehand.name),
                                            QCheckBox(Handlers.Line.name),
                                            QCheckBox(Handlers.Textbox.name),
                                            selector_box,
                                            fallback = selector_box.text())
        self.pen_size_selector_label = QLabel("Pen Width")
        self.pen_size_selector = IntBox()
        self.toggle_menu_button = QPushButton("Toggle Menu")
#        self.width_widget =
    def _add_widgets(self):
        self.toolbar_layout.addWidget(self.tool_checkbox)
        self.toolbar_layout.addStretch()
        self.toolbar_layout.addWidget(self.pen_size_selector_label)
        self.toolbar_layout.addWidget(self.pen_size_selector)
        self.toolbar_layout.addWidget(self.toggle_menu_button)

    def connectClickedTool(self, func: Callable):
        self.tool_checkbox.clicked.connect(func)

    def connectClickedPenWidth(self, func: Callable[[int], None]):
        self.pen_size_selector.clicked.connect(func)

    def connectToggleMenuButton(self, func: Callable[[], None]):
        self.toggle_menu_button.clicked.connect(func)

class ModeView(QLabel):
    def __init__(self):
        super().__init__()

    def notify(self, msg):
        self.setText(msg)

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._filepath = None
        self.scene_default_width = 1052 * 0.75
        self.scene_default_height = 744 * 0.75
        self.initUi()

    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, filepath):
        self._filepath = filepath
        self.filename_widget.setText(self._filepath)

    @property
    def filename(self):
        if self._filepath is None:
            return UNSAVED_NAME
        return Path(self._filepath).name

    def initUi(self):
        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout(self.main_widget)
        self.setCentralWidget(self.main_widget)

        self.resize(1100, 600)
        self._create_widgets()
        self._create_tool_bar()
        self._configure_widgets()
        self._add_widgets()

    def _create_tool_bar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        save_action = QAction("Save", self)
        open_action = QAction("Open", self)
        self.filename_widget = QLabel(self.filename)
        self.mode_label = ModeView()
        self.filename_widget.setStyleSheet('font-size: 16pt;')
        spacer, spacer_2 = QWidget(), QWidget()
        expanding_spacer = QWidget()
        expanding_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setFixedWidth(200)
        spacer_2.setFixedWidth(50)

        toolbar.addAction(save_action)
        toolbar.addAction(open_action)
        toolbar.addWidget(spacer)
        toolbar.addWidget(self.filename_widget)
        toolbar.addWidget(expanding_spacer)
        toolbar.addWidget(self.mode_label)
        toolbar.addWidget(spacer_2)

        save_action.triggered.connect(self.save_as_svg)
        open_action.triggered.connect(self._load_from_selection)


    def _create_widgets(self):
        self.graphics_view = GraphicsView()
        self._scene = TexGraphicsScene()
        self.tool_bar = VToolBar()
        self.toggle_menu = ToggleMenuWidget()
        scroll_widget = QWidget()
        scroll_layout = QHBoxLayout(scroll_widget)
        scroll_layout.addWidget(self.graphics_view)
        self.scroll_area = ZoomableScrollArea(scroll_widget)
        self.scroll_area.setWidget(scroll_widget)

    def _configure_widgets(self):
        self.toggle_menu.hide()
        self.tool_bar.connectToggleMenuButton(self.toggleMenuWidget)
        self._scene.setBackgroundBrush(QBrush(Qt.GlobalColor.white))
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
#        self.graphics_view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.graphics_view.setInteractive(True)
        self.graphics_view.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.graphics_view.setScene(self._scene)
        self.graphics_view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.graphics_view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.graphics_view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.IgnoreAspectRatio)

        self._scene.setSceneRect(QRectF(0, 0, self.scene_default_width, self.scene_default_height)) # TODO
        self.scroll_area.setWidgetResizable(True)

    def _add_widgets(self):
#        self.main_layout.addWidget(self.graphics_view)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(self.tool_bar)
        self.main_layout.addWidget(self.toggle_menu)

    def setController(self, controller: DrawingController):
        """ Design needs to be re thought.... entire gui """
        controller.setSceneView(self.graphics_view)
        self.graphics_view.setController(controller)
        self.tool_bar.connectClickedTool(controller.setHandlerFromName)
        self.tool_bar.connectClickedPenWidth(controller.setPenWidth)

    def setShortcutManager(self, shortcut_manager: ShortcutManager):
        if self.scene:
            shortcut_manager.add_listener(self.mode_label)
            self._scene.setShortcutManager(shortcut_manager)

    @property
    def scene(self):
        return self.graphics_view.scene()

    def _load_from_selection(self):
        # TODO empty arg is dir to check... how do I decide this? allow for sys.argv?
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "SVG Files (*.svg)")
        if Path(file_path).is_file():
            self.load_svg(file_path)

    def scene_to_svg(self, file_path):
        """ Return 0 if not error else 1
        TODO: Re write this"""
        viewport = self.graphics_view.viewport()
        if file_path is None or not Path(file_path).is_file() or viewport is None:
            logger.error(f"Invalid file_path: {file_path}")
            return 1
        svg_gen = QSvgGenerator()
        svg_gen.setFileName(file_path)
        svg_gen.setSize(viewport.size())
        svg_gen.setViewBox(self.graphics_view.sceneRect())
        painter = QPainter(svg_gen)
        self._scene.render(painter)
        painter.end()
        return 0

    def closeEvent(self, event: QCloseEvent): #type: ignore
        """ TODO: Make this better """
        if self.filename != UNSAVED_NAME:
            self.save()
            return

        if isinstance(event, ShortcutCloseEvent):
            home_dir = Path().home()
            num, attempts = 0, 0
            while (home_dir / f"veditor_unamed_{num}").is_file() and attempts < 30:
                num += 1
            self.filepath = str(home_dir / f"veditor_unamed{num}")
            self.save()
            return

        reply = QMessageBox.question(self, "Confirm Close", "Do you want to save before closing?",
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Save:
            return_code = self.save_as_svg()
            if return_code == 0:
                event.accept()
            else:
                event.ignore()
        elif reply == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()

    def save_as_svg(self):
#        options = QFileDialog.options
        if self._filepath is None:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "SVG Files (*.svg)")
        else:
            file_path = self._filepath

        return_code = self.scene_to_svg(file_path)
        if return_code == 1:
            display_name = f"error while saving: {file_path}" if return_code == 1 else file_path.split("/")[-1]
            self.filename_widget.setText(display_name)
        else:
            self.filepath = file_path
        return return_code

    def save(self):
        """ Save svg """
        self.scene_to_svg(self._filepath)

    def open_with_svg(self, filepath: str):
        """ Loads svg and sets filename to svg name. Implements 'editing' functionality, the original svg will
        overidden when saved"""
        self.load_svg(filepath, scale=1)
        self.filepath = filepath

    def load_svg(self, file_path: str, scale=0.5):
        """ TODO """
        svg_item = QGraphicsSvgItem(file_path)
        svg_item.setFlag(QGraphicsSvgItem.GraphicsItemFlag.ItemClipsToShape, True) # Make background transparent
        cont = self.graphics_view.controller()
        if cont:
            handler = cont.handler
            signal = cont.handler_signal
        else:
            signal = None
            handler = None
        selectable_item = SelectableRectItem(svg_item, Handlers.Selector.value,signal)
        selectable_item.setScale(scale) # TODO determine scale based on width relative to window width, height width
        self._scene.addItem(selectable_item)
        # hack to 'refresh' signals.. without this loaded graphic won't be selectable untill selector button is pressed again
        if handler and signal:
            signal.emit(handler.__class__.__name__)

    def toggleMenuWidget(self):
        if self.toggle_menu.isVisible():
            self.toggle_menu.hide()
            self.resize(self.width() - self.toggle_menu.width(), self.height())
        else:
            self.resize(self.width() + self.toggle_menu.width(), self.height())
            self.toggle_menu.show()

    def modeView(self):
        return self.mode_label
