from lib.pyenvlib.entity import Entity
from lib.pyenvlib.environment import Environment


def test_new_environment_has_a_square_grid_of_the_given_size():
    environment = Environment("board", 4)
    assert environment.getName() == "board"
    assert environment.getGrid().getColumns() == 4
    assert environment.getGrid().getRows() == 4
    assert environment.getNumEntities() == 0


def test_add_entity_stamps_the_environment_id_and_places_it():
    environment = Environment("board", 3)
    entity = Entity("thing")
    environment.addEntity(entity)
    assert entity.getEnvironmentID() == environment.getID()
    assert environment.getNumEntities() == 1
    assert environment.getEntity(entity.getID()) is entity


def test_add_entity_to_location_uses_that_location():
    environment = Environment("board", 3)
    target = environment.getGrid().getLocationByCoordinates(1, 2)
    entity = Entity("thing")
    environment.addEntityToLocation(entity, target)
    assert entity.getEnvironmentID() == environment.getID()
    assert target.isEntityPresent(entity)


def test_remove_entity_takes_it_off_the_grid():
    environment = Environment("board", 3)
    entity = Entity("thing")
    environment.addEntity(entity)
    environment.removeEntity(entity)
    assert environment.getNumEntities() == 0
    assert environment.getEntity(entity.getID()) is None


def test_set_grid_replaces_the_grid():
    environment = Environment("board", 3)
    replacement = Environment("other", 5).getGrid()
    environment.setGrid(replacement)
    assert environment.getGrid() is replacement
