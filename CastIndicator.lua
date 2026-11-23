


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








--自动输出

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

local indicator = CreateFrame("Frame", nil, UIParent)
indicator:SetSize(5, 5)
indicator:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 10, 0)

local tex = indicator:CreateTexture(nil, "BACKGROUND")
tex:SetAllPoints(indicator)
tex:SetColorTexture(1, 1, 1, 1)



local indicator1 = CreateFrame("Frame", nil, UIParent)
indicator1:SetSize(5, 5)
indicator1:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 10, 0)

local tex1 = indicator1:CreateTexture(nil, "BACKGROUND")
tex1:SetAllPoints(indicator1)
tex1:SetColorTexture(1, 1, 1, 1)
indicator1:SetAlphaFromBoolean(false, 1, 0)


local indicator2 = CreateFrame("Frame", nil, UIParent)
indicator2:SetSize(5, 5)
indicator2:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 10, 0)

local tex2 = indicator2:CreateTexture(nil, "BACKGROUND")
tex2:SetAllPoints(indicator2)
tex2:SetColorTexture(1, 1, 1, 1)
indicator2:SetAlphaFromBoolean(false, 1, 0)

indicator:SetFrameLevel(1)
indicator1:SetFrameLevel(2)
indicator2:SetFrameLevel(3)


function GetButtonSpell(slotIndex,nextSpellID)
    local actionType, id = GetActionInfo(slotIndex)
    if actionType == "spell" then
		--print("返回技能id: " .. id);
        return id
	elseif actionType == "macro" then
	
		if nextSpellID then
			if(GetActionTexture(slotIndex) == C_Spell.GetSpellTexture(nextSpellID)) then
				--print("返回宏: " .. id);
				return nextSpellID
			end
		end
		
    end
    return nil
end


local function UpdateIndicator()
	
	if IsAltKeyDown() then
        tex:SetColorTexture(0, 0, 0, 1)
        return
    end
	
	if SpellIsTargeting() then
        tex:SetColorTexture(0, 0, 0, 1)
        return
    end
	
    local nextSpellID = C_AssistedCombat.GetNextCastSpell(true)
	
	local _, class = UnitClass("player")
	if class == "ROGUE" then
		-- 60能量
		isUsable, insufficientPower = C_Spell.IsSpellUsable(1247227)
		if insufficientPower then
			tex:SetColorTexture(0, 0, 0, 1)
			return
		end
	
		
		-- 50能量
		isUsable, insufficientPower = C_Spell.IsSpellUsable(197835)
		if insufficientPower then
			tex:SetColorTexture(0, 0, 0, 1)
			return
		end
	elseif class == "WARRIOR" then
        
        
	elseif class == "MONK" then
		--醉酿投 40能量
		isUsable, insufficientPower = C_Spell.IsSpellUsable(121253)
		if insufficientPower then
			tex:SetColorTexture(0, 0, 0, 1)
			return
		end

    elseif class == "DEMONHUNTER" then
		-- 邪能之刃 232893
		local isNotOnCooldown1 = C_Spell.GetSpellCooldownDuration(232893,true):IsZero() 
        indicator1:SetAlphaFromBoolean(isNotOnCooldown1, 1, 0)

        for i = 1, 9 do
            local spellID = GetButtonSpell(i,232893)
            if spellID and spellID == 232893 then
                local c = colors[i]
                tex1:SetColorTexture(c[1] / 255, c[2] / 255, c[3] / 255, 1)
            end
        end

    elseif class == "WARLOCK" then
        -- 内爆 196277
        local isNotOnCooldown1 = C_Spell.GetSpellCooldownDuration(196277,true):IsZero() 
        indicator1:SetAlphaFromBoolean(isNotOnCooldown1, 1, 0)

        for i = 1, 9 do
            local spellID = GetButtonSpell(i,196277)
            if spellID and spellID == 196277 then
                local c = colors[i]
                tex1:SetColorTexture(c[1] / 255, c[2] / 255, c[3] / 255, 1)
            end
        end


        -- 小鬼 1276452
        local isNotOnCooldown2 = C_Spell.GetSpellCooldownDuration(1276452,true):IsZero() 
        indicator2:SetAlphaFromBoolean(isNotOnCooldown2, 1, 0)

        for i = 1, 9 do
            local spellID = GetButtonSpell(i,1276452)
            if spellID and spellID == 1276452 then
                local c = colors[i]
                tex2:SetColorTexture(c[1] / 255, c[2] / 255, c[3] / 255, 1)
            end
        end
        
    end




	for i = 109, 117 do
        local spellID = GetButtonSpell(i,nextSpellID)
		if spellID and spellID == nextSpellID then
            local c = colors[i-108]
            tex:SetColorTexture(c[1] / 255, c[2] / 255, c[3] / 255, 1)
            return
        end
    end
	
	for i = 73, 81 do
        local spellID = GetButtonSpell(i,nextSpellID)
        if spellID and spellID == nextSpellID then
            local c = colors[i-72]
            tex:SetColorTexture(c[1] / 255, c[2] / 255, c[3] / 255, 1)
            return
        end
    end
	
	for i = 85, 93 do
        local spellID = GetButtonSpell(i,nextSpellID)
        if spellID and spellID == nextSpellID then
            local c = colors[i-84]
            tex:SetColorTexture(c[1] / 255, c[2] / 255, c[3] / 255, 1)
            return
        end
    end

    for i = 1, 9 do
        local spellID = GetButtonSpell(i,nextSpellID)
        if spellID and spellID == nextSpellID then
            local c = colors[i]
            tex:SetColorTexture(c[1] / 255, c[2] / 255, c[3] / 255, 1)
            return
        end
    end
	
	for i = 97, 105 do
        local spellID = GetButtonSpell(i,nextSpellID)
        if spellID and spellID == nextSpellID then
            local c = colors[i-96]
            tex:SetColorTexture(c[1] / 255, c[2] / 255, c[3] / 255, 1)
            return
        end
    end
		
	
    tex:SetColorTexture(0, 0, 0, 1)
end

local function OnUpdate(self, elapsed)
    UpdateIndicator()
end

indicator:SetScript("OnUpdate", OnUpdate)


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



