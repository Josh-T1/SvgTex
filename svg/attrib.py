from typing import Dict, Literal, Any
from PyQt6.QtGui import QColor, QPainterPath, QPen, QBrush
from PyQt6.QtCore import Qt
from lxml import etree
import re

def tools_from_attrib(attrib: etree._Element.attrib) -> tuple[QPen, QBrush]:
    pen, brush = QPen(QColor("white")), QBrush(Qt.BrushStyle.SolidPattern)
    pen = build_pen_from_attrib(attrib, pen)
    brush = build_brush_from_attrib(attrib, brush)
    pen, brush = build_tools_from_style(attrib.get("style", ""), pen, brush)
    return pen, brush

def build_pen_from_attrib(attrib: etree._Element.attrib, pen: QPen) -> QPen:
    _defaults = {"fill": None, "stroke": "black", "stroke-width": None, "stroke-linecap": None}
    stroke_color = attrib.get('stroke', _defaults["stroke"])
    stroke_width = attrib.get('stroke-width', _defaults["stroke-width"])
    stroke_linecap = attrib.get('stroke-linecap', _defaults["stroke-linecap"])
    if stroke_color: pen.setColor(QColor(stroke_color))
    if stroke_width: pen.setWidthF(float(stroke_width))
    # Apply stroke line cap style to QPen
    if stroke_linecap:
        if stroke_linecap == 'round': pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        elif stroke_linecap == 'square': pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        elif stroke_linecap == 'butt': pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    return pen

def build_brush_from_attrib(attrib: etree._Element.attrib, brush: QBrush) -> QBrush:
    # name vs rgb handle both
    fill_color = attrib.get('fill', "none")
    fill_opacity = attrib.get("fill-opacity", 255)
    if "rgb" in fill_color:
        contents = fill_color.split("(")[1].split(")")[0]
        contents_clean = [i.strip() for i in contents.split(",")]
        if len(contents_clean) == 3:
            r, g, b = contents_clean
            brush.setColor(QColor(int(r), int(g), int(b), int(fill_opacity)))
        elif len(contents_clean) == 4:
            r, g, b, opacity = contents_clean
            brush.setColor(QColor(int(r), int(g), int(b), int(opacity)))
    else:
        if fill_color != "none": # for some reason ```brush = QBrush(); brush.setColor(QColor("black"))``` does not work.. tmp fix
            brush.setColor(QColor(fill_color))
        else:
            brush = QBrush(QColor("transparent")) # does this work
    return brush

def build_tools_from_style(style: str, pen: QPen, brush: QBrush) -> tuple[QPen, QBrush]:
    properties = style.split(';')

    for prop in properties:
        if ':' not in prop:
            continue
        key, value = prop.split(':', 1)
        key = key.strip()
        value = value.strip()

        if key == 'fill':
            if value == "none":
                continue
            elif value.startswith("url"):
                url = value.split("(")[1].split(")")[0]
                re_pattern = r'^#(\d+)-(\d+)-(\d+)-(\d+)-([\w]+)$'
                match = re.match(re_pattern, url)
                if not match:
                    continue
                r, g, b, opacity, pattern_id = match.group(1), match.group(2), match.group(3), match.group(4), match.group(5)
                if pattern_id == "dense1Pattern": brush.setStyle(Qt.BrushStyle.Dense1Pattern)
                elif pattern_id == "dense2Pattern": brush.setStyle(Qt.BrushStyle.Dense2Pattern)
                elif pattern_id == "dense3Pattern": brush.setStyle(Qt.BrushStyle.Dense3Pattern)
                elif pattern_id == "dense4Pattern": brush.setStyle(Qt.BrushStyle.Dense4Pattern)
                elif pattern_id == "dense5Pattern": brush.setStyle(Qt.BrushStyle.Dense5Pattern)
                elif pattern_id == "dense6Pattern": brush.setStyle(Qt.BrushStyle.Dense6Pattern)
                elif pattern_id == "dense7Pattern": brush.setStyle(Qt.BrushStyle.Dense7Pattern)
                elif pattern_id == "horPattern": brush.setStyle(Qt.BrushStyle.HorPattern)
                elif pattern_id == "verPattern": brush.setStyle(Qt.BrushStyle.VerPattern)
                elif pattern_id == "crossPattern": brush.setStyle(Qt.BrushStyle.CrossPattern)
                elif pattern_id == "bDiagPattern": brush.setStyle(Qt.BrushStyle.BDiagPattern)
                elif pattern_id == "fDiagPattern": brush.setStyle(Qt.BrushStyle.FDiagPattern)
                elif pattern_id == "diagCrossPattern": brush.setStyle(Qt.BrushStyle.DiagCrossPattern)
                brush.setColor(QColor(int(r), int(g), int(b), int(opacity)))
            else:
                if "rgb" in value:
                    contents = value.split("(")[1].split(")")[0]
                    contents_clean = [i.strip() for i in contents.split(",")]
                    if len(contents_clean) == 3:
                        r, g, b = contents_clean
                        brush.setColor(QColor(int(r), int(b), int(g)))
                        brush.setStyle(Qt.BrushStyle.SolidPattern)
                    elif len(contents_clean) == 4:
                        r, g, b, opacity = contents_clean
                        brush.setColor(QColor(int(r), int(b), int(g), int(opacity)))
                        brush.setStyle(Qt.BrushStyle.SolidPattern)
                else:
                    brush.setColor(QColor(value))
                    brush.setStyle(Qt.BrushStyle.SolidPattern)

        elif key == "fill_opacity":
            r, g, b = brush.color().red(), brush.color().green(), brush.color().blue()
            brush.setColor(QColor(int(r), int(g), int(b), int(value)))

        elif key == 'stroke': pen.setColor(QColor(value))
        elif key == 'stroke-width': pen.setWidthF(float(value))
        elif key == 'stroke-linecap':
            # Handle pen line cap (but may need additional conversion from string)
            if value == 'round': pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            elif value == 'square': pen.setCapStyle(Qt.PenCapStyle.SquareCap)
            elif value == 'butt': pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        elif key == "stroke-dasharray":
            if value == "5, 5": pen.setStyle(Qt.PenStyle.DashLine)
            elif value == "1, 5": pen.setStyle(Qt.PenStyle.DotLine)
            elif value == "5, 5, 1, 5": pen.setStyle(Qt.PenStyle.DashDotLine)
            elif value == "5, 5, 1, 5, 1, 5": pen.setStyle(Qt.PenStyle.DashDotLine)
    return pen, brush

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


