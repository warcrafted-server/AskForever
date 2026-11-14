local _, ns = ...

ns.Flights = {}

local MAX_DEBUG_NODES = 200

-- El cliente es una versión clásica moderna y no se sabe qué API de taxi trae:
-- todas las llamadas van protegidas.
local function SafeCall(fn, ...)
    if type(fn) ~= 'function' then
        return nil
    end
    local ok, result = pcall(fn, ...)
    if ok then
        return result
    end
    return nil
end

local function CharacterKey()
    local name = SafeCall(UnitName, 'player')
    if type(name) ~= 'string' or name == '' then
        return nil
    end
    local realm = SafeCall(GetRealmName)
    if type(realm) ~= 'string' then
        realm = ''
    end
    return name .. '-' .. realm
end

local function CountKeys(tbl)
    local total = 0
    for _ in pairs(tbl) do
        total = total + 1
    end
    return total
end

local function EnsureRecord()
    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    if type(AskForeverDB.flights) ~= 'table' then
        AskForeverDB.flights = {}
    end
    local key = CharacterKey()
    if not key then
        return nil
    end
    local record = AskForeverDB.flights[key]
    if type(record) ~= 'table' then
        record = {}
        AskForeverDB.flights[key] = record
    end
    if type(record.ids) ~= 'table' then
        record.ids = {}
    end
    if type(record.names) ~= 'table' then
        record.names = {}
    end
    return record
end

local function TaxiMapID()
    if type(C_TaxiMap) == 'table' and type(C_TaxiMap.GetTaxiMapID) == 'function' then
        local mapID = SafeCall(C_TaxiMap.GetTaxiMapID)
        if type(mapID) == 'number' then
            return mapID
        end
    end
    local mapID = SafeCall(GetTaxiMapID)
    if type(mapID) == 'number' then
        return mapID
    end
    return nil
end

local function FlightStates()
    if type(Enum) == 'table' and type(Enum.FlightPathState) == 'table' then
        return Enum.FlightPathState.Current or 0, Enum.FlightPathState.Reachable or 1
    end
    return 0, 1
end

local function ReadMethodA()
    if type(C_TaxiMap) ~= 'table'
        or type(C_TaxiMap.GetAllTaxiNodes) ~= 'function' then
        return nil
    end
    local mapID = TaxiMapID()
    if type(mapID) ~= 'number' then
        return nil
    end
    local nodes = SafeCall(C_TaxiMap.GetAllTaxiNodes, mapID)
    if type(nodes) ~= 'table' then
        return nil
    end
    local current, reachable = FlightStates()
    local debugNodes = {}
    local known = {}
    local found = 0
    for _, node in pairs(nodes) do
        if type(node) == 'table' then
            found = found + 1
            local nodeID = node.nodeID
            local name = node.name
            local state = node.state
            if #debugNodes < MAX_DEBUG_NODES then
                debugNodes[#debugNodes + 1] = {
                    id = type(nodeID) == 'number' and nodeID or nil,
                    name = type(name) == 'string' and name or nil,
                    state = state,
                }
            end
            if type(nodeID) == 'number'
                and (state == current or state == reachable) then
                known[#known + 1] = { id = nodeID, name = name }
            end
        end
    end
    if found == 0 then
        return nil
    end
    return { mapID = mapID, nodes = debugNodes, known = known }
end

local function ReadMethodB()
    if type(NumTaxiNodes) ~= 'function'
        or type(TaxiNodeGetType) ~= 'function'
        or type(TaxiNodeName) ~= 'function' then
        return nil
    end
    local total = SafeCall(NumTaxiNodes)
    if type(total) ~= 'number' then
        return nil
    end
    local debugNodes = {}
    local known = {}
    for index = 1, total do
        local nodeType = SafeCall(TaxiNodeGetType, index)
        local name = SafeCall(TaxiNodeName, index)
        if #debugNodes < MAX_DEBUG_NODES then
            debugNodes[#debugNodes + 1] = {
                id = index,
                name = type(name) == 'string' and name or nil,
                state = nodeType,
            }
        end
        if nodeType == 'CURRENT' or nodeType == 'REACHABLE' then
            known[#known + 1] = { name = name }
        end
    end
    return { mapID = TaxiMapID(), nodes = debugNodes, known = known }
end

local function SaveDebug(method, result)
    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    local now = SafeCall(time)
    if type(now) ~= 'number' then
        now = 0
    end
    AskForeverDB.flightsDebug = {
        method = method,
        time = now,
        mapID = result and result.mapID or nil,
        nodes = result and result.nodes or {},
    }
end

local function AddKnown(record, known)
    local added = 0
    for _, point in ipairs(known) do
        local nodeID = point.id
        local name = point.name
        local newPoint = false
        if type(nodeID) == 'number' and not record.ids[nodeID] then
            record.ids[nodeID] = true
            newPoint = true
        end
        if type(name) == 'string' and name ~= '' and not record.names[name] then
            record.names[name] = true
            if type(nodeID) ~= 'number' then
                newPoint = true
            end
        end
        if newPoint then
            added = added + 1
        end
    end
    return added
end

local function TotalKnown(record, method)
    if method == 'A' then
        return CountKeys(record.ids)
    end
    return CountKeys(record.names)
end

function ns.Flights.KnownIds()
    local key = CharacterKey()
    if not key or type(AskForeverDB) ~= 'table'
        or type(AskForeverDB.flights) ~= 'table' then
        return nil
    end
    local record = AskForeverDB.flights[key]
    if type(record) ~= 'table' or type(record.ids) ~= 'table' then
        return nil
    end
    local ids = {}
    for nodeID, known in pairs(record.ids) do
        if known and type(nodeID) == 'number' then
            ids[#ids + 1] = nodeID
        end
    end
    if #ids == 0 then
        return nil
    end
    table.sort(ids)
    return ids
end

local frame = CreateFrame('Frame')
frame:RegisterEvent('TAXIMAP_OPENED')
frame:SetScript('OnEvent', function()
    local record = EnsureRecord()
    local method = 'A'
    local result = ReadMethodA()
    if not result then
        method = 'B'
        result = ReadMethodB()
    end
    if not result then
        method = 'none'
    end
    SaveDebug(method, result)
    if not record or not result then
        return
    end
    local added = AddKnown(record, result.known)
    if added > 0 then
        local template = ns.L and ns.L.FLIGHTS_SAVED
        if type(template) == 'string' then
            print(template:format(TotalKnown(record, method)))
        end
    end
end)
