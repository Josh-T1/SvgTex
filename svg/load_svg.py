from typing import Type
from PyQt6.QtWidgets import QApplication, QGraphicsItem, QGraphicsItemGroup, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPathItem
from PyQt6.QtGui import QColor, QPainterPath, QPen, QBrush, QTransform
from PyQt6.QtCore import QRectF, QPointF, QSize, QSizeF
import sys
from lxml import etree
import re
import xml.etree.ElementTree as ET
from ..graphics import (DeepCopyableSvgItem, DeepCopyableEllipseItem, DeepCopyableGraphicsItem, DeepCopyableLineItem,
                        DeepCopyablePathItem,DeepCopyableRectItem, DeepCopyableTextbox, SelectableRectItem, DeepCopyableItemGroup)
from pathlib import Path
import numpy as np

def translate_matrix(tx: float, ty: float) -> np.ndarray:
    return np.array([
        [1.0, 0.0, tx],
        [0.0, 1.0, ty],
        [0.0, 0.0, 1.0]
    ])

def scale_matrix(sx: float, sy: float) -> np.ndarray:
    return np.array([
        [sx, 0, 0],
        [0, sy, 0],
        [0, 0, 1]
    ])

def rotate_matrix(angle: float, cx=0, cy=0) -> np.ndarray:
    rad = np.radians(angle)
    cos_a, sin_a = np.cos(rad), np.sin(rad)
    return np.array([
        [cos_a, -sin_a, cx - cos_a * cx + sin_a * cy],
        [sin_a, cos_a, cy - sin_a * cx - cos_a * cy],
        [0, 0, 1]
    ])

def skew_x_matrix(angle: float) -> np.ndarray:
    return np.array([
        [1, np.tan(np.radians(angle)), 0],
        [0, 1, 0],
        [0, 0, 1]
    ])

def skew_y_matrix(angle) -> np.ndarray:
    return np.array([
        [1, 0, 0],
        [np.tan(np.radians(angle)), 1, 0],
        [0, 0, 1]
    ])

def combine_transforms_from_string(transforms: list[str]) -> np.ndarray:
    """
    -- Params --
    transforms: list of transformatinos represented as strings. eg. 'scale(1, 2)' or 'translate(100, 50)'
    returns: matrix of transformation
    """
    matrix = np.identity(3)

    for transform in transforms:
        args = transform.split("(")[1].split(")")[0].split(" ")
        action = transform.split("(")[0] #)
        if action == "translate":
            args = [float(arg) for arg in args]
            matrix = np.dot(matrix, translate_matrix(*args))
        elif action == "scale":
            args = [float(arg) for arg in args]
            if len(args) == 1:
                args = args * 2
            matrix = np.dot(matrix, scale_matrix(*args))

        elif action == "rotate":
            args = [int(arg) for arg in args]
            matrix = np.dot(matrix, rotate_matrix(*args))

        elif action == "skewX":
            args = [float(arg) for arg in args]
            matrix = np.dot(matrix, skew_x_matrix(*args))

        elif action == "skewY":
            args = [float(arg) for arg in args]
            matrix = np.dot(matrix, skew_y_matrix(*args))
        elif action == "matrix":
            matrix_ = np.array([
                [float(args[0]), float(args[1]), float(args[4])],
                               [float(args[2]), float(args[3]), float(args[5])],
                               [0.0, 0.0, 1]
                               ])
            matrix = np.dot(matrix, matrix_)

    return matrix

def color_to_rgb(color: QColor):
    return f'rgb({color.red()}, {color.green()}, {color.blue()})'

def gradient_to_svg(gradient):
    stops = gradient.stops()
    stop_elements = []
    for offset, color in stops:
        stop_elements.append(f'<stop offset="{offset}" style="stop-color:{color_to_rgb(color)};stop-opacity:{color.alpha() / 255.0}"/>')
    return ''.join(stop_elements)

def linear_gradient_to_svg(gradient):
    svg = (f'<linearGradient id="linearGradient" gradientUnits="userSpaceOnUse" '
           f'x1="{gradient.start().x()}" y1="{gradient.start().y()}" x2="{gradient.finalStop().x()}" y2="{gradient.finalStop().y()}">')
    svg += gradient_to_svg(gradient)
    svg += '</linearGradient>'
    return svg

def radial_gradient_to_svg(gradient):
    svg = (f'<radialGradient id="radialGradient" gradientUnits="userSpaceOnUse" '
           f'cx="{gradient.center().x()}" cy="{gradient.center().y()}" r="{gradient.radius()}" '
           f'fx="{gradient.focalPoint().x()}" fy="{gradient.focalPoint().y()}">')
    svg += gradient_to_svg(gradient)
    svg += '</radialGradient>'
    return svg

def conical_gradient_to_svg(gradient):
    svg = (f'<radialGradient id="conicalGradient" gradientUnits="userSpaceOnUse" '
           f'cx="{gradient.center().x()}" cy="{gradient.center().y()}" r="50%" fx="{gradient.center().x()}" fy="{gradient.center().y()}">')
    svg += gradient_to_svg(gradient)
    svg += '</radialGradient>'
    return svg

defs_svg = (f'<defs>\n'
            f'<!-- Dense1Pattern -->\n'
            f'<pattern id="dense1Pattern" patternUnits="userSpaceOnUse" width="10" height="10">\n'
            '<rect width="10" height="10" fill="white"/>\n'
            '<path d="M 0 0 L 10 10 M -1 10 L 1 10 M 10 -1 L 10 1" stroke="black" stroke-width="1"/>\n'
            '</pattern>\n'
            '<!-- Horizontal Pattern -->\n'
            '<pattern id="horPattern" patternUnits="userSpaceOnUse" width="10" height="10">\n'
            '<rect width="10" height="10" fill="white"/>\n'
            '<path d="M 0 5 L 10 5" stroke="black" stroke-width="1"/>\n'
            '</pattern>\n'
            '<!-- Vertical Pattern -->\n'
            '<pattern id="verPattern" patternUnits="userSpaceOnUse" width="10" height="10">\n'
            '<rect width="10" height="10" fill="white"/>\n'
            '<path d="M 5 0 L 5 10" stroke="black" stroke-width="1"/>\n'
            '</pattern>\n'
            '<!-- Cross Pattern -->\n'
            '<pattern id="crossPattern" patternUnits="userSpaceOnUse" width="10" height="10">\n'
            '<rect width="10" height="10" fill="white"/>\n'
            '<path d="M 0 5 L 10 5 M 5 0 L 5 10" stroke="black" stroke-width="1"/>\n'
            '</pattern>\n'
            '<!-- Diagonal Cross Pattern -->\n'
            '<pattern id="diagCrossPattern" patternUnits="userSpaceOnUse" width="10" height="10">\n'
            '<rect width="10" height="10" fill="white"/>\n'
            '<path d="M 0 0 L 10 10 M 10 0 L 0 10" stroke="black" stroke-width="1"/>\n'
            '</pattern>\n'
            '</defs>')


def scene_to_svg(scene: QGraphicsScene, filename: str):
    svg_viewbox = scene.sceneRect()

    svg_content = ''
    for item in scene.items():
        if item.parentItem() is None: # Only consider Selectable rect items
            if hasattr(item, 'to_svg'):
                to_svg = getattr(item, 'to_svg')
                svg_content += to_svg() + '\n'

    full_svg = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
            f'<svg width="{svg_viewbox.width()}px" height="{svg_viewbox.height()}px" viewBox="{svg_viewbox.topLeft().x()} {svg_viewbox.topLeft().y()} {svg_viewbox.bottomRight().x()} {svg_viewbox.bottomRight().y()}"\n'
            f'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.2" baseProfile="tiny">\n'
            f'{defs_svg}\n'
            f'{svg_content}\n'
            f'</svg>'
            )

    with open(filename, 'w') as file:
        file.write(full_svg)

def matrix_to_qtransform(matrix: np.ndarray):
    qtransform = QTransform(matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1], matrix[0][2], matrix[1][2])
    return qtransform


def build_transform(transform: str) -> QTransform:
    transforms = transform.split(" ")
    matrix = combine_transforms_from_string(transforms)
    qtransform = matrix_to_qtransform(matrix)
    return qtransform

def build_ellipse(element: ET.Element, parent_transform=None):
    pen = QPen()
    transform_str = element.attrib.get('transform', None)
    transform = None if transform_str is None else build_transform(transform_str)
    x, y = float(element.attrib['x']), float(element.attrib['y'])
    cy, cx = float(element.attrib['cy']), float(element.attrib['cx'])
    fill = element.attrib.get('fill', None)
    pen_stroke = element.attrib.get('stroke', "black")
    pen_width = element.attrib.get("width", "1")
    pen.setWidth(int(pen_width))
    pen.setColor(QColor(pen_stroke))

    ellipse_item = DeepCopyableEllipseItem(x, y, cx, cy)
    ellipse_item.setPen(pen)
    if transform is not None:
        ellipse_item.setTransform(transform)
    if fill is not None:
        ellipse_item.setBrush(QBrush(QColor(fill)))
    return ellipse_item

def build_rect(element: ET.Element, parent_transform=None):
    transform_str = element.attrib.get('transform', None)
    transform = None if transform_str is None else build_transform(transform_str)
    x, y = float(element.attrib['x']), float(element.attrib['y'])
    width, height = float(element.attrib['width']), float(element.attrib['height'])
    fill = element.attrib.get('fill', None)
    pen_stroke = element.attrib.get('stroke', "black")
    pen_width = element.attrib.get('width', "1")
    pen = QPen()
    pen.setColor(QColor(pen_stroke))
    pen.setWidth(int(pen_width))

    rect_item = QGraphicsRectItem(x, y, width, height)

    if transform is not None:
        rect_item.setTransform(transform)
    if fill is not None:
        rect_item.setBrush(QBrush(QColor(fill)))
    return rect_item

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
            print(cmd, x, y)

        elif cmd == 'L':
            # Line to
            i += 1
            x, y = float(commands[i]), float(commands[i+1])
            path.lineTo(x, y)
            i += 2
            print(cmd, x, y)
        elif cmd == 'C':
            # Cubic Bezier curve
            i += 1
            x1, y1 = float(commands[i]), float(commands[i+1])
            x2, y2 = float(commands[i+2]), float(commands[i+3])
            x3, y3 = float(commands[i+4]), float(commands[i+5])
            path.cubicTo(x1, y1, x2, y2, x3, y3)
            i += 6
            print(cmd, x1, y1, x2, y2, x3, y3)
        elif cmd == 'Q':
            # Quadratic Bezier curve (absolute)
            i += 1
            x1, y1 = float(commands[i]), float(commands[i+1])
            x2, y2 = float(commands[i+2]), float(commands[i+3])
            path.quadTo(x1, y1, x2, y2)
            current_pos = (x2, y2)
            i += 4
            print(cmd, x1, y1, x2, y2)

        elif cmd == 'Z' or cmd == 'z':
            # Close path
            print(cmd)
            path.closeSubpath()
            i += 1
        else:
            i += 1
    return path


def build_path(element: ET.Element, parent_transform=None):
    transform_str = element.attrib.get('transform', None)
    transform = None if transform_str is None else build_transform(transform_str)
    path_str = element.attrib.get("d", None)
    if path_str is None:
        return

    pen_stroke = element.attrib.get('stroke', "black")
    pen_width = element.attrib.get('width', "1")
    fill = element.attrib.get('fill', "black")
    pen = QPen()
    pen.setWidth(int(pen_width))
    pen.setColor(QColor(pen_stroke))

    path = parse_d_attribute(path_str)
    path_svg = DeepCopyablePathItem(path)
    path_svg.setPen(pen)
    if fill is not None:
        path_svg.setBrush(QBrush(QColor(fill)))
    if transform is not None:
        path_svg.setTransform(transform)
    return path_svg

def build_textbox(element: ET.Element):
    pass

def build_line(element: ET.Element):
    pass

func_map = {"rect": build_rect,
            "ellipse": build_ellipse,
            "path": build_path,
            "text": build_textbox,
            "line": build_line,
            # how tf do I do svg image
            }
def build_scene_items_from_file(scene, filename: Path):
    with open(filename, 'rb') as file:
        contents = file.read()
    items = build_scene_items(scene, contents)
    return items

def build_scene_items_(scene, svg_doc: bytes):
    svg_namespace = {'svg': 'http://www.w3.org/2000/svg'}
    scene_items = []

    root = etree.fromstring(svg_doc)
    for g in root.findall('.//svg:g', namespaces=svg_namespace):
        group_items = []
        child_tags = g.findall('.//*', namespaces=svg_namespace)
        for child_tag in child_tags:
            func = func_map.get(child_tag.tag.split("}")[-1], None)
            if not func:
                continue
            item = func(child_tag)
            if item:
                group_items.append(item)

        if len(group_items) == 1:
            selectable_item = SelectableRectItem(group_items[0])
            group_items.append(selectable_item)
        elif len(group_items) > 1:
            group = DeepCopyableItemGroup()
            for item in group_items:
                group.addToGroup(item)
            selectable_item = SelectableRectItem(group)
            group_items.append(selectable_item)
        scene_items.extend(group_items)
    return scene_items

def parse_g_tag(g_tag):
    pass
def has_g_ancestor(tag):
    has_g_ancestor = False
    parent = tag.getparent()
    while parent is not None:
        if parent.tag.split("}")[-1] == "g":
            has_g_ancestor = True
            break
        parent = parent.getparent()
    return has_g_ancestor

def build_scene_items(scene, svg_doc: bytes):
    svg_namespace = {'svg': 'http://www.w3.org/2000/svg'}
    scene_items = []
    print(svg_doc.decode('utf-8'))
    root = etree.fromstring(svg_doc)
    g_tags = root.findall('.//svg:g', namespaces=svg_namespace)
    outer_g_tags = [g_tag for g_tag in g_tags if not has_g_ancestor(g_tag)]

    for tag in outer_g_tags:
        group_items = []
        child_tags = tag.findall('.//*', namespaces=svg_namespace)
        for child_tag in child_tags:
            func = func_map.get(child_tag.tag.split("}")[-1], None)
            if not func:
                continue
            item = func(child_tag)
            if item:
                group_items.append(item)

        scene_items.extend(group_items)
    return scene_items

