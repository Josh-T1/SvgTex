from abc import ABC, abstractmethod
from collections.abc import Callable
from PyQt6.QtGui import QTransform
from PyQt6.QtCore import QLineF, QPointF, QRectF, QObject
from PyQt6.QtWidgets import (QGraphicsSceneMouseEvent, QGraphicsItem)
import math

class TransformationHandler(ABC):
    def __init__(self, set_rect_callback: Callable[[], QRectF], item):
        self.set_rect_callback = set_rect_callback
        self.item = item
    @abstractmethod
    def handle_mouse_move(self, event) -> None: ...
    @abstractmethod
    def handle_mouse_press(self, event) -> None: ...
    @abstractmethod
    def handle_mouse_release(self, event) -> None: ...
    @property
    def rect(self):
        return self.set_rect_callback()

class RotationHandler(TransformationHandler):
    """ RotationHandler implements rotation behaviour of QGraphicsItem """
    def __init__(self, set_rect_callback: Callable[[], QRectF], item: QGraphicsItem):
        """
        -- Params --
        set_rect_callback: Callable that returns QRectF object representing the are in which RotationHandler will handle mouseEvents
        item: the QGraphicsItem for which RotationHandler is implementing rotation behaviour
        """
        super().__init__(set_rect_callback, item)
        self.is_rotating = False
        self.is_resizing = False
        self.rotation_start_angle = 0

    def handle_mouse_press(self, event):
        if self.rect.contains(self.item.mapFromScene(event.scenePos())):
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.is_rotating = True
#            self.rotation_start_angle = self.angle(event.scenePos(), self.item.transform().map(self.item.boundingRect().center()))
            self.rotation_start_angle = self.angle(event.scenePos(), self.item.mapToScene(self.item.boundingRect().center()))

    @staticmethod
    def angle(p1: QPointF, p2: QPointF) -> float:
        """ Returns angle of the line connecting p1 with p2, measured counter clockwise starting on the right of the x-axis (x > 0). Note that the angle
        is measured from p1 to p2.
        """
        return QLineF(p1, p2).angle()

    @property
    def rect(self):
        return self.set_rect_callback()

    def handle_mouse_move(self, event: QGraphicsSceneMouseEvent):
        if self.is_rotating:
            # Modulo 360, degree of line origin -> event going clockwise
#            current_angle = self.angle(event.scenePos(), self.item.transform().map(self.item.boundingRect().center()))
            current_angle = self.angle(event.scenePos(), self.item.mapToScene(self.item.boundingRect().center()))
            angle_diff = (self.rotation_start_angle - current_angle) % 360
            transform = self.build_transform(angle_diff)
            self.item.setTransform(transform, combine=True)
            self.rotation_start_angle = current_angle

    def handle_mouse_release(self, event: QGraphicsSceneMouseEvent):
        if self.is_rotating:
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.is_rotating = False

    def build_transform(self, degrees: float):
        """
        degrees: the number of degrees
        """
        center = self.item.boundingRect().center()
        transform = QTransform()
        transform.translate(center.x() , center.y() )
        transform.rotate(degrees)
        transform.translate(-center.x() , -center.y() )
        return transform


class ScaleHandler(TransformationHandler):
    """
    ScaleHandler handles all scaling of QGraphicsItems when the users cursor is inside its rectangle. This rectangle is passed in by means of a callback and
    detects when mouse events are in the rect area. This class needs to be delegated mouseEvents as they happen. Scaling of items occurs with the opposing diagonal
    corner fixed.

    -- Limitations --
    1. We can not invert item. If you drag the top left corner towards the top right corner, you can not pass the top right corner. There is also glitching when you get close or the width of the image
    becomes tiny.
    """
    def __init__(self, set_rect_callback: Callable[[],QRectF], item: QGraphicsItem, bounding_rect_callback: Callable[[], QRectF]):
        """
        -- Params --
        set_rect_callback: Callable that returns the QRectF object representing the QRectF in which the handler should implement its functionality
        item: QGraphicsItem wich is the target of the scaling
        bounding_rect_callback: Callable wich returns the QRectF object representing the bounding rectangle of self.item
        corner: of the form '(top/down)_(right/left)'. The corner of items's bounding rectangle on which handler rect resides.
        """
        super().__init__(set_rect_callback, item)
        self.bounding_rect_callback = bounding_rect_callback
        self.stretching = False

    def edge_coordinate(self):
        """ Scene coordinates for the center of the handler rectangle  """
        return self.item.mapToScene(self.rect.center())

    def scene_corner(self):
        corner_center = self.set_rect_callback().topLeft()
        bounding_top_left = self.item.boundingRect().topLeft()
        top = round(corner_center.y() - bounding_top_left.y(), 3) == 0
        left = round(corner_center.x() - bounding_top_left.x(), 3) == 0
        return top, left

    def local_corner(self) -> tuple[bool, bool]:
        """ Returns true for 'top' if the point this handler holds reference to is located on the top of the items bounding rect in scene coordinates
        Similary returns true for 'left' if the point this handler holds reference to is located on the left of the items bounding rect in scene coordinates
        """
        corner_center = self.item.mapToScene(self.set_rect_callback().topLeft())
        bounding_rect = self.item.mapRectToScene(self.item.boundingRect())
        middle = QPointF(bounding_rect.left() +7 + (bounding_rect.width()-14) / 2 , bounding_rect.top() +7 + (bounding_rect.height() -14) / 2 )
        top = corner_center.y() < middle.y()
        left = corner_center.x() < middle.x()
        return top, left

    def handle_mouse_press(self, event: QGraphicsSceneMouseEvent):
        if self.rect.contains(self.item.mapFromScene(event.scenePos())):
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.stretching = True

    def handle_mouse_move(self, event):
        if self.stretching:
            new_coordinate = self.item.mapFromScene(event.scenePos())
            edge_coordinate = self.rect.center()

            if new_coordinate.x() == 0 or edge_coordinate.x() == 0 or edge_coordinate.y() == 0 or new_coordinate.y() == 0:
                return

            delta_x = new_coordinate.x() - edge_coordinate.x()
            delta_y = new_coordinate.y() - edge_coordinate.y()

            # Moving the cursor left has the inverse effect when draging a left corner compared with a right corner
            top, left = self.scene_corner()
            if left:
                delta_x = -delta_x

            if top:
                delta_y = -delta_y
            bounding_rect = self.item.boundingRect()
            x_scale_factor = (bounding_rect.width() + delta_x) / max(bounding_rect.width(), 10)
            y_scale_factor = (bounding_rect.height() + delta_y) / max(bounding_rect.height(), 10)
            # Prevent large scaling factors
            if x_scale_factor > 0:
                x_scale_factor_restricted = min(x_scale_factor, 1.5)
            else:
                x_scale_factor_restricted = max(x_scale_factor, -1.5)

            if y_scale_factor > 0:
                y_scale_factor_restricted = min(y_scale_factor, 1.5)
            else:
                y_scale_factor_restricted = max(y_scale_factor, -1.5)

            x_scale_factor_restricted = x_scale_factor_restricted if bounding_rect.width() > 20 or x_scale_factor_restricted > 1 else 1
            y_scale_factor_restricted = y_scale_factor_restricted if bounding_rect.height() > 20 or y_scale_factor_restricted > 1 else 1
            transform = self.build_transform(x_scale_factor_restricted, y_scale_factor_restricted)
            self.item.setTransform(transform, combine=True)

    def handle_mouse_release(self, event: QGraphicsSceneMouseEvent):
        if self.stretching:
            self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.stretching = False

    def _get_corner(self, top: bool, left: bool) -> QPointF | None:
        """ stationary corner refers the corner that stays inplace during scaling
        top: true if stationary corner is on the top item relative to scene
        left: true if stationary corner is on the left of item relative to scene
        returns: stationary corner (QPointF) of item in its local coordinates
        """
        bounding_rect = self.bounding_rect_callback()
        corners = [bounding_rect.topLeft() , bounding_rect.topRight() , bounding_rect.bottomLeft() , bounding_rect.bottomRight() ]
        corners = [(self.item.mapToScene(corner), corner) for corner in corners]
        bounding_rect = self.item.mapRectToScene(bounding_rect)
        middle = QPointF(bounding_rect.left() +7 + (bounding_rect.width()-14) / 2 , bounding_rect.top() +7 + (bounding_rect.height() -14) / 2 )
        def left_f(x):
            if left:
                return x <= middle.x()
            return x >= middle.x()
        def top_f(y):
            if top:
                return y <= middle.y()
            return y >= middle.y()
        for scene_corner, local_corner in corners:
            if top_f(scene_corner.y()) and left_f(scene_corner.x()):
                return local_corner
        return None

    def build_transform(self, x_scale_factor: float, y_scale_factor: float):
        """ Create QTransform required to scale item fixed to the opposing diagonal corner """
        top, left = self.local_corner()
        transform = QTransform()
        # We determine orientation of object through its boundingRect however boundingRect
        # holds no information pertaining to reflections. We check manually
        reflected_about_x = self.item.sceneTransform().m11() < 0
        reflected_about_y = self.item.sceneTransform().m22() < 0
        if reflected_about_x:
            left = not left
        if reflected_about_y:
            top = not top

        translate_center = self._get_corner(not top, not left)
        if translate_center is None:
            return transform

        transform.translate(translate_center.x() , translate_center.y())
        transform.scale(abs(x_scale_factor), abs(y_scale_factor))
        transform.translate(-translate_center.x() , -translate_center.y())

        return transform
