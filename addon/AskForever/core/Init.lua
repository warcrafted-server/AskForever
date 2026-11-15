local ADDON, ns = ...

local DEFAULTS = {
    minimap = { angle = 225, hide = false },
    window = {},
    welcomeShown = false,
}

-- Copia recursiva: rellena solo las claves ausentes y respeta lo ya guardado.
local function ApplyDefaults(target, defaults)
    for key, value in pairs(defaults) do
        if type(value) == 'table' then
            if type(target[key]) ~= 'table' then
                target[key] = {}
            end
            ApplyDefaults(target[key], value)
        elseif target[key] == nil then
            target[key] = value
        end
    end
end

local function GetAddonVersion()
    if C_AddOns and C_AddOns.GetAddOnMetadata then
        return C_AddOns.GetAddOnMetadata(ADDON, 'Version')
    end
    return GetAddOnMetadata(ADDON, 'Version')
end

local locale = GetLocale()
local strings = ((locale == 'esES' or locale == 'esMX') and ns.L_esES) or ns.L_enUS or {}

ns.L = setmetatable({}, {
    __index = function(_, key)
        local value = strings[key]
        if value == nil then
            value = ns.L_enUS[key]
        end
        if value == nil then
            value = key
        end
        return value
    end,
})

local eventFrame = CreateFrame('Frame')
eventFrame:RegisterEvent('ADDON_LOADED')

eventFrame:SetScript('OnEvent', function(self, event, addonName)
    if event ~= 'ADDON_LOADED' or addonName ~= ADDON then
        return
    end
    self:UnregisterEvent('ADDON_LOADED')

    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    ApplyDefaults(AskForeverDB, DEFAULTS)

    print(ns.L.ADDON_LOADED_MSG:format(GetAddonVersion() or '?'))
end)

local loginFrame = CreateFrame('Frame')
loginFrame:RegisterEvent('PLAYER_LOGIN')
loginFrame:SetScript('OnEvent', function(self)
    self:UnregisterEvent('PLAYER_LOGIN')
    local other = ADDON == 'AskForever' and 'AskForeverDev' or 'AskForever'
    local isLoaded = (C_AddOns and C_AddOns.IsAddOnLoaded) or IsAddOnLoaded
    local ok, loaded = pcall(isLoaded, other)
    if ok and loaded then
        print(ns.L.MSG_TWO_COPIES:format(other))
    end
end)
