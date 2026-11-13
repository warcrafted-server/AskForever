local _, ns = ...

ns.UI = ns.UI or {}

local Theme = ns.UI.Theme
local colors = Theme.colors

local copyFrame
local copyScrollFrame
local copyEditBox

local function CreateScrollFrame(parent)
    local ok, scroll = pcall(CreateFrame, 'ScrollFrame', nil, parent, 'UIPanelScrollFrameTemplate')
    if ok and scroll then
        return scroll
    end
    return CreateFrame('ScrollFrame', nil, parent)
end

local function EnsureCopyFrame()
    if copyFrame then
        return copyFrame
    end

    copyFrame = ns.UI.CreateWindow('AskForeverCopyFrame', 480, 340, ns.L.COPY_PROMPT)
    copyFrame:SetFrameStrata('DIALOG')
    copyFrame:SetPoint('CENTER', UIParent, 'CENTER', 0, 0)
    table.insert(UISpecialFrames, 'AskForeverCopyFrame')

    local body = copyFrame.body

    local panel = ns.UI.CreatePanel(body)
    panel:SetPoint('TOPLEFT', body, 'TOPLEFT', 8, -8)
    panel:SetPoint('BOTTOMRIGHT', body, 'BOTTOMRIGHT', -8, 30)

    copyScrollFrame = CreateScrollFrame(panel)
    copyScrollFrame:SetPoint('TOPLEFT', panel, 'TOPLEFT', 6, -6)
    copyScrollFrame:SetPoint('BOTTOMRIGHT', panel, 'BOTTOMRIGHT', -26, 6)

    copyEditBox = CreateFrame('EditBox', nil, copyScrollFrame)
    copyEditBox:SetMultiLine(true)
    copyEditBox:SetFontObject(Theme.font.body)
    copyEditBox:SetWidth(400)
    -- Alto fijo amplio: el ScrollFrame aporta la barra para recorrer prompts largos.
    copyEditBox:SetHeight(900)
    copyEditBox:SetAutoFocus(true)
    copyEditBox:SetMaxLetters(0)
    copyEditBox:SetScript('OnEscapePressed', function()
        copyFrame:Hide()
    end)
    copyScrollFrame:SetScrollChild(copyEditBox)

    local function FitEditBox()
        local width = copyScrollFrame:GetWidth()
        if width and width > 4 then
            copyEditBox:SetWidth(width - 4)
        end
    end
    copyScrollFrame:SetScript('OnSizeChanged', FitEditBox)

    local hint = ns.UI.CreateText(body, Theme.font.small, colors.textDim)
    hint:SetPoint('BOTTOMLEFT', body, 'BOTTOMLEFT', 10, 8)
    hint:SetText(ns.L.COPY_HINT)

    copyFrame:SetScript('OnHide', function()
        copyEditBox:ClearFocus()
    end)

    return copyFrame
end

function ns.UI.ShowCopyBox(text)
    local frame = EnsureCopyFrame()
    copyEditBox:SetText(text or '')
    copyScrollFrame:SetVerticalScroll(0)
    frame:Show()
    copyEditBox:HighlightText()
    copyEditBox:SetFocus()
end
