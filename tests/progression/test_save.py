import json
import os

from progression.save import SAVE_VERSION, SaveManager, defaultSaveData, migrateSaveData


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
