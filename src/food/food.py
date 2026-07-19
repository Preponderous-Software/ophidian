from lib.pyenvlib.entity import Entity

# Growth food (the original behavior) adds a snake segment; speed food
# instead grants a temporary speed boost. Kept as plain string ids to match
# the rest of the codebase's id conventions (see progression/shop.py).
FOOD_TYPE_GROWTH = "growth"
FOOD_TYPE_SPEED = "speed"


# @author Daniel McCoy Stephenson
# @since August 6th, 2022
class Food(Entity):
    def __init__(self, color, foodType=FOOD_TYPE_GROWTH):
        Entity.__init__(self, "Food")
        self.color = color
        self.foodType = foodType

    def getColor(self):
        return self.color

    def getFoodType(self):
        return self.foodType
