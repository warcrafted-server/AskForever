local _, ns = ...

ns.SlotSpike = {}

local SLOT_MIN = 1
local SLOT_MAX = 999
local PROBE_DELAY = 0.5
local DATA_TEXT_LIMIT = 200
local CHAT_TEXT_LIMIT = 60

local probeFrame

local function ValidSlot(k)
    return type(k) == 'number' and k >= SLOT_MIN and k <= SLOT_MAX
        and k == math.floor(k)
end

local function EnsureSlot(k)
    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    if type(AskForeverDB.diag) ~= 'table' then
        AskForeverDB.diag = {}
    end
    if type(AskForeverDB.diag.slots) ~= 'table' then
        AskForeverDB.diag.slots = {}
    end
    local slot = AskForeverDB.diag.slots[k]
    if type(slot) ~= 'table' then
        slot = {}
        AskForeverDB.diag.slots[k] = slot
    end
    if type(slot.probes) ~= 'table' then
        slot.probes = {}
    end
    if type(slot.tests) ~= 'table' then
        slot.tests = {}
    end
    return slot
end

local function EnsureProbeFrame()
    if probeFrame == nil then
        probeFrame = CreateFrame('Frame')
        probeFrame:Hide()
    end
    return probeFrame
end

local function TextCall(fn, ...)
    if type(fn) ~= 'function' then
        return 'n/a'
    end
    local ok, first = pcall(fn, ...)
    if not ok then
        return 'error: ' .. tostring(first)
    end
    return tostring(first)
end

local function PcallValues(fn, ...)
    local values = {}
    if type(fn) ~= 'function' then
        return false, values
    end
    local ok, first, second = pcall(fn, ...)
    if first ~= nil then
        values[#values + 1] = tostring(first)
    end
    if second ~= nil then
        values[#values + 1] = tostring(second)
    end
    return ok, values
end

local function SetTextureText(ok, values)
    if not ok then
        return 'error: ' .. tostring(values[1] or '?')
    end
    if #values == 0 then
        return 'ok'
    end
    return 'ok: ' .. table.concat(values, ', ')
end

local function Probe(k, callback)
    local frame = EnsureProbeFrame()
    local texture = frame:CreateTexture()
    if texture.SetSize then
        -- Una textura sin tamaño no intenta cargar el archivo: la sonda no diría nada.
        pcall(texture.SetSize, texture, 16, 16)
    end

    local path = 'Interface\\AddOns\\AskForever_Signals\\ready_'
        .. string.format('%03d', k) .. '.tga'
    local setOk, setValues = PcallValues(texture.SetTexture, texture, path)
    local result = {
        setTexture = {
            ok = setOk,
            values = setValues,
            text = SetTextureText(setOk, setValues),
        },
        getTexture = TextCall(texture.GetTexture, texture),
        fileId = TextCall(texture.GetTextureFileID, texture),
        filePath = TextCall(texture.GetTextureFilePath, texture),
        loadedNow = TextCall(texture.IsObjectLoaded, texture),
        loadedLater = 'n/a',
        width = 'n/a',
        height = 'n/a',
    }

    local function Finish()
        result.loadedLater = TextCall(texture.IsObjectLoaded, texture)
        result.width = TextCall(texture.GetWidth, texture)
        result.height = TextCall(texture.GetHeight, texture)
        callback(result)
    end

    local scheduled = false
    if C_Timer and type(C_Timer.After) == 'function' then
        scheduled = pcall(C_Timer.After, PROBE_DELAY, Finish)
    end
    if not scheduled then
        Finish()
    end
end

function ns.SlotSpike.ProbeCmd(k)
    if not ValidSlot(k) then
        print(ns.L.SLOT_BAD_ARG)
        return
    end
    local slot = EnsureSlot(k)
    Probe(k, function(result)
        result.time = date('%H:%M:%S')
        table.insert(slot.probes, result)
        print(ns.L.SLOT_PROBE_RESULT:format(tostring(k), result.setTexture.text,
            result.fileId, result.loadedLater))
    end)
end

local function ApiFunction(name)
    if type(C_AddOns) == 'table' and type(C_AddOns[name]) == 'function' then
        return C_AddOns[name]
    end
    if name == 'GetAddOnInfo' then
        return GetAddOnInfo
    end
    if name == 'IsAddOnLoaded' then
        return IsAddOnLoaded
    end
    if name == 'LoadAddOn' then
        return LoadAddOn
    end
    return nil
end

local function AddonInfoText(name)
    local fn = ApiFunction('GetAddOnInfo')
    if type(fn) ~= 'function' then
        return { 'n/a' }
    end
    local ok, a, b, c, d, e, f, g = pcall(fn, name)
    local values = { a, b, c, d, e, f, g }
    local info = {}
    if not ok then
        info[1] = 'error: ' .. tostring(a)
        return info
    end
    for index = 1, 7 do
        info[index] = tostring(values[index])
    end
    return info
end

local function LoadSlotAddon(name)
    local fn = ApiFunction('LoadAddOn')
    if type(fn) ~= 'function' then
        return 'n/a', 'n/a'
    end
    local ok, first, second = pcall(fn, name)
    if not ok then
        return 'false', 'error: ' .. tostring(first)
    end
    return tostring(first), tostring(second)
end

local function CopySlotData(k)
    if type(AskForeverSlotData) ~= 'table' then
        return 'nil'
    end
    local source = AskForeverSlotData[k]
    if type(source) ~= 'table' then
        return 'nil'
    end
    return {
        state = tostring(source.state),
        text = tostring(source.text):sub(1, DATA_TEXT_LIMIT),
        written = source.written,
    }
end

function ns.SlotSpike.TestCmd(k)
    if not ValidSlot(k) then
        print(ns.L.SLOT_BAD_ARG)
        return
    end
    local slot = EnsureSlot(k)
    Probe(k, function(probe)
        local name = 'AskForever_Slot' .. string.format('%03d', k)
        local before = {
            isLoaded = TextCall(ApiFunction('IsAddOnLoaded'), name),
            info = AddonInfoText(name),
        }
        local loaded, reason = LoadSlotAddon(name)
        local after = {
            isLoaded = TextCall(ApiFunction('IsAddOnLoaded'), name),
        }
        local data = CopySlotData(k)
        local state = 'nil'
        local text = 'nil'
        if type(data) == 'table' then
            state = data.state
            text = data.text
        end
        table.insert(slot.tests, {
            time = date('%H:%M:%S'),
            probe = probe,
            before = before,
            loaded = loaded,
            reason = reason,
            after = after,
            data = data,
        })
        print(ns.L.SLOT_TEST_RESULT:format(tostring(k), loaded, reason, state,
            text:sub(1, CHAT_TEXT_LIMIT)))
    end)
end
