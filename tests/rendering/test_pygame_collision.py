"""What the graphical UI shows when a run ends in a collision: the board
repainted red, then the obituary screen once the death frame has been held.
The text UI's half of this sequence lives in
tests/test_ophidian_collision_frame.py."""

from ophidian import Ophidian
from snake.snakePart import SnakePart

# a colour nothing in the game uses, so a cell showing it can only be the head
HEAD_SENTINEL_COLOR = (1, 2, 3)


def _headCentre(game):
    location = game.getLocation(game.selectedSnakePart)
    return (
        int((location.getX() + 0.5) * game.locationWidth),
        int((location.getY() + 0.5) * game.locationHeight),
    )


def _blockTheWayAhead(game):
    """Parks a segment on the cell the head is about to enter and returns
    the head, so the caller can drive it into the block itself."""
    head = game.selectedSnakePart
    grid, location = game.getLocationAndGrid(head)
    ahead = game.getLocationDirection(head.getDirection(), grid, location)
    if ahead == -1:
        # the head spawned against the wall it was facing; any other
        # direction with a cell behind it will do
        for direction in range(4):
            candidate = game.getLocationDirection(direction, grid, location)
            if candidate != -1:
                head.setDirection(direction)
                ahead = candidate
                break
    for entityId in list(ahead.getEntities().keys()):
        ahead.removeEntity(ahead.getEntity(entityId))
    blocker = SnakePart((1, 1, 1))
    game.environment.addEntityToLocation(blocker, ahead)
    game.snakeParts.append(blocker)
    # the paid-for near-miss would otherwise absorb the first collision
    game.secondWindAvailableThisRun = False
    return head


def test_the_board_is_drawn_in_its_own_colours_while_the_run_is_alive(pygameGame):
    game = pygameGame
    game.selectedSnakePart.setColor(HEAD_SENTINEL_COLOR)

    game.drawEnvironment()

    assert tuple(game.gameDisplay.get_at(_headCentre(game)))[:3] == (
        HEAD_SENTINEL_COLOR
    )


def test_the_whole_board_is_drawn_red_once_the_run_has_collided(pygameGame):
    game = pygameGame
    game.selectedSnakePart.setColor(HEAD_SENTINEL_COLOR)
    game.collision = True

    game.drawEnvironment()

    width, height = game.gameDisplay.get_size()
    for point in [
        _headCentre(game),
        (2, 2),
        (width - 3, 2),
        (2, height - 3),
        (width - 3, height - 3),
    ]:
        assert tuple(game.gameDisplay.get_at(point))[:3] == game.config.red


def test_a_graphical_collision_holds_the_death_frame_then_shows_the_obituary(
    pygameGame, monkeypatch
):
    game = pygameGame
    events = []
    monkeypatch.setattr(
        Ophidian, "renderCollisionFrame", lambda self: events.append("frame")
    )
    monkeypatch.setattr(
        Ophidian, "holdFrame", lambda self, seconds: events.append("hold")
    )
    monkeypatch.setattr(
        Ophidian, "renderObituaryScreen", lambda self: events.append("obituary")
    )
    head = _blockTheWayAhead(game)

    game.moveEntity(head, head.getDirection())

    assert events == ["frame", "hold", "obituary"]
