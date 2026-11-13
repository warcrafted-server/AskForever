local _, ns = ...

ns.Strip = {}

local STRIP_COLUMNS = 128
local BLOCK_SIZE = 4
local MAX_ROWS = 8
local SYNC_SYMBOLS = { 0, 21, 42, 63, 51, 12, 51, 12 }

local frame
local textures = {}

local function Normalize(symbol)
    if type(symbol) ~= 'number' then
        return 0
    end
    symbol = math.floor(symbol)
    if symbol ~= symbol or symbol < 0 or symbol > 63 then
        return 0
    end
    return symbol
end

function ns.Strip.SymbolColor(symbol)
    local value = Normalize(symbol)
    local r = math.floor(value / 16) % 4
    local g = math.floor(value / 4) % 4
    local b = value % 4
    return r / 3, g / 3, b / 3
end

local function EnsureFrame()
    if frame then
        return frame
    end

    frame = CreateFrame('Frame', 'AskForeverStripFrame', UIParent)
    if frame.SetIgnoreParentScale then
        frame:SetIgnoreParentScale(true)
    end

    local physicalHeight
    if type(GetPhysicalScreenSize) == 'function' then
        local ok, _, height = pcall(GetPhysicalScreenSize)
        if ok and type(height) == 'number' and height > 0 then
            physicalHeight = height
        end
    end

    local scale
    if physicalHeight then
        scale = 768 / physicalHeight
    else
        local ok, effective = pcall(UIParent.GetEffectiveScale, UIParent)
        if ok and type(effective) == 'number' and effective > 0 then
            scale = 1 / effective
        end
    end
    if scale then
        frame:SetScale(scale)
    end

    frame:SetPoint('TOPLEFT', UIParent, 'TOPLEFT', 0, 0)
    frame:SetFrameStrata('TOOLTIP')
    frame:SetSize(STRIP_COLUMNS * BLOCK_SIZE, MAX_ROWS * BLOCK_SIZE)
    frame:Hide()
    return frame
end

local function AcquireTexture(index)
    local texture = textures[index]
    if texture then
        return texture
    end
    texture = frame:CreateTexture(nil, 'ARTWORK')
    texture:SetSize(BLOCK_SIZE, BLOCK_SIZE)
    if texture.SetSnapToPixelGrid then
        texture:SetSnapToPixelGrid(false)
    end
    if texture.SetTexelSnappingBias then
        texture:SetTexelSnappingBias(0)
    end
    textures[index] = texture
    return texture
end

local function SymbolAt(symbols, index)
    if index <= #SYNC_SYMBOLS then
        return SYNC_SYMBOLS[index]
    end
    return Normalize(symbols and symbols[index - #SYNC_SYMBOLS])
end

function ns.Strip.Show(symbols, rows)
    EnsureFrame()

    rows = math.floor(tonumber(rows) or 1)
    if rows < 1 then
        rows = 1
    elseif rows > MAX_ROWS then
        rows = MAX_ROWS
    end

    local total = rows * STRIP_COLUMNS
    for index = 1, total do
        local r, g, b = ns.Strip.SymbolColor(SymbolAt(symbols, index))
        local texture = AcquireTexture(index)
        local column = (index - 1) % STRIP_COLUMNS
        local row = math.floor((index - 1) / STRIP_COLUMNS)
        texture:ClearAllPoints()
        texture:SetPoint('TOPLEFT', frame, 'TOPLEFT', column * BLOCK_SIZE, -row * BLOCK_SIZE)
        texture:SetColorTexture(r, g, b, 1)
        texture:Show()
    end
    for index = total + 1, #textures do
        textures[index]:Hide()
    end

    frame:SetSize(STRIP_COLUMNS * BLOCK_SIZE, rows * BLOCK_SIZE)
    frame:Show()
end

function ns.Strip.Hide()
    if frame then
        frame:Hide()
    end
end

function ns.Strip.IsShown()
    return frame ~= nil and frame:IsShown()
end

function ns.Strip.Ensure()
    return EnsureFrame()
end

function ns.Strip.GetFrame()
    return frame
end

function ns.Strip.GetSampleTexture()
    EnsureFrame()
    return AcquireTexture(1)
end
