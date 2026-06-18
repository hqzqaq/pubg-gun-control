"""
预设管理器

管理 presets/ 目录下的 JSON 预设文件，提供：
  - list_presets: 列出所有预设
  - save_preset: 保存新预设（同名拒绝覆盖）
  - load_preset: 加载预设
  - delete_preset: 删除预设

@author huquanzhi
@since 2026-06-18 19:45
@version 1.0
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from .ballistic_data import BallisticConfig, BallisticPreset


logger = logging.getLogger(__name__)


class PresetError(Exception):
    """预设操作错误"""


class PresetManager:
    """预设文件管理器

    预设存储路径: <project_root>/presets/<name>.json
    预设名规则: 仅允许 [A-Za-z0-9_-]，长度 1~50
    """

    VALID_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]{1,50}$")

    def __init__(self, presets_dir: str | Path) -> None:
        self.presets_dir = Path(presets_dir)
        self.presets_dir.mkdir(parents=True, exist_ok=True)

    def list_presets(self) -> list[str]:
        """列出所有预设名（按字母序）"""
        if not self.presets_dir.exists():
            return []
        return sorted(p.stem for p in self.presets_dir.glob("*.json"))

    def preset_exists(self, name: str) -> bool:
        return (self.presets_dir / f"{name}.json").exists()

    def save_preset(
        self,
        name: str,
        config: BallisticConfig,
        description: str = "",
        overwrite: bool = False,
    ) -> Path:
        """保存预设

        Args:
            name: 预设名
            config: 完整配置
            description: 备注
            overwrite: 是否覆盖同名预设（默认 False 拒绝覆盖）

        Returns:
            写入的文件路径
        """
        if not self.VALID_NAME_RE.match(name):
            raise PresetError(
                f"预设名不合法: {name!r}（仅允许字母、数字、下划线、连字符，长度 1~50）"
            )

        target = self.presets_dir / f"{name}.json"
        if target.exists() and not overwrite:
            raise PresetError(f"预设已存在: {name}（请使用 overwrite=True 覆盖）")

        preset = BallisticPreset(
            name=name,
            config=config,
            created_at=datetime.now().isoformat(timespec="seconds"),
            description=description,
        )

        try:
            target.write_text(
                json.dumps(preset.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise PresetError(f"保存失败: {exc}") from exc

        logger.info("已保存预设: %s -> %s", name, target)
        return target

    def load_preset(self, name: str) -> BallisticPreset:
        """加载预设"""
        target = self.presets_dir / f"{name}.json"
        if not target.exists():
            raise PresetError(f"预设不存在: {name}")
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PresetError(f"读取失败: {exc}") from exc

        try:
            return BallisticPreset.from_dict(data)
        except (KeyError, ValueError) as exc:
            raise PresetError(f"预设文件损坏: {exc}") from exc

    def delete_preset(self, name: str) -> bool:
        """删除预设，返回是否成功"""
        target = self.presets_dir / f"{name}.json"
        if not target.exists():
            return False
        try:
            target.unlink()
        except OSError as exc:
            raise PresetError(f"删除失败: {exc}") from exc
        logger.info("已删除预设: %s", name)
        return True
