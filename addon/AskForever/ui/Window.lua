local _, ns = ...

ns.UI = ns.UI or {}

local Theme = ns.UI.Theme
local colors = Theme.colors

local function TryCreateFrame(frameType, name, parent, template)
    local ok, frame = pcall(CreateFrame, frameType, name, parent, template)
    if ok and frame then
        return frame
    end
    return nil
end

local function AddEdge(parent, color, pointA, pointB, horizontal)
    local line = parent:CreateTexture(nil, 'BORDER')
    line:SetColorTexture(color[1], color[2], color[3], color[4] or 1)
    line:SetPoint(pointA, parent, pointA)
    line:SetPoint(pointB, parent, pointB)
    if horizontal then
        line:SetHeight(1)
    else
        line:SetWidth(1)
    end
    return line
end

local function StylePanel(frame, background, border)
    local bg = frame:CreateTexture(nil, 'BACKGROUND')
    bg:SetAllPoints(frame)
    bg:SetColorTexture(background[1], background[2], background[3], background[4] or 1)

    AddEdge(frame, border, 'TOPLEFT', 'TOPRIGHT', true)
    AddEdge(frame, border, 'BOTTOMLEFT', 'BOTTOMRIGHT', true)
    AddEdge(frame, border, 'TOPLEFT', 'BOTTOMLEFT', false)
    AddEdge(frame, border, 'TOPRIGHT', 'BOTTOMRIGHT', false)
end

local function ApplyTitle(frame, title)
    local titled = false
    if frame.SetTitle then
        titled = pcall(frame.SetTitle, frame, title or '')
    end
    if not titled and frame.TitleText then
        frame.TitleText:SetText(title or '')
        titled = true
    end
    if not titled then
        local titleText = frame:CreateFontString(nil, 'OVERLAY')
        titleText:SetFontObject(Theme.font.title)
        titleText:SetPoint('TOPLEFT', frame, 'TOPLEFT', 12, -8)
        titleText:SetText(title or '')
    end
end

local function ApplyPortrait(frame)
    local applied = false
    if frame.SetPortraitToAsset then
        applied = pcall(frame.SetPortraitToAsset, frame, Theme.icon)
    end
    if not applied and frame.SetPortraitTextureRaw then
        applied = pcall(frame.SetPortraitTextureRaw, frame, Theme.icon)
    end
    if not applied and frame.PortraitContainer then
        applied = pcall(frame.PortraitContainer.SetTexture, frame.PortraitContainer, Theme.icon)
    end
    if not applied then
        local portrait = frame:CreateTexture(nil, 'ARTWORK')
        portrait:SetSize(32, 32)
        portrait:SetPoint('TOPLEFT', frame, 'TOPLEFT', 10, -6)
        pcall(portrait.SetTexture, portrait, Theme.icon)
    end
end

function ns.UI.CreateWindow(name, width, height, title)
    local frame = TryCreateFrame('Frame', name, UIParent, 'ButtonFrameTemplate')
    if not frame then
        frame = TryCreateFrame('Frame', name, UIParent, 'PortraitFrameTemplate')
    end
    if not frame then
        frame = TryCreateFrame('Frame', name, UIParent, 'BackdropTemplate')
    end
    if not frame then
        frame = CreateFrame('Frame', name, UIParent)
    end

    frame:SetSize(width, height)
    frame:SetFrameStrata('HIGH')
    frame:SetClampedToScreen(true)
    frame:SetMovable(true)
    frame:Hide()

    if ButtonFrameTemplate_HideButtonBar then
        pcall(ButtonFrameTemplate_HideButtonBar, frame)
    end
    if frame.ButtonBar then
        frame.ButtonBar:Hide()
    end

    ApplyTitle(frame, title)
    ApplyPortrait(frame)

    local close = frame.CloseButton
    if not close then
        close = TryCreateFrame('Button', nil, frame, 'UIPanelCloseButton')
    end
    if close then
        if not frame.CloseButton then
            close:SetPoint('TOPRIGHT', frame, 'TOPRIGHT', -4, -4)
        end
        close:SetScript('OnClick', function()
            frame:Hide()
        end)
    end

    local dragArea = frame.TitleContainer or frame
    dragArea:EnableMouse(true)
    dragArea:RegisterForDrag('LeftButton')
    dragArea:SetScript('OnDragStart', function()
        frame:StartMoving()
    end)
    dragArea:SetScript('OnDragStop', function()
        frame:StopMovingOrSizing()
        if frame.onMoveStop then
            frame.onMoveStop()
        end
    end)

    local inset = frame.Inset
    if not inset then
        inset = CreateFrame('Frame', nil, frame)
        inset:SetPoint('TOPLEFT', frame, 'TOPLEFT', 12, -30)
        inset:SetPoint('BOTTOMRIGHT', frame, 'BOTTOMRIGHT', -12, 12)
    end

    local body = CreateFrame('Frame', nil, inset)
    body:SetPoint('TOPLEFT', inset, 'TOPLEFT', 2, -2)
    body:SetPoint('BOTTOMRIGHT', inset, 'BOTTOMRIGHT', -2, 2)
    StylePanel(body, colors.windowBg, colors.panelBorder)
    frame.body = body

    return frame
end

function ns.UI.CreatePanel(parent)
    local panel = CreateFrame('Frame', nil, parent)
    StylePanel(panel, colors.panelBg, colors.panelBorder)
    return panel
end

function ns.UI.CreateText(parent, font, color)
    -- Las fuentes del Theme son objetos: CreateFontString solo acepta nombres de plantilla.
    local text = parent:CreateFontString(nil, 'OVERLAY')
    text:SetFontObject(font or Theme.font.body)
    if color then
        text:SetTextColor(color[1], color[2], color[3], color[4] or 1)
    end
    return text
end

function ns.UI.CreateButton(parent, text, width, height, onClick)
    local button = TryCreateFrame('Button', nil, parent, 'UIPanelButtonTemplate')
    if not button then
        button = CreateFrame('Button', nil, parent)
        local label = button:CreateFontString(nil, 'OVERLAY')
        label:SetFontObject(Theme.font.body)
        label:SetPoint('CENTER')
        button.label = label
    end

    button:SetSize(width, height)
    if button.SetText then
        pcall(button.SetText, button, text or '')
    elseif button.label then
        button.label:SetText(text or '')
    end
    button:SetScript('OnClick', function(self)
        if onClick then
            onClick(self)
        end
    end)
    return button
end

function ns.UI.CreateInput(parent)
    local input = TryCreateFrame('EditBox', nil, parent, 'BackdropTemplate')
    if not input then
        input = CreateFrame('EditBox', nil, parent)
    end

    input:SetSize(120, 24)
    input:SetFontObject(Theme.font.body)
    input:SetAutoFocus(false)
    if input.SetTextInsets then
        input:SetTextInsets(6, 6, 0, 0)
    end

    if input.SetBackdrop and input.SetBackdropColor then
        local bg = colors.barBg
        local border = colors.panelBorder
        local focus = colors.primaryBorder
        input:SetBackdrop(Theme.backdrop)
        input:SetBackdropColor(bg[1], bg[2], bg[3], bg[4] or 1)
        input:SetBackdropBorderColor(border[1], border[2], border[3], border[4] or 1)
        input:SetScript('OnEditFocusGained', function(self)
            self:SetBackdropBorderColor(focus[1], focus[2], focus[3], focus[4] or 1)
        end)
        input:SetScript('OnEditFocusLost', function(self)
            self:SetBackdropBorderColor(border[1], border[2], border[3], border[4] or 1)
        end)
    end

    return input
end
