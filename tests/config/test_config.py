from config.config import Config


def test_default_grid_size_is_within_min_and_max():
    config = Config()
    assert config.minGridSize <= config.gridSize <= config.maxGridSize


def test_tick_speed_defaults_to_a_positive_limited_value():
    config = Config()
    assert config.limitTickSpeed is True
    assert config.tickSpeed > 0


def test_growth_food_spawn_rate_is_a_valid_probability():
    config = Config()
    assert 0 < config.growthFoodSpawnRate < 1
