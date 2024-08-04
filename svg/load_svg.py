from PyQt6.QtWidgets import QApplication, QGraphicsItem, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPathItem
from PyQt6.QtGui import QColor, QPainterPath, QPen, QBrush, QTransform
from PyQt6.QtCore import QRectF, QPointF, QSize, QSizeF
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

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


class SvgGraphicsFactory:
    def __init__(self, scene: QGraphicsScene):
        self.scene = scene
        self.items = []

    def build_ellipse(self, element: ET.Element, parent_transform=None):
        transform_str = element.attrib.get('transform', None)
        transform = None if transform_str is None else self.build_transform(transform_str)
        x = float(element.attrib['x'])
        y = float(element.attrib['y'])
        cy = float(element.attrib['cy'])
        cx = float(element.attrib['cx'])
        fill = element.attrib.get('fill', None)
        stroke = element.attrib.get('stroke', None)
        ellipse_item = QGraphicsEllipseItem(x, y, cx, cy)
        if fill is not None:
            ellipse_item.setBrush(QBrush(QColor(fill)))
        if parent_transform:
            ellipse_item.setTransform(parent_transform)
        if transform is not None:
            ellipse_item.setTransform(transform)
        if stroke is not None:
            ellipse_item.setPen(QPen(QColor(stroke)))
        if fill is not None:
            ellipse_item.setBrush(QBrush(QColor(fill)))
        return ellipse_item

    def build_rect(self, element: ET.Element, parent_transform=None):
        transform_str = element.attrib.get('transform', None)
        transform = None if transform_str is None else self.build_transform(transform_str)
        x = float(element.attrib['x'])
        y = float(element.attrib['y'])
        width = float(element.attrib['width'])
        height = float(element.attrib['height'])
        fill = element.attrib.get('fill', None)
        stroke = element.attrib.get('stroke', None)

        rect_item = QGraphicsRectItem(x, y, width, height)

        if parent_transform is not None:
            rect_item.setTransform(parent_transform, True)
        if transform is not None:
            rect_item.setTransform(transform)

        if fill is not None:
            rect_item.setBrush(QBrush(QColor(fill)))
        if stroke is not None:
            rect_item.setPen(QPen(QColor(stroke)))
        return rect_item

    def build_transform(self, transform):
        matrix = [float(num) for num in transform.split('(')[1].split(')')[0].split(',')]
        transform = QTransform(*matrix)
        return transform

    def parse_item(self, item, parent_transform=None) -> list[QGraphicsItem]:
        group_items = []
        if item.tag.endswith('rect'):
            graphics_item = self.build_rect(item)
        elif item.tag.endswith('ellipse'):
            graphics_item = self.build_ellipse(item)
        else:
            graphics_item = None
        if graphics_item:
            child_items = []
            group_items.append(graphics_item)
            for child in item:
                child_items.extend(self.parse_item(child))
                for child in child_items:
                    child.setParent(graphics_item)
        return group_items

    def build(self, filename):
        items = []
        file = Path(filename)
        if not file.is_file(): raise ValueError(f"File: {filename} does not exist")
        if file.stem != '.svg': raise TypeError("Invalid extension of non exist")
        tree = ET.parse(filename)
        root = tree.getroot()

        for group in root.iter():
            graphics_items = self.parse_item(group)
            if graphics_items:
                items.extend(graphics_items)
        for item in items:
            print(item)

def get_children(element):
    children = []
    for child in element:
        if child.tag.split("}")[-1] == 'rect':
            print([e for e in child])
            children.append(child)
            new_children = get_children(child)
            children.extend(new_children)
    return children

def main(svg_file):
    tree = ET.parse(svg_file)
    root = tree.getroot()
    elements = []
    for item in root.iter():
        new = get_children(item)
        elements.extend(new)
    print(elements)


def scene_to_svg(scene: QGraphicsScene, filename: str):
    svg_viewbox = scene.sceneRect()

    svg_content = ''
    for item in scene.items():
        if item.parentItem() is None: # Only consider Selectable rect items
            if hasattr(item, 'to_svg'):
                to_svg = getattr(item, 'to_svg')
                svg_content += to_svg() + '\n'
        else:
            print(item)

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


if __name__ == '__main__':
    file = Path("test.svg")
    main(file)
