local _, ns = ...

SLASH_ASKFOREVER1 = '/askforever'
SLASH_ASKFOREVER2 = '/af'

SlashCmdList.ASKFOREVER = function(msg)
    local command = string.lower((msg or ''):match('^%s*(.-)%s*$'))

    if command == '' then
        ns.UI.ToggleMain()
    elseif command == 'help' then
        print(ns.L.HELP_TITLE)
        print(ns.L.HELP_OPEN)
        print(ns.L.HELP_RESET)
        print(ns.L.HELP_HELP)
    elseif command == 'reset' then
        ns.UI.ResetPosition()
        print(ns.L.RESET_DONE)
    else
        print(ns.L.UNKNOWN_COMMAND)
    end
end

function AskForever_Toggle()
    ns.UI.ToggleMain()
end

BINDING_HEADER_ASKFOREVER = 'AskForever'
BINDING_NAME_ASKFOREVER_TOGGLE = ns.L.BINDING_TOGGLE
