local _, ns = ...

ns.Prompt = {}

local function IsEmpty(value)
    return value == nil or value == ''
end

-- Función pura: solo usa ns.L y los argumentos, nunca la API del juego.
function ns.Prompt.Build(question, ctx, opts)
    ctx = ctx or {}
    opts = opts or {}

    local L = ns.L
    local context = {}

    local function Add(key, value)
        if not IsEmpty(value) then
            context[#context + 1] = L[key]:format(value)
        end
    end

    Add('CTX_LEVEL', ctx.level)
    Add('CTX_RACE', ctx.race)
    Add('CTX_CLASS', ctx.class)
    Add('CTX_FACTION', ctx.faction)

    local zone = ctx.zone
    if not IsEmpty(ctx.subzone) and ctx.subzone ~= zone then
        if IsEmpty(zone) then
            zone = ctx.subzone
        else
            zone = zone .. ' - ' .. ctx.subzone
        end
    end
    Add('CTX_ZONE', zone)

    if ctx.x ~= nil and ctx.y ~= nil then
        context[#context + 1] = L.CTX_COORDS:format(ctx.x, ctx.y)
    end

    if opts.includeQuests ~= false and type(ctx.quests) == 'table' and #ctx.quests > 0 then
        context[#context + 1] = L.CTX_QUESTS
        for _, quest in ipairs(ctx.quests) do
            local line = quest.complete and '- [x] ' or '- [ ] '
            line = line .. tostring(quest.title)
            if quest.level ~= nil then
                line = line .. ' (' .. tostring(quest.level) .. ')'
            end
            context[#context + 1] = line
        end
    end

    local blocks = { L.PROMPT_INSTRUCTION }
    if #context > 0 then
        blocks[#blocks + 1] = table.concat(context, '\n')
    end
    blocks[#blocks + 1] = L.PROMPT_QUESTION:format(question or '')
    return table.concat(blocks, '\n\n')
end
