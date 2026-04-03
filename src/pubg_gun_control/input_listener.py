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

    # 鼠标侧键映射
    MOUSE_FORWARD = Button.x2  # 前进侧键
    MOUSE_BACKWARD = Button.x1  # 后退侧键

    # 默认压枪枪械
    DEFAULT_GUN = "UMP5"

    def __init__(self, callback: Callable[[str], None]):
        """
        初始化输入监听器

        Args:
            callback: 当检测到有效组合键时的回调函数，参数为要显示的枪械名称
        """
        self.callback = callback
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self.mouse_listener: Optional[mouse.Listener] = None

        # 修饰键状态
        self.alt_pressed = False
        self.ctrl_pressed = False
        self.shift_pressed = False

        # 当前显示的文本
        self.current_text: str = "无"

        # 压枪模式是否开启
        self.aim_mode_enabled: bool = False

        # 上次使用的枪械名称（用于压枪模式恢复）
        self.last_gun_name: str = self.DEFAULT_GUN

        # 标志：是否正在通过程序关闭大写锁定
        self._turning_off_caps_lock = False

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

    def _on_key_press(self, key):
        """键盘按下事件处理"""
        try:
            if key == Key.alt_l or key == Key.alt:
                self.alt_pressed = True
            elif key == Key.ctrl_l or key == Key.ctrl:
                self.ctrl_pressed = True
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

        # 检测组合键并触发回调
        gun_name = self._get_gun_name(button)
        if gun_name:
            self.current_text = gun_name
            self.callback(self.current_text)

    def _get_gun_name(self, button: Button) -> Optional[str]:
        """
        根据当前修饰键状态和鼠标按钮获取枪械名称

        Args:
            button: 鼠标按钮

        Returns:
            枪械名称，如果没有匹配的组合键则返回 None
        """
        # 检查是否只有一个修饰键被按下
        modifier_count = sum([self.alt_pressed, self.ctrl_pressed, self.shift_pressed])
        if modifier_count != 1:
            return None

        # LAlt + 鼠标侧键
        if self.alt_pressed:
            if button == self.MOUSE_FORWARD:
                return "MP5k"
            elif button == self.MOUSE_BACKWARD:
                return "UMP5"

        # LCtrl + 鼠标侧键
        elif self.ctrl_pressed:
            if button == self.MOUSE_FORWARD:
                return "M416"
            elif button == self.MOUSE_BACKWARD:
                return "ACE32"

        # LShift + 鼠标侧键
        elif self.shift_pressed:
            if button == self.MOUSE_FORWARD:
                return "SCAR-L"
            elif button == self.MOUSE_BACKWARD:
                return "AUG"

        return None

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
