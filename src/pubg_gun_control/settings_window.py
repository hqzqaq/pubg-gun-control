"""
设置窗口模块

枪械配置 + 配件勾选 + 语音设置 + 自动识别配置

@author huquanzhi
@since 2026-04-18 19:38
@version 3.1
"""

import logging
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from typing import Callable

from pynput import keyboard, mouse
from pynput.keyboard import Key
from pynput.mouse import Button

from pubg_gun_control.voice_prompt import VoicePlayer

logger = logging.getLogger(__name__)


def _get_project_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent

_VOICE_EVENT_LABELS: dict[str, str] = {
    "recoil_on": "压枪开启",
    "recoil_off": "压枪关闭",
    "lock_on": "模式锁定",
    "lock_off": "模式解锁",
    "locked_action": "锁定拦截",
}

_ATTACH_COLS = ("muzzle", "grip", "stock")
_ATTACH_LABELS = {"muzzle": "枪口", "grip": "握把", "stock": "枪托"}
_AMMO_LABELS = {"7.62": "7.62mm", "5.56": "5.56mm", "9mm": "9mm", ".45": "0.45mm"}


def _load_guns_from_lua(lua_path: str | None = None) -> dict[str, list[str]]:
    from pubg_gun_control.lua_parser import LuaBallisticParser
    from pubg_gun_control.config_manager import load_base_lua_path
    if lua_path is None:
        lua_path = load_base_lua_path()
    try:
        parser = LuaBallisticParser()
        config = parser.parse(lua_path)
        result: dict[str, list[str]] = {}
        # 保留原始 ammo key（如 ".45"），写回 lua 时才能匹配原 canUse 分组
        # UI 显示由 _AMMO_LABELS 做映射，避免数据层与显示层混淆
        for ammo, guns in config.ammo_groups.items():
            if ammo not in result:
                result[ammo] = []
            result[ammo].extend(g.name for g in guns)
        return result
    except Exception:
        logger.warning("无法解析 Lua 脚本，使用默认枪械列表")
        return {
            "7.62": ["Beryl M762", "AKM", "Groza", "ACE32", "MK47"],
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
            bool,
        ], None],
        voice_enabled: bool = True,
        voice_volume: int = 100,
        voice_event_enabled: dict[str, bool] | None = None,
        voice_player: VoicePlayer | None = None,
        recognition_config: dict | None = None,
        on_recognition_save: Callable[[dict], None] | None = None,
        overlay_visible: bool = True,
        recoil_hotkeys: dict[str, list[str]] | None = None,
    ) -> None:
        self.parent = parent
        self.shortcuts = list(shortcuts)
        self.gun_attachments = dict(gun_attachments)
        self.on_save = on_save
        self.voice_player = voice_player
        self._recognition_config = recognition_config or {}
        self.on_recognition_save = on_recognition_save
        default_hotkeys: dict[str, list[str]] = {"enable": ["caps_lock", "1"], "disable": ["tab", "2", "g", "3", "4", "5"]}
        self._recoil_hotkeys = dict(recoil_hotkeys) if recoil_hotkeys else default_hotkeys
        self._recoil_enable_list: list[str] = list(self._recoil_hotkeys.get("enable", default_hotkeys["enable"]))
        self._recoil_disable_list: list[str] = list(self._recoil_hotkeys.get("disable", default_hotkeys["disable"]))
        self._recording_for: str | None = None
        self._record_keyboard_listener: keyboard.Listener | None = None
        self._record_mouse_listener: mouse.Listener | None = None
        self.rec_enabled_var = tk.BooleanVar(value=bool(self._recognition_config.get("enabled", False)))
        self.rec_hotkey_var = tk.StringVar(value=str(self._recognition_config.get("hotkey", "f2")))
        self.rec_path_var = tk.StringVar(value=str(self._recognition_config.get("rec_path", "")))
        self.rec_template_dir_var = tk.StringVar(value=str(self._recognition_config.get("template_dir", "")))
        self.base_lua_path_var = tk.StringVar(value=str(self._recognition_config.get("base_lua_path", "")))
        self.threshold_gun_var = tk.DoubleVar(value=float(self._recognition_config.get("threshold_gun", 0.5)))
        self.threshold_muzzle_var = tk.DoubleVar(value=float(self._recognition_config.get("threshold_muzzle", 0.25)))
        self.threshold_grip_var = tk.DoubleVar(value=float(self._recognition_config.get("threshold_grip", 0.3)))
        self.threshold_stock_var = tk.DoubleVar(value=float(self._recognition_config.get("threshold_stock", 0.35)))
        self.threshold_scope_var = tk.DoubleVar(value=float(self._recognition_config.get("threshold_scope", 0.35)))
        self.voice_enabled_var = tk.BooleanVar(value=voice_enabled)
        self.voice_volume_var = tk.IntVar(value=max(0, min(100, int(voice_volume))))
        self.overlay_visible_var = tk.BooleanVar(value=overlay_visible)
        self._default_event_enabled = self._build_default_event_enabled(voice_event_enabled)
        self.voice_event_vars: dict[str, tk.BooleanVar] = {
            event: tk.BooleanVar(value=self._default_event_enabled.get(event, True))
            for event in _VOICE_EVENT_LABELS
        }
        from pubg_gun_control.config_manager import load_base_lua_path
        self._guns_by_ammo = _load_guns_from_lua(
            load_base_lua_path(self._recognition_config),
        )
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
        self.window.title("设置")
        self.window.resizable(True, True)
        self.window.attributes("-topmost", True)
        self.window.grab_set()
        self.window.geometry("700x650")

        main_frame = ttk.Frame(self.window, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        basic_tab = ttk.Frame(notebook, padding=8)
        gun_tab = ttk.Frame(notebook, padding=8)
        rec_tab = ttk.Frame(notebook, padding=8)
        voice_tab = ttk.Frame(notebook, padding=8)

        notebook.add(basic_tab, text="基础")
        notebook.add(gun_tab, text="枪械")
        notebook.add(rec_tab, text="识别")
        notebook.add(voice_tab, text="语音")

        basic_tab.columnconfigure(0, weight=1)
        gun_tab.columnconfigure(0, weight=1)
        gun_tab.rowconfigure(0, weight=1)
        rec_tab.columnconfigure(0, weight=1)
        voice_tab.columnconfigure(0, weight=1)

        self._create_overlay_section(basic_tab, row=0)
        self._create_recoil_hotkey_section(basic_tab, row=1)
        self._create_gun_section(gun_tab, row=0)
        self._create_recognition_section(rec_tab, row=0)
        self._create_voice_section(voice_tab, row=0)
        self._create_buttons(main_frame, row=1)

        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

    # ---- 界面设置区 ----

    def _create_overlay_section(self, parent: ttk.Frame, row: int) -> None:
        frame = ttk.LabelFrame(parent, text="界面设置", padding=5)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        ttk.Checkbutton(frame, text="显示左上角浮窗", variable=self.overlay_visible_var).grid(
            row=0, column=0, sticky="w"
        )

    # ---- 压枪开关快捷键区 ----

    _RECOIL_HOTKEY_OPTIONS: tuple[str, ...] = (
        "caps_lock", "tab", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
        "1", "2", "3", "4", "5", "g", "mouse_forward", "mouse_backward", "mouse_middle",
    )

    _RECOIL_HOTKEY_LABELS: dict[str, str] = {
        "caps_lock": "CapsLock",
        "tab": "Tab",
        "mouse_forward": "鼠标前进键(G5)",
        "mouse_backward": "鼠标后退键(G4)",
        "mouse_middle": "鼠标中键",
    }

    def _create_recoil_hotkey_section(self, parent: ttk.Frame, row: int) -> None:
        frame = ttk.LabelFrame(parent, text="压枪模式开关", padding=5)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        frame.columnconfigure((0, 1), weight=1)

        self._recoil_enable_listbox, self._recoil_enable_combo, self._recoil_enable_record_btn = self._build_recoil_hotkey_column(
            frame, row=0, column=0, title="开启压枪", items=self._recoil_enable_list,
            add_cmd=self._on_add_recoil_enable, remove_cmd=self._on_remove_recoil_enable,
            record_cmd=lambda: self._on_record_recoil_hotkey("enable"),
        )
        self._recoil_disable_listbox, self._recoil_disable_combo, self._recoil_disable_record_btn = self._build_recoil_hotkey_column(
            frame, row=0, column=1, title="关闭压枪", items=self._recoil_disable_list,
            add_cmd=self._on_add_recoil_disable, remove_cmd=self._on_remove_recoil_disable,
            record_cmd=lambda: self._on_record_recoil_hotkey("disable"),
        )

        ttk.Label(
            frame,
            text="通过控制键盘大小写状态实现，CapsLock 为切换开关，其他按键为独立开关；"
                 "可直接输入键名，如 space、alt_l、shift_r、a、0、mouse_forward 等",
            font=("Arial", 8), foreground="gray",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 0))

    def _build_recoil_hotkey_column(
        self,
        parent: ttk.Frame,
        row: int,
        column: int,
        title: str,
        items: list[str],
        add_cmd: Callable[[], None],
        remove_cmd: Callable[[], None],
        record_cmd: Callable[[], None],
    ) -> tuple[tk.Listbox, ttk.Combobox, ttk.Button]:
        col_frame = ttk.LabelFrame(parent, text=title, padding=3)
        col_frame.grid(row=row, column=column, sticky="nsew", padx=3, pady=3)
        col_frame.rowconfigure(0, weight=1)
        col_frame.columnconfigure(0, weight=1)

        listbox = tk.Listbox(col_frame, height=4, exportselection=False)
        listbox.grid(row=0, column=0, columnspan=3, sticky="nsew")
        for item in items:
            listbox.insert(tk.END, self._RECOIL_HOTKEY_LABELS.get(item, item))

        combo = ttk.Combobox(col_frame, values=list(self._RECOIL_HOTKEY_OPTIONS), width=14, state="normal")
        combo.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(3, 0))

        btn_frame = ttk.Frame(col_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(3, 0))
        ttk.Button(btn_frame, text="添加", command=add_cmd, width=5).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text="删除", command=remove_cmd, width=5).pack(side=tk.LEFT, padx=(0, 3))
        record_btn = ttk.Button(btn_frame, text="录制", command=record_cmd, width=5)
        record_btn.pack(side=tk.LEFT)

        return listbox, combo, record_btn

    def _add_recoil_hotkey(self, listbox: tk.Listbox, combo: ttk.Combobox) -> None:
        key = combo.get().strip().lower()
        if not key:
            return
        existing = [listbox.get(i) for i in range(listbox.size())]
        label = self._RECOIL_HOTKEY_LABELS.get(key, key)
        if label not in existing:
            listbox.insert(tk.END, label)
        combo.set("")

    def _remove_recoil_hotkey(self, listbox: tk.Listbox) -> None:
        selection = listbox.curselection()
        if selection:
            listbox.delete(selection[0])

    def _on_add_recoil_enable(self) -> None:
        self._add_recoil_hotkey(self._recoil_enable_listbox, self._recoil_enable_combo)

    def _on_remove_recoil_enable(self) -> None:
        self._remove_recoil_hotkey(self._recoil_enable_listbox)

    def _on_add_recoil_disable(self) -> None:
        self._add_recoil_hotkey(self._recoil_disable_listbox, self._recoil_disable_combo)

    def _on_remove_recoil_disable(self) -> None:
        self._remove_recoil_hotkey(self._recoil_disable_listbox)

    def _on_record_recoil_hotkey(self, target: str) -> None:
        """开始录制压枪开关热键，target 为 enable 或 disable。"""
        if self._recording_for is not None:
            self._stop_recording()
            return
        self._recording_for = target
        messagebox.showinfo("录制热键", "请在 5 秒内按下要录制的按键", parent=self.window)
        self._update_record_buttons()

        try:
            self._record_keyboard_listener = keyboard.Listener(
                on_press=self._on_record_key_press,
                suppress=False,
            )
            self._record_mouse_listener = mouse.Listener(
                on_click=self._on_record_mouse_click,
                suppress=False,
            )
            self._record_keyboard_listener.start()
            self._record_mouse_listener.start()
            self.window.after(5000, self._stop_recording)
        except Exception as exc:
            logger.error("启动热键录制监听失败: %s", exc)
            self._stop_recording()

    def _on_record_key_press(self, key: Key | keyboard.KeyCode | None) -> None:
        hotkey_name = self._pynput_key_to_name(key)
        if hotkey_name and hotkey_name not in {"alt_l", "alt_r", "alt_gr", "ctrl_l", "ctrl_r", "shift_l", "shift_r", "cmd_l", "cmd_r"}:
            self.window.after(0, lambda: self._apply_recorded_key(hotkey_name))

    def _on_record_mouse_click(self, x: int, y: int, button: Button, pressed: bool) -> None:
        if not pressed:
            return
        mouse_map = {
            Button.x2: "mouse_forward",
            Button.x1: "mouse_backward",
            Button.middle: "mouse_middle",
        }
        hotkey_name = mouse_map.get(button)
        if hotkey_name:
            self.window.after(0, lambda: self._apply_recorded_key(hotkey_name))

    def _apply_recorded_key(self, hotkey_name: str) -> None:
        if self._recording_for == "enable":
            self._recoil_enable_combo.set(hotkey_name)
            self._add_key_to_listbox(self._recoil_enable_listbox, hotkey_name)
        elif self._recording_for == "disable":
            self._recoil_disable_combo.set(hotkey_name)
            self._add_key_to_listbox(self._recoil_disable_listbox, hotkey_name)
        self._stop_recording()

    def _add_key_to_listbox(self, listbox: tk.Listbox, key: str) -> None:
        label = self._RECOIL_HOTKEY_LABELS.get(key, key)
        existing = [listbox.get(i) for i in range(listbox.size())]
        if label not in existing:
            listbox.insert(tk.END, label)

    def _stop_recording(self) -> None:
        if self._record_keyboard_listener is not None:
            try:
                self._record_keyboard_listener.stop()
            except Exception:
                pass
            self._record_keyboard_listener = None
        if self._record_mouse_listener is not None:
            try:
                self._record_mouse_listener.stop()
            except Exception:
                pass
            self._record_mouse_listener = None
        self._recording_for = None
        self._update_record_buttons()

    def _update_record_buttons(self) -> None:
        text = "停止" if self._recording_for else "录制"
        self._recoil_enable_record_btn.config(text=text)
        self._recoil_disable_record_btn.config(text=text)

    @staticmethod
    def _pynput_key_to_name(key: Key | keyboard.KeyCode | None) -> str | None:
        if key is None:
            return None
        if isinstance(key, Key):
            return key.name
        if hasattr(key, "char") and key.char:
            return key.char.lower()
        return None

    def _get_recoil_hotkeys(self) -> dict[str, list[str]]:
        label_to_key = {label: key for key, label in self._RECOIL_HOTKEY_LABELS.items()}
        enable_labels = [self._recoil_enable_listbox.get(i) for i in range(self._recoil_enable_listbox.size())]
        disable_labels = [self._recoil_disable_listbox.get(i) for i in range(self._recoil_disable_listbox.size())]
        return {
            "enable": [label_to_key.get(label, label) for label in enable_labels],
            "disable": [label_to_key.get(label, label) for label in disable_labels],
        }

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

        tpl_frame = ttk.Frame(frame)
        tpl_frame.grid(row=4, column=0, sticky="ew", pady=2)
        ttk.Label(tpl_frame, text="模板目录").pack(side=tk.LEFT)
        ttk.Entry(tpl_frame, textvariable=self.rec_template_dir_var, width=35).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        ttk.Label(frame, text="留空使用默认路径（exe目录下templates/）",
                  font=("Arial", 8), foreground="gray").grid(row=5, column=0, sticky="w")

        base_frame = ttk.Frame(frame)
        base_frame.grid(row=6, column=0, sticky="ew", pady=2)
        ttk.Label(base_frame, text="基础脚本").pack(side=tk.LEFT)
        ttk.Entry(base_frame, textvariable=self.base_lua_path_var, width=35).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(base_frame, text="浏览", command=self._on_browse_base_lua, width=5).pack(side=tk.LEFT)

        ttk.Label(frame, text="留空使用默认路径（exe目录下1.2.2-2024.5.20.-GHUB.-github.lua）",
                  font=("Arial", 8), foreground="gray").grid(row=7, column=0, sticky="w")

        export_frame = ttk.Frame(frame)
        export_frame.grid(row=8, column=0, sticky="w", pady=(3, 0))
        ttk.Button(export_frame, text="导出GHUB脚本", command=self._on_export_lua).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(export_frame, text="导出dofile脚本（编辑器保存自动生效）", command=self._on_export_dofile).pack(side=tk.LEFT)

        thr_frame = ttk.LabelFrame(frame, text="识别阈值（0~1，越低越宽松）", padding=3)
        thr_frame.grid(row=9, column=0, sticky="ew", pady=(5, 0))

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
        from pubg_gun_control.config_manager import load_base_lua_path
        lua_path = load_base_lua_path(self._recognition_config)
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
        overlay_visible = self.overlay_visible_var.get()
        recoil_hotkeys = self._get_recoil_hotkeys()
        self.on_save(self.shortcuts, new_gun_attachments, voice_enabled, voice_volume, voice_event_enabled, overlay_visible, recoil_hotkeys)
        if self.on_recognition_save is not None:
            rec_cfg = {
                "enabled": self.rec_enabled_var.get(),
                "hotkey": self.rec_hotkey_var.get().strip() or "f2",
                "rec_path": self.rec_path_var.get().strip(),
                "template_dir": self.rec_template_dir_var.get().strip(),
                "base_lua_path": self.base_lua_path_var.get().strip(),
                "threshold_gun": round(self.threshold_gun_var.get(), 2),
                "threshold_muzzle": round(self.threshold_muzzle_var.get(), 2),
                "threshold_grip": round(self.threshold_grip_var.get(), 2),
                "threshold_stock": round(self.threshold_stock_var.get(), 2),
                "threshold_scope": round(self.threshold_scope_var.get(), 2),
            }
            self.on_recognition_save(rec_cfg)

    def _get_effective_base_lua_path(self) -> str:
        from pubg_gun_control.config_manager import load_base_lua_path
        configured = self.base_lua_path_var.get().strip()
        if configured:
            self._recognition_config["base_lua_path"] = configured
        return load_base_lua_path(self._recognition_config)

    def _on_browse_base_lua(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="选择基础GHUB脚本",
            defaultextension=".lua",
            filetypes=[("Lua脚本", "*.lua")],
            initialfile="1.2.2-2024.5.20.-GHUB.-github.lua",
        )
        if path:
            self.base_lua_path_var.set(path)

    def _on_export_lua(self) -> None:
        from tkinter import filedialog, messagebox
        from pubg_gun_control.lua_generator import generate_auto_recognize_script

        source = self._get_effective_base_lua_path()
        rec_path = self.rec_path_var.get().strip()
        if not rec_path:
            rec_path = str(_get_project_root() / "pubg_rec.lua")

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

        project_root = _get_project_root()
        source = self._get_effective_base_lua_path()
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
            # 若 pubg_config.lua 比基础脚本新，说明编辑器保存后基础脚本未同步
            # （或用户手动改过 pubg_config.lua），此时跳过覆盖以保护新增数据
            regenerate_config = True
            config_file = Path(config_path)
            source_file = Path(source)
            if config_file.exists() and source_file.exists():
                if config_file.stat().st_mtime > source_file.stat().st_mtime:
                    regenerate_config = False

            wrapper, config = generate_dofile_files(
                source, config_output=config_path, wrapper_output=save_path,
                rec_path=rec_path, regenerate_config=regenerate_config,
            )
            skip_note = "" if regenerate_config else "\n\n注意：pubg_config.lua 比基础脚本新，已跳过覆盖以保留编辑器最新保存的数据。"
            messagebox.showinfo(
                "导出成功",
                f"包装脚本: {wrapper}\n"
                f"配置文件: {config}\n\n"
                f"使用方法:\n"
                f"1. 将包装脚本粘贴到 GHUB\n"
                f"2. 用编辑器修改弹道参数并保存\n"
                f"3. CapsLock 开关时 GHUB 自动加载最新配置{skip_note}",
            )
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def _on_cancel(self) -> None:
        self.window.destroy()
