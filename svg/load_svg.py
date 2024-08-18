from typing import Dict, Literal, Any
from PyQt6.QtGui import QColor, QFont, QPainterPath, QPen, QBrush, QTransform
from PyQt6.QtCore import QLineF, QByteArray, QPoint, QPointF, QRect, QRectF, Qt
from lxml import etree
import re
from ..graphics import (DeepCopyableEllipseItem, DeepCopyableGraphicsItem, DeepCopyableGraphicsItem, SelectableRectItem, DeepCopyableSvgItem, StoringQSvgRenderer,
                        DeepCopyablePathItem,DeepCopyableRectItem, DeepCopyableLineItem, DeepCopyableTextbox)
from pathlib import Path
from ..utils import build_transform, transform_path

def parse_d_attribute(d_attr: str) -> QPainterPath:
    """ Parses d attribute belonging to an svg path tag
    returns: painter path object
    TODO: Currently only 'simple' paths are parsed. We do not handle arcs or relative commands
        """
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

        elif cmd == 'L':
            # Line to
            i += 1
            x, y = float(commands[i]), float(commands[i+1])
            path.lineTo(x, y)
            i += 2
        elif cmd == 'C':
            # Cubic Bezier curve
            i += 1
            x1, y1 = float(commands[i]), float(commands[i+1])
            x2, y2 = float(commands[i+2]), float(commands[i+3])
            x3, y3 = float(commands[i+4]), float(commands[i+5])
            path.cubicTo(x1, y1, x2, y2, x3, y3)
            i += 6
        elif cmd == 'Q':
            # Quadratic Bezier curve (absolute)
            i += 1
            x1, y1 = float(commands[i]), float(commands[i+1])
            x2, y2 = float(commands[i+2]), float(commands[i+3])
            path.quadTo(x1, y1, x2, y2)
            i += 4

        elif cmd == 'Z' or cmd == 'z':
            # Close path
            path.closeSubpath()
            i += 1
        else:
            i += 1
    return path


def parse_element_style(element: etree._Element, default: Dict[Literal["fill", "stroke", "stroke-width", "stroke-linecap"], Any] | None = None) -> tuple[QPen, QBrush]:
    """ parses element style attribute
    element: etree._Element representation of svg document
    default: any key value pairs set in dict will overide the default values
    returns: QPen and QBrush from style attribute
    """
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
            if "rgb" in value:
                pattern = r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)|rgb\s*\(\s*(\d+)\s+(\d+)\s+(\d+)\s*\)'
                match = re.match(pattern, value)
                if match:
        # Extract the captured groups, handling both formats
                    if match.group(1) is not None:
                        r, g, b = match.group(1), match.group(2), match.group(3)
                    else:
                        r, g, b = match.group(4), match.group(5), match.group(6)
                    brush = QBrush(QColor(int(r), int(g), int(b)))
                    print(brush.color().red(), "RED")

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
    """ Class for building a scene with selectable items from svg document
    TODO: 1.finsish writing docu
          2. Fix parse defs
          3. Fix parse patterns
          4. Fix load svg
    """
    def __init__(self, source: Path | bytes):
        self.svg_namespace = {'svg': 'http://www.w3.org/2000/svg'}

        if isinstance(source, Path):
            with open(source, "rb") as file:
                self.source = file.read()
        else:
            self.source = source
        self.scene_items = []
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
        """ This does not take into account viewport sizes """
#        print(etree.tostring(self.root, encoding='utf-8', pretty_print=True))
        elements = self.root.findall('.//*', namespaces=self.svg_namespace)
        outer_elements = [e for e in elements if self.is_child_to("svg", e)]
#        for outer_element in outer_elements:
#            g_items = self.parse_element(outer_element, dict(outer_element.attrib))
#            scene_items.extend(g_items)
        self.parse_element(self.root, {}, None)
        return self.scene_items

    def parse_defs_element(self, defs_element: etree._Element, parent_attr, parent_transform) -> dict:
        defs = {}
        immediate_children = [e for e in defs_element if self.is_child_to("defs", e)]
        for e in immediate_children:
            if isinstance(e, etree._Comment):
                continue
            elif (id := e.attrib.get("id", None)) is not None and self.element_name(e) != "use":
                element_transform = e.attrib.get("transform", None)
                element_transform = self.combine_parent_child_transform(element_transform, parent_transform)
                element_attr = parent_attr | dict(e.attrib)
                defs[id] = (e, element_attr, element_transform)

            elif self.element_name(e) == "use":
                if (id := e.attrib.get("id", None)) is not None:
                    if defs.get(id, None) is not None:
                        element, def_parent_attr, def_parent_transform = defs[id]
                        self.parse_element(element, def_parent_attr, def_parent_transform)


            elif self.element_name(e) not in self.func_map.keys():
                self.parse_defs_element(e, parent_attr, parent_transform)
        return defs


    def parse_element(self, element, parent_attr, parent_transform: QTransform | None =None):
        defs = {}
        element_transform = element.attrib.get("transform", None)
        element_transform = self.combine_parent_child_transform(element_transform, parent_transform)
#        element_attr = parent_attr
        element_attr = parent_attr | dict(element.attrib)

#        if self.element_name(element) == "g":
#            element_attr = parent_attr | dict(element.attrib)
        for e in element:
            if isinstance(e, etree._Comment):
                continue
            if self.element_name(e) == "g" and e.attrib.get("metadata-custom-type", None) == "DeepCopyableSvgItem":
                item = self.build_svg_item(e, parent_attr, parent_transform)
                self.scene_items.append(item)
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
                print("USE")
                element_id = None
                for k, v in e.attrib.items():
                    if k.endswith("href"):
                        element_id = v[1:] # remove starting '#'
                if element_id is None: continue
                defs_item_tuple = defs.get(element_id, None)
                if defs_item_tuple is None:
                    continue
                defs_item, defs_item_attr, defs_item_transform = defs_item_tuple

                if isinstance(defs_item, etree._Element):
                    func = self.func_map.get(self.element_name(defs_item))
                    # Check if element is scene element
                    if func:
                        # use tag can define transform which is applied after transform specified in defs tag
                        use_transform = e.attrib.get("transform", None)
                        use_transform = self.combine_parent_child_transform(use_transform, element_transform)
                        # Defined element attributes default to those defined in use tag
                        defs_item_attr = element_attr | defs_item_attr
                        item = func(defs_item, defs_item_attr, use_transform)
                        if item:
                            self.scene_items.append(item)
                continue

            func = self.func_map.get(self.element_name(e), None)
            if func is None:
                self.parse_element(e, element_attr, parent_transform=element_transform)
                continue
            item = func(e, element_attr, element_transform)
            if item:
                self.scene_items.append(item)
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
        rect_item.setBrush(QColor(255, 0, 0))
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

    def build_svg_item(self, element: etree._Element, parent_attrs: dict, parent_transform: QTransform | None) -> DeepCopyableSvgItem | None:
        """
        TODO: determine if these defaults make any sense
        """
        transform = self.combine_parent_child_transform(element.attrib.get("transform", None), parent_transform)
        # Get xml_declartion and doctype info
        version = element.attrib.get("metadata-version", "1.0")
        encoding = element.attrib.get("metadata-encoding", "utf-8")
        standalone = element.attrib.get("metadata-standalone", "no")
        public_id = element.attrib.get("metadata-public_id", "-//W3C/DTD SVG 1.1//EN")
        system_id = element.attrib.get("system_id", "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd")

        doc_header = f'<?xml version="{version}" encoding="{encoding}" standalone="{standalone}"?>\n<!DOCTYPE svg PUBLIC "{public_id}"\n "{system_id}">\n'
        doc_header_bytes = doc_header.encode("utf-8")

        body_str = etree.tostring(element, encoding="utf-8").decode('utf-8')
        # Remove outermost g tag
        body_str = re.sub(r'<g[^>]*>', '', body_str, count=1)
        pattern = f'</g>'
        body_str = re.sub(pattern[::-1], '', body_str[::-1], count=1)
        body_str = body_str[::-1]

        doc_bytes = doc_header_bytes + body_str.encode('utf-8')
        q_byte_array = QByteArray(doc_bytes)
        renderer = StoringQSvgRenderer(q_byte_array)
        item = DeepCopyableSvgItem()
        item.setSharedRenderer(renderer)
        if transform:
            item.setTransform(transform)
        return item
