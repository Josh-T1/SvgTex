from collections.abc import Callable
from copy import deepcopy
from PyQt6.QtGui import QAction, QBrush, QCloseEvent, QColor, QCursor, QGuiApplication, QIcon, QKeyEvent, QKeySequence, QMouseEvent, QPen, QPainter, QPixmap, QTransform
from PyQt6.QtCore import QByteArray, QKeyCombination, QPointF, QRect, Qt, QRectF, pyqtSignal, QEvent, QSize
from PyQt6.QtSvg import QSvgGenerator, QSvgRenderer
from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget
from PyQt6.QtWidgets import (QApplication, QCheckBox, QColorDialog, QFileDialog, QGestureEvent, QGraphicsItem, QGraphicsPathItem, QGraphicsSceneMouseEvent, QLabel, QMessageBox, QPinchGesture, QPushButton, QScrollArea, QSizePolicy, QToolBar, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView,
                             QGraphicsScene, QGraphicsLineItem, QMainWindow, QGraphicsTextItem, QGraphicsRectItem)
from ..drawing.tools import NullDrawingHandler, Textbox
from ..control.drawing_controller import DrawingController
from .graphics_items import DeepCopyableSvgItem, SelectableRectItem, StoringQSvgRenderer, Textbox
from pathlib import Path
from functools import partial
from collections import deque
import logging
from ..control.shortcut_manager import Shortcut, ShortcutCloseEvent, ShortcutManager
from ..svg.load_svg import scene_to_svg as scene_to_svg_test, SvgGraphicsFactory
from ..utils import tex2svg, text_is_latex, Handlers
logger = logging.getLogger(__name__)

UNSAVED_NAME = "No Name **"
MEDIA_PATH = Path(__file__).parent.parent / "media"

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

        self.initUi()
        self.setLayout(self.toggle_menu_layout)
        self.setFixedWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def initUi(self):
        self._create_widgets()
    def _create_widgets(self):
        self.label = QLabel("Item 1")
    def _add_widgets(self):
        self.toggle_menu_layout.addWidget(self.label)


class GraphicsView(QGraphicsView):
    def __init__(self, controller: None | DrawingController = None):
        super().__init__()
        self._controller =  controller
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

    def setShortcutManager(self, shortcut_manager: ShortcutManager):
        self.shortcut_manager = shortcut_manager


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
            self.clipboard_item.setPos(self.clipboard_item.scenePos() + offset)
#            text = SelectableRectItem(Textbox(QRectF(0, 0, 100, 100)), select_signal=self.clipboard_item.select_signal)
#            self.addItem(text)
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
                        del SelectableRectItem.selectableItems[item._id]


        super().keyPressEvent(event)

    def add_to_cache(self, item: QGraphicsItem):
        if len(self.cache) > self.cache_max:
            self.cache.popleft()
        self.cache.append(item)

    def compile_latex(self):
        # TODO
        print("attempting to compile")
        for item in self.items():
            parent = item.parentItem()
            if not isinstance(item, Textbox) or not isinstance(parent, SelectableRectItem):
                continue

            res_item = self.attempt_compile(item.text())

            if res_item is not None:
                global_pos = item.mapToScene(item.boundingRect().topLeft())# - parent.pos()
                res_item.setTransform(QTransform().translate(global_pos.x(), global_pos.y()))
                parent.item = res_item
                # not sure this is necessary
                self.removeItem(item)
                item.setParentItem(None)
                del item

    def attempt_compile(self, text):
        if not text_is_latex(text):
            return
        svg_bytes = tex2svg(text)
        if not svg_bytes:
            return
        svg_data = QByteArray(svg_bytes.read())
        renderer = StoringQSvgRenderer(svg_data)
        item = DeepCopyableSvgItem(renderer)
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
#        self.toolbar_layout.setSpacing()

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
                            QCheckBox(str(Handlers.Fill.name)),
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

    def connectClickedTool(self, func: Callable):
        self.tool_checkbox.clicked.connect(func)

    def connectClickedPenWidth(self, func: Callable[[int], None]):
        self.pen_size_selector.clicked.connect(func)

    def connectToggleMenuButton(self, func: Callable[[], None]):
        self.toggle_menu_button.clicked.connect(func)

    def connectColorSelection(self, func: Callable[[QColor], None]):
        self.color_selection.clicked.connect(func)

    def connectFillColorSelection(self, func: Callable[[QColor], None]):
        self.fill_color_selection.clicked.connect(func)

    def connectToggleSelection(self, func: Callable[[QColor], None]):
        self.selection_toggle.clicked.connect(func)

    def getClickCallback(self, box_text: str):
        for box in self.check_boxes:
            if box.text() == box_text and not box.isChecked():
                return box.click
        return None


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._filepath = None
        self.scene_default_width = 1052 * 0.75
        self.scene_default_height = 744 * 0.75
        self.initUi()

        shortcuts = self.set_default_shortcuts()
        for shortcut in shortcuts:
            self.add_shortcut(*shortcut[:-1], **shortcut[-1])

    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, filepath):
        self._filepath = filepath
        self.filename_widget.setText(self._filepath)

    @property
    def filename(self):
        if self._filepath is None:
            return UNSAVED_NAME
        return Path(self._filepath).name

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
        self.filename_widget = QLabel(self.filename)
#        self.mode_label = ModeView()
        self.filename_widget.setStyleSheet('font-size: 16pt;')
        spacer = QWidget()
        spacer.setFixedWidth(200)

        toolbar.addAction(save_action)
        toolbar.addAction(open_action)
        toolbar.addWidget(spacer)
        toolbar.addWidget(self.filename_widget)
        save_action.triggered.connect(self.save_as_svg)
        open_action.triggered.connect(self._load_from_selection)


    def _create_widgets(self):
        self.graphics_view = GraphicsView()
        self._scene = TexGraphicsScene()
        self.tool_bar = VToolBar()
        self.toggle_menu = ToggleMenuWidget()
        scroll_widget = QWidget()
        scroll_layout = QHBoxLayout(scroll_widget)
        scroll_layout.addWidget(self.graphics_view)
        self.scroll_area = ZoomableScrollArea(scroll_widget)
        self.scroll_area.setWidget(scroll_widget)


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

        self._scene.setSceneRect(QRectF(0, 0, self.scene_default_width, self.scene_default_height)) # TODO
        self.scroll_area.setWidgetResizable(True)

        self.tool_bar.connectToggleSelection(SelectableRectItem.toggleEnabled)

    def _add_widgets(self):
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(self.tool_bar)
        self.main_layout.addWidget(self.toggle_menu)

    def setController(self, controller: DrawingController):
        """ set controller object and connect relevant signals """
        controller.setSceneView(self.graphics_view)
        self.graphics_view.setController(controller)
        self.tool_bar.connectClickedTool(controller.setHandlerFromName)
        self.tool_bar.connectClickedPenWidth(controller.setPenWidth)
        self.tool_bar.connectColorSelection(controller.setPenColor)
        self.tool_bar.connectFillColorSelection(controller.setFill)


    @property
    def scene(self):
        return self.graphics_view.scene()

    def _load_from_selection(self):
        # TODO empty arg is dir to check... how do I decide this? allow for sys.argv?
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "SVG Files (*.svg)")
        if Path(file_path).is_file():
            self.load_svg(file_path)

    def scene_to_svg(self, file_path):
        """ Return 0 if not error else 1
        TODO: Re write this"""
        viewport = self.graphics_view.viewport()
        if viewport is None: return
#        if file_path is None or viewport is None:
#            logger.error(f"Invalid file_path: {file_path}")
#            return 1
#        svg_gen = QSvgGenerator()
#        svg_gen.setFileName(file_path)
#        svg_gen.setSize(viewport.size())
#        svg_gen.setViewBox(self.graphics_view.sceneRect())
#        painter = QPainter(svg_gen)
#        self._scene.render(painter)
#        painter.end()
        scene_to_svg_test(self._scene, file_path)
        return 0

    def closeEvent(self, event: QCloseEvent): #type: ignore
        """ TODO: Make this better """
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
            return

        reply = QMessageBox.question(self, "Confirm Close", "Do you want to save before closing?",
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Save:
            return_code = self.save_as_svg()
            if return_code == 0:
                event.accept()
            else:
                event.ignore()
        elif reply == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()

    def save_as_svg(self):
#        options = QFileDialog.options
        if self._filepath is None:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "SVG Files (*.svg)")
        else:
            file_path = self._filepath

        return_code = self.scene_to_svg(file_path)
        if return_code == 1:
            display_name = f"error while saving: {file_path}" if return_code == 1 else file_path.split("/")[-1]
            self.filename_widget.setText(display_name)
        else:
            self.filepath = file_path
        return return_code

    def save(self):
        """ Save svg """
        self.scene_to_svg(self._filepath)

    def build_svg(self):
        builder = SvgGraphicsFactory(self._scene)
        builder.build(self._filepath)

    def open_with_svg(self, filepath: str):
        """ Loads svg and sets filename to svg name. Implements 'editing' functionality, the original svg will
        overidden when saved"""
        self.load_svg(filepath, scale=1)
        self.filepath = filepath

    def load_svg(self, file_path: str, scale=0.5):
        """ TODO """
        svg_item = DeepCopyableSvgItem(file_path)
        svg_item.setFlag(QGraphicsSvgItem.GraphicsItemFlag.ItemClipsToShape, True) # Make background transparent
        cont = self.graphics_view.controller()
        if cont:
            handler = cont.handler
            signal = cont.handler_signal
        else:
            signal = None
            handler = None
        selectable_item = SelectableRectItem(svg_item, signal) # TODO
        #selectable_item.setScale(scale) # TODO determine scale based on width relative to window width, height width
        self._scene.addItem(selectable_item)
        # hack to 'refresh' signals.. without this loaded graphic won't be selectable untill selector button is pressed again
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

    def set_default_shortcuts(self):
        def call_click(button_name):
            func = self.tool_bar.getClickCallback(button_name)
            if callable(func):
                func()
            return
        shortcuts = [
                (Qt.Key.Key_F, lambda: call_click(str(Handlers.Freehand.name)), "Freehand", {"modifiers":Qt.KeyboardModifier.ShiftModifier}),
                (Qt.Key.Key_L, lambda: call_click(str(Handlers.Line.name)), "Line", {"modifiers":Qt.KeyboardModifier.ShiftModifier}),
                (Qt.Key.Key_T, lambda: call_click(str(Handlers.Textbox.name)), "Textbox", {"modifiers":Qt.KeyboardModifier.ShiftModifier}),
                (Qt.Key.Key_R, lambda: call_click(str(Handlers.Rect.name)), "Rect", {"modifiers":Qt.KeyboardModifier.ShiftModifier}),
                (Qt.Key.Key_P, lambda: call_click(str(Handlers.Fill.name)), "Pain", {"modifiers":Qt.KeyboardModifier.ShiftModifier}),
                (Qt.Key.Key_S, lambda: call_click(str(Handlers.Selector.name)), "Selector", {"modifiers":Qt.KeyboardModifier.ShiftModifier}),
                (Qt.Key.Key_C, lambda: self._scene.compile_latex(), "Compile latex", {"modifiers": Qt.KeyboardModifier.ShiftModifier}),
                (Qt.Key.Key_N, lambda: SelectableRectItem.cycle(self.get_cursor_pos()), "Cycle selectable items under curosr", {"modifiers": Qt.KeyboardModifier.MetaModifier}),
                (Qt.Key.Key_C, self._scene.copy_to_clipboard, "Copy item", {"modifiers": Qt.KeyboardModifier.ControlModifier}),
                (Qt.Key.Key_V, lambda: self._scene.paste_from_clipboard(self.get_cursor_pos()), "Paste item", {"modifiers": Qt.KeyboardModifier.ControlModifier}),
                ]
        return shortcuts
