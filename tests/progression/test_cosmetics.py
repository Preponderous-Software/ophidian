from progression.save import defaultSaveData
from progression.cosmetics import (
    SKINS,
    checkForNewUnlocks,
    getNextCosmeticId,
    getSkinColor,
    getSkinName,
    getUnlockedSkinIds,
)


def test_no_unlocks_with_default_stats():
    saveData = defaultSaveData()
    newlyUnlocked = checkForNewUnlocks(saveData)
    assert newlyUnlocked == []
    assert saveData["unlockedCosmetics"] == ["default"]


def test_ember_unlocks_at_highest_level_reached_threshold():
    saveData = defaultSaveData()
    saveData["lifetimeStats"]["highestLevelReached"] = 2
    assert checkForNewUnlocks(saveData) == []
    assert "ember" not in saveData["unlockedCosmetics"]

    saveData["lifetimeStats"]["highestLevelReached"] = 3
    newlyUnlocked = checkForNewUnlocks(saveData)
    assert newlyUnlocked == ["ember"]
    assert "ember" in saveData["unlockedCosmetics"]


def test_frost_unlocks_at_total_ticks_survived_threshold():
    saveData = defaultSaveData()
    saveData["lifetimeStats"]["totalTicksSurvived"] = 299
    assert checkForNewUnlocks(saveData) == []

    saveData["lifetimeStats"]["totalTicksSurvived"] = 300
    newlyUnlocked = checkForNewUnlocks(saveData)
    assert newlyUnlocked == ["frost"]
    assert "frost" in saveData["unlockedCosmetics"]


def test_gold_unlocks_at_total_food_eaten_threshold():
    saveData = defaultSaveData()
    saveData["lifetimeStats"]["totalFoodEaten"] = 19
    assert checkForNewUnlocks(saveData) == []

    saveData["lifetimeStats"]["totalFoodEaten"] = 20
    newlyUnlocked = checkForNewUnlocks(saveData)
    assert newlyUnlocked == ["gold"]
    assert "gold" in saveData["unlockedCosmetics"]


def test_obsidian_unlocks_at_total_runs_threshold():
    saveData = defaultSaveData()
    saveData["lifetimeStats"]["totalRuns"] = 4
    assert checkForNewUnlocks(saveData) == []

    saveData["lifetimeStats"]["totalRuns"] = 5
    newlyUnlocked = checkForNewUnlocks(saveData)
    assert newlyUnlocked == ["obsidian"]
    assert "obsidian" in saveData["unlockedCosmetics"]


def test_calling_twice_is_idempotent_no_duplicates():
    saveData = defaultSaveData()
    saveData["lifetimeStats"]["highestLevelReached"] = 5
    saveData["lifetimeStats"]["totalRuns"] = 10

    firstPass = checkForNewUnlocks(saveData)
    assert set(firstPass) == {"ember", "obsidian"}

    secondPass = checkForNewUnlocks(saveData)
    assert secondPass == []
    assert saveData["unlockedCosmetics"].count("ember") == 1
    assert saveData["unlockedCosmetics"].count("obsidian") == 1


def test_already_unlocked_skin_not_reported_as_newly_unlocked_again():
    saveData = defaultSaveData()
    saveData["lifetimeStats"]["totalFoodEaten"] = 20
    checkForNewUnlocks(saveData)
    assert "gold" in saveData["unlockedCosmetics"]

    # stats improve further, but gold was already unlocked - shouldn't be
    # reported again, and shouldn't duplicate in the list
    saveData["lifetimeStats"]["totalFoodEaten"] = 45
    newlyUnlocked = checkForNewUnlocks(saveData)
    assert "gold" not in newlyUnlocked
    assert saveData["unlockedCosmetics"].count("gold") == 1


def test_all_thresholds_crossed_at_once_reports_all_new_unlocks():
    saveData = defaultSaveData()
    saveData["lifetimeStats"] = {
        "totalRuns": 5,
        "totalFoodEaten": 20,
        "totalTicksSurvived": 300,
        "longestLength": 1,
        "highestLevelReached": 3,
        "highestScore": 0,
    }
    newlyUnlocked = checkForNewUnlocks(saveData)
    assert set(newlyUnlocked) == {"ember", "frost", "gold", "obsidian"}
    assert set(saveData["unlockedCosmetics"]) == {
        "default",
        "ember",
        "frost",
        "gold",
        "obsidian",
    }


def test_registry_has_default_plus_four_milestone_skins():
    ids = {skin["id"] for skin in SKINS}
    assert ids == {"default", "ember", "frost", "gold", "obsidian"}


def test_default_skin_color_is_none_so_random_behavior_is_preserved():
    assert getSkinColor("default") is None


def test_get_skin_color_and_name_for_known_and_unknown_ids():
    assert getSkinColor("gold") == (212, 175, 55)
    assert getSkinName("gold") == "Gold"
    # unresolvable id falls back gracefully rather than raising
    assert getSkinColor("not-a-real-skin") is None
    assert getSkinName("not-a-real-skin") == "not-a-real-skin"


def test_get_unlocked_skin_ids_preserves_registry_order():
    saveData = defaultSaveData()
    saveData["unlockedCosmetics"] = ["default", "obsidian", "ember"]
    assert getUnlockedSkinIds(saveData) == ["default", "ember", "obsidian"]


def test_get_next_cosmetic_id_wraps_around_unlocked_only():
    saveData = defaultSaveData()
    saveData["unlockedCosmetics"] = ["default", "ember", "gold"]

    assert getNextCosmeticId(saveData, "default") == "ember"
    assert getNextCosmeticId(saveData, "ember") == "gold"
    assert getNextCosmeticId(saveData, "gold") == "default"

    # a locked/unknown current id falls back to the first unlocked skin
    assert getNextCosmeticId(saveData, "frost") == "default"
