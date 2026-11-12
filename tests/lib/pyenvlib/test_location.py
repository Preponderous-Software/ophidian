from lib.pyenvlib.entity import Entity
from lib.pyenvlib.location import Location


def test_new_location_holds_its_coordinates_and_no_entities():
    location = Location(3, 7)
    assert (location.getX(), location.getY()) == (3, 7)
    assert location.getNumEntities() == 0
    assert location.getEntities() == {}


def test_add_entity_stores_it_and_stamps_the_location_id():
    location = Location(0, 0)
    entity = Entity("thing")
    location.addEntity(entity)
    assert location.isEntityPresent(entity)
    assert location.getEntity(entity.getID()) is entity
    assert entity.getLocationID() == location.getID()


def test_adding_the_same_entity_twice_warns_and_keeps_one(capsys):
    location = Location(0, 0)
    entity = Entity("thing")
    location.addEntity(entity)
    location.addEntity(entity)
    assert location.getNumEntities() == 1
    assert "already present" in capsys.readouterr().out


def test_remove_entity_takes_it_out():
    location = Location(0, 0)
    entity = Entity("thing")
    location.addEntity(entity)
    location.removeEntity(entity)
    assert not location.isEntityPresent(entity)
    assert location.getNumEntities() == 0


def test_removing_an_absent_entity_warns_and_changes_nothing(capsys):
    location = Location(0, 0)
    present = Entity("present")
    location.addEntity(present)
    location.removeEntity(Entity("absent"))
    assert location.getNumEntities() == 1
    assert "was not present when attempting to remove" in capsys.readouterr().out


def test_get_entity_for_an_unknown_id_warns_and_returns_none(capsys):
    location = Location(0, 0)
    assert location.getEntity(Entity("absent").getID()) is None
    assert "was not present when attempting to retrieve" in capsys.readouterr().out
