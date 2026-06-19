"""
语音播放模块

提供基于 winsound 的异步语音播放能力，用于 PUBG 枪械切换辅助工具。

@author huquanzhi
@since 2026-06-18
@version 1.0
"""

import logging
import sys
import tempfile
import threading
import wave
import winsound
from pathlib import Path

try:
    import audioop  # type: ignore
except ImportError:  # Python 3.13+ 已移除
    audioop = None  # type: ignore

logger = logging.getLogger(__name__)

# 临时文件延迟清理的兜底时长（秒），覆盖多数提示音时长
_TEMP_FILE_TTL_SECONDS = 2.0


def _resolve_voice_dir() -> Path:
    """定位 voice/ 目录，兼容开发路径与 PyInstaller 打包路径。"""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS) / "voice"
        return Path(sys.executable).parent / "voice"
    return Path(__file__).resolve().parent.parent.parent / "voice"


def _safe_remove(path: str) -> None:
    """尽最大努力删除临时文件，失败仅记录。"""
    try:
        Path(path).unlink(missing_ok=True)
    except OSError as exc:  # noqa: BLE001
        logger.debug("删除临时语音文件失败: %s, 原因: %s", path, exc)


class VoicePlayer:
    """
    语音播放器。

    根据事件名称异步播放 voice/ 目录下的 WAV 文件，支持开发路径与 PyInstaller 打包路径。
    支持音量调节与单事件开关。

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
        self.volume: int = 100
        self.event_enabled: dict[str, bool] = {event: True for event in self._EVENT_FILES.keys()}

    def play(self, event: str) -> None:
        """根据事件名称异步播放对应的语音文件。"""
        if not self.enabled:
            return
        if not self.event_enabled.get(event, True):
            return
        if self.volume <= 0:
            return

        wav_name = self._EVENT_FILES.get(event)
        if wav_name is None:
            logger.warning("未知语音事件: %s", event)
            return

        wav_path = self._voice_dir / wav_name
        if not wav_path.exists():
            logger.warning("语音文件不存在: %s", wav_path)
            return

        wav_str = str(wav_path)
        if self.volume >= 100:
            self._play_native(wav_str)
        else:
            self._play_with_volume(wav_str, self.volume)

    def _play_native(self, path: str) -> None:
        """以原音量异步播放 wav。"""
        try:
            winsound.PlaySound(
                path,
                winsound.SND_ASYNC | winsound.SND_FILENAME,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("播放语音失败: %s, 原因: %s", path, exc)

    def _play_with_volume(self, path: str, volume: int) -> None:
        """
        生成调整音量后的临时 wav 并异步播放。

        若 audioop 不可用或 wav 读取/调整失败，回退到原音量播放。
        """
        if audioop is None:
            logger.warning("audioop 不可用，跳过音量调节，使用原音量播放: %s", path)
            self._play_native(path)
            return

        tmp_path: str | None = None
        try:
            with wave.open(path, "rb") as wf:
                sampwidth = wf.getsampwidth()
                nchannels = wf.getnchannels()
                framerate = wf.getframerate()
                nframes = wf.getnframes()
                frames = wf.readframes(nframes)

            factor = max(0.0, min(1.0, volume / 100.0))
            adjusted = audioop.mul(frames, sampwidth, factor)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            with wave.open(tmp_path, "wb") as wf_out:
                wf_out.setnchannels(nchannels)
                wf_out.setsampwidth(sampwidth)
                wf_out.setframerate(framerate)
                wf_out.writeframes(adjusted)
        except (wave.Error, EOFError, ValueError, audioop.error) as exc:  # type: ignore[attr-defined]
            logger.warning("音量调节失败, 播放原始 wav: %s, 原因: %s", path, exc)
            if tmp_path is not None:
                _safe_remove(tmp_path)
            self._play_native(path)
            return
        except OSError as exc:
            logger.warning("生成临时语音文件失败, 播放原始 wav: %s, 原因: %s", path, exc)
            if tmp_path is not None:
                _safe_remove(tmp_path)
            self._play_native(path)
            return

        try:
            winsound.PlaySound(
                tmp_path,
                winsound.SND_ASYNC | winsound.SND_FILENAME,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("播放调节后语音失败: %s, 原因: %s", tmp_path, exc)
            _safe_remove(tmp_path)
            self._play_native(path)
            return

        # 异步清理临时文件：winsound 异步播放时无法直接获取完成回调，
        # 使用 Timer 延迟兜底清理，覆盖所有提示音时长
        threading.Timer(_TEMP_FILE_TTL_SECONDS, _safe_remove, args=(tmp_path,)).start()
