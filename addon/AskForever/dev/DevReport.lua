local _, ns = ...

ns.DevReport = {}

local MAX_REPORTS = 50
local ROW_HEIGHT = 44

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
    local reportListTitle
    local reportListScroll
    local reportListContent
    local reportListRows = {}
    local reportEmpty
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

    local function CurrentQuestionText()
        local last = type(ns.UI) == 'table' and ns.UI.lastQuestion or nil
        if type(last) == 'string' and last:match('%S') then
            return last
        end
        return '(todavía no has enviado ninguna pregunta)'
    end

    local function NextMessageId()
        if type(AskForeverDB) ~= 'table' then
            AskForeverDB = {}
        end
        if type(AskForeverDB.transport) ~= 'table' then
            AskForeverDB.transport = { msgId = 0 }
        end
        local current = tonumber(AskForeverDB.transport.msgId) or 0
        local nextId = current + 1
        if nextId > 65535 then
            nextId = 1
        end
        return nextId
    end

    local function NextRid()
        local ok, stamp = pcall(date, '%Y%m%d-%H%M%S')
        if not ok or type(stamp) ~= 'string' then
            stamp = tostring(math.floor(time() or 0))
        end
        return stamp .. '-' .. tostring(NextMessageId())
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

    local function TruncateLine(value, max)
        local text = tostring(value or ''):gsub('%s+', ' ')
        text = text:gsub('^%s*(.-)%s*$', '%1')
        if #text <= max then
            return text
        end
        local cut = text:sub(1, max):gsub('[\192-\255][\128-\191]*$', '')
        return cut .. '...'
    end

    local function ShowWarning(text)
        if not reportWarning then
            return
        end
        if reportWarning.SetText then
            pcall(reportWarning.SetText, reportWarning, text)
        end
        if reportWarning.Show then
            pcall(reportWarning.Show, reportWarning)
        end
    end

    local function GetRecords()
        if type(AskForeverDB) ~= 'table' then
            AskForeverDB = {}
        end
        if type(AskForeverDB.devReports) ~= 'table' then
            AskForeverDB.devReports = {}
        end
        return AskForeverDB.devReports
    end

    local function RefreshReports()
        if not reportFrame then
            return
        end
        local records = GetRecords()
        local count = math.min(#records, MAX_REPORTS)
        if reportListTitle then
            pcall(reportListTitle.SetText, reportListTitle,
                  'Informes abiertos (' .. count .. ')')
        end
        if reportEmpty then
            if count == 0 then
                pcall(reportEmpty.Show, reportEmpty)
            else
                pcall(reportEmpty.Hide, reportEmpty)
            end
        end
        for index = 1, MAX_REPORTS do
            local row = reportListRows[index]
            if row then
                local record = index <= count and records[index] or nil
                if type(record) == 'table' then
                    if row.date and row.date.SetText then
                        local ok, stamp = pcall(date, '%d/%m %H:%M', record.time or 0)
                        pcall(row.date.SetText, row.date, ok and tostring(stamp or '') or '')
                    end
                    if row.question and row.question.SetText then
                        pcall(row.question.SetText, row.question,
                              TruncateLine(record.question, 40))
                    end
                    if row.note and row.note.SetText then
                        pcall(row.note.SetText, row.note,
                              TruncateLine(record.note, 40))
                    end
                    pcall(row.Show, row)
                else
                    pcall(row.Hide, row)
                end
            end
        end
        if reportListContent then
            pcall(reportListContent.SetHeight, reportListContent,
                  math.max(count * ROW_HEIGHT, 1))
        end
        if reportListScroll and reportListScroll.SetVerticalScroll then
            pcall(reportListScroll.SetVerticalScroll, reportListScroll, 0)
        end
        if reportWarning and reportWarning.Hide then
            pcall(reportWarning.Hide, reportWarning)
        end
    end

    local function CloseRecord(index)
        pcall(function()
            local records = GetRecords()
            local record = records[index]
            if type(record) ~= 'table' or not record.rid then
                return
            end
            local accepted = false
            if type(ns.Transport) == 'table' and type(ns.Transport.Send) == 'function' then
                local ok, result = pcall(ns.Transport.Send, '', nil, CurrentConversation(),
                                         'report-close', { rid = record.rid })
                if ok then
                    accepted = result
                end
            end
            if accepted then
                table.remove(records, index)
                RefreshReports()
            else
                ShowWarning('No se pudo enviar el cierre (¿en combate o enviando otro mensaje?)')
            end
        end)
    end

    local function SendReport()
        pcall(function()
            local note = TrimEdit()
            if note == '' and not confirmEmpty then
                confirmEmpty = true
                ShowWarning('Escribe qué está mal (o pulsa Enviar otra vez para mandarlo sin nota).')
                return
            end

            local rid = NextRid()
            local accepted = false
            if type(ns.Transport) == 'table' and type(ns.Transport.Send) == 'function' then
                local ok, result = pcall(ns.Transport.Send, note, nil, CurrentConversation(),
                                         'report', { rid = rid })
                if ok then
                    accepted = result
                end
            end
            if not accepted then
                ShowWarning('No se pudo enviar el informe.')
                Add('No se pudo enviar el informe.', colorMissing)
                return
            end

            local records = GetRecords()
            table.insert(records, 1, {
                rid = rid,
                time = time(),
                question = CurrentQuestionText(),
                note = note,
            })
            while #records > MAX_REPORTS do
                table.remove(records, #records)
            end
            confirmEmpty = false
            if reportEditBox and reportEditBox.SetText then
                pcall(reportEditBox.SetText, reportEditBox, '')
            end
            RefreshReports()
            Add('Informe enviado al companion.', colorDim)
            if reportEditBox and reportEditBox.SetFocus then
                pcall(reportEditBox.SetFocus, reportEditBox)
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

        local ok, frame = pcall(ns.UI.CreateWindow, 'AskForeverReportFrame', 440, 480,
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
            panel:SetPoint('BOTTOMRIGHT', windowBody, 'BOTTOMRIGHT', -10, 232)

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
            reportWarning:SetPoint('BOTTOMLEFT', windowBody, 'BOTTOMLEFT', 10, 206)
            reportWarning:SetPoint('RIGHT', windowBody, 'RIGHT', -10, 0)
            reportWarning:SetJustifyH('LEFT')
            reportWarning:SetText('')
            reportWarning:Hide()
        end

        local cancelButton = NewButton(windowBody, 'Cancelar', 90, 24, CloseReport)
        if cancelButton then
            cancelButton:SetPoint('BOTTOMRIGHT', windowBody, 'BOTTOMRIGHT', -10, 172)
        end
        local sendButton = NewButton(windowBody, 'Enviar', 90, 24, SendReport)
        if sendButton then
            if cancelButton then
                sendButton:SetPoint('RIGHT', cancelButton, 'LEFT', -8, 0)
            else
                sendButton:SetPoint('BOTTOMRIGHT', windowBody, 'BOTTOMRIGHT', -10, 172)
            end
        end

        reportListTitle = NewText(windowBody, fontBody, colorSection)
        if reportListTitle then
            reportListTitle:SetPoint('BOTTOMLEFT', windowBody, 'BOTTOMLEFT', 10, 146)
            reportListTitle:SetText('Informes abiertos (0)')
        end

        local listPanel = NewPanel(windowBody)
        if listPanel then
            listPanel:SetPoint('BOTTOMLEFT', windowBody, 'BOTTOMLEFT', 10, 30)
            listPanel:SetPoint('BOTTOMRIGHT', windowBody, 'BOTTOMRIGHT', -10, 30)
            listPanel:SetHeight(110)

            reportListScroll = NewScroll(listPanel)
            if reportListScroll then
                reportListScroll:SetPoint('TOPLEFT', listPanel, 'TOPLEFT', 6, -6)
                reportListScroll:SetPoint('BOTTOMRIGHT', listPanel, 'BOTTOMRIGHT', -26, 6)
                local contentOk, content = pcall(CreateFrame, 'Frame', nil, reportListScroll)
                if contentOk and content then
                    reportListContent = content
                    content:SetWidth(320)
                    content:SetHeight(1)
                    reportListScroll:SetScrollChild(content)
                    local function FitList()
                        local width = reportListScroll:GetWidth()
                        if width and width > 4 then
                            content:SetWidth(width - 4)
                        end
                    end
                    reportListScroll:SetScript('OnSizeChanged', FitList)

                    for index = 1, MAX_REPORTS do
                        local row = CreateFrame('Frame', nil, content)
                        row:SetHeight(ROW_HEIGHT)
                        row:SetPoint('TOPLEFT', content, 'TOPLEFT', 0,
                                     -((index - 1) * ROW_HEIGHT))
                        row:SetPoint('RIGHT', content, 'RIGHT', 0, 0)
                        row.date = NewText(row, fontSmall, colorDim)
                        if row.date then
                            row.date:SetPoint('TOPLEFT', row, 'TOPLEFT', 4, -2)
                        end
                        row.question = NewText(row, fontBody, colorText)
                        if row.question then
                            row.question:SetPoint('TOPLEFT', row, 'TOPLEFT', 4, -15)
                            row.question:SetPoint('RIGHT', row, 'RIGHT', -70, 0)
                            row.question:SetJustifyH('LEFT')
                            if row.question.SetWordWrap then
                                pcall(row.question.SetWordWrap, row.question, false)
                            end
                        end
                        row.note = NewText(row, fontSmall, colorDim)
                        if row.note then
                            row.note:SetPoint('TOPLEFT', row, 'TOPLEFT', 4, -28)
                            row.note:SetPoint('RIGHT', row, 'RIGHT', -70, 0)
                            row.note:SetJustifyH('LEFT')
                            if row.note.SetWordWrap then
                                pcall(row.note.SetWordWrap, row.note, false)
                            end
                        end
                        row.close = NewButton(row, 'Cerrar', 60, 20, function()
                            CloseRecord(index)
                        end)
                        if row.close then
                            row.close:SetPoint('RIGHT', row, 'RIGHT', -4, 0)
                        end
                        row:Hide()
                        reportListRows[index] = row
                    end
                end
            end

            reportEmpty = NewText(listPanel, fontSmall, colorDim)
            if reportEmpty then
                reportEmpty:SetPoint('CENTER', listPanel, 'CENTER', 0, 0)
                reportEmpty:SetText('(no hay informes abiertos)')
                reportEmpty:Hide()
            end
        end

        local listHint = NewText(windowBody, fontSmall, colorDim)
        if listHint then
            listHint:SetPoint('BOTTOMLEFT', windowBody, 'BOTTOMLEFT', 10, 6)
            listHint:SetPoint('RIGHT', windowBody, 'RIGHT', -10, 0)
            listHint:SetJustifyH('LEFT')
            listHint:SetText('Si Claude ya cerró un informe, ciérralo aquí también: '
                             .. 'el companion verá que ya no existe.')
        end

        frame:SetScript('OnHide', function()
            if reportEditBox and reportEditBox.ClearFocus then
                pcall(reportEditBox.ClearFocus, reportEditBox)
            end
        end)

        reportFrame = frame
        return frame
    end

    local function RefreshQuestion()
        if not reportQuestion then
            return
        end
        pcall(reportQuestion.SetText, reportQuestion, CurrentQuestionText())
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
            RefreshReports()
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
