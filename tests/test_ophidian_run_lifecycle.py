import time

from textui.textrenderer import TextRenderer

from ophidian import Ophidian
from snake.snakePart import SnakePart


def _makeGame(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True)


def _silenceTextRenderer(monkeypatch):
    monkeypatch.setattr(TextRenderer, "renderGrid", lambda self, *args: None)
    monkeypatch.setattr(TextRenderer, "renderMessage", lambda self, message: None)
    monkeypatch.setattr(TextRenderer, "renderStats", lambda self, *args: None)
    monkeypatch.setattr(TextRenderer, "renderHud", lambda self, *args: None)
    monkeypatch.setattr(TextRenderer, "renderControls", lambda self: None)
    monkeypatch.setattr(TextRenderer, "getKeyPress", lambda self, timeout=0: None)


def _runOneTextUiIteration(game, monkeypatch):
    """Runs exactly one pass of runTextUI by having the movement step stop
    the loop, so the end-of-tick bookkeeping still runs before the while
    condition is re-checked."""
    _silenceTextRenderer(monkeypatch)
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)
    monkeypatch.setattr(
        Ophidian,
        "moveEntity",
        lambda self, entity, direction: setattr(self, "running", False),
    )
    game.runTextUI()


def test_end_of_tick_advances_tick_and_clears_latch_without_the_tick_limit(
    tmp_path, monkeypatch
):
    # regression test: self.tick and changedDirectionThisTick used to be
    # incremented/reset inside the `if limitTickSpeed:` block next to the
    # sleep, so pressing 'l' locked the snake into one direction forever and
    # froze the tick counter (see issue #112)
    game = _makeGame(monkeypatch, tmp_path)
    game.config.limitTickSpeed = False
    game.tick = 0
    game.changedDirectionThisTick = True

    slept = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(seconds))

    game.endOfTick()

    assert game.tick == 1
    assert game.changedDirectionThisTick is False
    assert slept == []


def test_end_of_tick_still_sleeps_when_the_tick_limit_is_on(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    game.config.limitTickSpeed = True
    game.config.tickSpeed = 0.25
    game.tick = 0
    game.changedDirectionThisTick = True

    slept = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(seconds))

    game.endOfTick()

    assert slept == [0.25]
    assert game.tick == 1
    assert game.changedDirectionThisTick is False


def test_direction_can_be_changed_again_after_a_tick_without_the_tick_limit(
    tmp_path, monkeypatch
):
    # the player-facing symptom of issue #112: with the limit off, the first
    # turn latched changedDirectionThisTick and every later direction key
    # was ignored for the rest of the process
    game = _makeGame(monkeypatch, tmp_path)
    game.config.limitTickSpeed = False
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    game.selectedSnakePart.setDirection(3)  # facing right
    game.changedDirectionThisTick = False

    game.handleKeyDownEvent("w")
    assert game.selectedSnakePart.getDirection() == 0
    assert game.changedDirectionThisTick is True

    game.endOfTick()

    game.handleKeyDownEvent("a")
    assert game.selectedSnakePart.getDirection() == 1


def test_text_ui_loop_runs_end_of_tick_without_the_tick_limit(tmp_path, monkeypatch):
    # the loop itself must reach the end-of-tick bookkeeping when
    # limitTickSpeed is off, not just endOfTick() in isolation
    game = _makeGame(monkeypatch, tmp_path)
    game.config.limitTickSpeed = False
    game.tick = 0
    game.changedDirectionThisTick = True

    _runOneTextUiIteration(game, monkeypatch)

    assert game.tick == 1
    assert game.changedDirectionThisTick is False


def test_text_ui_restart_frame_renders_the_new_board_before_advancing_it(
    tmp_path, monkeypatch
):
    # the "restart" sentinel means exactly one thing in both loops: skip
    # this iteration's movement step, so the freshly initialized board is
    # presented before the snake takes its first step (issue #117). The
    # pygame counterpart lives in tests/rendering/test_pygame_run_loop.py.
    game = _makeGame(monkeypatch, tmp_path)
    _silenceTextRenderer(monkeypatch)
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)

    keys = ["r"]
    monkeypatch.setattr(
        TextRenderer,
        "getKeyPress",
        lambda self, timeout=0: keys.pop(0) if keys else None,
    )
    renders = []
    monkeypatch.setattr(
        TextRenderer, "renderGrid", lambda self, *args: renders.append(1)
    )
    moves = []

    def recordMoveAndStop(self, entity, direction):
        moves.append(direction)
        self.running = False

    monkeypatch.setattr(Ophidian, "moveEntity", recordMoveAndStop)

    game.runTextUI()

    # two full frames: the restart frame renders but does not move, the
    # frame after it moves as usual
    assert len(renders) == 2
    assert len(moves) == 1


def test_restart_records_the_run_with_a_restart_cause_of_death(tmp_path, monkeypatch):
    # regression test: 'r' used to jump straight to
    # checkForLevelProgressAndReinitialize, discarding the run's obituary,
    # currency and lifetime stats (see issue #113)
    game = _makeGame(monkeypatch, tmp_path)
    runsBefore = game.saveManager.data["lifetimeStats"]["totalRuns"]
    obituariesBefore = len(game.saveManager.data["obituaries"])

    game.handleKeyDownEvent("r")

    assert game.saveManager.data["lifetimeStats"]["totalRuns"] == runsBefore + 1
    assert len(game.saveManager.data["obituaries"]) == obituariesBefore + 1
    assert game.saveManager.data["obituaries"][-1]["causeOfDeath"] == "restart"


def test_restart_banks_the_currency_earned_this_run(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    game.saveManager.data["currency"] = 0
    # currencyEarnedForRun is length - 1, mirroring "one per food eaten"
    game.snakeParts = [SnakePart((0, 0, 0)) for _ in range(4)]

    game.handleKeyDownEvent("r")

    assert game.saveManager.data["currency"] == 3


def test_restart_records_the_run_before_reinitializing_the_board(tmp_path, monkeypatch):
    # order matters: initialize() resets snakeParts back to a single head,
    # so recording after the reset would log every restart as length 1
    game = _makeGame(monkeypatch, tmp_path)
    game.snakeParts = [SnakePart((0, 0, 0)) for _ in range(6)]

    game.restartRun()

    assert game.saveManager.data["obituaries"][-1]["length"] == 6
    assert len(game.snakeParts) == 1


def test_restart_still_reinitializes_and_signals_restart(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(
        game, "checkForLevelProgressAndReinitialize", lambda: calls.append("reinit")
    )

    result = game.handleKeyDownEvent("r")

    assert calls == ["reinit"]
    assert result == "restart"
