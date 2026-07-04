import random
import time
from config.config import Config
from lib.pyenvlib.entity import Entity
from lib.pyenvlib.environment import Environment
from food.food import Food
from lib.pyenvlib.grid import Grid
from lib.pyenvlib.location import Location
from snake.snakePart import SnakePart
from progression.save import SaveManager
from progression.obituary import formatObituaryScreen
from progression.cosmetics import checkForNewUnlocks, getNextCosmeticId, getSkinColor, getSkinName
from progression.shop import currencyEarnedForRun, listUpgrades, purchaseUpgrade
from progression.lore import generateOphidianName, getBiome
from progression.ascension import (
    computeGridSizeForLevel,
    shouldAscend,
    applyAscension,
)


# @author Daniel McCoy Stephenson
# @since August 6th, 2022
class Ophidian:
    def __init__(self, useTextUI=False):
        self.config = Config()
        self.config.useTextUI = useTextUI
        
        # Import pygame and graphik only if not using text UI
        if not self.config.useTextUI:
            import pygame
            self.pygame = pygame
            from lib.graphik.src.graphik import Graphik
            
            pygame.init()
            self.initializeGameDisplay()
            pygame.display.set_icon(pygame.image.load("src/media/icon.PNG"))
            self.graphik = Graphik(self.gameDisplay)
        else:
            from textui.textrenderer import TextRenderer
            self.pygame = None
            self.textRenderer = TextRenderer(self.config)
            self.textRenderer.enableRawMode()
        
        self.saveManager = SaveManager()
        if self.saveManager.data["ophidianName"] is None:
            self.saveManager.data["ophidianName"] = generateOphidianName()
            self.saveManager.save()
        self.lastObituary = None
        self.running = True
        self.snakeParts = []
        self.level = 1
        # base tick speed captured once so shop/ascension bonuses can derive
        # an effective tick speed each run without compounding across restarts
        self.baseTickSpeed = self.config.tickSpeed
        self.ascensionBonus = None
        # queue (not a single slot) so back-to-back notify() calls in the same
        # tick - e.g. an ascension message immediately followed by the next
        # biome's arrival message - don't clobber each other before either is
        # ever drawn; each is shown in turn instead of only the last one.
        self.uiMessageQueue = []
        self.uiMessageExpiresAt = None
        self.initialize()
        self.tick = 0
        self.score = 0
        self.changedDirectionThisTick = False
        self.collision = False

    def initializeGameDisplay(self):
        if self.config.useTextUI:
            return  # No display needed for text UI
        
        if self.config.fullscreen:
            self.gameDisplay = self.pygame.display.set_mode(
                (self.config.displayWidth, self.config.displayHeight), self.pygame.FULLSCREEN
            )
        else:
            self.gameDisplay = self.pygame.display.set_mode(
                (self.config.displayWidth, self.config.displayHeight), self.pygame.RESIZABLE
            )

    def initializeLocationWidthAndHeight(self):
        if self.config.useTextUI:
            return  # Not needed for text UI
        
        x, y = self.gameDisplay.get_size()
        self.locationWidth = x / self.environment.getGrid().getRows()
        self.locationHeight = y / self.environment.getGrid().getColumns()

    # Draws the environment in its entirety.
    def drawEnvironment(self):
        if self.config.useTextUI:
            return  # Rendering handled separately in text UI
        
        for locationId in self.environment.getGrid().getLocations():
            location = self.environment.getGrid().getLocation(locationId)
            self.drawLocation(
                location,
                location.getX() * self.locationWidth - 1,
                location.getY() * self.locationHeight - 1,
                self.locationWidth + 2,
                self.locationHeight + 2,
            )

    # Returns the color that a location should be displayed as.
    def getColorOfLocation(self, location):
        if location == -1:
            color = self.config.white
        else:
            color = self.config.white
            if location.getNumEntities() > 0:
                topEntityId = list(location.getEntities().keys())[-1]
                topEntity = location.getEntity(topEntityId)
                return topEntity.getColor()
        return color

    # Draws a location at a specified position.
    def drawLocation(self, location, xPos, yPos, width, height):
        if self.collision == True:
            color = self.config.red
        else:
            color = self.getColorOfLocation(location)
        self.graphik.drawRectangle(xPos, yPos, width, height, color)

    def calculateScore(self):
        length = len(self.snakeParts)
        numLocations = len(self.environment.grid.getLocations())
        percentage = int(length / numLocations * 100)
        self.score = length * percentage

    def displayStatsInConsole(self):
        length = len(self.snakeParts)
        numLocations = len(self.environment.grid.getLocations())
        percentage = int(length / numLocations * 100)
        print(
            "The ophidian had a length of",
            length,
            "and took up",
            percentage,
            "percent of the world.",
        )
        print("Score:", self.score)
        print("-----")

    def checkForLevelProgressAndReinitialize(self):
        if (
            len(self.snakeParts)
            > len(self.environment.grid.getLocations())
            * self.config.levelProgressPercentageRequired
        ):
            if shouldAscend(
                self.level,
                self.config.gridSize,
                self.config.minGridSize,
                self.config.maxGridSize,
            ):
                self.ascensionBonus = applyAscension(self.saveManager.data)
                self.saveManager.save()
                self.level = 1
                self.notify(
                    f"The ophidian ascends! (Ascension {self.saveManager.data['ascensionLevel']})"
                )
            else:
                self.level += 1
        self.initialize()

    def recordCurrentRun(self, causeOfDeath):
        # bank currency earned this run before folding it into lifetime stats;
        # recordRun() below calls saveManager.save() which persists both
        earnedCurrency = currencyEarnedForRun(len(self.snakeParts))
        self.saveManager.data["currency"] = self.saveManager.data.get("currency", 0) + earnedCurrency
        self.lastObituary = self.saveManager.recordRun(
            length=len(self.snakeParts),
            level=self.level,
            ticks=self.tick,
            score=self.score,
            causeOfDeath=causeOfDeath,
        )
        newlyUnlocked = checkForNewUnlocks(self.saveManager.data)
        if newlyUnlocked:
            for skinId in newlyUnlocked:
                self.notify("New skin unlocked: " + getSkinName(skinId) + "!")
            self.saveManager.save()
        self.printObituaryToConsole()

    def printObituaryToConsole(self):
        """Prints the just-recorded obituary and lifetime chronicle to the console.

        Called once per run-ending event (from recordCurrentRun), so this
        never doubles up even when restartUponCollision immediately starts a
        new life.
        """
        for line in formatObituaryScreen(
            self.lastObituary, self.saveManager.data["lifetimeStats"]
        ):
            print(line)
        print("-----")

    def notify(self, message):
        """Player-facing feedback: always printed to console (which is the
        whole UI in text mode) and, in pygame mode, also queued as a brief
        on-screen banner via drawUiMessage() so it isn't invisible behind the
        graphical window. Queued rather than a single slot, so several
        notify() calls firing back-to-back (e.g. an ascension message
        immediately followed by the next run's biome-arrival message) each
        get their turn instead of the earlier one being silently lost."""
        print(message)
        if not self.config.useTextUI:
            self.uiMessageQueue.append(message)

    def drawUiMessage(self):
        if self.config.useTextUI or not self.uiMessageQueue:
            return
        if self.uiMessageExpiresAt is None:
            self.uiMessageExpiresAt = time.time() + 2.0
        if time.time() >= self.uiMessageExpiresAt:
            self.uiMessageQueue.pop(0)
            self.uiMessageExpiresAt = None
            if not self.uiMessageQueue:
                return
        width, _ = self.gameDisplay.get_size()
        self.graphik.drawRectangle(0, 0, width, 30, self.config.black)
        self.graphik.drawText(self.uiMessageQueue[0], width // 2, 15, 16, self.config.white)

    def renderObituaryScreen(self):
        """Briefly overlays the obituary + chronicle screen on the pygame display.

        No-op for the text UI (which gets its version via
        printObituaryToConsole) and when there's nothing recorded yet.
        """
        if self.config.useTextUI or self.lastObituary is None:
            return
        lines = formatObituaryScreen(
            self.lastObituary, self.saveManager.data["lifetimeStats"]
        )
        width, height = self.gameDisplay.get_size()
        self.graphik.drawRectangle(0, 0, width, height, self.config.black)
        lineHeight = 24
        startY = height // 2 - (len(lines) * lineHeight) // 2
        for index, line in enumerate(lines):
            if not line:
                continue
            self.graphik.drawText(
                line, width // 2, startY + index * lineHeight, 18, self.config.white
            )
        self.pygame.display.update()
        time.sleep(1.5)

    def quitApplication(self):
        if not self.collision:
            self.recordCurrentRun("quit")
            self.renderObituaryScreen()
        self.displayStatsInConsole()
        if self.config.useTextUI:
            self.textRenderer.disableRawMode()
        else:
            self.pygame.quit()
        quit()

    def getLocation(self, entity: Entity):
        locationID = entity.getLocationID()
        grid = self.environment.getGrid()
        return grid.getLocation(locationID)

    def getLocationAndGrid(self, entity: Entity):
        locationID = entity.getLocationID()
        grid = self.environment.getGrid()
        return grid, grid.getLocation(locationID)

    def moveEntity(self, entity: Entity, direction):
        grid, location = self.getLocationAndGrid(entity)

        newLocation = -1
        # get new location
        if direction == 0:
            newLocation = grid.getUp(location)
        elif direction == 1:
            newLocation = grid.getLeft(location)
        elif direction == 2:
            newLocation = grid.getDown(location)
        elif direction == 3:
            newLocation = grid.getRight(location)

        if newLocation == -1:
            # location doesn't exist, we're at a border
            return

        # if new location has a snake part already
        for eid in newLocation.getEntities():
            e = newLocation.getEntity(eid)
            if type(e) is SnakePart:
                # second_wind upgrade: the first collision each run is
                # converted into a near-miss instead of ending the run;
                # only the second collision in the same run actually kills
                if self.secondWindAvailableThisRun:
                    self.secondWindAvailableThisRun = False
                    self.notify("The ophidian narrowly survives!")
                    return
                # we have a collision
                self.collision = True
                print("The ophidian collides with itself and ceases to be.")
                self.recordCurrentRun("collision")
                if not self.config.useTextUI:
                    self.drawEnvironment()
                    self.pygame.display.update()
                time.sleep(self.config.tickSpeed * 20)
                if not self.config.useTextUI:
                    self.renderObituaryScreen()
                if self.config.restartUponCollision:
                    self.checkForLevelProgressAndReinitialize()
                else:
                    self.running = False
                return

        # move entity
        location.removeEntity(entity)
        newLocation.addEntity(entity)
        entity.lastPosition = location

        # move all attached snake parts
        if entity.hasPrevious():
            self.movePreviousSnakePart(entity)

        if self.config.debug:
            print(
                "[EVENT] ",
                entity.getName(),
                "moved to (",
                location.getX(),
                ",",
                location.getY(),
                ")",
            )

        food = -1
        # check for food
        for eid in newLocation.getEntities():
            e = newLocation.getEntity(eid)
            if type(e) is Food:
                food = e

        if food == -1:
            return

        foodColor = food.getColor()

        self.removeEntity(food)
        self.spawnFood()
        self.spawnSnakePart(entity.getTail(), foodColor)
        self.calculateScore()

    def movePreviousSnakePart(self, snakePart):
        previousSnakePart = snakePart.previousSnakePart

        previousSnakePartLocation = self.getLocation(previousSnakePart)

        if previousSnakePartLocation == -1:
            print("Error: A previous snake part's location was unexpectantly -1.")
            time.sleep(1)
            self.quitApplication()

        targetLocation = snakePart.lastPosition

        # move entity
        previousSnakePartLocation.removeEntity(previousSnakePart)
        targetLocation.addEntity(previousSnakePart)
        previousSnakePart.lastPosition = previousSnakePartLocation

        if previousSnakePart.hasPrevious():
            self.movePreviousSnakePart(previousSnakePart)

    def removeEntityFromLocation(self, entity: Entity):
        location = self.getLocation(entity)
        if location.isEntityPresent(entity):
            location.removeEntity(entity)

    def removeEntity(self, entity: Entity):
        self.removeEntityFromLocation(entity)

    def openShop(self):
        """Opens the upgrade shop. Text UI gets a console menu (that's its
        native UI); pygame mode gets a real in-window screen (runPygameShop)
        instead of blocking on stdin behind the graphical window."""
        if self.config.useTextUI:
            self.openTextShop()
        else:
            self.runPygameShop()

    def openTextShop(self):
        self.textRenderer.disableRawMode()
        try:
            data = self.saveManager.data
            upgrades = listUpgrades()
            purchasedUpgrades = data.get("purchasedUpgrades", [])
            print("\n=== Ophidian Shop ===")
            print("Currency: {}".format(data.get("currency", 0)))
            for index, upgrade in enumerate(upgrades, start=1):
                ownedTag = " (owned)" if upgrade["id"] in purchasedUpgrades else ""
                print(
                    "{}. {} - cost {}{}".format(
                        index, upgrade["name"], upgrade["cost"], ownedTag
                    )
                )
                print("   {}".format(upgrade["description"]))
            print("0. Exit shop")
            choice = input("Choose an upgrade to purchase (0 to exit): ").strip()
            if choice and choice != "0":
                try:
                    selectedUpgrade = upgrades[int(choice) - 1]
                except (ValueError, IndexError):
                    print("Invalid selection.")
                else:
                    success, message = purchaseUpgrade(data, selectedUpgrade["id"])
                    print(message)
                    if success:
                        self.saveManager.save()
        finally:
            self.textRenderer.enableRawMode()

    def runPygameShop(self):
        """Self-contained in-window shop screen: its own small event loop
        (poll -> handle -> draw -> present) until the player closes it, same
        shape as the main pygame loop but scoped to just the shop. Nothing
        here ever blocks on stdin, so the graphical window stays live and
        responsive the whole time."""
        upgrades = listUpgrades()
        selectedIndex = 0
        shopMessage = None
        viewingShop = True
        while viewingShop:
            for event in self.pygame.event.get():
                if event.type == self.pygame.QUIT:
                    self.quitApplication()
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
                        # drawn directly on the shop screen below rather than
                        # via notify()/drawUiMessage() - this loop never calls
                        # drawUiMessage(), so that banner would never actually
                        # be seen while still inside the shop
                        print(message)
                        shopMessage = message
                    elif event.key in (self.pygame.K_ESCAPE, self.pygame.K_p):
                        viewingShop = False
            self.drawShopScreen(upgrades, selectedIndex, shopMessage)
            self.pygame.display.update()
            self.pygame.time.delay(16)

    def drawShopScreen(self, upgrades, selectedIndex, shopMessage=None):
        width, height = self.gameDisplay.get_size()
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

    def handleKeyDownEvent(self, key):
        # For text UI, key is a character; for pygame, it's a key code
        if self.config.useTextUI:
            # Text UI key handling
            if key == 'q':
                self.running = False
            elif key == 'w' or key == '\x1b[A':  # w or up arrow
                if (
                    self.changedDirectionThisTick == False
                    and self.selectedSnakePart.getDirection() != 2
                ):
                    self.selectedSnakePart.setDirection(0)
                    self.changedDirectionThisTick = True
            elif key == 'a' or key == '\x1b[D':  # a or left arrow
                if (
                    self.changedDirectionThisTick == False
                    and self.selectedSnakePart.getDirection() != 3
                ):
                    self.selectedSnakePart.setDirection(1)
                    self.changedDirectionThisTick = True
            elif key == 's' or key == '\x1b[B':  # s or down arrow
                if (
                    self.changedDirectionThisTick == False
                    and self.selectedSnakePart.getDirection() != 0
                ):
                    self.selectedSnakePart.setDirection(2)
                    self.changedDirectionThisTick = True
            elif key == 'd' or key == '\x1b[C':  # d or right arrow
                if (
                    self.changedDirectionThisTick == False
                    and self.selectedSnakePart.getDirection() != 1
                ):
                    self.selectedSnakePart.setDirection(3)
                    self.changedDirectionThisTick = True
            elif key == 'r':
                self.checkForLevelProgressAndReinitialize()
                return "restart"
            elif key == 'c':
                self.cycleSelectedCosmetic()
            elif key == 'p':
                self.openShop()
                return "restart"
        else:
            # Pygame key handling
            if key == self.pygame.K_q:
                self.running = False
            elif key == self.pygame.K_w or key == self.pygame.K_UP:
                if (
                    self.changedDirectionThisTick == False
                    and self.selectedSnakePart.getDirection() != 2
                ):
                    self.selectedSnakePart.setDirection(0)
                    self.changedDirectionThisTick = True
            elif key == self.pygame.K_a or key == self.pygame.K_LEFT:
                if (
                    self.changedDirectionThisTick == False
                    and self.selectedSnakePart.getDirection() != 3
                ):
                    self.selectedSnakePart.setDirection(1)
                    self.changedDirectionThisTick = True
            elif key == self.pygame.K_s or key == self.pygame.K_DOWN:
                if (
                    self.changedDirectionThisTick == False
                    and self.selectedSnakePart.getDirection() != 0
                ):
                    self.selectedSnakePart.setDirection(2)
                    self.changedDirectionThisTick = True
            elif key == self.pygame.K_d or key == self.pygame.K_RIGHT:
                if (
                    self.changedDirectionThisTick == False
                    and self.selectedSnakePart.getDirection() != 1
                ):
                    self.selectedSnakePart.setDirection(3)
                    self.changedDirectionThisTick = True
            elif key == self.pygame.K_F11:
                if self.config.fullscreen:
                    self.config.fullscreen = False
                else:
                    self.config.fullscreen = True
                self.initializeGameDisplay()
            elif key == self.pygame.K_l:
                if self.config.limitTickSpeed:
                    self.config.limitTickSpeed = False
                else:
                    self.config.limitTickSpeed = True
            elif key == self.pygame.K_r:
                self.checkForLevelProgressAndReinitialize()
                return "restart"
            elif key == self.pygame.K_c:
                self.cycleSelectedCosmetic()
            elif key == self.pygame.K_p:
                self.openShop()
                return "restart"

    def cycleSelectedCosmetic(self):
        currentCosmetic = self.saveManager.data.get("selectedCosmetic", "default")
        nextCosmetic = getNextCosmeticId(self.saveManager.data, currentCosmetic)
        self.saveManager.data["selectedCosmetic"] = nextCosmetic
        self.saveManager.save()
        # apply immediately to the live snake part, not just on next restart
        self.selectedSnakePart.setColor(self.resolveSelectedCosmeticColor())
        self.notify("Skin selected: " + getSkinName(nextCosmetic))

    def getRandomDirection(self, grid: Grid, location: Location):
        direction = random.randrange(0, 4)
        if direction == 0:
            return grid.getUp(location)
        elif direction == 1:
            return grid.getRight(location)
        elif direction == 2:
            return grid.getDown(location)
        elif direction == 3:
            return grid.getLeft(location)

    def getLocationDirection(self, direction, grid, location):
        if direction == 0:
            return grid.getUp(location)
        elif direction == 1:
            return grid.getLeft(location)
        elif direction == 2:
            return grid.getDown(location)
        elif direction == 3:
            return grid.getRight(location)

    def getLocationOppositeDirection(self, direction, grid, location):
        if direction == 0:
            return grid.getDown(location)
        elif direction == 1:
            return grid.getRight(location)
        elif direction == 2:
            return grid.getUp(location)
        elif direction == 3:
            return grid.getLeft(location)

    def spawnSnakePart(self, snakePart: SnakePart, color):
        newSnakePart = SnakePart(color)
        snakePart.setPrevious(newSnakePart)
        newSnakePart.setNext(snakePart)
        grid, location = self.getLocationAndGrid(snakePart)

        targetLocation = -1
        while True:
            targetLocation = self.getRandomDirection(grid, location)
            if targetLocation != -1 and targetLocation != self.getLocationDirection(
                snakePart.getDirection(), grid, location
            ):
                break

        self.environment.addEntityToLocation(newSnakePart, targetLocation)
        self.snakeParts.append(newSnakePart)

    def spawnFood(self):
        food = Food(
            (
                random.randrange(50, 200),
                random.randrange(50, 200),
                random.randrange(50, 200),
            )
        )

        # get target location
        targetLocation = -1
        notFound = True
        while notFound:
            targetLocation = self.environment.getGrid().getRandomLocation()
            if targetLocation.getNumEntities() == 0:
                notFound = False

        self.environment.addEntity(food)

    def resolveSelectedCosmeticColor(self):
        # Falls back to the original random-color behavior for "default"
        # or any unresolvable/unknown cosmetic id.
        color = getSkinColor(self.saveManager.data.get("selectedCosmetic", "default"))
        if color is not None:
            return color
        return (
            random.randrange(50, 200),
            random.randrange(50, 200),
            random.randrange(50, 200),
        )

    def initialize(self):
        self.collision = False
        self.score = 0
        self.snakeParts = []
        self.tick = 0
        purchasedUpgrades = self.saveManager.data.get("purchasedUpgrades", [])
        # effective tick speed is always derived from the stored base each
        # time (never mutated in place), so ascension/slow_starter bonuses
        # don't compound across restarts
        ascensionTickSpeedMultiplier = (
            self.ascensionBonus["tickSpeedMultiplier"]
            if self.ascensionBonus is not None
            else 1
        )
        effectiveTickSpeed = self.baseTickSpeed * ascensionTickSpeedMultiplier
        # slow_starter upgrade: first level only
        if "slow_starter" in purchasedUpgrades and self.level == 1:
            effectiveTickSpeed *= 1.25
        self.config.tickSpeed = effectiveTickSpeed
        # second_wind upgrade: one near-miss available per run, consumed in moveEntity()
        self.secondWindAvailableThisRun = "second_wind" in purchasedUpgrades
        gridSize = computeGridSizeForLevel(
            self.level,
            self.config.gridSize,
            self.config.minGridSize,
            self.config.maxGridSize,
        )
        self.environment = Environment("Level " + str(self.level), gridSize)
        self.initializeLocationWidthAndHeight()
        biome = getBiome(self.level)
        if not self.config.useTextUI:
            self.pygame.display.set_caption(
                f"Ophidian - {biome['name']} (Level {self.level})"
            )
        self.selectedSnakePart = SnakePart(self.resolveSelectedCosmeticColor())
        self.environment.addEntity(self.selectedSnakePart)
        self.snakeParts.append(self.selectedSnakePart)
        # head_start upgrade: begin the run with 2 extra pre-grown segments
        if "head_start" in purchasedUpgrades:
            for _ in range(2):
                self.spawnSnakePart(
                    self.selectedSnakePart.getTail(), self.selectedSnakePart.getColor()
                )
        ophidianName = self.saveManager.data["ophidianName"]
        self.notify(f"{ophidianName} enters {biome['name']}. {biome['flavorText']}")
        self.spawnFood()
        if self.ascensionBonus is not None:
            for _ in range(self.ascensionBonus["startingBonusSegments"]):
                tail = self.selectedSnakePart.getTail()
                self.spawnSnakePart(tail, tail.getColor())

    def run(self):
        if self.config.useTextUI:
            self.runTextUI()
        else:
            self.runPygameUI()

    def runTextUI(self):
        """Run the game with text-based UI"""
        while self.running:
            # Check for key press (non-blocking)
            key = self.textRenderer.getKeyPress(timeout=0)
            if key:
                result = self.handleKeyDownEvent(key)
                if result == "restart":
                    continue

            # Move snake based on direction
            if self.selectedSnakePart.getDirection() == 0:
                self.moveEntity(self.selectedSnakePart, 0)
            elif self.selectedSnakePart.getDirection() == 1:
                self.moveEntity(self.selectedSnakePart, 1)
            elif self.selectedSnakePart.getDirection() == 2:
                self.moveEntity(self.selectedSnakePart, 2)
            elif self.selectedSnakePart.getDirection() == 3:
                self.moveEntity(self.selectedSnakePart, 3)

            # Render the game state
            percentage = len(self.snakeParts) / len(
                self.environment.grid.getLocations()
            )
            self.textRenderer.renderGrid(
                self.environment, self.snakeParts, self.collision
            )
            self.textRenderer.renderStats(
                self.level, len(self.snakeParts), self.score, percentage
            )
            self.textRenderer.renderControls()

            if self.config.limitTickSpeed:
                time.sleep(self.config.tickSpeed)
                self.tick += 1
                self.changedDirectionThisTick = False

        self.quitApplication()

    def runPygameUI(self):
        """Run the game with pygame graphical UI"""
        while self.running:
            for event in self.pygame.event.get():
                if event.type == self.pygame.QUIT:
                    self.quitApplication()
                elif event.type == self.pygame.KEYDOWN:
                    result = self.handleKeyDownEvent(event.key)
                    if result == "restart":
                        continue
                elif event.type == self.pygame.WINDOWRESIZED:
                    self.initializeLocationWidthAndHeight()

            if self.selectedSnakePart.getDirection() == 0:
                self.moveEntity(self.selectedSnakePart, 0)
            elif self.selectedSnakePart.getDirection() == 1:
                self.moveEntity(self.selectedSnakePart, 1)
            elif self.selectedSnakePart.getDirection() == 2:
                self.moveEntity(self.selectedSnakePart, 2)
            elif self.selectedSnakePart.getDirection() == 3:
                self.moveEntity(self.selectedSnakePart, 3)

            self.gameDisplay.fill(self.config.white)
            self.drawEnvironment()
            x, y = self.gameDisplay.get_size()

            # draw progress bar
            percentage = len(self.snakeParts) / len(
                self.environment.grid.getLocations()
            )
            self.pygame.draw.rect(self.gameDisplay, self.config.black, (0, y - 20, x, 20))
            if percentage < self.config.levelProgressPercentageRequired / 2:
                self.pygame.draw.rect(
                    self.gameDisplay, self.config.red, (0, y - 20, x * percentage, 20)
                )
            elif percentage < self.config.levelProgressPercentageRequired:
                self.pygame.draw.rect(
                    self.gameDisplay,
                    self.config.yellow,
                    (0, y - 20, x * percentage, 20),
                )
            else:
                self.pygame.draw.rect(
                    self.gameDisplay, self.config.green, (0, y - 20, x * percentage, 20)
                )
            self.pygame.draw.rect(self.gameDisplay, self.config.black, (0, y - 20, x, 20), 1)

            self.drawUiMessage()
            self.pygame.display.update()

            if self.config.limitTickSpeed:
                time.sleep(self.config.tickSpeed)
                self.tick += 1
                self.changedDirectionThisTick = False

        self.quitApplication()


import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Ophidian - A snake game')
    parser.add_argument('--text-ui', action='store_true', 
                        help='Use text-based UI instead of graphical UI')
    args = parser.parse_args()
    
    ophidian = Ophidian(useTextUI=args.text_ui)
    ophidian.run()
