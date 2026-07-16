# @author Daniel McCoy Stephenson
# @since July 4th, 2026

# Meta-currency + permanent upgrade shop MVP.
#
# Currency is earned from a run's final snake length and banked permanently
# in SaveManager.data["currency"]. It can be spent on a small registry of
# permanent upgrades (SaveManager.data["purchasedUpgrades"]) that change how
# future runs start or play out. Everything here is a pure function operating
# on plain dicts so it can be unit tested without any UI or game loop.

UPGRADES = {
    "head_start": {
        "id": "head_start",
        "name": "Head Start",
        "cost": 10,
        "description": "Start each run with 2 extra pre-grown snake segments instead of 1.",
    },
    "slow_starter": {
        "id": "slow_starter",
        "name": "Slow Starter",
        "cost": 15,
        "description": "The first level's tick speed starts 25% slower, giving more reaction time early on.",
    },
    "second_wind": {
        "id": "second_wind",
        "name": "Second Wind",
        "cost": 25,
        "description": "The first collision each run is survived as a near-miss; only a second collision ends the run.",
    },
}

# Stable display order for the shop menu.
UPGRADE_ORDER = ["head_start", "slow_starter", "second_wind"]


def currencyEarnedForRun(length):
    """Currency earned for a finished run based on its final snake length.

    MVP rule: 1 currency per food eaten. This mirrors how
    SaveManager.recordRun computes totalFoodEaten (max(0, length - 1)),
    since a snake of length 1 has eaten no food yet.
    """
    return max(0, length - 1)


def getUpgrade(upgradeId):
    """Returns the upgrade definition dict for upgradeId, or None if unknown."""
    return UPGRADES.get(upgradeId)


def listUpgrades():
    """Returns all purchasable upgrades in a stable, display-friendly order."""
    return [UPGRADES[upgradeId] for upgradeId in UPGRADE_ORDER]


def purchaseUpgrade(saveData, upgradeId):
    """Attempts to buy upgradeId using saveData["currency"].

    On success: deducts the upgrade's cost from saveData["currency"] and
    appends upgradeId to saveData["purchasedUpgrades"]. On failure (unknown
    upgrade, already owned, or insufficient currency): saveData is left
    completely unmutated.

    Does not persist anything to disk -- callers (e.g. SaveManager.save())
    are responsible for that.

    Returns a (success, message) tuple.
    """
    upgrade = UPGRADES.get(upgradeId)
    if upgrade is None:
        return False, "Unknown upgrade: {}".format(upgradeId)

    purchasedUpgrades = saveData.setdefault("purchasedUpgrades", [])
    if upgradeId in purchasedUpgrades:
        return False, "{} is already owned.".format(upgrade["name"])

    cost = upgrade["cost"]
    currentCurrency = saveData.get("currency", 0)
    if currentCurrency < cost:
        return False, "Not enough currency for {} (costs {}, you have {}).".format(
            upgrade["name"], cost, currentCurrency
        )

    saveData["currency"] = currentCurrency - cost
    purchasedUpgrades.append(upgradeId)
    return True, "Purchased {} for {} currency.".format(upgrade["name"], cost)


def getActiveUpgradeLabels(saveData, secondWindAvailableThisRun):
    """Returns a display label for each owned upgrade, so the player can see
    what's active without having to reopen the shop. second_wind additionally
    shows whether it's still armed for the current run or already used.
    """
    purchasedUpgrades = saveData.get("purchasedUpgrades", [])
    labels = []
    for upgrade in listUpgrades():
        if upgrade["id"] not in purchasedUpgrades:
            continue
        label = upgrade["name"]
        if upgrade["id"] == "second_wind":
            label += " (armed)" if secondWindAvailableThisRun else " (used)"
        labels.append(label)
    return labels
