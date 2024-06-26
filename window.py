from collections.abc import Callable
from PyQt6.QtGui import QAction, QBrush, QGuiApplication, QMouseEvent, QPen, QPainter, QTransform
from PyQt6.QtCore import QPointF, QRect, Qt, QRectF, pyqtSignal, QEvent, QSize
from PyQt6.QtSvg import QSvgGenerator
from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget
from PyQt6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QGraphicsItem, QGraphicsPathItem, QLabel, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QToolBar, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                             QGraphicsScene, QGraphicsLineItem, QMainWindow, QGraphicsRectItem)
from .tools import DrawingController, DrawingHandler, FreeHandDrawingHandler, LineDrawingHandler, NullDrawingHandler, SelectableRectItem
from pathlib import Path
import logging
logger = logging.getLogger(__name__)
from collections import deque
from .keyboard_utils import KeyCodes

UNSAVED_NAME = "No Name **"

class GraphicsView(QGraphicsView):
    def __init__(self, controller: None | DrawingController = None):
        super().__init__()
        self._controller =  controller
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
#        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)

    def mousePressEvent(self, event):
        if self._controller:
            self._controller.mousePressEvent(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._controller:
            self._controller.mouseMoveEvent(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._controller:
            self._controller.mouseReleaseEvent(event)
        super().mouseReleaseEvent(event)

    def setController(self, controller):
        self._controller = controller

    def controller(self) -> DrawingController | None:
        return self._controller

    def wheelEvent(self, event):
        event.ignore()

    def resizeEvent(self, event):
#        self.center_scene()
        dpr = self.devicePixelRatioF()
        self.setTransform(QTransform().scale(dpr, dpr))
        super().resizeEvent(event)


class ZoomableScrollArea(QScrollArea):
    def __init__(self, container):
        super().__init__()
#        self.view = view
        self.container = container
        self.zoom_factor = 1.5
        self.current_zoom = 1.0
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.grabGesture(Qt.GestureType.PinchGesture)
#
    def gestureEvent(self, event):
        if gesture := event.gesture(Qt.GestureType.PinchGesture):
            self.pinchTriggered(gesture, gesture.centerPoint())
            return True
        return super().event(event)

    def pinchTriggered(self, gesture: Qt.GestureState, pinch_center: QPointF):
        if gesture.state() == Qt.GestureState.GestureUpdated:
#            self.container.resize(int(self.container.width() * gesture.scaleFactor()), int(self.container.height() * gesture.scaleFactor())) # TODO Make this work
            pass

    def event(self, event: QEvent):
        if event.type() == QEvent.Type.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

class GraphicsScene(QGraphicsScene):
    def __init__(self, max = 5):
        super().__init__()
        self.cache = deque()
        self.cache_max = max

    def keyPressEvent(self, event):
        print(f"Event modifiers: {event.modifiers()}")
        print(f"Key code: {event.key()}")
        if event.key() == KeyCodes.Key_Delete.value:
            selected_items = self.selectedItems()
            for item in selected_items:
                self.removeItem(item)
                self.add_to_cache(item)

        elif (event.key() == KeyCodes.Key_U.value and event.modifiers() == Qt.KeyboardModifier(Qt.KeyboardModifier.ShiftModifier)) and len(self.cache) > 0:
            item = self.cache.pop()
            self.addItem(item)
        else:
            super().keyPressEvent(event)

    def add_to_cache(self, item):
        if len(self.cache) > self.cache_max:
            self.cache.popleft()
        self.cache.append(item)

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
        self.setFixedWidth(100)

    def _create_widgets(self):
        selector_box = QCheckBox("Selector")
        selector_box.setChecked(True)
        self.tool_checkbox = SingleCheckBox(QCheckBox("Freehand"), QCheckBox("Line"), selector_box, fallback = selector_box.text())
        self.pen_size_selector_label = QLabel("Pen Width")
        self.pen_size_selector = IntBox()
#        self.width_widget =
    def _add_widgets(self):
        self.toolbar_layout.addWidget(self.tool_checkbox)
        self.toolbar_layout.addStretch()
        self.toolbar_layout.addWidget(self.pen_size_selector_label)
        self.toolbar_layout.addWidget(self.pen_size_selector)

    def connectClickedTool(self, func: Callable):
        self.tool_checkbox.clicked.connect(func)

    def connectClickedPenWidth(self, func: Callable[[int], None]):
        self.pen_size_selector.clicked.connect(func)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._filepath = None
        self.scene_default_width = 1052 * 0.75
        self.scene_default_height = 744 * 0.75
#        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        self.initUi()

    @property
    def filename(self):
        if self._filepath is None:
            return UNSAVED_NAME
        return Path(self._filepath).name

    def initUi(self):
        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout(self.main_widget)
        self.setCentralWidget(self.main_widget)

        self.resize(1000, 600)
        self._create_widgets()
        self._create_tool_bar()
        self._configure_widgets()
        self._add_widgets()

    def setFileName(self, filepath: str):
        self._filepath = filepath
        self.filename_widget.setText(self._filepath)

    def _create_tool_bar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        save_action = QAction("Save", self)
        open_action = QAction("Open", self)
        self.filename_widget = QLabel(self.filename)
        self.filename_widget.setStyleSheet('font-size: 16pt;')
        spacer = QWidget()
        spacer.setFixedWidth(200)

        toolbar.addAction(save_action)
        toolbar.addAction(open_action)
        toolbar.addWidget(spacer)
        toolbar.addWidget(self.filename_widget)

        save_action.triggered.connect(self.save_as_svg)
        open_action.triggered.connect(self._load_from_selection)


    def _create_widgets(self):
        self.graphics_view = GraphicsView()
#        self._scene = QGraphicsScene()
        self._scene = GraphicsScene()
        self.tool_bar = VToolBar()

        scroll_widget = QWidget()
        scroll_layout = QHBoxLayout(scroll_widget)
        scroll_layout.addWidget(self.graphics_view)
        self.scroll_area = ZoomableScrollArea(scroll_widget)
        self.scroll_area.setWidget(scroll_widget)

    def _configure_widgets(self):
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

    def setController(self, controller: DrawingController):
        """ Design needs to be re thought.... entire gui """
        controller.setSceneView(self.graphics_view)
        self.graphics_view.setController(controller)
        self.tool_bar.connectClickedTool(controller.setHandlerFromName)
        self.tool_bar.connectClickedPenWidth(controller.setPenWidth)

#    def setDrawingHandler(self, drawing_handler: DrawingHandler) -> bool:
#        controller = self.graphics_view.controller()
#        if controller:
#            controller.setHandler(drawing_handler)
#            return True
#        return False

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
        if file_path is None or not Path(file_path).is_file():
            logger.error(f"Invalid file_path: {file_path}")
            return 1
        svg_gen = QSvgGenerator()
        svg_gen.setFileName(file_path)
        svg_gen.setSize(self.graphics_view.viewport().size())
        svg_gen.setViewBox(self.graphics_view.sceneRect())
        painter = QPainter(svg_gen)
        self._scene.render(painter)
        painter.end()
        return 0

    def closeEvent(self, event):
        """ TODO: Make this better """
        if self.filename != UNSAVED_NAME:
            self.save()
            event.accept()
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
        display_name = f"error while saving: {file_path}" if return_code == 1 else str(Path(file_path).name)
        self.setFileName(display_name)
        return return_code

    def save(self):
        """ Save svg """
        self.scene_to_svg(self._filepath)

    def load_svg(self, file_path):
#        p = Path(__file__).parent / filename
        svg_item = QGraphicsSvgItem(file_path)
        svg_item.setFlag(QGraphicsSvgItem.GraphicsItemFlag.ItemClipsToShape, True) # Make background transparent
        cont = self.graphics_view.controller()
        if cont:
            handler = cont.handler
            signal = cont.handler_signal
        else:
            signal = None
            handler = None
        selectable_item = SelectableRectItem(svg_item, signal)
        selectable_item.setScale(0.5) # TODO determine scale based on width relative to window width, height width
        self._scene.addItem(selectable_item)
        # hack to 'refresh' signals.. without this loaded graphic won't be selectable untill selector button is pressed again
        if handler and signal:
            signal.emit(handler.__class__.__name__)
