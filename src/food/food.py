from lib.pyenvlib.entity import Entity

# Growth food (the original behavior) adds a snake segment. Timed effects
# are not food types: they spawn as their own PowerUp entities (see
# powerup/powerup.py), so there is exactly one path for temporary effects
# rather than two that can drift apart. Kept as a plain string id to match
# the rest of the codebase's id conventions (see progression/shop.py).
FOOD_TYPE_GROWTH = "growth"


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
