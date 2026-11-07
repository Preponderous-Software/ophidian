"""The bonuses initialize() applies at the start of every run.

The shop's purchase rules live in tests/progression/test_shop.py and the
ascension bonus formula in tests/progression/test_ascension.py; these cover
what initialize() does with them - the tick speed a run starts at, how many
segments the snake starts with, and whether Second Wind is armed.
"""

import json
import random

import pytest

from textui.textrenderer import TextRenderer

from lib.pyenvlib.environment import Environment
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


def _adjacent(first, second):
    return abs(first.getX() - second.getX()) + abs(first.getY() - second.getY()) == 1


def test_the_longest_starting_body_never_stacks_and_never_covers_the_pickup(
    tmp_path, monkeypatch
):
    # regression test for #188: the longest start the game can produce, on
    # its smallest board, where growing one random neighbor at a time stacked
    # segments in roughly one run in eight
    game = _makeGame(monkeypatch, tmp_path, purchasedUpgrades=["head_start"])
    game.ascensionBonus = {"tickSpeedMultiplier": 1, "startingBonusSegments": 5}
    random.seed(188)

    for _ in range(300):
        game.initialize()

        grid = game.environment.getGrid()
        locations = [game.getLocation(part) for part in game.snakeParts]
        assert len(locations) == 8
        assert len(set(locations)) == 8
        for first, second in zip(locations, locations[1:]):
            assert _adjacent(first, second)
        head = game.selectedSnakePart
        headedFor = game.getLocationDirection(head.getDirection(), grid, locations[0])
        assert headedFor not in locations
        assert grid.getNumEntities() == 9
        for location in grid.getLocations().values():
            assert location.getNumEntities() <= 1


def test_the_starting_body_is_linked_from_head_to_tail_in_the_head_color(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path, purchasedUpgrades=["head_start"])
    game.ascensionBonus = {"tickSpeedMultiplier": 1, "startingBonusSegments": 1}

    game.initialize()

    part = game.selectedSnakePart
    for expected in game.snakeParts[1:]:
        assert part.previousSnakePart is expected
        assert expected.nextSnakePart is part
        assert expected.getColor() == game.selectedSnakePart.getColor()
        part = expected


def test_the_starting_body_search_backs_out_of_a_dead_end(tmp_path, monkeypatch):
    # from the middle of a 3x3 facing up, the first turns tried lead into the
    # top left corner, and only backing up finds a path 5 cells long
    game = _makeGame(monkeypatch, tmp_path)
    game.environment = Environment("small", 3)
    game.snakeParts = []
    head = game.selectedSnakePart
    grid = game.environment.getGrid()
    game.environment.addEntityToLocation(head, grid.getLocationByCoordinates(1, 1))
    head.setDirection(0)
    monkeypatch.setattr("ophidian.random.shuffle", lambda candidates: None)

    path = game.findStartingBodyPath(5)

    assert [(cell.getX(), cell.getY()) for cell in path] == [
        (0, 1),
        (0, 2),
        (1, 2),
        (2, 2),
        (2, 1),
    ]


def test_a_board_too_small_for_the_starting_body_still_grants_every_segment(
    tmp_path, monkeypatch
):
    # a 2x2 board has 3 free cells at most, and one is the heading, so a path
    # of 3 can't exist; falling back keeps the segments the player paid for
    game = _makeGame(monkeypatch, tmp_path, purchasedUpgrades=["head_start"])
    game.ascensionBonus = {"tickSpeedMultiplier": 1, "startingBonusSegments": 1}
    game.config.gridSize = 2
    game.config.minGridSize = 2
    monkeypatch.setattr(
        Environment,
        "addEntity",
        lambda self, entity: self.addEntityToLocation(
            entity, self.getGrid().getLocationByCoordinates(0, 1)
        ),
    )

    game.initialize()

    assert game.findStartingBodyPath(3) is None
    assert len(game.snakeParts) == 4
    assert _chainLength(game.selectedSnakePart) == 4


def test_tick_speed_bonuses_do_not_compound_across_runs(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path, purchasedUpgrades=["slow_starter"])
    game.level = 1
    game.ascensionBonus = {"tickSpeedMultiplier": 0.8, "startingBonusSegments": 0}

    game.initialize()
    firstRunTickSpeed = game.config.tickSpeed
    game.initialize()

    assert game.config.tickSpeed == firstRunTickSpeed
    assert firstRunTickSpeed == pytest.approx(game.baseTickSpeed * 0.8 * 1.25)


def test_a_saved_ascension_level_restores_its_bonus_on_relaunch(tmp_path, monkeypatch):
    (tmp_path / "save.json").write_text(json.dumps({"ascensionLevel": 3}))

    game = _makeGame(monkeypatch, tmp_path)

    assert game.config.tickSpeed == pytest.approx(game.baseTickSpeed * 0.85)
    assert len(game.snakeParts) == 2
    assert _chainLength(game.selectedSnakePart) == 2
