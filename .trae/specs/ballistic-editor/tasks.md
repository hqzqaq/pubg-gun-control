# Tasks

> 实施顺序按依赖排列；带「并行」标记的可在同批次启动多个 sub-agent。

- [x] Task 1: 引入新依赖并在 pyproject.toml 落库
  - [x] SubTask 1.1: 在 `pyproject.toml` 的 `[project].dependencies` 增加 `PySide6>=6.6.0` 与 `matplotlib>=3.8.0`
  - [x] SubTask 1.2: 同步更新 `uv.lock`（执行 `uv lock`）
  - [x] SubTask 1.3: 验证 `uv sync` 后 `from PySide6 import QtWidgets` 与 `import matplotlib` 不报错

- [x] Task 2: 实现 lua 解析器与数据模型（核心数据层，先做）
  - [x] SubTask 2.1: 新建 `src/pubg_gun_control/ballistic_data.py`，定义 5 个 dataclass
  - [x] SubTask 2.2: 新建 `src/pubg_gun_control/lua_parser.py`，定义异常与解析器类
  - [x] SubTask 2.3: 实现 `parse(path) -> BallisticConfig`
  - [x] SubTask 2.4: 实现 `serialize(config, path)`
  - [x] SubTask 2.5: 实现 `backup(path)`
  - [x] SubTask 2.6: 编写 `test/test_lua_parser.py`（4 项全过）

- [x] Task 3: 实现弹道轨迹计算与 matplotlib 渲染组件
  - [x] SubTask 3.1: 新建 `src/pubg_gun_control/editor_ui/trajectory_view.py` + `TrajectoryCalculator`
  - [x] SubTask 3.2: 实现 `TrajectoryView(QWidget)` 嵌入 matplotlib
  - [x] SubTask 3.3: 绘图样式：裸配红/当前绿，标题写枪名，等比例坐标轴

- [x] Task 4: 实现编辑器主窗口与各面板
  - [x] SubTask 4.1: `BallisticEditorWindow(QMainWindow)` 三栏布局 + 菜单栏
  - [x] SubTask 4.2: `GunListPanel` 按弹药类型分组，mode 0/1/2 颜色区分
  - [x] SubTask 4.3: `GunDetailPanel` 8 个 QDoubleSpinBox + mode QComboBox
  - [x] SubTask 4.4: `AttachmentPanel` 3 个 Combobox + 满配综合系数实时显示
  - [x] SubTask 4.5: 信号连接：列表 → 详情 → 轨迹图实时刷新

- [x] Task 5: 实现预设管理
  - [x] SubTask 5.1: 菜单项「保存/加载/删除预设」
  - [x] SubTask 5.2: `src/pubg_gun_control/preset_manager.py`
  - [x] SubTask 5.3: `PresetNameDialog(QDialog)`

- [x] Task 6: 编辑器独立入口与最近文件
  - [x] SubTask 6.1: 项目根 `main_editor.py`
  - [x] SubTask 6.2: 扩展 `config_manager.py` 加 `editor.recent_files`
  - [x] SubTask 6.3: 编辑器主窗口「最近打开」子菜单

- [x] Task 7: 与主应用托盘集成
  - [x] SubTask 7.1: 修改 `tray_icon.py` 增加「打开编辑器」菜单项
  - [x] SubTask 7.2: 修改 `main.py` 的 `GunControlApp._on_open_editor` 方法

- [x] Task 8: 端到端测试与验证
  - [x] SubTask 8.1: 集成测试 4/4 项通过（test_editor_integration.py）
  - [x] SubTask 8.2: lua 解析器测试 4/4 项通过（test_lua_parser.py）
  - [x] SubTask 8.3: 所有模块导入验证通过

# Task Dependencies
- Task 2 必须在 Task 3 之前完成（数据层 → 计算层）✓
- Task 3 与 Task 5 可与 Task 4 并行 ✓
- Task 4 必须在 Task 6 之前完成（窗口类要先存在）✓
- Task 7 依赖 Task 6 完成 ✓
- Task 8 必须在所有任务完成后执行 ✓
