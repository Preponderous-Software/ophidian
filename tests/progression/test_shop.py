import pytest

from progression.save import defaultSaveData
from progression.shop import (
    UPGRADES,
    currencyEarnedForRun,
    getActiveUpgradeLabels,
    listUpgrades,
    purchaseUpgrade,
)


@pytest.mark.parametrize(
    "length,expected",
    [
        (0, 0),
        (1, 0),
        (2, 1),
        (5, 4),
        (10, 9),
    ],
)
def test_currency_earned_for_run(length, expected):
    assert currencyEarnedForRun(length) == expected


def test_upgrade_registry_has_exactly_three_upgrades_with_positive_costs():
    upgrades = listUpgrades()
    assert len(upgrades) == 3

    expectedIds = {"head_start", "slow_starter", "second_wind"}
    actualIds = {upgrade["id"] for upgrade in upgrades}
    assert actualIds == expectedIds

    for upgrade in upgrades:
        assert isinstance(upgrade["cost"], int)
        assert upgrade["cost"] > 0
        assert upgrade["name"]
        assert upgrade["description"]


def test_purchase_upgrade_success_deducts_cost_and_records_ownership():
    saveData = defaultSaveData()
    saveData["currency"] = 20

    success, message = purchaseUpgrade(saveData, "head_start")

    assert success is True
    assert saveData["currency"] == 20 - UPGRADES["head_start"]["cost"]
    assert "head_start" in saveData["purchasedUpgrades"]
    assert "Purchased" in message


def test_purchase_upgrade_fails_on_insufficient_funds_without_mutation():
    saveData = defaultSaveData()
    saveData["currency"] = 1

    success, message = purchaseUpgrade(saveData, "second_wind")

    assert success is False
    assert saveData["currency"] == 1
    assert saveData["purchasedUpgrades"] == []
    assert "Not enough currency" in message


def test_purchase_upgrade_fails_on_already_owned_without_double_charge():
    saveData = defaultSaveData()
    saveData["currency"] = 100
    saveData["purchasedUpgrades"] = ["slow_starter"]

    success, message = purchaseUpgrade(saveData, "slow_starter")

    assert success is False
    assert saveData["currency"] == 100
    assert saveData["purchasedUpgrades"] == ["slow_starter"]
    assert "already owned" in message


def test_purchase_upgrade_fails_on_unknown_upgrade():
    saveData = defaultSaveData()
    saveData["currency"] = 100

    success, message = purchaseUpgrade(saveData, "does_not_exist")

    assert success is False
    assert saveData["currency"] == 100
    assert "Unknown upgrade" in message


def test_get_active_upgrade_labels_empty_when_nothing_purchased():
    saveData = defaultSaveData()
    assert getActiveUpgradeLabels(saveData, secondWindAvailableThisRun=True) == []


def test_get_active_upgrade_labels_lists_owned_upgrades_in_display_order():
    saveData = defaultSaveData()
    saveData["purchasedUpgrades"] = ["slow_starter", "head_start"]

    labels = getActiveUpgradeLabels(saveData, secondWindAvailableThisRun=True)

    assert labels == ["Head Start", "Slow Starter"]


def test_get_active_upgrade_labels_shows_second_wind_armed_state():
    saveData = defaultSaveData()
    saveData["purchasedUpgrades"] = ["second_wind"]

    armed = getActiveUpgradeLabels(saveData, secondWindAvailableThisRun=True)
    used = getActiveUpgradeLabels(saveData, secondWindAvailableThisRun=False)

    assert armed == ["Second Wind (armed)"]
    assert used == ["Second Wind (used)"]
