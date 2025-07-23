from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Protocol

from PyQt6.QtGui import QBrush, QMouseEvent, QPen, QPainterPath
from PyQt6.QtCore import QPointF, Qt, pyqtBoundSignal, QRectF, QLineF
from PyQt6.QtWidgets import (QGraphicsItem, QGraphicsPathItem, QGraphicsView, QGraphicsScene, QGraphicsRectItem)

from ..graphics import (DeepCopyableEllipseItem, DeepCopyableLineItem, DeepCopyablePathItem, DeepCopyableRectItem, SelectableRectItem, DeepCopyableTextbox,
                        DeepCopyableArrowItem, DeepCopyableLineABC)

TOLERENCE = 10 # GraphicsItems with width or height less than tolerence will be discarded from scene. Assumed to be 'miss click' items

class DrawingHandler(ABC):
    """ Abstact base class for drawing handlers """
    def __init__(self, handler_signal: pyqtBoundSignal) -> None:
        self.handler_signal = handler_signal
    @abstractmethod
    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen) -> None: ...
    @abstractmethod
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen) -> None: ...
    @abstractmethod
    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen) -> None: ...
    def max_z_value(self, scene: QGraphicsScene):
        """ Returns z-value of graphicsitem in the forefront of the scene """
        max_val = 0
        for item in scene.items():
            if not isinstance(item, QGraphicsItem):
                continue
            if (item_z_val:= item.zValue()) > max_val:
                max_val = item_z_val
        return max_val

class ToolProtocol(Protocol):
    """ Protocol for any tool that only requires mouse press """
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, tool: QBrush | QPen) -> None: ...

class NullDrawingHandler(DrawingHandler):
    """ No drawing behaviour """
    def __init__(self, handler_signal: pyqtBoundSignal):
        super().__init__(handler_signal)

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        return
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        return
    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        return

class BrushTool(ToolProtocol):
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, tool: QBrush):
        scene = view.scene()
        if not scene: return
        selected = scene.selectedItems()
        for item in selected:
            method = getattr(item, "setBrush", None)
            if callable(method):
                method(tool)

class PenTool(ToolProtocol):
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, tool: QPen):
        scene = view.scene()
        if not scene: return
        selected = scene.selectedItems()
        for item in selected:
            method = getattr(item, "setPen", None)
            if callable(method):
                method(tool)

class TextboxDrawingHandler(DrawingHandler):
    """ Tool for drawing Textbox's """
    def __init__(self, handler_signal):
        super().__init__(handler_signal)
        self.start_point = None
        self.drawing = False
        self.rect_item: DeepCopyableTextbox | None = None
        self.selectable_rect_item: SelectableRectItem | None = None

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton:
            scene = view.scene()
            if scene is None:
                return
            self.drawing = True
            self.start_point = view.mapToScene(event.position().toPoint())

    def _get_rect(self, start_point: QPointF, event_pos: QPointF) -> QRectF:
        bottom_right_x = event_pos.x() if event_pos.x() > start_point.x() else start_point.x()
        bottom_right = QPointF( bottom_right_x, event_pos.y())
        start_point = start_point if start_point.x() < event_pos.x() else QPointF(event_pos.x(), start_point.y())
        return QRectF(start_point, bottom_right)

    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if self.drawing and self.start_point is not None:
            scene = view.scene()
            if scene is None and self.rect_item is None:
                return

            event_pos = view.mapToScene(event.position().toPoint())
            rect = self._get_rect(self.start_point, event_pos)

            if self.rect_item is None:
                self.rect_item = DeepCopyableTextbox(rect)
                self.rect_item.moving = True
                scene.addItem(self.rect_item) # type: ignore -> impossible for scene to be none in our app
            else:
                self.rect_item.setRect(rect)

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        scene = view.scene()
        if scene is None: return
        if self.rect_item:
            scene.removeItem(self.rect_item)
        if self.rect_item and self.rect_item.boundingRect().width() > (TOLERENCE + 7) and self.rect_item.boundingRect().height() > (TOLERENCE + 7):
            # prevent accidental creation of textbox item
            self.selectable_rect_item = SelectableRectItem(self.rect_item, self.handler_signal)
            scene.addItem(self.selectable_rect_item)
            self.selectable_rect_item.setZValue(self.max_z_value(scene))

            self.rect_item.moving = False
            self.rect_item = None
        self.drawing = False


class GenericLineDrawingHandler(DrawingHandler):
    """ Tool for drawing straight lines """
    def __init__(self, line_item: Callable[[], DeepCopyableLineABC], handler_signal: pyqtBoundSignal):
        super().__init__(handler_signal)
        self.start_point = None
        self.current_line = None
        self.line_item = line_item
        self.drawing = False

    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if (self.start_point is not None and self.current_line is not None and self.drawing):
            end_point = view.mapToScene(event.position().toPoint())
            self.current_line.setLine(QLineF(self.start_point, end_point))

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.start_point = view.mapToScene(event.position().toPoint())
            self.current_line = self.line_item()
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

            self.current_line.setLine(QLineF(self.start_point, end_point))
            if self.current_line.line().length() > TOLERENCE:
                selectable_line = SelectableRectItem(self.current_line, self.handler_signal)
                scene.addItem(selectable_line)
                selectable_line.setZValue(self.max_z_value(scene))

            self.start_point = None
            self.current_line = None
            self.drawing = False

class LineDrawingHandler(GenericLineDrawingHandler):
    def __init__(self, signal: pyqtBoundSignal):
        super().__init__(DeepCopyableLineItem, signal)

class ArrowDrawingHandler(GenericLineDrawingHandler):
    def __init__(self, signal: pyqtBoundSignal):
        super().__init__(DeepCopyableArrowItem, signal)

class ShapeDrawingHandler(DrawingHandler):
    """ Tool for drawing rectangles """
    def __init__(self, handler_signal: pyqtBoundSignal, shape: Callable[[], DeepCopyableRectItem | DeepCopyableEllipseItem]) -> None:
        super().__init__(handler_signal)
        self.shape_callback = shape
        self.drawing_started = False
        self.shape_item = None
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
        scene = view.scene()
        if scene is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing_started = True
            self.start_point = view.mapToScene(event.position().toPoint())
            self.shape_item = self.shape_callback()
            scene.addItem(self.shape_item)

    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if self.start_point is not None and self.shape_item is not None and self.drawing_started:
            event_pos = view.mapToScene(event.position().toPoint())
            rect = self._get_rect(self.start_point, event_pos)
            self.shape_item.setRect(rect)

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        scene = view.scene()
        if scene is None:
            return
        if event.button() == Qt.MouseButton.LeftButton and self.shape_item is not None:
            if self.shape_item.boundingRect().width() > TOLERENCE or self.shape_item.boundingRect().height() > TOLERENCE:
                selectable_rect = SelectableRectItem(self.shape_item, self.handler_signal)
                scene.addItem(selectable_rect)

            self.drawing_started = False
            self.shape_item = None

class RectDrawingHandler(ShapeDrawingHandler):
    def __init__(self, handler_signal):
        super().__init__(handler_signal, DeepCopyableRectItem)

class EllipseDrawingHandler(ShapeDrawingHandler):
    def __init__(self, handler_signal):
        super().__init__(handler_signal, DeepCopyableEllipseItem)

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
        if (not self.drawing_started or scene is None
            or not self.inBounds(scene, event) or self.current_path_item is None
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

class ConnectedLineHandler(DrawingHandler):
    connection_zones: list[QPointF] = []
    radius = 5

    def __init__(self, handler_signal: pyqtBoundSignal):
        self.handler_signal = handler_signal
        self.drawing = False
        self.current_line = None
        self.start_point = None
        self._tolerance = 15

    @classmethod
    def _add_connection_zone(cls, pos: QPointF):
        """
        pos: position in scene coordinates
        """
        cls.connection_zones.append(pos)

    @staticmethod
    def _euclid_distance(p1: QPointF, p2: QPointF):
        return ((p1.x() - p2.x())**2 + (p1.y() - p2.y())**2 )** (1/2)

    @classmethod
    def attempt_connection(cls, pos: QPointF) -> None | QPointF:
        for point in cls.connection_zones:
            if cls._euclid_distance(point, pos) < cls.radius:
                return point

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen) -> None:
        scene = view.scene()
        if scene is None:
            return None

        if event.button() == Qt.MouseButton.LeftButton:
            # End drawing
            if self.drawing and self.start_point is not None and self.current_line is not None:
                self._end_drawing(self.current_line, scene)

            self._init_drawing(view, scene, event, pen)


    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen) -> None:
        if self.start_point is not None and self.current_line is not None and self.drawing:
            event_pos = view.mapToScene(event.position().toPoint())
            maybe_point = self.attempt_connection(event_pos)
            if maybe_point is not None and self.current_line.line().length() > self._tolerance:
                scene = view.scene()
                if scene is None:
                    return None
                self.connection_zones.append(self.current_line.line().p2())
                self.current_line.setLine(QLineF(self.start_point, maybe_point))
                self._end_drawing(self.current_line, scene)
                self._init_drawing(view, scene, event, pen)
            else:
                self.current_line.setLine(QLineF(self.start_point, event_pos))

    def mouseRelease(self, view, event, pen):
        return

    def _end_drawing(self, line_item, scene):
        selectable_rect = SelectableRectItem(line_item, select_signal=self.handler_signal)
        scene.addItem(selectable_rect)

    def _init_drawing(self, view, scene, event, pen):
        self.drawing = True
        event_scene_pos = view.mapToScene(event.position().toPoint())
        maybe_point = self.attempt_connection(event_scene_pos)
        if maybe_point is not None:
            self.start_point = maybe_point
        else:
            self.start_point = event_scene_pos
            self.connection_zones.append(event_scene_pos)

        self.start_point = maybe_point if maybe_point is not None else event_scene_pos
        self.current_line = DeepCopyableLineItem()
        self.current_line.setPen(pen)
        scene.addItem(self.current_line)
        self.current_line.setZValue(self.max_z_value(scene))

    def reset(self, scene):
        self.drawing = False
        if self.current_line is not None:
            scene.removeItem(self.current_line)
            self.current_line = None
        self.start_point = None
