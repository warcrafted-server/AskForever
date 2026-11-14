local _, ns = ...

ns.DevReport = {}

function ns.DevReport.Attach(body, editBox, addHistory, colors, conversationNumber)
    if not body or type(ns.UI) ~= 'table' or type(ns.UI.CreateButton) ~= 'function' then
        return nil
    end

    local Theme = ns.UI.Theme
    local fontBody = Theme and Theme.font and Theme.font.body or nil
    local fontSmall = Theme and Theme.font and Theme.font.small or nil
    local colorSection = type(colors) == 'table' and colors.sectionLabel or nil
    local colorText = type(colors) == 'table' and colors.text or nil
    local colorDim = type(colors) == 'table' and colors.textDim or nil
    local colorMissing = type(colors) == 'table' and colors.missing or nil

    local reportFrame
    local reportQuestion
    local reportEditBox
    local reportScroll
    local reportWarning
    local confirmEmpty = false

    local function Add(text, color)
        if type(addHistory) == 'function' and type(color) == 'table' then
            pcall(addHistory, text, color)
        end
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

    local function TrimEdit()
        if not reportEditBox or type(reportEditBox.GetText) ~= 'function' then
            return ''
        end
        local ok, text = pcall(reportEditBox.GetText, reportEditBox)
        if not ok or type(text) ~= 'string' then
            return ''
        end
        return text:match('^%s*(.-)%s*$') or ''
    end

    local function CloseReport()
        if reportFrame then
            pcall(reportFrame.Hide, reportFrame)
        end
    end

    local function RefreshQuestion()
        if not reportQuestion then
            return
        end
        local last = type(ns.UI) == 'table' and ns.UI.lastQuestion or nil
        local text = '(todavía no has enviado ninguna pregunta)'
        if type(last) == 'string' and last:match('%S') then
            text = last
        end
        pcall(reportQuestion.SetText, reportQuestion, text)
    end

    local function SendReport()
        pcall(function()
            local note = TrimEdit()
            if note == '' and not confirmEmpty then
                confirmEmpty = true
                if reportWarning then
                    if reportWarning.SetText then
                        pcall(reportWarning.SetText, reportWarning,
                              'Escribe qué está mal (o pulsa Enviar otra vez para mandarlo sin nota).')
                    end
                    if reportWarning.Show then
                        pcall(reportWarning.Show, reportWarning)
                    end
                end
                return
            end

            local accepted = false
            if type(ns.Transport) == 'table' and type(ns.Transport.Send) == 'function' then
                local ok, result = pcall(ns.Transport.Send, note, nil, CurrentConversation(),
                                         'report')
                if ok then
                    accepted = result
                end
            end
            if reportFrame then
                pcall(reportFrame.Hide, reportFrame)
            end
            if accepted then
                Add('Informe enviado al companion.', colorDim)
            else
                Add('No se pudo enviar el informe.', colorMissing)
            end
        end)
    end

    local function NewText(parent, font, color)
        if type(ns.UI.CreateText) ~= 'function' then
            return nil
        end
        local ok, text = pcall(ns.UI.CreateText, parent, font, color)
        if ok then
            return text
        end
        return nil
    end

    local function NewPanel(parent)
        if type(ns.UI.CreatePanel) ~= 'function' then
            return nil
        end
        local ok, panel = pcall(ns.UI.CreatePanel, parent)
        if ok then
            return panel
        end
        return nil
    end

    local function NewButton(parent, text, width, height, onClick)
        if type(ns.UI.CreateButton) ~= 'function' then
            return nil
        end
        local ok, button = pcall(ns.UI.CreateButton, parent, text, width, height, onClick)
        if ok then
            return button
        end
        return nil
    end

    local function NewScroll(parent)
        local ok, scroll = pcall(CreateFrame, 'ScrollFrame', nil, parent,
                                 'UIPanelScrollFrameTemplate')
        if ok and scroll then
            return scroll
        end
        local ok2, fallback = pcall(CreateFrame, 'ScrollFrame', nil, parent)
        if ok2 and fallback then
            return fallback
        end
        return nil
    end

    local function EnsureReportFrame()
        if reportFrame then
            return reportFrame
        end
        if type(ns.UI.CreateWindow) ~= 'function' then
            return nil
        end

        local ok, frame = pcall(ns.UI.CreateWindow, 'AskForeverReportFrame', 440, 320,
                                'Informe de desarrollo')
        if not ok or not frame or not frame.body then
            return nil
        end

        frame:SetFrameStrata('DIALOG')
        frame:SetPoint('CENTER', UIParent, 'CENTER', 0, 0)
        if type(UISpecialFrames) == 'table' then
            table.insert(UISpecialFrames, 'AskForeverReportFrame')
        end

        local windowBody = frame.body
        local questionLabel = NewText(windowBody, fontSmall, colorSection)
        if questionLabel then
            questionLabel:SetPoint('TOPLEFT', windowBody, 'TOPLEFT', 10, -8)
            questionLabel:SetText('Última pregunta:')
        end

        reportQuestion = NewText(windowBody, fontBody, colorText)
        if reportQuestion then
            reportQuestion:SetPoint('TOPLEFT', windowBody, 'TOPLEFT', 10, -26)
            reportQuestion:SetPoint('RIGHT', windowBody, 'RIGHT', -10, 0)
            reportQuestion:SetJustifyH('LEFT')
            reportQuestion:SetHeight(38)
            if reportQuestion.SetWordWrap then
                pcall(reportQuestion.SetWordWrap, reportQuestion, true)
            end
            reportQuestion:SetText('')
        end

        local hint = NewText(windowBody, fontSmall, colorDim)
        if hint then
            local anchor = reportQuestion or questionLabel
            if anchor then
                hint:SetPoint('TOPLEFT', anchor, 'BOTTOMLEFT', 0, -6)
            else
                hint:SetPoint('TOPLEFT', windowBody, 'TOPLEFT', 10, -70)
            end
            hint:SetPoint('RIGHT', windowBody, 'RIGHT', -10, 0)
            hint:SetJustifyH('LEFT')
            hint:SetText('La respuesta y los datos que recibió la IA los añade el companion al informe.')
        end

        local wrongLabel = NewText(windowBody, fontBody, colorSection)
        if wrongLabel then
            local anchor = hint or reportQuestion or questionLabel
            if anchor then
                wrongLabel:SetPoint('TOPLEFT', anchor, 'BOTTOMLEFT', 0, -10)
            else
                wrongLabel:SetPoint('TOPLEFT', windowBody, 'TOPLEFT', 10, -110)
            end
            wrongLabel:SetText('¿Qué está mal?')
        end

        local panel = NewPanel(windowBody)
        if panel then
            local anchor = wrongLabel or hint or reportQuestion or questionLabel
            if anchor then
                panel:SetPoint('TOPLEFT', anchor, 'BOTTOMLEFT', 0, -6)
            else
                panel:SetPoint('TOPLEFT', windowBody, 'TOPLEFT', 10, -130)
            end
            panel:SetPoint('BOTTOMRIGHT', windowBody, 'BOTTOMRIGHT', -10, 72)

            reportScroll = NewScroll(panel)
            if reportScroll then
                reportScroll:SetPoint('TOPLEFT', panel, 'TOPLEFT', 6, -6)
                reportScroll:SetPoint('BOTTOMRIGHT', panel, 'BOTTOMRIGHT', -26, 6)
                local editOk, edit = pcall(CreateFrame, 'EditBox', nil, reportScroll)
                if editOk and edit then
                    reportEditBox = edit
                    edit:SetMultiLine(true)
                    if fontBody then
                        edit:SetFontObject(fontBody)
                    end
                    edit:SetWidth(360)
                    edit:SetHeight(400)
                    edit:SetAutoFocus(false)
                    edit:SetMaxLetters(0)
                    edit:SetScript('OnEscapePressed', CloseReport)
                    edit:SetScript('OnTextChanged', function()
                        if reportWarning and reportWarning.Hide then
                            pcall(reportWarning.Hide, reportWarning)
                        end
                    end)
                    reportScroll:SetScrollChild(edit)
                    local function Fit()
                        local width = reportScroll:GetWidth()
                        if width and width > 4 then
                            edit:SetWidth(width - 4)
                        end
                    end
                    reportScroll:SetScript('OnSizeChanged', Fit)
                end
            end
        end

        reportWarning = NewText(windowBody, fontSmall, colorMissing)
        if reportWarning then
            reportWarning:SetPoint('BOTTOMLEFT', windowBody, 'BOTTOMLEFT', 10, 46)
            reportWarning:SetPoint('RIGHT', windowBody, 'RIGHT', -10, 0)
            reportWarning:SetJustifyH('LEFT')
            reportWarning:SetText('')
            reportWarning:Hide()
        end

        local cancelButton = NewButton(windowBody, 'Cancelar', 90, 24, CloseReport)
        if cancelButton then
            cancelButton:SetPoint('BOTTOMRIGHT', windowBody, 'BOTTOMRIGHT', -10, 12)
        end
        local sendButton = NewButton(windowBody, 'Enviar', 90, 24, SendReport)
        if sendButton then
            if cancelButton then
                sendButton:SetPoint('RIGHT', cancelButton, 'LEFT', -8, 0)
            else
                sendButton:SetPoint('BOTTOMRIGHT', windowBody, 'BOTTOMRIGHT', -10, 12)
            end
        end

        frame:SetScript('OnHide', function()
            if reportEditBox and reportEditBox.ClearFocus then
                pcall(reportEditBox.ClearFocus, reportEditBox)
            end
        end)

        reportFrame = frame
        return frame
    end

    local function OpenReport()
        pcall(function()
            local frame = EnsureReportFrame()
            if not frame then
                return
            end
            RefreshQuestion()
            confirmEmpty = false
            if reportWarning and reportWarning.Hide then
                pcall(reportWarning.Hide, reportWarning)
            end
            if reportEditBox and reportEditBox.SetText then
                pcall(reportEditBox.SetText, reportEditBox, '')
            end
            if reportScroll and reportScroll.SetVerticalScroll then
                pcall(reportScroll.SetVerticalScroll, reportScroll, 0)
            end
            if frame.Raise then
                pcall(frame.Raise, frame)
            end
            frame:Show()
            if reportEditBox and reportEditBox.SetFocus then
                pcall(reportEditBox.SetFocus, reportEditBox)
            end
        end)
    end

    local ok, button = pcall(ns.UI.CreateButton, body, 'Informe', 80, 24, OpenReport)
    if not ok or not button then
        return nil
    end
    if type(button.SetPoint) == 'function' then
        pcall(button.SetPoint, button, 'BOTTOMRIGHT', body, 'BOTTOMRIGHT', -8, 16)
    end
    return button
end
