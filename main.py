"""
PUBG Gun Control 主程序入口

@author hqzqaq
@since 2026-03-30 19:49
@version 1.0
"""

import logging
import subprocess
import sys
import threading
import time
from pathlib import Path

import keyboard
from pynput import keyboard as pynput_keyboard

from pubg_gun_control.config_manager import (
    load_config,
    save_config,
    load_attachments,
    load_gun_attachments,
    load_voice_enabled,
    load_voice_volume,
    load_voice_event_enabled,
    load_overlay_visible,
    load_recoil_hotkeys,
    load_recognition,
    save_recognition,
    ensure_base_lua_script,
    load_base_lua_path,
)
from pubg_gun_control.input_listener import InputListener
from pubg_gun_control.overlay_window import OverlayWindow
from pubg_gun_control.voice_prompt import VoicePlayer
from pubg_gun_control.settings_window import SettingsWindow
from pubg_gun_control.tray_icon import TrayIcon
from pubg_gun_control.rec_lua_writer import RecLuaWriter
from pubg_gun_control.lua_parser import LuaBallisticParser

PROJECT_ROOT = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)


class GunControlApp:
    """PUBG枪械控制应用主类"""

    def __init__(self) -> None:
        self.overlay = OverlayWindow()
        self.voice_player = VoicePlayer()
        self.input_listener: InputListener | None = None
        self.tray_icon: TrayIcon | None = None
        self._running = False
        self._lock = threading.Lock()
        self._shortcuts: list[dict[str, str]] = load_config()
        self._attachments: list[dict[str, str]] = load_attachments()
        self._gun_attachments: dict[str, dict[str, bool]] = load_gun_attachments()
        self._voice_enabled: bool = load_voice_enabled()
        self._voice_volume: int = load_voice_volume()
        self._voice_event_enabled: dict[str, bool] = load_voice_event_enabled()
        self._overlay_visible: bool = load_overlay_visible()
        self._recoil_hotkeys: dict[str, list[str]] = load_recoil_hotkeys()
        self.voice_player.enabled = self._voice_enabled
        self.voice_player.volume = self._voice_volume
        self.voice_player.event_enabled = self._voice_event_enabled

        ensure_base_lua_script()
        self._recognition_config: dict = load_recognition()
        self._recognizer = None
        rec_path = self._recognition_config.get("rec_path") or None
        self._rec_lua_writer = RecLuaWriter(rec_path)
        self._hotkey_listener = None
        self._editor_process: subprocess.Popen | None = None
        # 枪名映射：{小写枪名: canUse表中的实际枪名}，用于识别结果大小写不敏感匹配
        self._gun_name_map: dict[str, str] = {}
        self._gun_name_map_mtime: float = 0.0

    def _on_gun_selected(self, gun_name: str) -> None:
        with self._lock:
            if self.overlay.is_created():
                self.overlay.update_text(gun_name)

    def _on_lock_changed(self, locked: bool) -> None:
        with self._lock:
            if self.overlay.is_created():
                self.overlay.set_locked(locked)
            status = "已锁定" if locked else "已解锁"
            logger.info("枪械切换%s", status)

    def _on_scope_changed(self, scope_mode: int) -> None:
        with self._lock:
            if self.overlay.is_created():
                self.overlay.set_scope_mode(scope_mode)
            logger.info("倍镜模式切换为 %d 倍镜", scope_mode)

    _ATTACHMENT_SHORT: dict[str, dict[str, str]] = {
        "muzzle": {"无": "无", "补偿器": "补偿器", "消焰器": "消焰器", "消音器": "消音器", "制退器": "制退器"},
        "grip": {"无": "无", "垂直": "垂直握把", "斜向": "斜向握把", "拇指": "拇指握把", "半截": "半截握把", "轻型": "轻型握把"},
        "stock": {"无": "无", "战术": "战术枪托", "重型": "重型枪托"},
    }

    def _on_attachment_changed(self, category: str, name: str) -> None:
        short = self._ATTACHMENT_SHORT.get(category, {}).get(name, name)
        with self._lock:
            if self.overlay.is_created():
                self.overlay.update_attachment(f"{category}:{short}")
        logger.info("配件切换: %s -> %s", category, short)

    def _on_reset(self) -> None:
        with self._lock:
            if self.overlay.is_created():
                self.overlay.update_text("无")
                self.overlay.set_scope_mode(1)
                for cat in ("muzzle", "grip", "stock"):
                    self.overlay.update_attachment(f"{cat}:无")
        logger.info("已重置所有状态")

    _ATTACHMENT_DISPLAY: dict[str, dict[int, str]] = {
        "muzzle": {1: "无", 2: "补偿器", 3: "消焰器", 4: "消音器", 5: "制退器"},
        "grip":   {1: "无", 2: "垂直握把", 3: "斜向握把", 4: "拇指握把", 5: "半截握把", 6: "轻型握把"},
        "stock":  {1: "无", 2: "战术枪托", 3: "重型枪托"},
    }
    _SCOPE_DISPLAY: dict[int, str] = {1: "1倍", 2: "2倍", 3: "3倍", 4: "4倍", 6: "6倍"}

    def _load_gun_name_map(self) -> None:
        """从基础脚本加载枪名映射表（小写 → canUse 表实际枪名）。

        模板文件名大小写可能与 lua 配置表不一致（如 K2.png vs pubg["k2"]），
        识别结果需经此映射转换为 canUse 表中的实际枪名，GHUB 脚本才能找到弹道函数。
        """
        try:
            parser = LuaBallisticParser()
            recognition = load_recognition()
            base_lua_path = load_base_lua_path(recognition)
            config = parser.parse(base_lua_path)
            self._gun_name_map = {
                gun.name.lower(): gun.name
                for ammo_guns in config.ammo_groups.values()
                for gun in ammo_guns
                if gun.mode != 0
            }
            self._gun_name_map_mtime = Path(base_lua_path).stat().st_mtime
            logger.info("已加载 %d 把枪械名映射", len(self._gun_name_map))
        except Exception as exc:
            logger.warning("加载枪械名映射失败: %s", exc)
            self._gun_name_map = {}

    def _refresh_gun_name_map_if_stale(self) -> None:
        """若基础脚本比上次加载新（编辑器保存过），则重新加载枪名映射。"""
        try:
            recognition = load_recognition()
            base_lua_path = load_base_lua_path(recognition)
            current_mtime = Path(base_lua_path).stat().st_mtime
            if current_mtime != self._gun_name_map_mtime:
                logger.info("基础脚本已更新，重新加载枪名映射")
                self._load_gun_name_map()
        except Exception:
            pass

    def _normalize_gun_name(self, gun: str) -> str:
        """把识别结果转换为 canUse 表中的实际枪名（大小写不敏感）。"""
        if not gun:
            return gun
        return self._gun_name_map.get(gun.lower(), gun)

    def _trigger_recognition(self) -> None:
        if not self._recognizer:
            return
        # 基础脚本可能被编辑器修改，检查并刷新枪名映射
        self._refresh_gun_name_map_if_stale()
        try:
            result = self._recognizer.recognize_all()
            gun = result.get("gun") or ""
            # 与 canUse 表做大小写不敏感匹配，写入实际枪名
            # 模板文件名大小写可能与 lua 配置表不一致（如 K2.png vs pubg["k2"]）
            gun = self._normalize_gun_name(gun)
            scores = result.get("scores", {})
            self._rec_lua_writer.write(
                gun=gun,
                muzzle=result.get("muzzle", 1),
                grip=result.get("grip", 1),
                stock=result.get("stock", 1),
                scope=result.get("scope", 1),
            )
            with self._lock:
                if self.overlay.is_created():
                    display_text = gun if gun else "---"
                    if self.input_listener:
                        self.input_listener.set_auto_text(display_text)
                    for cat in ("muzzle", "grip", "stock"):
                        idx = result.get(cat, 1)
                        label = self._ATTACHMENT_DISPLAY.get(cat, {}).get(idx, "?")
                        self.overlay.update_attachment(f"{cat}:{label}")
                    self.overlay.set_scope_mode(result.get("scope", 1))
                    status = f"REC:{gun}" if gun else "REC:---"
                    self.overlay.update_recognition_status(status)
            muzzle_label = self._ATTACHMENT_DISPLAY["muzzle"].get(result.get("muzzle", 1), "?")
            grip_label = self._ATTACHMENT_DISPLAY["grip"].get(result.get("grip", 1), "?")
            stock_label = self._ATTACHMENT_DISPLAY["stock"].get(result.get("stock", 1), "?")
            scope_label = self._SCOPE_DISPLAY.get(result.get("scope", 1), "?")
            logger.info("[识别] 枪械=%s(%.2f) 枪口=%s(%.2f) 握把=%s(%.2f) 枪托=%s(%.2f) 倍镜=%s(%.2f)",
                        gun or "---", scores.get("gun", 0),
                        muzzle_label, scores.get("muzzle", 0),
                        grip_label, scores.get("grip", 0),
                        stock_label, scores.get("stock", 0),
                        scope_label, scores.get("scope", 0))
        except Exception:
            logger.exception("识别异常")

    def _on_exit(self) -> None:
        self.stop()

    def _on_settings(self) -> None:
        if self.overlay.root:
            self.overlay.root.after(0, self._open_settings)

    def _open_settings(self) -> None:
        SettingsWindow(
            self.overlay.root,
            self._shortcuts,
            self._gun_attachments,
            self._on_settings_saved,
            voice_enabled=self._voice_enabled,
            voice_volume=self._voice_volume,
            voice_event_enabled=self._voice_event_enabled,
            voice_player=self.voice_player,
            recognition_config=self._recognition_config,
            on_recognition_save=self._on_recognition_saved,
            overlay_visible=self._overlay_visible,
            recoil_hotkeys=self._recoil_hotkeys,
        )

    def _on_open_editor(self) -> None:
        """从托盘菜单启动弹道编辑器（独立进程）"""
        if self._editor_process and self._editor_process.poll() is None:
            logger.info("编辑器已在运行")
            return
        try:
            self._editor_process = subprocess.Popen(
                [sys.executable, str(PROJECT_ROOT / "main_editor.py")],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            logger.info("已启动编辑器进程")
        except OSError as exc:
            logger.error("启动编辑器失败: %s", exc)

    def _on_init_roi(self) -> None:
        """托盘菜单：重新框选ROI区域"""
        threading.Thread(target=self._run_init_roi, daemon=True).start()

    def _run_init_roi(self) -> None:
        from pubg_gun_control.roi_selector import RoiSelector
        def on_done(rois):
            self._recognition_config.update(rois)
            save_recognition(self._recognition_config)
            logger.info("ROI 已保存: %s", rois)
        RoiSelector(on_complete=on_done).start()

    def _on_capture_templates(self) -> None:
        """托盘菜单：重新采集模板"""
        threading.Thread(target=self._run_capture_templates, daemon=True).start()

    def _run_capture_templates(self) -> None:
        rois = {}
        for key in ["weapon_roi", "muzzle_roi", "grip_roi", "stock_roi", "scope_roi"]:
            val = self._recognition_config.get(key, [])
            if val and len(val) == 4:
                rois[key] = val
        if not rois:
            logger.warning("请先框选ROI区域")
            return
        self._run_template_capture(rois)

    def _on_ballistic_analysis(self) -> None:
        """托盘菜单：弹道分析"""
        threading.Thread(target=self._run_ballistic_analysis, daemon=True).start()

    def _run_ballistic_analysis(self) -> None:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
        from pubg_gun_control.ballistic_analyzer import analyze_spray_image, format_lua_function

        GUN_INTERVALS = {
            "M416": 87, "Beryl M762": 87, "AKM": 102, "AUG": 85, "SCAR-L": 96,
            "QBZ": 92, "G36C": 86, "ACE32": 90, "UMP45": 94, "MP5K": 94,
            "Vector": 57, "Micro UZI": 46, "P90": 61, "M249": 222, "M16A4": 280,
            "Groza": 80, "MK47": 300, "Tommy Gun": 84, "Famas": 65, "MG3": 60,
        }

        # 从当前基础脚本读取枪械列表与 interval，确保新增枪械可见
        gun_intervals: dict[str, int] = dict(GUN_INTERVALS)
        try:
            parser = LuaBallisticParser()
            # 设置界面保存后 self._recognition_config 可能不是最新，重新加载
            recognition = load_recognition()
            config = parser.parse(load_base_lua_path(recognition))
            script_guns = [
                gun
                for ammo_guns in config.ammo_groups.values()
                for gun in ammo_guns
                if gun.mode != 0
            ]
            gun_intervals = {
                gun.name: (gun.interval if gun.ballistic else GUN_INTERVALS.get(gun.name, 87))
                for gun in script_guns
            } or gun_intervals
            logger.info("弹道分析从基础脚本读取到 %d 把枪械", len(gun_intervals))
        except Exception as exc:
            logger.warning("读取基础脚本枪械列表失败，回退到默认列表: %s", exc)

        root = tk.Tk()
        root.title("弹道分析")
        root.attributes("-topmost", True)
        root.grab_set()
        root.geometry("520x400")

        ttk.Label(root, text="从弹孔截图自动提取弹道数据", font=("Arial", 11, "bold")).pack(pady=(10, 5))
        ttk.Label(root, text="支持灰色/黑色弹孔（对墙射击）和绿色标记点", font=("Arial", 9), foreground="gray").pack()

        file_frame = ttk.Frame(root)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(file_frame, text="弹孔截图:").pack(side=tk.LEFT)
        file_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=file_var, width=50)
        file_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def select_file():
            # 当前窗口有 grab_set()，会拦截原生文件对话框的焦点事件，
            # 导致 askopenfilename 可能返回空串或路径无法写回 Entry。
            # 选择前临时释放 grab，选择完成后再恢复。
            root.grab_release()
            try:
                logger.info("正在打开文件选择对话框...")
                path = filedialog.askopenfilename(
                    parent=root,
                    title="选择弹孔截图",
                    filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp")],
                )
                logger.info("文件选择对话框返回: %r", path)
                if path:
                    file_var.set(path)
                    file_entry.delete(0, tk.END)
                    file_entry.insert(0, path)
                    file_entry.update_idletasks()
                    file_entry.xview_moveto(1.0)
                    logger.info("已写入路径到输入框: %s", path)
                else:
                    logger.warning("未选择任何文件")
            except Exception:
                logger.exception("选择文件时发生异常")
            finally:
                root.grab_set()

        ttk.Button(file_frame, text="选择", width=5, command=select_file).pack(side=tk.LEFT)

        name_frame = ttk.Frame(root)
        name_frame.pack(fill=tk.X, padx=10, pady=3)
        ttk.Label(name_frame, text="枪械名称:").pack(side=tk.LEFT)
        gun_names = list(gun_intervals.keys())
        # 默认优先 M416，否则列表第一项；取值一律用 combobox.get()，
        # 避免 Windows 下 ttk.Combobox 与 StringVar 不同步（界面显示 K2 但变量仍是 M416）
        default_gun = "M416" if "M416" in gun_names else (gun_names[0] if gun_names else "")
        gun_combo = ttk.Combobox(
            name_frame,
            values=gun_names,
            width=15,
            state="readonly" if gun_names else "normal",
        )
        if default_gun:
            gun_combo.set(default_gun)
        gun_combo.pack(side=tk.LEFT, padx=5)

        # 常见枪械整匣发数（扩容），用于把识别点规范到整匣
        GUN_BULLET_COUNTS = {
            "M416": 40, "Beryl M762": 40, "AKM": 40, "AUG": 40, "SCAR-L": 40,
            "QBZ": 40, "G36C": 40, "ACE32": 40, "K2": 40, "Famas": 30,
            "Groza": 40, "MK47": 30, "M16A4": 40, "M249": 75, "MG3": 75,
            "UMP45": 40, "MP5K": 40, "Vector": 33, "Micro UZI": 35, "P90": 50,
            "Tommy Gun": 50,
        }

        param_frame = ttk.Frame(root)
        param_frame.pack(fill=tk.X, padx=10, pady=3)
        ttk.Label(param_frame, text="射击间隔(ms):").pack(side=tk.LEFT)
        default_interval = gun_intervals.get(default_gun, 87)
        interval_var = tk.IntVar(value=default_interval)
        # 保存控件引用：ttk.Spinbox 手动输入后 textvariable 不会立即同步，
        # 需用 spinbox.get() 直接读取控件显示值
        interval_spin = ttk.Spinbox(param_frame, textvariable=interval_var, from_=10, to=500, width=8)
        interval_spin.pack(side=tk.LEFT, padx=5)
        ttk.Label(param_frame, text="缩放系数:").pack(side=tk.LEFT, padx=(10, 0))
        scale_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(param_frame, textvariable=scale_var, from_=0.1, to=3.0, increment=0.1, width=6, format="%.1f").pack(side=tk.LEFT, padx=5)

        param_frame2 = ttk.Frame(root)
        param_frame2.pack(fill=tk.X, padx=10, pady=3)
        ttk.Label(param_frame2, text="整匣子弹数:").pack(side=tk.LEFT)
        bullet_var = tk.IntVar(value=GUN_BULLET_COUNTS.get(default_gun, 40))
        ttk.Spinbox(param_frame2, textvariable=bullet_var, from_=5, to=150, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(param_frame2, text="每段子弹数:").pack(side=tk.LEFT, padx=(10, 0))
        seg_var = tk.IntVar(value=1)
        ttk.Spinbox(param_frame2, textvariable=seg_var, from_=1, to=50, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(param_frame2, text="(1=逐发, 越大越平滑)", font=("Arial", 8), foreground="gray").pack(side=tk.LEFT)

        def _selected_gun() -> str:
            return (gun_combo.get() or "").strip()

        def on_gun_change(event=None):
            gun = _selected_gun()
            if gun in gun_intervals:
                interval_var.set(gun_intervals[gun])
            if gun in GUN_BULLET_COUNTS:
                bullet_var.set(GUN_BULLET_COUNTS[gun])
        gun_combo.bind("<<ComboboxSelected>>", on_gun_change)

        ttk.Label(
            root,
            text=(
                "整匣子弹数: 按真实弹匣规范弹道（如 K2 扩容 40）| "
                "缩放系数: 1.0=原始像素 | "
                "每段子弹数: 相邻几发取平均（1=逐发对齐原版脚本）"
            ),
            font=("Arial", 8),
            foreground="gray",
        ).pack(padx=10, anchor="w")

        result_label = ttk.Label(root, text="", wraplength=500)
        result_label.pack(pady=8)

        def _safe_filename(name: str) -> str:
            """将枪械名转为可用作文件名的片段（保留中文/字母数字，其余替换为下划线）"""
            cleaned = []
            for ch in name.strip():
                if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff"):
                    cleaned.append(ch)
                elif ch in (" ", "-", "_", "."):
                    cleaned.append("_")
                else:
                    cleaned.append("_")
            result = "".join(cleaned).strip("_")
            while "__" in result:
                result = result.replace("__", "_")
            return result or "ballistic"

        def on_analyze():
            path = file_var.get().strip()
            gun = _selected_gun()
            # 直接从控件读取：手动输入后 textvariable 可能尚未同步
            try:
                interval = int(float(interval_spin.get()))
            except (ValueError, TypeError):
                interval = interval_var.get()
            scale = scale_var.get()
            max_seg = seg_var.get()
            bullet_count = bullet_var.get()
            if not path:
                result_label.config(text="请选择弹孔截图", foreground="red")
                return
            if not gun:
                result_label.config(text="请输入枪械名称", foreground="red")
                return
            if bullet_count < 2:
                result_label.config(text="整匣子弹数至少为 2", foreground="red")
                return
            logger.info(
                "弹道分析使用枪械: %s (interval=%s, scale=%s, seg=%s, bullets=%s)",
                gun, interval, scale, max_seg, bullet_count,
            )
            result = analyze_spray_image(
                path,
                scale=scale,
                max_seg_count=max_seg,
                bullet_count=bullet_count,
            )
            if not result:
                result_label.config(text="分析失败: 未检测到足够的弹孔。尝试调整缩放系数或换一张更清晰的截图", foreground="red")
                return
            lua_code = format_lua_function(gun, result["ballistic"], interval)
            suggested_name = f"{_safe_filename(gun)}_ballistic.lua"
            last_bullet = result["ballistic"][-1][0] if result["ballistic"] else 0
            result_label.config(
                text=(
                    f"[{gun}] 识别 {result['shot_count']} 点 → 规范为 {result['bullet_count']} 发, "
                    f"{len(result['ballistic'])} 段(末发={last_bullet}) → {suggested_name}"
                ),
                foreground="green",
            )
            # 与选图一致：临时释放 grab，避免 Windows 下 initialfile 失效/对话框异常
            root.grab_release()
            try:
                save_path = filedialog.asksaveasfilename(
                    parent=root,
                    title=f"保存弹道数据（{gun}）",
                    defaultextension=".lua",
                    filetypes=[("Lua脚本", "*.lua")],
                    initialfile=suggested_name,
                )
            finally:
                root.grab_set()
            if save_path:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(lua_code)
                messagebox.showinfo(
                    "保存成功",
                    f"[{gun}] 弹道数据已保存到:\n{save_path}\n\n请在编辑器中将此函数合并到Lua脚本中",
                )

        ttk.Button(root, text="分析弹道", command=on_analyze, width=12).pack(pady=10)
        root.mainloop()

    def _on_settings_saved(
        self,
        shortcuts: list[dict[str, str]],
        gun_attachments: dict[str, dict[str, bool]],
        voice_enabled: bool,
        voice_volume: int,
        voice_event_enabled: dict[str, bool],
        overlay_visible: bool,
        recoil_hotkeys: dict[str, list[str]],
    ) -> None:
        self._shortcuts = shortcuts
        self._gun_attachments = gun_attachments
        self._voice_enabled = voice_enabled
        self._voice_volume = voice_volume
        self._voice_event_enabled = voice_event_enabled
        self._overlay_visible = overlay_visible
        self._recoil_hotkeys = recoil_hotkeys
        self.voice_player.enabled = voice_enabled
        self.voice_player.volume = voice_volume
        self.voice_player.event_enabled = voice_event_enabled
        save_config(
            shortcuts,
            gun_attachments=gun_attachments,
            voice_enabled=voice_enabled,
            voice_volume=voice_volume,
            voice_event_enabled=voice_event_enabled,
            overlay_visible=overlay_visible,
            recoil_hotkeys=recoil_hotkeys,
        )
        if self.overlay.is_created():
            if overlay_visible:
                self.overlay.show()
            else:
                self.overlay.hide()
        if self.input_listener:
            self.input_listener.update_shortcuts(shortcuts)
            self.input_listener.update_gun_attachments(gun_attachments)
            self.input_listener.update_recoil_hotkeys(recoil_hotkeys)
        logger.info("设置已保存")

    def _on_recognition_saved(self, rec_cfg: dict) -> None:
        """识别配置保存回调：持久化并按需启停识别"""
        old_enabled = self._recognition_config.get("enabled", False)
        old_template_dir = self._recognition_config.get("template_dir", "")
        self._recognition_config.update(rec_cfg)
        save_recognition(self._recognition_config)
        logger.info("识别配置已保存: enabled=%s, hotkey=%s, rec_path=%s, template_dir=%s",
                    rec_cfg.get("enabled"), rec_cfg.get("hotkey"), rec_cfg.get("rec_path"),
                    rec_cfg.get("template_dir"))
        new_rec_path = rec_cfg.get("rec_path", "").strip()
        if new_rec_path:
            self._rec_lua_writer = RecLuaWriter(new_rec_path)
        new_enabled = bool(rec_cfg.get("enabled"))
        new_template_dir = rec_cfg.get("template_dir", "")
        template_changed = new_template_dir != old_template_dir
        if new_enabled and not old_enabled:
            self._start_recognition()
        elif not new_enabled and old_enabled:
            # 基础脚本可能被编辑器修改，重新加载枪名映射以保持同步
            self._gun_name_map = {}
            if self._hotkey_listener:
                self._hotkey_listener.stop()
                self._hotkey_listener = None
            if self.overlay.is_created():
                self.overlay.update_recognition_status("")
        elif new_enabled and template_changed and self._recognizer:
            if self._hotkey_listener:
                self._hotkey_listener.stop()
                self._hotkey_listener = None
            self._start_recognition()

    def start(self) -> None:
        self._running = True

        self.overlay.create()
        if self._overlay_visible:
            self.overlay.show()
        else:
            self.overlay.hide()
        self.input_listener = InputListener(
            self._on_gun_selected, self._on_lock_changed, self._on_scope_changed,
            self._on_attachment_changed, self._on_reset, self._shortcuts, self._attachments,
            self._gun_attachments, voice_callback=self.voice_player.play,
            recoil_hotkeys=self._recoil_hotkeys,
        )
        self.input_listener.start()

        self.tray_icon = TrayIcon(
            self._on_exit, self._on_settings, self._on_open_editor,
            on_init_roi=self._on_init_roi,
            on_capture_templates=self._on_capture_templates,
            on_ballistic_analysis=self._on_ballistic_analysis,
        )
        self.tray_icon.start()

        self._start_recognition()

        self.overlay.run()

    def _start_recognition(self) -> None:
        if not self._recognition_config.get("enabled"):
            return
        # 加载枪名映射，确保识别结果与 canUse 表枪名大小写一致
        self._load_gun_name_map()
        rois = {}
        for key in ["weapon_roi", "muzzle_roi", "grip_roi", "stock_roi", "scope_roi"]:
            val = self._recognition_config.get(key, [])
            if val and len(val) == 4:
                rois[key] = val
        if not rois:
            logger.info("未配置识别区域，跳过自动识别")
            return
        try:
            from pubg_gun_control.recognizer import GunRecognizer
            template_dir = self._recognition_config.get("template_dir") or None
            thresholds = {
                "gun": self._recognition_config.get("threshold_gun", 0.5),
                "muzzle": self._recognition_config.get("threshold_muzzle", 0.25),
                "grip": self._recognition_config.get("threshold_grip", 0.3),
                "stock": self._recognition_config.get("threshold_stock", 0.35),
                "scope": self._recognition_config.get("threshold_scope", 0.35),
            }
            self._recognizer = GunRecognizer(rois, template_dir, thresholds)
            if not self._recognizer.has_gun_templates():
                logger.warning("未找到枪械模板，请先运行 python main.py --init")
                return
            hotkey = self._recognition_config.get("hotkey", "f2")
            self._hotkey_listener = pynput_keyboard.Listener(on_press=self._on_hotkey)
            self._hotkey_listener.start()
            logger.info("自动识别已启动，快捷键: %s", hotkey)
        except Exception:
            logger.exception("启动自动识别失败")

    def _on_hotkey(self, key) -> None:
        try:
            hotkey_name = self._recognition_config.get("hotkey", "f2")
            key_name = getattr(key, "name", None) or getattr(key, "char", None) or str(key)
            if key_name.lower() != hotkey_name.lower():
                return
            self._trigger_recognition()
        except Exception:
            logger.exception("识别异常")

    def stop(self) -> None:
        self._running = False

        if self._editor_process and self._editor_process.poll() is None:
            self._editor_process.terminate()
            try:
                self._editor_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._editor_process.kill()
            self._editor_process = None

        if self._hotkey_listener:
            self._hotkey_listener.stop()
            self._hotkey_listener = None

        if self.input_listener:
            self.input_listener.stop()
            self.input_listener = None

        if self.overlay.is_created():
            self.overlay.close()

        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def init_recognition(self) -> None:
        """启动识别初始化向导（ROI框选 + 模板采集）"""
        from pubg_gun_control.roi_selector import RoiSelector
        from pubg_gun_control.template_capture import (
            capture_gun_templates, capture_muzzle_templates,
            capture_shared_attachment_templates, capture_scope_templates,
        )

        existing_rois: dict[str, list[int]] = {}
        for key in ["weapon_roi", "muzzle_roi", "grip_roi", "stock_roi", "scope_roi"]:
            val = self._recognition_config.get(key, [])
            if val and len(val) == 4:
                existing_rois[key] = val

        def on_rois_complete(rois: dict[str, list[int]]) -> None:
            logger.info("ROI 框选完成: %s", rois)
            self._recognition_config.update(rois)
            save_recognition(self._recognition_config)
            self._run_template_capture(rois)

        if existing_rois:
            logger.info("检测到已保存的 ROI 配置，跳过框选")
            self._run_template_capture(existing_rois)
        else:
            logger.info("请在游戏中打开背包，确保武器栏可见")
            RoiSelector(on_complete=on_rois_complete).start()

    def _run_template_capture(self, rois: dict[str, list[int]]) -> None:
        from pubg_gun_control.template_capture import (
            capture_gun_templates, capture_muzzle_templates,
            capture_shared_attachment_templates, capture_scope_templates,
        )

        # 从当前基础脚本读取枪械列表，确保设置界面新增的枪械也能被采集
        gun_names: list[str] = []
        try:
            parser = LuaBallisticParser()
            # 设置界面保存后 self._recognition_config 可能不是最新，重新加载
            recognition = load_recognition()
            config = parser.parse(load_base_lua_path(recognition))
            gun_names = [
                gun.name
                for ammo_guns in config.ammo_groups.values()
                for gun in ammo_guns
                if gun.mode != 0
            ]
            logger.info("从基础脚本读取到 %d 把可采集枪械", len(gun_names))
        except Exception as exc:
            logger.warning("读取基础脚本枪械列表失败，回退到默认列表: %s", exc)

        logger.info("开始采集枪械模板...")
        captured = capture_gun_templates(
            weapon_roi=rois["weapon_roi"],
            save_fn=self._save_gun_template,
            gun_names=gun_names if gun_names else None,
        )
        logger.info("枪械模板采集完成，共 %d 个", captured)

        for weapon_type, type_label in [("ar", "步枪"), ("smg", "冲锋枪")]:
            muzzle_roi = rois.get("muzzle_roi")
            if muzzle_roi and len(muzzle_roi) == 4:
                logger.info("开始采集 %s 枪口配件模板...", type_label)
                cnt = capture_muzzle_templates(
                    roi=muzzle_roi,
                    save_fn=self._save_muzzle_template,
                    weapon_type=weapon_type,
                )
                logger.info("%s 枪口配件模板采集完成，共 %d 个", type_label, cnt)

        for category in ["grip", "stock"]:
            roi_key = f"{category}_roi"
            roi = rois.get(roi_key)
            if roi and len(roi) == 4:
                logger.info("开始采集 %s 模板...", category)
                cnt = capture_shared_attachment_templates(
                    roi=roi,
                    category=category,
                    save_fn=self._save_shared_attachment_template,
                )
                logger.info("%s 模板采集完成，共 %d 个", category, cnt)

        scope_roi = rois.get("scope_roi")
        if scope_roi and len(scope_roi) == 4:
            logger.info("开始采集倍镜模板...")
            cnt = capture_scope_templates(
                roi=scope_roi,
                save_fn=self._save_scope_template,
            )
            logger.info("倍镜模板采集完成，共 %d 个", cnt)

        self._recognition_config["enabled"] = True
        save_recognition(self._recognition_config)
        logger.info("识别初始化完成")

    def _save_gun_template(self, gun_name: str, image) -> None:
        try:
            from pubg_gun_control.recognizer import GunRecognizer
            template_dir = self._recognition_config.get("template_dir") or None
            recognizer = GunRecognizer({}, template_dir)
            recognizer.save_gun_template(gun_name, image)
        except Exception:
            logger.exception("保存枪械模板失败")

    def _save_muzzle_template(self, category: str, name: str, image, weapon_type: str) -> None:
        try:
            from pubg_gun_control.recognizer import GunRecognizer
            template_dir = self._recognition_config.get("template_dir") or None
            recognizer = GunRecognizer({}, template_dir)
            recognizer.save_attachment_template(category, name, image, weapon_type)
        except Exception:
            logger.exception("保存枪口模板失败")

    def _save_shared_attachment_template(self, category: str, name: str, image) -> None:
        try:
            from pubg_gun_control.recognizer import GunRecognizer
            template_dir = self._recognition_config.get("template_dir") or None
            recognizer = GunRecognizer({}, template_dir)
            recognizer.save_attachment_template(category, name, image)
        except Exception:
            logger.exception("保存配件模板失败")

    def _save_scope_template(self, scope_value: int, image, label: str = "") -> None:
        try:
            from pubg_gun_control.recognizer import GunRecognizer
            template_dir = self._recognition_config.get("template_dir") or None
            recognizer = GunRecognizer({}, template_dir)
            recognizer.save_scope_template(scope_value, image, label)
        except Exception:
            logger.exception("保存倍镜模板失败")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    _setup_logging()

    if "--init" in sys.argv:
        logger.info("启动识别初始化向导...")
        app = GunControlApp()
        app.init_recognition()
        return 0

    if "--generate-lua" in sys.argv:
        from pubg_gun_control.lua_generator import generate_auto_recognize_script
        source = load_base_lua_path()
        output = generate_auto_recognize_script(source)
        logger.info("已生成 GHUB 脚本: %s", output)
        return 0

    if "--init-roi" in sys.argv:
        logger.info("重新框选识别区域...")
        app = GunControlApp()
        from pubg_gun_control.roi_selector import RoiSelector
        from pubg_gun_control.config_manager import save_recognition
        def on_done(rois):
            app._recognition_config.update(rois)
            save_recognition(app._recognition_config)
            logger.info("ROI 已保存: %s", rois)
        RoiSelector(on_complete=on_done).start()
        return 0

    logger.info("PUBG Gun Control 启动中...")
    logger.info("命令行参数:")
    logger.info("  --init         启动识别初始化向导（有ROI则跳过框选，直接采集模板）")
    logger.info("  --init-roi     重新框选识别区域（不重新采集模板）")
    logger.info("  --generate-lua 生成包含自动识别的 GHUB 脚本")
    logger.info("自动识别:")
    logger.info("  初始化后，按快捷键(默认F2)截图识别当前武器并写入 rec.lua")
    logger.info("使用方法：")
    logger.info("  - 大写锁定开启时：")
    logger.info("    LAlt + 鼠标前进键 = MP5k")
    logger.info("    LAlt + 鼠标后退键 = UMP5")
    logger.info("    LCtrl + 鼠标前进键 = M416")
    logger.info("    LCtrl + 鼠标后退键 = ACE32")
    logger.info("    LShift + 鼠标前进键 = Beryl M762")
    logger.info("    LShift + 鼠标后退键 = AUG")
    logger.info("    LAlt + 鼠标中键(G3) = 循环切换枪口")
    logger.info("    LCtrl + 鼠标中键(G3) = 循环切换握把")
    logger.info("    LShift + 鼠标中键(G3) = 循环切换枪托")
    logger.info("  - 大写锁定关闭时：显示 '无'")
    logger.info("  - 按 G/3/4/5 或 Tab 键取消压枪模式")
    logger.info("  - RCtrl + 鼠标后退键 = 锁定/解锁")
    logger.info("  - RAlt + 鼠标G5键 = 切换2倍镜")
    logger.info("  - RAlt + 鼠标G4键 = 切换3倍镜")
    logger.info("  - 右键点击托盘图标可退出程序")

    app = GunControlApp()

    try:
        app.start()
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在退出...")
    finally:
        app.stop()
        logger.info("程序已退出")

    return 0


if __name__ == "__main__":
    sys.exit(main())
