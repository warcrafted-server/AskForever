local _, ns = ...

-- Copia de los campos simples de la primera misión para descubrir los nombres reales de la API.
local function GetFirstQuestInfo()
    if type(C_QuestLog) ~= 'table' or type(C_QuestLog.GetInfo) ~= 'function' then
        return nil
    end
    local ok, info = pcall(C_QuestLog.GetInfo, 1)
    if not ok or type(info) ~= 'table' then
        return nil
    end

    local copy = {}
    for key, value in pairs(info) do
        local kind = type(value)
        if kind == 'string' or kind == 'number' or kind == 'boolean' then
            copy[key] = value
        end
    end
    return copy
end

-- Temporal: quitar antes de la release.
function AskForeverDebug(question)
    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end

    local okCollect, ctx = pcall(ns.Context.Collect)
    local errorMessage
    if not okCollect then
        errorMessage = tostring(ctx)
        ctx = nil
    end

    local okBuild, prompt = pcall(ns.Prompt.Build, question or 'test', ctx)
    if not okBuild then
        if errorMessage then
            errorMessage = errorMessage .. ' | ' .. tostring(prompt)
        else
            errorMessage = tostring(prompt)
        end
        prompt = nil
    end

    local interfaceVersion
    if type(GetBuildInfo) == 'function' then
        interfaceVersion = select(4, GetBuildInfo())
    end

    AskForeverDB.debug = {
        time = date('%Y-%m-%d %H:%M:%S'),
        api = {
            C_QuestLog = C_QuestLog ~= nil,
            C_Map = C_Map ~= nil,
            interface = interfaceVersion,
        },
        ctx = ctx,
        prompt = prompt,
        firstQuestInfo = GetFirstQuestInfo(),
        error = errorMessage,
    }

    print(ns.L.DEBUG_SAVED)
end
