import pygame


def test_pygame_direction_keys_set_direction_and_guard_against_reversal(pygameGame):
    game = pygameGame

    game.selectedSnakePart.setDirection(3)  # facing right
    game.changedDirectionThisTick = False
    game.handleKeyDownEvent(pygame.K_LEFT)  # opposite of right: no-op
    assert game.selectedSnakePart.getDirection() == 3
    assert game.changedDirectionThisTick == False

    game.handleKeyDownEvent(pygame.K_UP)
    assert game.selectedSnakePart.getDirection() == 0
    assert game.changedDirectionThisTick == True

    # already changed direction this tick: a second key is a no-op
    game.handleKeyDownEvent(pygame.K_d)
    assert game.selectedSnakePart.getDirection() == 0

    game.changedDirectionThisTick = False
    game.handleKeyDownEvent(pygame.K_a)
    assert game.selectedSnakePart.getDirection() == 1

    game.changedDirectionThisTick = False
    game.handleKeyDownEvent(pygame.K_s)
    assert game.selectedSnakePart.getDirection() == 2

    game.selectedSnakePart.setDirection(2)  # facing down
    game.changedDirectionThisTick = False
    game.handleKeyDownEvent(pygame.K_w)  # opposite of down: no-op
    assert game.selectedSnakePart.getDirection() == 2

    game.changedDirectionThisTick = False
    game.handleKeyDownEvent(pygame.K_DOWN)
    assert game.selectedSnakePart.getDirection() == 2

    game.changedDirectionThisTick = False
    game.handleKeyDownEvent(pygame.K_RIGHT)
    assert game.selectedSnakePart.getDirection() == 3


def test_pygame_l_key_toggles_tick_speed_limit(pygameGame):
    game = pygameGame
    startingValue = game.config.limitTickSpeed

    game.handleKeyDownEvent(pygame.K_l)
    assert game.config.limitTickSpeed == (not startingValue)

    game.handleKeyDownEvent(pygame.K_l)
    assert game.config.limitTickSpeed == startingValue


def test_pygame_f11_key_toggles_fullscreen(pygameGame):
    game = pygameGame
    startingValue = game.config.fullscreen

    game.handleKeyDownEvent(pygame.K_F11)
    assert game.config.fullscreen == (not startingValue)

    game.handleKeyDownEvent(pygame.K_F11)
    assert game.config.fullscreen == startingValue


def test_pygame_q_key_stops_the_game(pygameGame):
    game = pygameGame
    game.running = True

    game.handleKeyDownEvent(pygame.K_q)

    assert game.running == False


def test_pygame_p_key_opens_shop_and_signals_restart(pygameGame, monkeypatch):
    game = pygameGame
    calls = []
    monkeypatch.setattr(game, "runPygameShop", lambda: calls.append("shop"))

    result = game.handleKeyDownEvent(pygame.K_p)

    assert calls == ["shop"]
    assert result == "restart"


def test_pygame_r_key_reinitializes_level_and_signals_restart(pygameGame, monkeypatch):
    game = pygameGame
    calls = []
    monkeypatch.setattr(
        game, "checkForLevelProgressAndReinitialize", lambda: calls.append("reinit")
    )

    result = game.handleKeyDownEvent(pygame.K_r)

    assert calls == ["reinit"]
    assert result == "restart"


def test_pygame_c_key_cycles_selected_cosmetic(pygameGame, monkeypatch):
    game = pygameGame
    calls = []
    monkeypatch.setattr(game, "cycleSelectedCosmetic", lambda: calls.append("cycle"))

    game.handleKeyDownEvent(pygame.K_c)

    assert calls == ["cycle"]
