from __future__ import annotations
from typing import OrderedDict
from PyQt6.QtGui import QPen, QPainterPath, QTransform
from PyQt6.QtCore import QPointF, Qt, pyqtBoundSignal, QRectF
from PyQt6.QtWidgets import QGraphicsItem
from ..drawing.transformation_handlers import RotationHandler, TransformationHandler, ScaleHandler
from ..utils import Handlers
from .wrappers import DeepCopyableGraphicsItem, DeepCopyableTextbox
from collections import OrderedDict
from copy import deepcopy

class SelectableRectItem(QGraphicsItem):
    """ Selectable container for QGraphicsItems """

    selectableItems: OrderedDict = OrderedDict()
    selectEnabled = True
    last_signal: str = ""
    selector_name: str | None = None

    def __init__(self, item : DeepCopyableGraphicsItem, select_signal: pyqtBoundSignal | None = None):
        super().__init__()
        self._pen = QPen(Qt.GlobalColor.darkBlue, 2, Qt.PenStyle.DashLine)
        self._item = None

        self.item = item
        self._id = id(self)
        self._transform = QTransform()
        self.setAcceptHoverEvents(True)
        self.select_signal = select_signal
        if select_signal:
            select_signal.connect(self._toggle_active)
        self.selectableItems[self._id] = self

    def scene_order(self):
        for index, key in enumerate(self.selectableItems.keys()):
            if key == self._id:
                return index
        return 0

    def bring_to_front(self):
        self.selectableItems.move_to_end(self._id, last=True)

    @property
    def item(self) -> DeepCopyableGraphicsItem:
        if not self._item:
            raise TypeError("I dont think this is even possible...")
        return self._item

    @item.setter
    def item(self, item: DeepCopyableGraphicsItem):
        self._item = item
        self._item.setParentItem(self)
        self.transformation_handlers: list[TransformationHandler] = self._register_transformation_handlers()
        if hasattr(item, 'to_svg'):
            self.__setattr__('to_svg', getattr(item, 'to_svg'))

    def transform(self):
        return self._transform

    def _register_transformation_handlers(self) -> list[TransformationHandler]:
        rotation_handler = RotationHandler(self.rotatingRectIcon, self)
        stretch_handler_top_right = ScaleHandler(self.topRightStretchIcon, self, self.item.boundingRect)
        stretch_handler_top_left = ScaleHandler(self.topLeftStretchIcon, self, self.item.boundingRect)
        stretch_handler_bottom_right = ScaleHandler(self.bottomRightStretchIcon, self, self.item.boundingRect)
        stretch_handler_bottom_left = ScaleHandler(self.bottomLeftStretchIcon, self, self.item.boundingRect)
        return [rotation_handler, stretch_handler_top_left, stretch_handler_top_right,
                stretch_handler_bottom_right, stretch_handler_bottom_left,
                ]

    def setFlag(self, *args):
        if isinstance(self.item, DeepCopyableTextbox):
            self.item.setFlag(*args)
        super().setFlag(*args)


    def sceneTransform(self):
        return self.item.sceneTransform()

    def add_handler(self, handler: TransformationHandler) -> None:
        self.transformation_handlers.append(handler)

    @classmethod
    def _toggle_active(cls, name: str) -> None:
        cls.last_signal = name
        if not cls.selectEnabled:
            return
        for item in cls.selectableItems.values():
            if name == Handlers.Selector.value:
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
                cls.selector_name = name
            elif name == Handlers.Fill.value:
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                cls.selector_name = name
            else:
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                cls.selector_name = None

    def setTransform(self, matrix: QTransform, combine=False) -> None:
        if round(matrix.determinant(), 3) != 1:
            self.item.setTransform(matrix, combine=combine)
        else:
            QGraphicsItem.setTransform(self, matrix, combine=combine)
        self._transform = matrix * self._transform
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

    def mouseMoveEvent(self, event) -> None:
        self.prepareGeometryChange()
        self.update()
        if self.selector_name == Handlers.Fill.value:
            return
        for handler in self.transformation_handlers:
            handler.handle_mouse_move(event)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if self.selector_name == Handlers.Fill.value:
            return
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

        self.setZValue(self.scene_order())
        if self.isSelected():
            painter.setPen(self._pen)
            painter.drawRect(self.itemBoundingRect())
            if self.selector_name != Handlers.Selector.value:
                return

            for handler in self.transformation_handlers:
                painter.drawRect(handler.rect) # Make this dynamic... handler should implement paint?

    def setBrush(self, *args):
        method = getattr(self.item, "setBrush", None)
        if callable(method):
            method(*args)

    def setPen(self, *args):
        method = getattr(self.item, "setPen", None)
        if callable(method):
            method(*args)

    def setSelected(self, selected):
        if selected:
            self.bring_to_front()
        super().setSelected(selected)

    def hoverEnterEvent(self, event) -> None:
        if not any([item.isSelected() for item in self.selectableItems.values()]):
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

    @classmethod
    def cycle(cls, cursor_pos: QPointF):
        """ Cycle's the z-values of all QSelectableItems under cursor
        cursor_pos: Scene curosr position """
        items_under_cursor = list(filter(lambda item: item.boundingRect().contains(cursor_pos), cls.selectableItems.values()))
        # Disable selection and hover behaviour while cycling through the items
        for item in items_under_cursor:
            item.setSelected(False)
            item.setAcceptHoverEvents(False)

        values = list(sorted([item.zValue() for item in items_under_cursor]))
        for item in items_under_cursor:
            old_index = values.index(item.zValue())
            new_index = (old_index + 1) % len(values)
            item.setZValue(values[new_index])
            if values[new_index] == values[-1]:
                item.setSelected(True)
        # Enable selection behaviour. The item with the greatest z value will become selected by default
        for item in items_under_cursor:
            item.setAcceptHoverEvents(True)

    @classmethod
    def toggleEnabled(cls):
        """ Used to toggle the class selection behaviour """
        cls.selectEnabled = not cls.selectEnabled
        if cls.selectEnabled:
            cls._toggle_active(cls.last_signal)
        else:
            # Disable selection behaviour
            for item in cls.selectableItems.values():
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def __deepcopy__(self, memo) -> SelectableRectItem:
        copy_item = SelectableRectItem(deepcopy(self.item), select_signal=self.select_signal)
        SelectableRectItem._toggle_active(SelectableRectItem.last_signal)
        return copy_item

    def __del__(self):
        del self.selectableItems[self._id]
