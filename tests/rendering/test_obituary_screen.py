from conftest import regionHasNonBackgroundPixel


def test_render_obituary_screen_draws_text_over_a_black_overlay(pygameGame, monkeypatch):
    game = pygameGame
    monkeypatch.setattr("ophidian.time.sleep", lambda seconds: None)

    game.recordCurrentRun("collision")
    assert game.lastObituary is not None

    game.renderObituaryScreen()

    surface = game.gameDisplay
    width, height = surface.get_size()

    # the overlay fills the whole display with black...
    assert tuple(surface.get_at((5, 5)))[:3] == game.config.black
    # ...and the obituary/chronicle text is actually blitted somewhere in
    # the vertically-centered band renderObituaryScreen draws it in
    assert regionHasNonBackgroundPixel(
        surface, (0, height // 2 - 100, width, 200), game.config.black
    )


def test_render_obituary_screen_is_a_noop_before_any_run_ends(pygameGame):
    game = pygameGame
    assert game.lastObituary is None

    # should not raise even though there's nothing to show yet
    game.renderObituaryScreen()
