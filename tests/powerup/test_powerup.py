import random

import pytest

from powerup.powerup import (
    POWER_UP_DEFINITIONS,
    POWER_UP_ORDER,
    PowerUp,
    PowerUpType,
    getPowerUpDefinition,
    getPowerUpDurationSeconds,
    getPowerUpHudLabel,
    getPowerUpName,
    listPowerUpTypes,
    rollPowerUpType,
)

REQUIRED_DEFINITION_KEYS = [
    "id",
    "name",
    "hudLabel",
    "activationMessage",
    "expiryMessage",
    "color",
    "textSymbol",
    "spawnWeight",
    "durationSeconds",
]


@pytest.mark.parametrize("powerUpType", list(PowerUpType))
def test_every_type_has_a_complete_definition(powerUpType):
    definition = POWER_UP_DEFINITIONS[powerUpType]
    for key in REQUIRED_DEFINITION_KEYS:
        assert key in definition, "{} is missing {}".format(powerUpType, key)
    assert definition["id"] == powerUpType
    assert definition["durationSeconds"] > 0
    assert definition["spawnWeight"] > 0
    assert len(definition["textSymbol"]) == 1


def test_power_up_order_covers_every_type_exactly_once():
    # the spawn roll and the HUD both walk this order, so a type missing
    # from it would silently never spawn
    assert sorted(POWER_UP_ORDER) == sorted(PowerUpType)
    assert len(POWER_UP_ORDER) == len(set(POWER_UP_ORDER))


def test_text_symbols_are_unique_and_do_not_collide_with_grid_glyphs():
    symbols = [definition["textSymbol"] for definition in POWER_UP_DEFINITIONS.values()]
    assert len(symbols) == len(set(symbols))
    # TextRenderer.renderGrid draws the snake, food and empty cells with these
    assert not set(symbols) & {"H", "S", "F", "."}


def test_definitions_can_be_looked_up_by_plain_string_id():
    # entities and save data carry the plain string, not the enum member
    assert getPowerUpDefinition("speed") is POWER_UP_DEFINITIONS[PowerUpType.SPEED]
    assert getPowerUpName("speed") == "Speed Boost"
    assert getPowerUpHudLabel("speed") == "Speed boost"
    assert getPowerUpDurationSeconds("invincibility") == 3.0


def test_unknown_power_up_id_is_rejected():
    with pytest.raises(ValueError):
        getPowerUpDefinition("not-a-power-up")


def test_list_power_up_types_returns_a_copy_in_display_order():
    types = listPowerUpTypes()
    assert types == POWER_UP_ORDER
    types.append("mutated")
    assert listPowerUpTypes() == POWER_UP_ORDER


def test_roll_weights_each_type_by_its_spawn_weight():
    recorded = {}

    class RecordingRng:
        def choices(self, population, weights):
            recorded["population"] = population
            recorded["weights"] = weights
            return [population[0]]

    assert rollPowerUpType(RecordingRng()) == POWER_UP_ORDER[0]
    assert recorded["population"] == listPowerUpTypes()
    assert recorded["weights"] == [
        POWER_UP_DEFINITIONS[powerUpType]["spawnWeight"]
        for powerUpType in listPowerUpTypes()
    ]


def test_invincibility_is_five_percent_of_pickups_at_the_default_food_rate():
    # issue #74 asks for a 5% spawn rate; power-ups are 20% of pickups
    # (1 - Config.growthFoodSpawnRate), so its weight must be a quarter of
    # the total
    totalWeight = sum(
        definition["spawnWeight"] for definition in POWER_UP_DEFINITIONS.values()
    )
    invincibilityShare = (
        POWER_UP_DEFINITIONS[PowerUpType.INVINCIBILITY]["spawnWeight"] / totalWeight
    )
    assert pytest.approx(0.05) == 0.2 * invincibilityShare


def test_roll_only_ever_returns_a_defined_type():
    rng = random.Random(1234)
    for _ in range(200):
        assert rollPowerUpType(rng) in POWER_UP_DEFINITIONS


def test_power_up_entity_exposes_its_type_and_presentation():
    powerUp = PowerUp(PowerUpType.SPEED)

    assert powerUp.getName() == "PowerUp"
    assert powerUp.getPowerUpType() == PowerUpType.SPEED
    assert powerUp.getDisplayName() == "Speed Boost"
    assert powerUp.getColor() == POWER_UP_DEFINITIONS[PowerUpType.SPEED]["color"]
    assert (
        powerUp.getTextSymbol() == POWER_UP_DEFINITIONS[PowerUpType.SPEED]["textSymbol"]
    )


def test_power_up_entity_accepts_a_plain_string_type():
    powerUp = PowerUp("invincibility")

    assert powerUp.getPowerUpType() is PowerUpType.INVINCIBILITY
    assert powerUp.getPowerUpType() == "invincibility"


def test_power_up_entity_rejects_an_unknown_type():
    with pytest.raises(ValueError):
        PowerUp("not-a-power-up")
