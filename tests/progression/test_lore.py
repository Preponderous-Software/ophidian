import random

from progression.lore import (
    BIOME_TABLE,
    OPHIDIAN_NAMES,
    generateOphidianName,
    getBiome,
)


def test_generate_ophidian_name_is_deterministic_with_seeded_rng():
    rng = random.Random(42)
    name = generateOphidianName(rng)
    assert name in OPHIDIAN_NAMES

    expected = random.Random(42).choice(OPHIDIAN_NAMES)
    assert name == expected


def test_generate_ophidian_name_same_seed_same_result():
    firstName = generateOphidianName(random.Random(7))
    secondName = generateOphidianName(random.Random(7))
    assert firstName == secondName


def test_generate_ophidian_name_without_rng_returns_curated_name():
    name = generateOphidianName()
    assert name in OPHIDIAN_NAMES


def test_biomes_1_through_6_are_distinct_and_not_generic():
    seenNames = set()
    for level in range(1, 7):
        biome = getBiome(level)
        assert biome["name"] != f"Level {level}"
        assert "Level" not in biome["name"]
        assert biome["name"]
        assert biome["flavorText"]
        seenNames.add(biome["name"])
    assert len(seenNames) == 6


def test_biome_table_matches_lookup():
    for level, expected in BIOME_TABLE.items():
        assert getBiome(level) == expected


def test_high_level_fallback_is_non_generic_and_non_empty():
    biome = getBiome(25)
    assert biome["name"] != "Level 25"
    assert "Level" not in biome["name"]
    assert biome["name"].strip() != ""
    assert biome["flavorText"].strip() != ""


def test_high_level_fallback_is_deterministic_for_same_level():
    first = getBiome(25)
    second = getBiome(25)
    assert first == second


def test_high_level_fallback_differs_across_some_levels():
    names = {getBiome(level)["name"] for level in range(10, 20)}
    # Not asserting all-unique (small word lists can collide), but there
    # should be meaningful variety rather than one repeated value.
    assert len(names) > 1
