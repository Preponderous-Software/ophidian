from textui.textrenderer import TextRenderer

from ophidian import Ophidian
from snake.snakePart import SnakePart


def _makeGame(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True)


def _centerLocation(game):
    grid = game.environment.getGrid()
    centerX, centerY = grid.getRows() // 2, grid.getColumns() // 2
    return grid, grid.getLocationByCoordinates(centerX, centerY)


def _moveHeadToCenter(game):
    grid, centerLocation = _centerLocation(game)
    game.environment.removeEntity(game.selectedSnakePart)
    game.environment.addEntityToLocation(game.selectedSnakePart, centerLocation)
    return grid, centerLocation


def test_calculate_score_is_length_times_percentage_of_grid(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    numLocations = len(game.environment.grid.getLocations())
    # force a known snake length rather than relying on the initial spawn
    game.snakeParts = [game.selectedSnakePart] * 5

    game.calculateScore()

    expectedPercentage = int(5 / numLocations * 100)
    assert game.score == 5 * expectedPercentage


def test_get_color_of_location_returns_white_for_the_missing_sentinel(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    assert game.getColorOfLocation(-1) == game.config.white


def test_get_color_of_location_returns_white_for_an_empty_location(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    _, centerLocation = _centerLocation(game)
    for entityId in list(centerLocation.getEntities().keys()):
        centerLocation.removeEntity(centerLocation.getEntity(entityId))

    assert game.getColorOfLocation(centerLocation) == game.config.white


def test_get_color_of_location_returns_the_top_entitys_color(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    _, centerLocation = _moveHeadToCenter(game)
    game.selectedSnakePart.setColor((1, 2, 3))

    assert game.getColorOfLocation(centerLocation) == (1, 2, 3)


def test_get_location_direction_returns_each_cardinal_neighbor(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    grid, centerLocation = _centerLocation(game)

    assert game.getLocationDirection(0, grid, centerLocation) is grid.getUp(
        centerLocation
    )
    assert game.getLocationDirection(1, grid, centerLocation) is grid.getLeft(
        centerLocation
    )
    assert game.getLocationDirection(2, grid, centerLocation) is grid.getDown(
        centerLocation
    )
    assert game.getLocationDirection(3, grid, centerLocation) is grid.getRight(
        centerLocation
    )


def test_resolve_selected_cosmetic_color_returns_the_skins_fixed_color(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    game.saveManager.data["selectedCosmetic"] = "ember"

    assert game.resolveSelectedCosmeticColor() == (226, 88, 34)


def test_resolve_selected_cosmetic_color_falls_back_to_random_for_default(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    game.saveManager.data["selectedCosmetic"] = "default"
    monkeypatch.setattr("ophidian.random.randrange", lambda a, b: 77)

    assert game.resolveSelectedCosmeticColor() == (77, 77, 77)


def test_get_active_upgrades_summary_shows_second_wind_armed_state(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    game.saveManager.data["purchasedUpgrades"] = ["second_wind"]

    game.secondWindAvailableThisRun = True
    assert game.getActiveUpgradesSummary() == ["Second Wind (armed)"]

    game.secondWindAvailableThisRun = False
    assert game.getActiveUpgradesSummary() == ["Second Wind (used)"]


def test_check_for_level_progress_increments_level_when_below_ascension_cap(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    numLocations = len(game.environment.grid.getLocations())
    game.snakeParts = [game.selectedSnakePart] * (
        int(numLocations * game.config.levelProgressPercentageRequired) + 1
    )
    game.level = 1

    game.checkForLevelProgressAndReinitialize()

    assert game.level == 2
    assert game.ascensionBonus is None


def test_check_for_level_progress_ascends_once_grid_cap_would_be_exceeded(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    numLocations = len(game.environment.grid.getLocations())
    game.snakeParts = [game.selectedSnakePart] * (
        int(numLocations * game.config.levelProgressPercentageRequired) + 1
    )
    # baseGridSize + level * 2 > maxGridSize (5 + 6*2=17 > 15) is the first
    # level at which another level-up would exceed the grid size cap
    game.level = 6
    startingAscensionLevel = game.saveManager.data["ascensionLevel"]

    game.checkForLevelProgressAndReinitialize()

    assert game.level == 1
    assert game.ascensionBonus is not None
    assert game.saveManager.data["ascensionLevel"] == startingAscensionLevel + 1


def test_self_collision_without_restart_ends_the_run(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    monkeypatch.setattr("ophidian.time.sleep", lambda seconds: None)
    game.config.restartUponCollision = False
    game.secondWindAvailableThisRun = False
    grid, centerLocation = _moveHeadToCenter(game)
    blockingPart = SnakePart((9, 9, 9))
    game.environment.addEntityToLocation(blockingPart, grid.getUp(centerLocation))

    game.moveEntity(game.selectedSnakePart, 0)

    assert game.collision is True
    assert game.running is False


def test_second_wind_absorbs_the_first_collision_then_kills_on_the_second(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    monkeypatch.setattr("ophidian.time.sleep", lambda seconds: None)
    game.config.restartUponCollision = False
    game.secondWindAvailableThisRun = True
    grid, centerLocation = _moveHeadToCenter(game)
    blockingPart = SnakePart((9, 9, 9))
    game.environment.addEntityToLocation(blockingPart, grid.getUp(centerLocation))

    game.moveEntity(game.selectedSnakePart, 0)
    assert game.collision is False
    assert game.secondWindAvailableThisRun is False
    assert game.running is True

    game.moveEntity(game.selectedSnakePart, 0)
    assert game.collision is True
    assert game.running is False
