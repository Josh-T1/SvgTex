from pathlib import Path, PureWindowsPath
from typing import Any, OrderedDict
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QPen, QPainterPath, QKeyEvent, QTextCursor
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QSize, Qt, pyqtBoundSignal, QRectF, QSizeF, QRect
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtSvgWidgets import QGraphicsSvgItem
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem,QGraphicsItem, QGraphicsRectItem, QVBoxLayout, QWidget)

from ..drawing.transformations import RotationHandler, TransformationHandler, ScaleHandler, TestHandler
from ..utils import KeyCodes, Handlers
from collections import OrderedDict
from copy import deepcopy
from abc import ABC, abstractmethod
import re
from lxml import etree

def translate_path(svg_document: bytes, x_shift: float, y_shift: float) -> str:
    """
    TODO: This should be possible using the builtin xml.etree instead of lxml.etree
    """
    svg_namespace = {'svg': 'http://www.w3.org/2000/svg'}
    root = etree.fromstring(svg_document)

    for g in root.findall('.//svg:g', namespaces=svg_namespace):
        paths = g.xpath('.//svg:path', namespaces=svg_namespace)
        if len(paths) != 0:

            g_transform_attrib = g.attrib.get("transform")
            if g_transform_attrib:
                transform_pattern = r'\b[a-zA-Z_]\w*\s*\([^)]*\)' # TODO determine limitation of this regex pattern

                matches = re.findall(transform_pattern, g_transform_attrib)
                new_transform = ""
                for match in matches:
                    if match.startswith("translate"):
                        translate_pattern = r'translate\((-?\d+(\.\d+)?) \s*(-?\d+(\.\d+)?)\)'
                        translate_match = re.match(translate_pattern, g_transform_attrib)
                        if not translate_match: # This should be impossible
                            continue

                        x_translate = float(translate_match.group(1)) + x_shift
                        y_translate = float(translate_match.group(2)) + y_shift
                        new_translate = f"translate({x_translate} {y_translate})"
                        new_transform += new_translate
                    else:
                        new_transform += match

                g.set("transform", new_transform)

    tree = etree.ElementTree(root)
    return etree.tostring(tree).decode('utf-8')

def color_to_rgb(color: QColor):
    return f'rgb({color.red()}, {color.green()}, {color.blue()})'

class DeepCopyableGraphicsItem(QGraphicsItem):
    @abstractmethod
    def __deepcopy__(self, memo) -> Any:
        pass

    def copy_pen(self, pen: QPen):
        new_pen = QPen()
        new_pen.setColor(pen.color())
        new_pen.setWidth(pen.width())
        new_pen.setStyle(pen.style())
        new_pen.setCapStyle(pen.capStyle())
        new_pen.setJoinStyle(pen.joinStyle())
        new_pen.setDashPattern(pen.dashPattern())
        new_pen.setDashOffset(pen.dashOffset())
        new_pen.setMiterLimit(pen.miterLimit())
        new_pen.setBrush(pen.brush())
        new_pen.setCosmetic(pen.isCosmetic())
        return new_pen

    def pen_to_svg(self, pen: QPen):
        color = pen.color()
        color_str = color_to_rgb(color)
        width = pen.widthF()
        style = pen.style()

        if style == Qt.PenStyle.DashLine:
            dasharray = '5, 5'
        elif style == Qt.PenStyle.DotLine:
            dasharray = '1, 5'
        elif style == Qt.PenStyle.DashDotLine:
            dasharray = '5, 5, 1, 5'
        elif style == Qt.PenStyle.DashDotDotLine:
            dasharray = '5, 5, 1, 5, 1, 5'
        else:
            dasharray = "none"
        return f'stroke:{color_str};stroke-width:{width};stroke-dasharray:{dasharray}'

    def brush_to_svg(self, brush: QBrush):
        brush_style = brush.style()
        color = brush.color()

        if brush_style == Qt.BrushStyle.SolidPattern:
            svg = f'fill:rgb({color.red()}, {color.green()}, {color.blue()});fill-opacity:{color.alpha() / 255.0}'
        elif brush_style == Qt.BrushStyle.Dense1Pattern:
            svg = f'fill:url(#dense1Pattern)'
        elif brush_style == Qt.BrushStyle.Dense2Pattern:
            svg = f'fill:url(#dense2Pattern)'
        elif brush_style == Qt.BrushStyle.Dense3Pattern:
            svg = f'fill:url(#dense3Pattern)'
        elif brush_style == Qt.BrushStyle.Dense4Pattern:
            svg = f'fill:url(#dense4Pattern)'
        elif brush_style == Qt.BrushStyle.Dense5Pattern:
            svg = f'fill:url(#dense5Pattern)'
        elif brush_style == Qt.BrushStyle.Dense6Pattern:
            svg = f'fill:url(#dense6Pattern)'
        elif brush_style == Qt.BrushStyle.Dense7Pattern:
            svg = f'fill:url(#dense7Pattern)'
        elif brush_style == Qt.BrushStyle.HorPattern:
            svg = 'fill:url(#horPattern)'
        elif brush_style == Qt.BrushStyle.VerPattern:
            svg = 'fill:url(#verPattern)'
        elif brush_style == Qt.BrushStyle.CrossPattern:
            svg = 'fill:url(#crossPattern)'
        elif brush_style == Qt.BrushStyle.BDiagPattern:
            svg = 'fill:url(#bDiagPattern)'
        elif brush_style == Qt.BrushStyle.FDiagPattern:
            svg = 'fill:url(#fDiagPattern)'
        elif brush_style == Qt.BrushStyle.DiagCrossPattern:
            svg = 'fill:url(#diagCrossPattern)'
        elif brush_style == Qt.BrushStyle.LinearGradientPattern:
            # Additional code needed to handle gradients
            svg = 'fill:url(#linearGradient)'  # Define gradient in <defs>
        elif brush_style == Qt.BrushStyle.RadialGradientPattern:
            # Additional code needed to handle gradients
            svg = 'fill:url(#radialGradient)'  # Define gradient in <defs>
        elif brush_style == Qt.BrushStyle.ConicalGradientPattern:
            # Additional code needed to handle gradients
            svg = 'fill:url(#conicalGradient)'  # Define gradient in <defs>
        elif brush_style == Qt.BrushStyle.TexturePattern: # TODO Implement at some point?
            svg = 'fill:none'
#            texture = brush.texture()
#            byte_array = QByteArray()
#            buffer = QBuffer(byte_array)
#            buffer.open(QIODevice.WriteOnly)
#            texture.save(buffer, 'PNG')
#            base64_data = b64encode(byte_array.data()).decode('utf-8')
#            svg = (f'fill:url(#texturePattern);" '
#                f'<defs>'
#                f'<pattern id="texturePattern" patternUnits="userSpaceOnUse" width="{texture.width()}" height="{texture.height()}">'
#                f'<image xlink:href="data:image/png;base64,{base64_data}" x="0" y="0" width="{texture.width()}" height="{texture.height()}" />'
#                f'</pattern>'
#                f'</defs>')Pattern:
#            svg =''
        else:
            svg = 'fill:none'
        return svg

    def copy_brush(self, brush: QBrush):
        new_brush = QBrush()
        new_brush.setColor(brush.color())
        new_brush.setStyle(brush.style())

        if brush.style() == Qt.BrushStyle.SolidPattern:
            # No additional properties for solid brushes
            pass
        elif brush.style() == Qt.BrushStyle.TexturePattern:
            new_brush.setTexture(brush.texture())
        # Add other brush styles if needed
        return new_brush

    def transform_to_svg(self, transform):
        if transform:
            return f'matrix({transform.m11()}, {transform.m12()}, {transform.m21()}, {transform.m22()}, {transform.dx()}, {transform.dy()})'
        else:
            return ''

class StoringQSvgRenderer(QSvgRenderer):
    def __init__(self, contents: QByteArray, parent = None):
        super().__init__(contents, parent=parent)
        self.svg_contents = contents.data().decode('utf-8')


class DeepCopyableSvgItem(QGraphicsSvgItem, DeepCopyableGraphicsItem):
    def __init__(self, data: None | StoringQSvgRenderer | str = None, parent=None):
        self.svg_data = None

        if isinstance(data, str):
            if not Path(data).is_file(): raise ValueError(f"Invalid path: {data}")
            super().__init__(data)
            self.svg_data = self._read_svg_file(data)

        elif isinstance(data, StoringQSvgRenderer):
            super().__init__()
            self.setSharedRenderer(data)
        else:
            super().__init__()

    # make property
    def svg_body(self):
        if not self.svg_data:
            return ""
        # Translate svg item to reflect its scene position instead of relative position
        svg_doc = translate_path(self.svg_data.encode('utf-8'), self.transform().dx(), self.transform().dy())
        start = svg_doc.find("<svg")
        end = svg_doc.rfind("</svg>")

        if start == -1 or end == -1:
            raise ValueError("Invalid Svg format: no <svg> tags found")
        # remove svg tags
        body = re.sub(r'<svg\s+([^>]*)/?>', '', svg_doc[start:end])
        body = body.replace("</svg>", "")
        return body

    def setSharedRenderer(self, renderer: StoringQSvgRenderer): # type: ignore
        super().setSharedRenderer(renderer)
        self.svg_data = renderer.svg_contents

    def _read_svg_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def __deepcopy__(self, memo) -> Any:
        if not self.svg_data:
            return DeepCopyableSvgItem()
        data = QByteArray(self.svg_data.encode('utf-8'))
        renderer = StoringQSvgRenderer(data)
        svg_item = DeepCopyableSvgItem(renderer)
        svg_item.setTransform(self.transform())
        return svg_item

    def to_svg(self):
        return self.svg_body()

class DeepCopyableEllipseItem(QGraphicsEllipseItem, DeepCopyableGraphicsItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __deepcopy__(self, memo):
        new_item = DeepCopyableEllipseItem(self.rect(), self.parentItem())
        new_item.setPen(self.copy_pen(self.pen()))
        new_item.setBrush(self.copy_brush(self.brush()))
        new_item.setTransform(deepcopy(self.transform(), memo))
        new_item.setPos(deepcopy(self.pos(), memo))
        new_item.setRotation(self.rotation())
        new_item.setScale(self.scale())
        new_item.setZValue(self.zValue())
        new_item.setVisible(self.isVisible())
        new_item.setOpacity(self.opacity())
        new_item.setFlags(self.flags())
        return new_item

    def to_svg(self):
        pen_svg = self.pen_to_svg(self.pen())
        brush_svg = self.brush_to_svg(self.brush())
        transform_svg = self.transform_to_svg(self.transform())
        item_svg = f'<ellipse cx="{self.rect().center().x()}" cy="{self.rect().center().y()}" rx="{self.rect().width() / 2}" ry="{self.rect().height() / 2}" style="{pen_svg};{brush_svg}"'
        item_svg += f' data-custom-type="DeepCopyableEllipseItem"/>'
        for child in self.childItems():
            if hasattr(child, "to_svg"):
                child_to_svg = getattr(child, 'to_svg')
                item_svg += "   " + child_to_svg()

        return (f'<g transform="{transform_svg}">\n'
                f'{item_svg}\n'
                f'</g>\n')

class DeepCopyableRectItem(QGraphicsRectItem, DeepCopyableGraphicsItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_svg(self):
        brush_svg = self.brush_to_svg(self.brush())
        pen_svg = self.pen_to_svg(self.pen())
        transform_svg = self.transform_to_svg(self.transform())
        item_svg = f'<rect x="{self.rect().x()}" y="{self.rect().y()}" width="{self.rect().width()}" height="{self.rect().height()}"'
        item_svg += f' style="{pen_svg};{brush_svg}"'
        item_svg += f' data-custom-type="DeepCopyableRectItem"/>'

        for child in self.childItems():
            if hasattr(child, "to_svg"):
                child_to_svg = getattr(child, 'to_svg')
                item_svg += "   " + child_to_svg()

        return (f'<g transform="{transform_svg}">\n'
                f'{item_svg}\n'
                f'</g>\n')

    def __deepcopy__(self, memo):
        new_item = DeepCopyableRectItem(self.rect(), self.parentItem())

        new_item.setPen(self.copy_pen(self.pen()))
        new_item.setBrush(self.copy_brush(self.brush()))
        new_item.setTransform(deepcopy(self.transform(), memo))
        new_item.setPos(deepcopy(self.pos(), memo))
        new_item.setRotation(self.rotation())
        new_item.setScale(self.scale())
        new_item.setZValue(self.zValue())
        new_item.setVisible(self.isVisible())
        new_item.setOpacity(self.opacity())
        new_item.setFlags(self.flags())
        return new_item

class DeepCopyableLineItem(QGraphicsLineItem, DeepCopyableGraphicsItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __deepcopy__(self, memo):
        new_item = DeepCopyableLineItem(self.line(), self.parentItem())
        new_item.setPen(self.copy_pen(self.pen()))
        new_item.setTransform(deepcopy(self.transform(), memo))
        new_item.setPos(deepcopy(self.pos(), memo))
        new_item.setRotation(self.rotation())
        new_item.setScale(self.scale())
        new_item.setZValue(self.zValue())
        new_item.setVisible(self.isVisible())
        new_item.setOpacity(self.opacity())
        new_item.setFlags(self.flags())
        return new_item

    def to_svg(self):
        pen_svg = self.pen_to_svg(self.pen())
        transform_svg = self.transform_to_svg(self.transform())
        item_svg = f'<polyline points="{self.line().x1()} {self.line().y1()} {self.line().x2()} {self.line().y2()} " style="{pen_svg}"'
        item_svg += ' data-custom-type="DeepCopyableLineItem"/>'

        for child in self.childItems():
            if hasattr(child, "to_svg"):
                child_to_svg = getattr(child, 'to_svg')
                item_svg += "   " + child_to_svg()

        return (f'<g transform="{transform_svg}">\n'
                f'{item_svg}\n'
                f'</g>\n')

class SelectableRectItem(QGraphicsItem):
    """ Selectable container for QGraphicsItems's """

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

    def setFlag(self, *args):
        if isinstance(self.item, Textbox):
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

    def __deepcopy__(self, memo):
        copy_item = SelectableRectItem(deepcopy(self.item), select_signal=self.select_signal)
        SelectableRectItem._toggle_active(SelectableRectItem.last_signal)
        return copy_item

    def __del__(self):
        del self.selectableItems[self._id]


class ClippedTextItem(QGraphicsTextItem):
    def __init__(self, text: str, clip_rect, parent=None):
        super().__init__(text, parent)
        self.text = text
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditable | Qt.TextInteractionFlag.TextSelectableByMouse
                                     | Qt.TextInteractionFlag.TextEditorInteraction)
        self.setDefaultTextColor(QColor(Qt.GlobalColor.black))
        self.clipRect = clip_rect
        self.update()

    def setClipRect(self, rect: QRectF):
        self.clipRect = self.mapRectFromParent(rect)
        print(self.clipRect)

    def paint(self, painter, option, widget=None):
        painter.setClipRect(self.clipRect)
        super().paint(painter, option, widget)



class Textbox(QGraphicsRectItem, DeepCopyableGraphicsItem):
    default_message = "Text..."

    def __init__(self, rect: QRectF, parent=None):
        super().__init__(rect, parent=parent)
        self.moving = False # move this logic into the tools module
        self.text_item: ClippedTextItem = ClippedTextItem(self.default_message, self.rect(), parent=self)
        self.moving_pen = QPen(Qt.GlobalColor.darkYellow)
        self.stationary_pen = QPen(Qt.GlobalColor.transparent)

#        self.text_item.setFont(QFont("Times", 12))
        self.text_item.setTextWidth(rect.width())
        self.text_item.setPos(self.rect().topLeft())

    def mousePressEvent(self, event):
        if self.text_item.clipRect.contains(event.scenePos()) and self.text() == self.default_message:
            pass

    def setRect(self, *args, **kwargs):
        super().setRect(*args, **kwargs)
        self.text_item.setTextWidth(self.rect().width())
        self.text_item.setClipRect(self.rect())
        self.text_item.setPos(self.rect().topLeft())
        self.text_item.update()

    def paint(self, painter, option, widget=None):
        if not painter:
            return
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

    def __deepcopy__(self, memo) -> Any:
        rect_copy = QRectF(self.rect().x(), self.rect().y(), self.rect().width(), self.rect().height())
        new_item = Textbox(rect_copy)
        # This is a temporary fix. When the item is copied and then added to scene the text does not appear. It seems that super().setRect(*args) in setRect() needs to be called for text to display...
        new_item.setRect(rect_copy)
        return new_item

    def to_svg(self):
        font_item = self.text_item.font()
        transform_svg = self.transform_to_svg(self.transform())
        item_svg = f'<text x="{self.rect().x()}" y="{self.rect().y()}" font-family="{font_item.family()}" font-size="{font_item.pointSize()}" fill="{color_to_rgb(self.text_item.defaultTextColor())}"'
        item_svg += f' data-custom-type="DeepCopyableRectItem"'
        item_svg += f' data-custom-params="({self.rect().width()}, {self.rect().height()}, {self.text()})">\n'
#        item_svg += f' style="{pen_svg};{brush_svg}"'
        item_svg += f"   {self.text()}\n"
        item_svg += f'</text>'



        for child in self.childItems():
            if hasattr(child, "to_svg"):
                child_to_svg = getattr(child, 'to_svg')
                item_svg += "   " + child_to_svg()

        return (f'<g transform="{transform_svg}">\n'
                f'{item_svg}\n'
                f'</g>\n')
