"""
设置窗口模块

枪械配置 + 配件勾选 + 语音设置 + 自动识别配置

@author huquanzhi
@since 2026-04-18 19:38
@version 3.1
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
_AMMO_LABELS = {"7.62": "7.62mm", "5.56": "5.56mm", "9mm": "9mm"}


def _load_guns_from_lua() -> dict[str, list[str]]:
    from pubg_gun_control.lua_parser import LuaBallisticParser
    lua_path = str(Path(__file__).resolve().parent.parent.parent / "1.2.2-2024.5.20.-GHUB.-github.lua")
    try:
        parser = LuaBallisticParser()
        config = parser.parse(lua_path)
        result: dict[str, list[str]] = {}
        for ammo, guns in config.ammo_groups.items():
            key = "9mm" if ammo == ".45" else ammo
            if key not in result:
                result[key] = []
            result[key].extend(g.name for g in guns)
        return result
    except Exception:
        logger.warning("无法解析 Lua 脚本，使用默认枪械列表")
        return {
            "7.62": ["Beryl M762", "AKM", "Groza", "ACE32", "DP-28", "MK47"],
            "5.56": ["AUG", "M416", "P90", "M249", "M16A4", "SCAR-L", "QBZ", "G36C"],
            "9mm": ["Tommy Gun", "Vector", "Micro UZI", "UMP45", "MP5K"],
        }


class SettingsWindow:

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
        self._init_all_checkbox_vars()
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

    def _init_all_checkbox_vars(self) -> None:
        for ammo, guns in self._guns_by_ammo.items():
            for gun in guns:
                ga = self.gun_attachments.get(gun, {"muzzle": True, "grip": True, "stock": True})
                self._checkbox_vars[gun] = {
                    cat: tk.BooleanVar(value=ga.get(cat, True)) for cat in _ATTACH_COLS
                }

    def _get_gun_vars(self, gun: str) -> dict[str, tk.BooleanVar]:
        if gun not in self._checkbox_vars:
            self._checkbox_vars[gun] = {cat: tk.BooleanVar(value=True) for cat in _ATTACH_COLS}
        return self._checkbox_vars[gun]

    def _create_window(self) -> None:
        self.window = tk.Toplevel(self.parent)
        self.window.title("枪械配置")
        self.window.resizable(True, True)
        self.window.attributes("-topmost", True)
        self.window.grab_set()
        self.window.geometry("650x800")

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
        frame = ttk.LabelFrame(parent, text="枪械配置", padding=5)
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 5))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="点击行选中枪械，点击枪口/握把/枪托列切换勾选状态").grid(
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

        self._tree.tag_configure("on", foreground="#2e7d32")
        self._tree.tag_configure("off", foreground="#9e9e9e")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._populate_tree()
        self._tree.bind("<ButtonRelease-1>", self._on_tree_click)

        detail_outer = ttk.Frame(frame)
        detail_outer.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        self._detail_frame = ttk.LabelFrame(detail_outer, text="选中枪械的配件", padding=5)
        self._detail_frame.pack(fill=tk.X)
        self._detail_label = ttk.Label(self._detail_frame, text="请在上方点击枪械行")
        self._detail_label.grid(row=0, column=0, columnspan=6)
        self._detail_checkbuttons: dict[str, ttk.Checkbutton] = {}

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=3, column=0, sticky="w", pady=(3, 0))
        ttk.Button(btn_row, text="添加枪械", command=self._on_add_gun, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="删除选中", command=self._on_delete_gun, width=10).pack(side=tk.LEFT)

    def _populate_tree(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        for ammo, guns in self._guns_by_ammo.items():
            label = _AMMO_LABELS.get(ammo, ammo)
            parent_id = self._tree.insert("", "end", text=label, open=True, values=("", "", ""))
            for gun in guns:
                self._insert_gun_row(parent_id, gun)

    def _insert_gun_row(self, parent: str, gun: str) -> None:
        vars = self._get_gun_vars(gun)
        vals = []
        tags = []
        for cat in _ATTACH_COLS:
            if vars[cat].get():
                vals.append("[x]")
                tags.append("on")
            else:
                vals.append("[ ]")
                tags.append("off")
        self._tree.insert(parent, "end", iid=gun, text=gun, values=vals, tags=tuple(tags))

    def _refresh_gun_row(self, gun: str) -> None:
        vars = self._get_gun_vars(gun)
        vals = []
        tags = []
        for cat in _ATTACH_COLS:
            if vars[cat].get():
                vals.append("[x]")
                tags.append("on")
            else:
                vals.append("[ ]")
                tags.append("off")
        self._tree.item(gun, values=vals, tags=tuple(tags))

    def _on_tree_click(self, event) -> None:
        item = self._tree.identify_row(event.y)
        col = self._tree.identify_column(event.x)

        if not item or item in self._guns_by_ammo:
            return

        self._tree.selection_set(item)
        col_map = {"#1": "muzzle", "#2": "grip", "#3": "stock"}
        col_name = col_map.get(col)

        if col_name:
            vars = self._get_gun_vars(item)
            vars[col_name].set(not vars[col_name].get())
            self._refresh_gun_row(item)

        self._show_detail_panel(item)

    def _show_detail_panel(self, gun: str) -> None:
        for w in self._detail_frame.winfo_children():
            w.destroy()

        vars = self._get_gun_vars(gun)
        ttk.Label(self._detail_frame, text=gun, font=("Arial", 10, "bold")).grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, 3)
        )
        for i, cat in enumerate(_ATTACH_COLS):
            cb = ttk.Checkbutton(
                self._detail_frame, text=_ATTACH_LABELS[cat], variable=vars[cat],
                command=lambda g=gun: self._refresh_gun_row(g),
            )
            cb.grid(row=1, column=i * 2, padx=(0, 10), sticky="w")

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
        ttk.Button(frame, text="导出dofile脚本（编辑器保存自动生效）", command=self._on_export_dofile).grid(
            row=4, column=1, columnspan=2, sticky="w", pady=(3, 0), padx=(10, 0)
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
        dialog.geometry("300x150")

        ttk.Label(dialog, text="枪械名称:").pack(pady=(10, 0))
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=20).pack(pady=3)

        ttk.Label(dialog, text="弹药类型:").pack()
        ammo_var = tk.StringVar(value="5.56")
        ttk.Combobox(dialog, textvariable=ammo_var, values=list(self._guns_by_ammo.keys()),
                     width=10, state="readonly").pack(pady=3)

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
            self._checkbox_vars[name] = {cat: tk.BooleanVar(value=True) for cat in _ATTACH_COLS}
            self.gun_attachments[name] = {"muzzle": True, "grip": True, "stock": True}
            self._sync_lua_canuse(name, ammo, add=True)
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
        ammo = None
        for a, guns in self._guns_by_ammo.items():
            if gun in guns:
                guns.remove(gun)
                ammo = a
                break
        self.gun_attachments.pop(gun, None)
        self._checkbox_vars.pop(gun, None)
        if ammo:
            self._sync_lua_canuse(gun, ammo, add=False)
        self._populate_tree()

    def _sync_lua_canuse(self, gun_name: str, ammo: str, add: bool) -> None:
        """同步枪械变更到 Lua 脚本的 canUse"""
        from pubg_gun_control.lua_parser import LuaBallisticParser, BallisticConfig, GunCoefficients
        lua_path = str(Path(__file__).resolve().parent.parent.parent / "1.2.2-2024.5.20.-GHUB.-github.lua")
        try:
            parser = LuaBallisticParser()
            config = parser.parse(lua_path)

            if add:
                if ammo not in config.ammo_groups:
                    config.ammo_groups[ammo] = []
                exists = any(g.name == gun_name for g in config.ammo_groups[ammo])
                if not exists:
                    config.ammo_groups[ammo].append(GunCoefficients(
                        name=gun_name, mode=1,
                        coef=1.0, crouch=0.8, breath=1.3,
                        bare=1.25, full=2.0, prone=0.5,
                        scope2x=1.1, scope3x=0.7,
                    ))
            else:
                if ammo in config.ammo_groups:
                    config.ammo_groups[ammo] = [
                        g for g in config.ammo_groups[ammo] if g.name != gun_name
                    ]

            parser.serialize(config, lua_path, backup=True)
            logger.info("Lua canUse 已更新: %s %s (%s)", "添加" if add else "删除", gun_name, ammo)
        except Exception:
            logger.exception("同步 Lua canUse 失败")

    def _on_save(self) -> None:
        new_gun_attachments: dict[str, dict[str, bool]] = {}
        for ammo, guns in self._guns_by_ammo.items():
            for gun in guns:
                if gun in self._checkbox_vars:
                    new_gun_attachments[gun] = {cat: var.get() for cat, var in self._checkbox_vars[gun].items()}
                else:
                    new_gun_attachments[gun] = self.gun_attachments.get(
                        gun, {"muzzle": True, "grip": True, "stock": True}
                    )

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

    def _on_export_dofile(self) -> None:
        from tkinter import filedialog, messagebox
        from pubg_gun_control.lua_generator import generate_dofile_files

        project_root = Path(__file__).resolve().parent.parent.parent
        source = str(project_root / "1.2.2-2024.5.20.-GHUB.-github.lua")
        config_path = str(project_root / "pubg_config.lua")
        rec_path = self.rec_path_var.get().strip()
        if not rec_path:
            rec_path = str(project_root / "pubg_rec.lua")

        save_path = filedialog.asksaveasfilename(
            title="导出dofile包装脚本",
            defaultextension=".lua",
            filetypes=[("Lua脚本", "*.lua")],
            initialfile="ghub_dofile_wrapper.lua",
        )
        if not save_path:
            return
        try:
            wrapper, config = generate_dofile_files(
                source, config_output=config_path, wrapper_output=save_path, rec_path=rec_path,
            )
            messagebox.showinfo(
                "导出成功",
                f"包装脚本: {wrapper}\n"
                f"配置文件: {config}\n\n"
                f"使用方法:\n"
                f"1. 将包装脚本粘贴到 GHUB\n"
                f"2. 用编辑器修改弹道参数并保存\n"
                f"3. CapsLock 开关时 GHUB 自动加载最新配置",
            )
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def _on_cancel(self) -> None:
        self.window.destroy()
