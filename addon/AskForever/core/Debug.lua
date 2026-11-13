local _, ns = ...

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
        error = errorMessage,
    }

    print(ns.L.DEBUG_SAVED)
end
