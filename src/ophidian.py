import math
import random
import time
from config.config import Config
from lib.pyenvlib.entity import Entity
from lib.pyenvlib.environment import Environment
from food.food import Food, FOOD_TYPE_GROWTH
from powerup.powerup import (
    PowerUp,
    PowerUpType,
    getPowerUpColor,
    getPowerUpDefinition,
    getPowerUpDurationSeconds,
    getPowerUpHudLabel,
    getPowerUpTextSymbol,
    getScoreMultiplier,
    rollPowerUpType,
)
from powerup.active import ActivePowerUps
from scoring.scoring import (
    applyScoreMultiplier,
    formatScoreLabel,
    getGridFillPercentage,
    pointsForFood,
)
from snake.snakePart import SnakePart
from progression.save import SaveManager
from progression.obituary import formatObituaryScreen
from progression.cosmetics import (
    checkForNewUnlocks,
    getNextCosmeticId,
    getSkinColor,
    getSkinName,
)
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
from controls.keybindings import (
    ACTION_CYCLE_COSMETIC,
    ACTION_OPEN_SHOP,
    ACTION_QUIT,
    ACTION_RESTART_RUN,
    ACTION_TOGGLE_FULLSCREEN,
    ACTION_TOGGLE_TICK_SPEED_LIMIT,
    OPPOSITE_DIRECTIONS,
    RESTART_SENTINEL,
    TEXT_UI_ACTION_KEYS,
    TEXT_UI_DIRECTION_KEYS,
    buildPygameActionKeys,
    buildPygameDirectionKeys,
)


# Geometry of one power-up indicator in the graphical HUD: a label row with
# a duration meter tucked underneath it. The row is taller than the plain
# text rows above it because it carries the meter as well, so the rows of a
# stack of indicators don't collide.
POWER_UP_INDICATOR_ROW_HEIGHT = 24
POWER_UP_INDICATOR_METER_WIDTH = 140
POWER_UP_INDICATOR_METER_HEIGHT = 4


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

        self.initializeKeyBindings()
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
        # timers for collected power-ups; must exist before initialize(),
        # which clears them for the starting run
        self.activePowerUps = ActivePowerUps()
        self.tickSpeedBeforeBoost = None
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
                (self.config.displayWidth, self.config.displayHeight),
                self.pygame.FULLSCREEN,
            )
        else:
            self.gameDisplay = self.pygame.display.set_mode(
                (self.config.displayWidth, self.config.displayHeight),
                self.pygame.RESIZABLE,
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

    def awardPointsForFood(self):
        """Banks the points one growth-food pickup is worth.

        Score accumulates per pickup instead of being recalculated from the
        ophidian's current size, so the score-multiplier power-up can double
        what a bite is worth while it runs without retroactively doubling -
        and then un-doubling - everything banked before it (see issue #73).
        What a bite is worth lives in scoring/scoring.py; this method only
        decides when one is earned and at what multiplier.
        """
        basePoints = pointsForFood(
            len(self.snakeParts), len(self.environment.grid.getLocations())
        )
        self.score += applyScoreMultiplier(basePoints, self.getActiveScoreMultiplier())

    def getActiveScoreMultiplier(self):
        """The combined score multiplier of every power-up currently running.

        Multiplied together rather than picked from, so two multiplier
        power-ups running at once would compound instead of one silently
        winning. 1.0 when nothing is active, or when what is active doesn't
        touch scoring.
        """
        multiplier = 1.0
        for powerUpType, _ in self.activePowerUps.statuses():
            multiplier *= getScoreMultiplier(powerUpType)
        return multiplier

    def getScoreLabel(self):
        """The current score, annotated with any multiplier now running.

        The same string the text UI's stats block shows, so neither UI has to
        restate when a multiplier is worth annotating.
        """
        return formatScoreLabel(self.score, self.getActiveScoreMultiplier())

    def displayStatsInConsole(self):
        length = len(self.snakeParts)
        numLocations = len(self.environment.grid.getLocations())
        percentage = getGridFillPercentage(length, numLocations)
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

    def restartRun(self):
        """Ends the current run on the player's 'r' key.

        The run is recorded first, so restarting banks its currency,
        obituary and lifetime stats exactly like dying or quitting does -
        previously 'r' jumped straight to reinitializing and silently threw
        all of that away (see issue #113).

        Recording lives here rather than inside
        checkForLevelProgressAndReinitialize because the collision path
        calls that method too, and has already recorded the run by then.
        """
        self.recordCurrentRun("restart")
        self.checkForLevelProgressAndReinitialize()

    def recordCurrentRun(self, causeOfDeath):
        # bank currency earned this run before folding it into lifetime stats;
        # recordRun() below calls saveManager.save() which persists both
        earnedCurrency = currencyEarnedForRun(len(self.snakeParts))
        self.saveManager.data["currency"] = (
            self.saveManager.data.get("currency", 0) + earnedCurrency
        )
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
        """Player-facing feedback: printed to console and queued on
        self.uiBanner, which both UI loops render from.

        The queue is needed in text mode too: a bare print() is wiped by
        TextRenderer.renderGrid()'s clearScreen() later in the very same
        tick, so every notification was previously invisible there (see
        issue #110). In text mode the console copy therefore only survives
        in redirected/piped output - the banner is what the player sees.
        Gameplay code only ever calls notify(); each renderer decides how
        to show the queued message."""
        print(message)
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
        """Score, currency, active-upgrades and active-power-up readout,
        always visible (not just inside the shop) so the player isn't stuck
        checking their balance or what they own by reopening the shop
        mid-run. Drawn just below the banner strip so the two never overlap.

        The score shares the first line with the currency rather than taking
        a line of its own, because graphik centres each string on the x it is
        given and two centred strings on one row would sit on top of each
        other. Until it was added here the score was only ever visible in the
        text UI and in the end-of-run summary (see issue #124).

        The optional lines flow upwards into whatever space the ones above
        them left free, so a run with no upgrades owned doesn't render its
        power-up lines with a blank row above them.
        """
        if self.config.useTextUI:
            return
        width, _ = self.gameDisplay.get_size()
        currency = self.saveManager.data.get("currency", 0)
        self.graphik.drawText(
            f"Score: {self.getScoreLabel()} | Currency: {currency}",
            width // 2,
            45,
            14,
            self.config.black,
        )
        lineY = 63
        labels = self.getActiveUpgradesSummary()
        if labels:
            self.graphik.drawText(
                " | ".join(labels), width // 2, lineY, 12, self.config.black
            )
            lineY += 18
        for status in self.getActivePowerUpStatuses():
            self.drawPowerUpIndicator(status, width // 2, lineY)
            lineY += POWER_UP_INDICATOR_ROW_HEIGHT

    def drawPowerUpIndicator(self, status, centerX, centerY):
        """One power-up's indicator: symbol, label, seconds left, and a meter
        that drains as its timer does.

        The status record arrives as plain numbers from gameplay and is
        formatted here, so each renderer presents an indicator in its own
        idiom. The meter is drawn from fractionRemaining rather than from the
        rounded-up seconds beside it, which is what makes an expiring
        power-up drain smoothly instead of stepping down once a second, and
        what makes a refreshed timer visibly jump back to full.

        The filled portion takes the power-up's own color - the same one it
        was collected in on the grid - so which of several stacked
        indicators is running out is readable without stopping to read the
        labels.
        """
        self.graphik.drawText(
            f"[{status['symbol']}] {status['label']}: "
            f"{math.ceil(status['secondsRemaining'])}s",
            centerX,
            centerY,
            12,
            self.config.black,
        )
        meterX = centerX - POWER_UP_INDICATOR_METER_WIDTH // 2
        meterY = centerY + 9
        self.graphik.drawRectangle(
            meterX,
            meterY,
            POWER_UP_INDICATOR_METER_WIDTH,
            POWER_UP_INDICATOR_METER_HEIGHT,
            self.config.gray,
        )
        filledWidth = int(POWER_UP_INDICATOR_METER_WIDTH * status["fractionRemaining"])
        if filledWidth > 0:
            self.graphik.drawRectangle(
                meterX,
                meterY,
                filledWidth,
                POWER_UP_INDICATOR_METER_HEIGHT,
                status["color"],
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
                # invincibility power-up: collisions simply don't land while
                # it is running. The move is dropped rather than letting the
                # head share a cell with its own body (which would leave the
                # snake overlapping itself once the power-up expires) - the
                # player keeps full steering control, so this stalls for a
                # tick instead of ending the run. Checked before second_wind
                # so a power-up never burns the paid-for upgrade.
                if self.activePowerUps.isActive(PowerUpType.INVINCIBILITY):
                    return
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

        pickup = None
        # check for something collectible - food grows the snake, a power-up
        # grants its timed effect instead
        for eid in newLocation.getEntities():
            e = newLocation.getEntity(eid)
            if type(e) is Food or type(e) is PowerUp:
                pickup = e

        if pickup is None:
            return

        pickupColor = pickup.getColor()

        self.removeEntity(pickup)
        self.spawnPickup()
        if type(pickup) is PowerUp:
            self.activatePowerUp(pickup.getPowerUpType())
        else:
            self.spawnSnakePart(entity.getTail(), pickupColor)
            # only growth food is worth points; a power-up pays out through
            # its effect instead
            self.awardPointsForFood()

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

    def initializeKeyBindings(self):
        """Builds this run's key tables for whichever UI is in use.

        Only the spelling of a key differs between the two UIs, so this is
        the one place either of them is consulted; every rule the keys
        trigger lives once, below.
        """
        if self.config.useTextUI:
            # copied rather than referenced so a table belongs to the
            # instance either way - the pygame builders below hand back a
            # fresh dict, and rebinding a key on one game must not reach
            # into the module-level table every other game reads
            self.directionKeys = dict(TEXT_UI_DIRECTION_KEYS)
            self.actionKeys = dict(TEXT_UI_ACTION_KEYS)
        else:
            self.directionKeys = buildPygameDirectionKeys(self.pygame)
            self.actionKeys = buildPygameActionKeys(self.pygame)

    def handleKeyDownEvent(self, key):
        """Turns one key press into the gameplay rule it stands for.

        Both run loops call this - the key is a character in text mode and
        a pygame key code in graphical mode, and the tables built by
        initializeKeyBindings() are the only part that knows the
        difference. Keys bound to nothing are ignored.

        Returns RESTART_SENTINEL when the press left a board that must not
        be advanced in the same frame; both loops have to honour that
        identically (issue #117).
        """
        if key in self.directionKeys:
            self.setDirectionIfAllowed(self.directionKeys[key])
            return None
        action = self.actionKeys.get(key)
        if action is None:
            return None
        return self.performAction(action)

    def setDirectionIfAllowed(self, direction):
        """Turns the snake, unless the turn is one of the two that are not
        allowed: reversing into its own neck, or a second turn in a tick
        the snake has already turned in (which would otherwise let two keys
        pressed between ticks add up to a reversal).
        """
        if self.changedDirectionThisTick:
            return
        if self.selectedSnakePart.getDirection() == OPPOSITE_DIRECTIONS[direction]:
            return
        self.selectedSnakePart.setDirection(direction)
        self.changedDirectionThisTick = True

    def performAction(self, action):
        """Carries out one non-directional action, whichever UI its key was
        pressed in. Returns RESTART_SENTINEL for the actions that leave a
        board the current frame must not advance.
        """
        if action == ACTION_QUIT:
            self.running = False
        elif action == ACTION_TOGGLE_TICK_SPEED_LIMIT:
            self.config.limitTickSpeed = not self.config.limitTickSpeed
        elif action == ACTION_TOGGLE_FULLSCREEN:
            self.config.fullscreen = not self.config.fullscreen
            self.initializeGameDisplay()
        elif action == ACTION_CYCLE_COSMETIC:
            self.cycleSelectedCosmetic()
        elif action == ACTION_RESTART_RUN:
            self.restartRun()
            return RESTART_SENTINEL
        elif action == ACTION_OPEN_SHOP:
            self.openShop()
            return RESTART_SENTINEL
        else:
            # an action a key table can produce but nothing here handles is
            # a binding that would silently do nothing - the same drift
            # this dispatch exists to remove, so it is raised rather than
            # swallowed. No key press can reach here without having been
            # found in a table first, so this is a programming error and
            # never player input.
            raise ValueError("Unhandled action: " + str(action))
        return None

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
        onGridNeighbors = [neighbor for neighbor in neighbors if neighbor != -1]
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

    def spawnPickup(self):
        """Spawns the next collectible on the board.

        config.growthFoodSpawnRate of them are growth food; the rest are
        power-ups, drawn from the registry by spawn weight (see
        powerup/powerup.py).
        """
        if random.random() < self.config.growthFoodSpawnRate:
            pickup = Food(self.config.red, FOOD_TYPE_GROWTH)
        else:
            pickup = PowerUp(rollPowerUpType())

        # a pickup must land on an empty location: moveEntity() checks the
        # destination for a SnakePart before it ever looks for something
        # collectible, so a pickup spawned underneath a segment isn't just
        # hidden - it's a cell that kills the player instead of rewarding
        # them (see issue #109). Choosing from the set of empty locations,
        # rather than redrawing random locations until one happens to be
        # empty, also can't spin forever once the snake has filled the grid.
        grid = self.environment.getGrid()
        emptyLocations = [
            location
            for location in grid.getLocations().values()
            if location.getNumEntities() == 0
        ]
        if emptyLocations:
            self.environment.addEntityToLocation(pickup, random.choice(emptyLocations))
        else:
            # every cell is occupied - there is no legal spot left, but the
            # board should still have something on it for when one frees up
            self.environment.addEntity(pickup)

    def activatePowerUp(self, powerUpType):
        """Starts (or refreshes) a collected power-up.

        The effect is applied only on a fresh activation: collecting a
        power-up that is already running extends its timer instead of
        compounding the effect (e.g. halving an already-halved tick speed).
        """
        newlyActivated = self.activePowerUps.activate(
            powerUpType, getPowerUpDurationSeconds(powerUpType)
        )
        if newlyActivated:
            self.applyPowerUpEffect(powerUpType)
        self.notify(getPowerUpDefinition(powerUpType)["activationMessage"])

    def applyPowerUpEffect(self, powerUpType):
        """Applies what a power-up actually does to the running game.

        The one place a new power-up type needs gameplay code; everything
        else about it (spawning, timing, both HUDs) is driven off the
        registry. Invincibility has no entry here because it is read
        directly off activePowerUps in moveEntity().
        """
        if powerUpType == PowerUpType.SPEED:
            definition = getPowerUpDefinition(powerUpType)
            self.tickSpeedBeforeBoost = self.config.tickSpeed
            self.config.tickSpeed = (
                self.tickSpeedBeforeBoost / definition["tickSpeedMultiplier"]
            )

    def revertPowerUpEffect(self, powerUpType):
        """Undoes applyPowerUpEffect() when a power-up runs out."""
        if powerUpType == PowerUpType.SPEED and self.tickSpeedBeforeBoost is not None:
            self.config.tickSpeed = self.tickSpeedBeforeBoost
            self.tickSpeedBeforeBoost = None

    def updatePowerUps(self):
        """Expires power-ups whose timers have run out, and reverts them.

        Called once per tick from both UI loops so power-ups are time-based
        (real seconds) rather than tick-count-based, which would otherwise
        let limitTickSpeed being toggled off make one last forever.
        """
        for powerUpType in self.activePowerUps.expire():
            self.revertPowerUpEffect(powerUpType)
            self.notify(getPowerUpDefinition(powerUpType)["expiryMessage"])

    def getActivePowerUpStatuses(self):
        """One indicator record per power-up currently running.

        A power-up's activation banner expires after UiBanner.durationSeconds
        (2s) while the power-up itself can last longer, so without this the
        snake spent the tail of every boost moving faster for reasons the
        player could no longer see (see issue #114).

        Each record carries only plain data - the symbol and color that the
        power-up is already recognized by on the grid, the seconds left as
        a number, and how much of the duration those seconds are as a
        fraction of one. Nothing is pre-formatted, so each renderer presents an
        indicator in its own idiom (a drawn meter, an ASCII one) and gameplay
        code stays out of the UI. Both loops already call updatePowerUps()
        once per iteration, so the values are naturally fresh with no extra
        bookkeeping.

        fractionRemaining is what makes the countdown read smoothly: it
        falls continuously across frames, where the whole seconds beside it
        only change once a second. Clamped to at most 1 because collecting a
        power-up that is already running refreshes its timer to a full
        duration.
        """
        statuses = []
        for powerUpType, secondsRemaining in self.activePowerUps.statuses():
            durationSeconds = getPowerUpDurationSeconds(powerUpType)
            statuses.append(
                {
                    "label": getPowerUpHudLabel(powerUpType),
                    "symbol": getPowerUpTextSymbol(powerUpType),
                    "color": getPowerUpColor(powerUpType),
                    "secondsRemaining": secondsRemaining,
                    "durationSeconds": durationSeconds,
                    "fractionRemaining": (
                        min(1.0, secondsRemaining / durationSeconds)
                        if durationSeconds > 0
                        else 0.0
                    ),
                }
            )
        return statuses

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
        # power-ups are reset on every initialize() (new run/level) so one
        # never carries over into a life the player didn't earn it in. No
        # effect needs reverting here: tickSpeed is recomputed from the
        # stored base just above.
        self.activePowerUps.clear()
        self.tickSpeedBeforeBoost = None
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
        self.spawnPickup()
        if self.ascensionBonus is not None:
            for _ in range(self.ascensionBonus["startingBonusSegments"]):
                tail = self.selectedSnakePart.getTail()
                self.spawnSnakePart(tail, tail.getColor())

    def endOfTick(self):
        """Closes out one movement step, for both UI loops.

        Only the sleep is gated on limitTickSpeed - one loop iteration is
        exactly one moveEntity call either way, so the tick counter and the
        per-tick direction latch have to advance every iteration. Gating
        those on limitTickSpeed too meant that pressing 'l' left
        changedDirectionThisTick permanently True after the first turn (it
        is reset nowhere else, not even in initialize()), locking the snake
        into one direction, and froze self.tick so runs recorded a stale
        ticksSurvived (see issue #112).
        """
        if self.config.limitTickSpeed:
            time.sleep(self.config.tickSpeed)
        self.tick += 1
        self.changedDirectionThisTick = False

    def moveSelectedSnakePart(self):
        """The one movement step of a tick, shared by both UI loops.

        Kept in one place (rather than duplicated as a direction if/elif
        chain per loop) so the graphical and text UIs cannot drift apart on
        what a tick does - the recurring problem behind PRs #92, #95 and
        #99.
        """
        self.moveEntity(self.selectedSnakePart, self.selectedSnakePart.getDirection())

    def run(self):
        if self.config.useTextUI:
            self.runTextUI()
        else:
            self.runPygameUI()

    def runTextUI(self):
        """Run the game with text-based UI"""
        while self.running:
            self.updatePowerUps()

            # Check for key press (non-blocking)
            restarted = False
            key = self.textRenderer.getKeyPress(timeout=0)
            if key:
                restarted = self.handleKeyDownEvent(key) == RESTART_SENTINEL

            # Move snake based on direction. Skipped on a restart frame so
            # the freshly initialized board is presented before it advances
            # - see runPygameUI, which must agree (issue #117).
            if not restarted:
                self.moveSelectedSnakePart()

            # Render the game state
            percentage = len(self.snakeParts) / len(
                self.environment.grid.getLocations()
            )
            self.textRenderer.renderGrid(
                self.environment, self.snakeParts, self.collision
            )
            # uiBanner.current() advances/expires the queue and must be
            # called exactly once per frame, mirroring UiBanner.draw() in
            # the pygame loop
            self.textRenderer.renderMessage(self.uiBanner.current())
            self.textRenderer.renderStats(
                self.level,
                len(self.snakeParts),
                self.score,
                percentage,
                self.getActiveScoreMultiplier(),
            )
            self.textRenderer.renderHud(
                self.saveManager.data.get("currency", 0),
                self.getActiveUpgradesSummary(),
                self.getActivePowerUpStatuses(),
            )
            self.textRenderer.renderControls()

            self.endOfTick()

        self.quitApplication()

    def runPygameUI(self):
        """Run the game with pygame graphical UI"""
        while self.running:
            self.updatePowerUps()

            # tracked across the whole event drain rather than acted on
            # inside it: `continue` in the for loop only advanced to the
            # next event, which left the graphical UI moving the snake in
            # the very frame a run restarted while the text UI did not
            # (issue #117). The drain still finishes either way, so events
            # queued behind the restart key aren't silently dropped.
            restarted = False
            for event in self.pygame.event.get():
                if event.type == self.pygame.QUIT:
                    self.quitApplication()
                elif event.type == self.pygame.KEYDOWN:
                    if self.handleKeyDownEvent(event.key) == RESTART_SENTINEL:
                        restarted = True
                elif event.type == self.pygame.WINDOWRESIZED:
                    self.initializeLocationWidthAndHeight()

            if not restarted:
                self.moveSelectedSnakePart()

            self.gameDisplay.fill(self.config.white)
            self.drawEnvironment()
            x, y = self.gameDisplay.get_size()

            # draw progress bar
            percentage = len(self.snakeParts) / len(
                self.environment.grid.getLocations()
            )
            self.pygame.draw.rect(
                self.gameDisplay, self.config.black, (0, y - 20, x, 20)
            )
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
            self.pygame.draw.rect(
                self.gameDisplay, self.config.black, (0, y - 20, x, 20), 1
            )

            self.drawHud()
            self.drawUiMessage()
            self.pygame.display.update()

            self.endOfTick()

        self.quitApplication()


import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ophidian - A snake game")
    parser.add_argument(
        "--text-ui",
        action="store_true",
        help="Use text-based UI instead of graphical UI",
    )
    args = parser.parse_args()

    ophidian = Ophidian(useTextUI=args.text_ui)
    ophidian.run()
