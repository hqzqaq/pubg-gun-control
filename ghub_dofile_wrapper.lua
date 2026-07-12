-- PUBG 自动压枪脚本（dofile 模式）
-- 此脚本粘贴到 GHUB 中
-- 配置文件: D:\develop\python\pubg-gun-control\pubg_config.lua
-- 编辑器保存后，CapsLock 开关自动加载最新配置

EnablePrimaryMouseButtonEvents(true)

local CONFIG_PATH = "D:\\develop\\python\\pubg-gun-control\\pubg_config.lua"
local REC_PATH = "D:\\develop\\python\\pubg-gun-control\\pubg_rec.lua"
local AUTO_RECOGNIZE = true
local _capsWasOn = false
local _configLoaded = false

rec_gun = ""
rec_muzzle = 1
rec_grip = 1
rec_stock = 1
rec_scope = 1

userInfo = {
	cpuLoad = 2,
	sensitivity = { ADS = 70, Aim = 0.55, scopeX2 = 1.4, scopeX3 = 3.6, scopeX4 = 3.0, scopeX6 = 1.25 },
}

pubg = {
	gun = {
		["9mm"] = {},
		["5.56"] = {},
		["7.62"] = {},
	}, -- 枪械库
	gunOptions = {
		["9mm"] = {},
		["5.56"] = {},
		["7.62"] = {},
	}, -- 配置库
	allCanUse = {}, -- 所有可用枪械
	allCanUse_index = 1, -- 所有可用枪械列表索引
	allCanUse_count = 0, -- 所有可用总数量
	bulletType = "", -- 默认子弹型号
	gunIndex = 1,	-- 选中枪械下标
	counter = 0, -- 计数器
	xCounter = 0, -- x计数器
	sleep = userInfo.cpuLoad, -- 频率设置 (这里不能设置成0，调试会出BUG)
	sleepRandom = { userInfo.cpuLoad, userInfo.cpuLoad + 3 }, -- 防检测随机延迟
	startTime = 0, -- 鼠标按下时记录脚本运行时间戳
	prevTime = 0, -- 记录上一轮脚本运行时间戳
	scopeX1 = 1, -- 基瞄压枪倍率 (裸镜、红点、全息、侧瞄)
	scopeX2 = userInfo.sensitivity.scopeX2, -- 二倍压枪倍率
	scopeX3 = userInfo.sensitivity.scopeX3, -- 三倍压枪倍率
	scopeX4 = userInfo.sensitivity.scopeX4, -- 四倍压枪倍率
	scopeX6 = userInfo.sensitivity.scopeX6, -- 六倍压枪倍率
	scope_current = "scopeX1", -- 当前使用倍镜
	generalSensitivityRatio = userInfo.sensitivity.ADS / 100, -- 按比例调整灵敏度
	isStart = false, -- 是否是启动状态
	stateLocked = false, -- 枪械倍镜锁定状态
	G1 = false, -- G1键状态
	currentTime = 0, -- 此刻
	bulletIndex = 0, -- 第几颗子弹
	-- 配件状态 (索引，1 = 第一个选项)
	muzzleIndex = 1,
	gripIndex = 1,
	stockIndex = 1,
}
pubg.xLengthForDebug = pubg.generalSensitivityRatio * 0 -- 调试模式下的水平移动单元长度
-- 渲染节点
pubg.renderDom = {
	switchTable = "",
	separator = "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n", -- 分割线
	combo_key = "G-key", -- 组合键
	cmd = "cmd", -- 指令
	autoLog = "No operational data yet.\n", -- 压枪过程产生的数据输出
}

-- 是否开镜或瞄准
function pubg.isAimingState (mode)
	local switch = {

		-- 开镜
		["ADS"] = function ()
			if userInfo.aimingSettings == "recommend" then
				return IsMouseButtonPressed(3) --and not IsModifierPressed("lshift")
			elseif userInfo.aimingSettings == "default" then
				return not IsModifierPressed("lshift") and not IsModifierPressed("lalt")
			elseif userInfo.aimingSettings == "ctrlmode" then
				return IsMouseButtonPressed(3)
			elseif userInfo.aimingSettings == "custom" then
				return userInfo.customAimingSettings.ADS()
			end
		end,

		-- 腰射
		["Aim"] = function ()
			if userInfo.aimingSettings == "recommend" then
				if userInfo.autoPressAimKey == "" then
					return IsModifierPressed("lctrl")
				else
					return not IsModifierPressed("lshift") and not IsModifierPressed("lalt")
				end
			elseif userInfo.aimingSettings == "default" then
				return IsMouseButtonPressed(3)
			elseif userInfo.aimingSettings == "ctrlmode" then
				return false
			elseif userInfo.aimingSettings == "custom" then
				return userInfo.customAimingSettings.Aim()
			end
		end,

	}

	return switch[mode]()
end


-- [[通过枪械名查找在 canuse 中的项]]
function pubg.canUseFindByGunName (gunName)
	local forList = { "9mm", "5.56", "7.62" }

	for i = 1, #forList do
		local bulletType = forList[i]
		for j = 1, #userInfo.canUse[bulletType] do
			local item = userInfo.canUse[bulletType][j]
			if item[1] == gunName then
				return item
			end
		end
	end
end

--[[ FormatFactory ]]
function pubg.execOptions (gunName, options)


	local gunInfo = pubg.canUseFindByGunName(gunName)

	local ballisticConfig1 = {}
	local ballisticConfig2 = {}

	local ballisticIndex = 1
	for i = 1, #options.ballistic do
		local nextCount = options.ballistic[i][1]
		if i ~= 1 then
			nextCount = options.ballistic[i][1] - options.ballistic[i - 1][1]
		end
		for j = 1, nextCount do
			ballisticConfig1[ballisticIndex] =
				options.ballistic[i][2] * pubg.generalSensitivityRatio * gunInfo[3]
			ballisticIndex = ballisticIndex + 1
		end
	end

	for i = 1, #ballisticConfig1 do
		if i == 1 then
			ballisticConfig2[i] = ballisticConfig1[i]
		else
			ballisticConfig2[i] = ballisticConfig2[i - 1] + ballisticConfig1[i]
		end
	end


	return {
		duration = options.interval * #ballisticConfig2, -- Time of duration
		amount = #ballisticConfig2, -- Number of bullets
		interval = options.interval, -- Time of each bullet
		ballistic = ballisticConfig2, -- ballistic data
		ctrlmodeRatio = gunInfo[4],
		BreathRatio = gunInfo[5],
		LuopeiRatio = gunInfo[6],
		ManpeiRatio = gunInfo[7],
		PaziRatio = gunInfo[8],
		scopeX2Ratio = gunInfo[9],
		scopeX3Ratio = gunInfo[10]
	}

end

--[[ Initialization of firearms database ]]
function pubg.init ()

	-- Clean up the firearms Depot
	local forList = { "9mm", "5.56", "7.62" }

	for i = 1, #forList do

		local type = forList[i]
		local gunCount = 0

		for j = 1, #userInfo.canUse[type] do
			local gunName = userInfo.canUse[type][j][1]
			local gunState = userInfo.canUse[type][j][2]

			if gunState >= 1 then
				-- one series
				gunCount = gunCount + 1 -- Accumulative number of firearms configuration files
				pubg.gun[type][gunCount] = gunName -- Adding available firearms to the Arsenal
				pubg.gunOptions[type][gunCount] = pubg[gunName](gunName) -- Get firearms data and add it to the configuration library

				-- 单独设置连发
				pubg.gunOptions[type][gunCount].autoContinuousFiring = ({ 0, 0, 1 })[
					math.max(1, math.min(gunState + 1, 3))
				]
				-- all canUse
				pubg.allCanUse_count = pubg.allCanUse_count + 1 -- Total plus one
				pubg.allCanUse[pubg.allCanUse_count] = gunName -- All available firearms

				if pubg.bulletType == "" then pubg.bulletType = type end -- Default Bullet type

			end

		end

	end

	-- Initial setting of random number seeds
	pubg.SetRandomseed()
	pubg.outputLogRender()
	-- console.log(pubg)

end

-- SetRandomseed
function pubg.SetRandomseed ()
	math.randomseed(GetRunningTime())
end

--[[ Before automatic press gun ]]
function pubg.auto (options)

	-- Accurate aiming press gun
	pubg.currentTime = GetRunningTime()
	pubg.bulletIndex = math.ceil(((pubg.currentTime - pubg.startTime == 0 and {1} or {pubg.currentTime - pubg.startTime})[1]) / options.interval) + 1

	if pubg.bulletIndex > options.amount then return false end
	-- Developer Debugging Mode
	local d = (IsKeyLockOn("scrolllock") and { (pubg.bulletIndex - 1) * pubg.xLengthForDebug } or { 0 })[1]
	local x = math.ceil((pubg.currentTime - pubg.startTime) / (options.interval * (pubg.bulletIndex - 1)) * d) - pubg.xCounter
	local y = math.ceil((pubg.currentTime - pubg.startTime) / (options.interval * (pubg.bulletIndex - 1)) * options.ballistic[pubg.bulletIndex]) - pubg.counter
	-- 4-fold pressure gun mode
	local realY = pubg.getRealY(options, y)
	MoveMouseRelative(x, realY)
	-- Whether to issue automatically or not
	if options.autoContinuousFiring == 1 then
		while IsMouseButtonPressed(1) do
		   --repeat
		   PressMouseButton(1)
		   Sleep(140)
		   ReleaseMouseButton(1)
		   MoveMouseRelative(0, 38)
			if not IsMouseButtonPressed(1)then
			  break
		    end
		end
	end

	-- Real-time operation parameters
	pubg.autoLog(options, y, realY)
	pubg.outputLogRender()

	pubg.xCounter = pubg.xCounter + x
	pubg.counter = pubg.counter + y

	pubg.autoSleep(IsKeyLockOn("scrolllock"))

end

--[[ Sleep of pubg.auto ]]
function pubg.autoSleep (isTest)
	local random = 0
	if isTest then
		-- When debugging mode is turned on, Turn off random delays in preventive testing
		random = math.random(pubg.sleep, pubg.sleep)
	else
		random = math.random(pubg.sleepRandom[1], pubg.sleepRandom[2])
	end
	-- Sleep(10)
	Sleep(random)
end

--[[ get real y position ]]
function pubg.getRealY (options, y)
	local realY = y

	if pubg.isAimingState("Aim") and pubg.scope_current == "scopeX1" then
		realY = y * userInfo.sensitivity.Aim * pubg.generalSensitivityRatio
	else
		realY = y * pubg[pubg.scope_current]
		if pubg.scope_current == "scopeX2" and options.scopeX2Ratio then
			realY = realY * options.scopeX2Ratio
		elseif pubg.scope_current == "scopeX3" and options.scopeX3Ratio then
			realY = realY * options.scopeX3Ratio
		end
	end
-- 下蹲压枪
	if userInfo.aimingSettings == "ctrlmode" and IsModifierPressed("lctrl") then
		realY = realY * options.ctrlmodeRatio
	end
-- 屏息压枪
	if userInfo.aimingSettings == "ctrlmode" and IsModifierPressed("lshift") then
		realY = realY * options.BreathRatio
	end
-- 配件压枪系数 (枪口 × 握把 × 枪托)
	if userInfo.aimingSettings == "ctrlmode" then
		local muzzleRatio = attachmentConfig.muzzle[pubg.muzzleIndex].ratio
		local gripRatio = attachmentConfig.grip[pubg.gripIndex].ratio
		local stockRatio = 1.0
		local currentGun = pubg.getCurrentGunName()
		if not gunNoStock[currentGun] then
			stockRatio = attachmentConfig.stock[pubg.stockIndex].ratio
		end
		realY = realY * muzzleRatio * gripRatio * stockRatio
	end
-- 趴姿压枪
	if userInfo.aimingSettings == "ctrlmode" and IsModifierPressed("lalt") then
		realY = realY * options.PaziRatio
	end

	return math.round(realY)
end

--[[ change pubg isStart status ]]
function pubg.changeIsStart (isTrue)
	pubg.isStart = isTrue
	if isTrue then
		SetBacklightColor(0, 255, 150, "kb")
		SetBacklightColor(0, 255, 150, "mouse")
	else
		SetBacklightColor(255, 0, 90, "kb")
		SetBacklightColor(255, 0, 90, "mouse")
	end
end

--[[ set bullet type ]]
function pubg.setBulletType (bulletType)
	pubg.bulletType = bulletType
	pubg.gunIndex = 1
	pubg.allCanUse_index = 0

	local forList = { "9mm", "5.56", "7.62" }

	for i = 1, #forList do
		local type = forList[i]
		if type ==  bulletType then
			pubg.allCanUse_index = pubg.allCanUse_index + 1
			break
		else
			pubg.allCanUse_index = pubg.allCanUse_index + #pubg.gun[type]
		end
	end

	pubg.changeIsStart(true)
end

--[[ 获取当前枪械名称 ]]
function pubg.getCurrentGunName ()
	if pubg.bulletType ~= "" and pubg.gun[pubg.bulletType] and pubg.gun[pubg.bulletType][pubg.gunIndex] then
		return pubg.gun[pubg.bulletType][pubg.gunIndex]
	end
	return ""
end

--[[ 切换配件 ]]
function pubg.setAttachment (category, index)
	if pubg.stateLocked then
		OutputLogMessage("========================================\n")
		OutputLogMessage("【锁定拦截】配件切换被阻止！当前状态已锁定\n")
		OutputLogMessage("  提示: 按下 右Ctrl+G4 解锁后可切换\n")
		OutputLogMessage("========================================\n")
		return
	end

	-- 无枪托的枪禁止切换枪托
	if category == "stock" then
		local currentGun = pubg.getCurrentGunName()
		if gunNoStock[currentGun] then
			OutputLogMessage("========================================\n")
			OutputLogMessage("【配件限制】%s 不支持枪托配件\n", currentGun)
			OutputLogMessage("========================================\n")
			return
		end
	end

	local config = attachmentConfig[category]
	if not config or index < 1 or index > #config then return end

	if category == "muzzle" then
		pubg.muzzleIndex = index
	elseif category == "grip" then
		pubg.gripIndex = index
	elseif category == "stock" then
		pubg.stockIndex = index
	end

	pubg.printAttachmentLog()
end

function pubg.cycleAttachment (category)
	if pubg.stateLocked then
		OutputLogMessage("========================================\n")
		OutputLogMessage("【锁定拦截】配件切换被阻止！当前状态已锁定\n")
		OutputLogMessage("  提示: 按下 右Ctrl+G4 解锁后可切换\n")
		OutputLogMessage("========================================\n")
		return
	end

	-- 无枪托的枪禁止循环枪托
	if category == "stock" then
		local currentGun = pubg.getCurrentGunName()
		if gunNoStock[currentGun] then
			OutputLogMessage("========================================\n")
			OutputLogMessage("【配件限制】%s 不支持枪托配件\n", currentGun)
			OutputLogMessage("========================================\n")
			return
		end
	end

	local config = attachmentConfig[category]
	if not config then return end

	local currentIndex = 1
	if category == "muzzle" then
		currentIndex = pubg.muzzleIndex
	elseif category == "grip" then
		currentIndex = pubg.gripIndex
	elseif category == "stock" then
		currentIndex = pubg.stockIndex
	end

	local nextIndex = (currentIndex % #config) + 1
	pubg.setAttachment(category, nextIndex)
end

--[[ 打印配件切换日志 ]]
function pubg.printAttachmentLog ()
	local muzzle = attachmentConfig.muzzle[pubg.muzzleIndex]
	local grip = attachmentConfig.grip[pubg.gripIndex]
	local stock = attachmentConfig.stock[pubg.stockIndex]
	local currentGun = pubg.getCurrentGunName()
	local hasStock = not gunNoStock[currentGun]
	local totalRatio = muzzle.ratio * grip.ratio
	if hasStock then
		totalRatio = totalRatio * stock.ratio
	end

	OutputLogMessage("========================================\n")
	OutputLogMessage("【配件切换】当前枪械: %s\n", currentGun)
	OutputLogMessage("  枪口: %s (%.2f)\n", muzzle.label, muzzle.ratio)
	OutputLogMessage("  握把: %s (%.2f)\n", grip.label, grip.ratio)
	if hasStock then
		OutputLogMessage("  枪托: %s (%.2f)\n", stock.label, stock.ratio)
	else
		OutputLogMessage("  枪托: 不支持\n")
	end
	OutputLogMessage("  综合系数: %.2f\n", totalRatio)
	OutputLogMessage("========================================\n")
end

function pubg.setMuzzle (cmd)
	local index = tonumber(string.match(cmd, "muzzle_(%d+)"))
	if index then pubg.setAttachment("muzzle", index) end
end

function pubg.setGrip (cmd)
	local index = tonumber(string.match(cmd, "grip_(%d+)"))
	if index then pubg.setAttachment("grip", index) end
end

function pubg.setStock (cmd)
	local index = tonumber(string.match(cmd, "stock_(%d+)"))
	if index then pubg.setAttachment("stock", index) end
end

function pubg.cycleMuzzle ()
	pubg.cycleAttachment("muzzle")
end

function pubg.cycleGrip ()
	pubg.cycleAttachment("grip")
end

function pubg.cycleStock ()
	pubg.cycleAttachment("stock")
end

--[[ set current scope ]]
function pubg.setScope (scope)
	if pubg.stateLocked then
		local gunName = "未选择"
		if pubg.bulletType ~= "" and pubg.gun[pubg.bulletType] and pubg.gun[pubg.bulletType][pubg.gunIndex] then
			gunName = pubg.gun[pubg.bulletType][pubg.gunIndex]
		end
		OutputLogMessage("========================================\n")
		OutputLogMessage("【锁定拦截】倍镜切换被阻止！当前状态已锁定\n")
		OutputLogMessage("  当前枪械: %s\n", gunName)
		OutputLogMessage("  当前倍镜: %s\n", pubg.scope_current)
		OutputLogMessage("  尝试切换到: %s\n", scope)
		OutputLogMessage("  提示: 按下 右Ctrl+G4 解锁后可切换\n")
		OutputLogMessage("========================================\n")
		return
	end
	OutputLogMessage("[DEBUG] setScope: %s -> %s\n", tostring(pubg.scope_current), tostring(scope))
	pubg.scope_current = scope
end

--[[ 循环切换倍镜状态 ]]
function pubg.toggleScope (targetScope)
	OutputLogMessage("[DEBUG] toggleScope called with target: %s, current scope: %s\n", targetScope, tostring(pubg.scope_current))

	-- 判断当前是否在目标倍镜状态，如果是则切换回基础倍镜
	if pubg.scope_current == targetScope then
		OutputLogMessage("[DEBUG] Current scope matches target, switching to scopeX1\n")
		pubg.scope_current = "scopeX1"
	else
		OutputLogMessage("[DEBUG] Current scope does not match target, switching to %s\n", targetScope)
		pubg.scope_current = targetScope
	end

	OutputLogMessage("[DEBUG] Scope changed to: %s\n", tostring(pubg.scope_current))

	-- 打印切换日志
	pubg.printScopeChangeLog()
end

--[[ 切换二倍镜 ]]
function pubg.toggleScopeX2 ()
	pubg.toggleScope("scopeX2")
end

--[[ 切换三倍镜 ]]
function pubg.toggleScopeX3 ()
	pubg.toggleScope("scopeX3")
end

--[[ 打印倍镜切换日志 ]]
function pubg.printScopeChangeLog ()
	local gunName = "未选择"
	if pubg.bulletType ~= "" and pubg.gun[pubg.bulletType] and pubg.gun[pubg.bulletType][pubg.gunIndex] then
		gunName = pubg.gun[pubg.bulletType][pubg.gunIndex]
	end

	local scopeNameMap = {
		["scopeX1"] = "基础倍镜(红点/全息/侧瞄)",
		["scopeX2"] = "二倍镜",
		["scopeX3"] = "三倍镜",
		["scopeX4"] = "四倍镜",
		["scopeX6"] = "六倍镜"
	}

	local scopeName = scopeNameMap[pubg.scope_current] or pubg.scope_current

	OutputLogMessage("========================================\n")
	OutputLogMessage("【倍镜切换】当前枪械: %s | 当前倍镜: %s\n", gunName, scopeName)
	OutputLogMessage("========================================\n")
end

--[[ 切换枪械倍镜锁定状态 ]]
function pubg.toggleLockState ()
	pubg.stateLocked = not pubg.stateLocked

	local gunName = "未选择"
	if pubg.bulletType ~= "" and pubg.gun[pubg.bulletType] and pubg.gun[pubg.bulletType][pubg.gunIndex] then
		gunName = pubg.gun[pubg.bulletType][pubg.gunIndex]
	end

	local scopeNameMap = {
		["scopeX1"] = "基础倍镜(红点/全息/侧瞄)",
		["scopeX2"] = "二倍镜",
		["scopeX3"] = "三倍镜",
		["scopeX4"] = "四倍镜",
		["scopeX6"] = "六倍镜"
	}
	local scopeName = scopeNameMap[pubg.scope_current] or pubg.scope_current

	OutputLogMessage("========================================\n")
	if pubg.stateLocked then
		OutputLogMessage("【状态锁定】枪械和倍镜已锁定！\n")
		OutputLogMessage("  锁定枪械: %s\n", gunName)
		OutputLogMessage("  锁定倍镜: %s (%s)\n", pubg.scope_current, scopeName)
		OutputLogMessage("  操作: 所有枪械/倍镜切换操作将被阻止\n")
		OutputLogMessage("  解锁: 再次按下 右Ctrl+G4 即可解锁\n")
	else
		OutputLogMessage("【状态解锁】枪械和倍镜已解锁！\n")
		OutputLogMessage("  当前枪械: %s\n", gunName)
		OutputLogMessage("  当前倍镜: %s (%s)\n", pubg.scope_current, scopeName)
		OutputLogMessage("  操作: 现在可以自由切换枪械和倍镜\n")
		OutputLogMessage("  锁定: 按下 右Ctrl+G4 可重新锁定\n")
	end
	OutputLogMessage("========================================\n")
end

--[[ 打印枪械切换完整日志 ]]
function pubg.printGunSwitchLog (gunName)
	local scopeNameMap = {
		["scopeX1"] = "基础倍镜(红点/全息/侧瞄)",
		["scopeX2"] = "二倍镜",
		["scopeX3"] = "三倍镜",
		["scopeX4"] = "四倍镜",
		["scopeX6"] = "六倍镜"
	}
	local scopeName = scopeNameMap[pubg.scope_current] or pubg.scope_current
	local muzzle = attachmentConfig.muzzle[pubg.muzzleIndex]
	local grip = attachmentConfig.grip[pubg.gripIndex]
	local stock = attachmentConfig.stock[pubg.stockIndex]
	local hasStock = not gunNoStock[gunName]
	local attachRatio = muzzle.ratio * grip.ratio
	if hasStock then
		attachRatio = attachRatio * stock.ratio
	end

	OutputLogMessage("========================================\n")
	OutputLogMessage("【枪械切换】%s\n", gunName)
	OutputLogMessage("  弹药: %s\n", pubg.bulletType)
	OutputLogMessage("  倍镜: %s (%s)\n", pubg.scope_current, scopeName)
	OutputLogMessage("  枪口: %s (%.2f)\n", muzzle.label, muzzle.ratio)
	OutputLogMessage("  握把: %s (%.2f)\n", grip.label, grip.ratio)
	if hasStock then
		OutputLogMessage("  枪托: %s (%.2f)\n", stock.label, stock.ratio)
	else
		OutputLogMessage("  枪托: 不支持\n")
	end
	OutputLogMessage("  配件综合系数: %.2f\n", attachRatio)
	OutputLogMessage("========================================\n")
end

--[[ set current gun ]]
function pubg.setGun (gunName)
	if pubg.stateLocked then
		local currentGun = "未选择"
		if pubg.bulletType ~= "" and pubg.gun[pubg.bulletType] and pubg.gun[pubg.bulletType][pubg.gunIndex] then
			currentGun = pubg.gun[pubg.bulletType][pubg.gunIndex]
		end
		OutputLogMessage("========================================\n")
		OutputLogMessage("【锁定拦截】枪械切换被阻止！当前状态已锁定\n")
		OutputLogMessage("  当前枪械: %s\n", currentGun)
		OutputLogMessage("  当前倍镜: %s\n", pubg.scope_current)
		OutputLogMessage("  尝试切换到: %s\n", gunName)
		OutputLogMessage("  提示: 按下 右Ctrl+G4 解锁后可切换\n")
		OutputLogMessage("========================================\n")
		return
	end

	local forList = { "9mm", "5.56", "7.62" }
	local allCanUse_index = 0

	for i = 1, #forList do

		local type = forList[i]
		local gunIndex = 0
		local selected = false

		for j = 1, #userInfo.canUse[type] do
			if userInfo.canUse[type][j][2] >= 1 then
				gunIndex = gunIndex + 1
				allCanUse_index = allCanUse_index + 1
				if userInfo.canUse[type][j][1] == gunName then
					pubg.bulletType = type
					pubg.gunIndex = gunIndex
					pubg.allCanUse_index = allCanUse_index
					selected = true
					break
				end
			end
		end

		if selected then break end

	end

	-- 无枪托的枪自动重置枪托为裸配
	if gunNoStock[gunName] then
		pubg.stockIndex = 1
	end

	pubg.changeIsStart(true)
	pubg.printGunSwitchLog(gunName)
end

--[[ Consider all available firearms as an entire list ]]
function pubg.findInCanUse (cmd)

	if "first_in_canUse" == cmd then
		pubg.allCanUse_index = 1
	elseif "next_in_canUse" == cmd then
		if pubg.allCanUse_index < #pubg.allCanUse then
			pubg.allCanUse_index = pubg.allCanUse_index + 1
		end
	elseif "last_in_canUse" == cmd then
		pubg.allCanUse_index = #pubg.allCanUse
	end

	pubg.setGun(pubg.allCanUse[pubg.allCanUse_index])
end

--[[ Switching guns in the same series ]]
function pubg.findInSeries (cmd)
	if "first" == cmd then
		pubg.gunIndex = 1
	elseif "next" == cmd then
		if pubg.gunIndex < #pubg.gun[pubg.bulletType] then
			pubg.gunIndex = pubg.gunIndex + 1
		end
	elseif "last" == cmd then
		pubg.gunIndex = #pubg.gun[pubg.bulletType]
	end

	pubg.setGun(pubg.gun[pubg.bulletType][pubg.gunIndex])
end

--[[ Script running status ]]
function pubg.runStatus ()
	if userInfo.startControl == "capslock" then
		return IsKeyLockOn("capslock")
	elseif userInfo.startControl == "numlock" then
		return IsKeyLockOn("numlock")
	end
end

--[[ 随机偏移 ]]
function pubg.randomOffset (val, offsetScopePx)
	local offsetScope = (offsetScopePx or 20) / 1080 * 65535

	return math.random(
		math.ceil(val - offsetScope),
		math.ceil(val + offsetScope)
	)
end

--[[ 一键舔包，仅拾取进背包的物品，无法拾取需穿戴的物品 ]]
function pubg.fastLickBox ()
	PressAndReleaseKey("tab")
	Sleep(50 + pubg.sleep)
	PressAndReleaseMouseButton(1)

	local lastItemCp = {
		300 / 2560 * 65535,
		1210 / 1440 * 65535
	}
	local itemHeight = 83 / 1440 * 65535

	-- 重复 3 次动作，强化拾取成功率
	for i = 1, 3 do
		for j = 1, 13 do
			MoveMouseTo(
				pubg.randomOffset(lastItemCp[1]),
				pubg.randomOffset(lastItemCp[2] - itemHeight * (j - 1))
			)
			PressMouseButton(1)
			MoveMouseTo(
				pubg.randomOffset(670 / 2560 * 65535, 50),
				pubg.randomOffset(710 / 1440 * 65535, 50)
			) -- 修改为背包的坐标
			ReleaseMouseButton(1)
			Sleep(10 + pubg.sleep)
		end
	end

	Sleep(200 + pubg.sleep)
	MoveMouseTo(
		pubg.randomOffset(lastItemCp[1]),
		pubg.randomOffset(lastItemCp[2])
	)
	PressAndReleaseKey("tab")
end



--[[ 一键拾取功能，支持所有分辨率 ]]
autoshootmin = 45  ---拾取最小延迟
autoshootmax = 60  ---拾取最大延迟
function pubg.fastPickup ()
	PressAndReleaseKey("tab")
	Sleep(math.random(16,28))
	PressAndReleaseMouseButton(1)

	local lastItemCp = {
		200 / 3560 * 65535,
		1210 / 1440 * 65535
	}
	local itemHeight = 46 / 1440 * 65535

	-- 重复 3 次动作，强化拾取成功率
	for i = 1, 1 do
		for j = 1, 13 do
			MoveMouseTo(
				pubg.randomOffset(lastItemCp[1]),
				pubg.randomOffset(lastItemCp[2] - itemHeight * (j + 9))
			)
			PressMouseButton(1)
			MoveMouseTo(
				pubg.randomOffset(32767, 100),
				pubg.randomOffset(32767, 100)
			)
			ReleaseMouseButton(1)
			Sleep(math.random(autoshootmin,autoshootmax))
		end
	end

	Sleep(math.random(autoshootmin,autoshootmax))
	MoveMouseTo(
		pubg.randomOffset(lastItemCp[1]),
		pubg.randomOffset(lastItemCp[2])
	)
	PressAndReleaseKey("tab")
end




--[[ 背包清空之术，就算战死，也要让敌人舔个空盒！ ]]
function pubg.fastDiscard ()
	PressAndReleaseKey("lshift")
	PressAndReleaseKey("lctrl")
	PressAndReleaseKey("lalt")
	PressAndReleaseKey("rshift")
	PressAndReleaseKey("rctrl")
	PressAndReleaseKey("ralt")
	PressAndReleaseKey("tab")
	Sleep(10 + pubg.sleep)
	PressAndReleaseMouseButton(1)
	local lastItemCp = {
		630 / 2560 * 65535,
		1210 / 1440 * 65535
	}
	local itemHeight = 83 / 1440 * 65535
	-- 清空背包 第一轮
	Sleep(10 + pubg.sleep)
	for i = 1, 5 do
		for j = 1, 13 do
			MoveMouseTo(
				pubg.randomOffset(lastItemCp[1]),
				pubg.randomOffset(lastItemCp[2] - itemHeight * (j - 1))
			)
			PressMouseButton(1)
			MoveMouseTo(0, 0)
			ReleaseMouseButton(1)
		end
	end
	-- 清空武器
	Sleep(10 + pubg.sleep)
	local itemPos = {
		{ 1770, 180 },
		{ 1770, 480 },
		{ 1770, 780 },
		{ 1770, 1050 },
		{ 2120, 1050 }
	}
	for i = 1, #itemPos do
		MoveMouseTo(
			pubg.randomOffset(itemPos[i][1] / 2560 * 65535),
			pubg.randomOffset(itemPos[i][2] / 1440 * 65535)
		)
		PressAndReleaseMouseButton(3)
	end
	-- 清空背包 第二轮
	Sleep(10 + pubg.sleep)
	for i = 1, 5 do
		for j = 1, 13 do
			MoveMouseTo(
				pubg.randomOffset(lastItemCp[1]),
				pubg.randomOffset(lastItemCp[2] - itemHeight * (j - 1))
			)
			PressMouseButton(1)
			MoveMouseTo(0, 0)
			ReleaseMouseButton(1)
		end
	end
	-- 清空装备
	Sleep(10 + pubg.sleep)
	local itemPos2 = {
		{ 900, 392 },
		{ 900, 630 },
		{ 900, 720 },
		{ 900, 808 },
		{ 1605, 397 },
		{ 1605, 481 },
		{ 1605, 632 },
		{ 1605, 719 },
		{ 1605, 807 },
		{ 1605, 1049 },
		{ 1605, 1229 }
	}
	for i = 1, #itemPos2 do
		MoveMouseTo(
			pubg.randomOffset(itemPos2[i][1] / 2560 * 65535),
			pubg.randomOffset(itemPos2[i][2] / 1440 * 65535)
		)
		-- Sleep(300 + pubg.sleep)
		PressAndReleaseMouseButton(3)
	end
	Sleep(10 + pubg.sleep)
	MoveMouseTo(
		pubg.randomOffset(lastItemCp[1]),
		pubg.randomOffset(lastItemCp[2])
	)
	PressAndReleaseKey("tab")
end

--[[ autputLog render ]]
function pubg.outputLogRender ()
	if userInfo.debug == 0 then return false end
	if not pubg.G1 then
		pubg.renderDom.switchTable = pubg.outputLogGunSwitchTable()
	end
	local resStr = table.concat({
		"\n>> [\"", pubg.renderDom.combo_key, "\"] = \"", pubg.renderDom.cmd, "\" <<\n",
		pubg.renderDom.separator,
		pubg.renderDom.switchTable,
		pubg.renderDom.separator,
		pubg.outputLogGunInfo(),
		pubg.renderDom.separator,
		pubg.renderDom.autoLog,
		pubg.renderDom.separator,
	})
	ClearLog()
	OutputLogMessage(resStr)
end

--[[ Output switching table ]]
function pubg.outputLogGunSwitchTable ()
	local forList = { "9mm", "5.56", "7.62" }
	local allCount = 0
	local resStr = "      canUse_i\t      series_i\t      Series\t      ratio\t      ctrl ratio\t      Breath\t      Luopei\t      Sanbei\t      Pazi\t      Gun Name\n\n"

	for i = 1, #forList do
		local type = forList[i]
		local gunCount = 0

		for j = 1, #userInfo.canUse[type] do
			if userInfo.canUse[type][j][2] >= 1 then
				local gunName = userInfo.canUse[type][j][1]
				local tag = gunName == pubg.gun[pubg.bulletType][pubg.gunIndex] and "=> " or "      "
				gunCount = gunCount + 1
				allCount = allCount + 1
				resStr = table.concat({ resStr, tag, allCount, "\t", tag,gunCount, "\t",  tag, type, "\t", tag, userInfo.canUse[type][j][3], "\t", tag, userInfo.canUse[type][j][4], "\t", tag , userInfo.canUse[type][j][5], "\t", tag, userInfo.canUse[type][j][6], "\t", tag, userInfo.canUse[type][j][7], "\t", tag, userInfo.canUse[type][j][8], "\t", tag, gunName, "\n" })
			end
		end

	end

	return resStr
end

-- output Log Gun Info
function pubg.outputLogGunInfo ()
	local k = pubg.bulletType
	local i = pubg.gunIndex
	local gunName = pubg.gun[k][i]

	local scopeNameMap = {
		["scopeX1"] = "基础倍镜(红点/全息/侧瞄)",
		["scopeX2"] = "二倍镜",
		["scopeX3"] = "三倍镜",
		["scopeX4"] = "四倍镜",
		["scopeX6"] = "六倍镜"
	}
	local scopeName = scopeNameMap[pubg.scope_current] or pubg.scope_current
	local lockStatus = pubg.stateLocked and "LOCKED" or "UNLOCKED"
	local muzzle = attachmentConfig.muzzle[pubg.muzzleIndex]
	local grip = attachmentConfig.grip[pubg.gripIndex]
	local stock = attachmentConfig.stock[pubg.stockIndex]
	local hasStock = not gunNoStock[gunName]
	local attachRatio = muzzle.ratio * grip.ratio
	local stockText = "不支持"
	if hasStock then
		attachRatio = attachRatio * stock.ratio
		stockText = stock.label .. " " .. string.format("%.2f", stock.ratio)
	end

	return table.concat({
		"Lock state: [ " .. lockStatus .. " ] (RightCtrl+G4 to toggle)\n",
		"Currently scope: [ " .. pubg.scope_current .. " (" .. scopeName .. ") ]\n",
		"Currently series: [ ", k, " ]\n",
		"Currently index in series: [ ", i, " / ", #pubg.gun[k], " ]\n",
		"Currently index in canUse: [ ", pubg.allCanUse_index, " / ", pubg.allCanUse_count, " ]\n",
		"Attachment: muzzle[", muzzle.label, " ", string.format("%.2f", muzzle.ratio),
		 "] grip[", grip.label, " ", string.format("%.2f", grip.ratio),
		 "] stock[", stockText,
		 "] = ", string.format("%.2f", attachRatio), "\n",
		"Recoil table of [ ", gunName, " ]:\n",
		pubg.outputLogRecoilTable(),
	})
end

--[[ output recoil table log ]]
function pubg.outputLogRecoilTable ()
	local k = pubg.bulletType
	local i = pubg.gunIndex
	local resStr = "{ "
	for j = 1, #pubg.gunOptions[k][i].ballistic do
		local num = pubg.gunOptions[k][i].ballistic[j]
		resStr = table.concat({ resStr, num })
		if j ~= #pubg.gunOptions[k][i].ballistic then
			resStr = table.concat({ resStr, ", " })
		end
	end

	resStr = table.concat({ resStr, " }\n" })

	return resStr
end

--[[ log of pubg.auto ]]
function pubg.autoLog (options, y, realY)
	local scopeVal = pubg[pubg.scope_current] or 0
	local adsDetected = pubg.isAimingState("ADS")
	pubg.renderDom.autoLog = table.concat({
		"----------------------------------- Automatically counteracting gun recoil -----------------------------------\n",
		"------------------------------------------------------------------------------------------------------------------------------\n",
		"scope: ", pubg.scope_current, " (", scopeVal, ") | ADS: ", tostring(adsDetected), " | y: ", y, " | realY: ", realY, "\n",
		"bullet index: ", pubg.bulletIndex, "    target counter: ", options.ballistic[pubg.bulletIndex], "    current counter: ", pubg.counter, "\n",
		"D-value(target - current): ", options.ballistic[pubg.bulletIndex], " - ", pubg.counter, " = ", options.ballistic[pubg.bulletIndex] - pubg.counter, "\n",
		"move: math.ceil((", pubg.currentTime, " - ", pubg.startTime, ") / (", options.interval, " * (", pubg.bulletIndex, " - 1)) * ", options.ballistic[pubg.bulletIndex], ") - ", pubg.counter, " = ", y, "\n",
		"------------------------------------------------------------------------------------------------------------------------------\n",
	})
end

function pubg.PressOrRelaseAimKey (toggle)
	if userInfo.autoPressAimKey ~= "" then
		if toggle then
			PressKey(userInfo.autoPressAimKey)
		else
			ReleaseKey(userInfo.autoPressAimKey)
		end
	end
end

--[[ Automatic press gun ]]
function pubg.OnEvent_NoRecoil (event, arg, family)
	if event == "MOUSE_BUTTON_PRESSED" and arg == 1 and family == "mouse" then
		if not pubg.runStatus() then return false end
		if userInfo.aimingSettings ~= "default" and not IsMouseButtonPressed(3) then
			pubg.PressOrRelaseAimKey(true)
		end
		pubg.startTime = GetRunningTime()
		pubg.G1 = true
        OutputLogMessage("Start Shooting....\n")
        pubg.shooting()
	end

	if event == "MOUSE_BUTTON_RELEASED" and arg == 1 and family == "mouse" then
		pubg.PressOrRelaseAimKey(false)
		pubg.G1 = false
		pubg.counter = 0 -- Initialization counter
		pubg.xCounter = 0 -- Initialization xCounter
		pubg.SetRandomseed() -- Reset random number seeds
	end

end

function pubg.shooting()
    repeat
        pubg.auto(pubg.gunOptions[pubg.bulletType][pubg.gunIndex])
    until not IsMouseButtonPressed(1)
    OutputLogMessage("Stop Shooting....\n")
end

--[[ 关闭压枪功能 ]]
function pubg.turnOffRecoil()
	if pubg.isStart then
		pubg.changeIsStart(false)
		OutputLogMessage("压枪已关闭\n")
	end
end

--[[ Listener method ]]

-- 通用 Lua 文件加载函数（绕过 GHub dofile 运行时缓存）
-- GHub 的 dofile 在脚本启动时内联文件内容，运行时调用不会重新读磁盘
-- 改用 io.open + loadstring 每次都从磁盘读取最新内容
function loadLuaFile(path)
    if io and io.open then
        local f = io.open(path, 'r')
        if f then
            local content = f:read('*a')
            f:close()
            local chunk, lerr = loadstring(content)
            if chunk then
                return pcall(chunk)
            else
                return false, 'loadstring 失败: ' .. tostring(lerr)
            end
        else
            return false, 'io.open 失败: ' .. path
        end
    else
        if package and package.loaded then package.loaded[path] = nil end
        return pcall(function() dofile(path) end)
    end
end

-- dofile 加载函数
function loadConfig()
    local ok, err = loadLuaFile(CONFIG_PATH)
    if ok then
        _configLoaded = true
        pubg.sleep = userInfo.cpuLoad
        pubg.sleepRandom = { userInfo.cpuLoad, userInfo.cpuLoad + 3 }
        pubg.scopeX2 = userInfo.sensitivity.scopeX2
        pubg.scopeX3 = userInfo.sensitivity.scopeX3
        pubg.scopeX4 = userInfo.sensitivity.scopeX4
        pubg.scopeX6 = userInfo.sensitivity.scopeX6
        pubg.generalSensitivityRatio = userInfo.sensitivity.ADS / 100
        pubg.init()
        OutputLogMessage("[CONFIG] 配置已加载\n")
    else
        OutputLogMessage("[CONFIG] 加载失败: %s\n", tostring(err))
    end
    return ok
end

function loadRecResult()
    local before = tostring(rec_gun)
    local ok, err = loadLuaFile(REC_PATH)
    if ok then
        OutputLogMessage("[AUTO] 读取识别结果: %s -> %s (muzzle=%d grip=%d stock=%d scope=%d)\n", before, tostring(rec_gun), rec_muzzle, rec_grip, rec_stock, rec_scope)
    else
        OutputLogMessage("[AUTO] 读取识别结果失败: %s\n", tostring(err))
    end
    return ok
end

function applyRecResult()
    if pubg.stateLocked then
        OutputLogMessage("[AUTO] 状态已锁定，跳过应用\n")
        return
    end
    OutputLogMessage("[AUTO] 应用识别结果: 当前=%s 目标=%s\n", tostring(pubg.getCurrentGunName()), tostring(rec_gun))
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
    local capsOn = IsKeyLockOn("capslock")
    if capsOn and not _capsWasOn then
        OutputLogMessage("[AUTO] CapsLock 上升沿: 加载配置+识别结果\n")
        loadConfig()
        if AUTO_RECOGNIZE then
            if loadRecResult() then
                applyRecResult()
            end
        end
    end
    _capsWasOn = capsOn

    if AUTO_RECOGNIZE and event == "MOUSE_BUTTON_PRESSED" and arg == 1 and family == "mouse" then
        if capsOn and _configLoaded then
            if loadRecResult() then
                applyRecResult()
            end
        end
    end

    if _configLoaded then
        pubg.OnEvent_NoRecoil(event, arg, family)
    end
end

-- 工具函数
function math.round(num, digit)
    local d = 10 ^ (digit or 0)
    return math.floor((num * d * 10 + 5) / 10) / d
end

function string.split(str, s)
    if string.find(str, s) == nil then return { str } end
    local res = {}
    local reg = "(.-)" .. s .. "()"
    local index = 0
    local last_i
    for n, i in string.gmatch(str, reg) do
        index = index + 1
        res[index] = n
        last_i = i
    end
    res[index + 1] = string.sub(str, last_i)
    return res
end