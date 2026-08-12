"""Text-UI key dispatch.

The graphical side of the same dispatch is covered by
tests/rendering/test_pygame_keydown_events.py. Both UIs now share one copy
of every rule (issue #126), so these two files together are what pins that
sharing down: a rule reachable from only one of them shows up here as a
missing test rather than as silent drift.
"""

from textui.textrenderer import TextRenderer

from controls.keybindings import RESTART_SENTINEL
from ophidian import Ophidian


def _makeGame(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True)


def test_text_ui_arrow_sequences_turn_the_snake(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)

    # each turn starts from a direction perpendicular to the one under
    # test, so the reversal guard never applies and the snake genuinely has
    # to turn for the assertion to hold
    for sequence, startingDirection, expectedDirection in (
        ("\x1b[A", 1, 0),  # facing left, turn up
        ("\x1b[D", 0, 1),  # facing up, turn left
        ("\x1b[B", 1, 2),  # facing left, turn down
        ("\x1b[C", 0, 3),  # facing up, turn right
    ):
        game.selectedSnakePart.setDirection(startingDirection)
        game.changedDirectionThisTick = False
        game.handleKeyDownEvent(sequence)
        assert game.selectedSnakePart.getDirection() == expectedDirection


def test_text_ui_direction_key_cannot_reverse_the_snake(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    game.selectedSnakePart.setDirection(3)  # facing right
    game.changedDirectionThisTick = False

    game.handleKeyDownEvent("a")  # opposite of right

    assert game.selectedSnakePart.getDirection() == 3
    assert game.changedDirectionThisTick == False


def test_text_ui_only_the_first_turn_of_a_tick_is_taken(tmp_path, monkeypatch):
    # without the latch, 'w' then 'a' between two ticks would add up to the
    # reversal each key on its own is forbidden from making
    game = _makeGame(monkeypatch, tmp_path)
    game.selectedSnakePart.setDirection(3)  # facing right
    game.changedDirectionThisTick = False

    game.handleKeyDownEvent("w")
    game.handleKeyDownEvent("a")

    assert game.selectedSnakePart.getDirection() == 0


def test_text_ui_unbound_key_is_ignored(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    game.selectedSnakePart.setDirection(3)
    game.changedDirectionThisTick = False
    game.running = True

    assert game.handleKeyDownEvent("z") is None
    assert game.handleKeyDownEvent("\x1b") is None  # a bare escape, not an arrow

    assert game.selectedSnakePart.getDirection() == 3
    assert game.changedDirectionThisTick == False
    assert game.running == True


def test_text_ui_q_key_stops_the_game(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    game.running = True

    game.handleKeyDownEvent("q")

    assert game.running == False


def test_text_ui_c_key_cycles_selected_cosmetic(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(game, "cycleSelectedCosmetic", lambda: calls.append("cycle"))

    assert game.handleKeyDownEvent("c") is None

    assert calls == ["cycle"]


def test_text_ui_p_key_opens_the_text_shop_and_signals_restart(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(game, "openTextShop", lambda: calls.append("shop"))

    result = game.handleKeyDownEvent("p")

    assert calls == ["shop"]
    assert result == RESTART_SENTINEL


def test_text_ui_r_key_restarts_the_run_and_signals_restart(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(
        game, "checkForLevelProgressAndReinitialize", lambda: calls.append("reinit")
    )

    result = game.handleKeyDownEvent("r")

    assert calls == ["reinit"]
    assert result == RESTART_SENTINEL


def test_text_ui_has_no_fullscreen_binding(tmp_path, monkeypatch):
    # there is no window to resize in a terminal, and initializeGameDisplay
    # would be reaching for a pygame this run never imported
    game = _makeGame(monkeypatch, tmp_path)

    assert game.handleKeyDownEvent("\x1b[21~") is None  # xterm's F11
