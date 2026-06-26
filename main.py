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
    load_recognition,
    save_recognition,
)
from pubg_gun_control.input_listener import InputListener
from pubg_gun_control.overlay_window import OverlayWindow
from pubg_gun_control.voice_prompt import VoicePlayer
from pubg_gun_control.settings_window import SettingsWindow
from pubg_gun_control.tray_icon import TrayIcon
from pubg_gun_control.rec_lua_writer import RecLuaWriter

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
        self.voice_player.enabled = self._voice_enabled
        self.voice_player.volume = self._voice_volume
        self.voice_player.event_enabled = self._voice_event_enabled

        self._recognition_config: dict = load_recognition()
        self._recognizer = None
        rec_path = self._recognition_config.get("rec_path") or None
        self._rec_lua_writer = RecLuaWriter(rec_path)
        self._hotkey_listener = None
        self._editor_process: subprocess.Popen | None = None

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

    def _trigger_recognition(self) -> None:
        if not self._recognizer:
            return
        try:
            result = self._recognizer.recognize_all()
            gun = result.get("gun") or ""
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

    def _on_settings_saved(
        self,
        shortcuts: list[dict[str, str]],
        gun_attachments: dict[str, dict[str, bool]],
        voice_enabled: bool,
        voice_volume: int,
        voice_event_enabled: dict[str, bool],
    ) -> None:
        self._shortcuts = shortcuts
        self._gun_attachments = gun_attachments
        self._voice_enabled = voice_enabled
        self._voice_volume = voice_volume
        self._voice_event_enabled = voice_event_enabled
        self.voice_player.enabled = voice_enabled
        self.voice_player.volume = voice_volume
        self.voice_player.event_enabled = voice_event_enabled
        save_config(
            shortcuts,
            gun_attachments=gun_attachments,
            voice_enabled=voice_enabled,
            voice_volume=voice_volume,
            voice_event_enabled=voice_event_enabled,
        )
        if self.input_listener:
            self.input_listener.update_shortcuts(shortcuts)
            self.input_listener.update_gun_attachments(gun_attachments)
        logger.info("设置已保存")

    def _on_recognition_saved(self, rec_cfg: dict) -> None:
        """识别配置保存回调：持久化并按需启停识别"""
        old_enabled = self._recognition_config.get("enabled", False)
        self._recognition_config.update(rec_cfg)
        save_recognition(self._recognition_config)
        logger.info("识别配置已保存: enabled=%s, hotkey=%s, rec_path=%s",
                    rec_cfg.get("enabled"), rec_cfg.get("hotkey"), rec_cfg.get("rec_path"))
        new_rec_path = rec_cfg.get("rec_path", "").strip()
        if new_rec_path:
            self._rec_lua_writer = RecLuaWriter(new_rec_path)
        new_enabled = bool(rec_cfg.get("enabled"))
        if new_enabled and not old_enabled:
            self._start_recognition()
        elif not new_enabled and old_enabled:
            if self._hotkey_listener:
                self._hotkey_listener.stop()
                self._hotkey_listener = None
            if self.overlay.is_created():
                self.overlay.update_recognition_status("")

    def start(self) -> None:
        self._running = True

        self.overlay.create()
        self.input_listener = InputListener(
            self._on_gun_selected, self._on_lock_changed, self._on_scope_changed,
            self._on_attachment_changed, self._on_reset, self._shortcuts, self._attachments,
            self._gun_attachments, voice_callback=self.voice_player.play,
        )
        self.input_listener.start()

        self.tray_icon = TrayIcon(
            self._on_exit, self._on_settings, self._on_open_editor,
            on_init_roi=self._on_init_roi,
            on_capture_templates=self._on_capture_templates,
        )
        self.tray_icon.start()

        self._start_recognition()

        self.overlay.run()

    def _start_recognition(self) -> None:
        if not self._recognition_config.get("enabled"):
            return
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
            self._recognizer = GunRecognizer(rois, template_dir)
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

        logger.info("开始采集枪械模板...")
        captured = capture_gun_templates(
            weapon_roi=rois["weapon_roi"],
            save_fn=self._save_gun_template,
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
        source = str(PROJECT_ROOT / "1.2.2-2024.5.20.-GHUB.-github.lua")
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
