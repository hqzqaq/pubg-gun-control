"""
配置管理模块

负责读写 config.json 配置文件

@author huquanzhi
@since 2026-04-18 19:38
@version 1.0
"""

import json
import sys
from pathlib import Path
from typing import Any


_CONFIG_FILENAME = "config.json"


def _get_config_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / _CONFIG_FILENAME
    return Path(__file__).resolve().parent.parent.parent / _CONFIG_FILENAME


def get_default_config() -> list[dict[str, str]]:
    return [
        {"modifier": "alt", "mouse_button": "forward", "text": "MP5k"},
        {"modifier": "alt", "mouse_button": "backward", "text": "UMP5"},
        {"modifier": "ctrl", "mouse_button": "forward", "text": "M416"},
        {"modifier": "ctrl", "mouse_button": "backward", "text": "ACE32"},
        {"modifier": "shift", "mouse_button": "forward", "text": "Beryl M762"},
        {"modifier": "shift", "mouse_button": "backward", "text": "AUG"},
    ]


def load_config() -> list[dict[str, str]]:
    config_path = _get_config_path()
    if not config_path.exists():
        default = get_default_config()
        save_config(default)
        return default

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        shortcuts: list[dict[str, str]] = data.get("shortcuts", [])
        if not shortcuts:
            return get_default_config()
        return shortcuts
    except (json.JSONDecodeError, OSError):
        return get_default_config()


def save_config(shortcuts: list[dict[str, str]]) -> None:
    config_path = _get_config_path()
    data = {"shortcuts": shortcuts}
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
