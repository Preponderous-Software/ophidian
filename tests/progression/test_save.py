import json
import os

import pytest

from progression.cosmetics import checkForNewUnlocks, getUnlockedSkinIds
from progression.save import SAVE_VERSION, SaveManager, defaultSaveData, migrateSaveData
from reporting.usage import defaultUsageReportingSettings


def test_new_save_uses_defaults(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    manager = SaveManager(path)
    assert manager.data == defaultSaveData()


def test_record_run_updates_lifetime_stats_and_persists(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    manager = SaveManager(path)

    manager.recordRun(length=5, level=2, ticks=100, score=50, causeOfDeath="collision")

    stats = manager.data["lifetimeStats"]
    assert stats["totalRuns"] == 1
    assert stats["totalFoodEaten"] == 4
    assert stats["totalTicksSurvived"] == 100
    assert stats["longestLength"] == 5
    assert stats["highestLevelReached"] == 2
    assert stats["highestScore"] == 50
    assert len(manager.data["obituaries"]) == 1
    assert manager.data["obituaries"][0]["causeOfDeath"] == "collision"

    with open(path) as f:
        onDisk = json.load(f)
    assert onDisk["lifetimeStats"]["totalRuns"] == 1


def test_record_run_tracks_bests_across_multiple_runs(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    manager = SaveManager(path)

    manager.recordRun(length=3, level=1, ticks=20, score=10, causeOfDeath="collision")
    manager.recordRun(length=8, level=3, ticks=200, score=90, causeOfDeath="quit")

    stats = manager.data["lifetimeStats"]
    assert stats["totalRuns"] == 2
    assert stats["longestLength"] == 8
    assert stats["highestLevelReached"] == 3
    assert stats["highestScore"] == 90
    assert len(manager.data["obituaries"]) == 2


def test_reload_restores_persisted_state(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    first = SaveManager(path)
    first.recordRun(length=4, level=1, ticks=30, score=12, causeOfDeath="collision")

    second = SaveManager(path)
    assert second.data["lifetimeStats"]["totalRuns"] == 1
    assert len(second.data["obituaries"]) == 1


def test_missing_save_file_is_recreated_with_defaults(tmp_path):
    path = os.path.join(tmp_path, "nested", "save.json")
    manager = SaveManager(path)
    assert manager.data["currency"] == 0
    assert not os.path.exists(path)  # not written until save() is called


def test_migrate_save_data_stamps_current_version_when_missing():
    data = migrateSaveData({"currency": 5})
    assert data["version"] == SAVE_VERSION
    assert data["currency"] == 5


def test_migrate_save_data_applies_registered_migrations_in_order(monkeypatch):
    from progression import save as saveModule

    calls = []

    def upgradeFromVersionOne(data):
        calls.append(1)
        data["migratedFromV1"] = True
        return data

    monkeypatch.setattr(saveModule, "SAVE_VERSION", 2)
    monkeypatch.setattr(saveModule, "MIGRATIONS", {1: upgradeFromVersionOne})

    result = saveModule.migrateSaveData({"version": 1, "currency": 5})

    assert calls == [1]
    assert result["migratedFromV1"] is True
    assert result["version"] == 2


def test_save_manager_stamps_version_on_a_save_file_missing_it(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    with open(path, "w") as f:
        json.dump({"currency": 7}, f)

    manager = SaveManager(path)

    assert manager.data["version"] == SAVE_VERSION
    assert manager.data["currency"] == 7


def test_new_save_carries_the_usage_reporting_block_and_owes_the_notice(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    manager = SaveManager(path)

    assert manager.data["usageReporting"] == defaultUsageReportingSettings()
    assert manager.usageReportingNoticeDue is True

    manager.save()
    assert SaveManager(path).usageReportingNoticeDue is False


def test_save_predating_usage_reporting_gets_the_defaults_and_owes_the_notice(
    tmp_path,
):
    path = os.path.join(tmp_path, "save.json")
    old = defaultSaveData()
    del old["usageReporting"]
    with open(path, "w") as f:
        json.dump(old, f)

    manager = SaveManager(path)

    assert manager.data["usageReporting"] == defaultUsageReportingSettings()
    assert manager.usageReportingNoticeDue is True


def test_opt_out_survives_reload_and_keeps_the_default_endpoint_and_key(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    manager = SaveManager(path)
    manager.data["usageReporting"] = {"enabled": False}
    manager.save()

    reloaded = SaveManager(path)

    assert reloaded.usageReportingNoticeDue is False
    assert reloaded.data["usageReporting"]["enabled"] is False
    assert (
        reloaded.data["usageReporting"]["endpoint"]
        == defaultUsageReportingSettings()["endpoint"]
    )
    assert (
        reloaded.data["usageReporting"]["key"] == defaultUsageReportingSettings()["key"]
    )


def test_corrupt_save_file_falls_back_to_defaults_and_owes_the_notice(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    with open(path, "w") as f:
        f.write('{"currency": 40, ')

    manager = SaveManager(path)

    assert manager.data == defaultSaveData()
    assert manager.usageReportingNoticeDue is True


def test_corrupt_save_file_is_overwritten_by_the_next_save(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    with open(path, "w") as f:
        f.write("not json")

    manager = SaveManager(path)
    manager.data["currency"] = 3
    manager.save()

    with open(path) as f:
        assert json.load(f)["currency"] == 3


def test_save_file_holding_a_non_object_is_ignored(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    with open(path, "w") as f:
        json.dump([{"currency": 40}], f)

    manager = SaveManager(path)

    assert manager.data == defaultSaveData()
    assert manager.usageReportingNoticeDue is True


def test_unreadable_save_path_falls_back_to_defaults(tmp_path):
    # a directory at the save path exists but cannot be opened as a file,
    # which raises an OSError rather than a JSON error
    path = os.path.join(tmp_path, "save.json")
    os.mkdir(path)

    manager = SaveManager(path)

    assert manager.data == defaultSaveData()


def test_stale_lifetime_stats_keep_their_values_and_gain_missing_keys(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    old = defaultSaveData()
    old["lifetimeStats"] = {"totalRuns": 9, "highestScore": 120}
    with open(path, "w") as f:
        json.dump(old, f)

    stats = SaveManager(path).data["lifetimeStats"]

    assert stats["totalRuns"] == 9
    assert stats["highestScore"] == 120
    assert stats["totalFoodEaten"] == 0
    assert stats["highestLevelReached"] == 1
    assert set(stats) == set(defaultSaveData()["lifetimeStats"])


def _writeSaveWith(path, **fields):
    saved = defaultSaveData()
    saved.update(fields)
    with open(path, "w") as f:
        json.dump(saved, f)


def test_save_file_that_is_not_utf8_falls_back_to_defaults(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    with open(path, "wb") as f:
        f.write(b"\xff\xfe\x00\x81")

    manager = SaveManager(path)

    assert manager.data == defaultSaveData()
    assert manager.usageReportingNoticeDue is True


@pytest.mark.parametrize(
    "field, value",
    [
        ("lifetimeStats", None),
        ("lifetimeStats", 5),
        ("purchasedUpgrades", None),
        ("ascensionLevel", "3"),
        ("ascensionLevel", None),
        ("ascensionLevel", True),
        ("ascensionLevel", 1.5),
        ("obituaries", None),
        ("currency", "lots"),
        ("unlockedCosmetics", None),
        ("selectedCosmetic", None),
        ("ophidianName", 5),
    ],
)
def test_wrong_typed_field_resets_alone(tmp_path, field, value):
    path = os.path.join(tmp_path, "save.json")
    _writeSaveWith(path, **{"purchasedUpgrades": ["head_start"], field: value})
    expected = defaultSaveData()
    if field != "purchasedUpgrades":
        expected["purchasedUpgrades"] = ["head_start"]

    assert SaveManager(path).data == expected


def test_wrong_typed_field_keeps_the_rest_of_the_save(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    _writeSaveWith(path, currency="lots", ascensionLevel=4, ophidianName="Ada")

    data = SaveManager(path).data

    assert data["currency"] == 0
    assert data["ascensionLevel"] == 4
    assert data["ophidianName"] == "Ada"


@pytest.mark.parametrize("value", ["12", None, False, [1]])
def test_wrong_typed_lifetime_stat_resets_alone(tmp_path, value):
    path = os.path.join(tmp_path, "save.json")
    _writeSaveWith(path, lifetimeStats={"totalRuns": 9, "highestScore": value})

    stats = SaveManager(path).data["lifetimeStats"]

    assert stats["totalRuns"] == 9
    assert stats["highestScore"] == 0


@pytest.mark.parametrize("field", ["purchasedUpgrades", "unlockedCosmetics"])
def test_non_string_ids_are_dropped_from_id_lists(tmp_path, field):
    path = os.path.join(tmp_path, "save.json")
    _writeSaveWith(path, **{field: ["default", 5, None, ["x"]]})

    assert SaveManager(path).data[field] == ["default"]


@pytest.mark.parametrize("version", ["1", None, [1], {"major": 1}])
def test_wrong_typed_version_is_stamped_with_the_current_one(tmp_path, version):
    path = os.path.join(tmp_path, "save.json")
    _writeSaveWith(path, version=version, currency=7)

    manager = SaveManager(path)

    assert manager.data["version"] == SAVE_VERSION
    assert manager.data["currency"] == 7


def test_fields_from_a_newer_version_survive_a_load(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    _writeSaveWith(path, fieldFromTheFuture={"kept": True})

    assert SaveManager(path).data["fieldFromTheFuture"] == {"kept": True}


def test_named_ophidian_survives_a_load(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    _writeSaveWith(path, ophidianName="Ada")

    assert SaveManager(path).data["ophidianName"] == "Ada"


def test_wrong_typed_usage_reporting_still_clears_the_notice(tmp_path):
    # the block's own type check reads it as off, so the type filter must not
    # make a present-but-wrong value look like an absent one
    path = os.path.join(tmp_path, "save.json")
    _writeSaveWith(path, usageReporting="off", currency=7)

    manager = SaveManager(path)

    assert manager.usageReportingNoticeDue is False
    assert manager.data["usageReporting"]["enabled"] is False
    assert manager.data["currency"] == 7


@pytest.mark.parametrize(
    "fields",
    [
        {"lifetimeStats": None},
        {"lifetimeStats": {"highestScore": None, "longestLength": "3"}},
        {"obituaries": None},
        {"currency": "lots"},
        {"unlockedCosmetics": None},
        {"unlockedCosmetics": [5]},
        {"purchasedUpgrades": None},
    ],
)
def test_a_run_can_be_recorded_on_a_repaired_save(tmp_path, fields):
    path = os.path.join(tmp_path, "save.json")
    _writeSaveWith(path, **fields)

    manager = SaveManager(path)
    manager.recordRun(length=5, level=2, ticks=100, score=50, causeOfDeath="collision")

    checkForNewUnlocks(manager.data)
    assert getUnlockedSkinIds(manager.data) == ["default"]
    assert manager.data["lifetimeStats"]["totalRuns"] == 1
    assert len(manager.data["obituaries"]) == 1


@pytest.mark.parametrize("value", [False, None, "off", 0, []])
def test_non_object_usage_reporting_reads_as_off(tmp_path, value):
    path = os.path.join(tmp_path, "save.json")
    old = defaultSaveData()
    old["usageReporting"] = value
    with open(path, "w") as f:
        json.dump(old, f)

    manager = SaveManager(path)

    expected = defaultUsageReportingSettings()
    expected["enabled"] = False
    assert manager.data["usageReporting"] == expected
    # the key was present, so the save is treated as having seen the notice
    assert manager.usageReportingNoticeDue is False
