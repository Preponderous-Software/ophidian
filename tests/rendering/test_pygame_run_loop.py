import pygame

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

    game.runPygameUI()

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

    game.runPygameUI()

    # two full frames drawn: the restart frame does not move, the frame
    # after it moves as usual
    assert game.tick == 2
    assert len(moves) == 1


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

    game.runPygameUI()

    assert game.selectedSnakePart.getDirection() == 3  # right
