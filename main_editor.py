"""
弹道系数可视化编辑器 - 独立入口

直接运行：
  uv run python main_editor.py [path/to/lua]

不带参数启动时，从 config.json 的 editor.recent_files 取最近文件，
若无最近文件则弹文件选择对话框。

@author huquanzhi
@since 2026-06-18 19:55
@version 1.0
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog

from pubg_gun_control.config_manager import (
    add_editor_recent,
    load_editor_recent,
)
from pubg_gun_control.editor_ui import BallisticEditorWindow
from pubg_gun_control.editor_ui.main_window import _DEFAULT_PRESETS_DIR


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    _setup_logging()
    logger = logging.getLogger("main_editor")

    # 解析命令行参数
    lua_path: str | None = None
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1])
        if candidate.exists() and candidate.suffix == ".lua":
            lua_path = str(candidate)
        else:
            logger.warning("忽略无效的 lua 路径: %s", sys.argv[1])

    # 确保预设目录存在
    _DEFAULT_PRESETS_DIR.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("PUBG 弹道编辑器")
    app.setStyle("Fusion")

    # 加载最近文件
    recent = load_editor_recent()
    window = BallisticEditorWindow(lua_path=lua_path)
    window.set_recent_files(recent)

    if lua_path:
        add_editor_recent(lua_path)
    elif recent:
        # 用最近的文件作为初始加载（异步，避免阻塞 UI）
        def load_recent() -> None:
            first = recent[0]
            if Path(first).exists():
                window._load_lua_file(first)
            else:
                logger.info("最近文件不存在: %s，跳过", first)
        QTimer.singleShot(0, load_recent)
    else:
        # 没有任何线索：弹文件选择对话框
        def prompt_open() -> None:
            path, _ = QFileDialog.getOpenFileName(
                window,
                "选择 GHUB lua 脚本",
                "",
                "Lua 脚本 (*.lua);;所有文件 (*)",
            )
            if path:
                window._load_lua_file(path)
        QTimer.singleShot(0, prompt_open)

    # 退出时把当前 lua 路径加入最近
    def save_recent_on_exit() -> None:
        if window._lua_path:
            add_editor_recent(window._lua_path)
    app.aboutToQuit.connect(save_recent_on_exit)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
