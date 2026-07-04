from progression.save import defaultSaveData

# @author Claude
# @since July 4th, 2026

"""Formatting helpers for the roguelike "obituary" screen shown when a run ends.

Turns a single obituary record (as produced by SaveManager.recordRun) plus the
player's lifetimeStats dict into plain display lines that either UI (pygame or
--text-ui) can render as-is, so death reads as a short story beat instead of a
silent reset.
"""

CAUSE_OF_DEATH_PHRASES = {
    "collision": "colliding with itself",
    "quit": "the player's own hand",
}


def causeOfDeathPhrase(causeOfDeath):
    """Returns a short narrative phrase for a cause-of-death code.

    Falls back to the raw code (or "unknown causes" if empty) for any code
    that isn't recognized, so this never raises on unexpected input.
    """
    if not causeOfDeath:
        return "unknown causes"
    return CAUSE_OF_DEATH_PHRASES.get(causeOfDeath, causeOfDeath)


def formatObituaryLines(obituary):
    """Formats a single obituary record into narrative display lines.

    `obituary` is expected to look like the dicts SaveManager.recordRun
    produces/appends to `data["obituaries"]`: name, level, length,
    ticksSurvived, score, causeOfDeath.
    """
    obituary = obituary or {}
    name = obituary.get("name") or "Unnamed Ophidian"
    level = obituary.get("level", 1)
    length = obituary.get("length", 0)
    ticks = obituary.get("ticksSurvived", 0)
    cause = causeOfDeathPhrase(obituary.get("causeOfDeath"))

    return [
        "== Obituary ==",
        "The ophidian {name} lived to level {level}, reaching a length of "
        "{length}, surviving {ticks} ticks, before {cause}.".format(
            name=name, level=level, length=length, ticks=ticks, cause=cause
        ),
    ]


def formatChronicleLines(lifetimeStats):
    """Formats the player's lifetime chronicle summary into display lines."""
    defaults = defaultSaveData()["lifetimeStats"]
    stats = lifetimeStats or defaults
    return [
        "== Chronicle ==",
        "Total runs: {}".format(stats.get("totalRuns", defaults["totalRuns"])),
        "Longest length ever: {}".format(
            stats.get("longestLength", defaults["longestLength"])
        ),
        "Highest level reached: {}".format(
            stats.get("highestLevelReached", defaults["highestLevelReached"])
        ),
        "Highest score ever: {}".format(
            stats.get("highestScore", defaults["highestScore"])
        ),
        "Total food eaten: {}".format(
            stats.get("totalFoodEaten", defaults["totalFoodEaten"])
        ),
    ]


def formatObituaryScreen(obituary, lifetimeStats):
    """Formats the full end-of-run screen: obituary narrative + chronicle.

    Returns a flat list of display lines (with a blank separator line
    between the two sections) that both the text UI and the pygame UI can
    render without caring about the underlying data shapes.
    """
    lines = formatObituaryLines(obituary)
    lines.append("")
    lines.extend(formatChronicleLines(lifetimeStats))
    return lines
