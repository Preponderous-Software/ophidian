import datetime
import uuid

from lib.pyenvlib.entity import Entity


def test_new_entity_has_its_name_and_no_placement():
    entity = Entity("thing")
    assert entity.getName() == "thing"
    assert entity.getEnvironmentID() == -1
    assert entity.getGridID() == -1
    assert entity.getLocationID() == -1


def test_new_entity_gets_a_fresh_uuid():
    first = Entity("thing")
    second = Entity("thing")
    assert isinstance(first.getID(), uuid.UUID)
    assert first.getID() != second.getID()


def test_new_entity_is_stamped_with_the_time_it_was_made():
    before = datetime.datetime.now()
    entity = Entity("thing")
    after = datetime.datetime.now()
    assert before <= entity.getCreationDate() <= after


def test_setters_replace_each_field():
    entity = Entity("thing")
    created = datetime.datetime(2022, 7, 1, 12, 0)
    entity.setID("entity-id")
    entity.setName("renamed")
    entity.setEnvironmentID("environment-id")
    entity.setGridID("grid-id")
    entity.setLocationID("location-id")
    entity.setCreationDate(created)
    assert entity.getID() == "entity-id"
    assert entity.getName() == "renamed"
    assert entity.getEnvironmentID() == "environment-id"
    assert entity.getGridID() == "grid-id"
    assert entity.getLocationID() == "location-id"
    assert entity.getCreationDate() == created


def test_print_info_prints_the_name_and_every_id(capsys):
    entity = Entity("thing")
    entity.setID("entity-id")
    entity.setEnvironmentID("environment-id")
    entity.setGridID("grid-id")
    entity.setLocationID("location-id")
    entity.setCreationDate(datetime.datetime(2022, 7, 1, 12, 0))
    entity.printInfo()
    out = capsys.readouterr().out
    assert "thing" in out
    assert "ID:  entity-id" in out
    assert "Creation Date:  2022-07-01 12:00:00" in out
    assert "Environment ID:  environment-id" in out
    assert "Grid ID:  grid-id" in out
    assert "Location ID:  location-id" in out
