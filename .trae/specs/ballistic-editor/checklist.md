# Checklist

## 数据层
- [x] `ballistic_data.py` 中 5 个 dataclass 定义完整且字段类型正确
- [x] `LuaBallisticParser.parse()` 能正确解析 `1.2.2-2024.5.20.-GHUB.-github.lua` 的 `canUse` 表（4 个弹药组、19 把枪）
- [x] `LuaBallisticParser.parse()` 能正确解析 `attachmentConfig` 表（5 枪口 + 6 握把 + 3 枪托）
- [x] 解析失败时抛 `BallisticParseError` 并附行号
- [x] `LuaBallisticParser.serialize()` 输出与原文件结构兼容（数字精度、缩进）
- [x] 序列化后 `parse()` 再解析能完全还原（round-trip 测试通过）
- [x] 备份功能正常：第二次保存时 `*.lua.bak` 仍为第一次的原内容

## 计算与可视化
- [x] `TrajectoryCalculator` 能基于 8 个系数生成 30 发累积偏移序列
- [x] 裸配与满配两条轨迹在图中颜色区分明显（红 vs 绿）
- [x] 轨迹图坐标轴等比例（`set_aspect("equal")`）
- [x] 切换枪支/修改系数时，轨迹图实时刷新

## UI 行为
- [x] 枪械列表按 4 个弹药类型分组显示（QTreeView 层级）
- [x] mode 0/1/2 在列表中有视觉区分（颜色：灰/绿/蓝）
- [x] 选中枪支后中部面板与轨迹图同步刷新
- [x] 修改系数时轨迹图实时刷新（`data_changed` 信号）
- [x] 配件 Combobox 在 `gunNoStock` 限制下正确禁用
- [x] 满配综合系数显示正确（实时计算）
- [x] 状态栏「未保存」标记在编辑后出现，保存后消失

## 预设管理
- [x] 保存预设：在 `presets/<name>.json` 生成文件，内容完整
- [x] 加载预设：所有面板正确填充预设值
- [x] 删除预设：JSON 文件被删除
- [x] 预设名重复时弹错误，不覆盖（`PresetError`）
- [x] 预设文件损坏时抛 `PresetError`

## 独立入口
- [x] `uv run python main_editor.py` 能直接启动编辑器
- [x] 启动时若无最近文件，弹出文件选择对话框
- [x] 「最近打开」菜单最多 5 项，去重（`add_editor_recent`）
- [x] 「打开 / 保存 / 另存为 / 退出」菜单功能正确

## 主应用集成
- [x] 主程序托盘菜单有「打开编辑器」项（`TrayIcon.on_open_editor` 回调）
- [x] 点击后 `subprocess.Popen` 启动独立进程
- [x] 编辑器异常退出不影响主浮窗（独立进程隔离）

## 端到端
- [x] 启动编辑器 → 打开 lua → 改 M762 系数 → 保存 → 重新解析 → 新值生效
- [x] 保存预设 → 修改 → 加载 → 值恢复
- [x] 所有模块导入验证通过（`PySide6`、`matplotlib`、`pubg_gun_control.*`）
