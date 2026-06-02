"""
PUBG Gun Control 主程序入口

@author hqzqaq
@since 2026-03-30 19:49
@version 1.0
"""

import logging
import sys
import threading

from pubg_gun_control.config_manager import load_config, save_config
from pubg_gun_control.input_listener import InputListener
from pubg_gun_control.overlay_window import OverlayWindow
from pubg_gun_control.settings_window import SettingsWindow
from pubg_gun_control.tray_icon import TrayIcon

logger = logging.getLogger(__name__)


class GunControlApp:
    """PUBG枪械控制应用主类"""

    def __init__(self) -> None:
        self.overlay = OverlayWindow()
        self.input_listener: InputListener | None = None
        self.tray_icon: TrayIcon | None = None
        self._running = False
        self._lock = threading.Lock()
        self._shortcuts: list[dict[str, str]] = load_config()

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

    def _on_exit(self) -> None:
        self.stop()

    def _on_settings(self) -> None:
        if self.overlay.root:
            self.overlay.root.after(0, self._open_settings)

    def _open_settings(self) -> None:
        SettingsWindow(self.overlay.root, self._shortcuts, self._on_settings_saved)

    def _on_settings_saved(self, shortcuts: list[dict[str, str]]) -> None:
        self._shortcuts = shortcuts
        save_config(shortcuts)
        if self.input_listener:
            self.input_listener.update_shortcuts(shortcuts)
        logger.info("设置已保存")

    def start(self) -> None:
        self._running = True

        self.overlay.create()
        self.input_listener = InputListener(self._on_gun_selected, self._on_lock_changed, self._on_scope_changed, self._shortcuts)
        self.input_listener.start()

        self.tray_icon = TrayIcon(self._on_exit, self._on_settings)
        self.tray_icon.start()

        self.overlay.run()

    def stop(self) -> None:
        self._running = False

        if self.input_listener:
            self.input_listener.stop()
            self.input_listener = None

        if self.overlay.is_created():
            self.overlay.close()

        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None


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

    logger.info("PUBG Gun Control 启动中...")
    logger.info("使用方法：")
    logger.info("  - 大写锁定开启时：")
    logger.info("    LAlt + 鼠标前进键 = MP5k")
    logger.info("    LAlt + 鼠标后退键 = UMP5")
    logger.info("    LCtrl + 鼠标前进键 = M416")
    logger.info("    LCtrl + 鼠标后退键 = ACE32")
    logger.info("    LShift + 鼠标前进键 = Beryl M762")
    logger.info("    LShift + 鼠标后退键 = AUG")
    logger.info("  - 大写锁定关闭时：显示 '无'")
    logger.info("  - 按 G/3/4/5 或 Tab 键取消压枪模式")
    logger.info("  - Ctrl + Alt = 锁定/解锁当前枪械（锁定后无法切换，窗口变黄色）")
    logger.info("  - RAlt + 鼠标G5键 = 切换2倍镜/1倍镜")
    logger.info("  - RAlt + 鼠标G4键 = 切换3倍镜/1倍镜")
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
