from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtGui import QColor

def color_to_rgb(color: QColor):
    return f'rgb({color.red()}, {color.green()}, {color.blue()})'

def build_defs_svg(defs: dict) -> str:
    defs_svg = '<defs>\n'
    defs_svg += "\n    ".join(defs.values())
    defs_svg += "</defs>\n"
    return defs_svg

def scene_to_svg(scene: QGraphicsScene, filename: str):
    defs = {}
    svg_viewbox = scene.sceneRect()
    svg_content = ''
    for item in scene.items():
        if item.parentItem() is None: # Only consider Selectable rect items
            if hasattr(item, 'to_svg'):
                to_svg = getattr(item, 'to_svg')
                svg_content += to_svg(defs) + '\n'

    defs_svg = build_defs_svg(defs)
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

