"""姿态识别诊断脚本

运行后切到 PUBG 里依次按 C / Z / Space，脚本会打印：
  1. 按键被 pynput 识别成什么名字（应看到 c / z / space）
  2. 当前前台窗口的进程名（应为 TslGame.exe）
  3. 姿态状态机的实际变化

按 Esc 或 Ctrl+C 结束。
"""

import ctypes
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pynput import keyboard  # noqa: E402

from pubg_gun_control.stance_tracker import StanceTracker, is_pubg_foreground  # noqa: E402

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def foreground_info() -> tuple[str, str]:
    """返回 (进程名, 窗口标题)"""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "<无前台窗口>", ""

        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        kernel32 = ctypes.windll.kernel32
        hproc = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not hproc:
            return f"<打开进程失败 pid={pid.value}>", title
        try:
            name_buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.psapi.GetModuleBaseNameW(hproc, None, name_buf, 260)
            return name_buf.value, title
        finally:
            kernel32.CloseHandle(hproc)
    except Exception as exc:  # noqa: BLE001
        return f"<异常 {exc}>", ""


# 与主程序一致的兜底：char 为 None 时用虚拟键码
_VK_NAME_MAP: dict[int, str] = {code: chr(code + 32) for code in range(65, 91)}
_VK_NAME_MAP.update({code: chr(code) for code in range(48, 58)})


def key_name(key) -> str:
    name = None
    if hasattr(key, "char") and key.char:
        name = key.char.lower()
    elif hasattr(key, "name"):
        name = key.name
    if name:
        return name
    vk = getattr(key, "vk", None)
    if vk is not None:
        return _VK_NAME_MAP.get(vk) or f"<vk={vk}>"
    return "<unknown>"


def main() -> None:
    tracker = StanceTracker(require_focus=True, on_change=lambda s: None)

    print("=" * 60)
    print("姿态识别诊断")
    print("切到 PUBG 窗口，依次按 C（蹲）、Z（趴）、Space（跳）")
    print("Esc 结束")
    print("=" * 60)
    print(f"当前前台: {foreground_info()}")
    print(f"is_pubg_foreground() = {is_pubg_foreground()}")
    print("-" * 60, flush=True)

    last_report = 0.0

    def on_press(key):
        nonlocal last_report
        name = key_name(key)
        proc, title = foreground_info()
        # 焦点检测有开销，同一秒内不重复查询
        now = time.monotonic()
        focus_ok = tracker._require_focus and is_pubg_foreground()

        before = tracker.stance
        changed = tracker.on_press(name) if focus_ok else False
        after = tracker.stance

        # 节流：同一按键连续 repeat 不打满屏
        if now - last_report > 0.05:
            print(
                f"key={str(key):<18} name={name:<6} "
                f"foreground={proc:<16} focus_ok={focus_ok} "
                f"stance: {before} -> {after} (changed={changed})",
                flush=True,
            )
            last_report = now

        if name == "esc":
            return False

    def on_release(key):
        tracker.on_release(key_name(key))

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
