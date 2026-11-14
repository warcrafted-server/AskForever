local _, ns = ...

local MAX_LIST = 400
local MAX_TABLE = 50
local MAX_DEPTH = 3

local function Pack(...)
    return { n = select('#', ...), ... }
end

local function Copy(value, depth)
    local kind = type(value)
    if kind ~= 'table' then
        if kind == 'nil' or kind == 'boolean' or kind == 'number' or kind == 'string' then
            return value
        end
        return kind
    end
    depth = depth or 1
    if depth > MAX_DEPTH then
        return 'table'
    end
    local result = {}
    local ok, iterator, state, control = pcall(pairs, value)
    if not ok then
        return 'table'
    end
    local count = 0
    pcall(function()
        for key, item in iterator, state, control do
            if count >= MAX_TABLE then
                break
            end
            count = count + 1
            local keyType = type(key)
            local safeKey = key
            if keyType ~= 'string' and keyType ~= 'number' and keyType ~= 'boolean' then
                safeKey = '[' .. keyType .. ']'
            elseif keyType == 'number' and key ~= key then
                safeKey = '[number]'
            end
            local copyOk, copied = pcall(Copy, item, depth + 1)
            if copyOk then
                result[safeKey] = copied
            else
                result[safeKey] = 'error'
            end
        end
    end)
    return result
end

local function Value(value)
    if value == nil then
        return 'missing'
    end
    local ok, copied = pcall(Copy, value, 1)
    if ok then
        return copied
    end
    return type(value)
end

local function Call(name, fn, ...)
    if type(fn) ~= 'function' then
        return 'missing'
    end
    local packed = Pack(pcall(fn, ...))
    local results = {}
    for index = 2, packed.n do
        local ok, copied = pcall(Copy, packed[index], 1)
        if ok then
            results[#results + 1] = copied
        else
            results[#results + 1] = 'error'
        end
    end
    return { ok = packed[1] and true or false, r = results }
end

local function CallOk(name, fn, ...)
    if type(fn) ~= 'function' then
        return 'missing'
    end
    local ok = pcall(fn, ...)
    return { ok = ok and true or false, r = { ok and true or false } }
end

local function CallCount(name, fn, ...)
    if type(fn) ~= 'function' then
        return 'missing'
    end
    local ok, value = pcall(fn, ...)
    local count = 0
    if ok and type(value) == 'table' then
        local countOk, length = pcall(function()
            return #value
        end)
        if countOk and type(length) == 'number' then
            count = length
        end
    end
    return { ok = ok and true or false, r = { count } }
end

local function Member(root, key)
    if root == nil then
        return nil
    end
    local ok, value = pcall(function()
        return root[key]
    end)
    if ok then
        return value
    end
    return nil
end

local function Section(fn)
    local ok, value = pcall(fn)
    if ok and (type(value) == 'table' or value == 'missing') then
        return value
    end
    return {}
end

local function PlayerClassID()
    if type(UnitClass) ~= 'function' then
        return nil
    end
    local ok, _, _, classID = pcall(UnitClass, 'player')
    if ok then
        return classID
    end
    return nil
end

local function BuildSection()
    local build = {}
    build.GetBuildInfo = Call('GetBuildInfo', GetBuildInfo)
    build.WOW_PROJECT_ID = Value(WOW_PROJECT_ID)
    build.WOW_PROJECT_MAINLINE = Value(WOW_PROJECT_MAINLINE)
    build.WOW_PROJECT_CLASSIC = Value(WOW_PROJECT_CLASSIC)
    build.WOW_PROJECT_BURNING_CRUSADE_CLASSIC = Value(WOW_PROJECT_BURNING_CRUSADE_CLASSIC)
    build.WOW_PROJECT_WRATH_CLASSIC = Value(WOW_PROJECT_WRATH_CLASSIC)
    build.LE_EXPANSION_LEVEL_CURRENT = Value(LE_EXPANSION_LEVEL_CURRENT)
    build.GetExpansionLevel = Call('GetExpansionLevel', GetExpansionLevel)
    build.GetClassicExpansionLevel = Call('GetClassicExpansionLevel', GetClassicExpansionLevel)
    build.GetServerExpansionLevel = Call('GetServerExpansionLevel', GetServerExpansionLevel)
    build.GetMaxPlayerLevel = Call('GetMaxPlayerLevel', GetMaxPlayerLevel)
    build.GetMaxLevelForPlayerExpansion = Call('GetMaxLevelForPlayerExpansion',
                                               GetMaxLevelForPlayerExpansion)
    build.GetAccountExpansionLevel = Call('GetAccountExpansionLevel', GetAccountExpansionLevel)
    build.C_Seasons = {
        HasActiveSeason = Call('C_Seasons.HasActiveSeason',
                               Member(C_Seasons, 'HasActiveSeason')),
        GetActiveSeason = Call('C_Seasons.GetActiveSeason',
                               Member(C_Seasons, 'GetActiveSeason')),
    }
    build.C_GameRules = {
        IsHardcoreActive = Call('C_GameRules.IsHardcoreActive',
                                Member(C_GameRules, 'IsHardcoreActive')),
        GetActiveGameMode = Call('C_GameRules.GetActiveGameMode',
                                 Member(C_GameRules, 'GetActiveGameMode')),
    }
    build.IsTrialAccount = Call('IsTrialAccount', IsTrialAccount)
    build.IsVeteranTrialAccount = Call('IsVeteranTrialAccount', IsVeteranTrialAccount)
    return build
end

local function CharacterSection()
    local character = {}
    character.UnitLevel = Call('UnitLevel', UnitLevel, 'player')
    character.UnitClass = Call('UnitClass', UnitClass, 'player')
    character.UnitRace = Call('UnitRace', UnitRace, 'player')
    character.UnitFactionGroup = Call('UnitFactionGroup', UnitFactionGroup, 'player')
    character.GetRealmName = Call('GetRealmName', GetRealmName)
    character.GetMoney = Call('GetMoney', GetMoney)
    character.GetNumSkillLines = Call('GetNumSkillLines', GetNumSkillLines)

    local skillCount = 0
    local skillCall = character.GetNumSkillLines
    if type(skillCall) == 'table' and skillCall.ok and type(skillCall.r) == 'table'
            and type(skillCall.r[1]) == 'number' then
        skillCount = math.max(0, math.min(skillCall.r[1], 1000))
    end
    if type(GetSkillLineInfo) == 'function' then
        local skills = {}
        for index = 1, skillCount do
            skills[index] = Call('GetSkillLineInfo ' .. index, GetSkillLineInfo, index)
        end
        character.skills = skills
    else
        character.skills = 'missing'
    end

    character.GetProfessions = Call('GetProfessions', GetProfessions)
    local professions = {}
    local professionsCall = character.GetProfessions
    if type(professionsCall) == 'table' and professionsCall.ok
            and type(professionsCall.r) == 'table' then
        for index = 1, 6 do
            local professionIndex = professionsCall.r[index]
            if type(professionIndex) == 'number' then
                professions[#professions + 1] = {
                    index = professionIndex,
                    info = Call('GetProfessionInfo ' .. index, GetProfessionInfo, professionIndex),
                }
            end
        end
    end
    character.professions = professions
    return character
end

local function SystemsSection()
    local systems = {}
    local classID = PlayerClassID()
    systems.playerClassID = Value(classID)

    local talents = {}
    talents.GetNumTalentGroups = Call('GetNumTalentGroups', GetNumTalentGroups)
    talents.GetNumTalentGroupsFalse = Call('GetNumTalentGroups(false)', GetNumTalentGroups, false)
    talents.GetNumTalentGroupsTrue = Call('GetNumTalentGroups(true)', GetNumTalentGroups, true)
    talents.GetActiveTalentGroup = Call('GetActiveTalentGroup', GetActiveTalentGroup)
    talents.GetNumTalentTabs = Call('GetNumTalentTabs', GetNumTalentTabs)
    local tabs = {}
    for index = 1, 3 do
        tabs[index] = Call('GetTalentTabInfo ' .. index, GetTalentTabInfo, index)
    end
    talents.tabs = tabs
    talents.C_SpecializationInfo = {
        CanPlayerUseTalentSpecUI = Call('C_SpecializationInfo.CanPlayerUseTalentSpecUI',
                                        Member(C_SpecializationInfo,
                                               'CanPlayerUseTalentSpecUI')),
        GetNumSpecializationsForClassID = Call(
            'C_SpecializationInfo.GetNumSpecializationsForClassID',
            Member(C_SpecializationInfo, 'GetNumSpecializationsForClassID'), classID),
    }
    talents.GetSpecialization = Call('GetSpecialization', GetSpecialization)
    talents.GetNumSpecializations = Call('GetNumSpecializations', GetNumSpecializations)
    systems.talents = talents

    systems.lfg = {
        GetAvailableCategories = Call('C_LFGList.GetAvailableCategories',
                                      Member(C_LFGList, 'GetAvailableCategories')),
        GetNumRandomDungeons = Call('GetNumRandomDungeons', GetNumRandomDungeons),
        CanPlayerUseLFD = Call('C_LFGInfo.CanPlayerUseLFD',
                               Member(C_LFGInfo, 'CanPlayerUseLFD')),
        CanPlayerUseGroupFinder = Call('C_LFGInfo.CanPlayerUseGroupFinder',
                                       Member(C_LFGInfo, 'CanPlayerUseGroupFinder')),
        CanPlayerUsePVP = Call('C_LFGInfo.CanPlayerUsePVP',
                               Member(C_LFGInfo, 'CanPlayerUsePVP')),
    }

    systems.achievements = {
        GetNumCompletedAchievements = Call('GetNumCompletedAchievements',
                                           GetNumCompletedAchievements),
        GetCategoryList = CallCount('GetCategoryList', GetCategoryList),
        GetTotalAchievementPoints = Call('GetTotalAchievementPoints',
                                         GetTotalAchievementPoints),
    }

    systems.collections = {
        GetNumMounts = Call('C_MountJournal.GetNumMounts',
                            Member(C_MountJournal, 'GetNumMounts')),
        GetNumDisplayedMounts = Call('C_MountJournal.GetNumDisplayedMounts',
                                     Member(C_MountJournal, 'GetNumDisplayedMounts')),
        GetNumPets = Call('C_PetJournal.GetNumPets',
                          Member(C_PetJournal, 'GetNumPets')),
        GetNumToys = Call('C_ToyBox.GetNumToys',
                          Member(C_ToyBox, 'GetNumToys')),
        GetNumHeirlooms = Call('C_Heirloom.GetNumHeirlooms',
                               Member(C_Heirloom, 'GetNumHeirlooms')),
        GetNumMaxOutfits = Call('C_TransmogCollection.GetNumMaxOutfits',
                                Member(C_TransmogCollection, 'GetNumMaxOutfits')),
        GetAppearanceSources = CallOk('C_TransmogCollection.GetAppearanceSources',
                                      Member(C_TransmogCollection, 'GetAppearanceSources'), 0),
    }

    systems.other = {
        GetNumDayEvents = Call('C_Calendar.GetNumDayEvents',
                               Member(C_Calendar, 'GetNumDayEvents'), 0, 1),
        GetActiveCovenantID = Call('C_Covenants.GetActiveCovenantID',
                                   Member(C_Covenants, 'GetActiveCovenantID')),
        HasGarrison = Call('C_Garrison.HasGarrison',
                           Member(C_Garrison, 'HasGarrison'), 2),
        GetBestMapForUnit = Call('C_Map.GetBestMapForUnit',
                                 Member(C_Map, 'GetBestMapForUnit'), 'player'),
        IsWarModeFeatureEnabled = Call('C_PvP.IsWarModeFeatureEnabled',
                                       Member(C_PvP, 'IsWarModeFeatureEnabled')),
        GetNumCompanionsMount = Call('GetNumCompanions(MOUNT)',
                                     GetNumCompanions, 'MOUNT'),
        GetNumCompanionsCritter = Call('GetNumCompanions(CRITTER)',
                                       GetNumCompanions, 'CRITTER'),
        IsInGuild = Call('IsInGuild', IsInGuild),
        GetNumGuildBankTabs = Call('GetNumGuildBankTabs', GetNumGuildBankTabs),
        GetAvailableCustomizations = CallOk('C_BarberShop.GetAvailableCustomizations',
                                            Member(C_BarberShop,
                                                   'GetAvailableCustomizations')),
        IsTimerunningPlayer = Call('C_ChatInfo.IsTimerunningPlayer',
                                   Member(C_ChatInfo, 'IsTimerunningPlayer')),
        IsPlayerNPERestricted = Call('C_PlayerInfo.IsPlayerNPERestricted',
                                     Member(C_PlayerInfo, 'IsPlayerNPERestricted')),
    }
    return systems
end

local KEYWORDS = {
    'legacy', 'forever', 'camelot', 'hardcore', 'season', 'talent', 'spec',
    'lfg', 'achievement', 'mount', 'transmog', 'collection', 'covenant',
    'calendar', 'guild', 'profession', 'heirloom', 'toy', 'battlepet',
    'petjournal', 'encounter', 'barber', 'warmode', 'timerunning',
}

local function MatchesKeyword(name)
    local lower = name:lower()
    for index = 1, #KEYWORDS do
        if lower:find(KEYWORDS[index], 1, true) then
            return true
        end
    end
    return false
end

local function SortAndLimit(list)
    local total = #list
    table.sort(list)
    local limited = {}
    for index = 1, math.min(total, MAX_LIST) do
        limited[index] = list[index]
    end
    return limited, total
end

local function ApiSection()
    local functions = {}
    local matching = {}
    pcall(function()
        for name, value in pairs(_G) do
            if type(name) == 'string' then
                if name:sub(1, 2) == 'C_' and type(value) == 'table' then
                    pcall(function()
                        for key, member in pairs(value) do
                            if type(key) == 'string' and type(member) == 'function' then
                                functions[#functions + 1] = name .. '.' .. key
                            end
                        end
                    end)
                end
                if (type(value) == 'function' or type(value) == 'table')
                        and MatchesKeyword(name) then
                    matching[#matching + 1] = name
                end
            end
        end
    end)
    local limitedFunctions, functionTotal = SortAndLimit(functions)
    local limitedMatching, matchingTotal = SortAndLimit(matching)
    return {
        cFunctions = limitedFunctions,
        cFunctionsTotal = functionTotal,
        matching = limitedMatching,
        matchingTotal = matchingTotal,
    }
end

local UI_NAMES = {
    'PlayerTalentFrame', 'ClassTalentFrame', 'TalentFrame', 'AchievementFrame',
    'CollectionsJournal', 'WardrobeFrame', 'EncounterJournal', 'PVEFrame',
    'LFGParentFrame', 'LFDParentFrame', 'LFGListFrame', 'CalendarFrame',
    'GuildFrame', 'CommunitiesFrame', 'MacroFrame', 'WorldMapFrame',
    'BarberShopFrame', 'AuctionHouseFrame', 'AuctionFrame', 'MailFrame',
    'SpellBookFrame', 'PlayerSpellsFrame', 'ProfessionsFrame', 'TradeSkillFrame',
    'CraftFrame', 'CharacterFrame', 'ReputationFrame', 'HonorFrame', 'PVPFrame',
    'PVPUIFrame', 'SettingsPanel', 'InterfaceOptionsFrame', 'VideoOptionsFrame',
    'GameMenuFrame', 'KeyBindingFrame', 'StoreFrame', 'HelpFrame',
    'ExpansionLandingPage', 'MinimapCluster', 'QuestLogFrame', 'QuestMapFrame',
    'ObjectiveTrackerFrame', 'WatchFrame', 'EditModeManagerFrame',
}

local function FrameInfo(frame)
    local objectType = type(frame)
    local getType = Member(frame, 'GetObjectType')
    if type(getType) == 'function' then
        local ok, value = pcall(getType, frame)
        if ok and value ~= nil then
            objectType = Copy(value, 1)
        end
    end
    local visible = false
    local isVisible = Member(frame, 'IsVisible')
    if type(isVisible) == 'function' then
        local ok, value = pcall(isVisible, frame)
        if ok then
            visible = value and true or false
        end
    else
        local isShown = Member(frame, 'IsShown')
        if type(isShown) == 'function' then
            local ok, value = pcall(isShown, frame)
            if ok then
                visible = value and true or false
            end
        end
    end
    return { type = objectType, visible = visible }
end

local function BlizzardAddons()
    local getNum = Member(C_AddOns, 'GetNumAddOns')
    local getInfo = Member(C_AddOns, 'GetAddOnInfo')
    local modernInfo = type(getInfo) == 'function'
    if type(getNum) ~= 'function' then
        getNum = GetNumAddOns
    end
    if not modernInfo then
        getInfo = GetAddOnInfo
    end
    if type(getNum) ~= 'function' or type(getInfo) ~= 'function' then
        return 'missing'
    end
    local ok, count = pcall(getNum)
    if not ok or type(count) ~= 'number' then
        return { list = {}, total = 0 }
    end
    count = math.max(0, math.min(count, 1000))
    local addons = {}
    local total = 0
    for index = 1, count do
        local infoOk, addonName, title, _, arg5, arg6 = pcall(getInfo, index)
        local loadable
        if modernInfo then
            loadable = arg5
        else
            loadable = arg6
        end
        if infoOk and type(addonName) == 'string'
                and addonName:sub(1, 9) == 'Blizzard_' then
            total = total + 1
            if #addons < MAX_LIST then
                addons[#addons + 1] = {
                    name = addonName,
                    title = Value(title),
                    loadable = loadable and true or false,
                }
            end
        end
    end
    return { list = addons, total = total }
end

local function UiSection()
    local ui = { frames = {} }
    for index = 1, #UI_NAMES do
        local name = UI_NAMES[index]
        local frame = _G[name]
        if frame == nil then
            ui.frames[name] = 'missing'
        else
            local ok, info = pcall(FrameInfo, frame)
            if ok and type(info) == 'table' then
                ui.frames[name] = info
            else
                ui.frames[name] = 'error'
            end
        end
    end
    local addonsOk, addons = pcall(BlizzardAddons)
    if not addonsOk or type(addons) ~= 'table' then
        addons = 'missing'
    end
    if type(addons) == 'table' then
        ui.blizzardAddons = addons.list
        ui.blizzardAddonsTotal = addons.total
    else
        ui.blizzardAddons = addons
    end
    return ui
end

local function OptionsSection()
    local categories = nil
    local source = nil

    local function Try(sourceObject, sourceName)
        if sourceObject == nil or categories ~= nil then
            return
        end
        local method = Member(sourceObject, 'GetAllCategories')
        if type(method) ~= 'function' then
            return
        end
        local ok, value = pcall(method, sourceObject)
        if ok and type(value) == 'table' then
            categories = value
            source = sourceName
        end
    end

    Try(SettingsPanel, 'SettingsPanel')
    Try(Settings, 'Settings')

    if type(categories) ~= 'table' then
        return 'missing'
    end

    local list = {}
    local total = 0
    local totalOk, length = pcall(function()
        return #categories
    end)
    if totalOk and type(length) == 'number' then
        total = length
    end
    for index = 1, math.min(total, MAX_LIST) do
        local category = Member(categories, index)
        local name = ''
        if category ~= nil then
            local getName = Member(category, 'GetName')
            if type(getName) == 'function' then
                local ok, value = pcall(getName, category)
                if ok then
                    local copied = Copy(value, 1)
                    if type(copied) == 'string' then
                        name = copied
                    elseif copied ~= nil then
                        name = tostring(copied)
                    end
                end
            else
                local rawName = Member(category, 'name')
                if type(rawName) == 'string' then
                    name = rawName
                end
            end
        end
        list[#list + 1] = { name = name, type = type(category) }
    end
    return { source = source, categories = list, total = total }
end

local function MakeData()
    local characterName = 'desconocido'
    if type(UnitName) == 'function' then
        local ok, value = pcall(UnitName, 'player')
        if ok and type(value) == 'string' and value ~= '' then
            characterName = value
        end
    end
    local realmName = 'desconocido'
    if type(GetRealmName) == 'function' then
        local ok, value = pcall(GetRealmName)
        if ok and type(value) == 'string' and value ~= '' then
            realmName = value
        end
    end
    local level = 0
    if type(UnitLevel) == 'function' then
        local ok, value = pcall(UnitLevel, 'player')
        if ok and type(value) == 'number' then
            level = value
        end
    end

    local stamp = '0'
    if type(time) == 'function' then
        local ok, value = pcall(time)
        if ok and type(value) == 'number' then
            stamp = tostring(math.floor(value))
        end
    end
    if type(date) == 'function' then
        local ok, value = pcall(date, '%Y-%m-%d %H:%M:%S')
        if ok and type(value) == 'string' then
            stamp = value
        end
    end

    local key = characterName .. '-' .. realmName .. '-' .. tostring(level)
    return key, {
        time = stamp,
        build = Section(BuildSection),
        character = Section(CharacterSection),
        systems = Section(SystemsSection),
        api = Section(ApiSection),
        ui = Section(UiSection),
        options = Section(OptionsSection),
    }
end

local function Run()
    local key, data = MakeData()
    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    if type(AskForeverDB.probe) ~= 'table' then
        AskForeverDB.probe = {}
    end
    AskForeverDB.probe[key] = data
    print('AskForever: diagnóstico guardado (haz /reload para escribirlo en disco).')
end

SLASH_ASKFOREVERPROBE1 = '/afprobe'
SlashCmdList['ASKFOREVERPROBE'] = function()
    local ok = pcall(Run)
    if not ok then
        print('AskForever: no se pudo completar el diagnóstico.')
    end
end
