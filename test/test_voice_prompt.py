"""
语音与输入监听测试

验证 VoicePlayer 能够正确定位语音文件并播放，
以及 InputListener 在锁定模式下能够拦截切换类操作并发出 locked_action 事件。

@author huquanzhi
@since 2026-06-18
@version 1.0
"""

from __future__ import annotations

import sys
import winsound
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pynput.keyboard import Key
from pynput.mouse import Button

from pubg_gun_control.input_listener import InputListener
from pubg_gun_control.voice_prompt import VoicePlayer, _resolve_voice_dir


def test_resolve_voice_dir() -> None:
    """voice/ 目录应存在且路径以 voice 结尾"""
    voice_dir = _resolve_voice_dir()
    assert voice_dir.exists(), f"voice 目录不存在: {voice_dir}"
    assert voice_dir.name == "voice", f"voice 目录名称异常: {voice_dir.name}"


def test_voice_player_play_unknown_event() -> None:
    """播放不存在的语音事件时不应抛出异常"""
    player = VoicePlayer()
    player.play("不存在的音频")


@patch("winsound.PlaySound")
def test_voice_player_play_known_event(mock_play_sound: MagicMock) -> None:
    """调用合法事件时 winsound.PlaySound 应被调用，且传入对应 wav 文件路径与异步标志"""
    player = VoicePlayer()
    player.play("recoil_on")

    assert mock_play_sound.called, "winsound.PlaySound 未被调用"
    call_args = mock_play_sound.call_args
    wav_path = call_args[0][0]
    assert wav_path.endswith("压枪开启.wav"), f"wav 路径异常: {wav_path}"
    flags = call_args[0][1]
    assert flags == winsound.SND_ASYNC | winsound.SND_FILENAME, f"播放标志异常: {flags}"
    assert flags & winsound.SND_NOSTOP == 0, "不应包含 SND_NOSTOP 标志"


@patch("winsound.PlaySound")
def test_voice_player_disabled(mock_play_sound: MagicMock) -> None:
    """关闭语音开关时不应调用 winsound.PlaySound"""
    player = VoicePlayer()
    player.enabled = False
    player.play("recoil_on")

    assert not mock_play_sound.called, "禁用状态下不应播放语音"


@patch("winsound.PlaySound")
def test_voice_player_volume_zero(mock_play_sound: MagicMock) -> None:
    """音量为 0 时不应调用 winsound.PlaySound"""
    player = VoicePlayer()
    player.volume = 0
    player.play("recoil_on")

    assert not mock_play_sound.called, "音量为 0 时不应播放语音"


@patch("winsound.PlaySound")
def test_voice_player_event_disabled(mock_play_sound: MagicMock) -> None:
    """单事件关闭时不应调用 winsound.PlaySound"""
    player = VoicePlayer()
    player.event_enabled = {"recoil_on": False, "recoil_off": True, "lock_on": True, "lock_off": True, "locked_action": True}
    player.play("recoil_on")

    assert not mock_play_sound.called, "事件被禁用时不应播放语音"


@patch("winsound.PlaySound")
def test_voice_player_volume_full(mock_play_sound: MagicMock) -> None:
    """音量为 100 时应直接调用 winsound.PlaySound"""
    player = VoicePlayer()
    player.volume = 100
    player.play("recoil_on")

    assert mock_play_sound.called, "音量为 100 时应播放语音"
    call_args = mock_play_sound.call_args
    wav_path = call_args[0][0]
    assert wav_path.endswith("压枪开启.wav"), f"wav 路径异常: {wav_path}"


@patch("pubg_gun_control.input_listener.ctypes.windll.user32.GetKeyState", return_value=1)
def test_input_listener_lock_intercept(_mock_get_key_state: MagicMock) -> None:
    """锁定模式下切换枪械/配件应被拦截并触发 locked_action 事件"""
    voice_events: list[str] = []
    listener = InputListener(
        callback=lambda _text: None,
        voice_callback=voice_events.append,
        attachment_callback=lambda _cat, _name: None,
        shortcuts=[
            {"modifier": "alt", "mouse_button": "forward", "text": "MP5k"}
        ],
        attachment_shortcuts=[
            {"modifier": "alt", "mouse_button": "middle", "category": "muzzle", "label": "枪口"}
        ],
    )

    # 进入压枪开启状态
    listener._on_key_press(Key.caps_lock)
    assert listener.current_text != "无", "未成功进入压枪开启状态"
    current_gun = listener.current_text
    assert "recoil_on" in voice_events

    # RCtrl + 鼠标后退键锁定
    listener._on_key_press(Key.ctrl_r)
    listener._on_mouse_click(0, 0, Button.x1, True)
    assert listener.is_locked(), "未进入锁定状态"
    assert "lock_on" in voice_events

    # LAlt + 鼠标前进键尝试切换枪械
    listener._on_key_press(Key.alt_l)
    listener._on_mouse_click(0, 0, Button.x2, True)
    assert "locked_action" in voice_events
    assert listener.current_text == current_gun, "锁定状态下枪械不应被切换"

    # LAlt + 鼠标中键尝试切换配件
    listener._on_mouse_click(0, 0, Button.middle, True)
    assert voice_events.count("locked_action") >= 2, "配件切换未触发 locked_action"

    # 无修饰键的鼠标点击不应触发 locked_action
    listener._on_key_release(Key.alt_l)
    before_count = voice_events.count("locked_action")
    listener._on_mouse_click(0, 0, Button.left, True)
    assert voice_events.count("locked_action") == before_count, "无修饰键点击不应触发 locked_action"
