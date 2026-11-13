local _, ns = ...

ns.UI = ns.UI or {}

local BUTTON_SIZE = 31
local ICON_SIZE = 20
local BORDER_SIZE = 54
local DEFAULT_ANGLE = 225
local ICON_TEXTURE = 'Interface\\Icons\\INV_Misc_Book_09'
local BORDER_TEXTURE = 'Interface\\Minimap\\MiniMap-TrackingBorder'
local HIGHLIGHT_TEXTURE = 'Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight'
local MASK_TEXTURE = 'Interface\\CharacterFrame\\TempPortraitAlphaMask'

local button
local suppressClick = false

local function SafeSetTexture(texture, path)
    pcall(texture.SetTexture, texture, path)
end

local function GetAngle()
    local minimap = type(AskForeverDB) == 'table' and AskForeverDB.minimap
    if type(minimap) == 'table' and type(minimap.angle) == 'number' then
        return minimap.angle
    end
    return DEFAULT_ANGLE
end

local function UpdatePosition()
    if not button then
        return
    end
    local angle = math.rad(GetAngle())
    local radius = Minimap:GetWidth() / 2 + 5
    button:ClearAllPoints()
    button:SetPoint('CENTER', Minimap, 'CENTER', math.cos(angle) * radius, math.sin(angle) * radius)
end

local function OnDragUpdate()
    if type(AskForeverDB) ~= 'table' or type(AskForeverDB.minimap) ~= 'table' then
        return
    end
    local cx, cy = GetCursorPosition()
    local scale = Minimap:GetEffectiveScale()
    local mx, my = Minimap:GetCenter()
    if not cx or not cy or not scale or scale == 0 or not mx or not my then
        return
    end

    local angle = math.deg(math.atan2(cy / scale - my, cx / scale - mx))
    if angle < 0 then
        angle = angle + 360
    end
    AskForeverDB.minimap.angle = angle
    UpdatePosition()
end

local function CreateButton()
    if button or not Minimap then
        return
    end

    button = CreateFrame('Button', 'AskForeverMinimapButton', Minimap)
    button:SetSize(BUTTON_SIZE, BUTTON_SIZE)
    button:SetFrameStrata('MEDIUM')
    button:SetFrameLevel(8)
    button:RegisterForClicks('LeftButtonUp')
    button:RegisterForDrag('LeftButton')

    local border = button:CreateTexture(nil, 'OVERLAY')
    border:SetSize(BORDER_SIZE, BORDER_SIZE)
    border:SetPoint('TOPLEFT')
    SafeSetTexture(border, BORDER_TEXTURE)

    local icon = button:CreateTexture(nil, 'BACKGROUND')
    icon:SetSize(ICON_SIZE, ICON_SIZE)
    icon:SetPoint('CENTER')
    SafeSetTexture(icon, ICON_TEXTURE)
    icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)

    if button.CreateMaskTexture and icon.SetMask then
        -- La máscara circular es opcional: si el cliente no la soporta, el icono se ve igual.
        pcall(function()
            local mask = button:CreateMaskTexture()
            mask:SetTexture(MASK_TEXTURE, 'CLAMP', 'CLAMP')
            mask:SetAllPoints(icon)
            icon:SetMask(mask)
        end)
    end

    local highlight = button:CreateTexture(nil, 'HIGHLIGHT')
    highlight:SetAllPoints(button)
    SafeSetTexture(highlight, HIGHLIGHT_TEXTURE)

    button:SetScript('OnDragStart', function(self)
        suppressClick = true
        self:SetScript('OnUpdate', OnDragUpdate)
    end)
    button:SetScript('OnDragStop', function(self)
        self:SetScript('OnUpdate', nil)
        -- Si el cliente no envía OnClick tras arrastrar, la bandera no debe tragarse el siguiente clic real.
        C_Timer.After(0.2, function()
            suppressClick = false
        end)
    end)
    button:SetScript('OnClick', function(self, mouseButton)
        if mouseButton ~= 'LeftButton' then
            return
        end
        -- El clic que cierra un arrastre no debe abrir la ventana.
        if suppressClick then
            suppressClick = false
            return
        end
        ns.UI.ToggleMain()
    end)
    button:SetScript('OnEnter', function(self)
        GameTooltip:SetOwner(self, 'ANCHOR_LEFT')
        GameTooltip:SetText(ns.L.WINDOW_TITLE)
        GameTooltip:AddLine(ns.L.MINIMAP_TIP_OPEN, 1, 1, 1)
        GameTooltip:AddLine(ns.L.MINIMAP_TIP_DRAG, 0.7, 0.7, 0.7)
        GameTooltip:Show()
    end)
    button:SetScript('OnLeave', function()
        GameTooltip:Hide()
    end)

    UpdatePosition()

    if type(AskForeverDB) == 'table' and AskForeverDB.minimap and AskForeverDB.minimap.hide then
        button:Hide()
    end
end

function ns.UI.SetMinimapShown(shown)
    if type(AskForeverDB) ~= 'table' then
        AskForeverDB = {}
    end
    AskForeverDB.minimap = AskForeverDB.minimap or {}
    AskForeverDB.minimap.hide = not shown

    if not button then
        return
    end
    if shown then
        button:Show()
    else
        button:Hide()
    end
end

function ns.UI.ToggleMinimap()
    local hidden = type(AskForeverDB) == 'table' and AskForeverDB.minimap
        and AskForeverDB.minimap.hide
    local shown = not not hidden
    ns.UI.SetMinimapShown(shown)
    return shown
end

local eventFrame = CreateFrame('Frame')
eventFrame:RegisterEvent('PLAYER_LOGIN')
eventFrame:SetScript('OnEvent', function(self, event)
    if event ~= 'PLAYER_LOGIN' then
        return
    end
    self:UnregisterEvent('PLAYER_LOGIN')
    CreateButton()
end)
