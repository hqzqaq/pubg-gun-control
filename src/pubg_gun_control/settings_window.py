"""
设置窗口模块

枪械配置 + 配件勾选 + 语音设置 + 自动识别配置

@author huquanzhi
@since 2026-04-18 19:38
@version 3.0
"""

import logging
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable

from pubg_gun_control.voice_prompt import VoicePlayer

logger = logging.getLogger(__name__)

_VOICE_EVENT_LABELS: dict[str, str] = {
    "recoil_on": "压枪开启",
    "recoil_off": "压枪关闭",
    "lock_on": "模式锁定",
    "lock_off": "模式解锁",
    "locked_action": "锁定拦截",
}

_ATTACH_COLS = ("muzzle", "grip", "stock")
_ATTACH_LABELS = {"muzzle": "枪口", "grip": "握把", "stock": "枪托"}


def _load_guns_from_lua() -> dict[str, list[str]]:
    """从 Lua 脚本解析枪械列表，按弹药类型分组"""
    from pubg_gun_control.lua_parser import LuaBallisticParser
    lua_path = str(Path(__file__).resolve().parent.parent.parent / "1.2.2-2024.5.20.-GHUB.-github.lua")
    try:
        parser = LuaBallisticParser()
        config = parser.parse(lua_path)
        result: dict[str, list[str]] = {}
        for ammo, guns in config.ammo_groups.items():
            result[ammo] = [g.name for g in guns]
        return result
    except Exception:
        logger.warning("无法解析 Lua 脚本，使用默认枪械列表")
        return {
            "7.62": ["Beryl M762", "AKM", "Groza", "ACE32", "DP-28", "MK47"],
            "5.56": ["AUG", "M416", "P90", "M249", "M16A4", "SCAR-L", "QBZ", "G36C"],
            ".45": ["Tommy Gun"],
            "9mm": ["Vector", "Micro UZI", "UMP45", "MP5K"],
        }


class SettingsWindow:
    """设置窗口"""

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
        self.threshold_gun_var = tk.DoubleVar(value=float(self._recognition_config.get("threshold_gun", 0.5)))
        self.threshold_muzzle_var = tk.DoubleVar(value=float(self._recognition_config.get("threshold_muzzle", 0.25)))
        self.threshold_grip_var = tk.DoubleVar(value=float(self._recognition_config.get("threshold_grip", 0.3)))
        self.threshold_stock_var = tk.DoubleVar(value=float(self._recognition_config.get("threshold_stock", 0.35)))
        self.threshold_scope_var = tk.DoubleVar(value=float(self._recognition_config.get("threshold_scope", 0.35)))
        self.voice_enabled_var = tk.BooleanVar(value=voice_enabled)
        self.voice_volume_var = tk.IntVar(value=max(0, min(100, int(voice_volume))))
        self._default_event_enabled = self._build_default_event_enabled(voice_event_enabled)
        self.voice_event_vars: dict[str, tk.BooleanVar] = {
            event: tk.BooleanVar(value=self._default_event_enabled.get(event, True))
            for event in _VOICE_EVENT_LABELS
        }
        self._guns_by_ammo = _load_guns_from_lua()
        self._checkbox_vars: dict[str, dict[str, tk.BooleanVar]] = {}
        self._selected_gun: str | None = None
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
        self.window.title("枪械配置")
        self.window.resizable(True, True)
        self.window.attributes("-topmost", True)
        self.window.grab_set()
        self.window.geometry("520x650")

        main_frame = ttk.Frame(self.window, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._create_gun_section(main_frame, row=0)
        self._create_voice_section(main_frame, row=1)
        self._create_recognition_section(main_frame, row=2)
        self._create_buttons(main_frame, row=3)

        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

    # ---- 枪械配置区 ----

    def _create_gun_section(self, parent: ttk.Frame, row: int) -> None:
        frame = ttk.LabelFrame(parent, text="枪械配置（从 Lua 脚本读取）", padding=5)
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 5))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="点击枪械名称后，在下方勾选支持的配件").grid(
            row=0, column=0, sticky="w", pady=(0, 3)
        )

        tree_frame = ttk.Frame(frame)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("muzzle", "grip", "stock")
        self._tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", height=12)
        self._tree.heading("#0", text="枪械名称")
        self._tree.heading("muzzle", text="枪口")
        self._tree.heading("grip", text="握把")
        self._tree.heading("stock", text="枪托")
        self._tree.column("#0", width=180)
        self._tree.column("muzzle", width=60, anchor="center")
        self._tree.column("grip", width=60, anchor="center")
        self._tree.column("stock", width=60, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<ButtonRelease-1>", self._on_tree_click)
        self._populate_tree()

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=3, column=0, sticky="w", pady=(3, 0))
        ttk.Button(btn_row, text="添加枪械", command=self._on_add_gun, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="删除选中", command=self._on_delete_gun, width=10).pack(side=tk.LEFT)

    _CHECK = "\u2611"  # ☑
    _UNCHECK = "\u2610"  # ☐

    def _populate_tree(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)

        ammo_labels = {"7.62": "7.62mm", "5.56": "5.56mm", ".45": ".45 ACP", "9mm": "9mm"}

        for ammo, guns in self._guns_by_ammo.items():
            label = ammo_labels.get(ammo, ammo)
            parent_id = self._tree.insert("", "end", text=label, open=True, values=("", "", ""))
            for gun in guns:
                ga = self.gun_attachments.get(gun, {"muzzle": True, "grip": True, "stock": True})
                m = self._CHECK if ga.get("muzzle", True) else self._UNCHECK
                g = self._CHECK if ga.get("grip", True) else self._UNCHECK
                s = self._CHECK if ga.get("stock", True) else self._UNCHECK
                self._tree.insert(parent_id, "end", iid=gun, text=gun, values=(m, g, s))

    def _on_tree_select(self, event) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        gun = sel[0]
        if gun in self._guns_by_ammo:
            return
        self._selected_gun = gun
        self._show_attachment_detail(gun)

    def _on_tree_click(self, event) -> None:
        """点击树形列表中的勾选框列，直接切换状态"""
        item = self._tree.identify_row(event.y)
        col = self._tree.identify_column(event.x)
        if not item or item in self._guns_by_ammo:
            return
        col_index = {"#1": "muzzle", "#2": "grip", "#3": "stock"}.get(col)
        if not col_index:
            return
        if item not in self._checkbox_vars:
            self._checkbox_vars[item] = {}
            ga = self.gun_attachments.get(item, {"muzzle": True, "grip": True, "stock": True})
            for cat in _ATTACH_COLS:
                self._checkbox_vars[item][cat] = tk.BooleanVar(value=ga.get(cat, True))
        var = self._checkbox_vars[item][col_index]
        var.set(not var.get())
        self._sync_tree_display(item)
        self._selected_gun = item
        self._show_attachment_detail(item)

    def _show_attachment_detail(self, gun: str) -> None:
        if hasattr(self, "_detail_frame"):
            self._detail_frame.destroy()

        self._detail_frame = ttk.LabelFrame(self._tree.master.master, text=f"配件配置: {gun}", padding=5)
        self._detail_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        ga = self.gun_attachments.get(gun, {"muzzle": True, "grip": True, "stock": True})
        self._checkbox_vars[gun] = {}
        for i, cat in enumerate(_ATTACH_COLS):
            var = tk.BooleanVar(value=ga.get(cat, True))
            self._checkbox_vars[gun][cat] = var
            ttk.Checkbutton(
                self._detail_frame, text=_ATTACH_LABELS[cat], variable=var,
                command=lambda g=gun: self._sync_tree_display(g),
            ).grid(row=0, column=i, padx=10, pady=3)

    def _sync_tree_display(self, gun: str) -> None:
        if gun not in self._checkbox_vars:
            return
        vars = self._checkbox_vars[gun]
        m = self._CHECK if vars["muzzle"].get() else self._UNCHECK
        g = self._CHECK if vars["grip"].get() else self._UNCHECK
        s = self._CHECK if vars["stock"].get() else self._UNCHECK
        self._tree.item(gun, values=(m, g, s))

    # ---- 语音设置区 ----

    def _create_voice_section(self, parent: ttk.Frame, row: int) -> None:
        frame = ttk.LabelFrame(parent, text="语音提示", padding=5)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))

        ttk.Checkbutton(frame, text="启用语音提示", variable=self.voice_enabled_var).grid(
            row=0, column=0, sticky="w"
        )

        vol_frame = ttk.Frame(frame)
        vol_frame.grid(row=1, column=0, sticky="ew", pady=2)
        vol_frame.columnconfigure(1, weight=1)
        ttk.Label(vol_frame, text="音量", width=6).grid(row=0, column=0)
        self._volume_value_label = ttk.Label(vol_frame, text=f"{self.voice_volume_var.get()}%", width=5)
        self._volume_value_label.grid(row=0, column=2)
        ttk.Scale(vol_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                  variable=self.voice_volume_var, command=self._on_volume_change).grid(row=0, column=1, sticky="ew")

        for idx, (event, label) in enumerate(_VOICE_EVENT_LABELS.items()):
            ttk.Checkbutton(frame, text=label, variable=self.voice_event_vars[event]).grid(
                row=2 + idx, column=0, sticky="w"
            )
            ttk.Button(frame, text="试听", width=5,
                       command=lambda e=event: self._on_preview(e)).grid(row=2 + idx, column=1, padx=5)

    # ---- 自动识别区 ----

    def _create_recognition_section(self, parent: ttk.Frame, row: int) -> None:
        frame = ttk.LabelFrame(parent, text="自动识别", padding=5)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))

        ttk.Checkbutton(frame, text="启用自动识别", variable=self.rec_enabled_var).grid(
            row=0, column=0, sticky="w"
        )

        hotkey_frame = ttk.Frame(frame)
        hotkey_frame.grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(hotkey_frame, text="识别快捷键").pack(side=tk.LEFT)
        ttk.Entry(hotkey_frame, textvariable=self.rec_hotkey_var, width=8, justify="center").pack(side=tk.LEFT, padx=5)

        path_frame = ttk.Frame(frame)
        path_frame.grid(row=2, column=0, sticky="ew", pady=2)
        ttk.Label(path_frame, text="rec.lua路径").pack(side=tk.LEFT)
        ttk.Entry(path_frame, textvariable=self.rec_path_var, width=35).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        ttk.Label(frame, text="留空使用默认路径（程序目录下pubg_rec.lua）",
                  font=("Arial", 8), foreground="gray").grid(row=3, column=0, sticky="w")

        ttk.Button(frame, text="导出GHUB脚本", command=self._on_export_lua).grid(
            row=4, column=0, sticky="w", pady=(3, 0)
        )

        thr_frame = ttk.LabelFrame(frame, text="识别阈值（0~1，越低越宽松）", padding=3)
        thr_frame.grid(row=5, column=0, sticky="ew", pady=(5, 0))

        thr_items = [
            ("枪械", self.threshold_gun_var),
            ("枪口", self.threshold_muzzle_var),
            ("握把", self.threshold_grip_var),
            ("枪托", self.threshold_stock_var),
            ("倍镜", self.threshold_scope_var),
        ]
        for i, (label, var) in enumerate(thr_items):
            ttk.Label(thr_frame, text=label, width=5).grid(row=0, column=i * 2, padx=(3, 0))
            ttk.Spinbox(thr_frame, textvariable=var, from_=0.0, to=1.0, increment=0.05,
                        width=5, format="%.2f").grid(row=0, column=i * 2 + 1, padx=(0, 5))

    # ---- 按钮区 ----

    def _create_buttons(self, parent: ttk.Frame, row: int) -> None:
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=row, column=0, pady=(5, 0))
        ttk.Button(btn_frame, text="保存", command=self._on_save, width=10).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=10).pack(side=tk.LEFT, padx=8)

    # ---- 回调 ----

    def _on_volume_change(self, value: str) -> None:
        try:
            current = int(float(value))
        except (TypeError, ValueError):
            return
        if hasattr(self, "_volume_value_label"):
            self._volume_value_label.config(text=f"{current}%")

    def _on_preview(self, event: str) -> None:
        if self.voice_player is None:
            return
        self.voice_player.volume = int(self.voice_volume_var.get())
        self.voice_player.event_enabled = {
            key: bool(var.get()) for key, var in self.voice_event_vars.items()
        }
        self.voice_player.play(event)

    def _on_add_gun(self) -> None:
        dialog = tk.Toplevel(self.window)
        dialog.title("添加枪械")
        dialog.attributes("-topmost", True)
        dialog.grab_set()
        dialog.geometry("300x120")

        ttk.Label(dialog, text="枪械名称:").pack(pady=(10, 0))
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=20).pack(pady=3)

        ttk.Label(dialog, text="弹药类型:").pack()
        ammo_var = tk.StringVar(value="5.56")
        ammo_combo = ttk.Combobox(dialog, textvariable=ammo_var, values=list(self._guns_by_ammo.keys()), width=10, state="readonly")
        ammo_combo.pack(pady=3)

        def confirm():
            name = name_var.get().strip()
            ammo = ammo_var.get().strip()
            if not name or not ammo:
                return
            if ammo not in self._guns_by_ammo:
                self._guns_by_ammo[ammo] = []
            if name in self._guns_by_ammo[ammo]:
                return
            self._guns_by_ammo[ammo].append(name)
            self.gun_attachments[name] = {"muzzle": True, "grip": True, "stock": True}
            self._populate_tree()
            dialog.destroy()

        ttk.Button(dialog, text="确定", command=confirm).pack(pady=5)

    def _on_delete_gun(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        gun = sel[0]
        if gun in self._guns_by_ammo:
            return
        for ammo, guns in self._guns_by_ammo.items():
            if gun in guns:
                guns.remove(gun)
                break
        self.gun_attachments.pop(gun, None)
        self._checkbox_vars.pop(gun, None)
        self._populate_tree()

    def _on_save(self) -> None:
        new_gun_attachments: dict[str, dict[str, bool]] = {}
        for ammo, guns in self._guns_by_ammo.items():
            for gun in guns:
                if gun in self._checkbox_vars:
                    new_gun_attachments[gun] = {
                        cat: var.get() for cat, var in self._checkbox_vars[gun].items()
                    }
                else:
                    ga = self.gun_attachments.get(gun, {"muzzle": True, "grip": True, "stock": True})
                    new_gun_attachments[gun] = ga

        voice_enabled = self.voice_enabled_var.get()
        voice_volume = int(self.voice_volume_var.get())
        voice_event_enabled = {
            event: bool(var.get()) for event, var in self.voice_event_vars.items()
        }
        self.on_save(self.shortcuts, new_gun_attachments, voice_enabled, voice_volume, voice_event_enabled)
        if self.on_recognition_save is not None:
            rec_cfg = {
                "enabled": self.rec_enabled_var.get(),
                "hotkey": self.rec_hotkey_var.get().strip() or "f2",
                "rec_path": self.rec_path_var.get().strip(),
                "threshold_gun": round(self.threshold_gun_var.get(), 2),
                "threshold_muzzle": round(self.threshold_muzzle_var.get(), 2),
                "threshold_grip": round(self.threshold_grip_var.get(), 2),
                "threshold_stock": round(self.threshold_stock_var.get(), 2),
                "threshold_scope": round(self.threshold_scope_var.get(), 2),
            }
            self.on_recognition_save(rec_cfg)
        self.window.destroy()

    def _on_export_lua(self) -> None:
        from tkinter import filedialog, messagebox
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
