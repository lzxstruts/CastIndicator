--控制开关 第一个色块
local combatIndicatorFrame = CreateFrame("Frame", "CombatIndicator", UIParent)
combatIndicatorFrame:SetSize(5, 5)
combatIndicatorFrame:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 0, 0)
local tex = combatIndicatorFrame:CreateTexture(nil, "BACKGROUND")
tex:SetAllPoints(combatIndicatorFrame)
local function CombatIndicatorUpdate(self, elapsed)
	if InCombatLockdown() then
        if IsMounted() or UnitChannelInfo("player") or UnitIsDead("target") or GetShapeshiftFormID() == 27 or GetShapeshiftFormID() == 3 then
			 -- 绿色：骑乘/引导
            tex:SetColorTexture(0, 1, 0, 1) 
        elseif UnitCanAttack("player", "target") then
			-- 红色：目标敌对
            tex:SetColorTexture(1, 0, 0, 1)  
        else
			-- 绿色：未骑乘、未引导但无目标或目标是友方
            tex:SetColorTexture(0, 1, 0, 1)  
        end
    else
		-- 绿色：非战斗
        tex:SetColorTexture(0, 1, 0, 1)      
    end
    combatIndicatorFrame:Show()
end
combatIndicatorFrame:SetScript("OnUpdate", CombatIndicatorUpdate)

-- 按键颜色映射表
local colors = {
    {255, 69, 69},--1
    {255, 135, 69},--2
    {255, 222, 69},--3
    {69, 255, 69},--4
    {69, 255, 222},--5
    {69, 135, 255},--6
    {171, 69, 255},--7
    {255, 69, 171},--8
    {255, 255, 255},--9
}

--输出循环色块 indicator是一键辅助.indicator1是特殊技能1 indicator2是特殊技能2 
local function CreateIndicator()
    local indicator = CreateFrame("Frame", nil, UIParent)
    indicator:SetSize(5, 5)
    indicator:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 10, 0)

    local tex = indicator:CreateTexture(nil, "BACKGROUND")
    tex:SetAllPoints(indicator)
    tex:SetColorTexture(1, 1, 1, 1)
    indicator:SetAlphaFromBoolean(false, 1, 0)

    return indicator, tex
end

local indicator, tex = CreateIndicator()
local indicator1, tex1 = CreateIndicator()
local indicator2, tex2 = CreateIndicator()

indicator:SetFrameLevel(1)
indicator:SetAlphaFromBoolean(true, 1, 0)

indicator1:SetFrameLevel(2)
indicator2:SetFrameLevel(3)

--获取动作条上的技能ID，如果是宏则检查宏的图标是否与下一个技能的图标匹配
function GetButtonSpell(slotIndex,nextSpellID)
    local actionType, id = GetActionInfo(slotIndex)
    if actionType == "spell" then
        return id
	elseif actionType == "macro" then	
		if nextSpellID then
			if(GetActionTexture(slotIndex) == C_Spell.GetSpellTexture(nextSpellID)) then
				return nextSpellID
			end
		end
    end
    return nil
end

-- 检查技能能量是否足够
local function CheckSpellUsable(spellID)
    local isUsable, insufficientPower = C_Spell.IsSpellUsable(spellID)
    if insufficientPower then
        tex:SetColorTexture(0, 0, 0, 1)
        return false
    end
    return true
end

-- 更新技能指示器的颜色和透明度
local function UpdateSpellIndicator(spellID,indicatorFrame,texture)
   if not CheckSpellUsable(spellID) then return end
    
    local isNotOnCooldown = C_Spell.GetSpellCooldownDuration(spellID, true):IsZero()
    indicatorFrame:SetAlphaFromBoolean(isNotOnCooldown, 1, 0)

    for i = 1, 9 do
        local buttonSpellID = GetButtonSpell(i, spellID)
        if buttonSpellID == spellID then
            local c = colors[i]
            texture:SetColorTexture(c[1] / 255, c[2] / 255, c[3] / 255, 1)
        end
    end
end
-- 更新下一个技能的颜色
local function UpdateSpellTexture(nextSpellID)
    local ranges = {{109, 117},{73, 81},{85, 93},{1, 9},{97, 105}}
    for _, range in ipairs(ranges) do
        for i = range[1], range[2] do
            local spellID = GetButtonSpell(i, nextSpellID)

            if spellID == nextSpellID then
                local c = colors[i - range[1] + 1]
                tex:SetColorTexture(c[1] / 255, c[2] / 255, c[3] / 255, 1)
                return
            end
        end
    end
    tex:SetColorTexture(0, 0, 0, 1)
end

--每帧循环检查技能状态和下一个技能的颜色
local function UpdateIndicator()	
    
	if IsAltKeyDown() then tex:SetColorTexture(0, 0, 0, 1) return end	
	if SpellIsTargeting() then tex:SetColorTexture(0, 0, 0, 1) return end	

	local _, class = UnitClass("player")
	if class == "ROGUE" then
	    -- 60能量
        if not CheckSpellUsable(1247227) then return end
		-- 50能量
        if not CheckSpellUsable(197835) then return end
	elseif class == "WARRIOR" then
        
        
	elseif class == "MONK" then
		--醉酿投 40能量
		if not CheckSpellUsable(121253) then return end
    elseif class == "DEMONHUNTER" then
		-- 邪能之刃 232893
		UpdateSpellIndicator(232893,indicator1, tex1)
    elseif class == "WARLOCK" then
        -- 内爆 196277
        UpdateSpellIndicator(196277,indicator1, tex1)
        -- 小鬼 1276452
        UpdateSpellIndicator(1276452,indicator2, tex2) 
    elseif class == "DEATHKNIGHT" then
        -- 血沸 50842
        UpdateSpellIndicator(50842,indicator1, tex1)
    end
    local nextSpellID = C_AssistedCombat.GetNextCastSpell(true)
	UpdateSpellTexture(nextSpellID)
end
indicator:SetScript("OnUpdate", UpdateIndicator)

--打印动作条上的技能、宏、物品和集结号信息
function reportActionButtons()
    for i = 1, 132 do
        local t, d = GetActionInfo(i)
        if t == "spell" then
            local s = d and C_Spell.GetSpellInfo(d)
            if s then
                print(i, "|cFF71D5FF技: " .. s.name .. "|r", d)
            end
        elseif t == "macro" then
            local name = C_ActionBar.GetActionText(i)
            if name then 
                print(i, "|cFF69CC69宏: " .. name .. "|r", d)
            end
        elseif t == "item" then
            local name = d and GetItemInfo(d)
            if name then
                print(i, "|cFFFF8000物: " .. name .. "|r", d or 0)
            end
		elseif t == "flyout" then
            local name = d and GetFlyoutInfo(d)
            if name then
                print(i, "|c8000FFFF集: " .. name .. "|r", d or 0)
            end
        else
            local tex, text = GetActionTexture(i), GetActionText(i)
            if tex then
                print(i, "|cFFFFFFFF" .. (text or tex or t) .. "|r", d or "?")
            end
        end
    end
end




--战斗中无目标提示 开始
local targetWarn = CreateFrame("Frame", "CombatTargetWarning", UIParent)
targetWarn:SetSize(1, 1)
targetWarn:SetPoint("CENTER", UIParent, "CENTER", 0, 190)

local warnText = targetWarn:CreateFontString(nil, "OVERLAY")
warnText:SetPoint("CENTER")
warnText:SetFont(GameFontNormalLarge:GetFont(), 60, "OUTLINE")
warnText:SetText("选择目标")
warnText:SetTextColor(1, 0.25, 0.25, 1)
warnText:SetShadowColor(0, 0, 0, 1)
warnText:SetShadowOffset(2, -2)
warnText:Hide()
local pulse = 0
local function TargetWarningUpdate(self, elapsed)
	local specIndex = GetSpecialization()
    local _,_,_,_, role = GetSpecializationInfo(specIndex)

    if role ~= "HEALER" and InCombatLockdown() and not UnitCanAttack("player", "target") and not IsMounted() then
        warnText:Show()
		pulse = pulse + elapsed * 3
        warnText:SetAlpha(0.5 + 0.5 * math.abs(math.sin(pulse))) 
    else
        warnText:Hide()
    end
end

targetWarn:SetScript("OnUpdate", TargetWarningUpdate)
--战斗中无目标提示 结束
