from progression.ascension import (
    applyAscension,
    computeGridSizeForLevel,
    shouldAscend,
)

BASE_GRID_SIZE = 5
MIN_GRID_SIZE = 5
MAX_GRID_SIZE = 12


def test_compute_grid_size_matches_original_formula_for_level_one():
    assert (
        computeGridSizeForLevel(1, BASE_GRID_SIZE, MIN_GRID_SIZE, MAX_GRID_SIZE)
        == BASE_GRID_SIZE
    )


def test_compute_grid_size_matches_original_formula_for_higher_levels():
    # original formula: gridSize + (level - 1) * 2
    assert (
        computeGridSizeForLevel(2, BASE_GRID_SIZE, MIN_GRID_SIZE, MAX_GRID_SIZE) == 7
    )
    assert (
        computeGridSizeForLevel(3, BASE_GRID_SIZE, MIN_GRID_SIZE, MAX_GRID_SIZE) == 9
    )
    assert (
        computeGridSizeForLevel(4, BASE_GRID_SIZE, MIN_GRID_SIZE, MAX_GRID_SIZE) == 11
    )


def test_compute_grid_size_clamps_at_max_grid_size():
    # level 5 would be 5 + 4*2 = 13, which exceeds maxGridSize of 12
    assert (
        computeGridSizeForLevel(5, BASE_GRID_SIZE, MIN_GRID_SIZE, MAX_GRID_SIZE)
        == MAX_GRID_SIZE
    )
    assert (
        computeGridSizeForLevel(100, BASE_GRID_SIZE, MIN_GRID_SIZE, MAX_GRID_SIZE)
        == MAX_GRID_SIZE
    )


def test_should_ascend_false_while_under_cap():
    for level in (1, 2, 3):
        assert not shouldAscend(level, BASE_GRID_SIZE, MIN_GRID_SIZE, MAX_GRID_SIZE)


def test_should_ascend_true_right_at_boundary():
    # at level 4, current size is 11; next level's size would be 13 > 12
    assert shouldAscend(4, BASE_GRID_SIZE, MIN_GRID_SIZE, MAX_GRID_SIZE)
    # further beyond the boundary should remain True
    assert shouldAscend(5, BASE_GRID_SIZE, MIN_GRID_SIZE, MAX_GRID_SIZE)


def test_apply_ascension_increments_ascension_level_on_fresh_save():
    saveData = {"ascensionLevel": 0}
    applyAscension(saveData)
    assert saveData["ascensionLevel"] == 1


def test_apply_ascension_returns_bounded_bonus():
    saveData = {"ascensionLevel": 0}
    bonus = applyAscension(saveData)
    assert bonus["tickSpeedMultiplier"] <= 1
    assert bonus["tickSpeedMultiplier"] > 0
    assert isinstance(bonus["startingBonusSegments"], int)
    assert bonus["startingBonusSegments"] >= 0


def test_apply_ascension_twice_increments_by_one_each_time_not_compounding():
    saveData = {"ascensionLevel": 0}
    applyAscension(saveData)
    assert saveData["ascensionLevel"] == 1
    applyAscension(saveData)
    assert saveData["ascensionLevel"] == 2


def test_apply_ascension_bonus_segments_stay_capped_after_many_ascensions():
    # regression test: startingBonusSegments must stay bounded (the
    # docstring promises a "small, bounded" bonus) - it must never grow to
    # the point spawnSnakePart could struggle to place segments on a
    # freshly-reset, minimum-size grid
    saveData = {"ascensionLevel": 0}
    for _ in range(50):
        bonus = applyAscension(saveData)
    assert saveData["ascensionLevel"] == 50
    assert bonus["startingBonusSegments"] <= 5


def test_default_config_reaches_all_curated_biome_levels_before_ascending():
    # regression test: with the actual default Config values, the level
    # counter must reach at least level 6 (the last curated biome in
    # progression/lore.py's BIOME_TABLE) before shouldAscend fires and
    # resets it back to 1 - otherwise curated biome content is silently
    # unreachable dead code
    from config.config import Config

    config = Config()
    highestLevelReached = 1
    level = 1
    for _ in range(20):
        if shouldAscend(
            level, config.gridSize, config.minGridSize, config.maxGridSize
        ):
            level = 1
        else:
            level += 1
            highestLevelReached = max(highestLevelReached, level)
    assert highestLevelReached >= 6
