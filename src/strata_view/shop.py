"""The upgrade shop in the 3D window.

The same shop as the 2D window's PygameShopScreen and the terminal's menu:
the same upgrades (progression.shop), the same purchase rule
(purchaseUpgrade), the same keys and the same information on screen, drawn
as screen-space labels and panels over the board. Only the drawing differs.
"""

from progression.shop import listUpgrades, purchaseUpgrade
from ui.text_wrap import wrapLineToWidth

# SDL scancodes the shop answers to, matching PygameShopScreen's keys.
SHOP_UP = {82, 26}  # Up, W
SHOP_DOWN = {81, 22}  # Down, S
SHOP_BUY = {40, 88, 44}  # Enter, keypad Enter, Space
SHOP_CLOSE = {41, 19}  # Escape, P

SHOP_HINT = "W/S or Up/Down: navigate   Enter: purchase   Esc/P: close"

TITLE_COLOR = (1.0, 1.0, 1.0, 1.0)
CURRENCY_COLOR = (1.0, 0.86, 0.25, 1.0)
OWNED_COLOR = (0.45, 0.90, 0.45, 1.0)
ROW_COLOR = (1.0, 1.0, 1.0, 1.0)
DESCRIPTION_COLOR = (0.71, 0.71, 0.71, 1.0)
HINT_COLOR = (0.63, 0.63, 0.63, 1.0)
BACKDROP_COLOR = (0.02, 0.02, 0.03, 0.88)
SELECTED_COLOR = (0.24, 0.24, 0.24, 0.95)


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

    def overlay(self, width, height, Label, Panel, fitText):
        """Labels and panels for the shop, in the 2D shop's layout."""
        data = self.saveManager.data
        owned = data.get("purchasedUpgrades", [])
        panels = [Panel(0, 0, width, height, BACKDROP_COLOR)]
        labels = []

        def centred(text, y, size, color):
            text = fitText(text, width, size, margin=28)
            labels.append(Label(text, (width - size * len(text)) / 2, y, size, color))

        centred("Ophidian Shop", 22, 28, TITLE_COLOR)
        centred("Currency: {}".format(data.get("currency", 0)), 60, 18, CURRENCY_COLOR)
        # Descriptions wrap rather than being cut short, so the whole text
        # the 2D shop shows is readable here too. The built-in font is
        # monospaced, about one pixel size wide per character.
        descriptionSize, lineGap = 12, 18
        maxWidth = width - 2 * 40
        rowY = 100
        for index, upgrade in enumerate(self.upgrades):
            lines = wrapLineToWidth(
                upgrade["description"],
                lambda text: descriptionSize * len(text),
                maxWidth,
            )
            rowHeight = 30 + lineGap * len(lines) + 14
            if index == self.selectedIndex:
                panels.append(
                    Panel(20, rowY - 6, width - 40, rowHeight - 8, SELECTED_COLOR)
                )
            isOwned = upgrade["id"] in owned
            centred(
                "{} - cost {}{}".format(
                    upgrade["name"], upgrade["cost"], " (owned)" if isOwned else ""
                ),
                rowY,
                20,
                OWNED_COLOR if isOwned else ROW_COLOR,
            )
            for lineIndex, line in enumerate(lines):
                centred(
                    line,
                    rowY + 28 + lineGap * lineIndex,
                    descriptionSize,
                    DESCRIPTION_COLOR,
                )
            rowY += rowHeight
        hintY = rowY + 10
        centred(SHOP_HINT, hintY, 14, HINT_COLOR)
        if self.message:
            centred(self.message, hintY + 28, 16, CURRENCY_COLOR)
        return labels, panels
