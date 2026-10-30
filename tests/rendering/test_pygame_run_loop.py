import asyncio

import pygame
import pytest

from ophidian import Ophidian


def test_pygame_loop_runs_end_of_tick_without_the_tick_limit(pygameGame, monkeypatch):
    # regression test: self.tick and changedDirectionThisTick used to be
    # updated inside the `if limitTickSpeed:` block next to the sleep, so
    # pressing 'l' in the graphical UI locked the snake into one direction
    # forever and froze the tick counter (see issue #112)
    game = pygameGame
    game.config.limitTickSpeed = False
    game.tick = 0
    game.changedDirectionThisTick = True

    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)
    # one pass only: stopping the loop from the movement step still leaves
    # the end-of-tick bookkeeping to run before the while condition is
    # re-checked
    monkeypatch.setattr(
        Ophidian,
        "moveEntity",
        lambda self, entity, direction: setattr(self, "running", False),
    )

    asyncio.run(game.runPygameUI())

    assert game.tick == 1
    assert game.changedDirectionThisTick is False


def test_pygame_restart_frame_renders_the_new_board_before_advancing_it(
    pygameGame, monkeypatch
):
    # regression test: `continue` after a "restart" only advanced to the
    # next *event*, so the graphical UI moved the snake in the very frame a
    # run restarted while the text UI skipped that step - the sentinel meant
    # two different things (issue #117). The text counterpart lives in
    # tests/test_ophidian_run_lifecycle.py.
    game = pygameGame
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)

    eventFrames = [[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r)], []]
    monkeypatch.setattr(
        pygame.event, "get", lambda: eventFrames.pop(0) if eventFrames else []
    )
    moves = []

    def recordMoveAndStop(self, entity, direction):
        moves.append(direction)
        self.running = False

    monkeypatch.setattr(Ophidian, "moveEntity", recordMoveAndStop)

    asyncio.run(game.runPygameUI())

    # two full frames drawn: the restart frame does not move, the frame
    # after it moves as usual
    assert game.tick == 2
    assert len(moves) == 1


def test_pygame_space_pauses_and_the_loop_declines_to_move_a_held_snake(
    pygameGame, monkeypatch
):
    # the graphical half of issue #130: pausing is gameplay state, so both
    # loops have to honour it identically. The text counterpart lives in
    # tests/test_ophidian_pause.py.
    game = pygameGame
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)

    # pause on the first frame, quit on the second; without the pause the
    # first frame would have moved the snake
    eventFrames = [
        [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)],
        [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q)],
    ]
    monkeypatch.setattr(
        pygame.event, "get", lambda: eventFrames.pop(0) if eventFrames else []
    )
    moves = []
    monkeypatch.setattr(
        Ophidian, "moveEntity", lambda self, entity, direction: moves.append(direction)
    )

    asyncio.run(game.runPygameUI())

    assert game.paused is True
    assert moves == []
    assert game.tick == 0


def test_pygame_restart_does_not_drop_events_queued_behind_it(pygameGame, monkeypatch):
    # the restart flag is tracked across the whole drain rather than
    # breaking out of it, so a key pressed in the same frame still lands
    game = pygameGame
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)

    eventFrames = [
        [
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d),
        ],
        [],
    ]
    monkeypatch.setattr(
        pygame.event, "get", lambda: eventFrames.pop(0) if eventFrames else []
    )
    monkeypatch.setattr(
        Ophidian,
        "moveEntity",
        lambda self, entity, direction: setattr(self, "running", False),
    )

    asyncio.run(game.runPygameUI())

    assert game.selectedSnakePart.getDirection() == 3  # right


def test_pygame_loop_opens_a_requested_shop_before_the_next_move(
    pygameGame, monkeypatch
):
    # the p key only sets shopRequested (the shop is async); the loop has to
    # actually open it, and the frame the key was pressed in must still not
    # advance the snake (issue #117)
    game = pygameGame
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)
    order = []

    async def recordShop(self):
        order.append("shop")

    monkeypatch.setattr(Ophidian, "runPygameShop", recordShop)
    eventFrames = [[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p)], []]
    monkeypatch.setattr(
        pygame.event, "get", lambda: eventFrames.pop(0) if eventFrames else []
    )

    def recordMoveAndStop(self, entity, direction):
        order.append("move")
        self.running = False

    monkeypatch.setattr(Ophidian, "moveEntity", recordMoveAndStop)

    asyncio.run(game.runPygameUI())

    assert order == ["shop", "move"]
    assert game.shopRequested is False
    assert game.tick == 2


def test_pygame_loop_replays_held_frames_without_blocking(pygameGame, monkeypatch):
    # a run that ends inside the loop holds its collision frame and its
    # obituary through holdFrame(), which must not time.sleep there (that
    # freezes a browser tab); the loop replays them, in order, awaiting each
    game = pygameGame
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)
    monkeypatch.setattr(
        "ophidian.time.sleep",
        lambda seconds: (_ for _ in ()).throw(AssertionError("blocking sleep")),
    )
    awaited = []
    realSleep = asyncio.sleep

    async def recordSleep(seconds):
        awaited.append(seconds)
        await realSleep(0)

    monkeypatch.setattr("ophidian.asyncio.sleep", recordSleep)

    def holdTwoFramesAndStop(self, entity, direction):
        self.gameDisplay.fill(self.config.red)
        self.holdFrame(3.0)
        self.gameDisplay.fill(self.config.blue)
        self.holdFrame(1.5)
        self.running = False

    monkeypatch.setattr(Ophidian, "moveEntity", holdTwoFramesAndStop)
    presented = []
    realUpdate = pygame.display.update

    def recordUpdate(*args):
        presented.append(tuple(game.gameDisplay.get_at((1, 1)))[:3])
        return realUpdate(*args)

    monkeypatch.setattr(pygame.display, "update", recordUpdate)

    asyncio.run(game.runPygameUI())

    # both held frames presented, in order, before the next frame is drawn
    assert presented[:2] == [game.config.red, game.config.blue]
    assert awaited[:2] == [3.0, 1.5]
    assert game.heldFrames == []
    assert game.deferFrameHolds is False


def test_pygame_loop_quits_when_the_window_is_closed(pygameGame, monkeypatch):
    game = pygameGame
    quits = []

    # the real quitApplication ends the process with quit(), so nothing
    # after it in the frame - the move included - is reached
    def recordQuitAndExit(self):
        quits.append("quit")
        raise SystemExit

    monkeypatch.setattr(Ophidian, "quitApplication", recordQuitAndExit)
    moves = []

    # stops the loop if the close is ever ignored, so that fails rather
    # than spinning forever
    def recordMoveAndStop(self, entity, direction):
        moves.append(direction)
        self.running = False

    monkeypatch.setattr(Ophidian, "moveEntity", recordMoveAndStop)
    eventFrames = [[pygame.event.Event(pygame.QUIT)]]
    monkeypatch.setattr(
        pygame.event, "get", lambda: eventFrames.pop(0) if eventFrames else []
    )

    with pytest.raises(SystemExit):
        asyncio.run(game.runPygameUI())

    assert quits == ["quit"]
    assert moves == []


def test_pygame_loop_resizes_the_cells_to_fit_a_resized_window(pygameGame, monkeypatch):
    game = pygameGame
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)
    monkeypatch.setattr(
        Ophidian,
        "moveEntity",
        lambda self, entity, direction: setattr(self, "running", False),
    )
    eventFrames = [[pygame.event.Event(pygame.WINDOWRESIZED)]]
    monkeypatch.setattr(
        pygame.event, "get", lambda: eventFrames.pop(0) if eventFrames else []
    )
    # stands in for the window the player has just dragged to a new size
    game.gameDisplay = pygame.Surface((400, 200))
    grid = game.environment.getGrid()
    assert game.locationWidth != 400 / grid.getRows()

    asyncio.run(game.runPygameUI())

    assert game.locationWidth == 400 / grid.getRows()
    assert game.locationHeight == 200 / grid.getColumns()


def _drawOneFrameAtLength(game, monkeypatch, length):
    """Runs a single frame of the pygame loop with the ophidian forced to
    the given length, and returns the colors the progress bar was drawn
    with at its left end and its right end."""
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)
    monkeypatch.setattr(
        Ophidian,
        "moveEntity",
        lambda self, entity, direction: setattr(self, "running", False),
    )
    game.config.limitTickSpeed = False
    # only the count is read when the bar is drawn
    game.snakeParts = [game.selectedSnakePart] * length

    asyncio.run(game.runPygameUI())

    width, height = game.gameDisplay.get_size()
    barY = height - 10
    return (
        tuple(game.gameDisplay.get_at((5, barY)))[:3],
        tuple(game.gameDisplay.get_at((width - 5, barY)))[:3],
    )


def test_pygame_progress_bar_is_red_below_half_the_level_threshold(
    pygameGame, monkeypatch
):
    game = pygameGame
    numLocations = len(game.environment.grid.getLocations())
    # the largest length still under half of the 50% needed to level up
    length = int(numLocations * game.config.levelProgressPercentageRequired / 2)
    assert length / numLocations < game.config.levelProgressPercentageRequired / 2

    filled, unfilled = _drawOneFrameAtLength(game, monkeypatch, length)

    assert filled == game.config.red
    assert unfilled == game.config.black


def test_pygame_progress_bar_is_yellow_from_half_the_level_threshold(
    pygameGame, monkeypatch
):
    game = pygameGame
    numLocations = len(game.environment.grid.getLocations())
    # the smallest length at or above half the threshold
    length = int(numLocations * game.config.levelProgressPercentageRequired / 2) + 1
    assert length / numLocations < game.config.levelProgressPercentageRequired

    filled, unfilled = _drawOneFrameAtLength(game, monkeypatch, length)

    assert filled == game.config.yellow
    assert unfilled == game.config.black


def test_pygame_progress_bar_is_green_once_the_level_threshold_is_met(
    pygameGame, monkeypatch
):
    game = pygameGame
    numLocations = len(game.environment.grid.getLocations())
    # the smallest length at or above the threshold itself
    length = int(numLocations * game.config.levelProgressPercentageRequired) + 1

    filled, unfilled = _drawOneFrameAtLength(game, monkeypatch, length)

    assert filled == game.config.green
    assert unfilled == game.config.black


def test_pygame_progress_bar_fills_the_whole_width_on_a_full_grid(
    pygameGame, monkeypatch
):
    game = pygameGame
    numLocations = len(game.environment.grid.getLocations())

    filled, unfilled = _drawOneFrameAtLength(game, monkeypatch, numLocations)

    assert filled == game.config.green
    assert unfilled == game.config.green


def test_hold_frame_sleeps_outside_the_async_loop(pygameGame, monkeypatch):
    # the text UI, tests and the way out of the desktop game still block
    game = pygameGame
    slept = []
    monkeypatch.setattr("ophidian.time.sleep", lambda seconds: slept.append(seconds))

    game.holdFrame(1.5)

    assert slept == [1.5]
    assert game.heldFrames == []
