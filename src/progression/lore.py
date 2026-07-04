import random

# @author Daniel McCoy Stephenson
# @since July 4th, 2026
#
# Pure texture layer: gives the player's ophidian a name and gives each
# level a place/atmosphere (biome name + flavor text) instead of the bare
# "Level N" label. No mechanical effects.

OPHIDIAN_NAMES = [
    "Kaa",
    "Nagini",
    "Basilisk",
    "Jormungandr",
    "Quetzalcoatl",
    "Apep",
    "Viper",
    "Sable",
    "Nidhogg",
    "Medusa",
    "Ouroboros",
    "Ssaruth",
]

# Curated biomes for the earliest, most-seen levels. Beyond this table,
# getBiome() falls back to a generative combination of adjectives and
# nouns so later levels still feel like distinct places rather than
# reverting to "Level N".
BIOME_TABLE = {
    1: {
        "name": "The Sunken Grove",
        "flavorText": "Mossy roots coil around still, black water.",
    },
    2: {
        "name": "The Ember Flats",
        "flavorText": "Cracked earth radiates a dry, slow-burning heat.",
    },
    3: {
        "name": "The Glass Marsh",
        "flavorText": "Brittle reeds chime like glass in the shifting wind.",
    },
    4: {
        "name": "The Hollow Reach",
        "flavorText": "An echoing expanse where the horizon never quite arrives.",
    },
    5: {
        "name": "The Frostbound Coil",
        "flavorText": "Frozen switchbacks twist into a pale, silent distance.",
    },
    6: {
        "name": "The Obsidian Spiral",
        "flavorText": "Black volcanic glass spirals downward into the dark.",
    },
}

_FALLBACK_ADJECTIVES = [
    "Withered",
    "Gilded",
    "Shattered",
    "Verdant",
    "Ashen",
    "Luminous",
    "Forsaken",
    "Crimson",
    "Silent",
    "Boundless",
]

_FALLBACK_NOUNS = [
    "Expanse",
    "Hollow",
    "Bastion",
    "Wastes",
    "Sanctum",
    "Thicket",
    "Abyss",
    "Causeway",
    "Reliquary",
    "Basin",
]

_FALLBACK_FLAVOR_TEMPLATES = [
    "Few who wander into the {name} speak of what they saw.",
    "The {name} stretches on, indifferent to the ophidian's passing.",
    "Something ancient still stirs within the {name}.",
    "The air itself seems to bend around the {name}.",
]


def generateOphidianName(rng=None):
    """Return a curated serpent-flavored name.

    Pass a seeded random.Random instance for deterministic output (e.g. in
    tests); otherwise the module-level random generator is used.
    """
    chooser = rng.choice if rng is not None else random.choice
    return chooser(OPHIDIAN_NAMES)


def getBiome(level):
    """Return {"name": str, "flavorText": str} for the given level.

    Levels 1-6 use a curated table of distinct, hand-written biomes.
    Higher levels fall back to a generative combination of adjective and
    noun word lists (seeded deterministically by the level number), plus
    a flavor line templated around the generated name, so it never
    degrades to a generic "Level N" label.
    """
    if level in BIOME_TABLE:
        return BIOME_TABLE[level]

    fallbackRng = random.Random(level)
    adjective = fallbackRng.choice(_FALLBACK_ADJECTIVES)
    noun = fallbackRng.choice(_FALLBACK_NOUNS)
    name = f"The {adjective} {noun}"
    template = fallbackRng.choice(_FALLBACK_FLAVOR_TEMPLATES)
    return {
        "name": name,
        "flavorText": template.format(name=name),
    }
