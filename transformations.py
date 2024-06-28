from abc import ABC, abstractmethod
import sys
import math
from PyQt6.QtGui import QAction, QBrush, QColor, QMouseEvent, QPen, QPainterPath, QPainter
from PyQt6.QtCore import QLineF, QObject, QPoint, QPointF, Qt, pyqtBoundSignal, pyqtSignal, QRect, QRectF
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGraphicsPathItem, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                           QGraphicsScene, QGraphicsLineItem, QMainWindow, QGraphicsItem)
from functools import reduce

class TransformationHandler(ABC):
    @abstractmethod
    def handle_mouse_move(self, event):
        pass
    @abstractmethod
    def handle_mouse_press(self, event):
        pass
    @abstractmethod
    def handle_mouse_release(self, event):
        pass

class RotationHandler(TransformationHandler):
    def __init__(self, rect: QRectF, item):
        self.rect = rect
        self.item = item
        self.is_rotating = False
        self.is_resizing = False
        self.rotation_start_angle = 0

    def handle_mouse_press(self, event):
        return
        if self.rect.contains(event.position()):
            self.is_rotating = True
            self.rotation_start_angle = self.angle(self.item.mapToScene(event.Position()), self.item.mapToScene(self.item.boundingRect().center()))

    def angle(self, p1, p2):
        return QLineF(p1, p2).angle()

    def handle_mouse_move(self, event):
        return
        if self.is_rotating:
            current_angle = self.angle(self.item.mapToScene(event.position()), self.item.mapToScene(self.item.boundingRect().center()))
            angle_diff = current_angle - self.rotation_start_angle
            self.item.setRotation(self.item.rotation() + angle_diff)
            self.rotation_start_angle = current_angle

    def handle_mouse_release(self, event):
        self.is_rotating = False

    def registerItem(self, item):
        self.item = item

