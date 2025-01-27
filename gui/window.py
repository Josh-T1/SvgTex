from collections.abc import Callable
import subprocess
from copy import deepcopy
from typing import Literal, Optional
from PyQt6.QtGui import QAction, QBrush, QCloseEvent, QColor, QCursor, QIcon, QKeyEvent, QKeySequence, QMouseEvent, QPaintEvent, QPainterPath, QPen, QPainter, QPixmap, QTransform
from PyQt6.QtCore import QByteArray, QKeyCombination, QLineF, QPointF, QRect, Qt, QRectF, pyqtBoundSignal, pyqtSignal, QEvent, QSize
from PyQt6.QtWidgets import (QApplication, QCheckBox, QColorDialog, QDialog, QFileDialog, QGestureEvent, QGraphicsItem, QGraphicsPathItem, QGraphicsSceneMouseEvent, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QScrollArea, QSizePolicy, QToolBar, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                             QGraphicsScene, QGraphicsLineItem, QMainWindow, QGraphicsTextItem, QGraphicsRectItem, QComboBox, QFormLayout, QStackedWidget)
from ..drawing.drawing_controller import DrawingController
from ..graphics import DeepCopyableSvgItem, StoringQSvgRenderer, DeepCopyableTextbox, SelectableRectItem
from collections import deque
import logging
from pathlib import Path
from ..svg import scene_to_svg, SvgBuilder
from ..utils import tex2svg, text_is_latex, Handlers, Tools
logger = logging.getLogger(__name__)


UNSAVED_NAME = "Unsaved"
MEDIA_PATH = Path(__file__).parent.parent / "media"

def is_float(string: str):
    try:
        float(string)
        return True
    except ValueError:
        return False

class ShortcutCloseEvent(QCloseEvent):
    pass
class LatexCompilationError(Exception):
    pass

class MissingMathDelimeterError(Exception):
    default_message = "Missing math delimeter"
    def __init__(self, message: str | None = None):
        self.message = message if message is not None else self.default_message
        super().__init__(self.message)

class PngCheckBox(QWidget):
    def __init__(self, path: str):
        super().__init__()
        self._layout = QVBoxLayout()
        self.path = path
        self.initUi()
        self.setLayout(self._layout)

    def initUi(self):
        self._create_widgets()
        self.checkbox.setIconSize(QSize(30, 30))

    def _create_widgets(self):
        self.checkbox = QCheckBox()
        custom_icon = QIcon(self.path)
        self.checkbox.setIcon(custom_icon)



class ToggleMenuWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.toggle_menu_layout = QVBoxLayout()
        self.toggle_menu_layout.setContentsMargins(0, 0, 0, 0)

        self.initUi()
        self.setLayout(self.toggle_menu_layout)
        self.setFixedWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)


    def initUi(self):
        self._create_widgets()
        self._add_widgets()

    def _create_widgets(self):
        brush_patterns = [QCheckBox(Qt.BrushStyle.SolidPattern.name),
                          QCheckBox(Qt.BrushStyle.VerPattern.name),
                          QCheckBox(Qt.BrushStyle.DiagCrossPattern.name),
                          QCheckBox(Qt.BrushStyle.CrossPattern.name)
                          ]
        pen_patterns = [QCheckBox(Qt.PenStyle.SolidLine.name),
                        QCheckBox(Qt.PenStyle.DashLine.name),
                        QCheckBox(Qt.PenStyle.DashDotDotLine.name),
                        QCheckBox(Qt.PenStyle.DashDotLine.name),
                        QCheckBox(Qt.PenStyle.DotLine.name)
                        ]
        self.brush_pattern_label = QLabel("Fill Pattern")
        self.brush_pattern_checkbox = SingleCheckBox(*brush_patterns)
        self.pen_pattern_checkbox = SingleCheckBox(*pen_patterns)
#        self.fill_patterns = QTextList()
        self.pen_pattern_label = QLabel("Pen Pattern")

    def _add_widgets(self):
        self.toggle_menu_layout.addWidget(self.pen_pattern_label)
        self.toggle_menu_layout.addWidget(self.pen_pattern_checkbox)
        self.toggle_menu_layout.addWidget(self.brush_pattern_label)
        self.toggle_menu_layout.addWidget(self.brush_pattern_checkbox)
        self.toggle_menu_layout.addStretch()
        self.toggle_menu_layout.addStretch()
        self.toggle_menu_layout.addStretch()

    def connectBrushStyle(self, func):
        self.brush_pattern_checkbox.clicked.connect(func)
    def connectPenStyle(self, func):
        self.pen_pattern_checkbox.clicked.connect(func)

class RulerWidget(QWidget):
    def __init__(self, orientation: Literal["horizontal", "vertical"], parent=None):
        raise NotImplemented()
#        super().__init__(parent)
#        self.orientation = orientation
#        if self.orientation == "horizontal": self.setFixedWidth(20)
#        else: self.setFixedHeight(20)
#        self.setAutoFillBackground(True)
#        pallete = self.palette()
#        pallete.setColor(self.backgroundRole(), QColor("lightgray"))
#        self.setPalette(pallete)

    def paintEvent(self, event: QPaintEvent):
        if not (parent := self.parent()): return
        painter = QPainter(self)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        if self.orientation == 'horizontal':
            height = self.height()
            view_width = parent.view.width()
            for x in range(0, view_width, 50):  # Draw ticks every 50 pixels
                painter.drawLine(x, 0, x, height)
                painter.drawText(x + 2, height - 5, str(x))
        else:
            width = self.width()
            view_height = parent.view.height()
            for y in range(0, view_height, 50):  # Draw ticks every 50 pixels
                painter.drawLine(0, y, width, y)
                painter.drawText(width - 30, y + 5, str(y))

class GraphicsView(QGraphicsView):
    def __init__(self, controller: None | DrawingController = None):
        super().__init__()
        self._controller =  controller
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if self._controller and event:
            self._controller.mousePressEvent(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._controller and event:
            self._controller.mouseMoveEvent(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._controller and event:
            self._controller.mouseReleaseEvent(event)
        super().mouseReleaseEvent(event)

    def setController(self, controller):
        self._controller = controller

    def controller(self) -> DrawingController | None:
        return self._controller

    def keyPressEvent(self, event: Optional[QKeyEvent]) -> None:
        if event is None:
            return
        if event.key() == Qt.Key.Key_Escape:
            if self._controller is not None:
                self._controller.reset_handler()
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        if event:
            event.ignore()

    def resizeEvent(self, event):
        dpr = self.devicePixelRatioF()
        self.setTransform(QTransform().scale(dpr, dpr))
        super().resizeEvent(event)


class ZoomableScrollArea(QScrollArea):
    """ Very possible this class does not work.. add type hinting"""
    def __init__(self, container):
        super().__init__()
#        self.view = view
        self.container = container
        self.zoom_factor = 1.5
        self.current_zoom = 1.0
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.grabGesture(Qt.GestureType.PinchGesture)
#
    def gestureEvent(self, event: QGestureEvent):
        if gesture := event.gesture(Qt.GestureType.PinchGesture):
            self.pinchTriggered(gesture, gesture.centerPoint())
            return True
        return super().event(event)

    def pinchTriggered(self, gesture: QGestureEvent, pinch_center: QPointF):
        if gesture.state() == Qt.GestureState.GestureUpdated:
            pass

    def event(self, event: QEvent): #type: ignore
        if event.type() == QEvent.Type.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

class TexGraphicsScene(QGraphicsScene):
    def __init__(self, cache_max = 100):
        super().__init__()
        self.cache = deque()
        self.cache_max = cache_max
        self.clipboard_item: QGraphicsItem | None = None


    def copy_to_clipboard(self):
        for item in self.selectedItems():
            if hasattr(item, "__deepcopy__") and isinstance(item, SelectableRectItem):
                self.clipboard_item = deepcopy(item)
                return

    def paste_from_clipboard(self, pos: QPointF):
        if self.clipboard_item:
            self.addItem(self.clipboard_item)

            offset = pos - self.clipboard_item.mapToScene(self.clipboard_item.boundingRect().topLeft())
            translation = QTransform().translate(offset.x(), offset.y())
            self.clipboard_item.setTransform(translation)
            self.clipboard_item = None

    def keyPressEvent(self, event: QKeyEvent | None):
        if event is None:
            return

        event_sequence = QKeySequence(QKeyCombination(event.modifiers(), Qt.Key(event.key())))
#        Qt.KeyboardModifier.ShiftModifier.value
        if QKeySequence(QKeyCombination(Qt.KeyboardModifier.ShiftModifier, Qt.Key.Key_U)).matches(event_sequence) == QKeySequence.SequenceMatch.ExactMatch:
            if len(self.cache) != 0:
                item = self.cache.pop()
                self.addItem(item)

        elif QKeySequence(QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Backspace)).matches(event_sequence) == QKeySequence.SequenceMatch.ExactMatch: #== QKeySequence.SequenceMatch.ExactMatch:
            focus_item = self.focusItem()
            if not isinstance(focus_item, QGraphicsTextItem):
                selected_items = self.selectedItems()
                for item in selected_items:
                    if isinstance(item, SelectableRectItem):
                        self.removeItem(item)
                        self.add_to_cache(item)
                        del item


        super().keyPressEvent(event)

    def add_to_cache(self, item: QGraphicsItem):
        if len(self.cache) > self.cache_max:
            self.cache.popleft()
        self.cache.append(item)

    def set_error_message(self, msg: str):
        msg_box = QMessageBox()
        msg_box.setText(msg)
        msg_box.setWindowTitle("Error")
        msg_box.exec()

    def compile_latex(self, signal):
        failed = set()
        for item in self.items():
            parent = item.parentItem()
            if not isinstance(item, DeepCopyableTextbox) or not isinstance(parent, SelectableRectItem):
                continue

            try:
                res_item = self.attempt_compile(item.text())
            except MissingMathDelimeterError as e:
                failed.add(str(e))
                continue
            except LatexCompilationError as e:
                failed.add(str(e))
                continue
#
            if res_item is not None:
                global_pos = item.mapToScene(item.boundingRect().topLeft())
                transform = res_item.sceneTransform()

                inverse = transform.inverted()[0]
                res_item.setTransform(inverse, combine=True)
                selectable_item = SelectableRectItem(res_item, signal)
                selectable_item.setTransform(QTransform().translate(global_pos.x(), global_pos.y()), combine=True)
                selectable_item.setTransform(transform, combine=True)
                self.addItem(selectable_item)

                item.setParentItem(None)
                self.removeItem(item)
                self.removeItem(parent)
                del item

        num_failed = len(failed)
        if num_failed > 0:
            msg = f"Failed to compile {num_failed} items\n"
            msg += "\n".join(failed)
            self.set_error_message(msg)


    def attempt_compile(self, text) -> DeepCopyableSvgItem:
        if not text_is_latex(text):
            raise MissingMathDelimeterError(f"Missing math delimeter\nEquation: {text}")
        try:
            svg_bytes = tex2svg(text)
        except Exception:
            raise LatexCompilationError(f"Failed to compile equation {text}")
        q_byte_array = QByteArray(svg_bytes.read())
        renderer = StoringQSvgRenderer(q_byte_array)
        item = DeepCopyableSvgItem()
        item.setSharedRenderer(renderer)
        return item

class IntBox(QWidget):
    clicked = pyqtSignal(int)
    def __init__(self, default=2, upper_bound=10, lower_bound=0):
        super().__init__()
        self.box_layout = QHBoxLayout()
        self.value = default
        self.upper_bound = upper_bound
        self.lower_bound = lower_bound
        self.initUi()
        self.setLayout(self.box_layout)
        self.box_layout.setSpacing(0)

    def initUi(self):
        self._create_widgets()
        self._add_widgets()
        self._configure_widgets()

    def _create_widgets(self):
        self.label = QLabel(str(self.value))
        self.increment_button = QPushButton("+")
        self.decrement_button = QPushButton("-")

    def _configure_widgets(self):
        self.increment_button.clicked.connect(self.increment)
        self.decrement_button.clicked.connect(self.decrement)

    def _add_widgets(self):
        self.box_layout.addWidget(self.label)
        self.box_layout.addSpacing(4)
        self.box_layout.addWidget(self.decrement_button)
        self.box_layout.addWidget(self.increment_button)

    def increment(self):
        self.clicked.emit(self.value)
        if self.value <= self.upper_bound:
            self.value += 1
            self.label.setText(str(self.value))

    def decrement(self):
        self.clicked.emit(self.value)
        if self.value >= self.lower_bound:
            self.value -= 1
            self.label.setText(str(self.value))

class SingleCheckBox(QWidget):
    """  """
    clicked = pyqtSignal(str)
    def __init__(self, *args, fallback: None | str = None):
        super().__init__()
        self.checkbox_layout = QVBoxLayout()
        self._checkboxes = []
        self.fallback = fallback

        self.checkbox_layout.addStretch()
        for box in args:
            self.add_checkbox(box)

        self.checkbox_layout.addStretch()
        self.setLayout(self.checkbox_layout)
        self.checkbox_layout.setSpacing(10)

    def add_checkbox(self, checkbox: QCheckBox):
        self._checkboxes.append(checkbox)
        checkbox.clicked.connect(self._handle_check)
        checkbox.clicked.connect(lambda _,t=checkbox.text(): self.clicked.emit(t))
        self.checkbox_layout.addWidget(checkbox)

    def _handle_check(self):
        one_checked = False
        for box in self._checkboxes:
            if box.isChecked() and box != self.sender():
                box.setChecked(False)
                one_checked = True
            elif box.isChecked():
                one_checked = True

        if not one_checked and self.fallback is not None:
            for box in self._checkboxes:
                if box.text() == self.fallback:
                    box.setChecked(True)

    def selected(self):
        for i in self._checkboxes:
            if i.isChecked():
                return i
        return None

class ColorBar(QWidget):

    clicked = pyqtSignal(QColor)
    def __init__(self, default_colors: None | list[QColor] = None, btn_size_x = 20, btn_size_y = 20):
        super().__init__()
        self.btn_size_x = btn_size_x
        self.btn_size_y = btn_size_y
        if default_colors:
            self.default_colors = default_colors
        else:
            self.default_colors = [
                    QColor("black"),
                    QColor("grey"),
                    QColor("red"),
                    QColor("blue"),
                    ]

        self.default_color_buttons = []
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.initUi()
        self.setLayout(self._layout)


    def initUi(self):
        self.first_row = QHBoxLayout()
        self.first_row.setContentsMargins(0, 0, 0, 0)
        self.first_row.setSpacing(3)
        self.second_row = QHBoxLayout()
        self.second_row.setSpacing(3)
        for color in self.default_colors:
            btn = QPushButton()
            btn.setStyleSheet(f"background-color: {color.name()}")
            btn.setProperty("QColor", color)
            btn.setFixedSize(QSize(20, 20))
            self.first_row.addWidget(btn)
            self.default_color_buttons.append(btn)

        self.custom_color_widget = QPushButton("Color Palete")
        self.custom_color_display = QPushButton()
        self.custom_color_display.setFixedSize(QSize(self.btn_size_x, self.btn_size_y))

        self.custom_color_display.setProperty('QColor', QColor("black"))
        self.custom_color_display.setStyleSheet("background-color: black")

        self.second_row.addWidget(self.custom_color_widget)
        self.second_row.addWidget(self.custom_color_display)
        self._layout.addLayout(self.first_row)
        self._layout.addLayout(self.second_row)

        self.connect_buttons()

    def custom_color_callback(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.clicked.emit(color)
            self.custom_color_display.setStyleSheet(f"background-color: {color.name()}")
            self.custom_color_display.setProperty('QColor', color)

    def custom_color_display_callback(self):
        self.clicked.emit(self.custom_color_display.property("QColor"))

    def connect_buttons(self):
        for button in self.default_color_buttons:
            button.clicked.connect(lambda _, color=button.property("QColor"): self.clicked.emit(color))
        self.custom_color_display.clicked.connect(self.custom_color_display_callback)
        self.custom_color_widget.clicked.connect(self.custom_color_callback)

    def add_color(self, color: QColor):
        btn = QPushButton()
        btn.setStyleSheet(f"background-color: {color.name()}")
        btn.setProperty("QColor", color)
        btn.setFixedSize(self.btn_size_x, self.btn_size_y)
        btn.clicked.connect(lambda _, color=btn.property("QColor"): self.clicked.emit(color))
        self.first_row.addWidget(btn)

    def add_button(self, button: QPushButton):
        button.setFixedSize(QSize(self.btn_size_x, self.btn_size_y))
        self.second_row.addWidget(button)

class LayersManager(QWidget):
    def __init__(self):
        super().__init__()
        self.layers_layout = QVBoxLayout()
        self.layers_layout.setContentsMargins(0, 0, 0, 0)
        self.initUi()
        self.setLayout(self.layers_layout)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def initUi(self):
#        self._create_widgets()
#        self._configure_widgets()
#        self._add_widgets()
        self.setFixedWidth(150)


class VToolBar(QWidget):
    """ Contains widgets related to customizing drawing tool.
    Implements interface for retreiving these user selection """
    def __init__(self):
        super().__init__()
        self.toolbar_layout = QVBoxLayout()
        self.toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.initUi()
        self.setLayout(self.toolbar_layout)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def initUi(self):
        self._create_widgets()
        self._configure_widgets()
        self._add_widgets()
        self.setFixedWidth(150)

    def _create_widgets(self):
        selector_box = QCheckBox("Selector")
        selector_box.setChecked(True)
        self.check_boxes = [QCheckBox(str(Handlers.Freehand.name)),
                            QCheckBox(str(Handlers.Line.name)),
                            QCheckBox(str(Handlers.Textbox.name)),
                            QCheckBox(str(Handlers.Rect.name)),
                            QCheckBox(str(Handlers.Ellipse.name)),
                            QCheckBox(str(Tools.Brush.name)),
                            QCheckBox(str(Tools.Pen.name)),
                            QCheckBox(str(Handlers.Arrow.name)),
                            QCheckBox(str(Handlers.ConnectedLine.name)),
                            selector_box]
        self.tool_checkbox = SingleCheckBox(*self.check_boxes, fallback = selector_box.text())
        self.pen_size_selector_label = QLabel("Pen Width")
        self.pen_size_selector = IntBox()
        self.toggle_menu_button = QPushButton("Toggle Menu")
        self.color_selection = ColorBar()
        self.fill_color_selection = ColorBar()
        self.selection_toggle = QCheckBox("Disable Selection")

    def _configure_widgets(self):
        button = QPushButton()
        pixmap = QPixmap(str(MEDIA_PATH / "NoFillIcon.png"))
        pixmap = pixmap.scaled(20, 20)
        icon = QIcon(pixmap)
        button.setIcon(icon)
        button.clicked.connect(lambda: self.fill_color_selection.clicked.emit(QColor(0, 0, 0, 0)))
        self.fill_color_selection.add_button(button)
        self.color_selection.add_color(QColor("purple"))
        self.fill_color_selection.add_color(QColor("white"))

    def _add_widgets(self):
        self.toolbar_layout.addWidget(self.tool_checkbox)
        self.toolbar_layout.addStretch()
        self.toolbar_layout.addWidget(self.pen_size_selector_label)
        self.toolbar_layout.addWidget(self.pen_size_selector)
        self.toolbar_layout.addWidget(self.toggle_menu_button)
        self.toolbar_layout.addWidget(QLabel("Pen Color"))
        self.toolbar_layout.addWidget(self.color_selection)
        self.toolbar_layout.addWidget(QLabel("Fill Color"))
        self.toolbar_layout.addWidget(self.fill_color_selection)
        self.toolbar_layout.addWidget(self.selection_toggle)

    def connectClickedTool(self, func: Callable): self.tool_checkbox.clicked.connect(func)
    def connectClickedPenWidth(self, func: Callable[[int], None]): self.pen_size_selector.clicked.connect(func)
    def connectToggleMenuButton(self, func: Callable[[], None]): self.toggle_menu_button.clicked.connect(func)
    def connectColorSelection(self, func: Callable[[QColor], None]): self.color_selection.clicked.connect(func)
    def connectFillColorSelection(self, func: Callable[[QColor], None]): self.fill_color_selection.clicked.connect(func)
    def connectToggleSelection(self, func: Callable[[QColor], None]): self.selection_toggle.clicked.connect(func)
    def getClickCallback(self, box_text: str):
        for box in self.check_boxes:
            if box.text() == box_text and not box.isChecked():
                return box.click
        return None

class ExportDialog(QDialog):
    def __init__(self, filename: str, dir: str, dimensions: tuple[int, int]=(789, 558)):
        """
        dimensions: Svg dimensions in pixels
        name: Export file name
        """
        super().__init__()
        self.setWindowTitle("Confirm export attributes")
        self.export_layout = QFormLayout()

        self.setLayout(self.export_layout)
        self.confirm_button = QPushButton("Export", self)
        self.cancel_button = QPushButton("Cancel", self)
        self.container_widget = QWidget(self)
        container_2_widget = QWidget(self)
        container_2_layout = QHBoxLayout(container_2_widget)
        self.dir = QLineEdit(self)
        self.dir_tree = QPushButton("..",self)
        container_2_layout.addWidget(self.dir)
        container_2_layout.addWidget(self.dir_tree)
        self.filename = QLineEdit(self)
        self.width_input = QLineEdit(self)
        self.height_input = QLineEdit(self)
        self.export_type = QComboBox(self)
        self.export_type.addItems(["pdf"])
        self.width_input.setText(str(dimensions[0]))
        self.height_input.setText(str(dimensions[1]))
        self.filename.setText(filename)
        self.dir.setFixedWidth(200)
        self.dir_tree.setFixedWidth(25)
        self.dir.setText(dir)
        self.export_layout.addRow("Filename:", self.filename)
        self.export_layout.addRow("Width:", self.width_input)
        self.export_layout.addRow("Height:", self.height_input)
        self.export_layout.addRow("Export Type: ", self.export_type)
        container_layout = QHBoxLayout(self.container_widget)
        self.export_layout.addRow(container_2_widget)
        self.export_layout.addRow(self.container_widget)
        container_layout.addWidget(self.cancel_button)
        container_layout.addWidget(self.confirm_button)
        self.cancel_button.clicked.connect(self.reject)
        self.confirm_button.clicked.connect(self.accept)
        self.dir_tree.clicked.connect(self.open_directory_dialog)

    def open_directory_dialog(self):
        selected_directory = QFileDialog.getExistingDirectory(
                self, "Selected Directory", self.dir_tree.text()
                )
        if selected_directory:
            self.dir.setText(selected_directory)

    def get_export_info(self) -> dict:
        return {"height": self.height_input.text(), "width": self.width_input.text(),
                "export_type": self.export_type.currentText(), "filename": self.filename.text(),
                "dir": self.dir.text()}

class NewCanvasDialog(QDialog):
    """
    TODO: allow for selection of save location
    """
    def __init__(self, dir: str, default_height: int=561, default_width: int=781):
        super().__init__()
        self.setWindowTitle("New Canvas")
        self.main_layout = QFormLayout()
        self.setLayout(self.main_layout)

        self.filename = QLineEdit(self)
        self.dir = QLineEdit(self)
        self.dir_tree = QPushButton("..",self)
        container_2_widget = QWidget(self)
        container_2_layout = QHBoxLayout()
        container_2_layout.addWidget(self.dir)
        container_2_layout.addWidget(self.dir_tree)
        self.dir.setFixedWidth(200)
        self.dir_tree.setFixedWidth(25)
        self.dir.setText(dir)

        self.confirm_button = QPushButton("Confirm")
        self.cancel_button = QPushButton("Cancel")
        self.width_input = QLineEdit(self)
        self.height_input = QLineEdit(self)


        self.container = QWidget(self)
        self.container_layout = QHBoxLayout()

        self.container_layout.addWidget(self.confirm_button)
        self.container_layout.addWidget(self.cancel_button)

        self.main_layout.addRow("Filename: ", self.filename)
        self.main_layout.addRow(container_2_widget)
        self.main_layout.addRow("Width: ", self.width_input)
        self.main_layout.addRow("Height: ", self.height_input)
        self.main_layout.addWidget(self.container)
        self.container.setLayout(self.container_layout)


        self.confirm_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        container_2_widget.setLayout(container_2_layout)
        # config
        self.dir_tree.clicked.connect(self.open_directory_dialog)
        self.width_input.setText(str(default_width))
        self.height_input.setText(str(default_height))

    def get_options(self):
        return (self.height_input.text(), self.width_input.text(), self.dir.text(),
                self.filename.text())
    def open_directory_dialog(self):
        selected_directory = QFileDialog.getExistingDirectory(
                self, "Selected Directory", self.dir_tree.text()
                )
        if selected_directory:
            self.dir.setText(selected_directory)


class MainWindow(QMainWindow):
    def __init__(self, height: int = 781, width: int = 561):
        """
        _filepath: path to svg file
        user_dir: location where script is launched

        """
        super().__init__()
        self._filepath: None | str = None
        self.user_dir: str | None = None
        self.scene_width = height
        self.scene_height = width
        self.initUi()

        shortcuts = self.set_default_shortcuts()
        for shortcut in shortcuts:
            self.add_shortcut(*shortcut[:-1], **shortcut[-1])

    @property
    def filepath(self) -> str | None:
        return self._filepath

    @filepath.setter
    def filepath(self, filepath):
        self._filepath = filepath
        self.filename_widget.setText(self._filepath)

    @property
    def filename(self):
        if self._filepath is None:
            return UNSAVED_NAME
        return Path(self._filepath).stem

    def initUi(self):
        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout(self.main_widget)
        self.setCentralWidget(self.main_widget)

        self.resize(1100, 600)
        self._create_widgets()
        self._create_tool_bar()
        self._configure_widgets()
        self._add_widgets()

    def _create_tool_bar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        save_action = QAction("Save", self)
        open_action = QAction("Open", self)
        export_action = QAction("Export", self)
        new_action = QAction("New", self)
        self.filename_widget = QLabel(self.filename)
        self.filename_widget.setStyleSheet('font-size: 16pt;')
        spacer = QWidget()
        spacer.setFixedWidth(150)

        toolbar.addAction(save_action)
        toolbar.addAction(new_action)
        toolbar.addAction(open_action)
        toolbar.addAction(export_action)
        toolbar.addWidget(spacer)
        toolbar.addWidget(self.filename_widget)
        save_action.triggered.connect(self.save)
        open_action.triggered.connect(self._load_from_selection)
        new_action.triggered.connect(self.new_canvas)
        export_action.triggered.connect(self.export)

    def new_canvas(self):
        self.save()
        error_msg = ""
        abort = False
        new_dialog = NewCanvasDialog(str(Path().cwd()))
        if new_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        height, width, dir, name= new_dialog.get_options()
        dir = Path(dir)
        valid_int = height.isdigit() and width.isdigit()

        if not valid_int:
            error_msg += f"\nDimensions must be valid integers\nInput height: {height}, width: {width} "
            abort = True
        else:
            height, width = int(height), int(width)
            if not (0 < height < 1200) or not (0 < width < 1200): # 1200 arbitrarly chosen, TODO: pick better upper bound
                error_msg += f"\nInvalid dimensions, valid dimensions are (0, 0) < (height, width) < (1200, 1200)\nInput: {height} {width}"
                abort = True
        if not dir.is_dir():
            error_msg += f"Invalid directory: {str(dir)}"

        if "." not in name: # assuming no '.' in filename, e.g test.file.pdf
            name = name + ".svg"

        output_file = dir / name
        if output_file.is_file():
            msg_box = QMessageBox()
            msg_box.setText(f"The file: {str(output_file)} already exits. Would you like export anyways?")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if msg_box.exec() == QMessageBox.StandardButton.No:
                abort = True

        if len(error_msg) != 0:
            self.error_dialoge(error_msg)

        if not abort:
            print("Ye")
            self.filepath = UNSAVED_NAME
            self.scene_height = height
            self.scene_width = width
            self._build_scene()


    def _create_widgets(self):
        self.graphics_view = GraphicsView()
        self._scene = TexGraphicsScene()
        self.toggle_menu = ToggleMenuWidget()
        self.tool_bar = VToolBar()
        scroll_widget = QWidget()
        scroll_layout = QHBoxLayout(scroll_widget)
        scroll_layout.addWidget(self.graphics_view)
        self.scroll_area = ZoomableScrollArea(scroll_widget)
        self.scroll_area.setWidget(scroll_widget)

    def _build_scene(self):
        self._scene = TexGraphicsScene()
        self._scene.setBackgroundBrush(QBrush(Qt.GlobalColor.white))
        self.graphics_view.setScene(self._scene)
        self._scene.setSceneRect(QRectF(0, 0, self.scene_width, self.scene_height)) # TODO
        self.graphics_view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._scene.update()
        self.graphics_view.update()
        print(self.graphics_view.sceneRect().width(), self.graphics_view.sceneRect().height())
        self._scene.setBackgroundBrush(QBrush(Qt.GlobalColor.black))
        self.graphics_view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.graphics_view.viewport().update()

    def switch_widgets(self):
        self.stacked_widget.setCurrentIndex((self.stacked_widget.currentIndex() + 1) % 2)

    def _configure_widgets(self):
        self.toggle_menu.hide()
        self.tool_bar.connectToggleMenuButton(self.toggleMenuWidget)
        self._scene.setBackgroundBrush(QBrush(Qt.GlobalColor.white))
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setInteractive(True)
        self.graphics_view.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.graphics_view.setScene(self._scene)
        self.graphics_view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.graphics_view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.graphics_view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.IgnoreAspectRatio)

        self._scene.setSceneRect(QRectF(0, 0, self.scene_width, self.scene_height)) # TODO
        self.scroll_area.setWidgetResizable(True)

        self.tool_bar.connectToggleSelection(SelectableRectItem.toggleEnabled)


    def _add_widgets(self):
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(self.toggle_menu)
        self.main_layout.addWidget(self.tool_bar)

    def setController(self, controller: DrawingController):
        """ set controller object and connect relevant signals """
        controller.setSceneView(self.graphics_view)
        self.graphics_view.setController(controller)
        self.tool_bar.connectClickedTool(controller.setHandlerFromName)
        self.tool_bar.connectClickedPenWidth(controller.setPenWidth)
        self.tool_bar.connectColorSelection(controller.setPenColor)
        self.tool_bar.connectFillColorSelection(controller.setFill)

        self.toggle_menu.connectBrushStyle(controller.setBrushStyle)
        self.toggle_menu.connectPenStyle(controller.setPenStyle)

    @property
    def scene(self):
        return self.graphics_view.scene()

    def load_svg_as_svgItem(self, filepath: str):
        """
        adds svg file to scene
        """
        with open(filepath, "rb") as f:
            file_bytes = f.read()
        q_byte_array = QByteArray(file_bytes)
        renderer = StoringQSvgRenderer(q_byte_array)
        item = DeepCopyableSvgItem()
        item.setSharedRenderer(renderer)
        self._scene.addItem(item)

    def error_dialoge(self, error_msg: str):
        msg_box = QMessageBox()
        msg_box.setText(error_msg)
        msg_box.setWindowTitle("Error")
        msg_box.exec()

    def export(self):
        """
        export svg image
        """
        if self.filepath is None or not Path(self.filepath).is_file():
            self.error_dialoge("Svg file must be saved before exporting")
            return

        error_msg = ""
        abort = False
        dialog = ExportDialog(self.filename, str(Path.cwd()) ,dimensions=(self.scene_height, self.scene_width))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        info = dialog.get_export_info()
        height, width, name, export_type, dir = info["height"], info["width"], info["filename"], info["export_type"], Path(info["dir"])
        valid_float = height.isdigit() and width.isdigit()

        if not valid_float:
            error_msg += f"\nDimensions must be valid integers\nInput height: {height}, width: {width} "
        else:
            height, width = int(height), int(width)
            if not (0 < height < 1200) or not (0 < width < 1200): # 1200 arbitrarly chosen, TODO: pick better upper bound
                error_msg += f"\nInvalid dimensions, valid dimensions are (0, 0) < (height, width) < (1200, 1200)\nInput: {height} {width}"

        if not dir.is_dir():
            error_msg += f"Invalid directory: {str(dir)}"

        if "." not in name: # assuming no '.' in filename, e.g test.file.pdf
            name = name + "." + export_type

        output_file = dir / name
        if output_file.is_file():
            msg_box = QMessageBox()
            msg_box.setText(f"The file: {str(output_file)} already exits. Would you like export anyways?")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if msg_box.exec() == QMessageBox.StandardButton.No:
                abort = True

        if len(error_msg) != 0:
            self.error_dialoge(error_msg)

        elif abort is False:
            command = [
                    "inkscape",
                    self.filepath,
                    f"--export-height={height}",
                    f"--export-filename={width}",
                    f"--export-filename={output_file}"
                    ]
            result = subprocess.run(command, capture_output=True)
            if result.returncode != 0:
                self.error_dialoge(str(result.stderr))

    def _load_from_selection(self):
        # TODO empty arg is dir to check... how do I decide this? allow for sys.argv?
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", str(Path().cwd()), "SVG Files (*.svg)")
        if Path(file_path).is_file():
            self.load_svg_as_svgItem(file_path)

    def closeEvent(self, event: QCloseEvent): #type: ignore
        if self.filename != UNSAVED_NAME:
            self.save()
            return

        if isinstance(event, ShortcutCloseEvent):
            # allow for some default directory? maybe in QApplication([sys.argv])
            home_dir = Path().home()
            num, attempts = 0, 0
            while (home_dir / f"veditor_unamed_{num}").is_file() and attempts < 30:
                num += 1
            # figure out a better way of doing this
            if attempts == 30:
                event.ignore()
                return

            self.filepath = str(home_dir / f"veditor_unamed{num}")
            self.save()

        reply = QMessageBox.question(self, "Confirm Close", "Do you want to save before closing?",
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Save:
            return_code = self.save()
            if return_code == 0:
                event.accept()
            else:
                event.ignore()
        elif reply == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()

    def save(self) -> int:
        """ Save svg """
        error_code = 0
        if self._filepath is None:
            self._filepath, _ = QFileDialog.getSaveFileName(self, "Save File", str(Path().cwd()), "SVG Files (*.svg)")

        if not isinstance(self._filepath, str) or self._filepath == "": # TODO fix this. We want to know it is possible to write to self._filepath
            error_msg = f"error while saving: {self._filepath}"
            self.error_dialoge(error_msg)
            error_code = 1
        else:
            scene_to_svg(self._scene, self._filepath)
        self.filename_widget.setText(self.filepath)
        return error_code

    def open_with_svg(self, filepath: str, user_dir: str | None = None):
        """ Loads svg and sets filename to svg name. Implements 'editing' functionality, the original svg will
        overidden when saved"""
        self.user_dir = user_dir if user_dir is not None else str(Path().cwd())
        self.load_svg(filepath)
        self.filepath = filepath

    def load_svg(self, file_path: str):
        """ TODO """
        builder = SvgBuilder(Path(file_path))
        svg_items = builder.build_scene_items()
        cont = self.graphics_view.controller()
        if cont:
            handler = cont.handler
            signal = cont.handler_signal
        else:
            signal = None
            handler = None

        for svg_item in svg_items:
            #svg_item.setFlag(QGraphicsSvgItem.GraphicsItemFlag.ItemClipsToShape, True) # Make background transparent
            if signal:
                selectable_item = SelectableRectItem(svg_item, signal) # TODO
            else:
                selectable_item = SelectableRectItem(svg_item) # TODO
            self._scene.addItem(selectable_item)

        # hack to 'refresh' signals.. without this loaded graphic won't be selectable untill selector button is pressed
        if handler and signal:
            signal.emit(handler.__class__.__name__)

    def toggleMenuWidget(self):
        if self.toggle_menu.isVisible():
            self.toggle_menu.hide()
            self.resize(self.width() - self.toggle_menu.width(), self.height())
        else:
            self.resize(self.width() + self.toggle_menu.width(), self.height())
            self.toggle_menu.show()

    def add_shortcut(self, key: Qt.Key, callback, name, modifiers=Qt.KeyboardModifier.NoModifier):
        action = QAction(name, self)
        action.setShortcut(QKeySequence(QKeyCombination(modifiers, key)))
        action.triggered.connect(callback)
        self.addAction(action)

    def get_cursor_pos(self) -> QPointF:
        global_pos = QCursor().pos()
        view_pos = self.graphics_view.mapFromGlobal(global_pos)
        scene_pos = self.graphics_view.mapToScene(view_pos)
        return QPointF(scene_pos.x(), scene_pos.y())

    def get_handeler_signal(self) -> pyqtBoundSignal | None:
        signal = None
        cont = self.graphics_view.controller()
        if cont:
            signal = cont.handler_signal
        return signal

    def set_default_shortcuts(self):
        def call_click(button_name):
            func = self.tool_bar.getClickCallback(button_name)
            if callable(func):
                func()
            return
        shortcuts = [
                (Qt.Key.Key_F, lambda: call_click(str(Handlers.Freehand.name)), "Freehand", {"modifiers":Qt.KeyboardModifier.MetaModifier}),
                (Qt.Key.Key_L, lambda: call_click(str(Handlers.Line.name)), "Line", {"modifiers":Qt.KeyboardModifier.MetaModifier}),
                (Qt.Key.Key_T, lambda: call_click(str(Handlers.Textbox.name)), "Textbox", {"modifiers":Qt.KeyboardModifier.MetaModifier}),
                (Qt.Key.Key_R, lambda: call_click(str(Handlers.Rect.name)), "Rect", {"modifiers":Qt.KeyboardModifier.MetaModifier}),
                (Qt.Key.Key_B, lambda: call_click(str(Tools.Brush.name)), "Brush", {"modifiers":Qt.KeyboardModifier.MetaModifier}),
                (Qt.Key.Key_P, lambda: call_click(str(Tools.Pen.name)), "Pen", {"modifiers":Qt.KeyboardModifier.MetaModifier}),
                (Qt.Key.Key_S, lambda: call_click(str(Handlers.Selector.name)), "Selector", {"modifiers":Qt.KeyboardModifier.MetaModifier}),
                (Qt.Key.Key_C, lambda: self._scene.compile_latex(self.get_handeler_signal()), "Compile latex", {"modifiers": Qt.KeyboardModifier.MetaModifier}),
                (Qt.Key.Key_N, lambda: SelectableRectItem.cycle(self.get_cursor_pos()), "Cycle selectable items under curosr", {"modifiers": Qt.KeyboardModifier.MetaModifier}),
                (Qt.Key.Key_C, self._scene.copy_to_clipboard, "Copy item", {"modifiers": Qt.KeyboardModifier.ControlModifier}),
                (Qt.Key.Key_V, lambda: self._scene.paste_from_clipboard(self.get_cursor_pos()), "Paste item", {"modifiers": Qt.KeyboardModifier.ControlModifier}),
                ]
        return shortcuts
