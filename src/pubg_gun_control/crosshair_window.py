"""
屏幕中心准星模块

在屏幕中心显示可自定义的准星（颜色/大小/形状），用于 PUBG 人物奔跑时
丢失准星点的场景。支持常驻显示与长按按键显示两种模式。

@author hqzqaq
@since 2026-09-20
@version 1.0
"""

import ctypes
import logging
import queue
import tkinter as tk
from ctypes import wintypes
from typing import Any, Final

logger = logging.getLogger(__name__)

_CANVAS_SIZE: Final[int] = 400
_COLOR_KEY: Final[str] = "#010101"
_POLL_INTERVAL: Final[int] = 16
_TOPMOST_REFRESH_EVERY: Final[int] = 32

_GWL_EXSTYLE: Final[int] = -20
_WS_EX_LAYERED: Final[int] = 0x00080000
_WS_EX_TRANSPARENT: Final[int] = 0x00000020
_WS_EX_TOOLWINDOW: Final[int] = 0x00000080
_WS_EX_APPWINDOW: Final[int] = 0x00040000
_WS_EX_TOPMOST: Final[int] = 0x00000008

_GA_ROOT: Final[int] = 2
_HWND_TOPMOST: Final[int] = -1
_SWP_NOMOVE: Final[int] = 0x0002
_SWP_NOSIZE: Final[int] = 0x0001
_SWP_NOACTIVATE: Final[int] = 0x0010
_SWP_FRAMECHANGED: Final[int] = 0x0020

_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "mode": "hold",
    "hold_key": "shift",
    "hotkey_enable": "1",
    "hotkey_disable": "2",
    "color": "#00FF00",
    "size": 40,
    "shape": "cross",
}

# 窗口透明色键对应的 RGB 值（与 _COLOR_KEY 一致），抗锯齿边缘在此底色上混合
_KEY_RGB: tuple[int, int, int] = (0x01, 0x01, 0x01)

_MONITOR_DEFAULTTONEAREST: Final[int] = 2


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


_user32 = ctypes.windll.user32


def _setup_win32_api() -> None:
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
    _user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
    _user32.GetAncestor.restype = wintypes.HWND
    _user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    _user32.GetCursorPos.restype = wintypes.BOOL
    _user32.GetForegroundWindow.argtypes = []
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    _user32.MonitorFromWindow.restype = ctypes.c_void_p
    _user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    _user32.MonitorFromPoint.restype = ctypes.c_void_p
    _user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_MONITORINFO)]
    _user32.GetMonitorInfoW.restype = wintypes.BOOL


_setup_win32_api()


def render_crosshair_image(color: str, size: int, shape: str) -> "Image.Image":
    """超采样绘制抗锯齿准星 PNG(RGBA) 图像。

    先以 4 倍分辨率用 PIL 绘制，再 LANCZOS 缩小到目标尺寸，得到平滑的弧形边缘
    （tkinter Canvas 原生绘制在 Windows 上无抗锯齿，小圆点会呈锯齿状）。
    """
    from PIL import Image, ImageDraw

    size = max(6, int(size))
    width = max(2, int(size * 0.12))
    gap = max(2, int(size * 0.12))
    half = size / 2
    pad = max(6, int(width) * 2)
    dim = int(2 * half) + pad * 2
    ss = 4  # 超采样倍数
    hi = dim * ss
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    c = hi // 2
    lw = max(1, int(width * ss))

    if shape == "dot":
        radius = max(1, int(size * 0.25))
        r = radius * ss
        draw.ellipse([c - r, c - r, c + r, c + r], fill=color)
    elif shape == "circle":
        r = int(half * ss)
        draw.ellipse([c - r, c - r, c + r, c + r], outline=color, width=lw)
    else:
        g = int(gap * ss)
        h = int(half * ss)
        draw.line([(c - h, c), (c - g, c)], fill=color, width=lw)
        draw.line([(c + g, c), (c + h, c)], fill=color, width=lw)
        draw.line([(c, c - h), (c, c - g)], fill=color, width=lw)
        draw.line([(c, c + g), (c, c + h)], fill=color, width=lw)
        if shape == "cross_dot":
            dot_r = max(1, int(size * 0.1)) * ss
            draw.ellipse([c - dot_r, c - dot_r, c + dot_r, c + dot_r], fill=color)

    return img.resize((dim, dim), Image.LANCZOS)


def _rgba_to_keyed_photo(img: "Image.Image") -> tk.PhotoImage:
    """把 RGBA 准星图合成到窗口透明色键上，转为无 alpha 的 Tk PhotoImage。

    透明区域像素固定为 #010101，与窗口 color-key 完全一致（屏幕上不可见）；
    抗锯齿边缘像素为 准星色→#010101 的平滑过渡，消除锯齿。
    注意：Tk PhotoImage 必须保持引用，否则会被 GC 导致不显示。
    """
    from PIL import Image

    bg = Image.new("RGBA", img.size, (*_KEY_RGB, 255))
    comp = Image.alpha_composite(bg, img).convert("RGB")
    photo = tk.PhotoImage(width=comp.width, height=comp.height)
    px = comp.load()
    rows = [
        tuple("#%02x%02x%02x" % px[x, y] for x in range(comp.width))
        for y in range(comp.height)
    ]
    photo.put(rows)
    return photo


def draw_crosshair(
    canvas: tk.Canvas,
    cx: int,
    cy: int,
    color: str,
    size: int,
    shape: str,
) -> None:
    """在 Canvas 上绘制抗锯齿准星，供实际准星窗口与设置预览共用。

    Args:
        canvas: 目标画布
        cx/cy: 准星中心坐标
        color: 颜色（tkinter 颜色名或 #RRGGBB）
        size: 准星整体尺寸（像素）
        shape: cross(十字) / dot(点) / circle(圆环) / cross_dot(十字带点)
    """
    canvas.delete("all")
    img = render_crosshair_image(color, size, shape)
    photo = _rgba_to_keyed_photo(img)
    canvas._crosshair_photo = photo  # 保持引用，防止被垃圾回收
    canvas.create_image(int(cx), int(cy), image=photo)


class CrosshairWindow:
    """屏幕中心准星浮窗（点击穿透、置顶、仅显示绘制的准星）。"""

    def __init__(self, parent: tk.Misc) -> None:
        self._parent = parent
        self._config: dict[str, Any] = dict(_DEFAULTS)
        self.root: tk.Toplevel | None = None
        self.canvas: tk.Canvas | None = None
        self._hwnd: int = 0
        self._visible: bool = False
        self._hotkey_enabled: bool = True  # 快捷键开关（1打开/2关闭），相对设置主开关的运行时状态
        self._poll_ticks: int = 0
        self._pending: queue.Queue[tuple[str, Any | None]] = queue.Queue()
        self._create_window()

    def _create_window(self) -> None:
        root = tk.Toplevel(self._parent)
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", _COLOR_KEY)

        canvas = tk.Canvas(
            root,
            width=_CANVAS_SIZE,
            height=_CANVAS_SIZE,
            bg=_COLOR_KEY,
            highlightthickness=0,
        )
        canvas.pack()

        self.root = root
        self.canvas = canvas

        root.geometry(f"{_CANVAS_SIZE}x{_CANVAS_SIZE}")
        self._center_window()

        root.update_idletasks()
        self._hwnd = self._resolve_hwnd()
        self._apply_click_through()
        # 初始隐藏，由 apply_config 决定显示方式
        root.withdraw()
        self._visible = False

        root.after(_POLL_INTERVAL, self._poll)
        logger.info("准星浮窗已创建，hwnd=0x%X", self._hwnd)

    def _resolve_hwnd(self) -> int:
        if self.root is None:
            return 0
        widget_hwnd = self.root.winfo_id()
        root_hwnd = _user32.GetAncestor(widget_hwnd, _GA_ROOT)
        return root_hwnd or widget_hwnd

    def _apply_click_through(self) -> None:
        hwnd = self._hwnd
        if not hwnd:
            return
        ex_style = _user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
        new_ex_style = (
            ex_style
            | _WS_EX_TOPMOST
            | _WS_EX_LAYERED
            | _WS_EX_TRANSPARENT
            | _WS_EX_TOOLWINDOW
        ) & ~_WS_EX_APPWINDOW
        _user32.SetWindowLongW(hwnd, _GWL_EXSTYLE, new_ex_style)
        _user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
        )

    def _force_topmost(self) -> None:
        if not self._hwnd:
            return
        _user32.SetWindowPos(
            self._hwnd, _HWND_TOPMOST, 0, 0, 0, 0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
        )

    # ---- 屏幕居中 ----

    def _get_screen_rect(self) -> tuple[int, int, int, int]:
        """返回用于居中的目标显示器矩形（left, top, right, bottom）。

        优先取前台窗口所在显示器（游戏中通常即 PUBG 所在屏幕），
        其次取鼠标所在显示器，最后回退到主屏幕。使用整块显示器区域
        （rcMonitor，含任务栏区域），与全屏游戏一致。
        """
        if self.root is None:
            return (0, 0, 0, 0)
        hmon = 0
        fg_hwnd = _user32.GetForegroundWindow()
        if fg_hwnd:
            hmon = _user32.MonitorFromWindow(fg_hwnd, _MONITOR_DEFAULTTONEAREST)
        if not hmon:
            pt = wintypes.POINT()
            if _user32.GetCursorPos(ctypes.byref(pt)):
                hmon = _user32.MonitorFromPoint(pt, _MONITOR_DEFAULTTONEAREST)
        if hmon:
            info = _MONITORINFO()
            info.cbSize = ctypes.sizeof(_MONITORINFO)
            if _user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
                r = info.rcMonitor
                return (r.left, r.top, r.right, r.bottom)
        return (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())

    def _center_window(self) -> None:
        """把准星窗口定位到目标显示器正中心。"""
        if self.root is None:
            return
        left, top, right, bottom = self._get_screen_rect()
        x = left + ((right - left - _CANVAS_SIZE) // 2)
        y = top + ((bottom - top - _CANVAS_SIZE) // 2)
        self.root.geometry(f"+{int(x)}+{int(y)}")

    # ---- 配置 ----

    def apply_config(self, config: dict[str, Any]) -> None:
        """应用配置（颜色/大小/形状/模式/启停），须在 Tk 线程调用。"""
        merged = dict(_DEFAULTS)
        merged.update({k: v for k, v in config.items() if v is not None})
        self._config = merged

        if self.canvas is not None:
            self._redraw()
        self._apply_visibility()

    def _redraw(self) -> None:
        if self.canvas is None:
            return
        center = _CANVAS_SIZE // 2
        draw_crosshair(
            self.canvas,
            center,
            center,
            str(self._config.get("color", "#00FF00")),
            int(self._config.get("size", 40)),
            str(self._config.get("shape", "cross")),
        )

    def _apply_visibility(self) -> None:
        if self.root is None:
            return
        enabled = bool(self._config.get("enabled", False)) and self._hotkey_enabled
        always = str(self._config.get("mode", "hold")) == "always"
        if enabled and always:
            if not self._visible:
                # 每次显示前重新居中，适应分辨率/显示器布局变化
                self._center_window()
                self.root.deiconify()
                self._force_topmost()
                self._visible = True
        else:
            if self._visible:
                self.root.withdraw()
                self._visible = False

    # ---- 长按显示 ----

    def set_enabled_override(self, enabled: bool) -> None:
        """快捷键开关准星（线程安全）：1 打开 / 2 关闭。"""
        self._pending.put(("enable", bool(enabled)))

    def _do_set_enabled(self, enabled: bool) -> None:
        self._hotkey_enabled = bool(enabled)
        self._apply_visibility()
        logger.info("准星快捷键开关 -> %s", "开" if enabled else "关")

    def show_crosshair(self) -> None:
        """长按按键按下时显示准星（线程安全，仅长按模式生效）。"""
        if not self._config.get("enabled") or not self._hotkey_enabled or self._config.get("mode") != "hold":
            return
        self._pending.put(("show", None))

    def hide_crosshair(self) -> None:
        """长按按键松开时隐藏准星（线程安全，仅长按模式生效）。"""
        if not self._config.get("enabled") or not self._hotkey_enabled or self._config.get("mode") != "hold":
            return
        self._pending.put(("hide", None))

    def _do_show(self) -> None:
        if self.root is None or self._visible:
            return
        # 每次长按显示前重新居中，保证准星始终在屏幕中心
        self._center_window()
        self.root.deiconify()
        self._force_topmost()
        self._visible = True

    def _do_hide(self) -> None:
        if self.root is None or not self._visible:
            return
        self.root.withdraw()
        self._visible = False

    def _poll(self) -> None:
        if self.root is None:
            return
        try:
            while True:
                cmd, payload = self._pending.get_nowait()
                if cmd == "show":
                    self._do_show()
                elif cmd == "hide":
                    self._do_hide()
                elif cmd == "enable":
                    self._do_set_enabled(bool(payload))
        except queue.Empty:
            pass

        self._poll_ticks += 1
        if self._poll_ticks % _TOPMOST_REFRESH_EVERY == 0:
            self._force_topmost()
        self.root.after(_POLL_INTERVAL, self._poll)

    def close(self) -> None:
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                logger.debug("销毁准星窗口异常", exc_info=True)
            self.root = None
            self.canvas = None
            self._hwnd = 0
        logger.info("准星浮窗已关闭")