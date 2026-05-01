"""
PUBG Gun Control - 枪械切换热键显示工具

通过监听键盘和鼠标组合键，在屏幕左上角显示当前选中的枪械名称

@author hqzqaq
@since 2026-03-30 19:49
@version 1.0
"""

from importlib.metadata import version

from .config_manager import load_config, save_config
from .input_listener import InputListener, ShortcutMatcher
from .overlay_window import OverlayWindow
from .settings_window import SettingsWindow
from .tray_icon import TrayIcon

try:
    __version__ = version("pubg-gun-control")
except Exception:
    __version__ = "1.0.8"

__all__ = ["InputListener", "ShortcutMatcher", "OverlayWindow", "TrayIcon", "SettingsWindow", "load_config", "save_config"]
