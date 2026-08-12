import pytest

from controls.keybindings import (
    ACTION_CYCLE_COSMETIC,
    ACTION_OPEN_SHOP,
    ACTION_QUIT,
    ACTION_RESTART_RUN,
    ACTION_TOGGLE_FULLSCREEN,
    ACTION_TOGGLE_TICK_SPEED_LIMIT,
    DIRECTION_DOWN,
    DIRECTION_LEFT,
    DIRECTION_RIGHT,
    DIRECTION_UP,
    OPPOSITE_DIRECTIONS,
    TEXT_UI_ACTION_KEYS,
    TEXT_UI_DIRECTION_KEYS,
    buildPygameActionKeys,
    buildPygameDirectionKeys,
)


class FakePygame:
    """Just the key codes the builders read. Distinct values are all that
    matter here; that the real names exist on pygame is covered by
    tests/rendering/test_pygame_keydown_events.py, which uses the real
    module."""

    K_w = 1
    K_a = 2
    K_s = 3
    K_d = 4
    K_UP = 5
    K_LEFT = 6
    K_DOWN = 7
    K_RIGHT = 8
    K_q = 9
    K_l = 10
    K_r = 11
    K_c = 12
    K_p = 13
    K_F11 = 14


def test_opposite_directions_covers_every_direction_symmetrically():
    directions = [DIRECTION_UP, DIRECTION_LEFT, DIRECTION_DOWN, DIRECTION_RIGHT]
    assert sorted(OPPOSITE_DIRECTIONS) == sorted(directions)
    for direction in directions:
        assert OPPOSITE_DIRECTIONS[OPPOSITE_DIRECTIONS[direction]] == direction


def test_text_ui_binds_both_a_letter_and_an_arrow_to_each_direction():
    assert TEXT_UI_DIRECTION_KEYS["w"] == TEXT_UI_DIRECTION_KEYS["\x1b[A"]
    assert TEXT_UI_DIRECTION_KEYS["w"] == DIRECTION_UP
    assert TEXT_UI_DIRECTION_KEYS["a"] == TEXT_UI_DIRECTION_KEYS["\x1b[D"]
    assert TEXT_UI_DIRECTION_KEYS["a"] == DIRECTION_LEFT
    assert TEXT_UI_DIRECTION_KEYS["s"] == TEXT_UI_DIRECTION_KEYS["\x1b[B"]
    assert TEXT_UI_DIRECTION_KEYS["s"] == DIRECTION_DOWN
    assert TEXT_UI_DIRECTION_KEYS["d"] == TEXT_UI_DIRECTION_KEYS["\x1b[C"]
    assert TEXT_UI_DIRECTION_KEYS["d"] == DIRECTION_RIGHT


def test_text_ui_action_keys_match_the_documented_controls():
    assert TEXT_UI_ACTION_KEYS == {
        "q": ACTION_QUIT,
        "l": ACTION_TOGGLE_TICK_SPEED_LIMIT,
        "r": ACTION_RESTART_RUN,
        "c": ACTION_CYCLE_COSMETIC,
        "p": ACTION_OPEN_SHOP,
    }


def test_no_key_is_bound_to_both_a_direction_and_an_action():
    # a key in both tables would be unreachable as an action, since
    # handleKeyDownEvent consults the direction table first
    assert not set(TEXT_UI_DIRECTION_KEYS) & set(TEXT_UI_ACTION_KEYS)
    pygameDirectionKeys = buildPygameDirectionKeys(FakePygame)
    pygameActionKeys = buildPygameActionKeys(FakePygame)
    assert not set(pygameDirectionKeys) & set(pygameActionKeys)


def test_both_uis_reach_the_same_directions():
    assert set(buildPygameDirectionKeys(FakePygame).values()) == set(
        TEXT_UI_DIRECTION_KEYS.values()
    )


def test_fullscreen_is_the_only_action_the_text_ui_does_not_have():
    # the drift guard this module exists for (issue #126): an action added
    # to one UI and forgotten in the other fails here. Fullscreen is
    # legitimately graphical-only - there is no window in a terminal.
    pygameActions = set(buildPygameActionKeys(FakePygame).values())
    textActions = set(TEXT_UI_ACTION_KEYS.values())
    assert pygameActions - textActions == {ACTION_TOGGLE_FULLSCREEN}
    assert textActions - pygameActions == set()


@pytest.mark.parametrize(
    "table",
    [TEXT_UI_ACTION_KEYS, buildPygameActionKeys(FakePygame)],
)
def test_each_action_is_bound_to_exactly_one_key(table):
    actions = list(table.values())
    assert len(actions) == len(set(actions))
