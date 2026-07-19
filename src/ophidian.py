import random
import time
from config.config import Config
from lib.pyenvlib.entity import Entity
from lib.pyenvlib.environment import Environment
from food.food import Food, FOOD_TYPE_GROWTH, FOOD_TYPE_SPEED
from snake.snakePart import SnakePart
from progression.save import SaveManager
from progression.obituary import formatObituaryScreen
from progression.cosmetics import checkForNewUnlocks, getNextCosmeticId, getSkinColor, getSkinName
from progression.shop import (
    currencyEarnedForRun,
    getActiveUpgradeLabels,
    listUpgrades,
    purchaseUpgrade,
)
from progression.lore import generateOphidianName, getBiome
from progression.ascension import (
    computeGridSizeForLevel,
    shouldAscend,
    applyAscension,
)
from ui.banner import UiBanner
from ui.shop_screen import PygameShopScreen


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
        self.uiBanner = UiBanner()
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
        whole UI in text mode) and, in pygame mode, also queued on
        self.uiBanner so it isn't invisible behind the graphical window."""
        print(message)
        if not self.config.useTextUI:
            self.uiBanner.push(message)

    def drawUiMessage(self):
        if self.config.useTextUI:
            return
        width, _ = self.gameDisplay.get_size()
        self.uiBanner.draw(self.graphik, width, self.config.black, self.config.white)

    def getActiveUpgradesSummary(self):
        return getActiveUpgradeLabels(
            self.saveManager.data, self.secondWindAvailableThisRun
        )

    def drawHud(self):
        """Currency + active-upgrades readout, always visible (not just
        inside the shop) so the player isn't stuck checking their balance or
        what they own by reopening the shop mid-run. Drawn just below the
        banner strip so the two never overlap."""
        if self.config.useTextUI:
            return
        width, _ = self.gameDisplay.get_size()
        currency = self.saveManager.data.get("currency", 0)
        self.graphik.drawText(
            f"Currency: {currency}", width // 2, 45, 14, self.config.black
        )
        labels = self.getActiveUpgradesSummary()
        if labels:
            self.graphik.drawText(
                " | ".join(labels), width // 2, 63, 12, self.config.black
            )

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
        # Grid.getLocation() does a raw dict lookup and raises KeyError for
        # an ID that isn't a real location (e.g. an entity's default -1
        # sentinel from Entity.__init__ that was never overwritten by
        # addEntity) - guard so callers get the -1 sentinel they already
        # check for instead of an unhandled crash (see issue #22).
        if locationID not in grid.getLocations():
            return -1
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
        foodType = food.getFoodType()

        self.removeEntity(food)
        self.spawnFood()
        if foodType == FOOD_TYPE_SPEED:
            self.activateSpeedBoost()
        else:
            self.spawnSnakePart(entity.getTail(), foodColor)
        self.calculateScore()

    def movePreviousSnakePart(self, snakePart):
        previousSnakePart = snakePart.previousSnakePart

        previousSnakePartLocation = self.getLocation(previousSnakePart)

        if previousSnakePartLocation == -1:
            print("Error: A previous snake part's location was unexpectantly -1.")
            time.sleep(1)
            self.quitApplication()
            return

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
        """Delegates to PygameShopScreen: its own poll/handle/draw loop,
        scoped to just the shop, so purchasing upgrades stays visible and
        interactive without blocking on stdin behind the graphical window."""
        PygameShopScreen(
            self.pygame,
            self.graphik,
            lambda: self.gameDisplay,
            self.config,
            self.saveManager,
            self.quitApplication,
        ).run()

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
            elif key == 'l':
                if self.config.limitTickSpeed:
                    self.config.limitTickSpeed = False
                else:
                    self.config.limitTickSpeed = True
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

    def getLocationDirection(self, direction, grid, location):
        if direction == 0:
            return grid.getUp(location)
        elif direction == 1:
            return grid.getLeft(location)
        elif direction == 2:
            return grid.getDown(location)
        elif direction == 3:
            return grid.getRight(location)

    def spawnSnakePart(self, snakePart: SnakePart, color):
        newSnakePart = SnakePart(color)
        snakePart.setPrevious(newSnakePart)
        newSnakePart.setNext(snakePart)
        grid, location = self.getLocationAndGrid(snakePart)

        # excludedLocation keeps a new segment out of the cell the snake is
        # currently facing/heading toward; among the rest, prefer a cell with
        # no entities so new segments never silently stack on an existing
        # snake part or hide a food entity underneath one
        excludedLocation = self.getLocationDirection(
            snakePart.getDirection(), grid, location
        )
        neighbors = [
            self.getLocationDirection(direction, grid, location)
            for direction in range(4)
        ]
        onGridNeighbors = [
            neighbor for neighbor in neighbors if neighbor != -1
        ]
        emptyCandidates = [
            neighbor
            for neighbor in onGridNeighbors
            if neighbor != excludedLocation and neighbor.getNumEntities() == 0
        ]
        if emptyCandidates:
            targetLocation = random.choice(emptyCandidates)
        elif onGridNeighbors:
            # every unoccupied neighbor is taken (or the only one is
            # excluded) - fall back to any on-grid neighbor rather than
            # looping forever or crashing on a full grid
            fallbackCandidates = [
                neighbor for neighbor in onGridNeighbors if neighbor != excludedLocation
            ] or onGridNeighbors
            targetLocation = random.choice(fallbackCandidates)
        else:
            # no on-grid neighbors at all (grid too small to have any) -
            # stack on the current location rather than crashing
            targetLocation = location

        self.environment.addEntityToLocation(newSnakePart, targetLocation)
        self.snakeParts.append(newSnakePart)

    def spawnFood(self):
        if random.random() < self.config.growthFoodSpawnRate:
            food = Food(self.config.red, FOOD_TYPE_GROWTH)
        else:
            food = Food(self.config.blue, FOOD_TYPE_SPEED)

        # get target location
        targetLocation = -1
        notFound = True
        while notFound:
            targetLocation = self.environment.getGrid().getRandomLocation()
            if targetLocation.getNumEntities() == 0:
                notFound = False

        self.environment.addEntity(food)

    def activateSpeedBoost(self):
        """Starts (or refreshes) a temporary tick-speed boost from speed food.

        The un-boosted tick speed is captured once, on the first speed food
        of a boost window, so eating a second speed food while one is
        already active extends the timer instead of compounding the
        multiplier.
        """
        if not self.speedBoostActive:
            self.speedBoostBaseTickSpeed = self.config.tickSpeed
            self.config.tickSpeed = (
                self.speedBoostBaseTickSpeed / self.config.speedBoostMultiplier
            )
        self.speedBoostActive = True
        self.speedBoostEndTime = time.time() + self.config.speedBoostDuration
        self.notify("Speed boost!")

    def updateSpeedBoost(self):
        """Reverts tick speed once an active speed boost's timer expires.

        Called once per tick from both UI loops so the boost is time-based
        (real seconds) rather than tick-count-based, which would otherwise
        let limitTickSpeed being toggled off make a boost last forever.
        """
        if self.speedBoostActive and time.time() >= self.speedBoostEndTime:
            self.config.tickSpeed = self.speedBoostBaseTickSpeed
            self.speedBoostActive = False
            self.speedBoostEndTime = None

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
        # speed food boost: reset on every initialize() (new run/level) so a
        # boost never carries over into a tick speed the player didn't earn
        # this life
        self.speedBoostActive = False
        self.speedBoostEndTime = None
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
            self.updateSpeedBoost()

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
            self.textRenderer.renderHud(
                self.saveManager.data.get("currency", 0),
                self.getActiveUpgradesSummary(),
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
            self.updateSpeedBoost()

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

            self.drawHud()
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
