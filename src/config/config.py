# @author Daniel McCoy Stephenson
# @since August 6th, 2022


# @author Daniel McCoy Stephenson
# @since August 6th, 2022
class Config:
    def __init__(self):
        # display
        self.useTextUI = False
        self.displayWidth = 500
        self.displayHeight = 500
        self.fullscreen = False
        self.black = (0, 0, 0)
        self.white = (255, 255, 255)
        self.green = (0, 255, 0)
        self.red = (255, 0, 0)
        self.yellow = (255, 255, 0)
        self.textSize = 50

        # grid size
        self.gridSize = 5
        self.minGridSize = 5
        # High enough that all 6 curated biomes (progression/lore.py) are
        # reachable before ascension resets the level back to 1 - at 12,
        # levels 5-6 ("The Frostbound Coil"/"The Obsidian Spiral") were
        # silently unreachable dead content.
        self.maxGridSize = 15

        # tick speed
        self.limitTickSpeed = True
        self.tickSpeed = 0.1

        # misc
        self.debug = False
        self.restartUponCollision = True
        self.levelProgressPercentageRequired = 0.5
