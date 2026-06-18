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
        {"modifier": "alt", "mouse_button": "backward", "text": "UMP5"},
        {"modifier": "alt", "mouse_button": "forward", "text": "MP5k"},
        {"modifier": "ctrl", "mouse_button": "forward", "text": "M416"},
        {"modifier": "ctrl", "mouse_button": "backward", "text": "ACE32"},
        {"modifier": "shift", "mouse_button": "forward", "text": "Beryl M762"},
        {"modifier": "shift", "mouse_button": "backward", "text": "AUG"},
    ]


_DEFAULT_ATTACHMENTS: list[dict[str, str]] = [
    {"modifier": "alt", "mouse_button": "middle", "category": "muzzle", "label": "枪口"},
    {"modifier": "ctrl", "mouse_button": "middle", "category": "grip", "label": "握把"},
    {"modifier": "shift", "mouse_button": "middle", "category": "stock", "label": "枪托"},
]

_DEFAULT_GUN_ATTACHMENTS: dict[str, dict[str, bool]] = {
    "UMP5":       {"muzzle": True, "grip": True, "stock": False},
    "MP5k":       {"muzzle": True, "grip": True, "stock": True},
    "M416":       {"muzzle": True, "grip": True, "stock": True},
    "ACE32":      {"muzzle": True, "grip": True, "stock": True},
    "Beryl M762": {"muzzle": True, "grip": True, "stock": False},
    "AUG":        {"muzzle": True, "grip": True, "stock": False},
}


def get_default_attachments() -> list[dict[str, str]]:
    return list(_DEFAULT_ATTACHMENTS)


def get_default_gun_attachments() -> dict[str, dict[str, bool]]:
    return dict(_DEFAULT_GUN_ATTACHMENTS)


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


def load_attachments() -> list[dict[str, str]]:
    config_path = _get_config_path()
    if not config_path.exists():
        return get_default_attachments()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        attachments: list[dict[str, str]] = data.get("attachments", [])
        if not attachments:
            return get_default_attachments()
        return attachments
    except (json.JSONDecodeError, OSError):
        return get_default_attachments()


def load_gun_attachments() -> dict[str, dict[str, bool]]:
    config_path = _get_config_path()
    if not config_path.exists():
        return get_default_gun_attachments()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        ga: dict[str, dict[str, bool]] = data.get("gun_attachments", {})
        if not ga:
            return get_default_gun_attachments()
        return ga
    except (json.JSONDecodeError, OSError):
        return get_default_gun_attachments()


def save_config(
    shortcuts: list[dict[str, str]],
    attachments: list[dict[str, str]] | None = None,
    gun_attachments: dict[str, dict[str, bool]] | None = None,
) -> None:
    config_path = _get_config_path()
    data: dict[str, Any] = {"shortcuts": shortcuts}
    if attachments is not None:
        data["attachments"] = attachments
    else:
        data["attachments"] = load_attachments()
    if gun_attachments is not None:
        data["gun_attachments"] = gun_attachments
    else:
        data["gun_attachments"] = load_gun_attachments()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
