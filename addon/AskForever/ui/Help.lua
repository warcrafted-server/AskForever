local _, ns = ...

ns.UI = ns.UI or {}

local Theme = ns.UI.Theme
local colors = Theme.colors
local RELEASES_URL = 'https://github.com/warcrafted-server/AskForever/releases'

local helpFrame
local linkBoxes = {}

local function StyleLink(editBox, url)
    editBox:SetText(url)
    editBox:SetAutoFocus(false)
    editBox:SetMaxLetters(0)
    editBox:SetScript('OnTextChanged', function(self, userInput)
        if userInput then
            self:SetText(url)
            self:HighlightText()
        end
    end)
    editBox:SetScript('OnEscapePressed', function(self)
        self:ClearFocus()
    end)
    editBox:HookScript('OnEditFocusGained', function(self)
        self:HighlightText()
    end)
end

local function NewLinkRow(parent, anchor, text, url)
    local label = ns.UI.CreateText(parent, Theme.font.body, colors.text)
    label:SetPoint('TOPLEFT', anchor, 'BOTTOMLEFT', 0, -10)
    label:SetPoint('RIGHT', parent, 'RIGHT', -10, 0)
    label:SetJustifyH('LEFT')
    label:SetWordWrap(true)
    label:SetHeight(36)
    label:SetText(text)

    local edit = ns.UI.CreateInput(parent)
    edit:SetPoint('TOPLEFT', label, 'BOTTOMLEFT', 0, -4)
    edit:SetPoint('RIGHT', parent, 'RIGHT', -76, 0)
    edit:SetHeight(24)
    StyleLink(edit, url)
    table.insert(linkBoxes, edit)

    local copy = ns.UI.CreateButton(parent, ns.L.HELP_COPY, 66, 24, function()
        edit:SetFocus()
        edit:HighlightText()
    end)
    copy:SetPoint('LEFT', edit, 'RIGHT', 6, 0)

    return edit
end

local function EnsureHelpFrame()
    if helpFrame then
        return helpFrame
    end
    if type(ns.UI.CreateWindow) ~= 'function' then
        return nil
    end

    local ok, frame = pcall(ns.UI.CreateWindow, 'AskForeverHelpFrame', 520, 420,
                            ns.L.HELP_WINDOW_TITLE)
    if not ok or not frame or not frame.body then
        return nil
    end

    frame:SetFrameStrata('DIALOG')
    frame:SetPoint('CENTER', UIParent, 'CENTER', 0, 0)
    if type(UISpecialFrames) == 'table' then
        local present = false
        for _, name in ipairs(UISpecialFrames) do
            if name == 'AskForeverHelpFrame' then
                present = true
                break
            end
        end
        if not present then
            table.insert(UISpecialFrames, 'AskForeverHelpFrame')
        end
    end

    local body = frame.body

    local intro = ns.UI.CreateText(body, Theme.font.body, colors.text)
    intro:SetPoint('TOPLEFT', body, 'TOPLEFT', 10, -10)
    intro:SetPoint('RIGHT', body, 'RIGHT', -10, 0)
    intro:SetJustifyH('LEFT')
    intro:SetWordWrap(true)
    intro:SetHeight(44)
    intro:SetText(ns.L.HELP_INTRO)

    local step1 = NewLinkRow(body, intro, ns.L.HELP_STEP_COMPANION, RELEASES_URL)
    local step2 = NewLinkRow(body, step1, ns.L.HELP_STEP_KEY, ns.L.HELP_URL_KEY)
    NewLinkRow(body, step2, ns.L.HELP_STEP_PLAY, ns.L.HELP_URL_GUIDE)

    local okButton = ns.UI.CreateButton(body, ns.L.HELP_OK, 90, 24, function()
        frame:Hide()
    end)
    okButton:SetPoint('BOTTOMRIGHT', body, 'BOTTOMRIGHT', -10, 10)

    local hint = ns.UI.CreateText(body, Theme.font.small, colors.textDim)
    hint:SetPoint('BOTTOMLEFT', body, 'BOTTOMLEFT', 10, 16)
    hint:SetPoint('RIGHT', okButton, 'LEFT', -8, 0)
    hint:SetJustifyH('LEFT')
    hint:SetText(ns.L.HELP_COPY_HINT)

    local footer = ns.UI.CreateText(body, Theme.font.small, colors.textDim)
    footer:SetPoint('BOTTOMLEFT', body, 'BOTTOMLEFT', 10, 46)
    footer:SetPoint('RIGHT', body, 'RIGHT', -10, 0)
    footer:SetJustifyH('LEFT')
    footer:SetWordWrap(true)
    footer:SetHeight(34)
    footer:SetText(ns.L.HELP_FOOTER)

    frame:SetScript('OnHide', function()
        for _, edit in ipairs(linkBoxes) do
            if edit.ClearFocus then
                pcall(edit.ClearFocus, edit)
            end
        end
    end)

    helpFrame = frame
    return frame
end

function ns.UI.ShowHelp()
    local frame = EnsureHelpFrame()
    if not frame then
        return
    end
    if frame.Raise then
        pcall(frame.Raise, frame)
    end
    frame:Show()
end

function ns.UI.ToggleHelp()
    local frame = EnsureHelpFrame()
    if not frame then
        return
    end
    if frame:IsShown() then
        frame:Hide()
    else
        ns.UI.ShowHelp()
    end
end

local loginFrame = CreateFrame('Frame')

local function TryShowWelcome()
    if type(AskForeverDB) ~= 'table' or AskForeverDB.welcomeShown == true then
        return
    end
    if InCombatLockdown() then
        loginFrame:RegisterEvent('PLAYER_REGEN_ENABLED')
        return
    end
    loginFrame:UnregisterEvent('PLAYER_REGEN_ENABLED')
    ns.UI.ShowHelp()
    AskForeverDB.welcomeShown = true
end

loginFrame:RegisterEvent('PLAYER_LOGIN')
loginFrame:SetScript('OnEvent', function(self, event)
    if event == 'PLAYER_LOGIN' then
        self:UnregisterEvent('PLAYER_LOGIN')
        if C_Timer and type(C_Timer.After) == 'function' then
            C_Timer.After(3, TryShowWelcome)
        else
            TryShowWelcome()
        end
    elseif event == 'PLAYER_REGEN_ENABLED' then
        self:UnregisterEvent('PLAYER_REGEN_ENABLED')
        TryShowWelcome()
    end
end)
