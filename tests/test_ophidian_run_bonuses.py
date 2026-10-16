"""The bonuses initialize() applies at the start of every run.

The shop's purchase rules live in tests/progression/test_shop.py and the
ascension bonus formula in tests/progression/test_ascension.py; these cover
what initialize() does with them - the tick speed a run starts at, how many
segments the snake starts with, and whether Second Wind is armed.
"""

import pytest

from textui.textrenderer import TextRenderer

from ophidian import Ophidian


def _makeGame(monkeypatch, tmp_path, purchasedUpgrades=None):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    game = Ophidian(useTextUI=True)
    game.saveManager.data["purchasedUpgrades"] = list(purchasedUpgrades or [])
    return game


def _chainLength(head):
    length = 1
    part = head
    while part.hasPrevious():
        part = part.previousSnakePart
        length += 1
    return length


def test_a_run_with_no_bonuses_starts_at_base_speed_with_one_segment(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)

    game.initialize()

    assert game.config.tickSpeed == game.baseTickSpeed
    assert len(game.snakeParts) == 1
    assert game.secondWindAvailableThisRun is False


def test_slow_starter_slows_the_first_level_by_a_quarter(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path, purchasedUpgrades=["slow_starter"])
    game.level = 1

    game.initialize()

    assert game.config.tickSpeed == pytest.approx(game.baseTickSpeed * 1.25)


def test_slow_starter_has_no_effect_past_the_first_level(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path, purchasedUpgrades=["slow_starter"])
    game.level = 2

    game.initialize()

    assert game.config.tickSpeed == game.baseTickSpeed


def test_head_start_begins_the_run_with_two_extra_linked_segments(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path, purchasedUpgrades=["head_start"])

    game.initialize()

    assert len(game.snakeParts) == 3
    assert _chainLength(game.selectedSnakePart) == 3
    grid = game.environment.getGrid()
    for part in game.snakeParts:
        assert grid.getLocation(part.getLocationID()).isEntityPresent(part)


def test_second_wind_is_rearmed_at_the_start_of_every_run(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path, purchasedUpgrades=["second_wind"])
    game.initialize()
    assert game.secondWindAvailableThisRun is True
    game.secondWindAvailableThisRun = False

    game.initialize()

    assert game.secondWindAvailableThisRun is True


def test_an_ascension_bonus_speeds_up_the_run_and_adds_starting_segments(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    game.ascensionBonus = {"tickSpeedMultiplier": 0.8, "startingBonusSegments": 2}

    game.initialize()

    assert game.config.tickSpeed == pytest.approx(game.baseTickSpeed * 0.8)
    assert len(game.snakeParts) == 3
    assert _chainLength(game.selectedSnakePart) == 3


def test_head_start_and_ascension_segments_stack(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path, purchasedUpgrades=["head_start"])
    game.ascensionBonus = {"tickSpeedMultiplier": 1, "startingBonusSegments": 2}

    game.initialize()

    assert len(game.snakeParts) == 5
    assert _chainLength(game.selectedSnakePart) == 5


def test_tick_speed_bonuses_do_not_compound_across_runs(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path, purchasedUpgrades=["slow_starter"])
    game.level = 1
    game.ascensionBonus = {"tickSpeedMultiplier": 0.8, "startingBonusSegments": 0}

    game.initialize()
    firstRunTickSpeed = game.config.tickSpeed
    game.initialize()

    assert game.config.tickSpeed == firstRunTickSpeed
    assert firstRunTickSpeed == pytest.approx(game.baseTickSpeed * 0.8 * 1.25)
