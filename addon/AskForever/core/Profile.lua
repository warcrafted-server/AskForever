local _, ns = ...

-- Resumen del personaje que viaja con cada pregunta: talentos aprendidos, profesiones, equipo y
-- estadísticas. Los nombres salen del propio cliente, así que ya vienen en el idioma del juego.
-- Cada lectura va protegida: si una función no existe o falla, ese apartado simplemente falta.

ns.Profile = {}

local MAX_TALENTS = 70

local function Protected(fn, ...)
    if type(fn) ~= 'function' then
        return nil
    end
    local ok, a, b, c, d, e, f, g, h, i, j, k = pcall(fn, ...)
    if ok then
        return a, b, c, d, e, f, g, h, i, j, k
    end
    return nil
end

local function Num(value)
    if type(value) == 'number' and value == value then
        return value
    end
    return nil
end

local function Round1(value)
    return math.floor(value * 10 + 0.5) / 10
end

local function SpellName(spellID)
    if type(spellID) ~= 'number' then
        return nil
    end
    if C_Spell and type(C_Spell.GetSpellName) == 'function' then
        local name = Protected(C_Spell.GetSpellName, spellID)
        if type(name) == 'string' and name ~= '' then
            return name
        end
    end
    if type(GetSpellInfo) == 'function' then
        local name = Protected(GetSpellInfo, spellID)
        if type(name) == 'string' and name ~= '' then
            return name
        end
    end
    return nil
end

-- Talentos aprendidos (rango > 0) del árbol activo, con el rango gastado en cada uno.
function ns.Profile.Talents()
    if not (C_ClassTalents and C_Traits
        and type(C_ClassTalents.GetActiveConfigID) == 'function') then
        return nil
    end
    local configID = Protected(C_ClassTalents.GetActiveConfigID)
    if type(configID) ~= 'number' then
        return nil
    end
    local config = Protected(C_Traits.GetConfigInfo, configID)
    if type(config) ~= 'table' or type(config.treeIDs) ~= 'table' then
        return nil
    end

    local found = {}
    for _, treeID in ipairs(config.treeIDs) do
        local nodes = Protected(C_Traits.GetTreeNodes, treeID)
        if type(nodes) == 'table' then
            for _, nodeID in ipairs(nodes) do
                local node = Protected(C_Traits.GetNodeInfo, configID, nodeID)
                if type(node) == 'table' and (Num(node.currentRank) or 0) > 0 then
                    local entryID = type(node.activeEntry) == 'table' and node.activeEntry.entryID
                        or (type(node.entryIDs) == 'table' and node.entryIDs[1])
                    local entry = entryID and Protected(C_Traits.GetEntryInfo, configID, entryID)
                    local definition = type(entry) == 'table' and entry.definitionID
                        and Protected(C_Traits.GetDefinitionInfo, entry.definitionID)
                    local name = type(definition) == 'table' and SpellName(definition.spellID)
                    if name then
                        found[#found + 1] = {
                            name = name,
                            rank = node.currentRank,
                            tree = Num(node.subTreeID) or treeID,
                            x = Num(node.posX) or 0,
                            y = Num(node.posY) or 0,
                        }
                    end
                end
            end
        end
    end
    if #found == 0 then
        return nil
    end

    table.sort(found, function(left, right)
        if left.tree ~= right.tree then
            return left.tree < right.tree
        end
        if left.y ~= right.y then
            return left.y < right.y
        end
        return left.x < right.x
    end)

    local list = {}
    for index = 1, math.min(#found, MAX_TALENTS) do
        list[#list + 1] = { found[index].name, found[index].rank }
    end
    return list
end

local function UnspentTalents()
    local value = Protected(GetNumUnspentTalents)
    return Num(value)
end

function ns.Profile.Professions()
    if type(GetProfessions) ~= 'function' or type(GetProfessionInfo) ~= 'function' then
        return nil
    end
    local indexes = { Protected(GetProfessions) }
    local list = {}
    for position = 1, 5 do
        local index = indexes[position]
        if type(index) == 'number' then
            local name, _, skill, maxSkill, _, _, _, _, _, _, lineName = Protected(GetProfessionInfo, index)
            local label = (type(lineName) == 'string' and lineName ~= '') and lineName or name
            if type(label) == 'string' and label ~= '' then
                list[#list + 1] = { label, Num(skill) or 0, Num(maxSkill) or 0 }
            end
        end
    end
    if #list == 0 then
        return nil
    end
    return list
end

function ns.Profile.Gear()
    if type(GetInventoryItemLink) ~= 'function' then
        return nil
    end
    local list = {}
    for slot = 1, 19 do
        local link = Protected(GetInventoryItemLink, 'player', slot)
        if type(link) == 'string' then
            local name = link:match('%[(.-)%]')
            if name and name ~= '' then
                list[#list + 1] = { slot, name }
            end
        end
    end
    if #list == 0 then
        return nil
    end
    return list
end

local function Percent(fn, ...)
    local value = Num(Protected(fn, ...))
    if value then
        return Round1(value)
    end
    return nil
end

local function AttackPower(fn)
    local base, positive, negative = Protected(fn, 'player')
    base = Num(base)
    if not base then
        return nil
    end
    return base + (Num(positive) or 0) + (Num(negative) or 0)
end

function ns.Profile.Stats()
    local stats = {
        hp = Num(Protected(UnitHealthMax, 'player')),
        power = Num(Protected(UnitPowerMax, 'player')),
        ap = AttackPower(UnitAttackPower),
        rap = AttackPower(UnitRangedAttackPower),
        crit = Percent(GetCritChance),
        rcrit = Percent(GetRangedCritChance),
        scrit = Percent(GetSpellCritChance, 2),
        dodge = Percent(GetDodgeChance),
        parry = Percent(GetParryChance),
        block = Percent(GetBlockChance),
    }
    local _, armor = Protected(UnitArmor, 'player')
    stats.armor = Num(armor)
    -- Fuerza, Agilidad, Aguante, Intelecto, Espíritu (valor total, con mejoras).
    local primary = {}
    for index = 1, 5 do
        local _, effective = Protected(UnitStat, 'player', index)
        primary[index] = Num(effective) or 0
    end
    stats.main = primary
    return stats
end

function ns.Profile.Collect()
    local profile = {}
    local talents = ns.Profile.Talents()
    local unspent = UnspentTalents()
    if talents or unspent then
        profile.tal = { list = talents, free = unspent }
    end
    profile.prof = ns.Profile.Professions()
    profile.gear = ns.Profile.Gear()
    profile.st = ns.Profile.Stats()
    if next(profile) == nil then
        return nil
    end
    return profile
end
