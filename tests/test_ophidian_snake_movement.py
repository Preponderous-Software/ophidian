"""The one movement step of a tick: the head steps, the body follows.

moveEntity() and movePreviousSnakePart() are the mechanic every other test
takes for granted, and spawnSnakePart() is how the body gets its segments.
None of the three had a test of its own, so these characterize what they do
today - a change to how the ophidian moves or grows should be caught here
rather than by a player.
"""

import time

from textui.textrenderer import TextRenderer

from food.food import Food
from lib.pyenvlib.environment import Environment
from ophidian import Ophidian
from powerup.powerup import PowerUp
from snake.snakePart import SnakePart


def _makeGame(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True)


def _clearPickupsFromGrid(game):
    # initialize() drops a pickup on a random empty cell; a move in these
    # tests must land on an empty one so eating is never mixed into it
    grid = game.environment.getGrid()
    for locationId in grid.getLocations():
        location = grid.getLocation(locationId)
        for entityId in list(location.getEntities().keys()):
            entity = location.getEntity(entityId)
            if isinstance(entity, (Food, PowerUp)):
                location.removeEntity(entity)


def _placeHead(game, location):
    # the head spawns at a random grid location - put it somewhere known
    game.environment.removeEntity(game.selectedSnakePart)
    game.environment.addEntityToLocation(game.selectedSnakePart, location)
    return location


def _centerHead(game):
    grid = game.environment.getGrid()
    centerX, centerY = grid.getRows() // 2, grid.getColumns() // 2
    return _placeHead(game, grid.getLocationByCoordinates(centerX, centerY))


def _attachSegmentBehind(game, snakePart, location):
    """Links a new segment behind snakePart, the way spawnSnakePart() does,
    but at a chosen cell so the test knows where the body starts."""
    segment = SnakePart(snakePart.getColor())
    snakePart.setPrevious(segment)
    segment.setNext(snakePart)
    game.environment.addEntityToLocation(segment, location)
    game.snakeParts.append(segment)
    return segment


def _coordinates(location):
    return (location.getX(), location.getY())


# --- moveEntity: the head ---


def test_moving_up_steps_the_head_one_cell_up(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    start = _centerHead(game)

    game.moveEntity(game.selectedSnakePart, 0)

    assert _coordinates(game.getLocation(game.selectedSnakePart)) == (
        start.getX(),
        start.getY() - 1,
    )


def test_moving_left_steps_the_head_one_cell_left(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    start = _centerHead(game)

    game.moveEntity(game.selectedSnakePart, 1)

    assert _coordinates(game.getLocation(game.selectedSnakePart)) == (
        start.getX() - 1,
        start.getY(),
    )


def test_moving_down_steps_the_head_one_cell_down(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    start = _centerHead(game)

    game.moveEntity(game.selectedSnakePart, 2)

    assert _coordinates(game.getLocation(game.selectedSnakePart)) == (
        start.getX(),
        start.getY() + 1,
    )


def test_moving_right_steps_the_head_one_cell_right(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    start = _centerHead(game)

    game.moveEntity(game.selectedSnakePart, 3)

    assert _coordinates(game.getLocation(game.selectedSnakePart)) == (
        start.getX() + 1,
        start.getY(),
    )


def test_a_move_vacates_the_cell_the_head_left_and_remembers_it(tmp_path, monkeypatch):
    # lastPosition is what the segment behind will step into next
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    start = _centerHead(game)

    game.moveEntity(game.selectedSnakePart, 0)

    assert start.isEntityPresent(game.selectedSnakePart) is False
    assert game.selectedSnakePart.lastPosition is start


def test_a_move_into_the_border_is_dropped(tmp_path, monkeypatch):
    # there is no cell above the top row, so the head stays where it is -
    # neither a collision nor a wrap-around
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    grid = game.environment.getGrid()
    corner = _placeHead(game, grid.getLocationByCoordinates(0, 0))

    game.moveEntity(game.selectedSnakePart, 0)

    assert game.getLocation(game.selectedSnakePart) is corner
    assert game.selectedSnakePart.lastPosition == -1
    assert game.collision is False


def test_a_move_onto_an_empty_cell_neither_grows_nor_scores(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    _centerHead(game)
    lengthBefore = len(game.snakeParts)
    game.score = 0

    game.moveEntity(game.selectedSnakePart, 0)

    assert len(game.snakeParts) == lengthBefore
    assert game.score == 0


# --- movePreviousSnakePart: the body ---


def test_the_segment_behind_the_head_steps_into_the_cell_the_head_left(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    grid = game.environment.getGrid()
    start = _centerHead(game)
    behind = grid.getDown(start)
    body = _attachSegmentBehind(game, game.selectedSnakePart, behind)

    game.moveEntity(game.selectedSnakePart, 0)

    assert game.getLocation(body) is start
    assert behind.isEntityPresent(body) is False
    assert body.lastPosition is behind


def test_every_segment_of_a_chain_steps_into_the_one_ahead(tmp_path, monkeypatch):
    # head at the center, body below it, tail below that: after one step up
    # the whole column has shifted up by one and the tail's cell is empty
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    grid = game.environment.getGrid()
    start = _centerHead(game)
    bodyCell = grid.getDown(start)
    tailCell = grid.getDown(bodyCell)
    body = _attachSegmentBehind(game, game.selectedSnakePart, bodyCell)
    tail = _attachSegmentBehind(game, body, tailCell)

    game.moveEntity(game.selectedSnakePart, 0)

    assert game.getLocation(game.selectedSnakePart) is grid.getUp(start)
    assert game.getLocation(body) is start
    assert game.getLocation(tail) is bodyCell
    assert tailCell.getNumEntities() == 0


def test_the_body_stays_put_when_the_heads_move_is_dropped_at_the_border(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    grid = game.environment.getGrid()
    corner = _placeHead(game, grid.getLocationByCoordinates(0, 0))
    behind = grid.getDown(corner)
    body = _attachSegmentBehind(game, game.selectedSnakePart, behind)

    game.moveEntity(game.selectedSnakePart, 0)

    assert game.getLocation(body) is behind


def test_a_segment_that_is_not_on_the_grid_quits_the_game(tmp_path, monkeypatch):
    # a linked segment with no cell is a broken chain the game cannot
    # recover from: it reports the error, waits a moment, and quits
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    start = _centerHead(game)
    detached = SnakePart(game.selectedSnakePart.getColor())
    game.selectedSnakePart.setPrevious(detached)
    detached.setNext(game.selectedSnakePart)
    slept = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(seconds))
    quits = []
    monkeypatch.setattr(game, "quitApplication", lambda: quits.append("quit"))

    game.moveEntity(game.selectedSnakePart, 0)

    assert quits == ["quit"]
    assert slept == [1]
    # the head itself had already moved before the chain was found broken
    assert game.getLocation(game.selectedSnakePart) is not start
    assert game.getLocation(detached) == -1


# --- spawnSnakePart: growing the body ---


def test_spawning_a_segment_links_it_behind_the_given_part(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    _centerHead(game)
    head = game.selectedSnakePart
    lengthBefore = len(game.snakeParts)

    game.spawnSnakePart(head, (9, 9, 9))

    segment = head.previousSnakePart
    assert segment != -1
    assert segment.nextSnakePart is head
    assert segment.getColor() == (9, 9, 9)
    assert game.snakeParts[-1] is segment
    assert len(game.snakeParts) == lengthBefore + 1
    assert head.getTail() is segment


def test_a_new_segment_lands_on_an_empty_neighbor_off_the_heading(
    tmp_path, monkeypatch
):
    # the cell the part is facing is where it moves next, so a segment
    # spawned there would be collided with on the very next tick
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    grid = game.environment.getGrid()
    center = _centerHead(game)
    head = game.selectedSnakePart
    head.setDirection(0)
    offered = []
    monkeypatch.setattr(
        "ophidian.random.choice",
        lambda candidates: offered.append(candidates) or candidates[0],
    )

    game.spawnSnakePart(head, head.getColor())

    segment = head.previousSnakePart
    neighbors = [
        grid.getUp(center),
        grid.getLeft(center),
        grid.getDown(center),
        grid.getRight(center),
    ]
    assert game.getLocation(segment) in neighbors
    assert game.getLocation(segment) is not grid.getUp(center)
    assert len(offered) == 1
    assert grid.getUp(center) not in offered[0]
    assert sorted(_coordinates(c) for c in offered[0]) == sorted(
        _coordinates(c) for c in neighbors[1:]
    )


def test_a_new_segment_skips_occupied_neighbors(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    grid = game.environment.getGrid()
    center = _centerHead(game)
    head = game.selectedSnakePart
    head.setDirection(0)
    game.environment.addEntityToLocation(Food((1, 1, 1)), grid.getLeft(center))
    game.environment.addEntityToLocation(SnakePart((2, 2, 2)), grid.getDown(center))

    game.spawnSnakePart(head, head.getColor())

    # right is the only neighbor that is both empty and not the heading
    assert game.getLocation(head.previousSnakePart) is grid.getRight(center)


def test_a_new_segment_falls_back_to_an_occupied_neighbor_when_none_is_empty(
    tmp_path, monkeypatch
):
    # in a corner facing right there are two neighbors: right (excluded as
    # the heading) and down. With down occupied there is no empty candidate,
    # and stacking on down beats spawning nothing or looping forever
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    grid = game.environment.getGrid()
    corner = _placeHead(game, grid.getLocationByCoordinates(0, 0))
    head = game.selectedSnakePart
    head.setDirection(3)
    game.environment.addEntityToLocation(Food((1, 1, 1)), grid.getDown(corner))

    game.spawnSnakePart(head, head.getColor())

    assert game.getLocation(head.previousSnakePart) is grid.getDown(corner)


def test_a_new_segment_prefers_an_occupied_neighbor_over_the_heading_cell(
    tmp_path, monkeypatch
):
    # corner, facing down, with both neighbors occupied: nothing is empty,
    # and the fallback still keeps the heading cell out of the running as
    # long as any other neighbor exists
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    grid = game.environment.getGrid()
    corner = _placeHead(game, grid.getLocationByCoordinates(0, 0))
    head = game.selectedSnakePart
    head.setDirection(2)
    game.environment.addEntityToLocation(SnakePart((2, 2, 2)), grid.getRight(corner))
    game.environment.addEntityToLocation(SnakePart((3, 3, 3)), grid.getDown(corner))

    game.spawnSnakePart(head, head.getColor())

    # down is the heading, so right (occupied but not excluded) is chosen
    assert game.getLocation(head.previousSnakePart) is grid.getRight(corner)


def test_a_new_segment_stacks_on_the_part_itself_when_there_are_no_neighbors(
    tmp_path, monkeypatch
):
    # a 1x1 grid has no neighbors in any direction
    game = _makeGame(monkeypatch, tmp_path)
    game.environment = Environment("tiny", 1)
    game.snakeParts = []
    head = SnakePart((5, 5, 5))
    game.environment.addEntity(head)
    game.snakeParts.append(head)
    only = game.getLocation(head)

    game.spawnSnakePart(head, head.getColor())

    assert game.getLocation(head.previousSnakePart) is only
    assert only.getNumEntities() == 2
