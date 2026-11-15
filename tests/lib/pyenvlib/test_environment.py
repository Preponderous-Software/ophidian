import datetime

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


def test_is_entity_present_reflects_whether_it_was_added():
    environment = Environment("board", 3)
    entity = Entity("thing")
    assert environment.isEntityPresent(entity) is False
    environment.addEntity(entity)
    assert environment.isEntityPresent(entity) is True


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


def test_new_environment_is_stamped_with_the_time_it_was_made():
    before = datetime.datetime.now()
    environment = Environment("board", 2)
    after = datetime.datetime.now()
    assert before <= environment.getCreationDate() <= after


def test_set_id_and_set_name_replace_those_fields():
    environment = Environment("board", 2)
    environment.setID("environment-id")
    environment.setName("renamed")
    assert environment.getID() == "environment-id"
    assert environment.getName() == "renamed"


def test_add_entity_stamps_an_id_set_with_set_id():
    environment = Environment("board", 2)
    environment.setID("environment-id")
    entity = Entity("thing")
    environment.addEntity(entity)
    assert entity.getEnvironmentID() == "environment-id"


def test_print_info_prints_the_counts_and_ids(capsys):
    environment = Environment("board", 3)
    environment.setID("environment-id")
    environment.getGrid().setID("grid-id")
    environment.addEntity(Entity("thing"))
    environment.printInfo()
    out = capsys.readouterr().out
    assert "board" in out
    assert "Num entities:  1" in out
    assert "Num locations:  9" in out
    assert "ID:  environment-id" in out
    assert "Grid ID:  grid-id" in out
