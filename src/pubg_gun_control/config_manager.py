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


def _get_project_root() -> Path:
    """获取项目根目录，兼容开发环境与 PyInstaller 打包。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def _get_config_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / _CONFIG_FILENAME
    return _get_project_root() / _CONFIG_FILENAME


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

_DEFAULT_VOICE_EVENT_ENABLED: dict[str, bool] = {
    "recoil_on": True,
    "recoil_off": True,
    "lock_on": True,
    "lock_off": True,
    "locked_action": True,
}

_VOICE_EVENT_KEYS: tuple[str, ...] = tuple(_DEFAULT_VOICE_EVENT_ENABLED.keys())

_DEFAULT_RECOIL_HOTKEYS: dict[str, list[str]] = {
    "enable": ["caps_lock", "1"],
    "disable": ["tab", "2", "g", "3", "4", "5"],
}

_RECOIL_HOTKEY_KEYS: tuple[str, ...] = tuple(_DEFAULT_RECOIL_HOTKEYS.keys())


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


def load_voice_enabled() -> bool:
    """读取语音提示开关状态，默认开启。"""
    config_path = _get_config_path()
    if not config_path.exists():
        return True

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        voice_enabled = data.get("voice_enabled")
        if isinstance(voice_enabled, bool):
            return voice_enabled
        return True
    except (json.JSONDecodeError, OSError):
        return True


def load_overlay_visible() -> bool:
    """读取浮窗显示开关状态，默认显示。"""
    config_path = _get_config_path()
    if not config_path.exists():
        return True

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        overlay_visible = data.get("overlay_visible")
        if isinstance(overlay_visible, bool):
            return overlay_visible
        return True
    except (json.JSONDecodeError, OSError):
        return True


def load_voice_volume() -> int:
    """读取语音音量（0~100），默认 100。"""
    config_path = _get_config_path()
    if not config_path.exists():
        return 100

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        volume = data.get("voice_volume")
        if isinstance(volume, int) and 0 <= volume <= 100:
            return volume
        if isinstance(volume, bool):
            # bool 是 int 的子类，单独排除
            return 100
        if isinstance(volume, (int, float)) and not isinstance(volume, bool):
            clamped = int(volume)
            if clamped < 0:
                return 0
            if clamped > 100:
                return 100
            return clamped
        return 100
    except (json.JSONDecodeError, OSError):
        return 100


def load_voice_event_enabled() -> dict[str, bool]:
    """读取每个语音事件是否启用，默认全部启用。"""
    config_path = _get_config_path()
    result: dict[str, bool] = dict(_DEFAULT_VOICE_EVENT_ENABLED)
    if not config_path.exists():
        return result

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        event_enabled = data.get("voice_event_enabled")
        if not isinstance(event_enabled, dict):
            return result
        for key in _VOICE_EVENT_KEYS:
            if key in event_enabled and isinstance(event_enabled[key], bool):
                result[key] = event_enabled[key]
        return result
    except (json.JSONDecodeError, OSError):
        return result


def _normalize_recoil_hotkeys(hotkeys: Any) -> dict[str, list[str]]:
    """把配置中的字符串或列表统一为字符串列表，过滤无效值。"""
    result: dict[str, list[str]] = {key: list(value) for key, value in _DEFAULT_RECOIL_HOTKEYS.items()}
    if not isinstance(hotkeys, dict):
        return result
    for key in _RECOIL_HOTKEY_KEYS:
        value = hotkeys.get(key)
        items: list[str] = []
        if isinstance(value, str):
            items = [value]
        elif isinstance(value, list):
            items = value
        normalized = [str(item).strip().lower() for item in items if isinstance(item, str) and str(item).strip()]
        if normalized:
            result[key] = normalized
    return result


def load_recoil_hotkeys() -> dict[str, list[str]]:
    """读取压枪模式开关快捷键配置，默认保留 caps_lock/1 开、tab/2/g/3/4/5 关。"""
    config_path = _get_config_path()
    if not config_path.exists():
        return dict(_DEFAULT_RECOIL_HOTKEYS)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        return _normalize_recoil_hotkeys(data.get("recoil_hotkeys"))
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT_RECOIL_HOTKEYS)


def save_config(
    shortcuts: list[dict[str, str]],
    attachments: list[dict[str, str]] | None = None,
    gun_attachments: dict[str, dict[str, bool]] | None = None,
    voice_enabled: bool | None = None,
    voice_volume: int | None = None,
    voice_event_enabled: dict[str, bool] | None = None,
    overlay_visible: bool | None = None,
    recoil_hotkeys: dict[str, list[str]] | None = None,
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
    if voice_enabled is not None:
        data["voice_enabled"] = voice_enabled
    else:
        data["voice_enabled"] = load_voice_enabled()
    if overlay_visible is not None:
        data["overlay_visible"] = bool(overlay_visible)
    else:
        data["overlay_visible"] = load_overlay_visible()
    if voice_volume is not None:
        clamped = int(voice_volume)
        if clamped < 0:
            clamped = 0
        elif clamped > 100:
            clamped = 100
        data["voice_volume"] = clamped
    else:
        data["voice_volume"] = load_voice_volume()
    if voice_event_enabled is not None:
        normalized: dict[str, bool] = {}
        for key in _VOICE_EVENT_KEYS:
            if key in voice_event_enabled:
                normalized[key] = bool(voice_event_enabled[key])
            else:
                normalized[key] = True
        data["voice_event_enabled"] = normalized
    else:
        data["voice_event_enabled"] = load_voice_event_enabled()
    if recoil_hotkeys is not None:
        data["recoil_hotkeys"] = _normalize_recoil_hotkeys(recoil_hotkeys)
    else:
        data["recoil_hotkeys"] = load_recoil_hotkeys()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 识别配置
# ---------------------------------------------------------------------------


_DEFAULT_RECOGNITION: dict[str, Any] = {
    "enabled": True,
    "weapon_roi": [],
    "muzzle_roi": [],
    "grip_roi": [],
    "stock_roi": [],
    "scope_roi": [],
    "hotkey": "f2",
    "rec_path": "",
    "template_dir": "",
    "threshold_gun": 0.5,
    "threshold_muzzle": 0.25,
    "threshold_grip": 0.3,
    "threshold_stock": 0.35,
    "threshold_scope": 0.35,
}


def load_recognition() -> dict[str, Any]:
    """读取自动识别配置"""
    config_path = _get_config_path()
    if not config_path.exists():
        return dict(_DEFAULT_RECOGNITION)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        rec = data.get("recognition", {})
        if not isinstance(rec, dict):
            return dict(_DEFAULT_RECOGNITION)
        result = dict(_DEFAULT_RECOGNITION)
        for key in _DEFAULT_RECOGNITION:
            if key in rec:
                result[key] = rec[key]
        return result
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT_RECOGNITION)


def save_recognition(recognition: dict[str, Any]) -> None:
    """保存自动识别配置到 config.json"""
    data = _load_full_config()
    data["recognition"] = recognition
    config_path = _get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 编辑器相关
# ---------------------------------------------------------------------------


_MAX_RECENT = 5


def _load_full_config() -> dict[str, Any]:
    """加载整个 config.json，避免覆盖其他字段"""
    config_path = _get_config_path()
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        return data
    except (json.JSONDecodeError, OSError):
        return {}


def load_editor_recent() -> list[str]:
    """读取编辑器最近打开的 lua 文件列表（最多 5 个）"""
    data = _load_full_config()
    editor = data.get("editor", {})
    if not isinstance(editor, dict):
        return []
    files = editor.get("recent_files", [])
    if not isinstance(files, list):
        return []
    return [str(f) for f in files[:_MAX_RECENT]]


def add_editor_recent(path: str) -> list[str]:
    """添加一个最近文件，去重并截断到 5 个，写回 config.json"""
    data = _load_full_config()
    editor = data.get("editor", {})
    if not isinstance(editor, dict):
        editor = {}
    files = editor.get("recent_files", [])
    if not isinstance(files, list):
        files = []
    files = [str(f) for f in files]

    abs_path = str(Path(path).resolve())
    if abs_path in files:
        files.remove(abs_path)
    files.insert(0, abs_path)
    files = files[:_MAX_RECENT]

    editor["recent_files"] = files
    data["editor"] = editor
    config_path = _get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return files


def clear_editor_recent() -> None:
    """清空最近文件"""
    data = _load_full_config()
    editor = data.get("editor", {})
    if isinstance(editor, dict):
        editor["recent_files"] = []
    data["editor"] = editor
    config_path = _get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
