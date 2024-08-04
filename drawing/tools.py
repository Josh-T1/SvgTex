from abc import ABC, abstractmethod
from collections.abc import Callable
from PyQt6.QtGui import QBrush, QMouseEvent, QPen, QPainterPath
from PyQt6.QtCore import QPointF, Qt, pyqtBoundSignal, QRectF
from PyQt6.QtWidgets import (QGraphicsItem, QGraphicsPathItem, QGraphicsView, QGraphicsScene)

from ..graphics import DeepCopyableEllipseItem, DeepCopyableLineItem, DeepCopyablePathItem, DeepCopyableRectItem, SelectableRectItem, DeepCopyableTextbox

# GraphicsItems with size smaller than tolerence will be discarded from scene. Assumed to be 'miss click' items
TOLERENCE = 10

class DrawingHandler(ABC):
    """ Abstact base class for drawing handlers """
    @abstractmethod
    def __init__(self, handler_signal: pyqtBoundSignal) -> None:
        self.handler_signal = handler_signal

    @abstractmethod
    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    @abstractmethod
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass

    @abstractmethod
    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass

    def max_z_value(self, scene: QGraphicsScene):
        """ Returns z-value of graphicsitem in the forefront of the scene """
        max_val = 0
        for item in scene.items():
            if not isinstance(item, QGraphicsItem):
                continue
            if (item_z_val:= item.zValue()) > max_val:
                max_val = item_z_val
        return max_val

class PaintHandler(ABC):
    """ Abstact base class for tools which 'paint'. eg fill tool """
    @abstractmethod
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, brush: QBrush):
        pass

class NullDrawingHandler(DrawingHandler):
    """ No drawing behaviour """
    def __init__(self, handler_signal: pyqtBoundSignal):
        super().__init__(handler_signal)

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass

class FillPaintHandler(PaintHandler):
    def __init__(self):
        super().__init__()

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, brush: QBrush):
        scene = view.scene()
        if not scene:
            return
        selected = scene.selectedItems()
        for item in selected:
            method = getattr(item, "setBrush", None)
            if callable(method):
                method(brush)

class TextboxDrawingHandler(DrawingHandler):
    """ Tool for drawing Textbox's """
    def __init__(self, handler_signal):
        super().__init__(handler_signal)
        self.start_point = None
        self.drawing = False
        self.rect_item: Textbox | None = None
        self.selectable_rect_item: SelectableRectItem | None = None

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton:
            scene = view.scene()
            if scene is None:
                return
            self.drawing = True
            self.start_point = event.scenePosition()
            self.start_point = view.mapToScene(event.position().toPoint())

    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if self.drawing:
            scene = view.scene()
            if self.start_point is None or not self.drawing or scene is None:
                return
            event_pos = view.mapToScene(event.position().toPoint())
            bottom_right_x = event_pos.x() if event_pos.x() > self.start_point.x() else self.start_point.x()
            bottom_right = QPointF( bottom_right_x, event_pos.y())

            start_point = self.start_point if self.start_point.x() < event_pos.x() else QPointF(event_pos.x(), self.start_point.y())
            rect = QRectF(start_point, bottom_right)
            if not self.rect_item:
                self.rect_item = Textbox(rect)
                self.rect_item.moving = True
                scene.addItem(self.rect_item)
            else:
                self.rect_item.setRect(rect)

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        scene = view.scene()
        if scene is None: return

        scene.removeItem(self.rect_item)
        if self.rect_item and self.rect_item.boundingRect().width() > (TOLERENCE + 7) and self.rect_item.boundingRect().height() > (TOLERENCE + 7):
            # prevent accidental creation of textbox item
            self.selectable_rect_item = SelectableRectItem(self.rect_item, self.handler_signal)
            scene.addItem(self.selectable_rect_item)
            self.selectable_rect_item.setZValue(self.max_z_value(scene))

            self.rect_item.moving = False
            self.rect_item = None
        self.drawing = False

class LineDrawingHandler(DrawingHandler):
    """ Tool for drawing straight lines """
    def __init__(self, handler_signal: pyqtBoundSignal):
        super().__init__(handler_signal)
        self.start_point = None
        self.current_line = None


    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if (self.start_point is not None and self.current_line is not None):
            end_point = view.mapToScene(event.position().toPoint())
            self.current_line.setLine(self.start_point.x(), self.start_point.y(), end_point.x(), end_point.y())

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = view.mapToScene(event.position().toPoint())
            self.current_line = DeepCopyableLineItem()
            self.current_line.setPen(pen)
            scene = view.scene()
            if scene:
                scene.addItem(self.current_line)

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton and self.current_line:
            scene = view.scene()
            if self.start_point is None or scene is None:
                return
            end_point = view.mapToScene(event.position().toPoint())

            self.current_line.setLine(self.start_point.x(), self.start_point.y(), end_point.x(), end_point.y())
            scene.removeItem(self.current_line)
            if self.current_line.line().length() > TOLERENCE:
                selectable_line = SelectableRectItem(self.current_line, self.handler_signal)
                scene.addItem(selectable_line)
                selectable_line.setZValue(self.max_z_value(scene))

            self.start_point = None
            self.current_line = None


class ShapeDrawingHandler(DrawingHandler):
    """ Tool for drawing rectangles """
    def __init__(self, handler_signal: pyqtBoundSignal, shape: Callable[[QRectF], DeepCopyableRectItem | DeepCopyableEllipseItem]) -> None:
        super().__init__(handler_signal)
        self.shape: Callable[[QRectF], DeepCopyableEllipseItem | DeepCopyableRectItem] = shape
        self.tmp_scene_item = None
        self.drawing_started = False
        self.start_point: None | QPointF = None
        self.selectable_rect_item = None

    @staticmethod
    def _get_rect(start_point: QPointF, event_pos: QPointF) -> QRectF:
        top_left_x = min(start_point.x(), event_pos.x())
        top_left_y = min(start_point.y(), event_pos.y())
        bottom_right_x = max(start_point.x(), event_pos.x())
        bottom_right_y = max(start_point.y(), event_pos.y())
        width = bottom_right_x - top_left_x
        height = bottom_right_y - top_left_y
        return QRectF(top_left_x, top_left_y, width, height)

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing_started = True
            self.start_point = view.mapToScene(event.position().toPoint())

    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        scene = view.scene()
        if self.start_point is not None and scene is not None and self.drawing_started:
            if self.tmp_scene_item is None:
                event_pos = view.mapToScene(event.position().toPoint())
                rect = self._get_rect(self.start_point, event_pos)
                self.tmp_scene_item = self.shape(rect)
                self.tmp_scene_item.setPen(pen)
                scene.addItem(self.tmp_scene_item)
                self.tmp_scene_item.setZValue(self.max_z_value(scene))
            else:
                event_pos = view.mapToScene(event.position().toPoint())
                rect = self._get_rect(self.start_point, event_pos)
                self.tmp_scene_item.setRect(rect)

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        scene = view.scene()
        if scene is not None and self.tmp_scene_item:
            scene.removeItem(self.tmp_scene_item)

            if self.tmp_scene_item.boundingRect().width() > TOLERENCE or self.tmp_scene_item.boundingRect().height() > TOLERENCE:
                selectable_rect = SelectableRectItem(self.tmp_scene_item, self.handler_signal)
                scene.addItem(selectable_rect)

            self.drawing_started = False
            self.tmp_scene_item = None

class RectDrawingHandler(ShapeDrawingHandler):
    def __init__(self, handler_signal):
        super().__init__(handler_signal, DeepCopyableRectItem)

class EllipseDrawingHandler(ShapeDrawingHandler):
    def __init__(self, handler_signal):
        super().__init__(handler_signal, DeepCopyableEllipseItem)

class BelzierDrawingHandler(DrawingHandler):
    def __init__(self, handler_signal: pyqtBoundSignal):
        super().__init__(handler_signal)
        self.drawing_started = False
        self.current_line = None
        self.selectable_rect_item = None
        self.item = None

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if self.drawing_started:
            # add stuff to scene
            # if new line is super short then flase
            self.drawing_started = False
        else:
            self.drawing_started = True
        pass
    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass

class FreeHandDrawingHandler(DrawingHandler):
    """ Handles drawing behaviour of free hand tool """
    def __init__(self, handler_signal: pyqtBoundSignal):
        super().__init__(handler_signal)
        self.drawing_started = False
        self.current_line = None
        self.current_path_item = None

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        scene = view.scene()
        if scene is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing_started = True
            start_point = view.mapToScene(event.position().toPoint())
            self.current_path = QPainterPath(start_point)
            self.current_path_item = QGraphicsPathItem(self.current_path)
            self.current_path_item.setPen(pen)
            scene.addItem(self.current_path_item)
            self.current_path_item.setZValue(self.max_z_value(scene))

    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        scene = view.scene()
        # Check for events occuring out of bounds or any required variables being None
        if (not self.drawing_started or
            scene is None or
            not self.inBounds(scene, event) or
            self.current_path_item is None
            ):
            return

        end = view.mapToScene(event.position().toPoint())
        # Only update current path if new event position is different from the previous entry event position
        if self.current_path.currentPosition() != end:
            self.current_path.lineTo(end)
            self.current_path_item.setPath(self.current_path)

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        scene = view.scene()
        # Code should run fine without this line
        if scene is None or self.current_path_item is None:
            return

        scene.removeItem(self.current_path_item)
        if self.current_path_item.path().length() > TOLERENCE:
            copyable_path = DeepCopyablePathItem(self.current_path_item.path())
            copyable_path.setPen(pen)
            selectable_path_item = SelectableRectItem(copyable_path, self.handler_signal)
            scene.addItem(selectable_path_item)
        self.drawing_started = False

    def inBounds(self, scene: QGraphicsScene, event: QMouseEvent) -> bool:
        """ Returns true if event took place within the bounds of scene """
        return scene.sceneRect().contains(event.position())
