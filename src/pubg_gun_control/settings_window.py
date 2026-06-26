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

from pubg_gun_control.voice_prompt import VoicePlayer

_MODIFIER_DISPLAY: dict[str, str] = {
    "alt": "LAlt",
    "ctrl": "LCtrl",
    "shift": "LShift",
}

_MOUSE_BUTTON_DISPLAY: dict[str, str] = {
    "forward": "前进键",
    "backward": "后退键",
}

_VOICE_EVENT_LABELS: dict[str, str] = {
    "recoil_on": "压枪开启",
    "recoil_off": "压枪关闭",
    "lock_on": "模式锁定",
    "lock_off": "模式解锁",
    "locked_action": "锁定拦截",
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
        on_save: Callable[[
            list[dict[str, str]],
            dict[str, dict[str, bool]],
            bool,
            int,
            dict[str, bool],
        ], None],
        voice_enabled: bool = True,
        voice_volume: int = 100,
        voice_event_enabled: dict[str, bool] | None = None,
        voice_player: VoicePlayer | None = None,
        recognition_config: dict | None = None,
        on_recognition_save: Callable[[dict], None] | None = None,
    ) -> None:
        self.parent = parent
        self.shortcuts = list(shortcuts)
        self.gun_attachments = dict(gun_attachments)
        self.on_save = on_save
        self.voice_player = voice_player
        self._recognition_config = recognition_config or {}
        self.on_recognition_save = on_recognition_save
        self.rec_enabled_var = tk.BooleanVar(value=bool(self._recognition_config.get("enabled", False)))
        self.rec_hotkey_var = tk.StringVar(value=str(self._recognition_config.get("hotkey", "f2")))
        self.rec_path_var = tk.StringVar(value=str(self._recognition_config.get("rec_path", "")))
        self.voice_enabled_var = tk.BooleanVar(value=voice_enabled)
        self.voice_volume_var = tk.IntVar(value=max(0, min(100, int(voice_volume))))
        self._default_event_enabled = self._build_default_event_enabled(voice_event_enabled)
        self.voice_event_vars: dict[str, tk.BooleanVar] = {
            event: tk.BooleanVar(value=self._default_event_enabled.get(event, True))
            for event in _VOICE_EVENT_LABELS
        }
        self.entries: list[tk.Entry] = []
        self.checkboxes: dict[int, dict[str, tk.BooleanVar]] = {}
        self._create_window()

    @staticmethod
    def _build_default_event_enabled(
        voice_event_enabled: dict[str, bool] | None,
    ) -> dict[str, bool]:
        result: dict[str, bool] = {event: True for event in _VOICE_EVENT_LABELS}
        if voice_event_enabled:
            for key, value in voice_event_enabled.items():
                if key in result and isinstance(value, bool):
                    result[key] = value
        return result

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

        ttk.Checkbutton(
            main_frame, text="启用语音提示", variable=self.voice_enabled_var
        ).grid(row=btn_row + 1, column=0, columnspan=self._COLUMNS, pady=(3, 3))

        # 音量设置
        volume_row = btn_row + 2
        volume_frame = ttk.Frame(main_frame)
        volume_frame.grid(row=volume_row, column=0, columnspan=self._COLUMNS, pady=(3, 3), padx=4, sticky="ew")
        volume_frame.columnconfigure(1, weight=1)
        ttk.Label(volume_frame, text="音量", width=6, anchor="w").grid(row=0, column=0, padx=(0, 4))
        self._volume_value_label = ttk.Label(volume_frame, text=f"{self.voice_volume_var.get()}%", width=6, anchor="e")
        self._volume_value_label.grid(row=0, column=2, padx=(4, 0))
        volume_scale = ttk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.voice_volume_var,
            command=self._on_volume_change,
        )
        volume_scale.grid(row=0, column=1, sticky="ew")

        # 单事件开关 + 试听
        events_row = volume_row + 1
        events_frame = ttk.Frame(main_frame)
        events_frame.grid(
            row=events_row, column=0, columnspan=self._COLUMNS, pady=(3, 3), padx=4, sticky="ew"
        )
        events_frame.columnconfigure(1, weight=1)
        for idx, (event, label) in enumerate(_VOICE_EVENT_LABELS.items()):
            ttk.Label(events_frame, text=label, width=10, anchor="w").grid(row=idx, column=0, padx=(0, 4), pady=1, sticky="w")
            ttk.Checkbutton(events_frame, text="启用", variable=self.voice_event_vars[event]).grid(
                row=idx, column=1, padx=4, pady=1, sticky="w"
            )
            ttk.Button(
                events_frame,
                text="试听",
                width=6,
                command=lambda e=event: self._on_preview(e),
            ).grid(row=idx, column=2, padx=4, pady=1, sticky="e")

        sep_row = events_row + 1

        # 自动识别配置区
        rec_row = sep_row
        rec_frame = ttk.Frame(main_frame)
        rec_frame.grid(row=rec_row, column=0, columnspan=self._COLUMNS, pady=(3, 3), padx=4, sticky="ew")
        ttk.Label(rec_frame, text="自动识别", font=("Arial", 10, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(0, 3), sticky="w"
        )
        ttk.Checkbutton(rec_frame, text="启用自动识别", variable=self.rec_enabled_var).grid(
            row=1, column=0, padx=(0, 8), sticky="w"
        )
        ttk.Label(rec_frame, text="识别快捷键", width=10, anchor="w").grid(
            row=1, column=1, padx=(0, 4), sticky="w"
        )
        ttk.Entry(rec_frame, textvariable=self.rec_hotkey_var, width=8, justify="center").grid(
            row=1, column=2, padx=2, sticky="w"
        )
        ttk.Label(rec_frame, text="rec.lua路径", width=10, anchor="w").grid(
            row=2, column=0, padx=(0, 4), sticky="w", pady=(4, 0)
        )
        ttk.Entry(rec_frame, textvariable=self.rec_path_var, width=30).grid(
            row=2, column=1, columnspan=2, padx=2, sticky="ew", pady=(4, 0)
        )
        ttk.Label(rec_frame, text="留空则使用默认路径（程序目录下pubg_rec.lua）", font=("Arial", 8), foreground="gray").grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(0, 2)
        )
        ttk.Button(rec_frame, text="导出GHUB脚本", command=self._on_export_lua, width=14).grid(
            row=4, column=0, columnspan=3, pady=(4, 2), sticky="w"
        )

        sep_row = rec_row + 1
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=sep_row, column=0, columnspan=self._COLUMNS, sticky="ew", pady=(3, 3)
        )

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=sep_row + 1, column=0, columnspan=self._COLUMNS, pady=(3, 0))

        ttk.Button(btn_frame, text="保存", command=self._on_save, width=10).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=10).pack(side=tk.LEFT, padx=8)

        self.window.update_idletasks()
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (w // 2)
        y = (self.window.winfo_screenheight() // 2) - (h // 2)
        self.window.geometry(f"+{x}+{y}")

        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_volume_change(self, value: str) -> None:
        """滑块拖动时同步更新右侧百分比标签。"""
        try:
            current = int(float(value))
        except (TypeError, ValueError):
            return
        if hasattr(self, "_volume_value_label"):
            self._volume_value_label.config(text=f"{current}%")

    def _on_preview(self, event: str) -> None:
        """试听按钮：将当前音量/事件开关临时同步到 player 并播放。"""
        if self.voice_player is None:
            return
        # 临时反映当前 UI 设置，便于试听生效
        self.voice_player.volume = int(self.voice_volume_var.get())
        # 试听不受启用语音总开关影响，仅受单事件开关控制
        self.voice_player.event_enabled = {
            key: bool(var.get()) for key, var in self.voice_event_vars.items()
        }
        self.voice_player.play(event)

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

        voice_enabled = self.voice_enabled_var.get()
        voice_volume = int(self.voice_volume_var.get())
        voice_event_enabled: dict[str, bool] = {
            event: bool(var.get()) for event, var in self.voice_event_vars.items()
        }
        self.on_save(new_shortcuts, new_gun_attachments, voice_enabled, voice_volume, voice_event_enabled)
        if self.on_recognition_save is not None:
            rec_cfg = {
                "enabled": self.rec_enabled_var.get(),
                "hotkey": self.rec_hotkey_var.get().strip() or "f2",
                "rec_path": self.rec_path_var.get().strip(),
            }
            self.on_recognition_save(rec_cfg)
        self.window.destroy()

    def _on_export_lua(self) -> None:
        from tkinter import filedialog, messagebox
        from pathlib import Path
        from pubg_gun_control.lua_generator import generate_auto_recognize_script

        source = str(Path(__file__).resolve().parent.parent.parent / "1.2.2-2024.5.20.-GHUB.-github.lua")
        rec_path = self.rec_path_var.get().strip()
        if not rec_path:
            rec_path = str(Path(__file__).resolve().parent.parent.parent / "pubg_rec.lua")

        save_path = filedialog.asksaveasfilename(
            title="导出GHUB压枪脚本",
            defaultextension=".lua",
            filetypes=[("Lua脚本", "*.lua")],
            initialfile="auto_recognize_ghub.lua",
        )
        if not save_path:
            return
        try:
            generate_auto_recognize_script(source, output_path=save_path, rec_path=rec_path)
            messagebox.showinfo("导出成功", f"脚本已导出到:\n{save_path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def _on_cancel(self) -> None:
        self.window.destroy()
