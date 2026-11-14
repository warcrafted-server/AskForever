local _, ns = ...

ns.DevReport = {}

function ns.DevReport.Attach(body, editBox, addHistory, colors, conversationNumber)
    if not body or type(ns.UI) ~= 'table' or type(ns.UI.CreateButton) ~= 'function' then
        return nil
    end

    local colorDim = type(colors) == 'table' and colors.textDim or nil
    local colorMissing = type(colors) == 'table' and colors.missing or nil

    local function Add(text, color)
        if type(addHistory) == 'function' and type(color) == 'table' then
            pcall(addHistory, text, color)
        end
    end

    local function TrimmedEditText()
        if not editBox or type(editBox.GetText) ~= 'function' then
            return ''
        end
        local ok, text = pcall(editBox.GetText, editBox)
        if not ok or type(text) ~= 'string' then
            return ''
        end
        return text:match('^%s*(.-)%s*$') or ''
    end

    local function CurrentConversation()
        if type(conversationNumber) ~= 'function' then
            return nil
        end
        local ok, conv = pcall(conversationNumber)
        if ok then
            return conv
        end
        return nil
    end

    local function ClearEditBox()
        if not editBox then
            return
        end
        if type(editBox.SetText) == 'function' then
            pcall(editBox.SetText, editBox, '')
        end
        if type(editBox.ClearFocus) == 'function' then
            pcall(editBox.ClearFocus, editBox)
        end
    end

    local function OnClick()
        local note = TrimmedEditText()
        local accepted = false
        if type(ns.Transport) == 'table' and type(ns.Transport.Send) == 'function' then
            local ok, result = pcall(ns.Transport.Send, note, nil, CurrentConversation(),
                                     'report')
            if ok then
                accepted = result
            end
        end
        ClearEditBox()
        if accepted then
            Add('Informe enviado al companion.', colorDim)
        else
            Add('No se pudo enviar el informe.', colorMissing)
        end
    end

    local ok, button = pcall(ns.UI.CreateButton, body, 'Informe', 80, 24, OnClick)
    if not ok or not button then
        return nil
    end
    if type(button.SetPoint) == 'function' then
        pcall(button.SetPoint, button, 'BOTTOMRIGHT', body, 'BOTTOMRIGHT', -8, 16)
    end
    return button
end
