local _, ns = ...

ns.UI = ns.UI or {}

local MAX_HISTORY_LINES = 200
local COLOR_QUESTION = { 0.4, 0.75, 1 }
local COLOR_SYSTEM = { 1, 0.85, 0.3 }
local COLOR_WARNING = { 1, 0.4, 0.4 }

local mainFrame
local history
local editBox

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

local function SendQuestion(text)
    local question = (text or ''):match('^%s*(.-)%s*$')
    if question == '' then
        return
    end
    AddHistory(question, COLOR_QUESTION)
    AddHistory(ns.L.PROMPT_READY, COLOR_SYSTEM)
    ns.UI.lastQuestion = question
    editBox:SetText('')
    editBox:ClearFocus()
end

local function CopyPrompt()
    local question = ns.UI.lastQuestion
    if not question then
        AddHistory(ns.L.NO_QUESTION, COLOR_WARNING)
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

    mainFrame = CreateFrame('Frame', 'AskForeverMainFrame', UIParent, 'BasicFrameTemplateWithInset')
    mainFrame:SetSize(420, 340)
    mainFrame:SetFrameStrata('DIALOG')
    mainFrame:SetClampedToScreen(true)
    mainFrame:SetMovable(true)
    mainFrame:Hide()
    table.insert(UISpecialFrames, 'AskForeverMainFrame')

    local title = mainFrame:CreateFontString(nil, 'OVERLAY', 'GameFontNormalLarge')
    title:SetPoint('TOP', mainFrame, 'TOP', 0, -8)
    title:SetText(ns.L.WINDOW_TITLE)

    history = CreateFrame('ScrollingMessageFrame', nil, mainFrame)
    history:SetPoint('TOPLEFT', mainFrame, 'TOPLEFT', 16, -36)
    history:SetPoint('BOTTOMRIGHT', mainFrame, 'BOTTOMRIGHT', -16, 84)
    history:SetFontObject(ChatFontNormal)
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

    editBox = CreateFrame('EditBox', nil, mainFrame, 'InputBoxTemplate')
    editBox:SetSize(296, 24)
    editBox:SetPoint('BOTTOMLEFT', mainFrame, 'BOTTOMLEFT', 18, 52)
    editBox:SetAutoFocus(false)
    editBox:SetMaxLetters(500)
    editBox:SetScript('OnEnterPressed', function(self)
        SendQuestion(self:GetText())
    end)
    editBox:SetScript('OnEscapePressed', function(self)
        self:ClearFocus()
    end)

    local sendButton = CreateFrame('Button', nil, mainFrame, 'UIPanelButtonTemplate')
    sendButton:SetSize(80, 24)
    sendButton:SetPoint('BOTTOMRIGHT', mainFrame, 'BOTTOMRIGHT', -16, 52)
    sendButton:SetText(ns.L.SEND)
    sendButton:SetScript('OnClick', function()
        SendQuestion(editBox:GetText())
    end)

    local copyButton = CreateFrame('Button', nil, mainFrame, 'UIPanelButtonTemplate')
    copyButton:SetSize(140, 22)
    copyButton:SetPoint('BOTTOMLEFT', mainFrame, 'BOTTOMLEFT', 16, 18)
    copyButton:SetText(ns.L.COPY_PROMPT)
    copyButton:SetScript('OnClick', CopyPrompt)

    local dragArea = CreateFrame('Frame', nil, mainFrame)
    dragArea:SetPoint('TOPLEFT', mainFrame, 'TOPLEFT', 8, -4)
    dragArea:SetPoint('TOPRIGHT', mainFrame, 'TOPRIGHT', -30, -4)
    dragArea:SetHeight(28)
    dragArea:EnableMouse(true)
    dragArea:RegisterForDrag('LeftButton')
    dragArea:SetScript('OnDragStart', function()
        mainFrame:StartMoving()
    end)
    dragArea:SetScript('OnDragStop', function()
        mainFrame:StopMovingOrSizing()
        SavePosition(mainFrame)
    end)

    mainFrame:SetScript('OnShow', function()
        editBox:SetFocus()
    end)
    mainFrame:SetScript('OnHide', function()
        editBox:ClearFocus()
    end)

    RestorePosition(mainFrame)
    return mainFrame
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
