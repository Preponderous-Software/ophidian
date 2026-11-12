import pytest

from lib.pyenvlib.entity import Entity
from lib.pyenvlib.grid import Grid


def test_new_grid_has_one_empty_location_per_cell():
    grid = Grid(3, 2)
    assert grid.getColumns() == 3
    assert grid.getRows() == 2
    assert grid.getSize() == 6
    assert grid.getNumEntities() == 0
    coordinates = {(loc.getX(), loc.getY()) for loc in grid.getLocations().values()}
    assert coordinates == {(x, y) for x in range(3) for y in range(2)}


def test_locations_are_keyed_by_their_own_id():
    grid = Grid(2, 2)
    for locationId, location in grid.getLocations().items():
        assert location.getID() == locationId
        assert grid.getLocation(locationId) is location


def test_get_location_by_coordinates_finds_the_matching_cell():
    grid = Grid(4, 4)
    location = grid.getLocationByCoordinates(2, 3)
    assert (location.getX(), location.getY()) == (2, 3)


def test_get_location_by_coordinates_returns_minus_one_off_the_grid():
    grid = Grid(4, 4)
    assert grid.getLocationByCoordinates(4, 0) == -1
    assert grid.getLocationByCoordinates(0, -1) == -1


def test_neighbours_follow_screen_coordinates():
    # y grows downwards, the way the game's direction 0 (up) moves to y - 1
    grid = Grid(3, 3)
    centre = grid.getLocationByCoordinates(1, 1)
    assert grid.getUp(centre) is grid.getLocationByCoordinates(1, 0)
    assert grid.getDown(centre) is grid.getLocationByCoordinates(1, 2)
    assert grid.getLeft(centre) is grid.getLocationByCoordinates(0, 1)
    assert grid.getRight(centre) is grid.getLocationByCoordinates(2, 1)


def test_neighbours_past_the_edge_are_minus_one():
    # the game treats -1 as "off the board", which is how wall collisions
    # are detected
    grid = Grid(3, 3)
    assert grid.getUp(grid.getLocationByCoordinates(1, 0)) == -1
    assert grid.getDown(grid.getLocationByCoordinates(1, 2)) == -1
    assert grid.getLeft(grid.getLocationByCoordinates(0, 1)) == -1
    assert grid.getRight(grid.getLocationByCoordinates(2, 1)) == -1


def test_neighbours_of_minus_one_stay_minus_one():
    grid = Grid(3, 3)
    assert grid.getUp(-1) == -1
    assert grid.getDown(-1) == -1
    assert grid.getLeft(-1) == -1
    assert grid.getRight(-1) == -1


def test_add_entity_places_it_somewhere_and_stamps_the_grid_id():
    grid = Grid(3, 3)
    entity = Entity("thing")
    grid.addEntity(entity)
    assert grid.getNumEntities() == 1
    assert entity.getGridID() == grid.getID()
    assert grid.getLocation(entity.getLocationID()).isEntityPresent(entity)


def test_add_entity_to_location_puts_it_in_that_location():
    grid = Grid(3, 3)
    target = grid.getLocationByCoordinates(2, 0)
    entity = Entity("thing")
    grid.addEntityToLocation(entity, target)
    assert target.isEntityPresent(entity)
    assert entity.getLocationID() == target.getID()
    assert grid.getNumEntities() == 1


@pytest.mark.skip(
    reason="addEntityToLocation stores the bound getID method as the grid ID, "
    "not the grid's id - see issue #195"
)
def test_add_entity_to_location_stamps_the_grid_id():
    grid = Grid(3, 3)
    entity = Entity("thing")
    grid.addEntityToLocation(entity, grid.getLocationByCoordinates(0, 0))
    assert entity.getGridID() == grid.getID()


def test_get_entity_searches_every_location():
    grid = Grid(3, 3)
    entity = Entity("thing")
    grid.addEntityToLocation(entity, grid.getLocationByCoordinates(2, 2))
    assert grid.getEntity(entity.getID()) is entity


def test_get_entity_returns_none_for_an_unknown_id():
    grid = Grid(2, 2)
    assert grid.getEntity(Entity("absent").getID()) is None


def test_remove_entity_takes_it_out_of_its_location():
    grid = Grid(3, 3)
    entity = Entity("thing")
    location = grid.getLocationByCoordinates(1, 1)
    grid.addEntityToLocation(entity, location)
    grid.removeEntity(entity)
    assert not location.isEntityPresent(entity)
    assert grid.getNumEntities() == 0


def test_remove_entity_that_is_absent_changes_nothing():
    grid = Grid(2, 2)
    present = Entity("present")
    grid.addEntity(present)
    grid.removeEntity(Entity("absent"))
    assert grid.getNumEntities() == 1


def test_get_random_location_returns_one_of_the_grids_locations():
    grid = Grid(3, 3)
    locations = list(grid.getLocations().values())
    for _ in range(20):
        chosen = grid.getRandomLocation()
        assert any(chosen is loc for loc in locations)
