"""
GHUB lua 脚本解析器

支持读写 1.2.2-2024.5.20.-GHUB.-github.lua 中的：
  - canUse 表（弹药分组 + 枪械 8 个系数）
  - attachmentConfig 表（muzzle / grip / stock 配件）
  - gunNoStock 表（不支持枪托的枪械名单）

设计要点：
  - 解析容错：缺字段、格式异常时抛 BallisticParseError 并附行号
  - 序列化保持原结构：canUse / attachmentConfig / gunNoStock 三段独立替换，
    其余 lua 内容（如 userInfo、function OnEvent 等）原样保留
  - 写前自动备份：<path>.bak

@author huquanzhi
@since 2026-06-18 19:30
@version 1.0
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

from .ballistic_data import (
    DEFAULT_INTERVAL,
    AttachmentCategory,
    AttachmentItem,
    BallisticConfig,
    GunCoefficients,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------


class BallisticParseError(Exception):
    """lua 解析错误"""

    def __init__(self, message: str, line_no: int = 0, context: str = "") -> None:
        super().__init__(f"{message} [行 {line_no}]: {context}".strip())
        self.line_no = line_no
        self.context = context


# ---------------------------------------------------------------------------
# 正则
# ---------------------------------------------------------------------------


# 匹配 ammo 分组起始: ["7.62"] = {
_RE_AMMO_OPEN = re.compile(r'\[\s*"([^"]+)"\s*\]\s*=\s*\{')

# 匹配单条枪械行: { "Name", 1, 8.65, 0.82, 1.40, 1.25, 1.95, 0.30, 1.24, 0.75},
_RE_GUN_ROW = re.compile(
    r'\{\s*"([^"]+)"\s*,\s*'                       # 枪名
    r'(\d+)\s*,\s*'                                  # mode
    r'([\d.]+)\s*,\s*'                               # coef
    r'([\d.]+)\s*,\s*'                               # crouch
    r'([\d.]+)\s*,\s*'                               # breath
    r'([\d.]+)\s*,\s*'                               # bare
    r'([\d.]+)\s*,\s*'                               # full
    r'([\d.]+)\s*,\s*'                               # prone
    r'([\d.]+)\s*,\s*'                               # scope2x
    r'([\d.]+)\s*'                                   # scope3x
    r'\s*\},?'
)

# 匹配 ammo 分组结束: },
# 简化判定: 行内独立一个 `}` 或 `},`
_RE_GROUP_CLOSE = re.compile(r'^\s*\},?\s*$')

# canUse 块起始: 行内包含 `canUse = {`（前面可有空白/注释）
_RE_CANUSE_START = re.compile(r'^\s*canUse\s*=\s*\{\s*$')
_RE_CANUSE_END = re.compile(r'^\s*\}\s*,?\s*$')

# attachmentConfig 块起始/结束
_RE_ATTACH_START = re.compile(r'^\s*attachmentConfig\s*=\s*\{\s*$')

# 匹配单条配件: { name = "x", label = "y", ratio = 1.00 },
_RE_ATTACH_ITEM = re.compile(
    r'\{\s*name\s*=\s*"([^"]+)"\s*,\s*'
    r'label\s*=\s*"([^"]+)"\s*,\s*'
    r'ratio\s*=\s*([\d.]+)\s*\},?'
)

# 匹配配件子表起始: muzzle = {  /  grip = {  /  stock = {
# 注意: 行尾可能带注释(如 "muzzle = {   -- 枪口配件")，不能用 \s*$ 锚定行尾
_RE_ATTACH_CAT = re.compile(r'^\s*(muzzle|grip|stock)\s*=\s*\{')

# gunNoStock 块
_RE_GUN_NO_STOCK_START = re.compile(r'^\s*gunNoStock\s*=\s*\{\s*$')
_RE_GUN_NO_STOCK_ENTRY = re.compile(r'\[\s*"([^"]+)"\s*\]\s*=\s*true')

# pubg["GunName"] = function (gunName)
_RE_GUN_FUNC_START = re.compile(r'^\s*pubg\[\s*"([^"]+)"\s*\]\s*=\s*function\s*\(')
_RE_INTERVAL = re.compile(r'interval\s*=\s*(\d+)')
_RE_BALLISTIC_ROW = re.compile(r'\{\s*(\d+)\s*,\s*([\d.]+)\s*\}')


# ---------------------------------------------------------------------------
# 解析器
# ---------------------------------------------------------------------------


class LuaBallisticParser:
    """GHUB lua 弹道配置解析器

    用法:
        parser = LuaBallisticParser()
        config = parser.parse("path/to/1.2.2-2024.5.20.-GHUB.-github.lua")
        # ... 修改 config ...
        parser.serialize(config, "path/to/1.2.2-2024.5.20.-GHUB.-github.lua")
    """

    def parse(self, path: str | Path) -> BallisticConfig:
        """解析 lua 文件为 BallisticConfig"""
        file_path = Path(path)
        if not file_path.exists():
            raise BallisticParseError(f"文件不存在: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise BallisticParseError(f"读取文件失败: {exc}") from exc

        config = BallisticConfig(source_path=str(file_path))
        config.ammo_groups = self._parse_canuse(content)
        config.attachment_config = self._parse_attachment_config(content)
        config.gun_no_stock = self._parse_gun_no_stock(content)
        self._merge_gun_functions(config, content)
        return config

    # ---- canUse ----

    def _parse_canuse(self, content: str) -> dict[str, list[GunCoefficients]]:
        result: dict[str, list[GunCoefficients]] = {}
        lines = content.splitlines()
        in_canuse = False
        current_ammo: str | None = None
        depth = 0  # 从 canUse `{` 开始的 brace 深度

        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not in_canuse:
                if _RE_CANUSE_START.match(line):
                    in_canuse = True
                    depth = 1
                continue

            # 统计本行 brace 变化
            prev_depth = depth
            depth += line.count("{") - line.count("}")

            # canUse 整块结束
            if depth <= 0:
                in_canuse = False
                current_ammo = None
                continue

            # 弹药组起始
            ammo_match = _RE_AMMO_OPEN.search(line)
            if ammo_match:
                current_ammo = ammo_match.group(1)
                result.setdefault(current_ammo, [])
                continue

            # 弹药组结束: depth 从 2 回到 1
            if (
                current_ammo is not None
                and prev_depth == 2
                and depth == 1
                and "[" not in stripped
            ):
                current_ammo = None
                continue

            # 枪械行
            if current_ammo is not None:
                gun_match = _RE_GUN_ROW.search(line)
                if gun_match:
                    name = gun_match.group(1)
                    mode = int(gun_match.group(2))
                    numbers = [float(gun_match.group(i)) for i in range(3, 11)]
                    try:
                        gun = GunCoefficients.from_lua_row(name, mode, numbers)
                        result[current_ammo].append(gun)
                    except ValueError as exc:
                        raise BallisticParseError(str(exc), line_no, line) from exc

        return result

    # ---- attachmentConfig ----

    def _parse_attachment_config(self, content: str) -> dict[str, AttachmentCategory]:
        result: dict[str, AttachmentCategory] = {}
        lines = content.splitlines()
        in_block = False
        current_cat: str | None = None
        in_cat = False

        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()

            if not in_block:
                if _RE_ATTACH_START.match(line):
                    in_block = True
                continue

            cat_match = _RE_ATTACH_CAT.match(line)
            if cat_match and not in_cat:
                current_cat = cat_match.group(1)
                result[current_cat] = AttachmentCategory()
                in_cat = True
                continue

            if in_cat and stripped == "},":
                in_cat = False
                current_cat = None
                continue

            if stripped == "}," and current_cat is None:
                # attachmentConfig 整块结束
                in_block = False
                continue

            if in_cat and current_cat is not None:
                item_match = _RE_ATTACH_ITEM.search(line)
                if item_match:
                    result[current_cat].items.append(
                        AttachmentItem(
                            name=item_match.group(1),
                            label=item_match.group(2),
                            ratio=float(item_match.group(3)),
                        )
                    )

        return result

    # ---- gunNoStock ----

    def _parse_gun_no_stock(self, content: str) -> dict[str, bool]:
        result: dict[str, bool] = {}
        lines = content.splitlines()
        in_block = False

        for line in lines:
            stripped = line.strip()
            if not in_block:
                if _RE_GUN_NO_STOCK_START.match(line):
                    in_block = True
                continue

            if stripped == "}":
                break

            match = _RE_GUN_NO_STOCK_ENTRY.search(line)
            if match:
                result[match.group(1)] = True

        return result

    # ---- pubg["GunName"] 弹道函数 ----

    def _merge_gun_functions(self, config: BallisticConfig, content: str) -> None:
        """解析 pubg[gunName] 函数，将 interval/ballistic 合并到对应 GunCoefficients"""
        gun_funcs = self.parse_gun_functions(content)
        for ammo, guns in config.ammo_groups.items():
            for gun in guns:
                func = gun_funcs.get(gun.name)
                if func is not None:
                    gun.interval = func["interval"]
                    gun.ballistic = func["ballistic"]

    def parse_gun_functions(
        self, content: str
    ) -> dict[str, dict[str, Any]]:
        """解析所有 pubg[gunName] 函数，返回 {gunName: {interval, ballistic}}"""
        result: dict[str, dict[str, Any]] = {}
        lines = content.splitlines()
        in_func = False
        func_depth = 0
        current_gun: str | None = None
        current_interval = DEFAULT_INTERVAL
        current_ballistic: list[tuple[int, float]] = []

        for line in lines:
            stripped = line.strip()
            if not in_func:
                match = _RE_GUN_FUNC_START.match(line)
                if match:
                    current_gun = match.group(1)
                    current_interval = DEFAULT_INTERVAL
                    current_ballistic = []
                    in_func = True
                    func_depth = 1
                continue

            func_depth += line.count("function")
            func_depth -= line.count("end")

            interval_match = _RE_INTERVAL.search(line)
            if interval_match:
                current_interval = int(interval_match.group(1))

            ballistic_match = _RE_BALLISTIC_ROW.search(line)
            if ballistic_match:
                current_ballistic.append(
                    (int(ballistic_match.group(1)), float(ballistic_match.group(2)))
                )

            if in_func and stripped == "end" and func_depth <= 0:
                if current_gun is not None:
                    result[current_gun] = {
                        "interval": current_interval,
                        "ballistic": current_ballistic,
                    }
                in_func = False
                current_gun = None

        return result

    # ---- 序列化 ----

    def serialize(
        self,
        config: BallisticConfig,
        path: str | Path,
        backup: bool = True,
    ) -> None:
        """将 config 写回 lua 文件

        策略: 用占位符标记三段（canUse / attachmentConfig / gunNoStock）的起止，
        然后只替换这三段，其余原样保留。
        """
        file_path = Path(path)
        if not file_path.exists():
            raise BallisticParseError(f"文件不存在: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        new_content = self._replace_block(
            content,
            block_start_re=_RE_CANUSE_START,
            new_block=self._render_canuse(config),
        )
        new_content = self._replace_block(
            new_content,
            block_start_re=_RE_ATTACH_START,
            new_block=self._render_attachment_config(config),
        )
        new_content = self._replace_block(
            new_content,
            block_start_re=_RE_GUN_NO_STOCK_START,
            new_block=self._render_gun_no_stock(config),
        )
        new_content = self._replace_gun_functions(new_content, config)

        if backup:
            self._backup(file_path)

        try:
            file_path.write_text(new_content, encoding="utf-8")
        except OSError as exc:
            raise BallisticParseError(f"写入失败: {exc}") from exc

    def _replace_block(
        self,
        content: str,
        block_start_re: re.Pattern[str],
        new_block: str,
    ) -> str:
        """在 content 中找到 block_start_re 匹配的行到对应结束 `}`，替换为 new_block

        如果目标块（如 canUse）嵌套在父块（如 userInfo）内部，
        则替换范围延伸到父块的结束 `}`，以保留父块的其余内容（如 G_bind）。
        """
        lines = content.splitlines(keepends=True)

        start_idx: int | None = None
        for i, line in enumerate(lines):
            if block_start_re.match(line):
                start_idx = i
                break

        if start_idx is None:
            logger.warning("未找到块: %s，跳过", block_start_re.pattern)
            return content

        # 从 start_idx 向上查找是否在父块内（如 userInfo = {）
        parent_start: int | None = None
        for i in range(start_idx - 1, -1, -1):
            stripped = lines[i].strip()
            # 跳过空行和注释
            if not stripped or stripped.startswith("--"):
                continue
            # 检查是否是块定义（xxx = {），且不是目标块自身
            if (stripped.endswith("= {") or stripped.endswith("={")) and i != start_idx:
                parent_start = i
                break
            break

        # 从 start_idx 之后开始扫描 brace 深度，找到目标块的结束 `}`
        depth = 1
        target_end: int | None = None
        for j in range(start_idx + 1, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            if depth <= 0:
                target_end = j
                break

        if target_end is None:
            logger.warning("未找到块结束: %s", block_start_re.pattern)
            return content

        # 如果在父块内，继续扫描到父块结束
        if parent_start is not None:
            parent_depth = 0
            for j in range(parent_start, len(lines)):
                parent_depth += lines[j].count("{") - lines[j].count("}")
                if parent_depth <= 0:
                    # 父块结束于 j，替换范围是 start_idx 到 j（保留父块开始到 start_idx 之间的内容）
                    before = lines[:start_idx]
                    after = lines[j + 1:]
                    # 保留 parent_start 到 start_idx 之间的内容（父块头部）
                    parent_header = lines[parent_start:start_idx]
                    # 保留 target_end+1 到 j 之间的内容（父块尾部，如 G_bind）
                    parent_tail = lines[target_end + 1:j + 1]
                    new_lines = lines[:parent_start] + parent_header + [new_block] + parent_tail + after
                    return "".join(new_lines)

        # 不在父块内，直接替换
        before = lines[:start_idx]
        after = lines[target_end + 1:]
        new_lines = before + [new_block] + after
        return "".join(new_lines)

    def _render_canuse(self, config: BallisticConfig) -> str:
        """渲染 canUse 表，保持与原文件一致的制表符缩进

        canUse 是 userInfo 表的字段（非顶级变量），因此：
        - 起始行保留制表符缩进
        - 结束花括号后必须带逗号，以分隔后续字段（如 G_bind）
        """
        lines: list[str] = ["\tcanUse = {"]
        for ammo, guns in config.ammo_groups.items():
            lines.append(f'\t\t["{ammo}"] = {{')
            if not guns:
                lines.append("\t\t},")
                continue
            name_width = max(len(g.name) for g in guns) + 2  # 包含引号
            for g in guns:
                lines.append("\t\t\t" + self._format_gun_row(g, name_width))
            lines.append("\t\t},")
        lines.append("\t},")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _format_gun_row(gun: GunCoefficients, name_width: int) -> str:
        """格式化为单行 gun entry"""
        name = f'"{gun.name}"'
        name_padded = name.ljust(name_width)
        nums = gun.to_lua_numbers()
        parts = [name_padded, str(gun.mode)]
        parts.extend(_format_number(n) for n in nums)
        return "{ " + ",".join("\t" + p for p in parts) + "},"

    def _render_attachment_config(self, config: BallisticConfig) -> str:
        """渲染 attachmentConfig 表"""
        lines: list[str] = ["attachmentConfig = {"]
        cat_labels = {"muzzle": "枪口配件", "grip": "握把配件", "stock": "枪托配件"}
        for cat in ("muzzle", "grip", "stock"):
            category = config.attachment_config.get(cat)
            lines.append(f"\t{cat} = {{   -- {cat_labels[cat]}")
            if category is None or not category.items:
                lines.append("\t},")
                continue
            name_w = max(len(i.name) for i in category.items) + 2
            label_w = max(len(i.label) for i in category.items) + 2
            for i, item in enumerate(category.items):
                sep = "," if i < len(category.items) - 1 else ""
                lines.append(
                    "\t\t" + self._format_attachment_item(item, name_w, label_w) + sep
                )
            lines.append("\t},")
        lines.append("}")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _format_attachment_item(
        item: AttachmentItem, name_w: int, label_w: int
    ) -> str:
        return (
            "{ name = "
            + f'"{item.name}"'.ljust(name_w)
            + ", label = "
            + f'"{item.label}"'.ljust(label_w)
            + f", ratio = {item.ratio:.2f} }}"
        )

    def _render_gun_no_stock(self, config: BallisticConfig) -> str:
        """渲染 gunNoStock 表"""
        if not config.gun_no_stock:
            return "gunNoStock = {}\n"
        lines = ["gunNoStock = {"]
        name_w = max(len(n) for n in config.gun_no_stock)
        for name in config.gun_no_stock:
            lines.append(f'\t["{name}"]{"".ljust(name_w - len(name))} = true,')
        lines.append("}")
        lines.append("")
        return "\n".join(lines)

    def _replace_gun_functions(self, content: str, config: BallisticConfig) -> str:
        """删除旧 pubg[gunName] 函数，在文件末尾追加渲染后的函数"""
        lines = content.splitlines(keepends=True)
        # 收集所有函数块范围
        blocks: list[tuple[int, int]] = []
        in_func = False
        func_depth = 0
        start_idx: int | None = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not in_func:
                if _RE_GUN_FUNC_START.match(line):
                    start_idx = i
                    in_func = True
                    func_depth = 1
                continue
            func_depth += line.count("function")
            func_depth -= line.count("end")
            if in_func and stripped == "end" and func_depth <= 0:
                blocks.append((start_idx, i))
                in_func = False
                start_idx = None

        # 从后往前删除，避免索引偏移
        new_lines = list(lines)
        for start, end in reversed(blocks):
            # 删除函数块及后续空行
            del_end = end
            while del_end + 1 < len(new_lines) and new_lines[del_end + 1].strip() == "":
                del_end += 1
            del new_lines[start:del_end + 1]

        # 确保末尾有换行
        while new_lines and new_lines[-1].strip() == "":
            new_lines.pop()
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"

        rendered = self._render_gun_functions(config)
        if rendered:
            new_lines.append("\n")
            new_lines.append(rendered)

        return "".join(new_lines)

    def _render_gun_functions(self, config: BallisticConfig) -> str:
        """渲染 canUse 中所有枪械的 pubg[gunName] 函数"""
        lines: list[str] = []
        for ammo, guns in config.ammo_groups.items():
            for gun in guns:
                if gun.mode == 0:
                    continue
                lines.append(f'pubg["{gun.name}"] = function (gunName)')
                lines.append("")
                lines.append("\treturn pubg.execOptions(gunName, {")
                lines.append(f"\t\tinterval = {gun.interval},")
                lines.append("\t\tballistic = {")
                for num, offset in gun.ballistic:
                    lines.append(f"\t\t\t{{{num}, {offset}}},")
                lines.append("\t\t}")
                lines.append("\t})")
                lines.append("")
                lines.append("end")
                lines.append("")
        return "\n".join(lines)

    # ---- 备份 ----

    @staticmethod
    def backup(path: str | Path) -> Path:
        """将 path 备份为 <path>.bak（覆盖旧备份）"""
        file_path = Path(path)
        bak_path = file_path.with_suffix(file_path.suffix + ".bak")
        if file_path.exists():
            shutil.copy2(file_path, bak_path)
            logger.info("已备份: %s", bak_path)
        return bak_path

    def _backup(self, path: Path) -> None:
        self.backup(path)


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------


def _format_number(n: float) -> str:
    """格式化为 2 位小数（与 lua 原文件一致）"""
    return f"{n:.2f}"
