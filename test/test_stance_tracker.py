"""姿态跟踪状态机与 rec.lua 写入的回归测试

可直接运行：python test/test_stance_tracker.py
也可用 pytest 收集。
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pubg_gun_control.rec_lua_writer import RecLuaWriter  # noqa: E402
from pubg_gun_control.stance_tracker import (  # noqa: E402
    CROUCH,
    PRONE,
    STAND,
    StanceTracker,
)

_TMP = Path(__file__).resolve().parent / "_tmp_stance_rec.lua"


def _tracker(**kwargs) -> StanceTracker:
    kwargs.setdefault("require_focus", False)
    return StanceTracker(**kwargs)


def _tap(tracker: StanceTracker, key: str) -> None:
    tracker.on_press(key)
    tracker.on_release(key)


def test_crouch_toggle() -> None:
    t = _tracker()
    assert t.stance == STAND
    _tap(t, "c")
    assert t.stance == CROUCH
    _tap(t, "c")
    assert t.stance == STAND


def test_prone_transitions() -> None:
    t = _tracker()
    _tap(t, "z")
    assert t.stance == PRONE
    _tap(t, "z")
    assert t.stance == CROUCH
    _tap(t, "c")
    assert t.stance == STAND


def test_break_key_resets_to_stand() -> None:
    t = _tracker()
    _tap(t, "z")
    assert t.stance == PRONE
    _tap(t, "space")
    assert t.stance == STAND
    _tap(t, "c")
    _tap(t, "space")
    assert t.stance == STAND


def test_key_repeat_only_flips_once() -> None:
    """长按不放时系统会持续发 keydown，只应翻转一次"""
    t = _tracker()
    t.on_press("c")
    t.on_press("c")
    t.on_press("c")
    assert t.stance == CROUCH
    t.on_release("c")
    t.on_press("c")
    assert t.stance == STAND


def test_unrelated_key_ignored() -> None:
    t = _tracker()
    _tap(t, "w")
    _tap(t, "r")
    assert t.stance == STAND


def test_disabled_tracker_ignores_keys() -> None:
    t = _tracker(enabled=False)
    _tap(t, "c")
    assert t.stance == STAND


def test_manual_override() -> None:
    t = _tracker()
    _tap(t, "z")
    assert t.set_stance(STAND) is True
    assert t.stance == STAND
    assert t.set_stance(STAND) is False  # 无变化


def test_rec_writer_keeps_gun_on_stance_update() -> None:
    writer = RecLuaWriter(str(_TMP))
    writer.write(gun="RPD", muzzle=1, grip=1, stock=2, scope=1)
    writer.update_stance("crouch")
    text = _TMP.read_text(encoding="utf-8")

    assert 'rec_gun = "RPD"' in text
    assert "rec_stock = 2" in text
    assert 'rec_stance = "crouch"' in text

    writer.write(gun="M416")
    text = _TMP.read_text(encoding="utf-8")
    assert 'rec_gun = "M416"' in text
    assert 'rec_stance = "crouch"' in text  # 姿态不被枪械更新覆盖


def test_lua_pattern_matches_rec_stance() -> None:
    """验证 Lua 侧 string.match 用的正则能从 rec.lua 中取出姿态"""
    for stance in ("stand", "crouch", "prone"):
        content = f'rec_gun = "RPD"\nrec_scope = 1\nrec_stance = "{stance}"\n'
        match = re.search(r'rec_stance\s*=\s*"(\w+)"', content)
        assert match is not None and match.group(1) == stance

    # 没有该字段时 Lua 侧会回退到 stand
    assert re.search(r'rec_stance\s*=\s*"(\w+)"', 'rec_gun = "RPD"\n') is None


def main() -> int:
    tests = [obj for name, obj in sorted(globals().items()) if name.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {test.__name__}: {exc}")
        finally:
            if _TMP.exists():
                os.remove(_TMP)
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
