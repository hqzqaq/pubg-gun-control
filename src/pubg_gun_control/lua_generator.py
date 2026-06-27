"""
GHUB Lua 脚本生成器

基于现有 1.2.2 GHUB 脚本，注入自动识别代码，生成完整的新脚本。

@author hqzqaq
@since 2026-06-25
@version 1.0
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_REC_PATH = str(Path(__file__).resolve().parent.parent.parent / "pubg_rec.lua")

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

DOFILE_WRAPPER = r'''-- PUBG 自动压枪脚本（dofile 模式）
-- 此脚本粘贴到 GHUB 中，通过 dofile 加载本地配置文件
-- 编辑器保存配置后，下次 CapsLock 开关自动生效

EnablePrimaryMouseButtonEvents(true)

local CONFIG_PATH = "%CONFIG_PATH%"
local REC_PATH = "%REC_PATH%"
local AUTO_RECOGNIZE = true
local _capsWasOn = false
local _configLoaded = false

rec_gun = ""
rec_muzzle = 1
rec_grip = 1
rec_stock = 1
rec_scope = 1

function loadConfig()
    local ok, err = pcall(function() dofile(CONFIG_PATH) end)
    if ok then
        _configLoaded = true
        pubg.init()
        OutputLogMessage("[CONFIG] 配置已加载\n")
    else
        OutputLogMessage("[CONFIG] 加载失败: %s\n", tostring(err))
    end
    return ok
end

function loadRecResult()
    local ok, err = pcall(function() dofile(REC_PATH) end)
    if not ok then
        OutputLogMessage("[AUTO] 读取识别结果失败: %s\n", tostring(err))
    end
    return ok
end

function applyRecResult()
    if pubg.stateLocked then return end
    if rec_gun ~= "" and rec_gun ~= pubg.getCurrentGunName() then
        if pubg[rec_gun] then
            pubg.setGun(rec_gun)
        else
            OutputLogMessage("[AUTO] %s 无弹道数据\n", rec_gun)
        end
    end
    if rec_muzzle and rec_muzzle ~= pubg.muzzleIndex then
        pubg.muzzleIndex = rec_muzzle
    end
    if rec_grip and rec_grip ~= pubg.gripIndex then
        pubg.gripIndex = rec_grip
    end
    if rec_stock then
        if gunNoStock[rec_gun] then
            pubg.stockIndex = 1
        elseif rec_stock ~= pubg.stockIndex then
            pubg.stockIndex = rec_stock
        end
    end
    if rec_scope and rec_scope >= 1 then
        local scopeMap = {[1]="scopeX1",[2]="scopeX2",[3]="scopeX3",[4]="scopeX4",[6]="scopeX6"}
        local s = scopeMap[rec_scope] or "scopeX1"
        if s ~= pubg.scope_current then
            pubg.scope_current = s
        end
    end
end

function OnEvent(event, arg, family)
    -- CapsLock 状态变化：开时加载配置 + 读取识别结果
    local capsOn = IsKeyLockOn("capslock")
    if capsOn and not _capsWasOn then
        loadConfig()
        if AUTO_RECOGNIZE then
            if loadRecResult() then
                applyRecResult()
            end
        end
    end
    _capsWasOn = capsOn

    -- 左键开枪：自动识别模式下读取 rec.lua
    if AUTO_RECOGNIZE and event == "MOUSE_BUTTON_PRESSED" and arg == 1 and family == "mouse" then
        if capsOn and _configLoaded then
            if loadRecResult() then
                applyRecResult()
            end
        end
    end

    -- 压枪逻辑
    if _configLoaded then
        pubg.OnEvent_NoRecoil(event, arg, family)
    end
end
'''


def generate_dofile_wrapper(
    config_path: str,
    rec_path: str | None = None,
    output_path: str | None = None,
) -> str:
    """生成 dofile 模式的 GHUB 包装脚本

    Args:
        config_path: 配置文件的本地路径（编辑器保存到此路径）
        rec_path: rec.lua 路径
        output_path: 输出路径

    Returns:
        生成的脚本路径
    """
    if output_path is None:
        output_path = str(
            Path(__file__).resolve().parent / "generated" / "ghub_dofile_wrapper.lua"
        )

    effective_config = config_path.replace("\\", "\\\\")
    effective_rec = (rec_path or DEFAULT_REC_PATH).replace("\\", "\\\\")

    content = DOFILE_WRAPPER.replace("%CONFIG_PATH%", effective_config)
    content = content.replace("%REC_PATH%", effective_rec)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("已生成 dofile 包装脚本: %s", output_path)
    return output_path
