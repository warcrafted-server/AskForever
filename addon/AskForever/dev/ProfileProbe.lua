local _, ns = ...

-- Solo desarrollo: guarda en AskForeverDB.diag.perfil qué datos del personaje ofrece este cliente
-- (talentos, profesiones, equipo, estadísticas, hechizos, reputaciones, Legacy) para leerlo tras /reload.
-- Uso: /afperfil

local function Try(fn, ...)
    if type(fn) ~= 'function' then
        return nil, 'sin-funcion'
    end
    local results = { pcall(fn, ...) }
    if not results[1] then
        return nil, 'error: ' .. tostring(results[2]):sub(1, 80)
    end
    table.remove(results, 1)
    return results
end

-- Valores planos (SavedVariables no guarda funciones ni referencias a tablas del cliente).
local function Flat(list, max)
    local out = {}
    for i = 1, math.min(#list, max or 12) do
        local v = list[i]
        local t = type(v)
        if t == 'string' or t == 'number' or t == 'boolean' then
            out[#out + 1] = v
        elseif v == nil then
            out[#out + 1] = '<nil>'
        else
            out[#out + 1] = '<' .. t .. '>'
        end
    end
    return out
end

local function Call(name, ...)
    local fn = _G[name]
    if fn == nil then
        local space, member = name:match('^([%w_]+)%.([%w_]+)$')
        fn = space and type(_G[space]) == 'table' and _G[space][member] or nil
    end
    local results, err = Try(fn, ...)
    if results then
        return Flat(results)
    end
    return err
end

local function NamesLike(source, patterns, limit)
    local found = {}
    for key in pairs(source) do
        if type(key) == 'string' then
            for _, pattern in ipairs(patterns) do
                if key:find(pattern) then
                    found[#found + 1] = key
                    break
                end
            end
        end
    end
    table.sort(found)
    while #found > limit do
        table.remove(found)
    end
    return found
end

local function Talents()
    local out = { tabs = {} }
    local tabs = Try(GetNumTalentTabs)
    out.numTabs = tabs and Flat(tabs) or 'sin-funcion'
    local count = tabs and tonumber(tabs[1]) or 0
    for tab = 1, math.min(count, 4) do
        local info = Call('GetTalentTabInfo', tab)
        local entry = { info = info, talents = {} }
        local num = Try(GetNumTalents, tab)
        entry.numTalents = num and Flat(num) or 'sin-funcion'
        local total = num and tonumber(num[1]) or 0
        for index = 1, math.min(total, 40) do
            local talent = Call('GetTalentInfo', tab, index)
            if type(talent) == 'table' and (tonumber(talent[5]) or 0) > 0 then
                entry.talents[#entry.talents + 1] = { index, talent[1], talent[5], talent[6] }
            end
        end
        out.tabs[#out.tabs + 1] = entry
    end
    out.unspent = Call('GetUnspentTalentPoints')
    out.classTalents = {
        activeConfig = C_ClassTalents and Call('C_ClassTalents.GetActiveConfigID') or 'sin-C_ClassTalents',
        globals = NamesLike(_G, { 'Talent' }, 40),
    }
    return out
end

local function Keys(value, limit)
    local out = {}
    if type(value) ~= 'table' then
        return tostring(value)
    end
    for key, item in pairs(value) do
        local kind = type(item)
        out[tostring(key)] = (kind == 'string' or kind == 'number' or kind == 'boolean') and item or ('<' .. kind .. '>')
        limit = limit - 1
        if limit <= 0 then
            break
        end
    end
    return out
end

-- Estructura de C_Traits tal como la devuelve este cliente (solo claves y valores sencillos).
local function RawTraits()
    local out = {}
    if not (C_ClassTalents and C_Traits) then
        return 'sin-C_Traits'
    end
    local okId, configID = pcall(C_ClassTalents.GetActiveConfigID)
    out.configID = okId and configID or 'error'
    local okCfg, config = pcall(C_Traits.GetConfigInfo, configID)
    out.config = okCfg and Keys(config, 20) or 'error'
    local treeID = okCfg and type(config) == 'table' and type(config.treeIDs) == 'table' and config.treeIDs[1]
    out.treeIDs = okCfg and type(config) == 'table' and config.treeIDs or nil
    if treeID then
        local okTree, nodes = pcall(C_Traits.GetTreeNodes, treeID)
        out.numNodes = okTree and type(nodes) == 'table' and #nodes or 'error'
        out.treeInfo = Call('C_Traits.GetTreeInfo', configID, treeID)
        out.sampleNodes = {}
        if okTree and type(nodes) == 'table' then
            for index = 1, math.min(#nodes, 3) do
                local okNode, node = pcall(C_Traits.GetNodeInfo, configID, nodes[index])
                out.sampleNodes[index] = okNode and Keys(node, 30) or 'error'
            end
        end
    end
    return out
end

local function Professions()
    local out = {}
    out.getProfessions = Call('GetProfessions')
    local lines = {}
    local numLines = Try(GetNumSkillLines)
    out.numSkillLines = numLines and Flat(numLines) or 'sin-funcion'
    for index = 1, math.min(numLines and tonumber(numLines[1]) or 0, 40) do
        local info = Call('GetSkillLineInfo', index)
        if type(info) == 'table' then
            lines[#lines + 1] = Flat(info, 8)
        end
    end
    out.skillLines = lines
    out.tradeSkillUI = C_TradeSkillUI and NamesLike(C_TradeSkillUI, { '.' }, 30) or 'sin-C_TradeSkillUI'
    return out
end

local function Gear()
    local items = {}
    for slot = 1, 19 do
        local link = Call('GetInventoryItemLink', 'player', slot)
        local id = Call('GetInventoryItemID', 'player', slot)
        if type(link) == 'table' and link[1] ~= '<nil>' or type(id) == 'table' and id[1] ~= '<nil>' then
            items[#items + 1] = { slot, link, id }
        end
    end
    return {
        slots = items,
        averageItemLevel = Call('GetAverageItemLevel'),
        durability = Call('GetInventoryItemDurability', 1),
    }
end

local function Stats()
    local out = {}
    for _, name in ipairs({ 'UnitHealthMax', 'UnitPowerMax', 'UnitArmor', 'UnitAttackPower',
        'UnitRangedAttackPower', 'GetCritChance', 'GetRangedCritChance', 'GetSpellCritChance',
        'GetDodgeChance', 'GetParryChance', 'GetBlockChance', 'GetCombatRating' }) do
        out[name] = Call(name, 'player')
    end
    out.stats = {}
    for stat = 1, 5 do
        out.stats[stat] = Call('UnitStat', 'player', stat)
    end
    return out
end

local function Spells()
    local out = {}
    local tabs = Try(GetNumSpellTabs)
    out.numTabs = tabs and Flat(tabs) or 'sin-funcion'
    out.tabs = {}
    for tab = 1, math.min(tabs and tonumber(tabs[1]) or 0, 8) do
        out.tabs[#out.tabs + 1] = Call('GetSpellTabInfo', tab)
    end
    out.spellBook = C_SpellBook and NamesLike(C_SpellBook, { '.' }, 30) or 'sin-C_SpellBook'
    return out
end

local function Reputations()
    local out = {}
    local num = Try(GetNumFactions)
    out.numFactions = num and Flat(num) or 'sin-funcion'
    out.sample = {}
    for index = 1, math.min(num and tonumber(num[1]) or 0, 12) do
        out.sample[#out.sample + 1] = Call('GetFactionInfo', index)
    end
    return out
end

local function Probe()
    local sample = { time = date('%H:%M:%S') }
    sample.player = {
        level = Call('UnitLevel', 'player'), class = Call('UnitClass', 'player'),
        race = Call('UnitRace', 'player'), build = Call('GetBuildInfo'),
        guild = Call('GetGuildInfo', 'player'),
    }
    -- Lo que enviaría el addon de verdad, y la estructura cruda de talentos para corregirlo si falla.
    if ns.Profile then
        local ok, collected = pcall(ns.Profile.Collect)
        sample.collector = ok and collected or ('error: ' .. tostring(collected))
        sample.talentList = select(2, pcall(ns.Profile.Talents))
    end
    sample.traits = RawTraits()
    sample.talents = Talents()
    sample.professions = Professions()
    sample.gear = Gear()
    sample.stats = Stats()
    sample.spells = Spells()
    sample.reputations = Reputations()
    -- Dónde vive Legacy en este cliente: solo nombres, para ver si hay una API que leer.
    sample.legacy = {
        globals = NamesLike(_G, { '[Ll]egacy' }, 60),
        pet = Call('UnitCreatureFamily', 'pet'),
    }

    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    AskForeverDB.diag = AskForeverDB.diag or {}
    AskForeverDB.diag.perfil = sample
    print('AskForever: datos del personaje guardados para el sondeo. Haz /reload para escribirlos.')
end

SLASH_ASKFOREVERPERFIL1 = '/afperfil'
SlashCmdList.ASKFOREVERPERFIL = function()
    local ok, err = pcall(Probe)
    if not ok then
        print('AskForever: el sondeo falló: ' .. tostring(err))
    end
end
