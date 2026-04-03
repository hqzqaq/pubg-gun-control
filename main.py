"""
PUBG Gun Control 主程序入口

@author hqzqaq
@since 2026-03-30 19:49
@version 1.0
"""

import sys
import threading
import time

from pubg_gun_control.input_listener import InputListener
from pubg_gun_control.overlay_window import OverlayWindow
from pubg_gun_control.tray_icon import TrayIcon


class GunControlApp:
    """PUBG枪械控制应用主类"""

    def __init__(self):
        """初始化应用"""
        self.overlay = OverlayWindow()
        self.input_listener: InputListener | None = None
        self.tray_icon: TrayIcon | None = None
        self._running = False
        self._lock = threading.Lock()

    def _on_gun_selected(self, gun_name: str):
        """
        枪械选择回调函数

        Args:
            gun_name: 选中的枪械名称
        """
        with self._lock:
            if self.overlay.is_created():
                self.overlay.update_text(gun_name)

    def _on_exit(self):
        """退出回调函数"""
        self.stop()

    def start(self):
        """启动应用"""
        self._running = True

        # 创建浮窗
        self.overlay.create()

        # 创建输入监听器
        self.input_listener = InputListener(self._on_gun_selected)
        self.input_listener.start()

        # 创建系统托盘图标
        self.tray_icon = TrayIcon(self._on_exit)
        self.tray_icon.start()

        # 启动浮窗主循环
        self.overlay.run()

    def stop(self):
        """停止应用"""
        self._running = False

        # 停止输入监听
        if self.input_listener:
            self.input_listener.stop()
            self.input_listener = None

        # 关闭浮窗
        if self.overlay.is_created():
            self.overlay.close()

        # 停止托盘图标
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None


def main():
    """主函数"""
    print("PUBG Gun Control 启动中...")
    print("使用方法：")
    print("  - 大写锁定开启时：")
    print("    LAlt + 鼠标前进键 = MP5k")
    print("    LAlt + 鼠标后退键 = UMP5")
    print("    LCtrl + 鼠标前进键 = M416")
    print("    LCtrl + 鼠标后退键 = ACE32")
    print("    LShift + 鼠标前进键 = SCAR-L")
    print("    LShift + 鼠标后退键 = AUG")
    print("  - 大写锁定关闭时：显示 '无'")
    print("  - 按 G/3/4/5 或 Tab 键取消压枪模式")
    print("  - 右键点击托盘图标可退出程序")
    print()

    app = GunControlApp()

    try:
        app.start()
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在退出...")
    finally:
        app.stop()
        print("程序已退出")

    return 0


if __name__ == "__main__":
    sys.exit(main())
