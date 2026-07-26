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
