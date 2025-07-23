from __future__ import annotations
from pathlib import Path
from abc import ABC, abstractmethod
import re

from PyQt6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPainterPath, QPen, QKeyEvent, QTextCursor, QTransform
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QLineF, QPointF, QSize, Qt, QRectF
from PyQt6.QtSvg import QSvgGenerator, QSvgRenderer
from PyQt6.QtSvgWidgets import QGraphicsSvgItem
from PyQt6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItemGroup, QGraphicsLineItem, QGraphicsPathItem, QGraphicsSceneMouseEvent, QGraphicsTextItem,QGraphicsItem, QGraphicsRectItem)

from .patterns import (build_dense_pattern_svg, color_to_rgb, build_hor_pattern_svg, build_ver_pattern_svg,
                            build_cross_pattern_svg, build_bdiag_pattern_svg, build_fdiag_pattern_svg, build_diagcross_pattern_svg)
from ..utils import KeyCodes




class DeepCopyableItemABC(QGraphicsItem):
    """ Wrapper for QGraphicsItem that supports deepcopy """
    @abstractmethod
    def __deepcopy__(self, memo) -> DeepCopyableItemABC: ...
    @abstractmethod
    def to_svg(self, defs) -> str: ...
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
        color_str = color_to_rgb(pen.color())
        width, style = pen.widthF(), pen.style()
        if style == Qt.PenStyle.DashLine: dasharray = '5, 5'
        elif style == Qt.PenStyle.DotLine: dasharray = '1, 5'
        elif style == Qt.PenStyle.DashDotLine: dasharray = '5, 5, 1, 5'
        elif style == Qt.PenStyle.DashDotDotLine: dasharray = '5, 5, 1, 5, 1, 5'
        else: dasharray = "none"
        return f'stroke:{color_str};stroke-width:{width};stroke-dasharray:{dasharray}'

    def brush_to_svg(self, brush: QBrush, defs: dict):
        """
        --- Limitations ---
        Only a couple fill patterns supported
        """
        brush_style = brush.style()
        color = brush.color()
        r, g, b = color.red(), color.green(), color.blue()
        if brush_style == Qt.BrushStyle.SolidPattern:
            svg = f'fill:rgb({r}, {g}, {b});fill-opacity:{int(color.alpha() / 255.0)}'
        elif brush_style == Qt.BrushStyle.Dense1Pattern:
            defs_svg = build_dense_pattern_svg(color, 1)
            id = f"{r}-{g}-{b}-{color.alpha()}-dense1Pattern"
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.Dense2Pattern:
            defs_svg = build_dense_pattern_svg(color, 1)
            id = f"{r}-{g}-{b}-{color.alpha()}-dense2Pattern"
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.Dense3Pattern:
            defs_svg = build_dense_pattern_svg(color, 1)
            id = f"{r}-{g}-{b}-{color.alpha()}-dense3Pattern"
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.Dense4Pattern:
            defs_svg = build_dense_pattern_svg(color, 1)
            id = f"{r}-{g}-{b}-{color.alpha()}-dense4Pattern"
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.Dense5Pattern:
            defs_svg = build_dense_pattern_svg(color, 1)
            id = f"{r}-{g}-{b}-{color.alpha()}-dense5Pattern"
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.Dense6Pattern:
            defs_svg = build_dense_pattern_svg(color, 1)
            id = f"{r}-{g}-{b}-{color.alpha()}-dense6Pattern"
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.Dense7Pattern:
            defs_svg = build_dense_pattern_svg(color, 1)
            id = f"{r}-{g}-{b}-{color.alpha()}-dense7Pattern"
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.HorPattern:
            id = f"{r}-{g}-{b}-{color.alpha()}-horPattern"
            defs_svg = build_hor_pattern_svg(color, id)
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.VerPattern:
            id = f"{r}-{g}-{b}-{color.alpha()}-verPattern"
            defs_svg = build_ver_pattern_svg(color, id)
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.CrossPattern:
            id = f"{r}-{g}-{b}-{color.alpha()}-crossPattern"
            defs_svg = build_cross_pattern_svg(color, id)
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.BDiagPattern:
            id = f"{r}-{g}-{b}-{color.alpha()}-bDiagPattern"
            defs_svg = build_bdiag_pattern_svg(color, id)
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.FDiagPattern:
            id = f"{r}-{g}-{b}-{color.alpha()}-fDiagPattern"
            defs_svg = build_fdiag_pattern_svg(color, id)
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        elif brush_style == Qt.BrushStyle.DiagCrossPattern:
            id = f"{r}-{g}-{b}-{color.alpha()}-diagCrossPattern"
            defs_svg = build_diagcross_pattern_svg(color, id)
            defs[id] = defs_svg
            svg = f'fill:url(#{id})'
        else: svg = 'fill:none'
        return svg

    def copy_brush(self, brush: QBrush):
        """ Brush textures are not supported """
        new_brush = QBrush()
        new_brush.setColor(brush.color())
        new_brush.setStyle(brush.style())
        return new_brush

    @classmethod
    def transform_to_svg(cls, transform: QTransform | None) -> str:
        if transform is None: return ''
        m11, m12, m21, m22 = transform.m11(), transform.m12(), transform.m21(), transform.m22()
        dx, dy = transform.dx(), transform.dy()
        return f'matrix({m11} {m12} {m21} {m22} {dx} {dy})'

class DeepCopyableLineABC(DeepCopyableItemABC):
    @abstractmethod
    def setLine(self, *args) -> None: ...
    @abstractmethod
    def setPen(self, pen: QPen) -> None: ...
    @abstractmethod
    def line(self) -> QLineF: ...

class DeepCopyableShapeABC(DeepCopyableItemABC):
    @abstractmethod
    def setRect(self, rect: QRectF) -> None: ...
    @abstractmethod
    def boundingRect(self) -> QRectF: ...


class StoringQSvgRenderer(QSvgRenderer):
    """ Wrapper for QSvgRenderer that stores data used to create renderer """
    def __init__(self, contents: QByteArray, parent = None):
        super().__init__(contents, parent=parent)
        self.svg_contents = contents.data().decode('utf-8')

class DeepCopyableSvgItem(QGraphicsSvgItem, DeepCopyableItemABC):
    """ Wrapper for QGraphicsSvgItem that supports deepcopying and conversion to valid SVG code that can be included in a SVG document """

    def __init__(self, data: None | StoringQSvgRenderer | str = None, parent=None):
        self.svg_data = None
        self.xml_info = {}
        self.doctype_info = {}

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
        body = self.svg_data

        xml_declaration_pattern_contents = r'<\?xml\s+version="([^"]+)"\s+encoding="([^"]+)"\s+standalone="([^"]+)"\?>'
        doctype_pattern_contents = r'<!DOCTYPE\s+svg\s+PUBLIC\s+"([^"]+)"\s+"([^"]+)">'
        xml_declaration_match = re.search(xml_declaration_pattern_contents, self.svg_data)
        doctype_match = re.search(doctype_pattern_contents, self.svg_data)
        if xml_declaration_match:
            self.xml_info = {
                'version': xml_declaration_match.group(1),
                'encoding': xml_declaration_match.group(2),
                'standalone': xml_declaration_match.group(3)
            }

        if doctype_match:
            self.doctype_info = {
                'public_id': doctype_match.group(1),
                'system_id': doctype_match.group(2)
            }

        # remove xml declartion and doctype_pattern
        xml_declaration_pattern = r'<\?xml[^>]*\?>'
        doctype_pattern = r'<!DOCTYPE[^>]*>'
        body = re.sub(xml_declaration_pattern, "", body)
        body = re.sub(doctype_pattern, "", body)
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

    def to_svg(self, defs: dict):
        transform_svg = self.transform_to_svg(self.sceneTransform())
        body = self.svg_body()
        xml_info = []
        for k, v in self.xml_info.items():
            xml_info.append(f' metadata-{k}="{v}"')
        for k, v in self.doctype_info.items():
            xml_info.append(f' metadata-{k}="{v}"')
        info = "".join(xml_info)
        return (f'<g transform="{transform_svg}" metadata-custom-type="DeepCopyableSvgItem" \n'
                f'{info}>\n'
                f'  {body}\n'
                f'</g>\n'
                )

class DeepCopyableEllipseItem(QGraphicsEllipseItem, DeepCopyableShapeABC):
    """ Wrapper for QGraphicsEllipseItem that supports deepcopy """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def boundingRect(self) -> QRectF:
        return super().boundingRect()

#    def setRect(self, rect: QRectF):
#        super().setRect(rect)

    def to_svg(self, defs: dict):
        pen_svg = self.pen_to_svg(self.pen())
        brush_svg = self.brush_to_svg(self.brush(), defs)
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

class DeepCopyableRectItem(QGraphicsRectItem, DeepCopyableShapeABC):
    """ Wrapper for QGraphicsRectItem that supports deepcopy """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def boundingRect(self):
        return super().boundingRect()

    def to_svg(self, defs: dict):
        brush_svg = self.brush_to_svg(self.brush(), defs)
        pen_svg = self.pen_to_svg(self.pen())
        transform = self.sceneTransform()
        transform_svg = self.transform_to_svg(transform)
        item_svg = f'<rect x="{self.rect().x()}" y="{self.rect().y()}" width="{self.rect().width()}" height="{self.rect().height()}"'
        item_svg += f' style="{pen_svg};{brush_svg}"/>'

        return (f'<g transform="{transform_svg}">\n'
                f'  {item_svg}\n'
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

class DeepCopyableLineItem(QGraphicsLineItem, DeepCopyableLineABC):
    """ Wrapper for QGraphicsLineItem that supports deepcopy """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_svg(self, defs: dict):
        pen_svg = self.pen_to_svg(self.pen())
        line = self.line()
        transform = self.sceneTransform()
        transform_svg = self.transform_to_svg(transform)
        item_svg = f'<polyline points="{line.x1()} {line.y1()} {line.x2()} {line.y2()}" style="{pen_svg}"/>'

        return (f'<g transform="{transform_svg}">\n'
                f'  {item_svg}\n'
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

class DeepCopyablePathItem(QGraphicsPathItem, DeepCopyableItemABC):
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

    def to_svg(self, defs: dict) -> str:
        pen_svg = self.pen_to_svg(self.pen())
        brush_svg = self.brush_to_svg(self.brush(), defs)
        path_svg = self._path_to_svg()
        path_element_svg = f'<path style="{pen_svg};{brush_svg}" d="{path_svg}"/>'
        transform = self.sceneTransform()
        transform_svg = self.transform_to_svg(transform)
        return (f'<g transform="{transform_svg}">\n'
                f'  {path_element_svg}\n'
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

class DeepCopyableTextbox(QGraphicsRectItem, DeepCopyableItemABC):
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

    def to_svg(self, defs: dict) -> str:
        font_item = self.text_item.font()
        rect = self.rect()
        transform = self.sceneTransform()
        transform_svg = self.transform_to_svg(transform)
        item_svg = f'<text x="{rect.x()}" y="{rect.y()}" font-family="{font_item.family()}" font-size="{font_item.pointSize()}"'
        item_svg += f' data-custom-params="{self.rect().width()} {self.rect().height()}">\n'
        item_svg += f"{self.text()}\n"
        item_svg += f'</text>'

        return (f'<g transform="{transform_svg}">\n'
                f'  {item_svg}\n'
                f'</g>\n')

    def __deepcopy__(self, memo) -> DeepCopyableTextbox:
        rect_copy = QRectF(self.rect().x(), self.rect().y(), self.rect().width(), self.rect().height())
        new_item = DeepCopyableTextbox(rect_copy)
        return new_item


class DeepCopyableItemGroup(QGraphicsItemGroup, DeepCopyableItemABC):
    """ Wrapper for QGraphicsItemGroup that supports deepcopy """
    def __init__(self, *args, **kwargs):
        raise NotImplementedError
#        super().__init__(*args, **kwargs)

#    def __deepcopy__(self) -> DeepCopyableItemGroup:
#        scene = self.scene()
#        group = DeepCopyableItemGroup()
#        scene.addItem(group)
#        for item in self.childItems():
#            item_copy = deepcopy(item)
#            group.addToGroup(item_copy)

#    def to_svg(self, defs: dict):
#        transform = self.sceneTransform()
#        transform_svg = self.transform_to_svg(transform)
#        item_svg = ""
#        for item in self.childItems():
#            print(item, "child item group")
#            if hasattr(item, "to_svg"):
#                to_svg = getattr(item, "to_svg")
#                item_svg += to_svg() + '\n'
#
#        return (f'<g transform="{transform_svg}">\n'
#                f'  {item_svg}\n'
#                f'</g>\n')
