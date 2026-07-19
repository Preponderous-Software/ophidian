from textui.textrenderer import TextRenderer

from food.food import Food, FOOD_TYPE_GROWTH, FOOD_TYPE_SPEED
from ophidian import Ophidian


def _makeGame(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True)


def _clearFoodFromGrid(game):
    grid = game.environment.getGrid()
    for locationId in grid.getLocations():
        location = grid.getLocation(locationId)
        for entityId in list(location.getEntities().keys()):
            entity = location.getEntity(entityId)
            if isinstance(entity, Food):
                location.removeEntity(entity)


def _placeFoodInFrontOfHead(game, foodType):
    # the head spawns at a random grid location, which may be on an edge
    # (missing an "up" neighbor) - move it to the center so direction 0
    # (the default heading) always has somewhere to go
    grid = game.environment.getGrid()
    centerX, centerY = grid.getRows() // 2, grid.getColumns() // 2
    centerLocation = grid.getLocationByCoordinates(centerX, centerY)
    game.environment.removeEntity(game.selectedSnakePart)
    game.environment.addEntityToLocation(game.selectedSnakePart, centerLocation)

    targetLocation = grid.getUp(centerLocation)
    color = game.config.red if foodType == FOOD_TYPE_GROWTH else game.config.blue
    food = Food(color, foodType)
    game.environment.addEntityToLocation(food, targetLocation)
    return food


def test_eating_growth_food_grows_the_snake_and_does_not_start_a_boost(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    _clearFoodFromGrid(game)
    _placeFoodInFrontOfHead(game, FOOD_TYPE_GROWTH)
    startingLength = len(game.snakeParts)

    game.moveEntity(game.selectedSnakePart, 0)

    assert len(game.snakeParts) == startingLength + 1
    assert game.speedBoostActive is False


def test_eating_speed_food_starts_a_boost_and_does_not_grow_the_snake(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    _clearFoodFromGrid(game)
    _placeFoodInFrontOfHead(game, FOOD_TYPE_SPEED)
    startingLength = len(game.snakeParts)
    baseTickSpeed = game.config.tickSpeed

    game.moveEntity(game.selectedSnakePart, 0)

    assert len(game.snakeParts) == startingLength
    assert game.speedBoostActive is True
    assert game.config.tickSpeed == baseTickSpeed / game.config.speedBoostMultiplier


def test_speed_boost_reverts_to_base_tick_speed_once_its_duration_elapses(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    baseTickSpeed = game.config.tickSpeed

    game.activateSpeedBoost()
    assert game.config.tickSpeed == baseTickSpeed / game.config.speedBoostMultiplier

    monkeypatch.setattr("ophidian.time.time", lambda: game.speedBoostEndTime + 1)
    game.updateSpeedBoost()

    assert game.speedBoostActive is False
    assert game.config.tickSpeed == baseTickSpeed


def test_activating_speed_boost_twice_refreshes_timer_without_compounding(
    tmp_path, monkeypatch
):
    # regression: a second speed food eaten while a boost is already active
    # should extend the timer, not stack another halving on top of the
    # already-boosted tick speed
    game = _makeGame(monkeypatch, tmp_path)
    baseTickSpeed = game.config.tickSpeed

    game.activateSpeedBoost()
    firstEndTime = game.speedBoostEndTime
    game.activateSpeedBoost()

    assert game.config.tickSpeed == baseTickSpeed / game.config.speedBoostMultiplier
    assert game.speedBoostEndTime >= firstEndTime


def test_spawn_food_can_produce_both_growth_and_speed_types(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)

    monkeypatch.setattr("ophidian.random.random", lambda: 0.0)
    game.spawnFood()
    growthFood = [
        e
        for locId in game.environment.getGrid().getLocations()
        for e in game.environment.getGrid().getLocation(locId).getEntities().values()
        if isinstance(e, Food)
    ]
    assert any(f.getFoodType() == FOOD_TYPE_GROWTH for f in growthFood)

    _clearFoodFromGrid(game)
    monkeypatch.setattr("ophidian.random.random", lambda: 0.99)
    game.spawnFood()
    speedFood = [
        e
        for locId in game.environment.getGrid().getLocations()
        for e in game.environment.getGrid().getLocation(locId).getEntities().values()
        if isinstance(e, Food)
    ]
    assert any(f.getFoodType() == FOOD_TYPE_SPEED for f in speedFood)
