from abc import ABC, abstractmethod
from PyQt6.QtGui import  QColor, QKeyEvent, QMouseEvent, QPen, QPainterPath, QTextCursor
from PyQt6.QtCore import  QObject, QPointF, Qt, pyqtBoundSignal, pyqtSignal,  QRectF, QSizeF
from PyQt6.QtWidgets import (QGraphicsPathItem, QGraphicsTextItem, QGraphicsView,
                           QGraphicsScene, QGraphicsLineItem, QGraphicsRectItem)
from enum import Enum
from ..graphics.graphics_items import SelectableRectItem
from ..utils import KeyCodes

class Handlers(Enum):
    Selector = "NullDrawingHandler"
    Freehand = "FreeHandDrawingHandler"
    Line = "LineDrawingHandler"
    Textbox = "TextboxDrawingHandler"

class DrawingHandler(ABC):
    @abstractmethod
    def __init__(self, handler_signal: pyqtBoundSignal) -> None:
        self.handler_signal = handler_signal
    """ Implements drawing behaviour from user inputs. ie how the 'tool' behaves (freehand, curve, ...)  """
    @abstractmethod
    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    @abstractmethod
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    @abstractmethod
    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass

class NullDrawingHandler(DrawingHandler):
    """ No drawing behaviour """
    def __init__(self, handler_signal: pyqtBoundSignal):
        super().__init__(handler_signal)
        self.pen = None
        self.start_point = None
        self.current_line = None

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass
    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        pass

class ClippedTextItem(QGraphicsTextItem):
    def __init__(self, text, clip_rect, parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditable | Qt.TextInteractionFlag.TextSelectableByMouse
                                     | Qt.TextInteractionFlag.TextEditorInteraction)
        self.setDefaultTextColor(QColor(Qt.GlobalColor.black))
        self.clipRect = clip_rect

    def setClipRect(self, rect: QRectF):
        self.clipRect = self.mapRectFromParent(rect)

    def paint(self, painter, option, widget=None):
        painter.setClipRect(self.clipRect)
        super().paint(painter, option, widget)

class Textbox(QGraphicsRectItem):
    def __init__(self, rect: QRectF, parent=None):
        super().__init__(rect, parent=parent)
        self.moving = True
        self.default_message = "Text..."

        self.text = ClippedTextItem(self.default_message, self.rect(), parent=self)
        self.text.setTextWidth(rect.width())
        self.text.setPos(self.rect().topLeft())
        self.moving_pen = QPen(Qt.GlobalColor.darkYellow)
        self.stationary_pen = QPen(Qt.GlobalColor.transparent)

    def setRect(self, *args, **kwargs):
        super().setRect(*args, **kwargs)
        self.text.setTextWidth(self.rect().width())
        self.text.setClipRect(self.rect())
        self.text.setPos(self.rect().topLeft())
        self.text.update()

    def paint(self, painter, option, widget=None):
        if self.moving:
            painter.setPen(self.moving_pen)
            painter.drawRect(self.rect())
        else:
            painter.setPen(self.stationary_pen)
            painter.drawRect(self.rect())
#        super().paint(painter, option, widget)

    def keyPressEvent(self, event: QKeyEvent | None):
        if event is None:
            return
        if event.key() == KeyCodes.Key_Delete.value:
            cursor = self.text.textCursor()
            cursor.deletePreviousChar()

            event.accept()

        elif event.key() == KeyCodes.Key_Left.value:
            cursor = self.text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
            self.text.setTextCursor(cursor)

        elif event.key() == KeyCodes.Key_Right.value:
            cursor = self.text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
            self.text.setTextCursor(cursor)
        else:
            super().keyPressEvent(event)

    def setTransform(self, transform, combine):
        if round(transform.determinant(), 3) == 1:
            super().setTransform(transform, combine)
        else:
            current_rect = self.rect()
            new_rect = transform.mapRect(current_rect)
            self.setRect(new_rect)

class TextboxDrawingHandler(DrawingHandler):
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
            self.start_point = view.mapToScene(event.position().toPoint())

    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if self.drawing:
            scene = view.scene()
            if self.start_point is None or not self.drawing or scene is None:
                return
            bottom_right = view.mapToScene(event.position().toPoint())
            rect = QRectF(self.start_point, bottom_right)
            if not self.selectable_rect_item or not self.rect_item:
                self.rect_item = Textbox(rect)
                self.selectable_rect_item = SelectableRectItem(self.rect_item, Handlers.Selector.value, self.handler_signal)
                self.rect_item.setParentItem(self.selectable_rect_item)
                scene.addItem(self.selectable_rect_item)
            else:
                self.rect_item.setRect(rect)

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        scene = view.scene()
        if self.rect_item and scene:
            self.rect_item.moving = False
            self.rect_item = None
        self.drawing = False


class LineDrawingHandler(DrawingHandler):
    """ Tool for drawing straight lines """
    def __init__(self, handler_signal: pyqtBoundSignal):
        super().__init__(handler_signal)
        self.start_point = None
        self.current_line = None

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton and self.current_line:
            scene = view.scene()
            if self.start_point is None or scene is None:
                return
            end_point = view.mapToScene(event.position().toPoint())

            scene.removeItem(self.current_line)
            self.current_line.setLine(self.start_point.x(), self.start_point.y(), end_point.x(), end_point.y())
            selectable_line = SelectableRectItem(self.current_line, Handlers.Selector.value, self.handler_signal)
            scene.addItem(selectable_line)

            self.start_point = None
            self.current_line = None

    def mouseMove(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if (self.start_point is not None and self.current_line is not None):
            end_point = view.mapToScene(event.position().toPoint())
            self.current_line.setLine(self.start_point.x(), self.start_point.y(), end_point.x(), end_point.y())

    def mousePress(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = view.mapToScene(event.position().toPoint())
            self.current_line = QGraphicsLineItem()
            self.current_line.setPen(pen)
            scene = view.scene()
            if scene:
                scene.addItem(self.current_line)

class BelzierDrawingHandler(DrawingHandler):
    def __init__(self, handler_signal):
        super().__init__(handler_signal)

class FreeHandDrawingHandler(DrawingHandler):
    """ Handles drawing behaviour of free hand tool """
    def __init__(self, handler_signal: pyqtBoundSignal):
        super().__init__(handler_signal)
        self.drawing_started = False
        self.current_line = None
        self.current_path_item = None

    def mouseRelease(self, view: QGraphicsView, event: QMouseEvent, pen: QPen):
        scene = view.scene()
        # Code should run fine without this line
        if scene is None or self.current_path_item is None:
            return

        scene.removeItem(self.current_path_item)
        selectable_path_item = SelectableRectItem(self.current_path_item, Handlers.Selector.value, self.handler_signal)
        scene.addItem(selectable_path_item)
        self.drawing_started = False

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

    def inBounds(self, scene: QGraphicsScene, event: QMouseEvent) -> bool:
        """ Returns true if event took place within the bounds of scene """
        return scene.sceneRect().contains(event.position())

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

class DrawingController(QObject):
    """
    Accepts QMouseEvents and delegates the drawing responsibility to its target DrawingHandler object.
    Class properties such as 'tool' or 'handler' are updated by connecting their respective set{property} method to other QWidget signals. These
    properties are then used to alter the behaviour of DrawingHandler objects
    """

    handler_signal = pyqtSignal(str)
    def __init__(self, scene_view: QGraphicsView | None = None, handler: DrawingHandler | None = None, tool: QPen | None = None):
        """
        -- Params --
        scene_view: QGraphicsScene object
        handler: responsible for implmenting drawing tool behaviour (e.g free hand tool)
        """
        super().__init__()
        self.scene_view = scene_view
        self.handler = handler if handler is not None else NullDrawingHandler(handler_signal=self.handler_signal)
        self.tool = tool if tool is not None else QPen(Qt.GlobalColor.black)
        self.name_to_classname_mapping = {Handlers.Line.value: LineDrawingHandler,
                                          Handlers.Freehand.value: FreeHandDrawingHandler,
                                          Handlers.Selector.value: NullDrawingHandler,
                                          Handlers.Textbox.value: TextboxDrawingHandler}

    def mousePressEvent(self, event: QMouseEvent):
        if self.handler and self.scene_view and self.tool:
            self.handler.mousePress(self.scene_view, event, self.tool)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.handler and self.scene_view and self.tool:
            self.handler.mouseMove(self.scene_view, event, self.tool)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.handler is not None and self.scene_view is not None and self.tool:
            self.handler.mouseRelease(self.scene_view, event, self.tool)

    def setSceneView(self, scene_view: QGraphicsView) -> None:
        self.scene_view = scene_view

    def setHandler(self, handler: DrawingHandler):
        self.handler = handler
        self.handler_signal.emit(self.handler.__class__.__name__)

    def setHandlerFromName(self, name: str) -> None:
        """
        Sets self.handler equal to the result of the mapping from param name(str) to
        class cls.__name__ or NullDrawingHandler, a DrawingHandler subclass

        -- Params --
        name: name of DrawingHandler subclass as string
        """
        value = Handlers[name].value
        class_obj = self.name_to_classname_mapping.get(value, NullDrawingHandler)
        handler_inst = class_obj(self.handler_signal)
        self.setHandler(handler_inst)

    def setPenWidth(self, size: int) -> None:
        self.tool.setWidth(size)
