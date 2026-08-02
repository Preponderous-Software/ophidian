import random
from enum import Enum

from lib.pyenvlib.entity import Entity

# @author Daniel McCoy Stephenson
# @since August 2nd, 2026

# The power-up registry: every collectible that grants a temporary, timed
# effect (as opposed to food, which permanently grows the snake).
#
# Adding a power-up type is meant to be a new PowerUpType member plus a new
# entry below - spawning, pickup, timing and both HUDs are all driven off
# this table. The only thing a new type needs elsewhere is its actual
# effect, which lives in gameplay (Ophidian.applyPowerUpEffect /
# revertPowerUpEffect) so this module stays free of game-state and UI
# dependencies and can be unit tested on its own, like progression/shop.py.


class PowerUpType(str, Enum):
    """Ids for every power-up the game can spawn.

    Subclasses str so a member compares equal to - and serializes as - its
    plain-string id, which keeps the enum compatible with the string-id
    convention the rest of the codebase already uses (food types, shop
    upgrade ids).
    """

    SPEED = "speed"
    INVINCIBILITY = "invincibility"


# spawnWeight is relative *within* the power-up share of spawned pickups,
# which is 1 - config.growthFoodSpawnRate (20% by default). Weights of 3 and
# 1 therefore work out to a 15% speed / 5% invincibility chance per pickup,
# the rates asked for in issues #71 and #74.
POWER_UP_DEFINITIONS = {
    PowerUpType.SPEED: {
        "id": PowerUpType.SPEED,
        "name": "Speed Boost",
        "hudLabel": "Speed boost",
        "activationMessage": "Speed boost!",
        "expiryMessage": "The speed boost fades.",
        "color": (0, 0, 255),
        "textSymbol": ">",
        "spawnWeight": 3,
        "durationSeconds": 5.0,
        # the un-boosted tick speed is divided by this while the boost runs
        "tickSpeedMultiplier": 2.0,
    },
    PowerUpType.INVINCIBILITY: {
        "id": PowerUpType.INVINCIBILITY,
        "name": "Invincibility",
        "hudLabel": "Invincible",
        "activationMessage": "The ophidian turns invincible!",
        "expiryMessage": "Invincibility fades.",
        "color": (255, 215, 0),
        "textSymbol": "*",
        "spawnWeight": 1,
        "durationSeconds": 3.0,
    },
}

# Stable order for spawning rolls and HUD listings.
POWER_UP_ORDER = [PowerUpType.SPEED, PowerUpType.INVINCIBILITY]


def listPowerUpTypes():
    """Every spawnable power-up type, in display order."""
    return list(POWER_UP_ORDER)


def getPowerUpDefinition(powerUpType):
    """The registry entry for a power-up type.

    Accepts either a PowerUpType or its plain-string id, so callers holding
    a value read back off an entity or a save file don't have to convert
    first.
    """
    return POWER_UP_DEFINITIONS[PowerUpType(powerUpType)]


def getPowerUpName(powerUpType):
    return getPowerUpDefinition(powerUpType)["name"]


def getPowerUpHudLabel(powerUpType):
    return getPowerUpDefinition(powerUpType)["hudLabel"]


def getPowerUpDurationSeconds(powerUpType):
    return getPowerUpDefinition(powerUpType)["durationSeconds"]


def rollPowerUpType(rng=random):
    """Picks a power-up type at random, weighted by spawnWeight.

    Takes the random source as an argument so a caller (or a test) can hand
    in a seeded Random instead of the shared module-level one.
    """
    types = listPowerUpTypes()
    weights = [
        POWER_UP_DEFINITIONS[powerUpType]["spawnWeight"] for powerUpType in types
    ]
    return rng.choices(types, weights=weights)[0]


class PowerUp(Entity):
    """A collectible power-up sitting on the grid.

    Carries its own color and text symbol - the way Food already carries its
    color - so both renderers can draw one without knowing the registry
    exists.
    """

    def __init__(self, powerUpType):
        Entity.__init__(self, "PowerUp")
        self.powerUpType = PowerUpType(powerUpType)

    def getPowerUpType(self):
        return self.powerUpType

    def getDisplayName(self):
        return getPowerUpName(self.powerUpType)

    def getColor(self):
        return getPowerUpDefinition(self.powerUpType)["color"]

    def getTextSymbol(self):
        return getPowerUpDefinition(self.powerUpType)["textSymbol"]
