from abc import ABC, abstractmethod
from PyQt6.QtGui import QAction, QBrush, QColor, QMouseEvent, QPen, QPainterPath, QPainter
from PyQt6.QtCore import QLineF, QObject, QPoint, QPointF, Qt, pyqtBoundSignal, pyqtSignal, QRect, QRectF
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGraphicsPathItem, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                           QGraphicsScene, QGraphicsLineItem, QMainWindow, QGraphicsItem)


class DrawingHandler(ABC):
    @abstractmethod
    def __init__(self, handler_signal: pyqtBoundSignal) -> None:
        self.handler_signal = handler_signal
    """ Implements drawing behaviour from user inputs. ie how the 'tool' behaves (freehand, curve, ...)  """
    @abstractmethod
    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    @abstractmethod
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    @abstractmethod
    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    def inBounds(self, scene, event) -> bool:
        """ Not currently used. Using inBounds with mousePressEvent creates all sorts of issues, simply suppressing the addition of
        new points to the graphics item will result in a line connecting the first point prior to leaving th escene with the first point after entering scene """
        return scene.sceneRect().contains(event.position())

class NullDrawingHandler(DrawingHandler):
    """ No drawing behaviour """
    def __init__(self, handler_signal: pyqtBoundSignal):
        self.pen = None
        self.start_point = None
        self.current_line = None

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass

class LineDrawingHandler(DrawingHandler):
    """ Tool for drawing straight lines """
    def __init__(self, handler_signal: pyqtBoundSignal):
        self.handler_signal = handler_signal
        self.start_point = None
        self.current_line = None

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton and self.current_line:

            if self.start_point is None:
                raise Exception("Can this even happend?")

            end_point = view.mapToScene(event.position().toPoint())
            scene = view.scene()
            scene.removeItem(self.current_line)
            self.current_line.setLine(self.start_point.x(), self.start_point.y(), end_point.x(), end_point.y())
            selectable_line = SelectableRectItem(self.current_line, self.handler_signal)
            scene.addItem(selectable_line)

            self.start_point = None
            self.current_line = None

    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if (self.start_point is not None and self.current_line is not None):
            end_point = view.mapToScene(event.position().toPoint())
            self.current_line.setLine(self.start_point.x(), self.start_point.y(), end_point.x(), end_point.y())

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = view.mapToScene(event.position().toPoint())
            self.current_line = QGraphicsLineItem()
            self.current_line.setPen(pen)
            scene = view.scene()
            if scene:
                scene.addItem(self.current_line)


class FreeHandDrawingHandler(DrawingHandler):
    """ Tool for drawing cursor path, 'freehand' tool """
    def __init__(self, handler_signal: pyqtBoundSignal):
        self.handler_signal = handler_signal
        self.drawing_started = False
        self.current_line = None
        self.current_path_item = None

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        scene = view.scene()
        scene.removeItem(self.current_path_item)

        selectable_path_item = SelectableRectItem(self.current_path_item, self.handler_signal)
        scene.addItem(selectable_path_item)
        self.drawing_started = False

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing_started = True
            start_point = view.mapToScene(event.position().toPoint())
            self.current_path = QPainterPath(start_point)
            self.current_path_item = QGraphicsPathItem(self.current_path)
            self.current_path_item.setPen(pen)
            scene = view.scene()
            scene.addItem(self.current_path_item)


    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if not self.drawing_started or not self.inBounds(view.scene(), event):
            return

        end = view.mapToScene(event.position().toPoint())

        if self.current_path.currentPosition() != end:
            self.current_path.lineTo(end)
            self.current_path_item.setPath(self.current_path)

class DrawingController(QObject):
    handler_signal = pyqtSignal(str)
    """
    1. Connects the user inputs in the scene with drawing handler.
    1. Provides drawing handler with the necessary methods to update scene
    1. Holds reference to 'tool' object which is used to customize drawing handler behaviour """
    handler_signal = pyqtSignal(str)
    def __init__(self, scene_view=None, handler=None, tool=None):
        super().__init__()
        self.scene_view = scene_view
        self.handler = handler
        self.tool = QPen()
        self.name_to_classname_mapping = {"Line": LineDrawingHandler, "Freehand": FreeHandDrawingHandler, "Selector": NullDrawingHandler}

    def mousePressEvent(self, event):
        if self.handler and self.scene_view and self.tool:
            self.handler.mousePress(self.scene_view, event, self.tool)

    def mouseMoveEvent(self, event):
        if self.handler and self.scene_view and self.tool:
            self.handler.mouseMove(self.scene_view, event, self.tool)

    def mouseReleaseEvent(self, event):
        if self.handler is not None and self.scene_view is not None and self.tool:
            self.handler.mouseRelease(self.scene_view, event, self.tool)

    def setSceneView(self, scene_view):
        self.scene_view = scene_view

    def setHandler(self, handler: DrawingHandler):
        self.handler = handler
        self.handler_signal.emit(self.handler.__class__.__name__)

    def setHandlerFromName(self, name):
        class_obj = self.name_to_classname_mapping.get(name, NullDrawingHandler)
        if not class_obj:
            return # TODO implement logging
        handler_inst = class_obj(self.handler_signal)
        self.setHandler(handler_inst)

    def setPenWidth(self, size: int):
        self.tool.setWidth(size)

