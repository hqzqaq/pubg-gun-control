"""
ROI 区域选择器

初始化时让用户在全屏截图上框选识别区域（武器名称、配件图标等），
保存坐标到 config.json 供识别引擎使用。

@author hqzqaq
@since 2026-06-25
@version 1.0
"""

import logging
import tkinter as tk
from typing import Callable

import mss
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)

ROI_LABELS = {
    "weapon_roi": "武器名称区域",
    "muzzle_roi": "枪口配件图标区域",
    "grip_roi": "握把配件图标区域",
    "stock_roi": "枪托配件图标区域",
    "scope_roi": "倍镜信息区域（可选，按 Esc 跳过）",
}

CAPTURE_HOTKEY = "F3"


class RoiSelector:
    """全屏截图上框选 ROI 区域的 tkinter 工具"""

    def __init__(self, on_complete: Callable[[dict[str, list[int]]], None]) -> None:
        self._on_complete = on_complete
        self._rois: dict[str, list[int]] = {}
        self._roi_keys = list(ROI_LABELS.keys())
        self._current_index = 0
        self._start_x = 0
        self._start_y = 0
        self._rect_id = None
        self._screenshot: Image.Image | None = None
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._selection_root: tk.Tk | None = None

    def start(self) -> None:
        """显示准备窗口，等待用户按 F3 截屏"""
        self._ready_root = tk.Tk()
        self._ready_root.title("准备截屏")
        self._ready_root.attributes("-topmost", True)
        self._ready_root.geometry("420x180")
        self._ready_root.resizable(False, False)

        tk.Label(
            self._ready_root,
            text="请先切换到游戏画面（打开背包，确保武器栏可见）",
            font=("Microsoft YaHei", 11),
            wraplength=400,
        ).pack(pady=(20, 8))

        tk.Label(
            self._ready_root,
            text=f"准备好后按 {CAPTURE_HOTKEY} 截屏",
            font=("Microsoft YaHei", 14, "bold"),
            fg="red",
        ).pack(pady=4)

        tk.Label(
            self._ready_root,
            text="（截屏后将进入区域框选）",
            font=("Microsoft YaHei", 9),
            fg="gray",
        ).pack(pady=2)

        self._ready_root.bind(f"<{CAPTURE_HOTKEY}>", self._on_capture_hotkey)
        self._ready_root.protocol("WM_DELETE_WINDOW", self._on_ready_close)
        self._ready_root.mainloop()

    def _on_ready_close(self) -> None:
        self._ready_root.destroy()

    def _on_capture_hotkey(self, event: tk.Event) -> None:
        self._ready_root.destroy()
        self._capture_and_select()

    def _capture_and_select(self) -> None:
        """截屏并打开区域选择窗口"""
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            self._screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        self._selection_root = tk.Tk()
        self._selection_root.title("框选识别区域")
        self._selection_root.attributes("-topmost", True)

        screen_w = self._selection_root.winfo_screenwidth()
        screen_h = self._selection_root.winfo_screenheight()
        img_w, img_h = self._screenshot.size

        self._scale_x = img_w / screen_w
        self._scale_y = img_h / screen_h

        display_img = self._screenshot.resize((screen_w, screen_h), Image.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(display_img)

        self._canvas = tk.Canvas(self._selection_root, width=screen_w, height=screen_h, highlightthickness=0)
        self._canvas.pack()
        self._canvas.create_image(0, 0, anchor=tk.NW, image=self._tk_img)

        self._label = tk.Label(
            self._selection_root,
            text=self._get_instruction(),
            font=("Microsoft YaHei", 16, "bold"),
            fg="yellow",
            bg="black",
        )
        self._label.place(x=20, y=20)

        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._selection_root.bind("<Escape>", self._on_skip)

        self._selection_root.mainloop()

    def _get_instruction(self) -> str:
        key = self._roi_keys[self._current_index]
        label = ROI_LABELS[key]
        return f"[{self._current_index + 1}/{len(self._roi_keys)}] 请框选: {label}"

    def _on_press(self, event: tk.Event) -> None:
        self._start_x = event.x
        self._start_y = event.y
        if self._rect_id:
            self._canvas.delete(self._rect_id)
        self._rect_id = self._canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline="lime", width=2,
        )

    def _on_drag(self, event: tk.Event) -> None:
        if self._rect_id:
            self._canvas.coords(self._rect_id, self._start_x, self._start_y, event.x, event.y)

    def _on_release(self, event: tk.Event) -> None:
        x1 = int(min(self._start_x, event.x) * self._scale_x)
        y1 = int(min(self._start_y, event.y) * self._scale_y)
        x2 = int(max(self._start_x, event.x) * self._scale_x)
        y2 = int(max(self._start_y, event.y) * self._scale_y)

        if x2 - x1 < 5 or y2 - y1 < 5:
            return

        key = self._roi_keys[self._current_index]
        self._rois[key] = [x1, y1, x2, y2]
        logger.info("已框选 %s: %s", key, self._rois[key])

        self._current_index += 1
        if self._current_index >= len(self._roi_keys):
            self._finish()
        else:
            self._label.config(text=self._get_instruction())

    def _on_skip(self, event: tk.Event) -> None:
        key = self._roi_keys[self._current_index]
        logger.info("跳过 %s", key)
        self._current_index += 1
        if self._current_index >= len(self._roi_keys):
            self._finish()
        else:
            self._label.config(text=self._get_instruction())

    def _finish(self) -> None:
        self._selection_root.destroy()
        self._on_complete(self._rois)
