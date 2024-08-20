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

def build_brush_from_attrib(attrib: etree._Element.attrib, brush: QBrush) -> QPen:
    fill_color = attrib.get('fill', "none")
    if fill_color: # for some reason ```brush = QBrush(); brush.setColor(QColor("black"))``` does not work.. tmp fix
        brush.setColor(fill_color)
    else:
        brush = QBrush(QColor("transparent")) # does this work

def build_tools_from_style(style: str, pen: QPen, brush: QBrush) -> QPen:
    properties = style.split(';')

    for prop in properties:
        if ':' not in prop:
            continue
        key, value = prop.split(':', 1)
        key = key.strip()
        value = value.strip()

        if key == 'fill':
            if value == "none": pass
            elif value.startswith("url"):
                url = value.split("(")[1].split(")")[0]
                if url == "#dense1Pattern": brush.setStyle(Qt.BrushStyle.Dense1Pattern)
                elif url == "#dense2Pattern": brush.setStyle(Qt.BrushStyle.Dense2Pattern)
                elif url == "#dense3Pattern": brush.setStyle(Qt.BrushStyle.Dense3Pattern)
                elif url == "#dense4Pattern": brush.setStyle(Qt.BrushStyle.Dense4Pattern)
                elif url == "#dense5Pattern": brush.setStyle(Qt.BrushStyle.Dense5Pattern)
                elif url == "#dense6Pattern": brush.setStyle(Qt.BrushStyle.Dense6Pattern)
                elif url == "#dense7Pattern": brush.setStyle(Qt.BrushStyle.Dense7Pattern)
                elif url == "#horPattern": brush.setStyle(Qt.BrushStyle.HorPattern)
                elif url == "#verPattern": brush.setStyle(Qt.BrushStyle.VerPattern)
                elif url == "#crossPattern": brush.setStyle(Qt.BrushStyle.CrossPattern)
                elif url == "#bDiagPattern": brush.setStyle(Qt.BrushStyle.BDiagPattern)
                elif url == "#fDiagPattern": brush.setStyle(Qt.BrushStyle.FDiagPattern)
                elif url == "#diagCrossPattern": brush.setStyle(Qt.BrushStyle.DiagCrossPattern)
            else:
                pairs = value.split(";")
                r, b, g,  fill_opacity = 0, 0, 0, 255
                for fill_key, fill_value in pairs:
                    if fill_key == "rgb":
                    # Handle brush color
                        contents = fill_value.split("(")[1].split(")")[0]
                        r_str, g_str, b_str = contents.split(" ")
                        r, g, b = int(r_str.strip()), int(g_str.strip()), int(b_str.strip())
                    elif fill_key == "fill-opacity":
                        fill_opacity = int(value.strip())
                brush.setColor(QColor(r, b, g, fill_opacity))
                brush.setStyle(Qt.BrushStyle.SolidPattern)

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


