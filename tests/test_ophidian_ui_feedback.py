from textui.textrenderer import TextRenderer

from ophidian import Ophidian
from progression.cosmetics import SKINS_BY_ID
from snake.snakePart import SnakePart


def _makeGame(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True)


def test_cycle_selected_cosmetic_updates_live_snake_part_color(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    game.saveManager.data["unlockedCosmetics"] = ["default", "ember"]
    game.saveManager.data["selectedCosmetic"] = "default"

    game.cycleSelectedCosmetic()

    assert game.saveManager.data["selectedCosmetic"] == "ember"
    assert game.selectedSnakePart.getColor() == SKINS_BY_ID["ember"]["color"]


def test_cycle_selected_cosmetic_wraps_and_updates_color_each_time(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    game.saveManager.data["unlockedCosmetics"] = ["default", "ember", "frost"]
    game.saveManager.data["selectedCosmetic"] = "frost"

    game.cycleSelectedCosmetic()

    assert game.saveManager.data["selectedCosmetic"] == "default"
    # default has no fixed color, but it must differ from frost's fixed color
    assert game.selectedSnakePart.getColor() != SKINS_BY_ID["frost"]["color"]


def test_notify_is_console_only_in_text_ui_mode(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)

    game.notify("hello")

    # text UI has no pygame banner queue to populate
    assert game.uiBanner.queue == []


def test_notify_queues_messages_instead_of_clobbering(tmp_path, monkeypatch):
    # regression test: checkForLevelProgressAndReinitialize's ascension
    # notify() is immediately followed by initialize()'s biome-arrival
    # notify() in the same synchronous call chain, before any frame is ever
    # drawn - a single-slot uiMessage would silently lose the first message
    game = _makeGame(monkeypatch, tmp_path)
    game.config.useTextUI = False  # pretend pygame mode without a real display

    game.notify("The ophidian ascends! (Ascension 1)")
    game.notify("Medusa enters The Sunken Grove.")

    assert list(game.uiBanner.queue) == [
        "The ophidian ascends! (Ascension 1)",
        "Medusa enters The Sunken Grove.",
    ]


def test_spawn_snake_part_prefers_an_empty_neighbor_over_occupied_ones(
    tmp_path, monkeypatch
):
    # regression test: spawnSnakePart used to pick a random neighbor with no
    # occupancy check at all, so it could silently stack a new segment
    # directly on top of an existing one (head_start's 2 segments and
    # ascension's startingBonusSegments both spawn several in a row). Here
    # every neighbor except one is deliberately occupied, so a correct
    # implementation has exactly one legal cell to land on.
    game = _makeGame(monkeypatch, tmp_path)
    grid = game.environment.getGrid()

    # the head spawns at a random grid location, which may be on an edge
    # (missing some neighbors) - move it to the center so all 4 neighbors
    # are guaranteed to exist, keeping this test deterministic
    centerX, centerY = grid.getRows() // 2, grid.getColumns() // 2
    tailLocation = grid.getLocationByCoordinates(centerX, centerY)
    game.environment.removeEntity(game.selectedSnakePart)
    game.environment.addEntityToLocation(game.selectedSnakePart, tailLocation)

    # spawnFood() during initialize() may have placed food on any of these
    # cells before we moved the head here - clear them all so the occupancy
    # setup below is deterministic regardless of where food landed
    leftLocation = grid.getLeft(tailLocation)
    for neighbor in (grid.getUp(tailLocation), grid.getDown(tailLocation), grid.getRight(tailLocation), leftLocation):
        for entityId in list(neighbor.getEntities().keys()):
            neighbor.removeEntity(neighbor.getEntity(entityId))

    # selectedSnakePart's direction defaults to 0 (up), which
    # spawnSnakePart always excludes regardless of occupancy - occupy the
    # remaining two neighbors, leaving exactly "left" empty
    game.environment.addEntityToLocation(SnakePart((0, 0, 0)), grid.getDown(tailLocation))
    game.environment.addEntityToLocation(SnakePart((0, 0, 0)), grid.getRight(tailLocation))

    game.spawnSnakePart(game.selectedSnakePart, (1, 2, 3))

    newSegment = game.snakeParts[-1]
    assert game.getLocation(newSegment) is grid.getLeft(tailLocation)
