"""
输入监听模块

负责监听键盘和鼠标事件，检测组合键状态

@author hqzqaq
@since 2026-03-30 19:49
@version 1.0
"""

import ctypes
import logging
import time
from typing import Callable

from pynput import keyboard, mouse
from pynput.keyboard import Key
from pynput.mouse import Button

logger = logging.getLogger(__name__)

_BUTTON_MAP: dict[str, Button] = {
    "forward": Button.x2,
    "backward": Button.x1,
}

_BUTTON_REVERSE_MAP: dict[Button, str] = {v: k for k, v in _BUTTON_MAP.items()}

_CAPS_LOCK_IGNORE_SECONDS = 0.3


class ShortcutMatcher:
    """快捷键匹配器，管理修饰键+鼠标按键到枪械名称的映射"""

    def __init__(self, shortcuts: list[dict[str, str]]) -> None:
        self._gun_map: dict[tuple[str, str], str] = {}
        self._build_map(shortcuts)

    def _build_map(self, shortcuts: list[dict[str, str]]) -> None:
        self._gun_map = {
            (s["modifier"], s["mouse_button"]): s["text"] for s in shortcuts
        }

    def update_shortcuts(self, shortcuts: list[dict[str, str]]) -> None:
        self._build_map(shortcuts)

    def match(self, modifier: str, button: Button) -> str | None:
        mouse_btn = _BUTTON_REVERSE_MAP.get(button)
        if mouse_btn is None:
            return None
        return self._gun_map.get((modifier, mouse_btn))

    @property
    def first_gun_name(self) -> str:
        return next(iter(self._gun_map.values()), "UMP5")


class InputListener:
    """输入监听器，监听键盘和鼠标组合键"""

    MOUSE_FORWARD = Button.x2
    MOUSE_BACKWARD = Button.x1

    def __init__(
        self,
        callback: Callable[[str], None],
        lock_callback: Callable[[bool], None] | None = None,
        shortcuts: list[dict[str, str]] | None = None,
    ) -> None:
        self.callback = callback
        self.lock_callback = lock_callback
        self.keyboard_listener: keyboard.Listener | None = None
        self.mouse_listener: mouse.Listener | None = None

        self.alt_pressed = False
        self.ctrl_pressed = False
        self.shift_pressed = False

        self.current_text: str = "无"
        self.aim_mode_enabled = False
        self.locked = False
        self._ignore_caps_lock_until: float = 0.0

        self.matcher = ShortcutMatcher(shortcuts or [])
        self.last_gun_name: str = self.matcher.first_gun_name

    def update_shortcuts(self, shortcuts: list[dict[str, str]]) -> None:
        self.matcher.update_shortcuts(shortcuts)

    def is_caps_lock_on(self) -> bool:
        return ctypes.windll.user32.GetKeyState(0x14) & 0xFFFF != 0

    def _turn_off_caps_lock(self) -> None:
        if self.is_caps_lock_on():
            self._ignore_caps_lock_until = time.monotonic() + _CAPS_LOCK_IGNORE_SECONDS
            ctypes.windll.user32.keybd_event(0x14, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x14, 0, 2, 0)

    def _cancel_aim_mode(self) -> None:
        if self.current_text != "无":
            self.last_gun_name = self.current_text
        self.aim_mode_enabled = False
        self.current_text = "无"
        self.callback(self.current_text)

    def _toggle_lock(self) -> None:
        self.locked = not self.locked
        if self.lock_callback:
            self.lock_callback(self.locked)

    def is_locked(self) -> bool:
        return self.locked

    def _on_key_press(self, key: Key | keyboard.KeyCode | None) -> None:
        try:
            if key == Key.alt_l or key == Key.alt:
                self.alt_pressed = True
                if self.ctrl_pressed:
                    self._toggle_lock()
            elif key == Key.ctrl_l or key == Key.ctrl:
                self.ctrl_pressed = True
                if self.alt_pressed:
                    self._toggle_lock()
            elif key == Key.shift_l or key == Key.shift:
                self.shift_pressed = True
            elif key == Key.caps_lock:
                if time.monotonic() < self._ignore_caps_lock_until:
                    return
                if self.current_text == "无":
                    self.aim_mode_enabled = True
                    self.current_text = self.last_gun_name
                else:
                    self._cancel_aim_mode()
                self.callback(self.current_text)
            elif key == Key.tab:
                self._cancel_aim_mode()
                self._turn_off_caps_lock()
            elif hasattr(key, "char") and key.char:
                if key.char.lower() == "g" or key.char in ("3", "4", "5"):
                    self._cancel_aim_mode()
                    self._turn_off_caps_lock()
        except AttributeError:
            pass

    def _on_key_release(self, key: Key | keyboard.KeyCode | None) -> None:
        try:
            if key == Key.alt_l or key == Key.alt:
                self.alt_pressed = False
            elif key == Key.ctrl_l or key == Key.ctrl:
                self.ctrl_pressed = False
            elif key == Key.shift_l or key == Key.shift:
                self.shift_pressed = False
        except AttributeError:
            pass

    def _on_mouse_click(self, x: int, y: int, button: Button, pressed: bool) -> None:
        if not pressed:
            return

        if not self.is_caps_lock_on():
            self.aim_mode_enabled = False
            self.current_text = "无"
            self.callback(self.current_text)
            return

        if self.locked:
            return

        gun_name = self._get_gun_name(button)
        if gun_name:
            self.current_text = gun_name
            self.callback(self.current_text)

    def _get_gun_name(self, button: Button) -> str | None:
        modifier_count = sum([self.alt_pressed, self.ctrl_pressed, self.shift_pressed])
        if modifier_count != 1:
            return None

        if self.alt_pressed:
            modifier = "alt"
        elif self.ctrl_pressed:
            modifier = "ctrl"
        elif self.shift_pressed:
            modifier = "shift"
        else:
            return None

        return self.matcher.match(modifier, button)

    def start(self) -> None:
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self.mouse_listener = mouse.Listener(on_click=self._on_mouse_click)

        self.keyboard_listener.start()
        self.mouse_listener.start()
        logger.info("输入监听器已启动")

    def stop(self) -> None:
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        logger.info("输入监听器已停止")

    def is_running(self) -> bool:
        return (
            self.keyboard_listener is not None
            and self.keyboard_listener.is_alive()
            and self.mouse_listener is not None
            and self.mouse_listener.is_alive()
        )
