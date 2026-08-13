"""Pausing, as gameplay sees it (issue #130).

Written against the text UI because it is the cheaper of the two to stand
up; the assertions are all about state both loops share. The graphical
loop's half of the same behaviour - that it too declines to move a held
snake - lives in tests/rendering/test_pygame_run_loop.py, since a loop
that only one UI honours is exactly the drift this dispatch exists to
prevent.
"""

import time

from controls.keybindings import RESTART_SENTINEL
from powerup.powerup import PowerUpType
from textui.textrenderer import TextRenderer

from ophidian import Ophidian


def _makeGame(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True)


def test_a_new_game_starts_unpaused(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)

    assert game.paused is False


def test_space_toggles_the_pause_in_the_text_ui(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)

    assert game.handleKeyDownEvent(" ") is None
    assert game.paused is True

    assert game.handleKeyDownEvent(" ") is None
    assert game.paused is False


def test_pausing_does_not_signal_a_restart(tmp_path, monkeypatch):
    # unlike the shop and restart keys, pausing leaves the board exactly as
    # it was - the frame it happens in has nothing it needs to withhold
    # beyond the movement the paused flag already suppresses
    game = _makeGame(monkeypatch, tmp_path)
    board = game.environment

    assert game.handleKeyDownEvent(" ") != RESTART_SENTINEL

    assert game.environment is board


def test_a_paused_frame_is_not_counted_as_a_tick(tmp_path, monkeypatch):
    # self.tick becomes the run's ticksSurvived, so counting held frames
    # would have the obituary claim the ophidian lasted longer than it did
    game = _makeGame(monkeypatch, tmp_path)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    game.tick = 0
    game.changedDirectionThisTick = True
    game.togglePause()

    game.endOfTick()

    assert game.tick == 0
    assert game.changedDirectionThisTick is True


def test_a_paused_frame_sleeps_even_with_the_tick_limit_off(tmp_path, monkeypatch):
    # with the limit off the loop is deliberately a busy one, but there is
    # nothing for it to be busy with while the run is held
    game = _makeGame(monkeypatch, tmp_path)
    game.config.limitTickSpeed = False
    game.config.tickSpeed = 0.25
    game.togglePause()

    slept = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(seconds))

    game.endOfTick()

    assert slept == [0.25]


def test_the_text_loop_does_not_move_a_paused_snake(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    monkeypatch.setattr(TextRenderer, "renderGrid", lambda self, *args: None)
    monkeypatch.setattr(TextRenderer, "renderMessage", lambda self, message: None)
    monkeypatch.setattr(TextRenderer, "renderStats", lambda self, *args: None)
    monkeypatch.setattr(TextRenderer, "renderHud", lambda self, *args: None)
    monkeypatch.setattr(TextRenderer, "renderControls", lambda self: None)
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)

    # pause on the first frame, quit on the second: without the pause the
    # first frame would have moved the snake
    keys = [" ", "q"]
    monkeypatch.setattr(
        TextRenderer,
        "getKeyPress",
        lambda self, timeout=0: keys.pop(0) if keys else None,
    )
    moves = []
    monkeypatch.setattr(
        Ophidian, "moveEntity", lambda self, entity, direction: moves.append(direction)
    )

    game.runTextUI()

    assert moves == []
    assert game.tick == 0


def test_the_text_loop_neither_expires_nor_announces_power_ups_while_held(
    tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path)
    monkeypatch.setattr(TextRenderer, "renderGrid", lambda self, *args: None)
    monkeypatch.setattr(TextRenderer, "renderMessage", lambda self, message: None)
    monkeypatch.setattr(TextRenderer, "renderStats", lambda self, *args: None)
    monkeypatch.setattr(TextRenderer, "renderHud", lambda self, *args: None)
    monkeypatch.setattr(TextRenderer, "renderControls", lambda self: None)
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    # already held before the loop starts, because the power-up step comes
    # first in the frame and would otherwise get one unheld pass at it
    game.togglePause()
    # already long past its deadline: an unheld frame would expire it
    game.activePowerUps.activate(PowerUpType.SPEED, -1)

    keys = ["q"]
    monkeypatch.setattr(
        TextRenderer,
        "getKeyPress",
        lambda self, timeout=0: keys.pop(0) if keys else None,
    )

    game.runTextUI()

    assert game.activePowerUps.isActive(PowerUpType.SPEED) is True


def test_resuming_gives_a_power_up_back_the_time_the_hold_cost_it(
    tmp_path, monkeypatch
):
    # the timers are wall-clock based, so a hold would otherwise drain them
    game = _makeGame(monkeypatch, tmp_path)
    clock = [1000.0]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    game.activePowerUps.activate(PowerUpType.SPEED, 5.0)

    game.togglePause()
    clock[0] += 60.0
    game.togglePause()

    assert game.activePowerUps.remainingSeconds(PowerUpType.SPEED) == 5.0


def test_restarting_a_held_run_starts_the_new_one_unpaused(tmp_path, monkeypatch):
    # initialize() clears the flag, so a restart cannot hand the player a
    # board that is frozen before they have touched it
    game = _makeGame(monkeypatch, tmp_path)
    game.togglePause()

    game.handleKeyDownEvent("r")

    assert game.paused is False
    assert game.pausedAt is None


def test_resuming_a_run_that_was_never_paused_is_harmless(tmp_path, monkeypatch):
    # e.g. a restart cleared the flag mid-hold; there is no recorded start
    # to measure a shift from
    game = _makeGame(monkeypatch, tmp_path)
    game.activePowerUps.activate(PowerUpType.SPEED, 5.0)
    game.paused = True
    game.pausedAt = None

    game.togglePause()

    assert game.paused is False
    assert game.activePowerUps.isActive(PowerUpType.SPEED) is True
