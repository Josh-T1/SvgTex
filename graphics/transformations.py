import numpy as np
from lxml import etree
import re
from PyQt6.QtGui import QTransform

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

    return matrix



def transform_path(svg_document: bytes, transform: QTransform) -> str:
    """
    Takes in svg document and updates all path tag id attributes to reflect an additional transformation.
    The transform id is set equal to string representation of final transformation matrix.

    -- Params --
    svg_document: A byte sequence representing an SVG document.
                  The bytes should contain a valid SVG XML structure. e.g:
                    ```
                    b'<?xml version="1.0" encoding="UTF-8"?>
                    <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                    <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />
                    </svg>'
                    ```
    returns: SVG document encoded in utf-8

    TODO: This should be possible using the builtin xml.etree instead of lxml.etree
    """
    transform_np = np.array([[transform.m11(), transform.m12(), transform.dx()], [transform.m21(), transform.m22(), transform.dy()], [0, 0, 1]])
    svg_namespace = {'svg': 'http://www.w3.org/2000/svg'}
    root = etree.fromstring(svg_document)

    for g in root.findall('.//svg:g', namespaces=svg_namespace):
        paths = g.xpath('.//svg:path', namespaces=svg_namespace)
        if len(paths) != 0:

            g_transform_attrib = g.attrib.get("transform")
            if g_transform_attrib:
                transform_pattern = r'\b[a-zA-Z_]\w*\s*\([^)]*\)' # TODO determine limitation of this regex pattern chatgpt provided...

                matches = re.findall(transform_pattern, g_transform_attrib)
                matrix = combine_transforms_from_string(reversed(matches))
                matrix = np.dot(transform_np, matrix)
                new_transform = f'''matrix({matrix[0][0]:.6f} {matrix[0][1]:.6f} {matrix[1][0]:.6f} {matrix[1][1]:.6f} {matrix[0][2]:.6f} {matrix[1][2]:.6f})'''

                g.set("transform", new_transform)
    tree = etree.ElementTree(root)
    return etree.tostring(tree).decode('utf-8')
