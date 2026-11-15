local _, ns = ...

ns.UI = ns.UI or {}

local Theme = ns.UI.Theme
local colors = Theme.colors

local MAX_HISTORY_LINES = 200

local mainFrame
local historyPanel
local history
local editBox
local summaryText
local sentThisOpening = false

local function AddHistory(text, color)
    history:AddMessage(text, color[1], color[2], color[3])
end

local function SavePosition(frame)
    local point, _, relPoint, x, y = frame:GetPoint(1)
    if not point then
        return
    end
    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    AskForeverDB.window = { point = point, relPoint = relPoint, x = x, y = y }
end

local function RestorePosition(frame)
    frame:ClearAllPoints()
    local saved = type(AskForeverDB) == 'table' and AskForeverDB.window
    if type(saved) == 'table' and saved.point then
        frame:SetPoint(saved.point, UIParent, saved.relPoint or saved.point, saved.x or 0, saved.y or 0)
    else
        frame:SetPoint('CENTER', UIParent, 'CENTER', 0, 0)
    end
end

local function BuildSummary()
    local ctx = ns.Context.Collect()
    local text = ns.L.CTX_SUMMARY:format(
        ctx.level and tostring(ctx.level) or '',
        ctx.race or '',
        ctx.class or '',
        ctx.zone or ''
    )
    text = text:gsub('%s+', ' '):gsub('^%s*·%s*', ''):gsub('%s*·%s*$', ''):gsub('^%s+', '')
    return text
end

local function ConversationNumber()
    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    if type(AskForeverDB.transport) ~= 'table' then
        AskForeverDB.transport = {}
    end
    local conv = AskForeverDB.transport.conv
    if type(conv) ~= 'number' or conv ~= math.floor(conv) then
        conv = 1
        AskForeverDB.transport.conv = conv
    end
    return conv
end

local function SendQuestion(text)
    local question = (text or ''):match('^%s*(.-)%s*$')
    if question == '' then
        return
    end
    AddHistory(question, colors.title)
    AddHistory(ns.L.PROMPT_READY, colors.textDim)
    ns.UI.lastQuestion = question
    editBox:SetText('')
    editBox:ClearFocus()

    local inCombat = InCombatLockdown()
    local wx, wy, ww, wh = ns.UI.GetChatRect()
    local extra
    if wx ~= nil then
        extra = { wx = wx, wy = wy, ww = ww, wh = wh }
    end
    local accepted = ns.Transport.Send(question, nil, ConversationNumber(), nil, extra)
    if accepted then
        sentThisOpening = true
        AddHistory(inCombat and ns.L.QUEUED_COMBAT or ns.L.SENT_STRIP, colors.textDim)
    else
        AddHistory(ns.L.SEND_FAILED, colors.missing)
    end
end

local function CopyPrompt()
    local question = ns.UI.lastQuestion
    if not question then
        AddHistory(ns.L.NO_QUESTION, colors.missing)
        return
    end
    local ctx = ns.Context.Collect()
    local prompt = ns.Prompt.Build(question, ctx)
    ns.UI.ShowCopyBox(prompt)
end

local function EnsureMainFrame()
    if mainFrame then
        return mainFrame
    end

    mainFrame = ns.UI.CreateWindow('AskForeverMainFrame', 480, 400, ns.L.WINDOW_TITLE)
    local body = mainFrame.body

    summaryText = ns.UI.CreateText(body, Theme.font.small, colors.textDim)
    summaryText:SetPoint('TOPLEFT', body, 'TOPLEFT', 10, -8)
    summaryText:SetPoint('TOPRIGHT', body, 'TOPRIGHT', -10, -8)
    summaryText:SetJustifyH('LEFT')
    summaryText:SetText('')

    historyPanel = ns.UI.CreatePanel(body)
    historyPanel:SetPoint('TOPLEFT', body, 'TOPLEFT', 8, -26)
    historyPanel:SetPoint('BOTTOMRIGHT', body, 'BOTTOMRIGHT', -8, 92)

    history = CreateFrame('ScrollingMessageFrame', nil, historyPanel)
    history:SetPoint('TOPLEFT', historyPanel, 'TOPLEFT', 8, -8)
    history:SetPoint('BOTTOMRIGHT', historyPanel, 'BOTTOMRIGHT', -8, 8)
    history:SetFontObject(ChatFontNormal or Theme.font.body)
    history:SetJustifyH('LEFT')
    history:SetFading(false)
    history:SetMaxLines(MAX_HISTORY_LINES)
    history:EnableMouse(true)
    history:EnableMouseWheel(true)
    history:SetScript('OnMouseWheel', function(self, delta)
        if delta > 0 then
            self:ScrollUp()
        else
            self:ScrollDown()
        end
    end)

    editBox = ns.UI.CreateInput(body)
    editBox:SetPoint('BOTTOMLEFT', body, 'BOTTOMLEFT', 8, 60)
    editBox:SetPoint('BOTTOMRIGHT', body, 'BOTTOMRIGHT', -96, 60)
    editBox:SetHeight(24)
    editBox:SetMaxLetters(500)
    editBox:SetScript('OnEnterPressed', function(self)
        SendQuestion(self:GetText())
    end)
    editBox:SetScript('OnEscapePressed', function(self)
        self:ClearFocus()
    end)

    local sendButton = ns.UI.CreateButton(body, ns.L.SEND, 80, 24, function()
        SendQuestion(editBox:GetText())
    end)
    sendButton:SetPoint('BOTTOMRIGHT', body, 'BOTTOMRIGHT', -8, 60)

    local copyButton = ns.UI.CreateButton(body, ns.L.COPY_PROMPT, 150, 24, CopyPrompt)
    copyButton:SetPoint('BOTTOMLEFT', body, 'BOTTOMLEFT', 8, 16)
    if copyButton.GetFontString then
        local label = copyButton:GetFontString()
        if label then
            label:SetTextColor(colors.title[1], colors.title[2], colors.title[3])
        end
    end

    local reportButton
    if ns.DevReport and type(ns.DevReport.Attach) == 'function' then
        local ok, button = pcall(ns.DevReport.Attach, body, editBox, AddHistory, colors,
                                 ConversationNumber)
        if ok then
            reportButton = button
        end
    end

    local helpButton = ns.UI.CreateButton(body, ns.L.HELP_BUTTON, 24, 24, function()
        if type(ns.UI.ShowHelp) == 'function' then
            ns.UI.ShowHelp()
        end
    end)
    helpButton:SetPoint('BOTTOMRIGHT', body, 'BOTTOMRIGHT', -8, 16)
    helpButton:SetScript('OnEnter', function(self)
        GameTooltip:SetOwner(self, 'ANCHOR_TOP')
        GameTooltip:SetText(ns.L.HELP_BUTTON_TIP)
        GameTooltip:Show()
    end)
    helpButton:SetScript('OnLeave', function()
        GameTooltip:Hide()
    end)

    if reportButton then
        reportButton:ClearAllPoints()
        reportButton:SetPoint('BOTTOMRIGHT', helpButton, 'BOTTOMLEFT', -8, 0)
    end

    local note = ns.UI.CreateText(body, Theme.font.small, colors.textDim)
    note:SetPoint('LEFT', copyButton, 'RIGHT', 10, 0)
    if reportButton then
        note:SetPoint('RIGHT', reportButton, 'LEFT', -10, 0)
    else
        note:SetPoint('RIGHT', helpButton, 'LEFT', -10, 0)
    end
    note:SetJustifyH('LEFT')
    note:SetText(ns.L.OFFLINE_NOTE)

    table.insert(UISpecialFrames, 'AskForeverMainFrame')

    mainFrame:SetScript('OnShow', function()
        sentThisOpening = false
        ConversationNumber()
        summaryText:SetText(BuildSummary())
        editBox:SetFocus()
        if ns.Transport and type(ns.Transport.SendUi) == 'function' then
            ns.Transport.SendUi('open')
        end
    end)
    mainFrame:SetScript('OnHide', function()
        editBox:ClearFocus()
        if sentThisOpening then
            local nextConv = ConversationNumber() + 1
            if nextConv > 65535 then
                nextConv = 1
            end
            AskForeverDB.transport.conv = nextConv
            sentThisOpening = false
        end
        if ns.Transport and type(ns.Transport.SendUi) == 'function' then
            ns.Transport.SendUi('close')
        end
    end)
    mainFrame.onMoveStop = function()
        SavePosition(mainFrame)
        if ns.Transport and type(ns.Transport.SendUi) == 'function' then
            ns.Transport.SendUi('move')
        end
    end

    RestorePosition(mainFrame)
    return mainFrame
end

function ns.UI.GetChatRect()
    if not mainFrame or not historyPanel then
        return nil
    end
    local shownOk, shown = pcall(mainFrame.IsShown, mainFrame)
    if not shownOk or not shown then
        return nil
    end
    local panelOk, left, top, width, height, scale = pcall(function()
        return historyPanel:GetLeft(), historyPanel:GetTop(),
               historyPanel:GetWidth(), historyPanel:GetHeight(),
               historyPanel:GetEffectiveScale()
    end)
    if not panelOk then
        return nil
    end
    if type(left) ~= 'number' or type(top) ~= 'number'
        or type(width) ~= 'number' or type(height) ~= 'number'
        or type(scale) ~= 'number' then
        return nil
    end
    if left ~= left or top ~= top or width ~= width or height ~= height or scale ~= scale then
        return nil
    end
    if width <= 0 or height <= 0 or scale <= 0 then
        return nil
    end
    if type(GetPhysicalScreenSize) ~= 'function' then
        return nil
    end
    local sizeOk, physW, physH = pcall(GetPhysicalScreenSize)
    if not sizeOk or type(physW) ~= 'number' or type(physH) ~= 'number' then
        return nil
    end
    if physW <= 0 or physH <= 0 or physW ~= physW or physH ~= physH then
        return nil
    end

    local unitsToPx = (physH / 768) * scale
    local wx = math.floor(left * unitsToPx + 0.5)
    local wy = math.floor(physH - top * unitsToPx + 0.5)
    local ww = math.floor(width * unitsToPx + 0.5)
    local wh = math.floor(height * unitsToPx + 0.5)
    if wx < 0 or wy < 0 or ww <= 0 or wh <= 0 then
        return nil
    end
    return wx, wy, ww, wh
end

function ns.UI.ShowMain()
    EnsureMainFrame():Show()
end

function ns.UI.ToggleMain()
    local frame = EnsureMainFrame()
    if frame:IsShown() then
        frame:Hide()
    else
        frame:Show()
    end
end

function ns.UI.ResetPosition()
    if type(AskForeverDB) == 'table' then
        AskForeverDB.window = nil
    end
    if mainFrame then
        mainFrame:ClearAllPoints()
        mainFrame:SetPoint('CENTER', UIParent, 'CENTER', 0, 0)
    end
end
