"""
浮窗显示模块

负责创建和管理置顶浮窗，显示枪械名称

@author hqzqaq
@since 2026-03-30 19:49
@version 1.0
"""

import tkinter as tk
from tkinter import font as tkfont
from typing import Optional


class OverlayWindow:
    """置顶浮窗，用于显示枪械名称"""

    def __init__(self):
        """初始化浮窗"""
        self.root: Optional[tk.Tk] = None
        self.label: Optional[tk.Label] = None
        self.current_text: str = ""

    def create(self):
        """创建浮窗窗口"""
        self.root = tk.Tk()
        self.root.title("PUBG Gun Control")

        # 设置窗口样式
        self.root.overrideredirect(True)  # 无边框
        self.root.attributes("-topmost", True)  # 始终置顶
        self.root.attributes("-transparentcolor", "#000000")  # 黑色透明

        # 设置窗口位置和大小
        self.root.geometry("200x60+0+0")  # 左上角，200x60像素

        # 创建标签
        self.label = tk.Label(
            self.root,
            text="无",
            font=tkfont.Font(family="Arial", size=24, weight="bold"),
            fg="red",  # 红字
            bg="white",  # 白底
            padx=10,
            pady=5
        )
        self.label.pack(fill=tk.BOTH, expand=True)

        # 设置窗口背景为白色
        self.root.configure(bg="white")

    def update_text(self, text: str):
        """
        更新显示的文本

        Args:
            text: 要显示的文本
        """
        if self.label is None or self.root is None:
            return

        if text != self.current_text:
            self.current_text = text
            self.label.config(text=text)
            self.root.update()

    def show(self):
        """显示浮窗"""
        if self.root:
            self.root.deiconify()

    def hide(self):
        """隐藏浮窗"""
        if self.root:
            self.root.withdraw()

    def run(self):
        """运行主循环"""
        if self.root:
            self.root.mainloop()

    def close(self):
        """关闭浮窗"""
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None
            self.label = None

    def is_created(self) -> bool:
        """检查浮窗是否已创建"""
        return self.root is not None
