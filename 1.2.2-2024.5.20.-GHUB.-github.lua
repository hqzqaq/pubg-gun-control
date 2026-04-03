--T8numen编辑修改，专为新人打造的船新萌新专用宏1.2.1，附带了较完整的文字说明。后续看情况修改补充为2.0
--使用提醒：此为ghub宏，亲测2024.3.553733版本可用。不一定非要版本一致，能用就行。
--二改自好人的宏，宏的源为github的Soldier76项目，免费且开源
--G4是1倍/红点/全息，G5是3倍，满配垂直+枪口补偿可以最稳，突击步枪通用，762和M4，ACE32都没问题
--interval是射击间隔.3倍762需要下蹲。不建议用三倍，因为各个枪都不一样，建议用G4的红点好压一点。远了建议直接打狙，这不是和平精英，没必要步枪压三倍.
--灵敏度一般不用管，真要改就改垂直灵敏度，但是前提是你还没开始调下面的参数或者说系数
--1.2版本G4为M762专用键，红点+垂直+站
--
-- ★★★ alt+数字键 切换枪械说明 ★★★
-- 需要在GHUB中将数字键1-8绑定为G键(G13-G20)，然后在按下alt+数字键时即可切换枪械
-- alt+1: ACE32    alt+2: M416    alt+3: AUG    alt+4: SCAR-L
-- alt+5: Beryl M762    alt+6: QBZ    alt+7: G36C    alt+8: UMP45
-- GHUB设置方法：打开GHUB -> 选择键盘 -> 点击"+"添加命令 -> 选择"脚本" -> 将数字键分配给G13-G20


--→→↓↓↓↓↓↓↓↓↓←←
--→→新手先看这里，再看上面←←
--新手教程：打开大写/按下键盘左边的CAPS键后，长按右键不松开，再按下左键就会开始压了。
--必看：下面的canuse里，倒数第二列 为满配系数，要改的自己调整，压高了就调高，压低了就调低
--必看：比如你要用的是G4的配置，比如我这里是["G4"] = "M762",意思就是我的G4键绑的是M762的配置，你就改canuse里M416的满配系数，满配之后再改，满配一般都是垂直握把+枪口补偿器，一般canuse的枪械系数后面会有会有说明，说这把枪的这个配置满配是啥情况
--必看：每次更改后记得左上角保存并应用
--必看：别问我为啥满配了还要改裸配系数，问  问我也不知道，反正改就对了。改的时候建议把ghub全屏，也就是扩大应用窗口，最好左右宽度拉满铺满，上下看自己习惯
--左右铺开是为了方便修改，因为一般文字说明和对应的数字有偏移，当然全铺开了也有


--此宏来自github开源76宏二改，倒卖死妈-二改后删改并用来引流卖东西的死妈
--我76宏历史悠久，群里一直有人更新弹道，确保每次更新后都能用。有的死妈盗用者把别人的宏改成自己的，然后卖自己的司马AI瞄准软件，甚至一个付费20的宏还不如别人精简76宏后拿来引流卖东西的免费宏
--二改者（也就是我）为bilibili用户-17995599
--我的github链接-
--https://github.com/T8numen/GHUB-PUBG-76-Suitable-for-beginners/releases/tag/GHUB-lua

--以下为原作者的开源链接，作者为76（全称太长就简称76了）
--https://github.com/kiccer/Soldier76

--调整记录：
--1-2024.5.调整了M762的弹道，特别调整了后15发，虽然不确定是否有用。添加ctrl+G4为ACE32,并添加游戏灵敏度备注（常规50垂直1.4瞄准40开镜45-2倍40-3倍30-4 6 8 15倍都是50，鼠标灵敏度为1400DPI，屏幕分辨率为1080，理论上分辨率灵敏度一样的前提下可以达到和我同样的压枪效果）
--2-2024.5.新增了lalt+G5为AUG。注释：lalt为左alt，ralt为右alt。小科普：l和r分别是英语left和right首字母
--3-2024.5.修改第二行文字错误应为第二列，感谢群友[G502]PUBG/醉酒当歌提醒。
userInfo = {
	debug = 1,
	cpuLoad = 2,
	sensitivity = {
		ADS = 70,-- 开镜 | sighting mirror
		Aim = 0.55,-- 腰射 | take aim
		scopeX2 = 1.4,-- 二倍 | twice scope
		scopeX3 = 3.6,-- 三倍 | trebling scope
		scopeX4 = 3.0,-- 四倍 | quadruple scope
		scopeX6 = 1.25,-- 六倍 | sixfold scope
	},
	autoPressAimKey = "",
	startControl = "capslock",	-- 启动控制 (capslock  | numlock   | G_bind )
	aimingSettings = "ctrlmode",
	customAimingSettings = {
		-- 开镜判断
		ADS = function ()
			return false -- 判断条件，返回值为布尔型2121
		end,
		Aim = function ()
			return false -- 判断条件，返回值为布尔型
		end,
	},

	-- 支持的枪械，排列顺序即是配置顺序，可以自行调整。模式：0 - 不启用 | 1 - 启用 | 2 - 开启连点	系数：枪械自身系数，基于 ADS 进行调整 (ADS为全局系数，此处为自身系数)	下蹲系数：下蹲时的系数，基于 ADS 和 自身系数
	canUse = {
		["7.62"] = {
			-- 枪械             模式         系数        下蹲系数		屏息系数	        裸配系数	      满配系数	      趴姿系数
			{ "Beryl M762",     1,          4.30, 		0.82,		1.38,		1.25,		0.83,		0.60}, 
			{ "AKM",            1,          1.95,		0.74,		1.38,		1.25,		2.12,		0.50}, 
			{ "Groza",          1,          1.60,		0.70,		1.38,		1.25,		2.10,		0.50},
			{ "ACE32",          1,          3.50,		0.70,		1.38,		0.30,		1.1,		0.00}, 
			{ "DP-28",          0,          1.00,		0.80,		1.38,		1.25,		2.60,		0.50}, 
			{ "MK47",           2,          1.00,		0.80,		1.38,		1.25,		2.60,		0.50},
		},
		["5.56"] = {
			-- 枪械             模式         系数		下蹲系数	      屏息系数	        ----          满配系数   	三倍系数
			{ "AUG",            1,          1.85,		0.80,		1.38,		2.50,		1.90,		0.50}, 
			{ "M416",	    1,          4.40,		0.85,		1.38,		1.50, 		0.91,		0.50}, 
			{ "P90",            1,          1.80,		0.85,		1.38,		1.25,		2.60,		0.50}, 
			{ "M249",           1,          1.50,		0.80,		1.38,		1.25,		2.60,		0.50},	
			{ "M16A4",          2,          1.50,		0.80,		1.38,		1.25,		3.20,		0.50}, 
			{ "SCAR-L",         1,          1.20,		0.88,		1.38,		1.25,		2.70,		0.50}, 
			{ "QBZ",            1,          1.00,		0.80,		1.38,		1.25,		2.60,		0.50}, 
			{ "G36C",           1,          1.00,		0.80,		1.38,		1.25,		2.60,		0.50}, 
		},
		[".45"] = {
			-- 枪械             模式         系数		XD系数	      XP系数	      LP系数 	       三倍系数
			{ "Tommy Gun",      0,          1.00,		0.80,		1.38,		1.25,		2.60,		0.50}, 
		},
		["9mm"] = {
			-- 枪械             模式         系数		XD系数	      XP系数	      LP系数	三倍系数
			{ "Vector",         0,          1.00,		0.80,		1.38,		1.25,		2.60,		0.50}, 
			{ "Micro UZI",      0,          1.00,		0.80,		1.38,		1.25,		2.60,		0.50}, 
			{ "UMP45",          1,          0.90,		0.80,		1.38,		1.25,		2.60,		0.50},
			{ "MP5K",           1,          0.75,		0.80,		1.38,		1.25,		2.60,		0.50},  
		},


	},

	-- G键自定义绑定，多余的组合键可以删除
	-- 可绑定指令请参考: 
	-- 指令绑定演示参考: https://github.com/kiccer/Soldier76#g_bind-%E6%8C%87%E4%BB%A4%E7%BB%91%E5%AE%9A%E6%BC%94%E7%A4%BA
	G_bind = {
		-- G
		["G3"] = "",
		["G4"] = "",
		["G5"] = "",
		["G6"] = "",
		["G7"] = "",
		["G8"] = "",
		["G9"] = "",
		["G10"] = "",
		["G11"] = "",
		-- lalt + G
		["lalt + G3"] = "",
		["lalt + G4"] = "UMP45",
		["lalt + G5"] = "MP5K",
		["lalt + G6"] = "",
		["lalt + G7"] = "",
		["lalt + G8"] = "",
		["lalt + G9"] = "",
		["lalt + G10"] = "",
		["lalt + G11"] = "",
		-- lctrl + G
		["lctrl + G3"] = "",
		["lctrl + G4"] = "ACE32",
		["lctrl + G5"] = "M416",
		["lctrl + G6"] = "",
		["lctrl + G7"] = "",
		["lctrl + G8"] = "",
		["lctrl + G9"] = "",
		["lctrl + G10"] = "",
		["lctrl + G11"] = "",
		-- lshift + G
		["lshift + G3"] = "",
		["lshift + G4"] = "AUG",
		["lshift + G5"] = "SCAR-L",
		["lshift + G6"] = "",
		["lshift + G7"] = "",
		["lshift + G8"] = "",
		["lshift + G9"] = "",
		["lshift + G10"] = "",
		["lshift + G11"] = "",
		-- ralt + G
		["ralt + G3"] = "",
		["ralt + G4"] = "",
		["ralt + G5"] = "",
		["ralt + G6"] = "",
		["ralt + G7"] = "",
		["ralt + G8"] = "",
		["ralt + G9"] = "",
		["ralt + G10"] = "",
		["ralt + G11"] = "",
		-- rctrl + G
		["rctrl + G3"] = "",
		["rctrl + G4"] = "",
		["rctrl + G5"] = "",
		["rctrl + G6"] = "",
		["rctrl + G7"] = "",
		["rctrl + G8"] = "",
		["rctrl + G9"] = "",
		["rctrl + G10"] = "",
		["rctrl + G11"] = "",
		-- rshift + G
		["rshift + G3"] = "",
		["rshift + G4"] = "",
		["rshift + G5"] = "",
		["rshift + G6"] = "",
		["rshift + G7"] = "",
		["rshift + G8"] = "",
		["rshift + G9"] = "",
		["rshift + G10"] = "",
		["rshift + G11"] = "",
		-- 非鼠标G键，可以使键盘或者耳机上的G键，默认使用键盘G键，请确保你使用的是可编程的罗技键盘 | F1~12 (Non-mouse G-key)
		["F1"] = "Beryl M762|scopeX1",
		["F2"] = "ACE32|scopeX1",
		["F3"] = "M416|scopeX1",
		["F4"] = "AUG|scopeX1",
		["F5"] = "AKM|scopeX1",
		["F6"] = "Groza|scopeX1",
		["F7"] = "M249|scopeX1",
		["F8"] = "P90|scopeX1",
		["F9"] = "",
		["F10"] = "",
		["F11"] = "",
		["F12"] = "",
		-- lalt + 数字键 (alt + 1~8)
		["lalt + 1"] = "ACE32",
		["lalt + 2"] = "M416",
		["lalt + 3"] = "AUG",
		["lalt + 4"] = "SCAR-L",
		["lalt + 5"] = "Beryl M762",
		["lalt + 6"] = "QBZ",
		["lalt + 7"] = "G36C",
		["lalt + 8"] = "UMP45",
	},
}
----------------------------- [[ 以下是脚本核心代码，非专业人士请勿改动 ]] -----------------------------
----------------------------- [[ 以下是脚本核心代码，非专业人士请勿改动 ]] -----------------------------
----------------------------- [[ 以下是脚本核心代码，非专业人士请勿改动 ]] -----------------------------
-- internal configuration
pubg = {
	gun = {
		[".45"] = {},
		["9mm"] = {},
		["5.56"] = {},
		["7.62"] = {},
	}, -- 枪械库
	gunOptions = {
		[".45"] = {},
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
	G1 = false, -- G1键状态
	currentTime = 0, -- 此刻
	bulletIndex = 0, -- 第几颗子弹
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
				return IsMouseButtonPressed(3) and not IsModifierPressed("lshift")
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


pubg["MG3"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 60,
		ballistic = {
			{1, 0},
			{2, 42},
			{3, 12},
			{6, 15},
			{8, 23},
			{10, 25},
			{16, 23},
			{25, 12},
			{75, 12},
		}
	})

end

pubg["MK47"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 10,
		ballistic = {
			{1, 0},	
			{2, 68},
			{3, 66},
			{4, 72},
			{5, 75},
			{6, 77},
			{7, 79},
			{8, 80},
			{9, 82},
			{10, 82},
			{11, 82},
			{12, 83},
			{13, 83},
			{14, 82},
			{15, 82},
		}
	})

end

pubg["Beryl M762"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 87,
		ballistic = {
{1, 0},
{2, 38},
{3, 20},
{4, 24},
{5, 25},
{6, 26},
{7, 28},
{8, 27},
{9, 29},
{10, 31},
{11, 33},
{12, 35},
{13, 36},
{14, 36},
{15, 37},
{16, 38},
{17, 39},
{18, 40},
{19, 41},
{20, 40},
{21, 41},
{22, 41},
{23, 40},
{24, 40},
{25, 39},
{26, 38},
{27, 40},
{28, 39},
{29, 38},
{30, 39},
{31, 39},
{32, 39},
{33, 40},
{34, 39},
{35, 39},
{36, 40},
{37, 38},
{38, 40},
{39, 40},
{40, 39},
{42, 41},

		}
	})

end

pubg["Famas"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 65,
		ballistic = {
			{1, 0},
			{2, 33},
			{4, 20},
			{6, 23},
			{10, 30},
			{15, 43},
			{20, 46},
			{25, 48},
			{30, 44},
		}
	})

end

pubg["M16A4"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 280,
		ballistic = {
			{1, 0},	
			{2, 98},
			{3, 104},
			{4, 109},
			{5, 113},
			{6, 115},
			{7, 114},
			{8, 113},
			{9, 111},
			{10, 110},
			{14, 109},
		}
	})

end

pubg["SCAR-L"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 96,
		ballistic = {
			{1, 0},
			{2, 30},
			{5, 20},
			{10, 24},
			{15, 28},
			{42, 32},
		}
	})

end



pubg["P90"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 61,
		ballistic = {
			{1, 0},
			{2, 8},
			{5, 11},
			{10, 14},
			{15, 17},
			{18, 20},
			{21, 10},
			{22, 7},
			{23, 8},
			{30, 9},
			{35, 10},
			{40, 10},
			{50, 11},
		}
	})
end

pubg["M249"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 222,
		ballistic = {
			{1, 0},
			{2, 40},
			{5, 50},
			{10, 45},
			{15, 55},
			{20, 70},
			{75, 76},
		}
	})

end

pubg["Tommy Gun"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 84,
		ballistic = {
			{1, 0},
			{3, 20},
			{6, 21},
			{8, 24},
			{10, 30},
			{15, 40},
			{50, 45},
		}
	})

end

pubg["G36C"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 86,
		ballistic = {
			{1, 0},
			{2, 40},
			{5, 16},
			{10, 26},
			{15, 30},
			{20, 34},
			{42, 36},
		}
	})

end

pubg["Vector"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 57,
		ballistic = {
			{1, 0},
			{3, 11},
			{6, 14},
			{10, 15},
			{12, 16},
			{15, 17},
			{20, 18},
			{25, 20},
			{30, 22},
			{33, 23},
		}
	})

end

pubg["Micro UZI"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 46,
		ballistic = {
			{1, 0},
			{2, 13},
			{10, 12},
			{15, 20},
			{35, 30},
		}
	})

end

pubg["UMP45"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 94,
		ballistic = {
			{1, 0},
			{5, 18},
			{15, 30},
			{35, 32},
		}
	})

end

pubg["MP5K"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 94,
		ballistic = {
			{1, 0},
			{5, 18},
			{15, 30},
			{35, 32},
		}
	})

end

pubg["Groza"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 80,
		ballistic = {
			{1, 0},
			{2, 26},
			{3, 22},
			{5, 24},
			{6, 25},
			{7, 26},
			{8, 28},
			{10, 29},
			{12, 31},
			{15, 34},
			{20, 35},
			{25, 39},
			{30, 41},
			{35, 42},
			{42, 43},
		}
	})

end

pubg["AKM"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 102,
		ballistic = {
{1, 0},
{2, 36},
{3, 19},
{4, 21},
{5, 23},
{6, 24},
{7, 25},
{8, 25},
{9, 26},
{10, 27},
{11, 27},
{12, 28},
{13, 28},
{14, 28},
{15, 28},
{16, 30},
{17, 31},
{18, 29},
{19, 30},
{20, 30},
{21, 28},
{22, 31},
{23, 28},
{24, 28},
{25, 29},
{26, 32},
{27, 30},
{28, 31},
{29, 34},
{30, 30},
{31, 31},
{32, 30},
{33, 31},
{34, 31},
{35, 30},
{36, 31},
{37, 32},
{38, 33},
{39, 31},
{40, 32},
{42, 32},
		}
	})

end

pubg["AUG"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 85,
		ballistic = {
{1, 0},
{2, 17},
{3, 12},
{4, 17},
{5, 21},
{6, 24},
{7, 26},
{8, 28},
{9, 28},
{10, 30},
{11, 31},
{12, 32},
{13, 32},
{14, 33},
{15, 35},
{16, 35},
{17, 36},
{18, 38},
{19, 37},
{20, 37},
{21, 38},
{22, 37},
{23, 38},
{24, 37},
{25, 36},
{26, 36},
{27, 37},
{28, 36},
{29, 35},
{30, 36},
{31, 38},
{32, 38},
{33, 38},
{34, 37},
{35, 37},
{36, 38},
{37, 38},
{38, 38},
{39, 36},
{40, 38},
{41, 38},
{42, 38},

		}
	})

end

pubg["M416"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 87,
		ballistic = {
{1, 0},
{2, 13},
{3, 13},
{4, 15},
{5, 16},
{6, 16},
{7, 23},
{8, 21},
{9, 21},
{10, 23},
{11, 23},
{12, 24},
{13, 23},
{14, 24},
{15, 25},
{16, 25},
{17, 25},
{18, 26},
{19, 25},
{20, 26},
{21, 24},
{22, 24},
{23, 27},
{24, 26},
{25, 28},
{26, 26},
{27, 22},
{28, 26},
{29, 25},
{30, 27},
{31, 28},
{32, 27},
{33, 27},
{34, 26},
{35, 26},
{36, 26},
{37, 27},
{38, 29},
{39, 29},
{40, 29},

		}
	})

end

pubg["QBZ"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 92,
		ballistic = {
			{1, 0},
			{2, 34},
			{5, 18},
			{10, 22},
			{15, 32},
			{20, 34},
			{42, 36},
		}
	})

end

pubg["DP-28"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 100,
		ballistic = {
			{1, 0},
			{2, 30},
			{5, 20},
			{47, 30},
		}
	})

end

pubg["ACE32"] = function (gunName)

	return pubg.execOptions(gunName, {
		interval = 90,
		ballistic = {
{1, 0},
{2, 17},
{3, 17},
{4, 23},
{5, 24},
{6, 20},
{7, 26},
{8, 22},
{9, 21},
{10, 24},
{11, 24},
{12, 23},
{13, 23},
{14, 24},
{15, 25},
{16, 27},
{17, 28},
{18, 29},
{19, 31},
{20, 30},
{21, 31},
{22, 29},
{23, 29},
{24, 30},
{25, 30},
{26, 31},
{27, 30},
{28, 30},
{29, 29},
{30, 30},
{31, 30},
{32, 31},
{33, 31},
{34, 31},
{35, 30},
{36, 28},
{37, 29},
{38, 30},
{39, 29},
{40, 28},
		}
	})

end
-- [[通过枪械名查找在 canuse 中的项]]
function pubg.canUseFindByGunName (gunName)
	local forList = { ".45", "9mm", "5.56", "7.62" }

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
		ctrlmodeRatio = gunInfo[4], -- Individual recoil coefficient for each gun when squatting
		BreathRatio = gunInfo[5],
		LuopeiRatio = gunInfo[6],
		SanbeiRatio = gunInfo[7],
		PaziRatio = gunInfo[8]
	}

end

--[[ Initialization of firearms database ]]
function pubg.init ()

	-- Clean up the firearms Depot
	local forList = { ".45", "9mm", "5.56", "7.62" }

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
	pubg.autoLog(options, y)
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

	if pubg.isAimingState("ADS") then
		realY = y * pubg[pubg.scope_current]
	elseif pubg.isAimingState("Aim") then
		realY = y * userInfo.sensitivity.Aim * pubg.generalSensitivityRatio
	end
-- 下蹲压枪
	if userInfo.aimingSettings == "ctrlmode" and IsModifierPressed("lctrl") then
		realY = realY * options.ctrlmodeRatio
	end
-- 屏息压枪
	if userInfo.aimingSettings == "ctrlmode" and IsModifierPressed("lshift") then
		realY = realY * options.BreathRatio
-- 三倍屏息压枪
    elseif userInfo.aimingSettings == "ctrlmode" and IsModifierPressed("lshift") and IsKeyLockOn("capslock") then
        realY = realY * options.BreathRatio * options.SanbeiRatio
	end
-- 裸配压枪
	--if userInfo.aimingSettings == "ctrlmode" and not IsKeyLockOn("numlock") then
		--realY = realY * options.LuopeiRatio
	--end
-- 三倍压枪
	--if userInfo.aimingSettings == "ctrlmode" and IsKeyLockOn("capslock") then
		realY = realY * options.SanbeiRatio
	--end
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

	local forList = { ".45", "9mm", "5.56", "7.62" }

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

--[[ set current scope ]]
function pubg.setScope (scope)
	pubg.scope_current = scope
end

--[[ set current gun ]]
function pubg.setGun (gunName)

	local forList = { ".45", "9mm", "5.56", "7.62" }
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

	pubg.changeIsStart(true)
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
	elseif userInfo.startControl == "G_bind" then
		return pubg.isStart
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

--[[ G key command binding ]]
function pubg.runCmd (cmd)
	if cmd == "" then cmd = "none" end
	local switch = {
		["none"] = function () end,
		[".45"] = pubg.setBulletType,
		["9mm"] = pubg.setBulletType,
		["5.56"] = pubg.setBulletType,
		["7.62"] = pubg.setBulletType,
		["scopeX1"] = pubg.setScope,
		["scopeX2"] = pubg.setScope,
		["scopeX3"] = pubg.setScope,
		["scopeX4"] = pubg.setScope,
		["scopeX6"] = pubg.setScope,
		["UMP45"] = pubg.setGun,
		["MP5K"] = pubg.setGun,
		["Tommy Gun"] = pubg.setGun,
		["P90"] = pubg.setGun,
		["Vector"] = pubg.setGun,
		["Micro UZI"] = pubg.setGun,
		["M416"] = pubg.setGun,
		["SCAR-L"] = pubg.setGun,
		["QBZ"] = pubg.setGun,
		["G36C"] = pubg.setGun,
		["AUG"] = pubg.setGun,
		["M249"] = pubg.setGun,
		["M16A4"] = pubg.setGun,
		["Groza"] = pubg.setGun,
		["AKM"] = pubg.setGun,
		["ACE32"] = pubg.setGun,
		["Beryl M762"] = pubg.setGun,
		["DP-28"] = pubg.setGun,
		["first"] = pubg.findInSeries,
		["next"] = pubg.findInSeries,
		["last"] = pubg.findInSeries,
		["first_in_canUse"] = pubg.findInCanUse,
		["next_in_canUse"] = pubg.findInCanUse,
		["last_in_canUse"] = pubg.findInCanUse,
		["fast_pickup"] = pubg.fastPickup,
		["fast_discard"] = pubg.fastDiscard,
		["fast_lick_box"] = pubg.fastLickBox,
		["off"] = function ()
			pubg.changeIsStart(false)
		end,
	}

	local cmdGroup = string.split(cmd, '|')

	for i = 1, #cmdGroup do
		local _cmd = cmdGroup[i]
		if switch[_cmd] then
			switch[_cmd](_cmd)
		end
	end
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
	local forList = { ".45", "9mm", "5.56", "7.62" }
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

	return table.concat({
		"Currently scope: [ " .. pubg.scope_current .. " ]\n",
		"Currently series: [ ", k, " ]\n",
		"Currently index in series: [ ", i, " / ", #pubg.gun[k], " ]\n",
		"Currently index in canUse: [ ", pubg.allCanUse_index, " / ", pubg.allCanUse_count, " ]\n",
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
function pubg.autoLog (options, y)
	pubg.renderDom.autoLog = table.concat({
		"----------------------------------- Automatically counteracting gun recoil -----------------------------------\n",
		"------------------------------------------------------------------------------------------------------------------------------\n",
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

-- [[ processing instruction ]]
function pubg.modifierHandle (modifier)
	local cmd = userInfo.G_bind[modifier]
	pubg.renderDom.combo_key = modifier -- Save combination keys

	if (cmd) then
		pubg.renderDom.cmd = cmd -- Save instruction name
		pubg.runCmd(cmd) -- Execution instructions
	else
		pubg.renderDom.cmd = ""
	end

	pubg.outputLogRender() -- Call log rendering method to output information
end

--[[ 关闭压枪功能 ]]
function pubg.turnOffRecoil()
	if pubg.isStart then
		pubg.changeIsStart(false)
		OutputLogMessage("压枪已关闭\n")
	end
end

--[[ Listener method ]]
function OnEvent (event, arg, family)

	-- OutputLogMessage("event = %s, arg = %s, family = %s\n", event, arg, family)
	-- console.log("event = " .. event .. ", arg = " .. arg .. ", family = " .. family)

	-- 按下G键关闭压枪（G键对应arg=8）
	if event == "G_PRESSED" and arg == 8 then
		pubg.turnOffRecoil()
		return
	end

	-- 按下键盘数字键3、4、5关闭压枪
	if event == "KEY_PRESSED" and family == "keyboard" then
		-- arg值：数字键0-9对应 10,11,12,13,14,15,16,17,18,19
		if arg == 13 or arg == 14 or arg == 15 then  -- 数字键3,4,5
			pubg.turnOffRecoil()
			return
		end
	end

	pubg.OnEvent_NoRecoil(event, arg, family)

	-- Switching arsenals according to different types of ammunition
	if event == "MOUSE_BUTTON_PRESSED" and arg >=3 and arg <= 11 and family == "mouse" then
		local modifier = "G" .. arg
		local list = { "lalt", "lctrl", "lshift", "ralt", "rctrl", "rshift" }
        
		for i = 1, #list do
			if IsModifierPressed(list[i]) then
				modifier = list[i] .. " + " .. modifier
				break
			end
		end

		pubg.modifierHandle(modifier)
	elseif event == "G_PRESSED" and arg >=1 and arg <= 12 then
		-- if not pubg.runStatus() and userInfo.startControl ~= "G_bind" then return false end
		local modifier = "F" .. arg

		pubg.modifierHandle(modifier)
	elseif event == "G_PRESSED" and arg >= 13 and arg <= 20 then
		-- 支持数字键1-8（需在GHUB中将数字键绑定为G13-G20）
		local numKey = arg - 12
		local modifier = numKey .. ""
		if IsModifierPressed("lalt") then
			modifier = "lalt + " .. modifier
		elseif IsModifierPressed("ralt") then
			modifier = "ralt + " .. modifier
		elseif IsModifierPressed("lctrl") then
			modifier = "lctrl + " .. modifier
		elseif IsModifierPressed("rctrl") then
			modifier = "rctrl + " .. modifier
		elseif IsModifierPressed("lshift") then
			modifier = "lshift + " .. modifier
		elseif IsModifierPressed("rshift") then
			modifier = "rshift + " .. modifier
		end
		pubg.modifierHandle(modifier)
	end

	-- Script deactivated event
	if event == "PROFILE_DEACTIVATED" then
		EnablePrimaryMouseButtonEvents(false)
		ReleaseKey("lshift")
		ReleaseKey("lctrl")
		ReleaseKey("lalt")
		ReleaseKey("rshift")
		ReleaseKey("rctrl")
		ReleaseKey("ralt")
		ClearLog()
	end

end

--[[ tools ]]

-- 四舍五入 #170
function math.round (num, digit)
    local decimalPlaces = 10 ^ (digit or 0)
    return math.floor((num * decimalPlaces * 10 + 5) / 10) / decimalPlaces
end

-- split function
function string.split (str, s)
	if string.find(str, s) == nil then return { str } end

	local res = {}
	local reg = "(.-)" .. s .. "()"
	local index = 0
	local last_i

	--- @diagnostic disable-next-line: undefined-field
	for n, i in string.gfind(str, reg) do
		index = index + 1
		res[index] = n
		last_i = i
	end

	res[index + 1] = string.sub(str, last_i)

	return res
end

-- Javascript Array.prototype.reduce
function table.reduce (t, c)
	local res = c(t[1], t[2])
	for i = 3, #t do res = c(res, t[i]) end
	return res
end

-- Javascript Array.prototype.map
function table.map (t, c)
	local res = {}
	for i = 1, #t do res[i] = c(t[i], i) end
	return res
end

-- Javascript Array.prototype.forEach
function table.forEach (t, c)
	for i = 1, #t do c(t[i], i) end
end

--[[
	* 打印 table
	* @param  {any} val     传入值
	* @return {str}         格式化后的文本
]]
function table.print (val)

	local function loop (val, keyType, _indent)
		_indent = _indent or 1
		keyType = keyType or "string"
		local res = ""
		local indentStr = "     " -- 缩进空格
		local indent = string.rep(indentStr, _indent)
		local end_indent = string.rep(indentStr, _indent - 1)
		local putline = function (...)
			local arr = { res, ... }
			for i = 1, #arr do
				if type(arr[i]) ~= "string" then arr[i] = tostring(arr[i]) end
			end
			res = table.concat(arr)
		end

		if type(val) == "table" then
			putline("{ ")

			if #val > 0 then
				local index = 0
				local block = false

				for i = 1, #val do
					local n = val[i]
					if type(n) == "table" or type(n) == "function" then
						block = true
						break
					end
				end

				if block then
					for i = 1, #val do
						local n = val[i]
						index = index + 1
						if index == 1 then putline("\n") end
						putline(indent, loop(n, type(i), _indent + 1), "\n")
						if index == #val then putline(end_indent) end
					end
				else
					for i = 1, #val do
						local n = val[i]
						index = index + 1
						putline(loop(n, type(i), _indent + 1))
					end
				end

			else
				putline("\n")
				for k, v in pairs(val) do
					putline(indent, k, " = ", loop(v, type(k), _indent + 1), "\n")
				end
				putline(end_indent)
			end

			putline("}, ")
		elseif type(val) == "string" then
			val = string.gsub(val, "\a", "\\a") -- 响铃(BEL)
			val = string.gsub(val, "\b", "\\b") -- 退格(BS),将当前位置移到前一列
			val = string.gsub(val, "\f", "\\f") -- 换页(FF),将当前位置移到下页开头
			val = string.gsub(val, "\n", "\\n") -- 换行(LF),将当前位置移到下一行开头
			val = string.gsub(val, "\r", "\\r") -- 回车(CR),将当前位置移到本行开头
			val = string.gsub(val, "\t", "\\t") -- 水平指标(HT),(调用下一个TAB位置)
			val = string.gsub(val, "\v", "\\v") -- 垂直指标(VT)
			putline("\"", val, "\", ")
		elseif type(val) == "boolean" then
			putline(val and "true, " or "false, ")
		elseif type(val) == "function" then
			putline(tostring(val), ", ")
		elseif type(val) == "nil" then
			putline("nil, ")
		else
			putline(val, ", ")
		end

		return res
	end

	local res = loop(val)
	res = string.gsub(res, ",(%s*})", "%1")
	res = string.gsub(res, ",(%s*)$", "%1")
	res = string.gsub(res, "{%s+}", "{}")

	return res
end

-- console
console = {}
function console.log (str)
	OutputLogMessage(table.print(str) .. "\n")
end

--[[ Other ]]
EnablePrimaryMouseButtonEvents(true) -- Enable left mouse button event reporting
pubg.GD = GetDate -- Setting aliases
pubg.init() -- Script initialization

--[[ Script End ]]