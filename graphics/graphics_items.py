from PyQt6.QtGui import QColor, QFont, QIcon, QPen, QPainterPath, QKeyEvent, QTextCursor
from PyQt6.QtCore import QPointF, QSize, Qt, pyqtBoundSignal, QRectF
from PyQt6.QtWidgets import (QCheckBox, QGraphicsTextItem,QGraphicsItem, QGraphicsRectItem, QVBoxLayout, QWidget)

from ..drawing.transformations import RotationHandler, TransformationHandler, ScaleHandler, TestHandler
from ..utils import KeyCodes, Handlers

class PngCheckBox(QWidget):
    def __init__(self, path: str):
        super().__init__()
        self._layout = QVBoxLayout()
        self.path = path
        self.initUi()
        self.setLayout(self._layout)

    def initUi(self):
        self._create_widgets()
        self.checkbox.setIconSize(QSize(30, 30))

    def _create_widgets(self):
        self.checkbox = QCheckBox()
        custom_icon = QIcon(self.path)
        self.checkbox.setIcon(custom_icon)




class SelectableRectItem(QGraphicsItem):
    def __init__(self, item : QGraphicsItem, select_signal: pyqtBoundSignal | None = None):
        super().__init__()
        self._pen = QPen(Qt.GlobalColor.darkBlue, 2, Qt.PenStyle.DashLine)
        self._item = None
        self.item = item

        self.setAcceptHoverEvents(True)
        if select_signal:
            select_signal.connect(self._toggle_active)
#
    @property
    def item(self) -> QGraphicsItem:
        if not self._item:
            raise TypeError("I dont think this is even possible...")
        return self._item

    @item.setter
    def item(self, item: QGraphicsItem):
        self._item = item
        self._item.setParentItem(self)
#        self.setTransformOriginPoint(self.item.boundingRect().center())
        self.transformation_handlers: list[TransformationHandler] = self._register_transformation_handlers()

    def transform(self):
        return self.item.transform()

    def _register_transformation_handlers(self) -> list[TransformationHandler]:
        rotation_handler = RotationHandler(self.rotatingRectIcon, self)
        stretch_handler_top_right = ScaleHandler(self.topRightStretchIcon, self, self.item.boundingRect)
        stretch_handler_top_left = ScaleHandler(self.topLeftStretchIcon, self, self.item.boundingRect)
        stretch_handler_bottom_right = ScaleHandler(self.bottomRightStretchIcon, self, self.item.boundingRect)
        stretch_handler_bottom_left = ScaleHandler(self.bottomLeftStretchIcon, self, self.item.boundingRect)
        return [rotation_handler, stretch_handler_top_left, stretch_handler_top_right,
                stretch_handler_bottom_right, stretch_handler_bottom_left,
                ]

    def sceneTransform(self):
        return self.item.sceneTransform()

    def add_handler(self, handler: TransformationHandler) -> None:
        self.transformation_handlers.append(handler)

    def _toggle_active(self, name: str) -> None:
        print(name)
        if name == Handlers.Selector.value:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        elif name == Handlers.Fill.value:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        else:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def setTransform(self, matrix, combine=False) -> None:
        if round(matrix.determinant(), 3) != 1:
            self.item.setTransform(matrix, combine=combine)
        else:
            QGraphicsItem.setTransform(self, matrix, combine=combine)
        self.prepareGeometryChange()
        self.update()

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
        return self.item.boundingRect().topLeft()
#        return self.mapFromScene(self.itemBoundingRect().center())
#        return self.boundingRect().topLeft()
#        return self.mapFromScene(self.itemBoundingRect().topLeft())

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

    def setBrush(self, *args):
        method = getattr(self.item, "setBrush", None)
        if callable(method):
            method(*args)

    def hoverEnterEvent(self, event) -> None:
        self.setSelected(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.setSelected(False)
        super().hoverLeaveEvent(event)

    def boundingRect(self):
        path = QPainterPath()
        path.addRect(self.itemBoundingRect())
        for handler in self.transformation_handlers:
            path.addRect(handler.rect)
        return path.boundingRect()


    def testIcon(self):
        handle_size = 14
        item_boundingRect = self.itemBoundingRect()
        center = QPointF(item_boundingRect.center().x(), item_boundingRect.topLeft().y())
        return QRectF(center.x() - handle_size / 2, center.y() - handle_size / 2, handle_size, handle_size)

    def rotatingRectIcon(self):
        handle_size = 14 # TODO: make this more dynamic
        item_boundingRect = self.itemBoundingRect()
        center_right = QPointF(item_boundingRect.right(), item_boundingRect.center().y())
        return QRectF(center_right.x() - handle_size / 2, center_right.y() - handle_size / 2, handle_size, handle_size )

    def topRightStretchIcon(self):
        handle_size = 14
        item_boundingRect = self.itemBoundingRect()
        top_right = QPointF(item_boundingRect.right(), item_boundingRect.top())
        return QRectF(top_right.x() - handle_size / 2, top_right.y() - handle_size / 2, handle_size, handle_size)

    def topLeftStretchIcon(self):
        handle_size = 14
        item_boundingRect = self.itemBoundingRect()
        top_left = QPointF(item_boundingRect.left(), item_boundingRect.top())
        return QRectF(top_left.x() - handle_size / 2, top_left.y() - handle_size / 2, handle_size, handle_size)

    def bottomRightStretchIcon(self):
        handle_size = 14
        item_boundingRect = self.itemBoundingRect()
        bottom_right = QPointF(item_boundingRect.right(), item_boundingRect.bottom())
        return QRectF(bottom_right.x() - handle_size / 2, bottom_right.y() - handle_size / 2, handle_size, handle_size)

    def bottomLeftStretchIcon(self):
        handle_size = 14
        item_boundingRect = self.itemBoundingRect()
        bottom_left = QPointF(item_boundingRect.left(), item_boundingRect.bottom())
        return QRectF(bottom_left.x() - handle_size / 2, bottom_left.y() - handle_size / 2, handle_size, handle_size)

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

        self.text_item: ClippedTextItem = ClippedTextItem(self.default_message, self.rect(), parent=self)
        self.text_item.setFont(QFont("Times", 12))
        self.text_item.setTextWidth(rect.width())
        self.text_item.setPos(self.rect().topLeft())
        self.moving_pen = QPen(Qt.GlobalColor.darkYellow)
        self.stationary_pen = QPen(Qt.GlobalColor.transparent)

    def setRect(self, *args, **kwargs):
        super().setRect(*args, **kwargs)
        self.text_item.setTextWidth(self.rect().width())
        self.text_item.setClipRect(self.rect())
        self.text_item.setPos(self.rect().topLeft())
        self.text_item.update()

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
            cursor = self.text_item.textCursor()
            cursor.deletePreviousChar()

            event.accept()

        elif event.key() == KeyCodes.Key_Left.value:
            cursor = self.text_item.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
            self.text_item.setTextCursor(cursor)

        elif event.key() == KeyCodes.Key_Right.value:
            cursor = self.text_item.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
            self.text_item.setTextCursor(cursor)
        else:
            super().keyPressEvent(event)

    def setTransform(self, matrix, combine=False):
        if round(matrix.determinant(), 3) == 1:
            super().setTransform(matrix, combine)
        else:
            current_rect = self.rect()
            new_rect = matrix.mapRect(current_rect)
            self.setRect(new_rect)

    def text(self):
        return self.text_item.toPlainText()

