from abc import ABC, abstractmethod
import sys
import math
from PyQt6.QtGui import QAction, QBrush, QColor, QMouseEvent, QPen, QPainterPath, QPainter
from PyQt6.QtCore import QLineF, QObject, QPoint, QPointF, Qt, pyqtBoundSignal, pyqtSignal, QRect, QRectF
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGraphicsPathItem, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                           QGraphicsScene, QGraphicsLineItem, QMainWindow, QGraphicsItem)
from functools import reduce
from .transformations import RotationHandler

class SelectableRectItem(QGraphicsItem):
    def __init__(self, item : QGraphicsItem, select_signal: pyqtBoundSignal | None = None):
        super().__init__()
        self.pen = QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine)
        self.item = item
        self.item.setParentItem(self)
        self.setAcceptHoverEvents(True)
        self.active = False
        self.transformation_handlers: list = self._register_transformation_handlers()
        if select_signal: # allow for setting after class init and
            select_signal.connect(self._toggle_active)

    def _register_transformation_handlers(self):
        rotation_handler = RotationHandler(self.rotatingRectIcon(), self)
        return [rotation_handler]

    def add_handler(self, handler: TransformationHandler):
        self.transformation_handlers.append(handler)

    def _toggle_active(self, name):
        if name == f"{NullDrawingHandler.__name__}":
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.active = True
        else:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.active = False
    def mouseMoveEvent(self, event):
        for handler in self.transformation_handlers:
            handler.handle_mouse_move(event)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        for handler in self.transformation_handlers:
            handler.handle_mouse_press(event)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        for handler in self.transformation_handlers:
            handler.handle_mouse_release(event)
        super().__init__()

    def hoverEnterEvent(self, event):
        self.setSelected(True)

    def hoverLeaveEvent(self, event):
        self.setSelected(False)

    def paint(self, painter, option, widget):
        if self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable == 0:
            return
        # TODO is the below line necessary, since this is a parent shouldnt the event propogate down by default?
#        self.item.paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(self.pen)
            painter.drawRect(self.boundingRect())
            for handler in self.transformation_handlers:
                painter.drawRect(handler.rect) # Make this dynamic... handler should implement paint?

    def boundingRect(self):
        rect = self.item.boundingRect()
        handler_rects = [handler.rect for handler in self.transformation_handlers]
        total_rect = reduce(lambda r1, r2: r1.united(r2),  handler_rects, rect)
        return total_rect

    def rotatingRectIcon(self):
        handle_size = 8 # TODO: make this more dynamic
        item_boundingRect = self.item.boundingRect()
        center_right = QPointF(item_boundingRect.right(), item_boundingRect.center().y())
        return QRectF(center_right.x() - handle_size / 2, center_right.y() - handle_size / 2, handle_size, handle_size )

