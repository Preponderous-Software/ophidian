import pytest

from textui.textrenderer import TextRenderer

from food.food import Food, FOOD_TYPE_GROWTH
from ophidian import Ophidian
from powerup.powerup import (
    PowerUp,
    PowerUpType,
    getPowerUpDefinition,
    getPowerUpDurationSeconds,
)
from scoring.scoring import pointsForFood
from snake.snakePart import SnakePart


def _makeGame(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True)


def _clearPickupsFromGrid(game):
    grid = game.environment.getGrid()
    for locationId in grid.getLocations():
        location = grid.getLocation(locationId)
        for entityId in list(location.getEntities().keys()):
            entity = location.getEntity(entityId)
            if isinstance(entity, (Food, PowerUp)):
                location.removeEntity(entity)


def _centerHead(game):
    # the head spawns at a random grid location, which may be on an edge
    # (missing an "up" neighbor) - move it to the center so direction 0
    # (the default heading) always has somewhere to go
    grid = game.environment.getGrid()
    centerX, centerY = grid.getRows() // 2, grid.getColumns() // 2
    centerLocation = grid.getLocationByCoordinates(centerX, centerY)
    game.environment.removeEntity(game.selectedSnakePart)
    game.environment.addEntityToLocation(game.selectedSnakePart, centerLocation)
    return centerLocation


def _placeInFrontOfHead(game, entity):
    grid = game.environment.getGrid()
    targetLocation = grid.getUp(_centerHead(game))
    game.environment.addEntityToLocation(entity, targetLocation)
    return entity


def test_eating_growth_food_grows_the_snake_and_starts_no_power_up(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    _placeInFrontOfHead(game, Food(game.config.red, FOOD_TYPE_GROWTH))
    startingLength = len(game.snakeParts)

    game.moveEntity(game.selectedSnakePart, 0)

    assert len(game.snakeParts) == startingLength + 1
    assert game.getActivePowerUpStatuses() == []


def test_collecting_a_speed_power_up_boosts_speed_and_does_not_grow_the_snake(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    _placeInFrontOfHead(game, PowerUp(PowerUpType.SPEED))
    startingLength = len(game.snakeParts)
    baseTickSpeed = game.config.tickSpeed
    multiplier = getPowerUpDefinition(PowerUpType.SPEED)["tickSpeedMultiplier"]

    game.moveEntity(game.selectedSnakePart, 0)

    assert len(game.snakeParts) == startingLength
    assert game.activePowerUps.isActive(PowerUpType.SPEED) is True
    assert game.config.tickSpeed == baseTickSpeed / multiplier


def test_collecting_a_score_multiplier_power_up_starts_it_without_growing(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    _placeInFrontOfHead(game, PowerUp(PowerUpType.SCORE_MULTIPLIER))
    startingLength = len(game.snakeParts)
    startingScore = game.score
    baseTickSpeed = game.config.tickSpeed

    game.moveEntity(game.selectedSnakePart, 0)

    assert len(game.snakeParts) == startingLength
    assert game.activePowerUps.isActive(PowerUpType.SCORE_MULTIPLIER) is True
    # collecting it is not itself worth points, and it must not touch speed
    assert game.score == startingScore
    assert game.config.tickSpeed == baseTickSpeed


def test_active_score_multiplier_is_neutral_when_nothing_is_running(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)

    assert game.getActiveScoreMultiplier() == 1.0


def test_a_speed_boost_alone_does_not_multiply_the_score(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)

    game.activatePowerUp(PowerUpType.SPEED)

    assert game.getActiveScoreMultiplier() == 1.0


def test_food_eaten_while_the_multiplier_runs_is_worth_double(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    numLocations = len(game.environment.grid.getLocations())
    game.snakeParts = [game.selectedSnakePart] * 4
    game.score = 0

    game.activatePowerUp(PowerUpType.SCORE_MULTIPLIER)
    game.awardPointsForFood()

    assert game.getActiveScoreMultiplier() == 2.0
    assert game.score == 2 * pointsForFood(4, numLocations)


def test_points_earned_before_the_multiplier_are_not_retroactively_doubled(
    tmp_path, monkeypatch
):
    # the whole reason the score is banked per pickup (issue #73): scaling a
    # recomputed total would rewrite everything already earned
    game = _makeGame(monkeypatch, tmp_path)
    numLocations = len(game.environment.grid.getLocations())
    game.snakeParts = [game.selectedSnakePart] * 4
    game.score = 0

    game.awardPointsForFood()
    game.activatePowerUp(PowerUpType.SCORE_MULTIPLIER)
    game.awardPointsForFood()

    expected = pointsForFood(4, numLocations) * 3
    assert game.score == expected


def test_points_return_to_normal_once_the_multiplier_expires(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    numLocations = len(game.environment.grid.getLocations())
    game.snakeParts = [game.selectedSnakePart] * 4
    game.score = 0

    game.activatePowerUp(PowerUpType.SCORE_MULTIPLIER)
    game.awardPointsForFood()
    scoreWhileDoubled = game.score

    endTime = game.activePowerUps.expiresAt[PowerUpType.SCORE_MULTIPLIER]
    monkeypatch.setattr("powerup.active.time.time", lambda: endTime + 1)
    game.updatePowerUps()
    game.awardPointsForFood()

    assert game.activePowerUps.isActive(PowerUpType.SCORE_MULTIPLIER) is False
    assert game.getActiveScoreMultiplier() == 1.0
    # the doubled award is kept; only the new one is back to normal
    assert game.score == scoreWhileDoubled + pointsForFood(4, numLocations)


def test_the_running_multiplier_is_listed_on_both_huds(tmp_path, monkeypatch):
    # getActivePowerUpStatuses is what drawHud and TextRenderer.renderHud
    # both read, so this is the shared "clearly see which power-ups are
    # active" path
    game = _makeGame(monkeypatch, tmp_path)

    game.activatePowerUp(PowerUpType.SCORE_MULTIPLIER)
    endTime = game.activePowerUps.expiresAt[PowerUpType.SCORE_MULTIPLIER]
    monkeypatch.setattr("powerup.active.time.time", lambda: endTime - 4)

    (status,) = game.getActivePowerUpStatuses()
    assert status["label"] == "Double points"
    assert status["secondsRemaining"] == 4


def test_collecting_an_invincibility_power_up_starts_it(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    _placeInFrontOfHead(game, PowerUp(PowerUpType.INVINCIBILITY))
    startingLength = len(game.snakeParts)
    baseTickSpeed = game.config.tickSpeed

    game.moveEntity(game.selectedSnakePart, 0)

    assert len(game.snakeParts) == startingLength
    assert game.activePowerUps.isActive(PowerUpType.INVINCIBILITY) is True
    # invincibility must not touch the tick speed
    assert game.config.tickSpeed == baseTickSpeed


def test_speed_boost_reverts_to_base_tick_speed_once_its_duration_elapses(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    baseTickSpeed = game.config.tickSpeed

    game.activatePowerUp(PowerUpType.SPEED)
    assert game.config.tickSpeed < baseTickSpeed

    endTime = game.activePowerUps.expiresAt[PowerUpType.SPEED]
    monkeypatch.setattr("powerup.active.time.time", lambda: endTime + 1)
    game.updatePowerUps()

    assert game.activePowerUps.isActive(PowerUpType.SPEED) is False
    assert game.config.tickSpeed == baseTickSpeed


def test_expiring_a_power_up_notifies_the_player(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    game.activatePowerUp(PowerUpType.SPEED)
    game.uiBanner.queue.clear()

    endTime = game.activePowerUps.expiresAt[PowerUpType.SPEED]
    monkeypatch.setattr("powerup.active.time.time", lambda: endTime + 1)
    game.updatePowerUps()

    assert game.uiBanner.queue == [
        getPowerUpDefinition(PowerUpType.SPEED)["expiryMessage"]
    ]


def test_activating_a_power_up_twice_refreshes_timer_without_compounding(
    tmp_path, monkeypatch
):
    # regression: a second speed power-up collected while one is already
    # active should extend the timer, not stack another halving on top of
    # the already-boosted tick speed
    game = _makeGame(monkeypatch, tmp_path)
    baseTickSpeed = game.config.tickSpeed
    multiplier = getPowerUpDefinition(PowerUpType.SPEED)["tickSpeedMultiplier"]

    game.activatePowerUp(PowerUpType.SPEED)
    firstEndTime = game.activePowerUps.expiresAt[PowerUpType.SPEED]
    game.activatePowerUp(PowerUpType.SPEED)

    assert game.config.tickSpeed == baseTickSpeed / multiplier
    assert game.activePowerUps.expiresAt[PowerUpType.SPEED] >= firstEndTime


def test_active_power_up_statuses_are_empty_when_none_are_running(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)

    assert game.getActivePowerUpStatuses() == []


def test_active_power_up_statuses_count_down_while_running(tmp_path, monkeypatch):
    # a power-up's activation banner expires after 2s while the power-up
    # itself can last longer, so both HUDs need the remaining time (#114)
    game = _makeGame(monkeypatch, tmp_path)

    game.activatePowerUp(PowerUpType.SPEED)
    endTime = game.activePowerUps.expiresAt[PowerUpType.SPEED]
    monkeypatch.setattr("powerup.active.time.time", lambda: endTime - 3)

    (status,) = game.getActivePowerUpStatuses()
    assert status["label"] == "Speed boost"
    assert status["secondsRemaining"] == 3


def test_active_power_up_statuses_identify_the_type_by_symbol_and_color(
    tmp_path, monkeypatch
):
    # the symbol and color a power-up was collected in on the grid, so an
    # indicator is recognizable as that power-up (issue #72)
    game = _makeGame(monkeypatch, tmp_path)

    game.activatePowerUp(PowerUpType.SPEED)

    (status,) = game.getActivePowerUpStatuses()
    definition = getPowerUpDefinition(PowerUpType.SPEED)
    assert status["symbol"] == definition["textSymbol"]
    assert status["color"] == definition["color"]


def test_active_power_up_statuses_report_the_fraction_of_duration_left(
    tmp_path, monkeypatch
):
    # what drives the duration meters both HUDs draw: it falls continuously
    # between whole seconds, so an expiring power-up drains smoothly
    game = _makeGame(monkeypatch, tmp_path)
    duration = getPowerUpDurationSeconds(PowerUpType.SPEED)

    game.activatePowerUp(PowerUpType.SPEED)
    endTime = game.activePowerUps.expiresAt[PowerUpType.SPEED]
    monkeypatch.setattr("powerup.active.time.time", lambda: endTime - duration / 4)

    (status,) = game.getActivePowerUpStatuses()
    assert status["durationSeconds"] == duration
    assert status["fractionRemaining"] == pytest.approx(0.25)


def test_refreshing_a_power_up_returns_its_meter_to_full(tmp_path, monkeypatch):
    # collecting one that is already running extends the timer to a full
    # duration, so the fraction must go back to 1 rather than past it
    game = _makeGame(monkeypatch, tmp_path)
    duration = getPowerUpDurationSeconds(PowerUpType.SPEED)

    game.activatePowerUp(PowerUpType.SPEED)
    endTime = game.activePowerUps.expiresAt[PowerUpType.SPEED]
    monkeypatch.setattr("powerup.active.time.time", lambda: endTime - duration / 4)
    game.activatePowerUp(PowerUpType.SPEED)

    (status,) = game.getActivePowerUpStatuses()
    assert status["fractionRemaining"] == 1.0


def test_active_power_up_statuses_omit_one_with_no_time_left(tmp_path, monkeypatch):
    # updatePowerUps() clears it on the next tick, so it stays readable for
    # one frame - neither HUD should advertise "Speed boost: 0s"
    game = _makeGame(monkeypatch, tmp_path)

    game.activatePowerUp(PowerUpType.SPEED)
    endTime = game.activePowerUps.expiresAt[PowerUpType.SPEED]
    monkeypatch.setattr("powerup.active.time.time", lambda: endTime + 5)

    assert game.getActivePowerUpStatuses() == []


def test_starting_a_new_run_clears_active_power_ups(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    baseTickSpeed = game.config.tickSpeed
    game.activatePowerUp(PowerUpType.SPEED)

    game.initialize()

    assert game.getActivePowerUpStatuses() == []
    assert game.config.tickSpeed == baseTickSpeed


def test_invincibility_survives_a_collision_with_the_snakes_own_body(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    centerLocation = _centerHead(game)
    grid = game.environment.getGrid()
    body = SnakePart((0, 0, 0))
    game.environment.addEntityToLocation(body, grid.getUp(centerLocation))
    game.secondWindAvailableThisRun = True
    game.activatePowerUp(PowerUpType.INVINCIBILITY)

    game.moveEntity(game.selectedSnakePart, 0)

    assert game.collision is False
    assert game.running is True
    # the move is dropped rather than overlapping the body...
    assert game.getLocation(game.selectedSnakePart) is centerLocation
    # ...and the paid-for second_wind upgrade is left intact for later
    assert game.secondWindAvailableThisRun is True


def test_collision_still_ends_the_run_once_invincibility_expires(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    game.config.restartUponCollision = False
    _clearPickupsFromGrid(game)
    centerLocation = _centerHead(game)
    grid = game.environment.getGrid()
    game.environment.addEntityToLocation(
        SnakePart((0, 0, 0)), grid.getUp(centerLocation)
    )
    game.secondWindAvailableThisRun = False
    game.activatePowerUp(PowerUpType.INVINCIBILITY)
    endTime = game.activePowerUps.expiresAt[PowerUpType.INVINCIBILITY]
    monkeypatch.setattr("powerup.active.time.time", lambda: endTime + 1)
    monkeypatch.setattr("ophidian.time.sleep", lambda seconds: None)

    game.updatePowerUps()
    game.moveEntity(game.selectedSnakePart, 0)

    assert game.collision is True
    assert game.running is False


def _pickupLocations(game):
    grid = game.environment.getGrid()
    return [
        grid.getLocation(locationId)
        for locationId in grid.getLocations()
        if any(
            isinstance(entity, (Food, PowerUp))
            for entity in grid.getLocation(locationId).getEntities().values()
        )
    ]


def test_spawn_pickup_lands_on_the_only_empty_location(tmp_path, monkeypatch):
    # regression test: spawning searched for an empty location and then
    # discarded it, handing placement to Environment.addEntity()'s
    # independent random draw - so a pickup routinely landed under a snake
    # part, on a cell that kills the player instead of rewarding them
    # (see issue #109)
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    grid = game.environment.getGrid()

    headLocation = game.getLocation(game.selectedSnakePart)
    emptyLocation = None
    for locationId in grid.getLocations():
        location = grid.getLocation(locationId)
        if location is headLocation:
            continue
        if emptyLocation is None:
            emptyLocation = location
            continue
        game.environment.addEntityToLocation(SnakePart((0, 0, 0)), location)

    game.spawnPickup()

    assert _pickupLocations(game) == [emptyLocation]


def test_spawn_pickup_never_lands_on_an_occupied_location(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    grid = game.environment.getGrid()

    # leave a handful of empty cells so placement is still random, but
    # heavily weighted toward collisions if occupancy were ignored
    emptyBudget = 3
    for locationId in grid.getLocations():
        location = grid.getLocation(locationId)
        if location.getNumEntities() > 0:
            continue
        if emptyBudget > 0:
            emptyBudget -= 1
            continue
        game.environment.addEntityToLocation(SnakePart((0, 0, 0)), location)

    for _ in range(20):
        _clearPickupsFromGrid(game)
        game.spawnPickup()
        for location in _pickupLocations(game):
            assert location.getNumEntities() == 1


def test_spawn_pickup_still_places_something_when_the_grid_is_full(
    tmp_path, monkeypatch
):
    # a completely full grid has no legal cell left; spawning must fall back
    # rather than hang searching for one
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)
    grid = game.environment.getGrid()
    for locationId in grid.getLocations():
        location = grid.getLocation(locationId)
        if location.getNumEntities() == 0:
            game.environment.addEntityToLocation(SnakePart((0, 0, 0)), location)

    game.spawnPickup()

    assert len(_pickupLocations(game)) == 1


def _spawnedPickups(game):
    grid = game.environment.getGrid()
    return [
        entity
        for locationId in grid.getLocations()
        for entity in grid.getLocation(locationId).getEntities().values()
        if isinstance(entity, (Food, PowerUp))
    ]


def test_spawn_pickup_can_produce_both_food_and_power_ups(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    _clearPickupsFromGrid(game)

    monkeypatch.setattr("ophidian.random.random", lambda: 0.0)
    game.spawnPickup()
    assert [type(pickup) for pickup in _spawnedPickups(game)] == [Food]

    _clearPickupsFromGrid(game)
    monkeypatch.setattr("ophidian.random.random", lambda: 0.99)
    monkeypatch.setattr("ophidian.rollPowerUpType", lambda: PowerUpType.INVINCIBILITY)
    game.spawnPickup()
    assert [pickup.getPowerUpType() for pickup in _spawnedPickups(game)] == [
        PowerUpType.INVINCIBILITY
    ]
