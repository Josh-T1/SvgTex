from PyQt6.QtGui import QAction, QBrush, QMouseEvent, QPen
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGraphicsPathItem, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                             QGraphicsScene, QGraphicsLineItem, QMainWindow)
from .tools import DrawingHandler, NullDrawingHandler


class GraphicsView(QGraphicsView):
    def __init__(self, drawing_handler: DrawingHandler = NullDrawingHandler()):
        super().__init__()
        self.handler = drawing_handler
        self.pen = QPen(Qt.GlobalColor.black)
        self.pen.setWidth(2)
        self.initUi()
        self.setScene(self._scene)
        self.start_point = None
        self.current_line = None

    def initUi(self):
        self._create_widgets()
        self._configure_widgets()

    def _create_widgets(self):
        self._scene = QGraphicsScene()


    def _configure_widgets(self):
        self._scene.setBackgroundBrush(QBrush(Qt.GlobalColor.white))
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setInteractive(False)

        self._scene.setSceneRect(QRectF(-200, -200, 400, 400)) # TODO

    def wheelEvent(self, event):
        if event:
            event.ignore()

    def mousePressEvent(self, event: QMouseEvent | None):
        print("Press")
        if event and event.button() == Qt.MouseButton.LeftButton:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.start_point = self.mapToScene(event.position().toPoint())
            self.current_line = QGraphicsLineItem()
            self.current_line.setPen(self.pen)
            self._scene.addItem(self.current_line)
#        if event is not None:
#            self.handler.mousePress(self, event, self.pen)
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event: QMouseEvent | None):
        print("Move")
        if event and not self.start_point is None and not self.current_line is None:
            end_point = self.mapToScene(event.position().toPoint())
            self.current_line.setLine(self.start_point.x(), self.start_point.y(), end_point.x(), end_point.y())
#        if event is not None:
#            self.handler.mouseMove(self, event, self.pen)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent | None):
        print("Release")
        if event and event.button() == Qt.MouseButton.LeftButton and self.current_line:

            if self.start_point is None:
                raise Exception("Can this even happend?")

            end_point = self.mapToScene(event.position().toPoint())
            self.current_line.setLine(self.start_point.x(), self.start_point.y(), end_point.x(), end_point.y())
            self.start_point = None
            self.current_line = None
#        if event is not None:
#            self.handler.mouseRelease(self, event, self.pen)
        super().mouseReleaseEvent(event)

    def setDrawingHandler(self, drawing_handler: DrawingHandler):
        self.handler = drawing_handler
    def setPenWdith(self, width: int):
        self.pen.setWidth(width)
    def setPenColor(self, color: Qt.GlobalColor):
        self.pen.setColor(color)
    def setPenBrush(self, brush: QBrush):
        self.pen.setBrush(brush)

class SingleCheckBox(QWidget):
    def __init__(self, *args):
        super().__init__()
        self.checkbox_layout = QVBoxLayout()
        self._checkboxes = []
        for box in args:
            self.add_checkbox(box)
        self.setLayout(self.checkbox_layout)

    def add_checkbox(self, checkbox: QCheckBox):
        self._checkboxes.append(checkbox)
        checkbox.setChecked(False)
        checkbox.clicked.connect(self._handle_check)
        self.checkbox_layout.addWidget(checkbox)

    def _handle_check(self):
        for box in self._checkboxes:
            if box.isChecked() and box != self.sender():
                box.setChecked(False)

class VToolBar(QWidget):
    def __init__(self):
        super().__init__()
        self.toolbar_layout = QVBoxLayout()
        self.initUi()

    def initUi(self):
        self._create_widgets()
        self._add_widgets()
        self.setFixedWidth(100)

    def _create_widgets(self):
        self.tool_checkbox = QCheckBox()

    def _add_widgets(self):
        pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1000, 600)
        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout(self.main_widget)
        self.setCentralWidget(self.main_widget)
        self.initUi()

    def initUi(self):
        self._create_widgets()
        self.main_layout.addWidget(self.graphics_view)


    def _create_widgets(self):
        self.graphics_view = GraphicsView()
