from __future__ import annotations
from os import RTLD_GLOBAL
from pathlib import Path
from typing import overload
from math import cos, sin, radians, pi

from PyQt6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPainterPath, QPen, QKeyEvent, QTextCursor, QTransform
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QLine, QLineF, QPoint, QPointF, QSize, Qt, QRectF
from PyQt6.QtSvg import QSvgGenerator, QSvgRenderer
from PyQt6.QtSvgWidgets import QGraphicsSvgItem
from PyQt6.QtWidgets import (QGraphicsColorizeEffect, QGraphicsEllipseItem, QGraphicsItemGroup, QGraphicsLineItem, QGraphicsPathItem, QGraphicsSceneMouseEvent, QGraphicsTextItem,QGraphicsItem, QGraphicsRectItem, QGraphicsTransform)

from .wrappers import DeepCopyableSvgItem, DeepCopyableLineABC


class DeepCopyableArrowItem(DeepCopyableLineABC):
    def __init__(self, line: QLineF | None = None,
                 point1: QPointF |  None = None,
                 point2: QPointF | None = None,
                 ):
        super().__init__()
        self.arrow_length = 20
        if line is None and point1 is None and point2 is None:
            self.line_item = QGraphicsLineItem()
        elif isinstance(line, QLineF):
            self.line_item = QGraphicsLineItem(line)
        elif isinstance(point1, QPointF) and isinstance(point1, QPointF):
            self.line_item = QGraphicsLineItem(point1, point2)
        else:
            raise TypeError("Unsupported argument type")
        left_line, right_line = self.build_arrow_head_lines()
        self.left_arrow_line = QGraphicsLineItem(left_line)
        self.right_arrow_line = QGraphicsLineItem(right_line)
        self.objects = [self.line_item, self.left_arrow_line, self.right_arrow_line]


    def build_arrow_head_lines(self) -> tuple[QLineF, QLineF]:
        p2_scene = self.line_item.mapToScene(self.line_item.line().p2())
        rotation_radians = radians(self.line_item.line().angle())
        x_left, y_left = -cos(45) * self.arrow_length, -sin(45)* self.arrow_length
        x_right, y_right = x_left, -y_left
        # scene has reflected y axis
        left_point_rotated = QPointF(cos(rotation_radians) * x_left, -sin(rotation_radians) * x_left) + QPointF(-sin(rotation_radians) * y_left, -cos(rotation_radians) * y_left)
        right_point_rotated = QPointF(cos(rotation_radians) * x_right, -sin(rotation_radians) * x_right) + QPointF(-sin(rotation_radians) * y_right, -cos(rotation_radians) * y_right)
        left_line = QLineF(p2_scene.x(), p2_scene.y(), p2_scene.x() + left_point_rotated.x(), p2_scene.y() + left_point_rotated.y())
        right_line = QLineF(p2_scene.x(), p2_scene.y(), p2_scene.x() + right_point_rotated.x(), p2_scene.y() + right_point_rotated.y())
        return left_line, right_line

    def transform(self) -> QTransform:
        return self.line_item.transform()

    def sceneTransform(self) -> QTransform:
        return self.line_item.sceneTransform()

    def setTransform(self, matrix: QTransform, combine: bool=False):
        self.line_item.setTransform(matrix, combine=True)
        left_arrow, right_arrow = self.build_arrow_head_lines()
        self.left_arrow_line.setLine(left_arrow)
        self.right_arrow_line.setLine(right_arrow)

    def setLine(self, line: QLineF):
        self.line_item.setLine(line)
        left_line, right_line = self.build_arrow_head_lines()
        self.left_arrow_line.setLine(left_line)
        self.right_arrow_line.setLine(right_line)
        self.update()

    def boundingRect(self):
        rect = QRectF()
        for obj in self.objects:
            rect |= obj.boundingRect()
        return rect

    def paint(self, painter: QPainter | None, option, widget=None):
        if painter is None:
            return
        for obj in self.objects:
            obj.paint(painter, option, widget=widget)
#            painter.drawLine(QLineF(obj.mapToScene(obj.line().p1()), obj.mapToScene(obj.line().p2())))

    def setPen(self, pen: QPen):
        for obj in self.objects:
            obj.setPen(pen)

    def setParentItem(self, parent):
        for obj in self.objects:
            obj.setParentItem(parent)

    def setFlag(self, flag, enabled: bool = True):
        for obj in self.objects:
            obj.setFlag(flag, enabled)

    def transformOriginPoint(self) -> QPointF:
        return self.line_item.transformOriginPoint()

    def to_svg(self, defs: dict) -> str:
        pen_svg = self.pen_to_svg(self.line_item.pen())
        line = self.line_item.line()
        transform = self.line_item.sceneTransform()
        transform_svg = self.transform_to_svg(transform)
        # TODO
        item_svg = f'<polyline points="{line.x1()} {line.y1()} {line.x2()} {line.y2()}" style="{pen_svg}"/>'
        return (f'<g transform="{transform_svg}">\n'
                f'  {item_svg}\n'
                f'</g>\n')

    def __deepcopy__(self, memo) -> DeepCopyableArrowItem:
        if (parent := self.parentItem()):
            new_line = QLineF(parent.mapFromParent(self.line_item.line().p1()), parent.mapFromParent(self.line_item.line().p2()))
        else:
            new_line = self.line_item.line()
        new_item = DeepCopyableArrowItem(new_line)
        new_item.setPen(self.copy_pen(self.line_item.pen()))
        new_item.setTransform(self.transform())
        new_item.setPos(self.pos())
        new_item.setZValue(self.zValue())
        new_item.setVisible(self.isVisible())
        new_item.setOpacity(self.opacity())
        new_item.setFlags(self.flags())
        return new_item

    def pos(self): return self.line_item.pos()
    def scenePos(self): return self.line_item.scenePos()
    def setZValue(self, z): self.line_item.setZValue(z)
    def isVisible(self): return self.line_item.isVisible()
    def opacity(self): return self.line_item.opacity()
    def setVisible(self, visible):
        for obj in self.objects:
            obj.setVisible(visible)
    def line(self):
        return self.line_item.line()

    def setPos(self, pos):
        for obj in self.objects:
            obj.setPos(pos)
