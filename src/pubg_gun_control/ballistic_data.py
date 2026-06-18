"""
弹道系数数据模型

定义枪械系数、配件、配置的 dataclass 及序列化方法。
被 lua_parser.py 与 editor_ui/* 共同依赖。

@author huquanzhi
@since 2026-06-18 19:30
@version 1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


# ---------------------------------------------------------------------------
# 配件
# ---------------------------------------------------------------------------


@dataclass
class AttachmentItem:
    """单个配件项"""

    name: str
    label: str
    ratio: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttachmentItem":
        return cls(
            name=str(data["name"]),
            label=str(data["label"]),
            ratio=float(data["ratio"]),
        )


@dataclass
class AttachmentCategory:
    """某类配件的完整配置（muzzle / grip / stock）"""

    items: list[AttachmentItem] = field(default_factory=list)

    def find_by_name(self, name: str) -> AttachmentItem | None:
        for item in self.items:
            if item.name == name:
                return item
        return None

    def to_dict(self) -> dict[str, Any]:
        return {"items": [i.to_dict() for i in self.items]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttachmentCategory":
        return cls(items=[AttachmentItem.from_dict(d) for d in data.get("items", [])])


# ---------------------------------------------------------------------------
# 枪械
# ---------------------------------------------------------------------------


@dataclass
class GunCoefficients:
    """单把枪的完整系数配置

    8 个系数顺序对应 lua canUse 表中 8 个数值列：
      自身 / 下蹲 / 屏息 / 裸配 / 满配 / 趴姿 / 2 倍镜 / 3 倍镜
    """

    name: str
    mode: int
    coef: float
    crouch: float
    breath: float
    bare: float
    full: float
    prone: float
    scope2x: float
    scope3x: float

    COEF_FIELDS: tuple[str, ...] = (
        "coef", "crouch", "breath", "bare", "full", "prone", "scope2x", "scope3x",
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GunCoefficients":
        return cls(
            name=str(data["name"]),
            mode=int(data["mode"]),
            **{f: float(data[f]) for f in cls.COEF_FIELDS},
        )

    @classmethod
    def from_lua_row(cls, name: str, mode: int, numbers: list[float]) -> "GunCoefficients":
        """从 lua 解析出的 (name, mode, [n1..n8]) 创建"""
        if len(numbers) < 8:
            raise ValueError(f"枪械 {name!r} 系数数量不足 8 个，实际 {len(numbers)}")
        return cls(
            name=name,
            mode=mode,
            coef=numbers[0],
            crouch=numbers[1],
            breath=numbers[2],
            bare=numbers[3],
            full=numbers[4],
            prone=numbers[5],
            scope2x=numbers[6],
            scope3x=numbers[7],
        )

    def to_lua_numbers(self) -> list[float]:
        return [getattr(self, f) for f in self.COEF_FIELDS]


# ---------------------------------------------------------------------------
# 整体配置
# ---------------------------------------------------------------------------


@dataclass
class BallisticConfig:
    """完整弹道配置：弹药分组 + 配件配置"""

    ammo_groups: dict[str, list[GunCoefficients]] = field(default_factory=dict)
    attachment_config: dict[str, AttachmentCategory] = field(default_factory=dict)
    gun_no_stock: dict[str, bool] = field(default_factory=dict)
    source_path: str = ""

    def find_gun(self, gun_name: str) -> GunCoefficients | None:
        for guns in self.ammo_groups.values():
            for g in guns:
                if g.name == gun_name:
                    return g
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ammo_groups": {
                ammo: [g.to_dict() for g in guns]
                for ammo, guns in self.ammo_groups.items()
            },
            "attachment_config": {
                cat: cfg.to_dict() for cat, cfg in self.attachment_config.items()
            },
            "gun_no_stock": dict(self.gun_no_stock),
            "source_path": self.source_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BallisticConfig":
        return cls(
            ammo_groups={
                ammo: [GunCoefficients.from_dict(g) for g in guns]
                for ammo, guns in data.get("ammo_groups", {}).items()
            },
            attachment_config={
                cat: AttachmentCategory.from_dict(cfg)
                for cat, cfg in data.get("attachment_config", {}).items()
            },
            gun_no_stock={k: bool(v) for k, v in data.get("gun_no_stock", {}).items()},
            source_path=str(data.get("source_path", "")),
        )


# ---------------------------------------------------------------------------
# 预设
# ---------------------------------------------------------------------------


@dataclass
class BallisticPreset:
    """用户预设（持久化为 presets/<name>.json）"""

    name: str
    config: BallisticConfig
    created_at: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "config": self.config.to_dict(),
            "created_at": self.created_at,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BallisticPreset":
        return cls(
            name=str(data["name"]),
            config=BallisticConfig.from_dict(data.get("config", {})),
            created_at=str(data.get("created_at", "")),
            description=str(data.get("description", "")),
        )
