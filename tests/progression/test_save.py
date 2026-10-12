import json
import os

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


def test_non_object_usage_reporting_is_replaced_by_the_defaults(tmp_path):
    path = os.path.join(tmp_path, "save.json")
    old = defaultSaveData()
    old["usageReporting"] = False
    with open(path, "w") as f:
        json.dump(old, f)

    manager = SaveManager(path)

    assert manager.data["usageReporting"] == defaultUsageReportingSettings()
    # the key was present, so the save is treated as having seen the notice
    assert manager.usageReportingNoticeDue is False
