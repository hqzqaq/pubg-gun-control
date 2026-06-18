"""
设置窗口模块

提供快捷键文本配置和配件勾选的可视化编辑界面

@author huquanzhi
@since 2026-04-18 19:38
@version 2.0
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

    _COLUMNS = 6
    _ATTACHMENT_COLS = ("muzzle", "grip", "stock")
    _ATTACHMENT_LABELS = {"muzzle": "枪口", "grip": "握把", "stock": "枪托"}

    def __init__(
        self,
        parent: tk.Tk,
        shortcuts: list[dict[str, str]],
        gun_attachments: dict[str, dict[str, bool]],
        on_save: Callable[[list[dict[str, str]], dict[str, dict[str, bool]]], None],
    ) -> None:
        self.parent = parent
        self.shortcuts = list(shortcuts)
        self.gun_attachments = dict(gun_attachments)
        self.on_save = on_save
        self.entries: list[tk.Entry] = []
        self.checkboxes: dict[int, dict[str, tk.BooleanVar]] = {}
        self._create_window()

    def _create_window(self) -> None:
        self.window = tk.Toplevel(self.parent)
        self.window.title("快捷键文本配置")
        self.window.resizable(False, False)
        self.window.attributes("-topmost", True)
        self.window.grab_set()

        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="快捷键配置", font=("Arial", 13, "bold")).grid(
            row=0, column=0, columnspan=self._COLUMNS, pady=(0, 10)
        )

        headers = ["修饰键", "鼠标按键", "显示文本", "枪口", "握把", "枪托"]
        widths = [8, 8, 12, 4, 4, 4]
        for col, (h, w) in enumerate(zip(headers, widths)):
            ttk.Label(main_frame, text=h, font=("Arial", 9, "bold"), width=w, anchor="center").grid(
                row=1, column=col, padx=3
            )

        ttk.Separator(main_frame, orient="horizontal").grid(
            row=2, column=0, columnspan=self._COLUMNS, sticky="ew", pady=3
        )

        for i, shortcut in enumerate(self.shortcuts):
            row = i + 3
            gun_name = shortcut["text"]
            ga = self.gun_attachments.get(gun_name, {"muzzle": True, "grip": True, "stock": True})

            mod_text = _MODIFIER_DISPLAY.get(shortcut["modifier"], shortcut["modifier"])
            btn_text = _MOUSE_BUTTON_DISPLAY.get(shortcut["mouse_button"], shortcut["mouse_button"])

            ttk.Label(main_frame, text=mod_text, width=8, anchor="center").grid(row=row, column=0, padx=3, pady=2)
            ttk.Label(main_frame, text=btn_text, width=8, anchor="center").grid(row=row, column=1, padx=3, pady=2)

            entry = ttk.Entry(main_frame, width=12, justify="center")
            entry.insert(0, gun_name)
            entry.grid(row=row, column=2, padx=3, pady=2)
            self.entries.append(entry)

            self.checkboxes[i] = {}
            for j, cat in enumerate(self._ATTACHMENT_COLS):
                var = tk.BooleanVar(value=ga.get(cat, True))
                cb = ttk.Checkbutton(main_frame, variable=var, width=2)
                cb.grid(row=row, column=3 + j, padx=2, pady=2)
                self.checkboxes[i][cat] = var

        btn_row = len(self.shortcuts) + 3
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=btn_row, column=0, columnspan=self._COLUMNS, sticky="ew", pady=(8, 3)
        )

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=btn_row + 1, column=0, columnspan=self._COLUMNS, pady=(3, 0))

        ttk.Button(btn_frame, text="保存", command=self._on_save, width=10).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=10).pack(side=tk.LEFT, padx=8)

        self.window.update_idletasks()
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (w // 2)
        y = (self.window.winfo_screenheight() // 2) - (h // 2)
        self.window.geometry(f"+{x}+{y}")

        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_save(self) -> None:
        new_shortcuts: list[dict[str, str]] = []
        new_gun_attachments: dict[str, dict[str, bool]] = {}

        for i, shortcut in enumerate(self.shortcuts):
            new_text = self.entries[i].get().strip() or shortcut["text"]
            new_shortcuts.append({
                "modifier": shortcut["modifier"],
                "mouse_button": shortcut["mouse_button"],
                "text": new_text,
            })
            new_gun_attachments[new_text] = {
                cat: self.checkboxes[i][cat].get() for cat in self._ATTACHMENT_COLS
            }

        self.on_save(new_shortcuts, new_gun_attachments)
        self.window.destroy()

    def _on_cancel(self) -> None:
        self.window.destroy()
