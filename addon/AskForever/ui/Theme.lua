local _, ns = ...

ns.UI = ns.UI or {}

local function hex(value)
    return {
        tonumber(value:sub(1, 2), 16) / 255,
        tonumber(value:sub(3, 4), 16) / 255,
        tonumber(value:sub(5, 6), 16) / 255,
        1,
    }
end

local function font(name, fallback)
    return _G[name] or _G[fallback]
end

ns.UI.Theme = {
    colors = {
        windowBg = hex('15100b'),
        barBg = hex('1d160f'),
        panelBg = hex('191209'),
        highlightBg = hex('221910'),
        windowBorder = hex('5a4630'),
        panelBorder = hex('2e2418'),
        title = hex('e6b84a'),
        sectionLabel = hex('c9a24a'),
        text = hex('e9dfc8'),
        textDim = hex('a3957c'),
        ok = hex('7fe08a'),
        missing = hex('ff6b62'),
        amber = hex('f2d43a'),
        orange = hex('ff8a3d'),
        primaryBg = hex('6b1d12'),
        primaryBorder = hex('b8914a'),
    },
    font = {
        title = font('GameFontNormalLarge', 'GameFontNormal'),
        body = font('GameFontHighlight', 'GameFontNormal'),
        small = font('GameFontHighlightSmall', 'GameFontNormalSmall'),
    },
    backdrop = {
        bgFile = 'Interface\\Buttons\\WHITE8X8',
        edgeFile = 'Interface\\Buttons\\WHITE8X8',
        edgeSize = 1,
    },
    icon = 'Interface\\AddOns\\AskForever\\Media\\Icon',
}
