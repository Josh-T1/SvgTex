from PyQt6.QtGui import QBrush, QColor, QKeyEvent, QMouseEvent, QPen, QPainterPath
from PyQt6.QtCore import QObject, Qt, pyqtBoundSignal, pyqtSignal,  QRectF
from PyQt6.QtWidgets import (QGraphicsPathItem, QGraphicsView, QGraphicsScene, QGraphicsLineItem)
from ..drawing.tools import EllipseDrawingHandler, FillPaintHandler, DrawingHandler, LineDrawingHandler, PaintHandler, RectDrawingHandler, TextboxDrawingHandler, FreeHandDrawingHandler, NullDrawingHandler
from ..utils import Handlers
from .shortcut_manager import ShortcutManager

class DrawingController(QObject):
    """
    Accepts QMouseEvents and QKeyEvent. QKeyEvent's are passed to ShortcutManager object and QMouseEvents are passed to DrawingHandler.
    Class properties such as 'tool' or 'handler' are updated by connecting their respective set{property} method to other QWidget signals. These
    properties are then used to alter the behaviour of DrawingHandler objects
    """

    handler_signal = pyqtSignal(str)
    def __init__(self, handler: DrawingHandler | PaintHandler | None = None,
                 scene_view: QGraphicsView | None = None,
                 pen: QPen | None = None,
                 shortcut_manager: ShortcutManager | None = None,
                 brush: QBrush | None = None
                 ):
        """
        -- Params --
        scene_view: QGraphicsScene object
        handler: responsible for implmenting drawing tool behaviour (e.g free hand tool)
        """
        super().__init__()
        self.scene_view = scene_view
        self.shortcut_manager = shortcut_manager
        self.handler = handler if handler is not None else NullDrawingHandler(handler_signal=self.handler_signal)
        self.pen = pen if pen is not None else QPen(Qt.GlobalColor.black)
        self.brush = brush if brush is not None else QBrush(Qt.GlobalColor.black)
        self.name_to_classname_mapping = {Handlers.Line.value: LineDrawingHandler,
                                          Handlers.Freehand.value: FreeHandDrawingHandler,
                                          Handlers.Selector.value: NullDrawingHandler,
                                          Handlers.Textbox.value: TextboxDrawingHandler,
                                          Handlers.Rect.value: RectDrawingHandler,
                                          Handlers.Ellipse.value: EllipseDrawingHandler,
                                          Handlers.Fill.value: FillPaintHandler,
                                          }


    def mousePressEvent(self, event: QMouseEvent):
        if self.handler and self.scene_view and self.pen:
            if isinstance(self.handler, DrawingHandler):
                self.handler.mousePress(self.scene_view, event, self.pen)
            else:
                self.handler.mousePress(self.scene_view, event, self.brush)

    def mouseMoveEvent(self, event: QMouseEvent):
        if (isinstance(self.handler, DrawingHandler)
            and self.scene_view
            and self.pen):
            self.handler.mouseMove(self.scene_view, event, self.pen)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if (isinstance(self.handler, DrawingHandler)
            and self.scene_view is not None
            and self.pen):
            self.handler.mouseRelease(self.scene_view, event, self.pen)

    def setSceneView(self, scene_view: QGraphicsView) -> None:
        self.scene_view = scene_view

    def setPenWidth(self, size: int) -> None:
        self.pen.setWidth(size)

    def setPenColor(self, color: QColor):
        self.pen.setColor(color)

    def setShortcutManager(self, shortcut_manager: ShortcutManager):
        self.shortcut_manager = shortcut_manager

    def setFill(self, color: QColor):
        self.brush.setColor(color)

    def setHandler(self, handler: DrawingHandler | FillPaintHandler):
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
        if issubclass(class_obj, FillPaintHandler):
            handler_inst = class_obj()
        else:
            handler_inst = class_obj(self.handler_signal)
        self.setHandler(handler_inst)
