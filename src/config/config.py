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
        self.maxGridSize = 12

        # tick speed
        self.limitTickSpeed = True
        self.tickSpeed = 0.2

        # misc
        self.debug = False
        self.restartUponCollision = True
        self.levelProgressPercentageRequired = 0.5
