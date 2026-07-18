from level.level import Level


def test_level_stores_name_and_size():
    level = Level("Level 1", 5)
    assert level.name == "Level 1"
    assert level.size == 5


def test_level_creates_environment_with_matching_name_and_grid_size():
    level = Level("Level 1", 5)
    assert level.environment.getName() == "Level 1"
    assert level.environment.getGrid().getRows() == 5
    assert level.environment.getGrid().getColumns() == 5
