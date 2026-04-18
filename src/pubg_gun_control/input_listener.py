"""
输入监听模块

负责监听键盘和鼠标事件，检测组合键状态

@author hqzqaq
@since 2026-03-30 19:49
@version 1.0
"""

import ctypes
from typing import Callable, Optional
from pynput import keyboard, mouse
from pynput.keyboard import Key
from pynput.mouse import Button


class InputListener:
    """输入监听器，监听键盘和鼠标组合键"""

    MOUSE_FORWARD = Button.x2
    MOUSE_BACKWARD = Button.x1
    DEFAULT_GUN = "UMP5"

    _BUTTON_MAP: dict[str, Button] = {
        "forward": Button.x2,
        "backward": Button.x1,
    }

    def __init__(self, callback: Callable[[str], None], lock_callback: Optional[Callable[[bool], None]] = None, shortcuts: Optional[list[dict[str, str]]] = None):
        """
        初始化输入监听器

        Args:
            callback: 当检测到有效组合键时的回调函数，参数为要显示的枪械名称
            lock_callback: 锁定状态变化时的回调函数，参数为锁定状态
            shortcuts: 快捷键配置列表，每项包含 modifier、mouse_button、text
        """
        self.callback = callback
        self.lock_callback = lock_callback
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self.mouse_listener: Optional[mouse.Listener] = None

        self.alt_pressed = False
        self.ctrl_pressed = False
        self.shift_pressed = False

        self.current_text: str = "无"
        self.aim_mode_enabled: bool = False
        self.last_gun_name: str = self.DEFAULT_GUN
        self._turning_off_caps_lock = False
        self.locked: bool = False

        self._gun_map: dict[tuple[str, str], str] = {}
        self._build_gun_map(shortcuts)

    def _build_gun_map(self, shortcuts: Optional[list[dict[str, str]]]) -> None:
        if not shortcuts:
            from pubg_gun_control.config_manager import get_default_config
            shortcuts = get_default_config()
        self._gun_map = {
            (s["modifier"], s["mouse_button"]): s["text"] for s in shortcuts
        }
        if self._gun_map:
            first_text = next(iter(self._gun_map.values()))
            self.last_gun_name = first_text
            self.DEFAULT_GUN = first_text

    def update_shortcuts(self, shortcuts: list[dict[str, str]]) -> None:
        self._build_gun_map(shortcuts)

    def is_caps_lock_on(self) -> bool:
        """
        检测大写锁定是否开启

        Returns:
            True 如果大写锁定开启，否则 False
        """
        return ctypes.windll.user32.GetKeyState(0x14) & 0xFFFF != 0

    def _turn_off_caps_lock(self):
        """关闭大写锁定"""
        if self.is_caps_lock_on():
            self._turning_off_caps_lock = True
            # 模拟按下并释放 Caps Lock 键
            ctypes.windll.user32.keybd_event(0x14, 0, 0, 0)  # 按下
            ctypes.windll.user32.keybd_event(0x14, 0, 2, 0)  # 释放
            self._turning_off_caps_lock = False

    def _cancel_aim_mode(self):
        """取消压枪模式"""
        if self.current_text != "无":
            self.last_gun_name = self.current_text
        self.aim_mode_enabled = False
        self.current_text = "无"
        self.callback(self.current_text)

    def _toggle_lock(self):
        """切换锁定状态"""
        self.locked = not self.locked
        if self.lock_callback:
            self.lock_callback(self.locked)

    def is_locked(self) -> bool:
        """
        获取当前锁定状态

        Returns:
            True 如果处于锁定状态，否则 False
        """
        return self.locked

    def _on_key_press(self, key):
        """键盘按下事件处理"""
        try:
            if key == Key.alt_l or key == Key.alt:
                self.alt_pressed = True
                # 检测 Ctrl + Alt 组合键
                if self.ctrl_pressed:
                    self._toggle_lock()
            elif key == Key.ctrl_l or key == Key.ctrl:
                self.ctrl_pressed = True
                # 检测 Ctrl + Alt 组合键
                if self.alt_pressed:
                    self._toggle_lock()
            elif key == Key.shift_l or key == Key.shift:
                self.shift_pressed = True
            elif key == Key.caps_lock:
                # 如果是通过程序模拟按键关闭大写锁定，则不处理
                if self._turning_off_caps_lock:
                    return
                # 检测大写锁定键
                # 如果当前是"无"，开启压枪模式（显示上次使用的枪械）
                # 如果当前是枪械名称，关闭压枪模式
                if self.current_text == "无":
                    self.aim_mode_enabled = True
                    self.current_text = self.last_gun_name
                else:
                    self._cancel_aim_mode()
                    self._turn_off_caps_lock()
                self.callback(self.current_text)
            elif key == Key.tab:
                # Tab键取消压枪模式
                self._cancel_aim_mode()
                self._turn_off_caps_lock()
            elif hasattr(key, 'char') and key.char:
                # 检测 G 键或数字键 3、4、5
                if key.char.lower() == 'g' or key.char in ('3', '4', '5'):
                    # 取消压枪模式，显示"无"
                    self._cancel_aim_mode()
                    self._turn_off_caps_lock()
        except AttributeError:
            pass

    def _on_key_release(self, key):
        """键盘释放事件处理"""
        try:
            if key == Key.alt_l or key == Key.alt:
                self.alt_pressed = False
            elif key == Key.ctrl_l or key == Key.ctrl:
                self.ctrl_pressed = False
            elif key == Key.shift_l or key == Key.shift:
                self.shift_pressed = False
        except AttributeError:
            pass

    def _on_mouse_click(self, x: int, y: int, button: Button, pressed: bool):
        """
        鼠标点击事件处理

        Args:
            x: 鼠标X坐标
            y: 鼠标Y坐标
            button: 鼠标按钮
            pressed: 是否按下
        """
        if not pressed:
            return

        # 检查大写锁定状态
        if not self.is_caps_lock_on():
            self.aim_mode_enabled = False
            self.current_text = "无"
            self.callback(self.current_text)
            return

        # 如果处于锁定状态，忽略枪械切换
        if self.locked:
            return

        # 检测组合键并触发回调
        gun_name = self._get_gun_name(button)
        if gun_name:
            self.current_text = gun_name
            self.callback(self.current_text)

    def _get_gun_name(self, button: Button) -> Optional[str]:
        modifier_count = sum([self.alt_pressed, self.ctrl_pressed, self.shift_pressed])
        if modifier_count != 1:
            return None

        modifier = ""
        if self.alt_pressed:
            modifier = "alt"
        elif self.ctrl_pressed:
            modifier = "ctrl"
        elif self.shift_pressed:
            modifier = "shift"

        mouse_btn = None
        for name, btn in self._BUTTON_MAP.items():
            if button == btn:
                mouse_btn = name
                break

        if mouse_btn is None:
            return None

        return self._gun_map.get((modifier, mouse_btn))

    def start(self):
        """启动监听器"""
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click
        )

        self.keyboard_listener.start()
        self.mouse_listener.start()

    def stop(self):
        """停止监听器"""
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()

    def is_running(self) -> bool:
        """检查监听器是否正在运行"""
        return (
            self.keyboard_listener is not None
            and self.keyboard_listener.is_alive()
            and self.mouse_listener is not None
            and self.mouse_listener.is_alive()
        )
