local _, ns = ...

ns.Transport = {}

local Transport = ns.Transport

local MAX_PAYLOAD = 749
local COLS = 128
local MAX_ROWS = 8
local PROTOCOL_VERSION = 1
local TICKER_INTERVAL = 0.2
local MIN_STEPS = 10
local LOOPS = 3
-- Equivalente a 0xEDB88320 como entero de 32 bits con signo (librería bit del juego).
local CRC_POLYNOMIAL = -306674912
local HEX_DIGITS = '0123456789abcdef'

local state = {
    pages = nil,
    step = 0,
    totalSteps = 0,
    ticker = nil,
    paused = false,
    pending = nil,
}

local CRC_TABLE

local function GetCrcTable()
    if CRC_TABLE then
        return CRC_TABLE
    end
    CRC_TABLE = {}
    for index = 0, 255 do
        local crc = index
        for _ = 1, 8 do
            if bit.band(crc, 1) == 1 then
                crc = bit.bxor(bit.rshift(crc, 1), CRC_POLYNOMIAL)
            else
                crc = bit.rshift(crc, 1)
            end
        end
        CRC_TABLE[index] = crc
    end
    return CRC_TABLE
end

function Transport.CRC32(str)
    local table_ = GetCrcTable()
    local crc = bit.bnot(0)
    for index = 1, #str do
        local byte = str:byte(index)
        crc = bit.bxor(bit.rshift(crc, 8), table_[bit.band(bit.bxor(crc, byte), 255)])
    end
    return bit.bnot(crc) % 4294967296
end

local function U16(value)
    return string.char(math.floor(value / 256) % 256, value % 256)
end

local function U32(value)
    return string.char(
        math.floor(value / 16777216) % 256,
        math.floor(value / 65536) % 256,
        math.floor(value / 256) % 256,
        value % 256
    )
end

function Transport.EncodeFrame(msgId, page, pages, payload)
    if #payload > MAX_PAYLOAD then
        error('frame payload too large')
    end
    local body = 'AF'
        .. string.char(PROTOCOL_VERSION)
        .. U16(msgId)
        .. string.char(page % 256, pages % 256)
        .. U16(#payload)
        .. payload
    return body .. U32(Transport.CRC32(body))
end

function Transport.BytesToSymbols(str)
    local symbols = {}
    local buffer = 0
    local bits = 0
    for index = 1, #str do
        buffer = buffer * 256 + str:byte(index)
        bits = bits + 8
        while bits >= 6 do
            bits = bits - 6
            local divisor = 2 ^ bits
            symbols[#symbols + 1] = math.floor(buffer / divisor) % 64
            buffer = buffer % divisor
        end
    end
    if bits > 0 then
        symbols[#symbols + 1] = buffer * 2 ^ (6 - bits) % 64
    end
    return symbols
end

local function RowsFor(symbolCount)
    local rows = math.ceil((8 + symbolCount) / COLS)
    if rows < 1 then
        return 1
    elseif rows > MAX_ROWS then
        return MAX_ROWS
    end
    return rows
end

function Transport.Paginate(message, msgId)
    if message == nil or #message == 0 then
        return nil, 'EMPTY'
    end
    local total = math.ceil(#message / MAX_PAYLOAD)
    if total > 255 then
        return nil, 'TOO_LONG'
    end

    local pages = {}
    for index = 0, total - 1 do
        local start = index * MAX_PAYLOAD + 1
        local chunk = message:sub(start, start + MAX_PAYLOAD - 1)
        local frame = Transport.EncodeFrame(msgId, index, total, chunk)
        local symbols = Transport.BytesToSymbols(frame)
        pages[#pages + 1] = { symbols = symbols, rows = RowsFor(#symbols) }
    end
    return pages
end

local function Round1(value)
    if type(value) ~= 'number' then
        return value
    end
    return math.floor(value * 10 + 0.5) / 10
end

function Transport.BuildMessage(question, ctx)
    ctx = ctx or {}

    local context = {}
    if ctx.level ~= nil then
        context.lvl = ctx.level
    end
    if ctx.race ~= nil then
        context.race = ctx.race
    end
    if ctx.class ~= nil then
        context.class = ctx.class
    end
    if ctx.faction ~= nil then
        context.fac = ctx.faction
    end
    if ctx.zone ~= nil then
        context.zone = ctx.zone
    end
    if ctx.subzone ~= nil then
        context.sub = ctx.subzone
    end
    if ctx.x ~= nil then
        context.x = Round1(ctx.x)
    end
    if ctx.y ~= nil then
        context.y = Round1(ctx.y)
    end
    if ctx.mapID ~= nil then
        context.map = ctx.mapID
    end

    if type(ctx.quests) == 'table' and #ctx.quests > 0 then
        local quests = {}
        local limit = math.min(#ctx.quests, 30)
        for index = 1, limit do
            local quest = ctx.quests[index]
            quests[#quests + 1] = {
                quest.title or ns.Json.null,
                quest.level ~= nil and quest.level or ns.Json.null,
                quest.complete and 1 or 0,
            }
        end
        context.quests = quests
    end

    return ns.Json.Encode({
        v = 1,
        lang = GetLocale(),
        q = question or '',
        ctx = context,
    })
end

function Transport.ToHex(str)
    local out = {}
    for index = 1, #str do
        local byte = str:byte(index)
        local high = math.floor(byte / 16) + 1
        local low = byte % 16 + 1
        out[#out + 1] = HEX_DIGITS:sub(high, high) .. HEX_DIGITS:sub(low, low)
    end
    return table.concat(out)
end

local function ShowPage()
    if not state.pages then
        return
    end
    local page = state.pages[state.step % #state.pages + 1]
    ns.Strip.Show(page.symbols, page.rows)
end

local function Finish()
    if state.ticker then
        state.ticker:Cancel()
        state.ticker = nil
    end
    state.pages = nil
    state.step = 0
    state.totalSteps = 0
    state.paused = false
    ns.Strip.Hide()
end

function Transport.Cancel()
    state.pending = nil
    Finish()
end

function Transport.IsBusy()
    return state.pages ~= nil
end

function Transport.Send(question, ctx)
    if InCombatLockdown() then
        state.pending = { question = question, ctx = ctx }
        return true
    end

    Transport.Cancel()

    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    AskForeverDB.transport = AskForeverDB.transport or { msgId = 0 }
    local msgId = (AskForeverDB.transport.msgId or 0) + 1
    if msgId > 65535 then
        msgId = 1
    end
    AskForeverDB.transport.msgId = msgId

    if ctx == nil then
        ctx = ns.Context.Collect()
    end

    local message = Transport.BuildMessage(question, ctx)
    local pages, reason = Transport.Paginate(message, msgId)
    if not pages then
        state.pending = nil
        return nil, reason
    end

    state.pages = pages
    state.totalSteps = math.max(#pages * LOOPS, MIN_STEPS)
    state.step = 0
    state.paused = false
    ShowPage()

    state.ticker = C_Timer.NewTicker(TICKER_INTERVAL, function()
        if not state.pages or state.paused then
            return
        end
        state.step = state.step + 1
        if state.step >= state.totalSteps then
            Finish()
            return
        end
        ShowPage()
    end)

    state.pending = nil
    return true
end

local eventFrame = CreateFrame('Frame')
eventFrame:RegisterEvent('PLAYER_REGEN_DISABLED')
eventFrame:RegisterEvent('PLAYER_REGEN_ENABLED')
eventFrame:SetScript('OnEvent', function(_, event)
    if event == 'PLAYER_REGEN_DISABLED' then
        if state.pages then
            state.paused = true
            ns.Strip.Hide()
        end
    elseif event == 'PLAYER_REGEN_ENABLED' then
        local pending = state.pending
        state.pending = nil
        if pending then
            Transport.Send(pending.question, pending.ctx)
        elseif state.pages and state.paused then
            state.paused = false
            ShowPage()
        end
    end
end)
