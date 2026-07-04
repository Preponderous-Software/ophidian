"""Pure functions for the level-growth cap and the ascension "prestige" reset.

# @author Daniel McCoy Stephenson
# @since July 4th, 2026
"""


def computeGridSizeForLevel(level, baseGridSize, minGridSize, maxGridSize):
    """Replicates the original `baseGridSize + (level - 1) * 2` growth formula
    (returning exactly `baseGridSize` for level 1), clamped into
    [minGridSize, maxGridSize] so the grid can never grow past the cap."""
    uncappedGridSize = baseGridSize if level == 1 else baseGridSize + (level - 1) * 2
    return max(minGridSize, min(uncappedGridSize, maxGridSize))


def shouldAscend(level, baseGridSize, minGridSize, maxGridSize):
    """True once leveling up again would require a grid size beyond maxGridSize,
    i.e. the current level is the last one reachable within the cap."""
    nextLevel = level + 1
    nextUncappedGridSize = baseGridSize + (nextLevel - 1) * 2
    return nextUncappedGridSize > maxGridSize


def applyAscension(saveData):
    """Increments the persistent ascensionLevel in saveData and returns a small,
    bounded permanent bonus derived from the new ascension level:
      - tickSpeedMultiplier shrinks the base tick speed by 5% per ascension,
        floored at 0.7 (a 30% speed increase cap) so runs never become instant.
      - startingBonusSegments grants one extra starting segment every 3
        ascensions, so growth is gradual rather than trivializing the game.
    """
    saveData["ascensionLevel"] += 1
    ascensionLevel = saveData["ascensionLevel"]

    tickSpeedDecreasePerAscension = 0.05
    minimumTickSpeedMultiplier = 0.7
    tickSpeedMultiplier = max(
        minimumTickSpeedMultiplier,
        1 - tickSpeedDecreasePerAscension * ascensionLevel,
    )

    ascensionsPerBonusSegment = 3
    startingBonusSegments = ascensionLevel // ascensionsPerBonusSegment

    return {
        "tickSpeedMultiplier": tickSpeedMultiplier,
        "startingBonusSegments": startingBonusSegments,
    }
