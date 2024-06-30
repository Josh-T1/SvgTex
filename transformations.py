from abc import ABC, abstractmethod
from collections.abc import Callable
import sys
import math
from PyQt6.QtGui import QAction, QBrush, QColor, QMouseEvent, QMoveEvent, QPen, QPainterPath, QPainter, QTransform
from PyQt6.QtCore import QEvent, QLineF, QObject, QPoint, QPointF, Qt, pyqtBoundSignal, pyqtSignal, QRect, QRectF
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGraphicsPathItem, QGraphicsRectItem, QGraphicsSceneMouseEvent, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                           QGraphicsScene, QGraphicsLineItem, QMainWindow, QGraphicsItem)
from functools import reduce
from math import comb, cos, sin
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
    """ RotationHandler implements rotation behaviour of QGraphicsItem """
    def __init__(self, set_rect_callback: Callable[[], QRectF], item: QGraphicsItem):
        """
        -- Params --
        set_rect_callback: Callable that returns QRectF object representing the are in which RotationHandler will handle mouseEvents
        item: the QGraphicsItem for which RotationHandler is implementing rotation behaviour
        """
        self.set_rect_callback = set_rect_callback
        self.item = item
        self._rect: QRectF = self.set_rect_callback()
        self.is_rotating = False
        self.is_resizing = False
        self.rotation_start_angle = 0

    def handle_mouse_press(self, event):
        if self.rect.contains(self.item.mapFromScene(event.scenePos())):
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.is_rotating = True
            self.rotation_start_angle = self.angle(event.scenePos(), self.item.mapToScene(self.item.boundingRect().center()))

    @staticmethod
    def angle(p1: QPointF, p2: QPointF):
        """ Returns the angle between the line p1 -> p2 and the x-axis """
        return QLineF(p1, p2).angle()

    @property
    def rect(self):
        return self.set_rect_callback()

    def handle_mouse_move(self, event):
        if self.is_rotating:
            current_angle = self.angle(event.scenePos(), self.item.mapToScene(self.item.transformOriginPoint()))
            angle_diff = self.rotation_start_angle - current_angle

#            rotation = (self.item.rotation() + angle_diff)
            transform = self.build_transform(angle_diff)
            self.item.setTransform(transform, combine=True)
            self.rotation_start_angle = current_angle

    def handle_mouse_release(self, event):
        if self.is_rotating:
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.is_rotating = False

    def build_transform(self, degrees):
        center = self.item.mapToScene(self.item.transformOriginPoint())
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(degrees)
        transform.translate(-center.x(), -center.y())
        return transform

class ScaleHandler(TransformationHandler):
    """
    ScaleHandler handles all scaling of QGraphicsItems when the users cursor is inside its rectangle. This rectangle is passed in by means of a callback and
    detects when mouse events are in the target area. This class needs to be delegated mouseEvents as they happen. Scaling of items occurs with the opposing diagonal
    corner fixed (it is assumed the handler rect resides on a corner of item: QGraphicsItem).

    -- Limitations --
    1. We can not invert item. If you drag the top left corner towards the top right corner, you can not pass the top right corner. There is also glitching when you get close or the width of the image
    becomes tiny.

    2. Class is messy
    We need a bounding rect for determing the translation required to implement fixed point scaling. Would
    be nice to use self.item.boundingRect() but this does not work when the item is a SelectableRect. It feels messy passing in a bunch of callbacks..."""
    def __init__(self, set_rect_callback: Callable[[], QRectF],item: QGraphicsItem, bounding_rect_callback: Callable[[], QRectF], corner: str = "top_right"):
        """
        -- Params --
        set_rect_callback: Callable that returns the QRectF object representing the are in which the handler should implement its functionality
        item: QGraphicsItem wich is the target of the scaling
        bounding_rect_callback: Callable wich returns the QRectF object representing the bounding rectangle of self.item
        corner: of the form '(top/down)_(right/left)'. The corner of items's bounding rectangle on which handler rect resides.
        """
        self.set_rect_callback = set_rect_callback
        self.bounding_rect_callback = bounding_rect_callback
        self.item = item
        self.stretching = False
        self.corner = corner

    def edge_coordinate(self):
        """ Scene coordinates for the center of the handler rectangle  """
        return self.item.mapToScene(self.rect.center())

    @property
    def rect(self):
        """ Returns the handler rect (QRectF object) """
        return self.set_rect_callback()

    def handle_mouse_press(self, event: QGraphicsSceneMouseEvent):
        if self.rect.contains(self.item.mapFromScene(event.scenePos())):
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.stretching = True

    def handle_mouse_move(self, event: QGraphicsSceneMouseEvent):
        if self.stretching:
            new_coordinate = event.scenePos()
            edge_coordinate = self.edge_coordinate()

            if new_coordinate.x() == 0 or edge_coordinate == 0 or edge_coordinate.y() == 0 or new_coordinate.y() == 0:
                return

            x_scale_factor = new_coordinate.x() / edge_coordinate.x()
            y_scale_factor = edge_coordinate.y() / new_coordinate.y()

            # Moving the cursor left has the inverse effect when draging a left corner compared with a right corner
            if "left" in self.corner:
                x_scale_factor = 1 / x_scale_factor

            if "bottom" in self.corner:
                y_scale_factor = 1 / y_scale_factor

            # Prevent large scaling factors
            if x_scale_factor > 0:
                x_scale_factor_restricted = min(x_scale_factor, 1.5)
            else:
                x_scale_factor_restricted = max(x_scale_factor, -1.5)

            if y_scale_factor > 0:
                y_scale_factor_restricted = min(y_scale_factor, 1.5)
            else:
                y_scale_factor_restricted = max(y_scale_factor, -1.5)

            transform = self.build_transform(x_scale_factor_restricted, y_scale_factor_restricted)
            self.item.setTransform(transform, combine=True)

    def handle_mouse_release(self, event: QGraphicsSceneMouseEvent):
        if self.stretching:
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.stretching = False

    def build_transform(self, x_scale_factor: float, y_scale_factor: float):
        """ Create QTransform required to scale item fixed to the opposing diagonal corner """
        bounding_rect = self.bounding_rect_callback()
        if self.corner == "top_right":
            translate_center = bounding_rect.bottomLeft()
        elif self.corner == "top_left":
            translate_center = bounding_rect.bottomRight()
        elif self.corner == "bottom_right":
            translate_center = bounding_rect.topLeft()
        else:
            translate_center = bounding_rect.topRight()

        transform = QTransform()
        transform.translate(translate_center.x() , translate_center.y())
        transform.scale(x_scale_factor, y_scale_factor)
        transform.translate(-translate_center.x() , -translate_center.y())
        return transform
