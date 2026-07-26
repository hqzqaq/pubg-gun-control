"""
GHUB Lua 脚本生成器

基于现有 1.2.2 GHUB 脚本，注入自动识别代码，生成完整的新脚本。

@author hqzqaq
@since 2026-06-25
@version 1.0
"""

import logging
import os
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_project_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


DEFAULT_REC_PATH = str(_get_project_root() / "pubg_rec.lua")

AUTO_RECOGNIZE_VARS = """
-- ====== 自动识别变量（由 Python 程序注入） ======
local AUTO_RECOGNIZE = true
local REC_PATH = "%REC_PATH%"

rec_gun = ""
rec_muzzle = 1
rec_grip = 1
rec_stock = 1
rec_scope = 1
local _capsWasOn = false
-- ====== 自动识别变量结束 ======
"""

AUTO_RECOGNIZE_FUNCS = """
-- ====== 自动识别函数（由 Python 程序注入） ======
function pubg.loadRecResult()
    local success, err = pcall(function()
        dofile(REC_PATH)
    end)
    if not success then
        OutputLogMessage("[AUTO] 读取识别结果失败: %s\\n", tostring(err))
        return false
    end
    return true
end

function pubg.applyRecResult()
    if pubg.stateLocked then return end
    if rec_gun ~= "" and rec_gun ~= pubg.getCurrentGunName() then
        if pubg[rec_gun] then
            OutputLogMessage("[AUTO] 切换枪械: %s -> %s\\n", pubg.getCurrentGunName(), rec_gun)
            pubg.setGun(rec_gun)
        else
            OutputLogMessage("[AUTO] 枪械 %s 无弹道数据，跳过\\n", rec_gun)
        end
    end
    if rec_muzzle and rec_muzzle ~= pubg.muzzleIndex then
        OutputLogMessage("[AUTO] 枪口: %d -> %d\\n", pubg.muzzleIndex, rec_muzzle)
        pubg.muzzleIndex = rec_muzzle
    end
    if rec_grip and rec_grip ~= pubg.gripIndex then
        OutputLogMessage("[AUTO] 握把: %d -> %d\\n", pubg.gripIndex, rec_grip)
        pubg.gripIndex = rec_grip
    end
    if rec_stock then
        if gunNoStock[rec_gun] then
            pubg.stockIndex = 1
        elseif rec_stock ~= pubg.stockIndex then
            OutputLogMessage("[AUTO] 枪托: %d -> %d\\n", pubg.stockIndex, rec_stock)
            pubg.stockIndex = rec_stock
        end
    end
    if rec_scope and rec_scope >= 1 then
        local scopeMap = {[1]="scopeX1",[2]="scopeX2",[3]="scopeX3",[4]="scopeX4",[6]="scopeX6"}
        local targetScope = scopeMap[rec_scope] or "scopeX1"
        if targetScope ~= pubg.scope_current then
            OutputLogMessage("[AUTO] 倍镜: %s -> %s\\n", pubg.scope_current, targetScope)
            pubg.scope_current = targetScope
        end
    end
end
-- ====== 自动识别函数结束 ======
"""

AUTO_RECOGNIZE_EVENT_BLOCK = """
    -- 【自动识别】CapsLock 状态变化检测：开启时读取 rec.lua
    if AUTO_RECOGNIZE then
        local capsOn = IsKeyLockOn("capslock")
        if capsOn and not _capsWasOn then
            if pubg.loadRecResult() then
                pubg.applyRecResult()
            end
            OutputLogMessage("[AUTO] ====== 压枪状态 ======\\n")
            OutputLogMessage("[AUTO] 枪械: %s\\n", tostring(rec_gun))
            OutputLogMessage("[AUTO] 枪口: %d | 握把: %d | 枪托: %d | 倍镜: %d\\n", rec_muzzle, rec_grip, rec_stock, rec_scope)
            OutputLogMessage("[AUTO] 当前压枪: %s\\n", pubg.getCurrentGunName())
            OutputLogMessage("[AUTO] ========================\\n")
        end
        _capsWasOn = capsOn
    end
"""


def generate_auto_recognize_script(
    source_path: str,
    output_path: str | None = None,
    rec_path: str | None = None,
) -> str:
    if output_path is None:
        output_path = str(
            Path(__file__).resolve().parent / "generated" / "auto_recognize_ghub.lua"
        )

    effective_rec_path = (rec_path or DEFAULT_REC_PATH).replace("\\", "\\\\")

    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    vars_block = AUTO_RECOGNIZE_VARS.replace("%REC_PATH%", effective_rec_path)

    code_marker = '----------------------------- [[ 以下是脚本核心代码，非专业人士请勿改动 ]] -----------------------------'
    if code_marker in source:
        parts = source.split(code_marker, 1)
        new_source = parts[0] + vars_block + "\n" + code_marker + parts[1]
    else:
        new_source = vars_block + "\n" + source

    init_marker = "pubg.xLengthForDebug"
    if init_marker in new_source:
        idx = new_source.index(init_marker)
        new_source = new_source[:idx] + AUTO_RECOGNIZE_FUNCS + "\n" + new_source[idx:]
    else:
        logger.warning("未找到 pubg 初始化位置，函数定义可能无法正常工作")

    event_marker = "function OnEvent (event, arg, family)"
    if event_marker in new_source:
        idx = new_source.index(event_marker) + len(event_marker)
        new_source = (
            new_source[:idx]
            + AUTO_RECOGNIZE_EVENT_BLOCK
            + new_source[idx:]
        )

    init_line = "pubg.gunOptions[type][gunCount] = pubg[gunName](gunName)"
    safe_init = (
        "if pubg[gunName] then\n"
        "\t\t\t\t\tpubg.gunOptions[type][gunCount] = pubg[gunName](gunName)\n"
        "\t\t\t\telse\n"
        "\t\t\t\t\tpubg.gunOptions[type][gunCount] = { duration=0, amount=0, interval=100, ballistic={0}, ctrlmodeRatio=1, BreathRatio=1, LuopeiRatio=1, ManpeiRatio=1, PaziRatio=1, scopeX2Ratio=1, scopeX3Ratio=1 }\n"
        "\t\t\t\t\tOutputLogMessage(\"[WARN] %s 无弹道数据，已跳过\\n\", gunName)\n"
        "\t\t\t\tend"
    )
    new_source = new_source.replace(init_line, safe_init)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(new_source)

    logger.info("已生成自动识别脚本: %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# dofile 模式：包装脚本 + 配置文件分离
# ---------------------------------------------------------------------------

def generate_config_only(
    source_path: str,
    config_output: str | None = None,
) -> str:
    """只生成纯数据的配置文件（attachmentConfig/gunNoStock/userInfo/枪械弹道函数）

    不包含 OnEvent、pubg.init 等执行逻辑，专供 dofile 模式使用。
    被 generate_dofile_files 和编辑器保存（main_window._on_save_lua）复用。

    Args:
        source_path: 原始基础脚本路径
        config_output: 配置文件输出路径

    Returns:
        配置文件路径
    """
    project_dir = _get_project_root()
    if config_output is None:
        config_output = str(project_dir / "pubg_config.lua")

    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    config_lines: list[str] = []
    config_lines.append("-- 此文件由编辑器自动生成，请勿手动编辑")
    config_lines.append("-- 路径: " + config_output)
    config_lines.append("")

    # 依次提取 attachmentConfig、gunNoStock、userInfo 三个数据块
    # 每个块独立提取：遇到块开始 → 跟踪 {/} 深度 → depth 归零即块结束
    # 不能用单循环 + depth<=0 停止，否则只会提取第一个块（attachmentConfig）
    # 也不能用 depth<=0 and "{" in stripped 停止，那样会把后续 pubg 表和函数都吞进来
    for block_name in ("attachmentConfig", "gunNoStock", "userInfo"):
        in_block = False
        depth = 0
        for line in source.splitlines(keepends=True):
            stripped = line.strip()
            if not in_block:
                if stripped.startswith(block_name):
                    in_block = True
                    depth = 0
            if in_block:
                config_lines.append(line.rstrip("\n"))
                depth += line.count("{") - line.count("}")
                if depth <= 0:
                    config_lines.append("")
                    break

    # 找到所有 pubg["GunName"] 弹道函数
    # 只跟踪 function/end 深度（不跟踪 {/}），否则 { 和 } 不配对会导致 depth 永不归零
    in_gun_func = False
    gun_depth = 0
    for line in source.splitlines(keepends=True):
        stripped = line.strip()
        if not in_gun_func:
            if stripped.startswith('pubg["') and "function" in stripped:
                in_gun_func = True
                gun_depth = 0
        if in_gun_func:
            config_lines.append(line.rstrip("\n"))
            gun_depth += line.count("function")
            gun_depth -= line.count("end")
            if in_gun_func and stripped == "end" and gun_depth <= 0:
                in_gun_func = False
                config_lines.append("")

    with open(config_output, "w", encoding="utf-8") as f:
        f.write("\n".join(config_lines))
    logger.info("已生成配置文件: %s", config_output)
    return config_output


def generate_dofile_files(
    source_path: str,
    config_output: str | None = None,
    wrapper_output: str | None = None,
    rec_path: str | None = None,
    regenerate_config: bool = True,
) -> tuple[str, str]:
    """生成 dofile 模式的两个文件：包装脚本 + 配置文件

    包装脚本：包含所有函数 + OnEvent + dofile加载逻辑 → 粘贴到 GHUB
    配置文件：只包含数据（attachmentConfig/gunNoStock/userInfo/枪械弹道）→ 编辑器保存到此

    Args:
        source_path: 原始基础脚本路径
        config_output: 配置文件输出路径
        wrapper_output: 包装脚本输出路径
        rec_path: rec.lua 路径
        regenerate_config: 是否重新生成配置文件。为 False 时跳过，
            保留现有 pubg_config.lua（当编辑器保存后的配置比基础脚本新时使用）

    Returns:
        (wrapper_path, config_path)
    """
    project_dir = _get_project_root()
    if config_output is None:
        config_output = str(project_dir / "pubg_config.lua")
    if wrapper_output is None:
        wrapper_output = str(
            Path(__file__).resolve().parent / "generated" / "ghub_dofile_wrapper.lua"
        )

    effective_rec = (rec_path or DEFAULT_REC_PATH).replace("\\", "\\\\")
    effective_config = config_output.replace("\\", "\\\\")

    # --- 生成配置文件（纯数据，无函数定义/初始化代码）---
    # 当 regenerate_config=False 时跳过，避免用旧的基础脚本覆盖编辑器刚保存的 pubg_config.lua
    if regenerate_config:
        generate_config_only(source_path, config_output)
    else:
        logger.info("跳过重新生成配置文件，保留现有: %s", config_output)

    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    # --- 生成包装脚本（函数 + OnEvent + dofile逻辑）---
    # 包含：pubg表定义、所有pubg.*函数、OnEvent、初始化逻辑
    wrapper_lines = []
    wrapper_lines.append("-- PUBG 自动压枪脚本（dofile 模式）")
    wrapper_lines.append("-- 此脚本粘贴到 GHUB 中")
    wrapper_lines.append("-- 配置文件: " + config_output)
    wrapper_lines.append("-- 编辑器保存后，CapsLock 开关自动加载最新配置")
    wrapper_lines.append("")
    wrapper_lines.append("EnablePrimaryMouseButtonEvents(true)")
    wrapper_lines.append("")
    wrapper_lines.append('local CONFIG_PATH = "' + effective_config + '"')
    wrapper_lines.append('local REC_PATH = "' + effective_rec + '"')
    wrapper_lines.append("local AUTO_RECOGNIZE = true")
    wrapper_lines.append("local _capsWasOn = false")
    wrapper_lines.append("local _configLoaded = false")
    wrapper_lines.append("")
    wrapper_lines.append("rec_gun = \"\"")
    wrapper_lines.append("rec_muzzle = 1")
    wrapper_lines.append("rec_grip = 1")
    wrapper_lines.append("rec_stock = 1")
    wrapper_lines.append("rec_scope = 1")
    wrapper_lines.append("")

    # userInfo 默认值（dofile 加载配置前供 pubg 表定义使用，加载后被覆盖）
    wrapper_lines.append("userInfo = {")
    wrapper_lines.append("\tcpuLoad = 2,")
    wrapper_lines.append("\tsensitivity = { ADS = 70, Aim = 0.55, scopeX2 = 1.4, scopeX3 = 3.6, scopeX4 = 3.0, scopeX6 = 1.25 },")
    wrapper_lines.append("}")
    wrapper_lines.append("")

    # 提取 pubg = { 表定义（到 pubg.xLengthForDebug 之前）
    in_pubg_table = False
    pubg_depth = 0
    user_info_fields = []  # 记录 pubg 表中引用 userInfo 的字段（供 loadConfig 刷新）
    for line in source.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("pubg = {"):
            in_pubg_table = True
            pubg_depth = 0
        if in_pubg_table:
            wrapper_lines.append(line.rstrip("\n"))
            pubg_depth += line.count("{") - line.count("}")
            if "userInfo" in stripped:
                user_info_fields.append(stripped)
            if pubg_depth <= 0:
                in_pubg_table = False
                break

    # 提取从 pubg.xLengthForDebug 到 OnEvent 之前的所有函数
    in_functions = False
    for line in source.splitlines(keepends=True):
        stripped = line.strip()
        if "pubg.xLengthForDebug" in stripped:
            in_functions = True
        if in_functions:
            if stripped.startswith("function OnEvent"):
                break
            wrapper_lines.append(line.rstrip("\n"))

    # 添加 dofile 相关函数
    wrapper_lines.append("")
    wrapper_lines.append("-- 通用 Lua 文件加载函数（绕过 GHub dofile 运行时缓存）")
    wrapper_lines.append("-- GHub 的 dofile 在脚本启动时内联文件内容，运行时调用不会重新读磁盘")
    wrapper_lines.append("-- 改用 io.open + loadstring 每次都从磁盘读取最新内容")
    wrapper_lines.append("function loadLuaFile(path)")
    wrapper_lines.append("    if io and io.open then")
    wrapper_lines.append("        local f = io.open(path, 'r')")
    wrapper_lines.append("        if f then")
    wrapper_lines.append("            local content = f:read('*a')")
    wrapper_lines.append("            f:close()")
    wrapper_lines.append("            local chunk, lerr = loadstring(content)")
    wrapper_lines.append("            if chunk then")
    wrapper_lines.append("                return pcall(chunk)")
    wrapper_lines.append("            else")
    wrapper_lines.append("                return false, 'loadstring 失败: ' .. tostring(lerr)")
    wrapper_lines.append("            end")
    wrapper_lines.append("        else")
    wrapper_lines.append("            return false, 'io.open 失败: ' .. path")
    wrapper_lines.append("        end")
    wrapper_lines.append("    else")
    wrapper_lines.append("        if package and package.loaded then package.loaded[path] = nil end")
    wrapper_lines.append("        return pcall(function() dofile(path) end)")
    wrapper_lines.append("    end")
    wrapper_lines.append("end")
    wrapper_lines.append("")
    wrapper_lines.append("-- dofile 加载函数")
    wrapper_lines.append("function loadConfig()")
    wrapper_lines.append("    local ok, err = loadLuaFile(CONFIG_PATH)")
    wrapper_lines.append("    if ok then")
    wrapper_lines.append("        _configLoaded = true")
    # dofile 后 userInfo 已被配置文件覆盖，刷新 pubg 表中引用 userInfo 的字段
    for field_line in user_info_fields:
        code_part = field_line.split("--")[0].strip()
        if code_part.endswith(","):
            code_part = code_part[:-1].strip()
        m = re.match(r"(\w+)\s*=\s*(.+)$", code_part)
        if m:
            field_name = m.group(1)
            field_expr = m.group(2).strip()
            wrapper_lines.append(f"        pubg.{field_name} = {field_expr}")
    wrapper_lines.append("        pubg.init()")
    wrapper_lines.append('        OutputLogMessage("[CONFIG] 配置已加载\\n")')
    wrapper_lines.append("    else")
    wrapper_lines.append('        OutputLogMessage("[CONFIG] 加载失败: %s\\n", tostring(err))')
    wrapper_lines.append("    end")
    wrapper_lines.append("    return ok")
    wrapper_lines.append("end")
    wrapper_lines.append("")
    wrapper_lines.append("function loadRecResult()")
    wrapper_lines.append("    local before = tostring(rec_gun)")
    wrapper_lines.append("    local ok, err = loadLuaFile(REC_PATH)")
    wrapper_lines.append("    if ok then")
    wrapper_lines.append('        OutputLogMessage("[AUTO] 读取识别结果: %s -> %s (muzzle=%d grip=%d stock=%d scope=%d)\\n", before, tostring(rec_gun), rec_muzzle, rec_grip, rec_stock, rec_scope)')
    wrapper_lines.append("    else")
    wrapper_lines.append('        OutputLogMessage("[AUTO] 读取识别结果失败: %s\\n", tostring(err))')
    wrapper_lines.append("    end")
    wrapper_lines.append("    return ok")
    wrapper_lines.append("end")
    wrapper_lines.append("")
    wrapper_lines.append("function applyRecResult()")
    wrapper_lines.append("    if pubg.stateLocked then")
    wrapper_lines.append('        OutputLogMessage("[AUTO] 状态已锁定，跳过应用\\n")')
    wrapper_lines.append("        return")
    wrapper_lines.append("    end")
    wrapper_lines.append('    OutputLogMessage("[AUTO] 应用识别结果: 当前=%s 目标=%s\\n", tostring(pubg.getCurrentGunName()), tostring(rec_gun))')
    wrapper_lines.append("    if rec_gun ~= \"\" and rec_gun ~= pubg.getCurrentGunName() then")
    wrapper_lines.append("        if pubg[rec_gun] then")
    wrapper_lines.append("            pubg.setGun(rec_gun)")
    wrapper_lines.append("        else")
    wrapper_lines.append('            OutputLogMessage("[AUTO] %s 无弹道数据\\n", rec_gun)')
    wrapper_lines.append("        end")
    wrapper_lines.append("    end")
    wrapper_lines.append("    if rec_muzzle and rec_muzzle ~= pubg.muzzleIndex then")
    wrapper_lines.append("        pubg.muzzleIndex = rec_muzzle")
    wrapper_lines.append("    end")
    wrapper_lines.append("    if rec_grip and rec_grip ~= pubg.gripIndex then")
    wrapper_lines.append("        pubg.gripIndex = rec_grip")
    wrapper_lines.append("    end")
    wrapper_lines.append("    if rec_stock then")
    wrapper_lines.append("        if gunNoStock[rec_gun] then")
    wrapper_lines.append("            pubg.stockIndex = 1")
    wrapper_lines.append("        elseif rec_stock ~= pubg.stockIndex then")
    wrapper_lines.append("            pubg.stockIndex = rec_stock")
    wrapper_lines.append("        end")
    wrapper_lines.append("    end")
    wrapper_lines.append("    if rec_scope and rec_scope >= 1 then")
    wrapper_lines.append('        local scopeMap = {[1]="scopeX1",[2]="scopeX2",[3]="scopeX3",[4]="scopeX4",[6]="scopeX6"}')
    wrapper_lines.append("        local s = scopeMap[rec_scope] or \"scopeX1\"")
    wrapper_lines.append("        if s ~= pubg.scope_current then")
    wrapper_lines.append("            pubg.scope_current = s")
    wrapper_lines.append("        end")
    wrapper_lines.append("    end")
    wrapper_lines.append("end")

    # 添加 OnEvent
    wrapper_lines.append("")
    wrapper_lines.append("function OnEvent(event, arg, family)")
    wrapper_lines.append("    local capsOn = IsKeyLockOn(\"capslock\")")
    wrapper_lines.append("    if capsOn and not _capsWasOn then")
    wrapper_lines.append('        OutputLogMessage("[AUTO] CapsLock 上升沿: 加载配置+识别结果\\n")')
    wrapper_lines.append("        loadConfig()")
    wrapper_lines.append("        if AUTO_RECOGNIZE then")
    wrapper_lines.append("            if loadRecResult() then")
    wrapper_lines.append("                applyRecResult()")
    wrapper_lines.append("            end")
    wrapper_lines.append("        end")
    wrapper_lines.append("    end")
    wrapper_lines.append("    _capsWasOn = capsOn")
    wrapper_lines.append("")
    wrapper_lines.append("    if AUTO_RECOGNIZE and event == \"MOUSE_BUTTON_PRESSED\" and arg == 1 and family == \"mouse\" then")
    wrapper_lines.append("        if capsOn and _configLoaded then")
    wrapper_lines.append("            if loadRecResult() then")
    wrapper_lines.append("                applyRecResult()")
    wrapper_lines.append("            end")
    wrapper_lines.append("        end")
    wrapper_lines.append("    end")
    wrapper_lines.append("")
    wrapper_lines.append("    if _configLoaded then")
    wrapper_lines.append("        pubg.OnEvent_NoRecoil(event, arg, family)")
    wrapper_lines.append("    end")
    wrapper_lines.append("end")

    # 添加工具函数和初始化
    wrapper_lines.append("")
    wrapper_lines.append("-- 工具函数")
    wrapper_lines.append("function math.round(num, digit)")
    wrapper_lines.append("    local d = 10 ^ (digit or 0)")
    wrapper_lines.append("    return math.floor((num * d * 10 + 5) / 10) / d")
    wrapper_lines.append("end")
    wrapper_lines.append("")
    wrapper_lines.append("function string.split(str, s)")
    wrapper_lines.append("    if string.find(str, s) == nil then return { str } end")
    wrapper_lines.append("    local res = {}")
    wrapper_lines.append('    local reg = "(.-)" .. s .. "()"')
    wrapper_lines.append("    local index = 0")
    wrapper_lines.append("    local last_i")
    wrapper_lines.append("    for n, i in string.gmatch(str, reg) do")
    wrapper_lines.append("        index = index + 1")
    wrapper_lines.append("        res[index] = n")
    wrapper_lines.append("        last_i = i")
    wrapper_lines.append("    end")
    wrapper_lines.append("    res[index + 1] = string.sub(str, last_i)")
    wrapper_lines.append("    return res")
    wrapper_lines.append("end")

    with open(wrapper_output, "w", encoding="utf-8") as f:
        f.write("\n".join(wrapper_lines))
    logger.info("已生成包装脚本: %s", wrapper_output)

    return wrapper_output, config_output


def generate_dofile_wrapper(
    config_path: str,
    rec_path: str | None = None,
    output_path: str | None = None,
) -> str:
    """生成 dofile 模式的 GHUB 包装脚本（兼容旧接口）"""
    if output_path is None:
        output_path = str(
            Path(__file__).resolve().parent / "generated" / "ghub_dofile_wrapper.lua"
        )

    effective_config = config_path.replace("\\", "\\\\")
    effective_rec = (rec_path or DEFAULT_REC_PATH).replace("\\", "\\\\")

    from pubg_gun_control.config_manager import load_base_lua_path
    source = load_base_lua_path()
    wrapper, _ = generate_dofile_files(source, config_output=config_path, wrapper_output=output_path, rec_path=rec_path)
    return wrapper
