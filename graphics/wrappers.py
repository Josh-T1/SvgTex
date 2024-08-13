from __future__ import annotations
from pathlib import Path
from PyQt6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPainterPath, QPen, QKeyEvent, QTextCursor, QTransform
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QLineF, QPointF, QSize, Qt, QRectF
from PyQt6.QtSvg import QSvgGenerator, QSvgRenderer
from PyQt6.QtSvgWidgets import QGraphicsSvgItem
from PyQt6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItemGroup, QGraphicsLineItem, QGraphicsPathItem, QGraphicsSceneMouseEvent, QGraphicsTextItem,QGraphicsItem, QGraphicsRectItem)
from ..utils import KeyCodes
from abc import ABC, abstractmethod
import re
from ..utils import transform_path


def color_to_rgb(color: QColor):
    """ Converts QColor object to string representation following valid svg formatting """
    return f'rgb({color.red()}, {color.green()}, {color.blue()})'

class DeepCopyableGraphicsItem(QGraphicsItem):
    """ Wrapper for QGraphicsItem that supports deepcopy """

    @abstractmethod
    def __deepcopy__(self, memo) -> DeepCopyableGraphicsItem:
        pass

    @abstractmethod
    def to_svg(self) -> str:
        """ Converts DeepCopyableGraphicsItem to svg code """
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

    @classmethod
    def transform_to_svg(cls, transform: QTransform | None) -> str:
        if transform is None: return ''
        m11, m12, m21, m22 = transform.m11(), transform.m12(), transform.m21(), transform.m22()
        dx, dy = transform.dx(), transform.dy()
        return f'matrix({m11} {m12} {m21} {m22} {dx} {dy})'

class StoringQSvgRenderer(QSvgRenderer):
    """ Wrapper for QSvgRenderer that stores data used to create renderer """
    def __init__(self, contents: QByteArray, parent = None):
        super().__init__(contents, parent=parent)
        self.svg_contents = contents.data().decode('utf-8')

class DeepCopyableSvgItem(QGraphicsSvgItem, DeepCopyableGraphicsItem):
    """ Wrapper for QGraphicsSvgItem that supports deepcopying and conversion to valid SVG code that can be included in a SVG document """

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

    def svg_body(self) -> str:
        """ Returns svg code representing the scene representation of the SvgItem, that can be directly imbeded into an SVG document """
        # alternative way. Get first path tag. Parse d attr get path. Map path from parent?
        if not self.svg_data:
            return ""

        # Transform svg item to reflect its scene position instead of relative position
        svg_doc = transform_path(self.svg_data.encode('utf-8'), self.transform())
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

    def __deepcopy__(self, memo) -> DeepCopyableSvgItem:
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
    """ Wrapper for QGraphicsEllipseItem that supports deepcopy """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_svg(self):
        pen_svg = self.pen_to_svg(self.pen())
        brush_svg = self.brush_to_svg(self.brush())
        rect = self.rect()
        transform = self.sceneTransform()
        transform_svg = self.transform_to_svg(transform)
        item_svg = f'<ellipse cx="{rect.center().x()}" cy="{rect.center().y()}" rx="{rect.width() / 2}" ry="{rect.height() / 2}" style="{pen_svg};{brush_svg}"/>'

        return (f'<g transform="{transform_svg}">\n'
                f'{item_svg}\n'
                f'</g>\n')

    def __deepcopy__(self, memo) -> DeepCopyableEllipseItem:
        if (parent := self.parentItem()):
            new_rect = parent.mapRectFromParent(self.rect())
        else:
            new_rect = self.rect()
        new_item = DeepCopyableEllipseItem(new_rect)

        new_item.setPen(self.copy_pen(self.pen()))
        new_item.setBrush(self.copy_brush(self.brush()))
        new_item.setPos(self.pos())
        new_item.setTransform(self.transform())
        new_item.setZValue(self.zValue())
        new_item.setVisible(self.isVisible())
        new_item.setOpacity(self.opacity())
        new_item.setFlags(self.flags())
        return new_item

class DeepCopyableRectItem(QGraphicsRectItem, DeepCopyableGraphicsItem):
    """ Wrapper for QGraphicsRectItem that supports deepcopy """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_svg(self):
        brush_svg = self.brush_to_svg(self.brush())
        pen_svg = self.pen_to_svg(self.pen())
        transform = self.sceneTransform()
        transform_svg = self.transform_to_svg(transform)
        item_svg = f'<rect x="{self.rect().x()}" y="{self.rect().y()}" width="{self.rect().width()}" height="{self.rect().height()}"'
        item_svg += f' style="{pen_svg};{brush_svg}"/>'

        return (f'<g transform="{transform_svg}">\n'
                f'{item_svg}\n'
                f'</g>\n')


    def __deepcopy__(self, memo) -> DeepCopyableRectItem:
        if (parent := self.parentItem()):
            new_rect = parent.mapRectFromParent(self.rect())
        else:
            new_rect = self.rect()
        new_item = DeepCopyableRectItem(new_rect)

        new_item.setPen(self.copy_pen(self.pen()))
        new_item.setBrush(self.copy_brush(self.brush()))
        new_item.setTransform(self.transform())
        new_item.setPos(self.pos())
        new_item.setZValue(self.zValue())
        new_item.setVisible(self.isVisible())
        new_item.setOpacity(self.opacity())
        new_item.setFlags(self.flags())
        return new_item

class DeepCopyableLineItem(QGraphicsLineItem, DeepCopyableGraphicsItem):
    """ Wrapper for QGraphicsLineItem that supports deepcopy """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_svg(self):
        pen_svg = self.pen_to_svg(self.pen())
        line = self.line()
        transform = self.sceneTransform()
        transform_svg = self.transform_to_svg(transform)
        item_svg = f'<polyline points="{line.x1()} {line.y1()} {line.x2()} {line.y2()}" style="{pen_svg}"/>'

        return (f'<g transform="{transform_svg}">\n'
                f'{item_svg}\n'
                f'</g>\n')

    def __deepcopy__(self, memo) -> DeepCopyableLineItem:
        if (parent := self.parentItem()):
            new_line = QLineF(parent.mapFromParent(self.line().p1()), parent.mapFromParent(self.line().p2()))
        else:
            new_line = self.line()

        new_item = DeepCopyableLineItem(new_line)
        new_item.setPen(self.copy_pen(self.pen()))
        new_item.setTransform(self.transform())
        new_item.setPos(self.pos())
        new_item.setZValue(self.zValue())
        new_item.setVisible(self.isVisible())
        new_item.setOpacity(self.opacity())
        new_item.setFlags(self.flags())
        return new_item

class DeepCopyablePathItem(QGraphicsPathItem, DeepCopyableGraphicsItem):
    """ Wrapper for QGraphicsPathItem that supports deepcopy """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _path_to_svg(self):
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        svg_gen = QSvgGenerator()
        svg_gen.setOutputDevice(buffer)
        svg_gen.setSize(QSize(int(self.boundingRect().width()), int(self.boundingRect().height())))
        svg_gen.setViewBox(self.boundingRect())

        painter = QPainter()
        painter.begin(svg_gen)
        painter.setTransform(self.transform(), True)
        painter.drawPath(self.path())

        painter.end()
        buffer.seek(0)
        byte_svg = buffer.data().data()
        svg_doc = byte_svg.decode('utf-8')

        start = svg_doc.find('d="') + 3
        end = svg_doc.find('"', start)

        if start == -1 or end == -1:
            raise ValueError("Invalid Svg format: no <svg> tags found")
        return svg_doc[start:end]

    def to_svg(self) -> str:
        pen_svg = self.pen_to_svg(self.pen())
        brush_svg = self.brush_to_svg(self.brush())
        path_svg = self._path_to_svg()
        path_element_svg = f'<path style="{pen_svg};{brush_svg}" d="{path_svg}"/>'
        transform = self.sceneTransform()
        transform_svg = self.transform_to_svg(transform)
        return (f'<g transform="{transform_svg}">\n'
                f'{path_element_svg}\n'
                f'</g>\n')

    def __deepcopy__(self, memo) -> DeepCopyablePathItem:
        if (parent := self.parentItem()):
            new_path = parent.mapFromParent(self.path())
        else:
            new_path = self.path()
        new_item = DeepCopyablePathItem(new_path)
        new_item.setTransform(self.transform())
        new_item.setPen(self.pen())
        new_item.setBrush(self.brush())
        new_item.setOpacity(self.opacity())
        new_item.setZValue(self.zValue())
        new_item.setVisible(self.isVisible())
        new_item.setFlags(self.flags())
        return new_item

class ClippedTextItem(QGraphicsTextItem):
    """ Wrapper for QGraphicsTextItem that supports a 'clipped rect', where text outside of the rect bounds will not be displayed """
    def __init__(self, text: str, clip_rect: QRectF, parent=None):
        super().__init__(text, parent)
        print(text, "clip text")
        self.text = text
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditable | Qt.TextInteractionFlag.TextSelectableByMouse
                                     | Qt.TextInteractionFlag.TextEditorInteraction)
        self.setDefaultTextColor(QColor(Qt.GlobalColor.black))
        self.clipRect = clip_rect
        self.update()

    def setClipRect(self, rect: QRectF):
        self.clipRect = self.mapRectFromParent(rect)

    def paint(self, painter, option, widget=None):
        if painter is None: return
        if self.toPlainText().isspace():
            self.setPlainText(self.text)
        painter.setClipRect(self.clipRect)
        super().paint(painter, option, widget)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent | None):
        if event is None: return
        if event.button() == Qt.MouseButton.LeftButton and self.toPlainText() == self.text:
            self.setPlainText("")

class DeepCopyableTextbox(QGraphicsRectItem, DeepCopyableGraphicsItem):
    # TODO: Allow for no clip rect
    default_message = "Text.."

    def __init__(self, rect: QRectF, text=None, parent=None):
        super().__init__(rect, parent=parent)
        self.moving = False # move this logic into the tools module
        _text = text if text is not None else self.default_message
        self.text_item: ClippedTextItem = ClippedTextItem(_text, self.rect(), parent=self)
        self.moving_pen = QPen(Qt.GlobalColor.darkYellow)
        self.stationary_pen = QPen(Qt.GlobalColor.transparent)
        self.text_item.setTextWidth(rect.width())
        self.text_item.setPos(self.rect().topLeft())
        # This is a temporary fix. When the item is copied and then added to scene the text does not appear. It seems that super().setRect(*args) in setRect() needs to be called for text to display...
        self.setRect(self.rect())


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

    def text(self) -> str:
        """ Returns textbox content as plain text """
        return self.text_item.toPlainText()

    def to_svg(self) -> str:
        font_item = self.text_item.font()
        rect = self.rect()
        transform = self.sceneTransform()
        transform_svg = self.transform_to_svg(transform)
        item_svg = f'<text x="{rect.x()}" y="{rect.y()}" font-family="{font_item.family()}" font-size="{font_item.pointSize()}"'
        item_svg += f' data-custom-params="{self.rect().width()} {self.rect().height()}">\n'
        item_svg += f"{self.text()}\n"
        item_svg += f'</text>'

        return (f'<g transform="{transform_svg}">\n'
                f'{item_svg}\n'
                f'</g>\n')

    def __deepcopy__(self, memo) -> DeepCopyableTextbox:
        rect_copy = QRectF(self.rect().x(), self.rect().y(), self.rect().width(), self.rect().height())
        new_item = DeepCopyableTextbox(rect_copy)
        return new_item


class DeepCopyableItemGroup(QGraphicsItemGroup, DeepCopyableGraphicsItem):
    """ Wrapper for QGraphicsItemGroup that supports deepcopy """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


#    def __deepcopy__(self) -> DeepCopyableItemGroup:
#        scene = self.scene()
#        group = DeepCopyableItemGroup()
#        scene.addItem(group)
#        for item in self.childItems():
#            item_copy = deepcopy(item)
#            group.addToGroup(item_copy)

    def to_svg(self):
        transform = self.sceneTransform()
        transform_svg = self.transform_to_svg(transform)
        item_svg = ""
        for item in self.childItems():
            print(item, "child item group")
            if hasattr(item, "to_svg"):
                to_svg = getattr(item, "to_svg")
                item_svg += to_svg() + '\n'

        return (f'<g transform="{transform_svg}">\n'
                f'{item_svg}\n'
                f'</g>\n'
                )



