local _, ns = ...

local null = {}

ns.Json = { null = null }

local ESCAPE_SHORT = {
    ['"'] = '\\"',
    ['\\'] = '\\\\',
    ['\n'] = '\\n',
    ['\r'] = '\\r',
    ['\t'] = '\\t',
}

local function EscapeString(value)
    local out = {}
    for index = 1, #value do
        local byte = value:byte(index)
        local char = value:sub(index, index)
        local short = ESCAPE_SHORT[char]
        if short then
            out[#out + 1] = short
        elseif byte < 0x20 then
            out[#out + 1] = string.format('\\u%04x', byte)
        else
            out[#out + 1] = char
        end
    end
    return '"' .. table.concat(out) .. '"'
end

local function EncodeNumber(value)
    if value ~= value or value == math.huge or value == -math.huge then
        error('JSON: invalid number')
    end
    if math.floor(value) == value then
        return string.format('%d', value)
    end
    return string.format('%.14g', value)
end

local function IsArray(value)
    local count = 0
    local highest = 0
    for key in pairs(value) do
        if type(key) ~= 'number' or key < 1 or math.floor(key) ~= key then
            return false
        end
        count = count + 1
        if key > highest then
            highest = key
        end
    end
    return count > 0 and highest == count
end

local function EncodeValue(value)
    if value == nil then
        return 'null'
    end
    if value == null then
        return 'null'
    end

    local kind = type(value)
    if kind == 'string' then
        return EscapeString(value)
    elseif kind == 'number' then
        return EncodeNumber(value)
    elseif kind == 'boolean' then
        return value and 'true' or 'false'
    elseif kind == 'table' then
        if IsArray(value) then
            local items = {}
            for index = 1, #value do
                items[#items + 1] = EncodeValue(value[index])
            end
            return '[' .. table.concat(items, ',') .. ']'
        end

        local entries = {}
        for key, item in pairs(value) do
            entries[#entries + 1] = { key = tostring(key), value = item }
        end
        table.sort(entries, function(left, right)
            return left.key < right.key
        end)

        local items = {}
        for _, entry in ipairs(entries) do
            items[#items + 1] = EscapeString(entry.key) .. ':' .. EncodeValue(entry.value)
        end
        return '{' .. table.concat(items, ',') .. '}'
    end
    error('JSON: unsupported type ' .. kind)
end

function ns.Json.Encode(value)
    return EncodeValue(value)
end
