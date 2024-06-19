from abc import ABC, abstractmethod
import sys
from PyQt6.QtGui import QAction, QBrush, QMouseEvent, QPen
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGraphicsPathItem, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                           QGraphicsScene, QGraphicsLineItem, QMainWindow)



class DrawingHandler(ABC):
    @abstractmethod
    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    @abstractmethod
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    @abstractmethod
    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, QPen):
        pass

class Pen(ABC):
    pass

class NullDrawingHandler(DrawingHandler):
    def __init__(self):
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
    def __init__(self):
        self.pen = None
        self.start_point = None
        self.current_line = None

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton and self.current_line:

            if self.start_point is None:
                raise Exception("Can this even happend?")

            end_point = view.mapToScene(event.position().toPoint())
            self.current_line.setLine(self.start_point.x(), self.start_point.y(), end_point.x(), end_point.y())
            self.start_point = None
            self.current_line = None

    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if not self.start_point is None and not self.current_line is None:
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
QGraphicsPathItem
class FreeHandDrawingHandler(DrawingHandler):
    def __init__(self):
        self.toggled = False
        self.pen = None
        self.start_point = None
        self.current_line = None

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        self.toggled = not self.toggled

    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if self.toggled:
            pass
