local _, ns = ...

ns.Context = {}

local MAX_QUESTS = 30

-- No se sabe qué API trae este cliente, así que cada llamada va protegida.
local function Protected(fn, ...)
    if type(fn) ~= 'function' then
        return nil
    end
    local ok, result = pcall(fn, ...)
    if ok then
        return result
    end
    return nil
end

local function Round1(value)
    return math.floor(value * 10 + 0.5) / 10
end

local function CollectPosition()
    if not (C_Map and type(C_Map.GetBestMapForUnit) == 'function'
        and type(C_Map.GetPlayerMapPosition) == 'function') then
        return nil, nil, nil
    end

    local mapID = Protected(C_Map.GetBestMapForUnit, 'player')
    if type(mapID) ~= 'number' then
        return nil, nil, nil
    end

    local position = Protected(C_Map.GetPlayerMapPosition, mapID, 'player')
    local ok, x, y = pcall(function()
        return position:GetXY()
    end)
    -- (0, 0) es lo que devuelve el cliente cuando todavía no conoce la posición.
    if not ok or type(x) ~= 'number' or type(y) ~= 'number' or (x == 0 and y == 0) then
        return nil, nil, mapID
    end

    return Round1(x * 100), Round1(y * 100), mapID
end

local function ReadClassicQuest(index)
    if type(GetQuestLogTitle) ~= 'function' then
        return nil
    end
    -- Devuelve title, level, suggestedGroup, isHeader, isCollapsed, isComplete, ...
    local results = { pcall(GetQuestLogTitle, index) }
    if not results[1] then
        return nil
    end
    return {
        title = results[2],
        level = results[3],
        isHeader = results[5],
        complete = results[7] and true or false,
        id = results[9],
    }
end

local function CollectQuests()
    local quests = {}
    local useNewApi = C_QuestLog ~= nil and type(C_QuestLog.GetNumQuestLogEntries) == 'function'
    local total

    if useNewApi then
        total = Protected(C_QuestLog.GetNumQuestLogEntries)
    else
        total = Protected(GetNumQuestLogEntries)
    end

    if type(total) ~= 'number' then
        return quests
    end

    for index = 1, total do
        if #quests >= MAX_QUESTS then
            break
        end

        local entry
        if useNewApi then
            local info = Protected(C_QuestLog.GetInfo, index)
            if type(info) == 'table' then
                entry = {
                    title = info.title,
                    level = info.level or info.questLevel,
                    complete = info.isComplete and true or false,
                    isHeader = info.isHeader,
                    isHidden = info.isHidden,
                    id = info.questID,
                }
            end
        else
            entry = ReadClassicQuest(index)
        end

        if entry and not entry.isHeader and not entry.isHidden
            and type(entry.title) == 'string' and entry.title ~= '' then
            quests[#quests + 1] = {
                title = entry.title,
                level = entry.level,
                complete = entry.complete,
                id = entry.id,
            }
        end
    end

    return quests
end

function ns.Context.Collect()
    local x, y, mapID = CollectPosition()

    local zone = Protected(GetRealZoneText)
    if zone == nil or zone == '' then
        zone = Protected(GetZoneText)
    end

    -- UnitFactionGroup devuelve (nombre en inglés, nombre localizado): nos quedamos con el segundo.
    local faction
    if type(UnitFactionGroup) == 'function' then
        local ok, englishName, localizedName = pcall(UnitFactionGroup, 'player')
        if ok then
            faction = localizedName or englishName
        end
    end

    local knownFlights
    if ns.Flights and type(ns.Flights.KnownIds) == 'function' then
        local ok, ids = pcall(ns.Flights.KnownIds)
        if ok then
            knownFlights = ids
        end
    end

    local profile
    if ns.Profile and type(ns.Profile.Collect) == 'function' then
        local ok, result = pcall(ns.Profile.Collect)
        if ok then
            profile = result
        end
    end

    return {
        profile = profile,
        level = Protected(UnitLevel, 'player'),
        race = Protected(UnitRace, 'player'),
        class = Protected(UnitClass, 'player'),
        faction = faction,
        zone = zone,
        subzone = Protected(GetSubZoneText),
        x = x,
        y = y,
        mapID = mapID,
        quests = CollectQuests(),
        knownFlights = knownFlights,
    }
end
