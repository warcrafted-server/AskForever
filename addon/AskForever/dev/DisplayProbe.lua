local _, ns = ...

-- Solo desarrollo: guarda el modo de pantalla en AskForeverDB.diag.display para leerlo tras /reload.
-- Uso: /afdisplay <etiqueta>  (por ejemplo «ventana», «completa-ventana», «completa»).

local CANDIDATES = {
    'gxWindow', 'gxMaximize', 'gxFullscreenResolution', 'gxWindowedResolution',
    'gxMonitor', 'gxApi', 'displayMode', 'gxDisplayMode',
}

local function ReadCVar(name)
    if C_CVar and C_CVar.GetCVar then
        local ok, value = pcall(C_CVar.GetCVar, name)
        if ok then
            return value
        end
    end
    local ok, value = pcall(GetCVar, name)
    if ok then
        return value
    end
    return nil
end

local function Probe(label)
    local sample = { label = label ~= '' and label or '?', time = date('%H:%M:%S'), cvars = {}, gx = {} }
    for _, name in ipairs(CANDIDATES) do
        sample.cvars[name] = ReadCVar(name)
    end
    -- Todas las variables gx* que conozca el cliente, por si el modo se guarda con otro nombre.
    if type(ConsoleGetAllCommands) == 'function' then
        local ok, commands = pcall(ConsoleGetAllCommands)
        if ok and type(commands) == 'table' then
            for _, info in ipairs(commands) do
                local name = type(info) == 'table' and info.command
                if type(name) == 'string' and name:lower():find('^gx') then
                    sample.gx[name] = ReadCVar(name)
                end
            end
        end
    end
    if type(GetPhysicalScreenSize) == 'function' then
        local ok, width, height = pcall(GetPhysicalScreenSize)
        if ok then
            sample.physical = { width, height }
        end
    end

    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    AskForeverDB.diag = AskForeverDB.diag or {}
    AskForeverDB.diag.display = AskForeverDB.diag.display or {}
    table.insert(AskForeverDB.diag.display, sample)
    print(('AskForever: modo de pantalla guardado (%s). Haz /reload cuando acabes.'):format(sample.label))
end

SLASH_ASKFOREVERDISPLAY1 = '/afdisplay'
SlashCmdList.ASKFOREVERDISPLAY = function(msg)
    Probe((msg or ''):match('^%s*(.-)%s*$'))
end

ns.DisplayProbe = Probe
