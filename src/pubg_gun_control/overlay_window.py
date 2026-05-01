"""
浮窗显示模块

负责创建和管理置顶浮窗，显示枪械名称

@author hqzqaq
@since 2026-03-30 19:49
@version 1.0
"""

import ctypes
import logging
import queue
import tkinter as tk
from ctypes import wintypes
from tkinter import font as tkfont
from typing import Final

logger = logging.getLogger(__name__)

# 窗口尺寸
_WINDOW_WIDTH: Final[int] = 200
_WINDOW_HEIGHT: Final[int] = 60
_WINDOW_X: Final[int] = 0
_WINDOW_Y: Final[int] = 0

# 字体配置
_FONT_FAMILY: Final[str] = "Arial"
_FONT_SIZE: Final[int] = 24
_FONT_WEIGHT: Final[str] = "bold"

# 颜色配置
_COLOR_FG_DEFAULT: Final[str] = "red"
_COLOR_BG_DEFAULT: Final[str] = "white"
_COLOR_BG_LOCKED: Final[str] = "#FFD700"
_COLOR_FG_LOCKED: Final[str] = "#8B0000"
_COLOR_TRANSPARENT: Final[str] = "#000000"

# Windows API 常量
_GWL_EXSTYLE: Final[int] = -20
_WS_EX_LAYERED: Final[int] = 0x00080000
_WS_EX_TRANSPARENT: Final[int] = 0x00000020

# 队列轮询间隔（毫秒）
_QUEUE_POLL_INTERVAL: Final[int] = 16

# 队列消息类型
_TYPE_TEXT: Final[str] = "text"
_TYPE_LOCK: Final[str] = "lock"


class OverlayWindow:
    """置顶浮窗，用于显示枪械名称"""

    GWL_EXSTYLE = _GWL_EXSTYLE
    WS_EX_LAYERED = _WS_EX_LAYERED
    WS_EX_TRANSPARENT = _WS_EX_TRANSPARENT

    def __init__(self) -> None:
        self.root: tk.Tk | None = None
        self.label: tk.Label | None = None
        self.current_text: str = ""
        self.locked: bool = False
        self._pending: queue.Queue[tuple[str, str | bool]] = queue.Queue()
        self._setup_windows_api()

    def _setup_windows_api(self) -> None:
        self._user32 = ctypes.windll.user32
        self._user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        self._user32.GetWindowLongW.restype = wintypes.LONG
        self._user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
        self._user32.SetWindowLongW.restype = wintypes.LONG

    def _set_click_through(self) -> None:
        if not self.root:
            return

        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        ex_style = self._user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
        new_ex_style = ex_style | self.WS_EX_LAYERED | self.WS_EX_TRANSPARENT
        self._user32.SetWindowLongW(hwnd, self.GWL_EXSTYLE, new_ex_style)

    def create(self) -> None:
        self.root = tk.Tk()
        self.root.title("PUBG Gun Control")

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", _COLOR_TRANSPARENT)

        self.root.update()
        self._set_click_through()

        self.root.geometry(f"{_WINDOW_WIDTH}x{_WINDOW_HEIGHT}+{_WINDOW_X}+{_WINDOW_Y}")

        self.label = tk.Label(
            self.root,
            text="无",
            font=tkfont.Font(family=_FONT_FAMILY, size=_FONT_SIZE, weight=_FONT_WEIGHT),
            fg=_COLOR_FG_DEFAULT,
            bg=_COLOR_BG_DEFAULT,
            padx=10,
            pady=5,
        )
        self.label.pack(fill=tk.BOTH, expand=True)

        self.root.configure(bg=_COLOR_BG_DEFAULT)

        self._start_polling()

        logger.info("浮窗已创建")

    def _start_polling(self) -> None:
        if self.root is None:
            return
        self.root.after(_QUEUE_POLL_INTERVAL, self._poll_queue)

    def _poll_queue(self) -> None:
        if self.root is None:
            return

        try:
            while True:
                msg_type, payload = self._pending.get_nowait()
                if msg_type == _TYPE_TEXT:
                    self._do_update_text(str(payload))
                elif msg_type == _TYPE_LOCK:
                    self._do_set_locked(bool(payload))
        except queue.Empty:
            pass

        self.root.after(_QUEUE_POLL_INTERVAL, self._poll_queue)

    def _do_update_text(self, text: str) -> None:
        if self.root is None or self.label is None:
            return

        if text != self.current_text:
            self.current_text = text
            self.label.config(text=self.current_text)

    def _do_set_locked(self, locked: bool) -> None:
        if self.root is None or self.label is None:
            return

        if self.locked == locked:
            return

        self.locked = locked

        if self.locked:
            self.root.configure(bg=_COLOR_BG_LOCKED)
            self.label.config(bg=_COLOR_BG_LOCKED, fg=_COLOR_FG_LOCKED)
        else:
            self.root.configure(bg=_COLOR_BG_DEFAULT)
            self.label.config(bg=_COLOR_BG_DEFAULT, fg=_COLOR_FG_DEFAULT)

        self.label.config(text=self.current_text)

    def update_text(self, text: str) -> None:
        if self.root is None or self.label is None:
            return
        self._pending.put((_TYPE_TEXT, text))

    def set_locked(self, locked: bool) -> None:
        if self.root is None or self.label is None:
            return
        self._pending.put((_TYPE_LOCK, locked))

    def show(self) -> None:
        if self.root:
            self.root.deiconify()

    def hide(self) -> None:
        if self.root:
            self.root.withdraw()

    def run(self) -> None:
        if self.root:
            self.root.mainloop()

    def close(self) -> None:
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None
            self.label = None
        logger.info("浮窗已关闭")

    def is_created(self) -> bool:
        return self.root is not None
