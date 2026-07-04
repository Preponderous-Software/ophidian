from progression.obituary import (
    causeOfDeathPhrase,
    formatChronicleLines,
    formatObituaryLines,
    formatObituaryScreen,
)


def sampleObituary(**overrides):
    obituary = {
        "timestamp": "2026-07-04T00:00:00+00:00",
        "name": "Noodle",
        "length": 12,
        "level": 3,
        "ticksSurvived": 456,
        "score": 789,
        "causeOfDeath": "collision",
    }
    obituary.update(overrides)
    return obituary


def sampleLifetimeStats(**overrides):
    stats = {
        "totalRuns": 7,
        "totalFoodEaten": 42,
        "totalTicksSurvived": 1000,
        "longestLength": 20,
        "highestLevelReached": 5,
        "highestScore": 999,
    }
    stats.update(overrides)
    return stats


def test_cause_of_death_phrase_collision():
    assert causeOfDeathPhrase("collision") == "colliding with itself"


def test_cause_of_death_phrase_quit():
    assert causeOfDeathPhrase("quit") == "the player's own hand"


def test_cause_of_death_phrase_unknown_code_falls_back_to_raw_code():
    assert causeOfDeathPhrase("something-new") == "something-new"


def test_cause_of_death_phrase_empty_falls_back_to_placeholder():
    assert causeOfDeathPhrase(None) == "unknown causes"
    assert causeOfDeathPhrase("") == "unknown causes"


def test_format_obituary_lines_interpolates_fields_for_collision():
    lines = formatObituaryLines(sampleObituary(causeOfDeath="collision"))
    assert lines[0] == "== Obituary =="
    narrative = lines[1]
    assert "Noodle" in narrative
    assert "level 3" in narrative
    assert "length of 12" in narrative
    assert "surviving 456 ticks" in narrative
    assert "colliding with itself" in narrative


def test_format_obituary_lines_interpolates_fields_for_quit():
    lines = formatObituaryLines(sampleObituary(causeOfDeath="quit"))
    narrative = lines[1]
    assert "the player's own hand" in narrative


def test_format_obituary_lines_falls_back_when_name_missing():
    lines = formatObituaryLines(sampleObituary(name=None))
    assert "Unnamed Ophidian" in lines[1]


def test_format_obituary_lines_handles_empty_dict():
    lines = formatObituaryLines({})
    assert lines[0] == "== Obituary =="
    assert "Unnamed Ophidian" in lines[1]
    assert "unknown causes" in lines[1]


def test_format_chronicle_lines_renders_lifetime_numbers():
    lines = formatChronicleLines(sampleLifetimeStats())
    joined = "\n".join(lines)
    assert lines[0] == "== Chronicle =="
    assert "Total runs: 7" in joined
    assert "Longest length ever: 20" in joined
    assert "Highest level reached: 5" in joined
    assert "Highest score ever: 999" in joined
    assert "Total food eaten: 42" in joined


def test_format_chronicle_lines_handles_missing_stats_with_defaults():
    lines = formatChronicleLines(None)
    joined = "\n".join(lines)
    assert "Total runs: 0" in joined
    assert "Highest level reached: 1" in joined


def test_format_obituary_screen_combines_both_sections_with_separator():
    lines = formatObituaryScreen(sampleObituary(), sampleLifetimeStats())
    assert lines[0] == "== Obituary =="
    blankIndex = lines.index("")
    assert lines[blankIndex + 1] == "== Chronicle =="
    joined = "\n".join(lines)
    assert "Noodle" in joined
    assert "Total runs: 7" in joined
