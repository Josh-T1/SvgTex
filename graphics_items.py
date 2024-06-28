from abc import ABC, abstractmethod
import sys
import math
from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QMouseEvent, QPen, QPainterPath, QPainter, QTransform
from PyQt6.QtCore import QLineF, QObject, QPoint, QPointF, Qt, pyqtBoundSignal, pyqtSignal, QRect, QRectF
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGraphicsPathItem, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                           QGraphicsScene, QGraphicsLineItem, QMainWindow, QGraphicsItem)
from functools import reduce
from .transformations import RotationHandler, TransformationHandler, ScaleHandler

class SelectableRectItem(QGraphicsItem):
    def __init__(self, item : QGraphicsItem, target_sig_name: str, select_signal: pyqtBoundSignal | None = None):
        super().__init__()
        self.pen = QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine)
        self.item = item
        self._item_boundingRect = self.item.boundingRect()
        self.target_sig_name = target_sig_name
        self.item.setParentItem(self)
        self.setAcceptHoverEvents(True)
        self.transformation_handlers: list[TransformationHandler] = self._register_transformation_handlers()
        self.setTransformOriginPoint(self.itemBoundingRect().center())

        if select_signal: # allow for setting after class init and
            select_signal.connect(self._toggle_active)

    def _register_transformation_handlers(self) -> list[TransformationHandler]:
        rotation_handler = RotationHandler(self.rotatingRectIcon, self)
        stretch_handler = ScaleHandler(self.topRightStretchIcon, self)
        return [rotation_handler, stretch_handler]

    def add_handler(self, handler: TransformationHandler) -> None:
        self.transformation_handlers.append(handler)

    def _toggle_active(self, name: str) -> None:
        if name == self.target_sig_name:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
#            self.active = True
        else:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
#            self.active = False

    def setTransform(self, matrix, combine=False) -> None:
        self.item.setTransform(matrix, combine=combine)
        # update rects
        self._item_boundingRect = self.updateRect(self._item_boundingRect, matrix)
        for handler in self.transformation_handlers:
            handler.rect = handler.set_rect_callback()

    def updateRect(self, rect, transform: QTransform):
        corners = [rect.topLeft(),
                   rect.topRight(),
                   rect.bottomRight(),
                   rect.bottomLeft()
                   ]
        transformed_corners = [transform.map(corner) for corner in corners]
        min_x = min(corner.x() for corner in transformed_corners)
        max_x = max(corner.x() for corner in transformed_corners)
        min_y = min(corner.y() for corner in transformed_corners)
        max_y = max(corner.y() for corner in transformed_corners)
        return QRectF(QPointF(min_x, min_y), QPointF(max_x, max_y))


    def transformOriginPoint(self):
        return self.itemBoundingRect().center()

    def mouseMoveEvent(self, event) -> None:
        for handler in self.transformation_handlers:
            handler.handle_mouse_move(event)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        for handler in self.transformation_handlers:
            handler.handle_mouse_press(event)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        for handler in self.transformation_handlers:
            handler.handle_mouse_release(event)
        super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event) -> None:
        self.setSelected(True)

    def hoverLeaveEvent(self, event) -> None:
        self.setSelected(False)

    def paint(self, painter, option, widget) -> None:
        if self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable == 0:
            return
        # TODO is the below line necessary, since this is a parent shouldnt the event propogate down by default?
#        self.item.paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(self.pen)
            painter.drawRect(self.itemBoundingRect())
            for handler in self.transformation_handlers:
                painter.drawRect(handler.rect) # Make this dynamic... handler should implement paint?

    def itemBoundingRect(self):
        """ Convenience method for getting boundingRect of item in scene coordinates """
        return self._item_boundingRect

    def boundingRect(self) -> QRectF:
        rect = self.itemBoundingRect()
        handler_rects = [handler.rect for handler in self.transformation_handlers]
        total_rect = reduce(lambda r1, r2: r1.united(r2),  handler_rects, rect)
        return total_rect

    def rotatingRectIcon(self) -> QRectF:
        handle_size = 8 # TODO: make this more dynamic
        item_boundingRect = self.itemBoundingRect()
        center_right = QPointF(item_boundingRect.right(), item_boundingRect.center().y())
        return QRectF(center_right.x() - handle_size / 2, center_right.y() - handle_size / 2, handle_size, handle_size )

    def topRightStretchIcon(self) -> QRectF:
        handle_size = 8
        top_right = self.itemBoundingRect().topRight()
        return QRectF(top_right.x() - handle_size / 2, top_right.y() - handle_size / 2, handle_size, handle_size)


class StretchableLine(QGraphicsLineItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

