"""
设置窗口模块

提供快捷键文本配置的可视化编辑界面

@author huquanzhi
@since 2026-04-18 19:38
@version 1.0
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable

_MODIFIER_DISPLAY: dict[str, str] = {
    "alt": "LAlt",
    "ctrl": "LCtrl",
    "shift": "LShift",
}

_MOUSE_BUTTON_DISPLAY: dict[str, str] = {
    "forward": "前进键",
    "backward": "后退键",
}


class SettingsWindow:
    """快捷键文本配置窗口"""

    def __init__(
        self,
        parent: tk.Tk,
        shortcuts: list[dict[str, str]],
        on_save: Callable[[list[dict[str, str]]], None],
    ) -> None:
        self.parent = parent
        self.shortcuts = list(shortcuts)
        self.on_save = on_save
        self.entries: list[tk.Entry] = []
        self._create_window()

    def _create_window(self) -> None:
        self.window = tk.Toplevel(self.parent)
        self.window.title("快捷键文本配置")
        self.window.resizable(False, False)
        self.window.attributes("-topmost", True)
        self.window.grab_set()

        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="快捷键文本配置", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))

        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
        ttk.Label(header_frame, text="修饰键", font=("Arial", 10, "bold"), width=12, anchor="center").grid(row=0, column=0, padx=5)
        ttk.Label(header_frame, text="鼠标按键", font=("Arial", 10, "bold"), width=12, anchor="center").grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text="显示文本", font=("Arial", 10, "bold"), width=18, anchor="center").grid(row=0, column=2, padx=5)

        ttk.Separator(main_frame, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)

        for i, shortcut in enumerate(self.shortcuts):
            row = i + 3
            modifier_text = _MODIFIER_DISPLAY.get(shortcut["modifier"], shortcut["modifier"])
            mouse_text = _MOUSE_BUTTON_DISPLAY.get(shortcut["mouse_button"], shortcut["mouse_button"])

            ttk.Label(main_frame, text=modifier_text, width=12, anchor="center").grid(row=row, column=0, padx=5, pady=3)
            ttk.Label(main_frame, text=mouse_text, width=12, anchor="center").grid(row=row, column=1, padx=5, pady=3)

            entry = ttk.Entry(main_frame, width=18, justify="center")
            entry.insert(0, shortcut["text"])
            entry.grid(row=row, column=2, padx=5, pady=3)
            self.entries.append(entry)

        btn_row = len(self.shortcuts) + 3
        ttk.Separator(main_frame, orient="horizontal").grid(row=btn_row, column=0, columnspan=3, sticky="ew", pady=(10, 5))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=btn_row + 1, column=0, columnspan=3, pady=(5, 0))

        save_btn = ttk.Button(btn_frame, text="保存", command=self._on_save, width=10)
        save_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=10)
        cancel_btn.pack(side=tk.LEFT, padx=10)

        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")

        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_save(self) -> None:
        new_shortcuts: list[dict[str, str]] = []
        for i, shortcut in enumerate(self.shortcuts):
            new_text = self.entries[i].get().strip()
            if not new_text:
                new_text = shortcut["text"]
            new_shortcuts.append({
                "modifier": shortcut["modifier"],
                "mouse_button": shortcut["mouse_button"],
                "text": new_text,
            })
        self.on_save(new_shortcuts)
        self.window.destroy()

    def _on_cancel(self) -> None:
        self.window.destroy()
