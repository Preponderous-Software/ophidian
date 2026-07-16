import json
import os
from datetime import datetime, timezone

# @author Daniel McCoy Stephenson
# @since July 4th, 2026

SAVE_VERSION = 1
DEFAULT_SAVE_PATH = os.path.join(os.getcwd(), "save.json")


def defaultSaveData():
    return {
        "version": SAVE_VERSION,
        "ophidianName": None,
        "currency": 0,
        "ascensionLevel": 0,
        "selectedCosmetic": "default",
        "unlockedCosmetics": ["default"],
        "purchasedUpgrades": [],
        "lifetimeStats": {
            "totalRuns": 0,
            "totalFoodEaten": 0,
            "totalTicksSurvived": 0,
            "longestLength": 0,
            "highestLevelReached": 1,
            "highestScore": 0,
        },
        "obituaries": [],
    }


# Registry of migration functions, keyed by the version they upgrade FROM.
# Each function takes a loaded save dict and returns it upgraded to
# (fromVersion + 1). Empty today since SAVE_VERSION has never changed - this
# is the seam a future schema change hooks into, rather than needing to
# retrofit migration handling into SaveManager._load() at that point.
MIGRATIONS = {}


def migrateSaveData(data):
    """Upgrades a loaded save dict to SAVE_VERSION by chaining any
    registered MIGRATIONS, then stamps the current version onto it."""
    version = data.get("version", SAVE_VERSION)
    while version in MIGRATIONS:
        data = MIGRATIONS[version](data)
        version += 1
    data["version"] = SAVE_VERSION
    return data


class SaveManager:
    """Loads, holds, and persists the player's cross-run progression state."""

    def __init__(self, path=None):
        self.path = path or DEFAULT_SAVE_PATH
        self.data = self._load()

    def _load(self):
        data = defaultSaveData()
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    loaded = migrateSaveData(loaded)
                    data.update(loaded)
                    # keep nested defaults for any keys a stale save is missing
                    stats = defaultSaveData()["lifetimeStats"]
                    stats.update(loaded.get("lifetimeStats", {}))
                    data["lifetimeStats"] = stats
            except (json.JSONDecodeError, OSError):
                pass
        return data

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def recordRun(self, *, length, level, ticks, score, causeOfDeath):
        """Folds a finished run into lifetime stats and appends an obituary entry."""
        stats = self.data["lifetimeStats"]
        stats["totalRuns"] += 1
        stats["totalFoodEaten"] += max(0, length - 1)
        stats["totalTicksSurvived"] += ticks
        stats["longestLength"] = max(stats["longestLength"], length)
        stats["highestLevelReached"] = max(stats["highestLevelReached"], level)
        stats["highestScore"] = max(stats["highestScore"], score)

        obituary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "name": self.data.get("ophidianName") or "Unnamed Ophidian",
            "length": length,
            "level": level,
            "ticksSurvived": ticks,
            "score": score,
            "causeOfDeath": causeOfDeath,
        }
        self.data["obituaries"].append(obituary)
        self.save()
        return obituary
