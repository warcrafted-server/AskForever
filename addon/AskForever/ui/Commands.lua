local _, ns = ...

SLASH_ASKFOREVER1 = '/askforever'
SLASH_ASKFOREVER2 = '/af'

local PATTERN_SECONDS = 10
local PATTERN_DATA_SYMBOLS = 1016

local patternRun = 0

local function BuildPatternSymbols()
    local symbols = {}
    for index = 1, PATTERN_DATA_SYMBOLS do
        symbols[index] = (index - 1) % 64
    end
    return symbols
end

local function GetPhysicalSize()
    if type(GetPhysicalScreenSize) ~= 'function' then
        return nil, nil
    end
    local ok, width, height = pcall(GetPhysicalScreenSize)
    if not ok then
        return nil, nil
    end
    return width, height
end

local function ShowPattern()
    local physW, physH = GetPhysicalSize()
    local uiScale = UIParent:GetEffectiveScale()

    ns.Strip.Ensure()
    local strip = ns.Strip.GetFrame()
    local texture = ns.Strip.GetSampleTexture()

    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    AskForeverDB.diag = {
        time = date('%Y-%m-%d %H:%M:%S'),
        physW = physW,
        physH = physH,
        uiScale = uiScale,
        frameScale = strip and strip:GetScale() or nil,
        ignoreParentScale = strip ~= nil and strip.SetIgnoreParentScale ~= nil,
        snap = texture ~= nil and texture.SetSnapToPixelGrid ~= nil,
        bit = bit ~= nil,
    }

    ns.Strip.Show(BuildPatternSymbols(), 8)
    print(ns.L.PATTERN_SHOWN)

    patternRun = patternRun + 1
    local run = patternRun
    if C_Timer and C_Timer.After then
        C_Timer.After(PATTERN_SECONDS, function()
            if run ~= patternRun then
                return
            end
            ns.Strip.Hide()
            print(ns.L.PATTERN_HIDDEN)
        end)
    end
end

local function RunPattern()
    if ns.Strip.IsShown() then
        ns.Strip.Hide()
    end
    ShowPattern()
end

SlashCmdList.ASKFOREVER = function(msg)
    local command = string.lower((msg or ''):match('^%s*(.-)%s*$'))

    if command == '' then
        ns.UI.ToggleMain()
    elseif command == 'help' then
        print(ns.L.HELP_TITLE)
        print(ns.L.HELP_OPEN)
        print(ns.L.HELP_RESET)
        print(ns.L.HELP_MINIMAP)
        print(ns.L.HELP_PATTERN)
        print(ns.L.HELP_HELP)
    elseif command == 'reset' then
        ns.UI.ResetPosition()
        print(ns.L.RESET_DONE)
    elseif command == 'minimap' then
        if ns.UI.ToggleMinimap() then
            print(ns.L.MINIMAP_SHOWN)
        else
            print(ns.L.MINIMAP_HIDDEN)
        end
    elseif command == 'pattern' then
        RunPattern()
    else
        print(ns.L.UNKNOWN_COMMAND)
    end
end

function AskForever_Toggle()
    ns.UI.ToggleMain()
end

BINDING_HEADER_ASKFOREVER = 'AskForever'
BINDING_NAME_ASKFOREVER_TOGGLE = ns.L.BINDING_TOGGLE
