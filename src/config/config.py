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
        self.blue = (0, 0, 255)
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
        # 0.15s/tick (rather than the earlier 0.1s) gives players more time
        # to react - see issue #97, "the game runs too quickly to react in
        # time to control the snake effectively."
        self.limitTickSpeed = True
        self.tickSpeed = 0.15

        # pickups
        # 65% of spawned pickups are growth food; the remainder are
        # power-ups (see issue #71). How long each power-up lasts and what
        # it does lives with its registry entry in powerup/powerup.py,
        # alongside its spawn weight, the same way progression/shop.py owns
        # its upgrades' costs and effects.
        #
        # The 35% power-up share is the sum of the absolute rates the
        # power-up issues each asked for - 15% speed (#71), 5%
        # invincibility (#74), 15% score multiplier (#73) - so adding a
        # type means raising the share rather than diluting the types
        # already there. powerup.getAbsoluteSpawnRates() derives the
        # per-type rates from this and is asserted against those numbers.
        self.growthFoodSpawnRate = 0.65

        # misc
        self.debug = False
        self.restartUponCollision = True
        self.levelProgressPercentageRequired = 0.5
