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
import threading
import tkinter as tk
from ctypes import wintypes
from tkinter import font as tkfont
from typing import Final

logger = logging.getLogger(__name__)

_WINDOW_WIDTH: Final[int] = 200
_WINDOW_HEIGHT: Final[int] = 60
_WINDOW_X: Final[int] = 0
_WINDOW_Y: Final[int] = 0

_FONT_FAMILY: Final[str] = "Arial"
_FONT_SIZE: Final[int] = 24
_FONT_WEIGHT: Final[str] = "bold"

_COLOR_FG_DEFAULT: Final[str] = "red"
_COLOR_BG_DEFAULT: Final[str] = "white"
_COLOR_BG_LOCKED: Final[str] = "#FFD700"
_COLOR_FG_LOCKED: Final[str] = "#8B0000"
_COLOR_TRANSPARENT: Final[str] = "#000000"

_GWL_EXSTYLE: Final[int] = -20
_GWL_STYLE: Final[int] = -16
_WS_EX_LAYERED: Final[int] = 0x00080000
_WS_EX_TRANSPARENT: Final[int] = 0x00000020
_WS_EX_TOOLWINDOW: Final[int] = 0x00000080
_WS_EX_APPWINDOW: Final[int] = 0x00040000
_WS_EX_TOPMOST: Final[int] = 0x00000008
_WS_CHILD: Final[int] = 0x40000000
_WS_POPUP: Final[int] = 0x80000000

_LWA_COLORKEY: Final[int] = 0x00000001

_GA_ROOT: Final[int] = 2
_HWND_TOPMOST: Final[int] = -1
_SWP_NOMOVE: Final[int] = 0x0002
_SWP_NOSIZE: Final[int] = 0x0001
_SWP_NOACTIVATE: Final[int] = 0x0010
_SWP_FRAMECHANGED: Final[int] = 0x0020

_QUEUE_POLL_INTERVAL: Final[int] = 16
_TOPMOST_REFRESH_MS: Final[int] = 500
_TOPMOST_THREAD_INTERVAL: Final[float] = 0.1

_TYPE_TEXT: Final[str] = "text"
_TYPE_LOCK: Final[str] = "lock"
_TYPE_SCOPE: Final[str] = "scope"

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32


def _rgb(r: int, g: int, b: int) -> int:
    return (b << 16) | (g << 8) | r


def _get_window_thread_process_id(hwnd: int) -> int:
    tid = ctypes.c_ulong()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(tid))
    return tid.value


class OverlayWindow:
    """置顶浮窗，用于显示枪械名称"""

    GWL_EXSTYLE = _GWL_EXSTYLE
    GWL_STYLE = _GWL_STYLE
    WS_EX_LAYERED = _WS_EX_LAYERED
    WS_EX_TRANSPARENT = _WS_EX_TRANSPARENT
    WS_EX_TOOLWINDOW = _WS_EX_TOOLWINDOW
    WS_EX_APPWINDOW = _WS_EX_APPWINDOW
    WS_EX_TOPMOST = _WS_EX_TOPMOST
    WS_CHILD = _WS_CHILD
    WS_POPUP = _WS_POPUP

    def __init__(self) -> None:
        self.root: tk.Tk | None = None
        self.label: tk.Label | None = None
        self.scope_label: tk.Label | None = None
        self.current_text: str = ""
        self.locked: bool = False
        self.scope_mode: int = 1
        self._pending: queue.Queue[tuple[str, str | bool | int]] = queue.Queue()
        self._topmost_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._cached_hwnd: int = 0
        self._setup_windows_api()

    def _setup_windows_api(self) -> None:
        _user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        _user32.GetWindowLongW.restype = wintypes.LONG
        _user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
        _user32.SetWindowLongW.restype = wintypes.LONG
        _user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.UINT,
        ]
        _user32.SetWindowPos.restype = wintypes.BOOL
        _user32.GetParent.argtypes = [wintypes.HWND]
        _user32.GetParent.restype = wintypes.HWND
        _user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
        _user32.GetAncestor.restype = wintypes.HWND
        _user32.IsWindowVisible.argtypes = [wintypes.HWND]
        _user32.IsWindowVisible.restype = wintypes.BOOL
        _user32.GetForegroundWindow.argtypes = []
        _user32.GetForegroundWindow.restype = wintypes.HWND
        _user32.GetWindowTextW.argtypes = [wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
        _user32.GetWindowTextW.restype = ctypes.c_int
        _user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        _user32.SetForegroundWindow.restype = wintypes.BOOL
        _user32.AttachThreadInput.argtypes = [ctypes.c_ulong, ctypes.c_ulong, wintypes.BOOL]
        _user32.AttachThreadInput.restype = wintypes.BOOL
        _user32.BringWindowToTop.argtypes = [wintypes.HWND]
        _user32.BringWindowToTop.restype = wintypes.BOOL
        _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(ctypes.c_ulong)]
        _user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
        _user32.SetLayeredWindowAttributes.argtypes = [
            wintypes.HWND, ctypes.c_ulong, wintypes.BYTE, ctypes.c_ulong,
        ]
        _user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
        _kernel32.GetCurrentThreadId.argtypes = []
        _kernel32.GetCurrentThreadId.restype = ctypes.c_ulong

    def _resolve_hwnd(self) -> int:
        if not self.root:
            return 0

        widget_hwnd = self.root.winfo_id()
        root_hwnd = _user32.GetAncestor(widget_hwnd, _GA_ROOT)
        if root_hwnd:
            return root_hwnd

        style = _user32.GetWindowLongW(widget_hwnd, self.GWL_STYLE)
        if style & self.WS_CHILD:
            parent_hwnd = _user32.GetParent(widget_hwnd)
            if parent_hwnd:
                return parent_hwnd

        return widget_hwnd

    def _get_hwnd(self) -> int | None:
        if self._cached_hwnd:
            return self._cached_hwnd
        return self._resolve_hwnd() or None

    def _diagnose_hwnd(self) -> None:
        widget_hwnd = self.root.winfo_id() if self.root else 0
        top_hwnd = self._get_hwnd()

        if not widget_hwnd or not top_hwnd:
            logger.warning("诊断: 无法获取 HWND")
            return

        widget_style = _user32.GetWindowLongW(widget_hwnd, self.GWL_STYLE)
        widget_ex = _user32.GetWindowLongW(widget_hwnd, self.GWL_EXSTYLE)
        top_style = _user32.GetWindowLongW(top_hwnd, self.GWL_STYLE)
        top_ex = _user32.GetWindowLongW(top_hwnd, self.GWL_EXSTYLE)

        top_is_topmost = bool(top_ex & self.WS_EX_TOPMOST)
        top_is_popup = bool(top_style & self.WS_POPUP)
        top_is_visible = bool(_user32.IsWindowVisible(top_hwnd))

        fg_hwnd = _user32.GetForegroundWindow()
        fg_title = ctypes.create_unicode_buffer(256)
        _user32.GetWindowTextW(fg_hwnd, fg_title, 256)

        logger.info(
            "诊断: widget=0x%X(st=0x%X,ex=0x%X) "
            "top=0x%X(st=0x%X,ex=0x%X) "
            "TOPMOST=%s POPUP=%s VIS=%s "
            "前台=0x%X(%s)",
            widget_hwnd, widget_style, widget_ex,
            top_hwnd, top_style, top_ex,
            top_is_topmost, top_is_popup, top_is_visible,
            fg_hwnd, fg_title.value,
        )

    def _apply_overlay_styles(self) -> None:
        hwnd = self._get_hwnd()
        if not hwnd:
            return

        ex_style = _user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
        new_ex_style = (
            ex_style
            | self.WS_EX_TOPMOST
            | self.WS_EX_LAYERED
            | self.WS_EX_TRANSPARENT
            | self.WS_EX_TOOLWINDOW
        ) & ~self.WS_EX_APPWINDOW
        _user32.SetWindowLongW(hwnd, self.GWL_EXSTYLE, new_ex_style)

        _user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
        )

    def _configure_transparency(self) -> None:
        hwnd = self._get_hwnd()
        if not hwnd:
            return

        color_key = _rgb(0, 0, 0)
        result = _user32.SetLayeredWindowAttributes(hwnd, color_key, 0, _LWA_COLORKEY)
        if not result:
            logger.warning("SetLayeredWindowAttributes 失败，hwnd=0x%X", hwnd)
        else:
            logger.info("SetLayeredWindowAttributes 成功，color_key=RGB(0,0,0)")

    def _force_topmost(self) -> None:
        hwnd = self._get_hwnd()
        if not hwnd:
            return

        _user32.SetWindowPos(
            hwnd, _HWND_TOPMOST, 0, 0, 0, 0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
        )

    def _brute_force_topmost(self) -> None:
        hwnd = self._get_hwnd()
        if not hwnd:
            return

        fg_hwnd = _user32.GetForegroundWindow()
        if fg_hwnd and fg_hwnd != hwnd:
            fg_tid = _get_window_thread_process_id(fg_hwnd)
            our_tid = _kernel32.GetCurrentThreadId()

            if fg_tid and fg_tid != our_tid:
                attached = _user32.AttachThreadInput(our_tid, fg_tid, True)
                if attached:
                    try:
                        _user32.SetForegroundWindow(hwnd)
                        _user32.BringWindowToTop(hwnd)
                    finally:
                        _user32.AttachThreadInput(our_tid, fg_tid, False)

        _user32.SetWindowPos(
            hwnd, _HWND_TOPMOST, 0, 0, 0, 0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
        )
        _user32.BringWindowToTop(hwnd)

    def _topmost_worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._brute_force_topmost()
            except Exception:
                logger.debug("topmost worker 异常", exc_info=True)
            self._stop_event.wait(_TOPMOST_THREAD_INTERVAL)

    def _refresh_topmost(self) -> None:
        if self.root is None:
            return
        self._force_topmost()
        self.root.after(_TOPMOST_REFRESH_MS, self._refresh_topmost)

    def create(self) -> None:
        self.root = tk.Tk()
        self.root.title("PUBG Gun Control")

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", _COLOR_TRANSPARENT)

        self.root.geometry(f"{_WINDOW_WIDTH}x{_WINDOW_HEIGHT}+{_WINDOW_X}+{_WINDOW_Y}")

        self.root.configure(bg=_COLOR_BG_DEFAULT)

        self.scope_label = tk.Label(
            self.root,
            text="1",
            font=tkfont.Font(family=_FONT_FAMILY, size=14, weight=_FONT_WEIGHT),
            fg=_COLOR_FG_DEFAULT,
            bg=_COLOR_BG_DEFAULT,
            padx=2,
            pady=0,
        )
        self.scope_label.place(x=2, y=2)

        self.label = tk.Label(
            self.root,
            text="无",
            font=tkfont.Font(family=_FONT_FAMILY, size=_FONT_SIZE, weight=_FONT_WEIGHT),
            fg=_COLOR_FG_DEFAULT,
            bg=_COLOR_BG_DEFAULT,
            padx=10,
            pady=5,
        )
        self.label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.root.update_idletasks()

        self._cached_hwnd = self._resolve_hwnd()
        logger.info("解析 HWND: widget=0x%X -> top=0x%X", self.root.winfo_id(), self._cached_hwnd)

        self._apply_overlay_styles()
        self._configure_transparency()
        self._force_topmost()

        self._diagnose_hwnd()

        self._start_polling()
        self._refresh_topmost()

        self._stop_event.clear()
        self._topmost_thread = threading.Thread(
            target=self._topmost_worker,
            daemon=True,
        )
        self._topmost_thread.start()

        logger.info("浮窗已创建，top_hwnd=0x%X", self._cached_hwnd)

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
                elif msg_type == _TYPE_SCOPE:
                    self._do_update_scope(int(payload))
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
            if self.scope_label:
                self.scope_label.config(bg=_COLOR_BG_LOCKED, fg=_COLOR_FG_LOCKED)
        else:
            self.root.configure(bg=_COLOR_BG_DEFAULT)
            self.label.config(bg=_COLOR_BG_DEFAULT, fg=_COLOR_FG_DEFAULT)
            if self.scope_label:
                self.scope_label.config(bg=_COLOR_BG_DEFAULT, fg=_COLOR_FG_DEFAULT)

        self.label.config(text=self.current_text)

    def _do_update_scope(self, scope_mode: int) -> None:
        if self.root is None or self.scope_label is None:
            return

        if scope_mode != self.scope_mode:
            self.scope_mode = scope_mode
            self.scope_label.config(text=str(scope_mode))

    def update_text(self, text: str) -> None:
        if self.root is None or self.label is None:
            return
        self._pending.put((_TYPE_TEXT, text))

    def set_locked(self, locked: bool) -> None:
        if self.root is None or self.label is None:
            return
        self._pending.put((_TYPE_LOCK, locked))

    def set_scope_mode(self, scope_mode: int) -> None:
        if self.root is None or self.scope_label is None:
            return
        self._pending.put((_TYPE_SCOPE, scope_mode))

    def show(self) -> None:
        if self.root:
            self.root.deiconify()
            self._force_topmost()

    def hide(self) -> None:
        if self.root:
            self.root.withdraw()

    def run(self) -> None:
        if self.root:
            self.root.mainloop()

    def close(self) -> None:
        self._stop_event.set()
        if self._topmost_thread and self._topmost_thread.is_alive():
            self._topmost_thread.join(timeout=2)
            self._topmost_thread = None

        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None
            self.label = None
            self._cached_hwnd = 0
        logger.info("浮窗已关闭")

    def is_created(self) -> bool:
        return self.root is not None
