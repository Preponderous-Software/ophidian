import random
import time
from config.config import Config
from lib.pyenvlib.entity import Entity
from lib.pyenvlib.environment import Environment
from food.food import Food
from lib.pyenvlib.grid import Grid
from lib.pyenvlib.location import Location
from snake.snakePart import SnakePart


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
        
        self.running = True
        self.snakeParts = []
        self.level = 1
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
            self.level += 1
        self.initialize()

    def quitApplication(self):
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
                # we have a collision
                self.collision = True
                print("The ophidian collides with itself and ceases to be.")
                if not self.config.useTextUI:
                    self.drawEnvironment()
                    self.pygame.display.update()
                time.sleep(self.config.tickSpeed * 20)
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

    def increaseSnakeSpeed(self):
        """Decrease tick speed to make snake faster"""
        self.config.tickSpeed = max(
            self.config.minTickSpeed,
            self.config.tickSpeed - self.config.tickSpeedStep
        )

    def decreaseSnakeSpeed(self):
        """Increase tick speed to make snake slower"""
        self.config.tickSpeed = min(
            self.config.maxTickSpeed,
            self.config.tickSpeed + self.config.tickSpeedStep
        )

    def toggleTickSpeedLimit(self):
        """Toggle tick speed limiting on/off"""
        self.config.limitTickSpeed = not self.config.limitTickSpeed

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
            elif key == 'l':
                self.toggleTickSpeedLimit()
            elif key == '+' or key == '=':
                self.increaseSnakeSpeed()
            elif key == '-' or key == '_':
                self.decreaseSnakeSpeed()
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
                self.toggleTickSpeedLimit()
            elif key == self.pygame.K_r:
                self.checkForLevelProgressAndReinitialize()
                return "restart"
            elif key == self.pygame.K_PLUS or key == self.pygame.K_EQUALS:
                self.increaseSnakeSpeed()
            elif key == self.pygame.K_MINUS or key == self.pygame.K_UNDERSCORE:
                self.decreaseSnakeSpeed()

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

    def initialize(self):
        self.collision = False
        self.score = 0
        self.snakeParts = []
        self.tick = 0
        if self.level == 1:
            self.environment = Environment(
                "Level " + str(self.level), self.config.gridSize
            )
        else:
            self.environment = Environment(
                "Level " + str(self.level), self.config.gridSize + (self.level - 1) * 2
            )
        self.initializeLocationWidthAndHeight()
        if not self.config.useTextUI:
            self.pygame.display.set_caption("Ophidian - Level " + str(self.level))
        self.selectedSnakePart = SnakePart(
            (
                random.randrange(50, 200),
                random.randrange(50, 200),
                random.randrange(50, 200),
            )
        )
        self.environment.addEntity(self.selectedSnakePart)
        self.snakeParts.append(self.selectedSnakePart)
        print("The ophidian enters the world.")
        self.spawnFood()

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
