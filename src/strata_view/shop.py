"""The upgrade shop in the 3D window.

The same shop as the 2D window's PygameShopScreen and the terminal's menu:
the same upgrades (progression.shop), the same purchase rule
(purchaseUpgrade), the same keys and the same information on screen, drawn
as screen-space labels and panels over the board. Only the drawing differs.
"""

from preponderous.graphik.grid3d import centredLabel, wrapText
from progression.shop import listUpgrades, purchaseUpgrade
from strata_view.scene import BUTTON_GAP, overlapsArea

# SDL scancodes the shop answers to, matching PygameShopScreen's keys.
SHOP_UP = {82, 26}  # Up, W
SHOP_DOWN = {81, 22}  # Down, S
SHOP_BUY = {40, 88, 44}  # Enter, keypad Enter, Space
SHOP_CLOSE = {41, 19}  # Escape, P

SHOP_HINT = "W/S or Up/Down: navigate   Enter: purchase   Esc/P: close"
SHOP_TITLE = "Ophidian Shop"

TITLE_COLOR = (1.0, 1.0, 1.0, 1.0)
CURRENCY_COLOR = (1.0, 0.86, 0.25, 1.0)
OWNED_COLOR = (0.45, 0.90, 0.45, 1.0)
ROW_COLOR = (1.0, 1.0, 1.0, 1.0)
DESCRIPTION_COLOR = (0.71, 0.71, 0.71, 1.0)
HINT_COLOR = (0.63, 0.63, 0.63, 1.0)
BACKDROP_COLOR = (0.02, 0.02, 0.03, 0.88)
SELECTED_COLOR = (0.24, 0.24, 0.24, 0.95)


def setText(text, room, size, smallest):
    """(size, lines) for text that has to fit across `room` pixels: as it
    is when it fits; otherwise set smaller, down to `smallest`, and wrapped
    rather than cut, so all of it can be read on a phone. Strata's font is
    one pixel size wide per character."""
    if len(text) * size <= room:
        return size, [text]
    size = max(smallest, int(room / max(1, len(text))))
    if len(text) * size <= room:
        return size, [text]
    return size, wrapText([text], room, size)


class StrataShop:
    """The shop's state while it is open. Keys go to handleScancode; the HUD
    draws overlay() over the board each frame."""

    def __init__(self, saveManager):
        self.saveManager = saveManager
        self.upgrades = listUpgrades()
        self.selectedIndex = 0
        self.message = None

    def handleScancode(self, scancode):
        """Returns True while the shop stays open, False once it closes."""
        if scancode in SHOP_UP:
            self.selectedIndex = (self.selectedIndex - 1) % len(self.upgrades)
        elif scancode in SHOP_DOWN:
            self.selectedIndex = (self.selectedIndex + 1) % len(self.upgrades)
        elif scancode in SHOP_BUY:
            success, message = purchaseUpgrade(
                self.saveManager.data, self.upgrades[self.selectedIndex]["id"]
            )
            if success:
                self.saveManager.save()
            self.message = message
        elif scancode in SHOP_CLOSE:
            return False
        return True

    def overlay(self, width, height, Label, Panel, fitText, keepClear=None):
        """Labels and panels for the shop, in the 2D shop's layout. The
        title moves down below `keepClear` ((x, y, width, height): the
        browser page's 2D/3D button) when it would run under it."""
        data = self.saveManager.data
        owned = data.get("purchasedUpgrades", [])
        panels = [Panel(0, 0, width, height, BACKDROP_COLOR)]
        labels = []

        room = width - 2 * 28

        def centred(text, y, size, color, smallest=12):
            """Centred lines from y down; returns how much further down than
            one line they reach (0 for a line that fits)."""
            size, lines = setText(text, room, size, smallest)
            for index, line in enumerate(lines):
                labels.append(
                    centredLabel(
                        line, width / 2, y + index * (size + 6), size, color, rise=0
                    )
                )
            return (len(lines) - 1) * (size + 6)

        titleY = 22
        titleSize, titleLines = setText(SHOP_TITLE, room, 28, 18)
        titleWidth = titleSize * max(len(line) for line in titleLines)
        if keepClear is not None and overlapsArea(
            width / 2 - titleWidth / 2,
            titleY,
            titleWidth,
            len(titleLines) * (titleSize + 6),
            keepClear,
        ):
            titleY = keepClear[1] + keepClear[3] + BUTTON_GAP
        y = titleY + 38 + centred(SHOP_TITLE, titleY, 28, TITLE_COLOR, smallest=18)
        y += centred(
            "Currency: {}".format(data.get("currency", 0)), y, 18, CURRENCY_COLOR
        )
        # Descriptions wrap rather than being cut short, so the whole text
        # the 2D shop shows is readable here too (graphik's wrapText
        # measures Strata's monospaced font).
        descriptionSize, lineGap = 12, 18
        maxWidth = width - 2 * 40
        rowY = y + 40
        for index, upgrade in enumerate(self.upgrades):
            isOwned = upgrade["id"] in owned
            name = "{} - cost {}{}".format(
                upgrade["name"], upgrade["cost"], " (owned)" if isOwned else ""
            )
            nameSize, nameLines = setText(name, room, 20, 14)
            nameExtra = (len(nameLines) - 1) * (nameSize + 6)
            lines = wrapText([upgrade["description"]], maxWidth, descriptionSize)
            rowHeight = 30 + nameExtra + lineGap * len(lines) + 14
            if index == self.selectedIndex:
                panels.append(
                    Panel(20, rowY - 6, width - 40, rowHeight - 8, SELECTED_COLOR)
                )
            centred(name, rowY, 20, OWNED_COLOR if isOwned else ROW_COLOR, 14)
            for lineIndex, line in enumerate(lines):
                centred(
                    line,
                    rowY + 28 + nameExtra + lineGap * lineIndex,
                    descriptionSize,
                    DESCRIPTION_COLOR,
                )
            rowY += rowHeight
        hintY = rowY + 10
        hintY += centred(SHOP_HINT, hintY, 14, HINT_COLOR, smallest=11)
        if self.message:
            centred(self.message, hintY + 28, 16, CURRENCY_COLOR)
        return labels, panels
