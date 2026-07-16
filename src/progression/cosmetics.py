"""Cosmetic skin registry and unlock evaluation.

Cosmetics are purely visual snake-color skins, earned through play and
persisted in the save file (see progression/save.py). None of this affects
gameplay mechanics.

# @author Daniel McCoy Stephenson
# @since July 4th, 2026
"""

DEFAULT_COSMETIC_ID = "default"

# Each skin is a plain dict:
#   id: str                       - stable identifier, stored in the save file
#   name: str                     - display name
#   color: tuple(int, int, int)   - RGB color, or None for "default" which
#                                    preserves the existing random-color feel
#   unlockCondition: fn(lifetimeStats: dict) -> bool
SKINS = [
    {
        "id": DEFAULT_COSMETIC_ID,
        "name": "Default",
        "color": None,
        "unlockCondition": lambda stats: True,
    },
    {
        "id": "ember",
        "name": "Ember",
        "color": (226, 88, 34),
        "unlockCondition": lambda stats: stats.get("highestLevelReached", 0) >= 3,
    },
    {
        "id": "frost",
        "name": "Frost",
        "color": (137, 207, 240),
        "unlockCondition": lambda stats: stats.get("totalTicksSurvived", 0) >= 300,
    },
    {
        "id": "gold",
        "name": "Gold",
        "color": (212, 175, 55),
        "unlockCondition": lambda stats: stats.get("totalFoodEaten", 0) >= 20,
    },
    {
        "id": "obsidian",
        "name": "Obsidian",
        "color": (40, 40, 45),
        "unlockCondition": lambda stats: stats.get("totalRuns", 0) >= 5,
    },
]

SKINS_BY_ID = {skin["id"]: skin for skin in SKINS}


def getSkin(skinId):
    """Returns the skin dict for skinId, or None if unknown."""
    return SKINS_BY_ID.get(skinId)


def getSkinColor(skinId):
    """Returns the RGB color tuple for skinId, or None if the skin is
    unknown or resolves to the randomized default look."""
    skin = getSkin(skinId)
    if skin is None:
        return None
    return skin["color"]


def getSkinName(skinId):
    """Returns the display name for skinId, falling back to the raw id
    if it isn't a known skin."""
    skin = getSkin(skinId)
    if skin is None:
        return skinId
    return skin["name"]


def checkForNewUnlocks(saveData):
    """Compares lifetimeStats against each skin's unlockCondition and adds
    any newly-qualifying skin id to saveData["unlockedCosmetics"].

    Mutates saveData in place. Idempotent - calling this repeatedly with the
    same stats never adds duplicates and never re-reports a skin that's
    already unlocked as newly unlocked.

    Returns the list of skin ids newly unlocked by this call (may be empty).
    """
    stats = saveData.get("lifetimeStats", {})
    unlocked = saveData.setdefault("unlockedCosmetics", [DEFAULT_COSMETIC_ID])

    newlyUnlocked = []
    for skin in SKINS:
        if skin["id"] in unlocked:
            continue
        if skin["unlockCondition"](stats):
            unlocked.append(skin["id"])
            newlyUnlocked.append(skin["id"])
    return newlyUnlocked


def getUnlockedSkinIds(saveData):
    """Returns the unlocked skin ids in registry order (unknown ids, e.g.
    from a save written by a newer version, are appended at the end)."""
    unlocked = saveData.get("unlockedCosmetics", [DEFAULT_COSMETIC_ID])
    ordered = [skin["id"] for skin in SKINS if skin["id"] in unlocked]
    extras = [skinId for skinId in unlocked if skinId not in SKINS_BY_ID]
    return ordered + extras


def getNextCosmeticId(saveData, currentId):
    """Returns the next unlocked skin id after currentId, wrapping around.
    Falls back to the first unlocked skin if currentId isn't unlocked."""
    unlockedIds = getUnlockedSkinIds(saveData)
    if not unlockedIds:
        return DEFAULT_COSMETIC_ID
    if currentId not in unlockedIds:
        return unlockedIds[0]
    index = unlockedIds.index(currentId)
    return unlockedIds[(index + 1) % len(unlockedIds)]
