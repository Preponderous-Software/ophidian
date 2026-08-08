# @author Daniel McCoy Stephenson
# @since August 4th, 2026

# What a single pickup is worth, kept as pure functions so the scoring rule
# can be reasoned about and unit tested without a running game, the way
# progression/shop.py owns its upgrade costs.
#
# Score is *banked* per pickup rather than recomputed from the ophidian's
# current size. The earlier rule (score = length * percentageOfGridFilled,
# recalculated on every pickup) had no room for a multiplier: scaling a
# recomputed absolute value would retroactively double everything already
# earned and then undo it again the moment the multiplier expired, which is
# not what "points are doubled while the multiplier is active" means (see
# issue #73).

# Every bite is worth at least this much, so a multiplier is visible even on
# an almost-empty board.
BASE_POINTS_PER_FOOD = 10


def getGridFillPercentage(snakeLength, numLocations):
    """Whole percent of the grid the ophidian currently occupies.

    Returns 0 for a grid with no locations rather than dividing by zero.
    """
    if numLocations <= 0:
        return 0
    return int(snakeLength / numLocations * 100)


def pointsForFood(snakeLength, numLocations):
    """Points one growth-food pickup is worth, before any multiplier.

    A flat base plus one point per percent of the grid already filled, so a
    longer ophidian on a fuller board earns more per bite - the same "reward
    filling the grid" shape the previous derived formula had, expressed as
    an amount earned rather than a total recalculated.

    snakeLength is the length *after* the pickup grew the ophidian, which is
    when gameplay calls this.
    """
    return BASE_POINTS_PER_FOOD + getGridFillPercentage(snakeLength, numLocations)


def applyScoreMultiplier(points, multiplier):
    """Scales an award by an active multiplier, as whole points.

    Truncating keeps the score an integer no matter what multiplier a
    power-up declares, so no renderer has to format a fractional score.
    """
    return int(points * multiplier)


def formatScoreLabel(score, multiplier=1.0):
    """A score with its active multiplier annotated, e.g. "120 (x2)".

    One rule shared by both UIs, the way progression/shop.py owns its
    upgrade labels: the graphical HUD and the text UI's stats block would
    otherwise each spell out when and how a multiplier is annotated, which
    is how the two have drifted apart before (see issues #124 and #73). A
    neutral multiplier annotates nothing, so a run with no multiplier
    running reads exactly as it did before power-ups existed.
    """
    if multiplier > 1:
        return f"{score} (x{multiplier:g})"
    return str(score)
