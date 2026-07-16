from progression.shop import listUpgrades, purchaseUpgrade

# @author Daniel McCoy Stephenson
# @since July 4th, 2026


class PygameShopScreen:
    """Self-contained in-window shop screen.

    Its own poll -> handle -> draw -> present loop, the same shape as the
    main pygame loop but scoped to just the shop, so purchasing upgrades is
    visible and interactive without ever blocking on stdin behind the
    graphical window (unlike the text-UI shop, which is fine using input()
    since the console *is* its UI).
    """

    def __init__(self, pygame, graphik, getGameDisplay, config, saveManager, onQuit):
        self.pygame = pygame
        self.graphik = graphik
        self.getGameDisplay = getGameDisplay
        self.config = config
        self.saveManager = saveManager
        self.onQuit = onQuit

    def run(self):
        upgrades = listUpgrades()
        selectedIndex = 0
        shopMessage = None
        viewingShop = True
        while viewingShop:
            for event in self.pygame.event.get():
                if event.type == self.pygame.QUIT:
                    self.onQuit()
                elif event.type == self.pygame.KEYDOWN:
                    if event.key in (self.pygame.K_UP, self.pygame.K_w):
                        selectedIndex = (selectedIndex - 1) % len(upgrades)
                    elif event.key in (self.pygame.K_DOWN, self.pygame.K_s):
                        selectedIndex = (selectedIndex + 1) % len(upgrades)
                    elif event.key in (self.pygame.K_RETURN, self.pygame.K_SPACE):
                        success, message = purchaseUpgrade(
                            self.saveManager.data, upgrades[selectedIndex]["id"]
                        )
                        if success:
                            self.saveManager.save()
                        # drawn directly by draw() below rather than through
                        # a shared notify()/banner path - this loop has its
                        # own draw/present cycle, so a banner meant for the
                        # main loop would never actually be seen in here
                        print(message)
                        shopMessage = message
                    elif event.key in (self.pygame.K_ESCAPE, self.pygame.K_p):
                        viewingShop = False
            self.draw(upgrades, selectedIndex, shopMessage)
            self.pygame.display.update()
            self.pygame.time.delay(16)

    def draw(self, upgrades, selectedIndex, shopMessage=None):
        gameDisplay = self.getGameDisplay()
        width, height = gameDisplay.get_size()
        self.graphik.drawRectangle(0, 0, width, height, self.config.black)
        self.graphik.drawText("Ophidian Shop", width // 2, 30, 28, self.config.white)
        self.graphik.drawText(
            "Currency: {}".format(self.saveManager.data.get("currency", 0)),
            width // 2,
            60,
            18,
            self.config.yellow,
        )
        purchasedUpgrades = self.saveManager.data.get("purchasedUpgrades", [])
        rowHeight = 60
        startY = 100
        for index, upgrade in enumerate(upgrades):
            rowY = startY + index * rowHeight
            if index == selectedIndex:
                self.graphik.drawRectangle(
                    20, rowY - 5, width - 40, rowHeight - 10, (60, 60, 60)
                )
            owned = upgrade["id"] in purchasedUpgrades
            label = "{} - cost {}{}".format(
                upgrade["name"], upgrade["cost"], " (owned)" if owned else ""
            )
            color = self.config.green if owned else self.config.white
            self.graphik.drawText(label, width // 2, rowY + 12, 20, color)
            self.graphik.drawText(
                upgrade["description"], width // 2, rowY + 34, 14, (180, 180, 180)
            )
        hintY = startY + len(upgrades) * rowHeight + 10
        self.graphik.drawText(
            "W/S or Up/Down: navigate   Enter: purchase   Esc/P: close",
            width // 2,
            hintY,
            14,
            (160, 160, 160),
        )
        if shopMessage:
            self.graphik.drawText(
                shopMessage, width // 2, hintY + 24, 16, self.config.yellow
            )
