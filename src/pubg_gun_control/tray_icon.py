"""
系统托盘模块

负责创建和管理系统托盘图标

@author hqzqaq
@since 2026-03-30 19:49
@version 1.0
"""

from typing import Callable, Optional
import pystray
from PIL import Image, ImageDraw


class TrayIcon:
    """系统托盘图标管理器"""

    def __init__(self, on_exit: Callable[[], None]):
        """
        初始化系统托盘图标

        Args:
            on_exit: 退出回调函数
        """
        self.on_exit = on_exit
        self.icon: Optional[pystray.Icon] = None
        self._running = False

    def _create_icon_image(self) -> Image.Image:
        """
        创建托盘图标图像

        Returns:
            PIL Image 对象
        """
        # 创建 64x64 的红色圆形图标
        width = 64
        height = 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 绘制红色圆形
        draw.ellipse(
            [4, 4, width - 4, height - 4],
            fill=(255, 0, 0, 255),
            outline=(200, 0, 0, 255),
            width=2
        )

        return image

    def _on_exit_clicked(self, icon: pystray.Icon):
        """退出菜单项点击处理"""
        self.stop()
        self.on_exit()

    def start(self):
        """启动系统托盘图标"""
        menu = pystray.Menu(
            pystray.MenuItem("退出", self._on_exit_clicked)
        )

        self.icon = pystray.Icon(
            "pubg-gun-control",
            self._create_icon_image(),
            "PUBG Gun Control",
            menu
        )

        self._running = True
        self.icon.run_detached()

    def stop(self):
        """停止系统托盘图标"""
        self._running = False
        if self.icon:
            self.icon.stop()
            self.icon = None

    def is_running(self) -> bool:
        """检查托盘图标是否正在运行"""
        return self._running and self.icon is not None
