from collections.abc import Callable
from collections import deque
from PyQt6.QtGui import QKeyEvent, QCloseEvent
from PyQt6.QtWidgets import QApplication, QGraphicsItem, QGraphicsScene, QGraphicsTextItem
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from ..utils import KeyCodes, Handlers
import logging

logger = logging.getLogger(__name__)

class ShortcutCloseEvent(QCloseEvent):
    def __init__(self):
        super().__init__()

#class Modes(Enum):
#    Normal = "normal"
#    Insert = "insert"
#    Close = "close"

class Shortcut:
    def __init__(self,
                 key: KeyCodes,
                 callback: Callable,
                 modifiers: Qt.KeyboardModifier | None = None,
                 name: str | None = None,
                 description: str | None = None,
                 builtin: bool = False
                 ) -> None:
        self.key: int = key.value
        self.modifiers: Qt.KeyboardModifier = modifiers if modifiers is not None else Qt.KeyboardModifier.NoModifier
        self.name = name if name is not None else f"{self.modifiers} + {self.key}"
        self.description = description
        self.callback = callback
        self.builtin = builtin
        self._enabled = True

    def execute(self):
        self.callback()

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def triggered(self, key: int, modifiers: Qt.KeyboardModifier):
        return key == self.key and (modifiers & self.modifiers) == modifiers


class ShortcutManager:
    def __init__(self, scene: QGraphicsScene, close_callback: Callable, cache_max = 10):
        self._close_callback = lambda: close_callback(ShortcutCloseEvent())
        self.shortcuts: list[Shortcut] = []
        self.scene = scene
        self.cache = deque()
        self.cache_max = cache_max
        self._set_sane_shortcuts()
        self.listeners = []

    def keyPress(self, event: QKeyEvent):
        print(f"Event modifiers: {event.modifiers()}")
        print(f"Key code: {event.key()}")
        for shortcut in self.shortcuts:
            if shortcut.triggered(event.key(), event.modifiers()):
                logger.info(f"Execting shortcut: {shortcut.name}")
                shortcut.execute()

    def compile_tex(self):
        # figure out how to import without going circular
        self.scene.compile_latex()

    def _set_sane_shortcuts(self):
        shortcuts = [
#                Shortcut(KeyCodes.Key_i, self.insert_mode, Modes.Normal, name="set insert mode", builtin=True),
#                Shortcut(KeyCodes.Key_esc, self.normal_mode, Modes.Insert, name="set normal mode", builtin=True),
                Shortcut(KeyCodes.Key_Delete, self.delete_from_scene, name="delete from scene", builtin=True),
                Shortcut(KeyCodes.Key_u, self.add_from_cache, name="Undo delete", modifiers=Qt.KeyboardModifier.ShiftModifier, builtin=True),
                Shortcut(KeyCodes.Key_c, self._close_callback, name="Close Application", modifiers=Qt.KeyboardModifier.ControlModifier, builtin=True),
                Shortcut(KeyCodes.Key_c, self.compile_tex, name="Compile embeded latex", modifiers=Qt.KeyboardModifier.ShiftModifier, builtin=True),
#                Shortcut(KeyCodes.Key_f, lambda: self.controller.setFromName(Handlers.Freehand.value), name="Set freehand tool", modifiers=Qt.KeyboardModifier.ShiftModifier, builtin=True),
#                Shortcut(KeyCodes.Key_l, lambda: self.controller.setFromName(Handlers.Line.value), name="Set freehand tool", modifiers=Qt.KeyboardModifier.ShiftModifier, builtin=True),
#                Shortcut(KeyCodes.Key_t, lambda: self.controller.setFromName(Handlers.Textbox.value), name="Set freehand tool", modifiers=Qt.KeyboardModifier.ShiftModifier, builtin=True),
#                Shortcut(KeyCodes.Key_s, lambda: self.controller.setFromName(Handlers.Selector.value), name="Set freehand tool", modifiers=Qt.KeyboardModifier.ShiftModifier, builtin=True),
                ]
        self.add_shortcut(shortcuts)

    def add_shortcut(self, shortcut: Shortcut | list[Shortcut]):
        if isinstance(shortcut, Shortcut):
            shortcut.callback = shortcut.callback if shortcut.builtin else lambda: shortcut.callback(self)
            self.shortcuts.append(shortcut)
        else:
            self.shortcuts.extend(shortcut)

    def delete_from_scene(self):
        focus_item = self.scene.focusItem()
        selected_items = self.scene.selectedItems()
        if not isinstance(focus_item, QGraphicsTextItem):
            for item in selected_items:
                self.scene.removeItem(item)
                self.add_to_cache(item)

    def add_from_cache(self):
        if len(self.cache) == 0:
            return
        item = self.cache.pop()
        self.scene.addItem(item)

    def add_to_cache(self, item: QGraphicsItem):
        if len(self.cache) > self.cache_max:
            self.cache.popleft()
        self.cache.append(item)

