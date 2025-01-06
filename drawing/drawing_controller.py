from PyQt6.QtGui import QBrush, QColor, QKeyEvent, QKeySequence, QMouseEvent, QPen, QPainterPath, QShortcut
from PyQt6.QtCore import QObject, Qt, pyqtBoundSignal, pyqtSignal,  QRectF
from PyQt6.QtWidgets import (QGraphicsPathItem, QGraphicsView, QGraphicsScene, QGraphicsLineItem)
from ..drawing.tools import ArrowDrawingHandler, ConnectedLineHandler, EllipseDrawingHandler, BrushTool, DrawingHandler, LineDrawingHandler, ToolProtocol, PenTool, RectDrawingHandler, TextboxDrawingHandler, FreeHandDrawingHandler, NullDrawingHandler
from ..utils import Handlers, Tools

class DrawingController(QObject):
    """
    Accepts QMouseEvents and QKeyEvent. QKeyEvent's are passed to ShortcutManager object and QMouseEvents are passed to DrawingHandler.
    Class properties such as 'tool' or 'handler' are updated by connecting their respective set{Property} method to other QWidget signals. These
    properties are then used to alter the behaviour of DrawingHandler objects
    """

    handler_signal = pyqtSignal(str)
    def __init__(self, handler: DrawingHandler | ToolProtocol | None = None,
                 scene_view: QGraphicsView | None = None,
                 pen: QPen | None = None,
                 brush: QBrush | None = None
                 ):
        """
        -- Params --
        scene_view: QGraphicsScene object
        handler: responsible for implmenting drawing tool behaviour (e.g free hand tool)
        """
        super().__init__()
        self.scene_view = scene_view
        self.handler = handler if handler is not None else NullDrawingHandler(handler_signal=self.handler_signal)
        self.pen = pen if pen is not None else QPen(Qt.GlobalColor.black)
        self.brush = brush if brush is not None else QBrush(Qt.GlobalColor.black)
        self.name_to_classname_mapping = {Handlers.Line.name: LineDrawingHandler,
                                          Handlers.Freehand.name: FreeHandDrawingHandler,
                                          Handlers.Selector.name: NullDrawingHandler,
                                          Handlers.Textbox.name: TextboxDrawingHandler,
                                          Handlers.Rect.name: RectDrawingHandler,
                                          Handlers.Ellipse.name: EllipseDrawingHandler,
                                          Handlers.Arrow.name: ArrowDrawingHandler,
                                          Handlers.ConnectedLine.name: ConnectedLineHandler,
                                          Tools.Brush.name: BrushTool,
                                          Tools.Pen.name: PenTool,

                                          }


    def mousePressEvent(self, event: QMouseEvent):
        if self.handler and self.scene_view:
            if isinstance(self.handler, DrawingHandler):
                self.handler.mousePress(self.scene_view, event, self.pen)

            elif isinstance(self.handler, PenTool):
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

    def setFill(self, color: QColor):
        self.brush.setColor(color)

    def setBrushStyle(self, style: str):
        if style in Qt.BrushStyle.__members__:
            self.brush.setStyle(Qt.BrushStyle[style])

    def setPenStyle(self, style: str):
        if style in Qt.PenStyle.__members__:
            self.pen.setStyle(Qt.PenStyle[style])

    def setHandler(self, handler: DrawingHandler | ToolProtocol):
        self.handler = handler
        self.handler_signal.emit(self.handler.__class__.__name__)

    def setHandlerFromName(self, name: str) -> None:
        """
        Sets self.handler equal to the result of the mapping from param name(str) to
        class cls.__name__ or NullDrawingHandler, a DrawingHandler subclass

        -- Params --
        name: name of DrawingHandler or ToolProtocol. If name is invalid we fallback on NullDrawingHandler
        """
        class_obj = self.name_to_classname_mapping.get(name, NullDrawingHandler)
        if issubclass(class_obj, DrawingHandler):
            handler_inst = class_obj(self.handler_signal)
        else:
            handler_inst = class_obj()
        self.setHandler(handler_inst)

    def reset_handler(self):
        if self.scene_view is None or (scene := self.scene_view.scene()) is None:
            return
        reset_method = getattr(self.handler, "reset", None)
        if callable(reset_method):
            reset_method(scene)
