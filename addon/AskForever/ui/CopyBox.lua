local _, ns = ...

ns.UI = ns.UI or {}

local copyFrame
local copyScrollFrame
local copyEditBox

local function EnsureCopyFrame()
    if copyFrame then
        return copyFrame
    end

    copyFrame = CreateFrame('Frame', 'AskForeverCopyFrame', UIParent, 'BasicFrameTemplateWithInset')
    copyFrame:SetSize(460, 300)
    copyFrame:SetPoint('CENTER', UIParent, 'CENTER', 0, 0)
    copyFrame:SetFrameStrata('DIALOG')
    copyFrame:SetClampedToScreen(true)
    copyFrame:SetMovable(true)
    copyFrame:EnableMouse(true)
    copyFrame:RegisterForDrag('LeftButton')
    copyFrame:SetScript('OnDragStart', function(self)
        self:StartMoving()
    end)
    copyFrame:SetScript('OnDragStop', function(self)
        self:StopMovingOrSizing()
    end)
    table.insert(UISpecialFrames, 'AskForeverCopyFrame')

    local title = copyFrame:CreateFontString(nil, 'OVERLAY', 'GameFontNormalLarge')
    title:SetPoint('TOP', copyFrame, 'TOP', 0, -8)
    title:SetText(ns.L.COPY_PROMPT)

    copyScrollFrame = CreateFrame('ScrollFrame', nil, copyFrame, 'UIPanelScrollFrameTemplate')
    copyScrollFrame:SetPoint('TOPLEFT', copyFrame, 'TOPLEFT', 14, -36)
    copyScrollFrame:SetPoint('BOTTOMRIGHT', copyFrame, 'BOTTOMRIGHT', -34, 38)

    copyEditBox = CreateFrame('EditBox', nil, copyScrollFrame)
    copyEditBox:SetMultiLine(true)
    copyEditBox:SetFontObject(ChatFontNormal)
    copyEditBox:SetWidth(410)
    -- Alto fijo amplio: el ScrollFrame aporta la barra para recorrer prompts largos.
    copyEditBox:SetHeight(900)
    copyEditBox:SetAutoFocus(true)
    copyEditBox:SetMaxLetters(0)
    copyEditBox:SetScript('OnEscapePressed', function()
        copyFrame:Hide()
    end)
    copyScrollFrame:SetScrollChild(copyEditBox)

    local hint = copyFrame:CreateFontString(nil, 'OVERLAY', 'GameFontHighlightSmall')
    hint:SetPoint('BOTTOMLEFT', copyFrame, 'BOTTOMLEFT', 16, 14)
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
