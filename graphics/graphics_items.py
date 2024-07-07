from abc import ABC, abstractmethod
import sys
import math
from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QMouseEvent, QPen, QPainterPath, QPainter, QTransform
from PyQt6.QtCore import QLineF, QObject, QPoint, QPointF, Qt, pyqtBoundSignal, pyqtSignal, QRect, QRectF
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGraphicsPathItem, QGraphicsTextItem, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                           QGraphicsScene, QGraphicsLineItem, QMainWindow, QGraphicsItem, QGraphicsRectItem)
from functools import reduce
from ..drawing.transformations import RotationHandler, TransformationHandler, ScaleHandler


class SelectableRectItem(QGraphicsItem):
    def __init__(self, item : QGraphicsItem, target_sig_name: str, select_signal: pyqtBoundSignal | None = None):
        super().__init__()
        self._pen = QPen(Qt.GlobalColor.darkBlue, 2, Qt.PenStyle.DashLine)
        self.item = item
        self.target_sig_name = target_sig_name
        self.item.setParentItem(self)
        self.setAcceptHoverEvents(True)
        self.transformation_handlers: list[TransformationHandler] = self._register_transformation_handlers()
        self.setTransformOriginPoint(self.item.boundingRect().center())

        if select_signal: # allow for setting after class init and
            select_signal.connect(self._toggle_active)

    def _register_transformation_handlers(self) -> list[TransformationHandler]:
        rotation_handler = RotationHandler(self.rotatingRectIcon, self)
        stretch_handler_top_right = ScaleHandler(self.topRightStretchIcon, self, self.item.boundingRect, corner="top_right")
        stretch_handler_top_left = ScaleHandler(self.topLeftStretchIcon, self, self.item.boundingRect, corner="top_left")
        stretch_handler_bottom_right = ScaleHandler(self.bottomRightStretchIcon, self, self.item.boundingRect, corner="bottom_right")
        stretch_handler_bottom_left = ScaleHandler(self.bottomLeftStretchIcon, self, self.item.boundingRect, corner="bottom_left")
        return [rotation_handler, stretch_handler_top_left, stretch_handler_top_right, stretch_handler_bottom_right, stretch_handler_bottom_left]

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
        if round(matrix.determinant(), 3) != 1:
            self.item.setTransform(matrix, combine=combine)
        else:
            QGraphicsItem.setTransform(self, matrix, combine=combine)

    def shape(self):
        path = QPainterPath()
        path.addRect(self.itemBoundingRect())
        for handler in self.transformation_handlers:
            path.addRect(handler.rect)
        return path

    def itemBoundingRect(self):
        """ This default behaviour kinda suck if bouding rect is almost zero in a directino the bounding rect will be wider however the item will be 'stuck' to the side """
        path = QPainterPath()
        bounding_rect = self.item.boundingRect()
        min_width, min_height = 20, 20
        width = max(min_width, bounding_rect.width())
        height = max(min_height, bounding_rect.height())
        x_offset = 10 if width == min_width else 0
        y_offset = 10 if height == min_height else 0

        rect = QRectF(bounding_rect.x() - x_offset, bounding_rect.y() - y_offset, width,height)
        path.addRect(rect)
        return self.item.transform().map(path).boundingRect()

    def transformOriginPoint(self):
        return self.mapFromScene(self.itemBoundingRect().center())

    def mouseMoveEvent(self, event) -> None:
        self.prepareGeometryChange()
        self.update()
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

    # TODO: Match args to abstract class
    def paint(self, painter, option, widget) -> None:
        if self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable == 0:
            return
        # TODO is the below line necessary, since this is a parent shouldnt the event propogate down by default?
#        self.item.paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(self._pen)
            painter.drawRect(self.itemBoundingRect())
            for handler in self.transformation_handlers:
                painter.drawRect(handler.rect) # Make this dynamic... handler should implement paint?

    def boundingRect(self):
        path = QPainterPath()
        path.addRect(self.itemBoundingRect())
        for handler in self.transformation_handlers:
            path.addRect(handler.rect)
        return path.boundingRect()



    def rotatingRectIcon(self) -> QRectF:
        handle_size = 14 # TODO: make this more dynamic
        item_boundingRect = self.itemBoundingRect()
        center_right = QPointF(item_boundingRect.right(), item_boundingRect.center().y())
        return QRectF(center_right.x() - handle_size / 2, center_right.y() - handle_size / 2, handle_size, handle_size )

    def topRightStretchIcon(self) -> QRectF:
        handle_size = 14
        item_boundingRect = self.itemBoundingRect()
        top_right = QPointF(item_boundingRect.right(), item_boundingRect.top())
        return QRectF(top_right.x() - handle_size / 2, top_right.y() - handle_size / 2, handle_size, handle_size)

    def topLeftStretchIcon(self) -> QRectF:
        handle_size = 14
        item_boundingRect = self.itemBoundingRect()
        top_left = QPointF(item_boundingRect.left(), item_boundingRect.top())
        return QRectF(top_left.x() - handle_size / 2, top_left.y() - handle_size / 2, handle_size, handle_size)

    def bottomRightStretchIcon(self) -> QRectF:
        handle_size = 14
        item_boundingRect = self.itemBoundingRect()
        bottom_right = QPointF(item_boundingRect.right(), item_boundingRect.bottom())
        return QRectF(bottom_right.x() - handle_size / 2, bottom_right.y() - handle_size / 2, handle_size, handle_size)

    def bottomLeftStretchIcon(self) -> QRectF:
        handle_size = 14
        item_boundingRect = self.itemBoundingRect()
        bottom_left = QPointF(item_boundingRect.left(), item_boundingRect.bottom())
        return QRectF(bottom_left.x() - handle_size / 2, bottom_left.y() - handle_size / 2, handle_size, handle_size)
