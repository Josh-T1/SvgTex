from abc import ABC, abstractmethod
from collections.abc import Callable
import sys
import math
from PyQt6.QtGui import QAction, QBrush, QColor, QMouseEvent, QPen, QPainterPath, QPainter, QTransform
from PyQt6.QtCore import QLineF, QObject, QPoint, QPointF, Qt, pyqtBoundSignal, pyqtSignal, QRect, QRectF
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGraphicsPathItem, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                           QGraphicsScene, QGraphicsLineItem, QMainWindow, QGraphicsItem)
from functools import reduce
from math import cos, sin
import numpy as np

""" I think we assume handler rects can not overlap """
class TransformationHandler(ABC):
    @abstractmethod
    def __init__(self, set_rect_callback, item):
        self.set_rect_callback = set_rect_callback
        self.rect = self.set_rect_callback()
        self.item = item
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
    def __init__(self, set_rect_callback: Callable[[], QRectF], item: QGraphicsItem):
        self.set_rect_callback = set_rect_callback
        self.rect = self.set_rect_callback()
        self.item = item
        self.is_rotating = False
        self.is_resizing = False
        self.rotation_start_angle = 0

    def handle_mouse_press(self, event):
        if self.rect.contains(self.item.mapFromScene(event.scenePos())):
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.is_rotating = True
            self.rotation_start_angle = self.angle(event.scenePos(), self.item.mapToScene(self.item.boundingRect().center()))

    @staticmethod
    def angle(p1, p2):
        return QLineF(p1, p2).angle()

    def handle_mouse_move(self, event):
        if self.is_rotating:
            current_angle = self.angle(event.scenePos(), self.item.mapToScene(self.item.transformOriginPoint()))
            angle_diff = self.rotation_start_angle - current_angle
            rotation = (self.item.rotation() + angle_diff)
            self.item.setRotation(rotation)
            self.rotation_start_angle = current_angle

    def handle_mouse_release(self, event):
        if self.is_rotating:
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.is_rotating = False

class ScaleHandler(TransformationHandler):
    def __init__(self, set_rect_callback: Callable[[], QRectF], item: QGraphicsItem):
        self.item = item
        self.set_rect_callback = set_rect_callback
        self.rect = self.set_rect_callback()
        self.stretching = False
#        self.coordinate = self.item.mapToScene(self.rect.topRight())

    def edge_coordinate(self):
        return self.item.mapToScene(self.rect.center())

    def handle_mouse_press(self, event):
        if self.rect.contains(self.item.mapFromScene(event.scenePos())):
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.stretching = True

    def handle_mouse_move(self, event):
        if self.stretching:
            new_coordinate = event.scenePos()
            x_scale_factor = new_coordinate.x() / self.edge_coordinate().x()
            y_scale_factor = self.edge_coordinate().y() / new_coordinate.y()
            print(x_scale_factor, "x")
            transform = self.build_transform(x_scale_factor, y_scale_factor)
            self.item.setTransform(transform)
#            self.item.setPos(self.item.pos() - translation_vector)

    def handle_mouse_release(self, event):
        if self.stretching:
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.stretching = False

    def build_transform(self, x_scale_factor, y_scale_factor):
        transform = QTransform()
        transform.translate(self.item.boundingRect().center().x(), self.item.boundingRect().center().y())
        transform.scale(x_scale_factor, y_scale_factor)
        transform.translate(-self.item.boundingRect().center().x(), -self.item.boundingRect().center().y())
        return transform


