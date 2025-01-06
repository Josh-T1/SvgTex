from PyQt6.QtGui import QColor

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

def build_dense_pattern_svg(color: QColor, num: int):
    r, g, b = color.red(), color.green(), color.blue()
    return(f'<pattern id="{r}-{g}-{b}-{color.alpha()}-dense{num}Pattern" patternUnits="userSpaceOnUse" width="10" height="10">\n'
           f'   <rect width="10" height="10" fill="rgb(255, 255, 255)"/>\n'
           f'   <path d="M 0 0 L 10 10 M -1 10 L 1 10 M 10 -1 L 10 1" stroke="{color_to_rgb(color)}" stroke-width="1"/>\n'
           f'</pattern>\n')

def build_hor_pattern_svg(color: QColor, id: str):
    return(
            f'<pattern id="{id}" patternUnits="userSpaceOnUse" width="10" height="10">\n'
            f'   <rect width="10" height="10" fill="rgb(255, 255, 255)"/>\n'
            f'   <path d="M 0 5 L 10 5" stroke="{color_to_rgb(color)}" stroke-width="1"/>\n'
            f'</pattern>\n')

def build_ver_pattern_svg(color: QColor, id: str):
    return (
            f'<pattern id="{id}" patternUnits="userSpaceOnUse" width="10" height="10">\n'
            f'   <rect width="10" height="10" fill="rgb(255, 255, 255)"/>\n'
            f'   <path d="M 5 0 L 5 10" stroke="{color_to_rgb(color)}" stroke-width="1"/>\n'
            f'</pattern>\n')

def build_cross_pattern_svg(color: QColor, id: str):
    return (
            f'<pattern id="{id}" patternUnits="userSpaceOnUse" width="10" height="10">\n'
            f'   <rect width="10" height="10" fill="rgb(255, 255, 255)"/>\n'
            f'   <path d="M 0 5 L 10 5 M 5 0 L 5 10" stroke="{color_to_rgb(color)}" stroke-width="1"/>\n'
            f'</pattern>\n')

def build_bdiag_pattern_svg(color: QColor, id):
    return (
            f'<pattern id="{id}" patternUnits="userSpaceOnUse" width="10" height="10">\n'
            f'  <rect width="10" height="10" fill="rgb(255, 255, 255)"/>\n'
            f'  <path d="M 0 10 L 10 0" stroke="{color_to_rgb(color)}" stroke-width="1"/>\n'
            f'</pattern>\n')

def build_fdiag_pattern_svg(color: QColor, id: str):
    return(
            f'<pattern id="{id}" patternUnits="userSpaceOnUse" width="10" height="10">\n'
            f'  <rect width="10" height="10" fill="rgb(255, 255, 255)"/>\n'
            f'  <path d="M 0 0 L 10 10" stroke="{color_to_rgb(color)}" stroke-width="1"/>\n'
            f'</pattern>\n')

def build_diagcross_pattern_svg(color: QColor, id: str):
    return (
            f'<pattern id="{id}" patternUnits="userSpaceOnUse" width="10" height="10">\n'
            f'  <rect width="10" height="10" fill="rgb(255, 255, 255)"/>\n'
            f'  <path d="M 0 0 L 10 10 M 10 0 L 0 10" stroke="{color_to_rgb(color)}" stroke-width="1"/>\n'
            f'</pattern>\n')
