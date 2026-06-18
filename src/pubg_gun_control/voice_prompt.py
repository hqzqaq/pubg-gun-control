"""
语音播放模块

提供基于 winsound 的异步语音播放能力，用于 PUBG 枪械切换辅助工具。

@author huquanzhi
@since 2026-06-18
@version 1.0
"""

import logging
import sys
import winsound
from pathlib import Path

logger = logging.getLogger(__name__)


def _resolve_voice_dir() -> Path:
    """定位 voice/ 目录，兼容开发路径与 PyInstaller 打包路径。"""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS) / "voice"
        return Path(sys.executable).parent / "voice"
    return Path(__file__).resolve().parent.parent.parent / "voice"


class VoicePlayer:
    """
    语音播放器。

    根据事件名称异步播放 voice/ 目录下的 WAV 文件，支持开发路径与 PyInstaller 打包路径。

    @since 2026-06-18
    @version 1.0
    """

    _EVENT_FILES = {
        "recoil_on": "压枪开启.wav",
        "recoil_off": "压枪关闭.wav",
        "lock_on": "压枪锁定.wav",
        "lock_off": "压枪解锁.wav",
        "locked_action": "压枪锁定.wav",
    }

    def __init__(self) -> None:
        self._voice_dir = _resolve_voice_dir()
        self.enabled = True

    def play(self, event: str) -> None:
        """根据事件名称异步播放对应的语音文件。"""
        if not self.enabled:
            return

        wav_name = self._EVENT_FILES.get(event)
        if wav_name is None:
            logger.warning("未知语音事件: %s", event)
            return

        wav_path = self._voice_dir / wav_name
        if not wav_path.exists():
            logger.warning("语音文件不存在: %s", wav_path)
            return

        try:
            winsound.PlaySound(
                str(wav_path),
                winsound.SND_ASYNC | winsound.SND_FILENAME,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("播放语音失败: %s, 原因: %s", wav_path, e)
