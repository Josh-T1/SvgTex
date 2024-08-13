from typing import Dict, Literal, Any
from PyQt6.QtGui import QColor, QFont, QPainterPath, QPen, QBrush, QTransform
from PyQt6.QtCore import QLineF, QPoint, QPointF, QRect, QRectF, Qt
from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsPathItem
from lxml import etree
import re

from ..graphics import (DeepCopyableEllipseItem, DeepCopyableGraphicsItem, DeepCopyableGraphicsItem,
                        DeepCopyablePathItem,DeepCopyableRectItem, DeepCopyableLineItem, DeepCopyableTextbox)
from pathlib import Path
from ..utils import build_transform, transform_path


def parse_d_attribute(d_attr: str) -> QPainterPath:
    path = QPainterPath()

    commands = re.findall(r'[MLCZQz]|-?\d+\.?\d*', d_attr)
    i = 0
    while i < len(commands):
        cmd = commands[i]

        if cmd == 'M':
            # Move to
            i += 1
            x, y = float(commands[i]), float(commands[i+1])
            path.moveTo(x, y)
            i += 2
#            print(cmd, x, y)

        elif cmd == 'L':
            # Line to
            i += 1
            x, y = float(commands[i]), float(commands[i+1])
            path.lineTo(x, y)
            i += 2
#            print(cmd, x, y)
        elif cmd == 'C':
            # Cubic Bezier curve
            i += 1
            x1, y1 = float(commands[i]), float(commands[i+1])
            x2, y2 = float(commands[i+2]), float(commands[i+3])
            x3, y3 = float(commands[i+4]), float(commands[i+5])
            path.cubicTo(x1, y1, x2, y2, x3, y3)
            i += 6
#            print(cmd, x1, y1, x2, y2, x3, y3)
        elif cmd == 'Q':
            # Quadratic Bezier curve (absolute)
            i += 1
            x1, y1 = float(commands[i]), float(commands[i+1])
            x2, y2 = float(commands[i+2]), float(commands[i+3])
            path.quadTo(x1, y1, x2, y2)
            current_pos = (x2, y2)
            i += 4
#            print(cmd, x1, y1, x2, y2)

        elif cmd == 'Z' or cmd == 'z':
            # Close path
#            print(cmd)
            path.closeSubpath()
            i += 1
        else:
            i += 1
    return path

def parse_element_style(element, default: Dict[Literal["fill", "stroke", "stroke-width", "stroke-linecap"], Any] | None = None) -> tuple[QPen, QBrush]:
    # Initialize default QPen and QBrush
    _defaults = {"fill": None, "stroke": "black", "stroke-width": None, "stroke-linecap": None}
    if default:
        _defaults.update(default) #type: ignore ... probably
    pen = QPen()
    brush = QBrush()

    # Extract attributes or style properties
    fill_color = element.attrib.get('fill', _defaults["fill"])
    stroke_color = element.attrib.get('stroke', _defaults["stroke"])
    stroke_width = element.attrib.get('stroke-width', _defaults["stroke-width"])
    stroke_linecap = element.attrib.get('stroke-linecap', _defaults["stroke-linecap"])

    # Apply fill color to QBrush
    if fill_color: # for some reason ```brush = QBrush(); brush.setColor(QColor("black"))``` does not work.. tmp fix
        brush = QBrush(QColor("black"))
    else:
        brush = QBrush(QColor("transparent")) # does this work
    # Apply stroke color to QPen
    if stroke_color:
        pen.setColor(QColor(stroke_color))

    # Apply stroke width to QPen
    if stroke_width:
        pen.setWidthF(float(stroke_width))

    # Apply stroke line cap style to QPen
    if stroke_linecap:
        if stroke_linecap == 'round':
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        elif stroke_linecap == 'square':
            pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        elif stroke_linecap == 'butt':
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)

    return pen, brush

def parse_style(style: str):
    # Default pen and brush
    pen = QPen()
    pen.setColor(QColor("white")) # svg docs default to white stroke while QPen defaults to black
    brush = QBrush()

    # Split style into properties
    properties = style.split(';')

    for prop in properties:
        if ':' not in prop:
            continue
        key, value = prop.split(':', 1)
        key = key.strip()
        value = value.strip()

        if key == 'fill':
            # Handle brush color
            brush.setColor(QColor(value))
        elif key == 'stroke':
            # Handle pen color
            pen.setColor(QColor(value))
        elif key == 'stroke-width':
            # Handle pen width
            pen.setWidthF(float(value))
        elif key == 'stroke-linecap':
            # Handle pen line cap (but may need additional conversion from string)
            if value == 'round':
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            elif value == 'square':
                pen.setCapStyle(Qt.PenCapStyle.SquareCap)
            elif value == 'butt':
                pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        # Add other properties as needed (e.g., stroke-dasharray)

    return pen, brush

class SvgBuilder:
    def __init__(self, source: Path | bytes):
        self.svg_namespace = {'svg': 'http://www.w3.org/2000/svg'}

        if isinstance(source, Path):
            with open(source, "rb") as file:
                self.source = file.read()
        else:
            self.source = source

        self.root = etree.fromstring(self.source)
        self.fallback_mappings = []
        self.func_map = {"rect": self.build_rect,
                    "ellipse": self.build_ellipse,
                    "path": self.build_path,
                    "text": self.build_textbox,
                    "polyline": self.build_line,
                    }

    def has_ancestor(self, tag: etree._Element):
        has_g_ancestor = False
        parent = tag.getparent()
        while parent is not None:
            if self.element_name(parent) == "g":
                has_g_ancestor = True
                break
            parent = parent.getparent()
        return has_g_ancestor

    def is_child_to(self, parent_name: str, tag: etree._Element):
        parent = tag.getparent()
        if self.element_name(parent) == parent_name:
            return True
        return False

    def build_scene_items(self):
#        print(etree.tostring(self.root, encoding='utf-8', pretty_print=True))
        scene_items = []
        doc_viewbox = self.root.attrib["viewBox"]
        x, y, width, height = [float(num) for num in doc_viewbox.split(" ")]
#        scale_x = width / viewbox.width()
#        scale_y = height / viewbox.height()
#        print(scale_x, scale_y)
#        doc_transform = QTransform().scale(scale_x, scale_y)
        elements = self.root.findall('.//*', namespaces=self.svg_namespace)
        outer_elements = [e for e in elements if self.is_child_to("svg", e)]
        for outer_element in outer_elements:
            g_items = self.parse_element(outer_element, dict(outer_element.attrib))
            scene_items.extend(g_items)
        return scene_items

    def parse_defs_element(self, defs_element: etree._Element, parent_attr, parent_transform) -> dict:
        defs = {}
        immediate_children = [e for e in defs_element if self.is_child_to("defs", e)]
        for e in immediate_children:
            if isinstance(e, etree._Comment):
                continue
            if (id := e.attrib.get("id", None)):
                defs[id] = e
            if self.element_name(e) == "use":
                self.parse_use_element(e, parent_attr, parent_transform, defs)

            if self.element_name(e) not in self.func_map.keys():
                self.parse_defs_element(e, parent_attr, parent_transform)
        return defs


    def parse_element(self, element, parent_attr, parent_transform: QTransform | None =None) -> list:
        e_items = []
        defs = {}
        element_transform = element.attrib.get("transform", None)
        element_transform = self.combine_parent_child_transform(element_transform, parent_transform)
        element_attr = parent_attr

        if self.element_name(element) == "g":
            element_attr = parent_attr | dict(element.attrib)

        for e in element:
            print(e)
            if isinstance(e, etree._Comment):
                continue
            if self.element_name(e) == "defs":
                defs.update(
                        self.parse_defs_element(e, element_attr, element_transform)
                        )
                continue

            elif self.element_name(e) == "pattern":
                # TODO
                continue
            elif self.element_name(e) == "use":
                # Check if item was define in def tags
                element_id = None
                for k, v in e.attrib.items():
                    if k.endswith("href"):
                        element_id = v[1:] # remove starting '#'
                if element_id is None: continue
                def_item = defs.get(element_id, None)

                if isinstance(def_item, etree._Element):
                    func = self.func_map.get(self.element_name(def_item))
                    # Check if element is scene element
                    if func:
                        # use tag can define transform which is applied after transform specified in defs tag
                        use_transform = e.attrib.get("transform", None)
                        use_transform = self.combine_parent_child_transform(use_transform, element_transform)
                        # Defined element attributes default to those defined in use tag
                        for k, v in e.attrib.items():
                            if k == "transform":
                                continue
                            def_item.attrib[k] = v
                        item = func(def_item, element_attr, use_transform)
                        if item:
                            e_items.append(item)
                continue

            func = self.func_map.get(self.element_name(e), None)
            if func is None:
                items = self.parse_element(e, element_attr, parent_transform=element_transform)
                e_items.extend(items)
                continue
            item = func(e, element_attr, element_transform)
            if item:
                e_items.append(item)
        return e_items

    def parse_use_element(self, use_element, parent_attrs, parent_transform, defs: dict) -> DeepCopyableGraphicsItem | None:
        # Check if item was define in def tags
        if (id := use_element.attrib.get("id", None)):
            if (def_item := defs.get(id, None)):
                func = self.func_map.get(self.element_name(def_item))
                # Check if element is scene element
                if func is None:
                    return None

                # use tag can define transform which is applied after transform specified in defs tag
                use_transform = use_element.attrib.get("transform", None)
                use_transform = self.combine_parent_child_transform(use_transform, parent_transform)
                # Defined element attributes default to those defined in use tag
                for k, v in use_element.attrib.items():
                    if k == "transform":
                        continue
                    def_item.attrib[k] = v
                item = func(def_item, parent_attrs, use_transform)
                return item
        return None

    def element_name(self, element: etree._Element) -> str:
        """ Returns element name from element """
        return element.tag.split("}")[-1]

    def combine_parent_child_transform(self, child_transform: str | None, parent_transform: QTransform | None) -> QTransform | None:
        """ Convenience method for setting transform any or non of; pre defined parent QTransform and contents of child element transform attribute """
        if not child_transform and parent_transform is None:
            return None
        if child_transform:
            if parent_transform:
                return build_transform(child_transform) * parent_transform
            else:
                return build_transform(child_transform)
        return parent_transform

    def build_ellipse(self, element: etree._Element, parent_attrs: dict, parent_transform: QTransform | None) -> DeepCopyableEllipseItem:
        transform = self.combine_parent_child_transform(element.attrib.get("transform", None), parent_transform)
        attrs = parent_attrs | dict(element.attrib)
        style = attrs.get("style", None)
        if style is None:
            pen, brush = parse_element_style(element)
        else:
            pen, brush = parse_style(style)

        rx, ry = float(attrs['rx']), float(attrs['ry'])
        cy, cx = float(attrs['cy']), float(attrs['cx'])
        x = cx - rx
        y = cy - ry
        width = rx * 2
        height = ry * 2

        ellipse_item = DeepCopyableEllipseItem(x, y, width, height)
        ellipse_item.setPen(pen)
        ellipse_item.setBrush(brush)
        if transform:
            ellipse_item.setTransform(transform)
        return ellipse_item

    def build_rect(self, element: etree._Element, parent_attrs: dict, parent_transform: QTransform | None):
        transform = self.combine_parent_child_transform(element.attrib.get("transform", None), parent_transform)
        attrs = parent_attrs | dict(element.attrib)
        style = attrs.get("style", None)
        if style is None:
            pen, brush = parse_element_style(element)
        else:
            pen, brush = parse_style(style)

        x, y = float(attrs.get('x', 0)), float(attrs.get('y', '0'))
        width, height = float(attrs['width']), float(attrs['height'])

        rect_item = DeepCopyableRectItem(x, y, width, height)
        rect_item.setPen(pen)
        rect_item.setBrush(brush)
        if transform:
            rect_item.setTransform(transform)
        return rect_item

    def build_path(self, element: etree._Element, parent_attrs: dict, parent_transform: QTransform | None):
        transform = self.combine_parent_child_transform(element.attrib.get("transform", None), parent_transform)
        attrs = parent_attrs | dict(element.attrib)
        path_str = attrs.get("d", None)
        style = attrs.get("style", None)
        if path_str is None:
            return
        if style is None:
            pen, brush = parse_element_style(element, default={"stroke": "black", "fill": "black"})
        else:
            pen, brush = parse_style(style)

        path = parse_d_attribute(path_str)
        path_svg = DeepCopyablePathItem(path)
        if transform:
            print(DeepCopyableGraphicsItem.transform_to_svg(transform))
            path_svg.setTransform(transform)

        path_svg.setPen(pen)
        path_svg.setBrush(brush)
        return path_svg

    def build_line(self, element: etree._Element, parent_attrs: dict, parent_transform: QTransform | None):
        transform = self.combine_parent_child_transform(element.attrib.get("transform", None), parent_transform)
        attrs = parent_attrs | dict(element.attrib)
        points_str = attrs.get("points", None)

        style = attrs.get("style", None)
        if points_str is None:
            return
        if style is None:
            pen, _ = parse_element_style(element, default={"stroke": "black"})
        else:
            pen, _ = parse_style(style)

        points = [float(point) for point in points_str.split(" ")]
        line_svg = DeepCopyableLineItem()
        line_svg.setLine(
                QLineF(QPointF(points[0], points[1]), QPointF(points[2], points[3]))
                )
        line_svg.setPen(pen)
        if transform:
            line_svg.setTransform(transform)
        return line_svg

    def build_textbox(self, element: etree._Element, parent_attrs: dict, parent_transform: QTransform | None):
        transform = self.combine_parent_child_transform(element.attrib.get("transform", None), parent_transform)
        attrs = parent_attrs | dict(element.attrib)
        x, y = float(element.attrib['x']), float(element.attrib['y'])
        element_text = element.text.strip()
        font_family = attrs.get("font-family", "Helvetica")
        font_size = float(attrs.get("font-size", "12"))
        font = QFont()
        font.setFamily(font_family)
        font.setPointSizeF(font_size)
        style = attrs.get("style", None)

        clip_rect = element.attrib.get("data-custom-params", "150 150") # default to 150x150 for standard text elements
        width_str, height_str = clip_rect.split(" ")
        width, height = float(width_str), float(height_str)
        rect = QRectF(x, y, width, height)

        if style is None:
            pen, _ = parse_element_style(element, default={"stroke": "black"})
        else:
            pen, _ = parse_style(style)

        textbox_svg = DeepCopyableTextbox(rect, text=element_text)
        if transform:
            textbox_svg.setTransform(transform)
        textbox_svg.setPen(pen)
        return textbox_svg
