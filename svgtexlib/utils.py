from enum import Enum
import importlib
import importlib.util
import sys
import json
from pathlib import Path
import re
import io

import numpy as np
from PyQt6.QtGui import QTransform
import matplotlib.pyplot as plt
from lxml import etree

class Handlers(Enum):
    Selector = "NullDrawingHandler"
    Freehand = "FreeHandDrawingHandler"
    Line = "LineDrawingHandler"
    Textbox = "TextboxDrawingHandler"
    Rect = "RectDrawingHandler"
    Ellipse = "EllipseDrawingHandler"
    ConnectedLine = "ConnectedLineHandler"
    Arrow = "ArrowHandler"

class Tools(Enum):
    Brush = "BrushTool"
    Pen = "PenTool"

CONFIG_PATH = Path(__file__).parent / "config.json"
def get_config():
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    return config
config = get_config()


def latex_template(tex: str) -> str:
    return fr"""
\documentclass[preview]{{standalone}}
\usepackage{{amsmath,amsfonts,amsthm,amssymb,mathtools}}
\begin{{document}}
{tex}
\end{{document}}"""
class LatexCompilationError(Exception):
    pass

def tex2svg(equation: str):
    fig = plt.figure(figsize=(1, 1))
    fig.text(0, 0, equation, fontsize=16)
    svg_data = io.BytesIO()
    fig.savefig(svg_data, format="svg", bbox_inches="tight", pad_inches=0.1, dpi=100, transparent=True)
#        raise LatexCompilationError(f"Failed to compile equation: {equation}")
    plt.close(fig)
    svg_data.seek(0)
    return svg_data


def text_is_latex(text: str):
    return text.count("$") == 2 and len(text) != 2


def lazy_import(name, path, parent_package):
    spec = importlib.util.spec_from_file_location(f"{parent_package}.{name}", path)
    if not spec or not spec.loader:
        return None
    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module

def load_shortcuts(module): #-> list[ShortCut]:
    """ Loads modules from path. Then finds all functions in the module that start with
    shortcut_prefix
    :param module: module object
    """
    shortcuts_name = "SHORTCUTS"

    for name, obj in module.__dict__.items():
        if not isinstance(obj, list):
            continue
        if name == shortcuts_name:
            return obj
    return []

class KeyCodes(Enum):
    Key_Delete = 16777219
    Key_Right = 16777236
    Key_Left = 16777234
    Key_u = 85
    Key_i = 73
    Key_c = 67
    Key_f = 70
    Key_l = 76
    Key_t = 84
    Key_s = 83
    Key_n = 78
    Key_esc = 16777216

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

def build_transform(transform: str) -> QTransform:
    transform_pattern = r'\b[a-zA-Z_]\w*\s*\([^)]*\)' # TODO determine limitation of this regex pattern chatgpt provided...
    matches = re.findall(transform_pattern, transform)
    matrix = combine_transforms_from_string(reversed(matches))
    qtransform = matrix_to_qtransform(matrix)
    return qtransform

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
            if len(args) == 1:
                args = args * 2
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
                               [0, 0, 1]
                               ])
            matrix = np.dot(matrix, matrix_)

    return matrix


def matrix_to_qtransform(matrix: np.ndarray):
    qtransform = QTransform(matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1], matrix[0][2], matrix[1][2])
    return qtransform


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
                new_transform = f'''matrix({matrix[0][0]:.8f} {matrix[0][1]:.8f} {matrix[1][0]:.8f} {matrix[1][1]:.8f} {matrix[0][2]:.8f} {matrix[1][2]:.8})'''
                g.set("transform", new_transform)

    tree = etree.ElementTree(root)
    return etree.tostring(tree).decode('utf-8')
