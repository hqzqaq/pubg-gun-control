"""
系统托盘模块

负责创建和管理系统托盘图标

@author hqzqaq
@since 2026-03-30 19:49
@version 1.0
"""

import logging
from typing import Callable

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class TrayIcon:
    """系统托盘图标管理器"""

    def __init__(self, on_exit: Callable[[], None], on_settings: Callable[[], None] | None = None) -> None:
        self.on_exit = on_exit
        self.on_settings = on_settings
        self.icon: pystray.Icon | None = None
        self._running = False

    def _create_icon_image(self) -> Image.Image:
        width = 64
        height = 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        draw.ellipse(
            [4, 4, width - 4, height - 4],
            fill=(255, 0, 0, 255),
            outline=(200, 0, 0, 255),
            width=2,
        )

        return image

    def _on_exit_clicked(self, icon: pystray.Icon) -> None:
        self.stop()
        self.on_exit()

    def _on_settings_clicked(self, icon: pystray.Icon) -> None:
        if self.on_settings:
            self.on_settings()

    def start(self) -> None:
        menu_items = [
            pystray.MenuItem("设置", self._on_settings_clicked),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_exit_clicked),
        ]
        menu = pystray.Menu(*menu_items)

        self.icon = pystray.Icon(
            "pubg-gun-control",
            self._create_icon_image(),
            "PUBG Gun Control",
            menu,
        )

        self._running = True
        self.icon.run_detached()
        logger.info("系统托盘图标已启动")

    def stop(self) -> None:
        self._running = False
        if self.icon:
            self.icon.stop()
            self.icon = None
        logger.info("系统托盘图标已停止")

    def is_running(self) -> bool:
        return self._running and self.icon is not None
