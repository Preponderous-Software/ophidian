import pygame
import pytest
from conftest import regionHasNonBackgroundPixel

from progression.shop import listUpgrades
from ui.shop_screen import PygameShopScreen


def _makeShopScreen(game, onQuit=None):
    return PygameShopScreen(
        game.pygame,
        game.graphik,
        lambda: game.gameDisplay,
        game.config,
        game.saveManager,
        onQuit or game.quitApplication,
    )


def test_draw_renders_title_and_upgrade_rows(pygameGame):
    game = pygameGame
    screen = _makeShopScreen(game)
    upgrades = listUpgrades()

    screen.draw(upgrades, selectedIndex=0, shopMessage=None)

    surface = game.gameDisplay
    width, height = surface.get_size()
    # background is a full-screen black fill...
    assert tuple(surface.get_at((5, 5)))[:3] == game.config.black
    # ...with the title/currency/upgrade text actually blitted onto it
    assert regionHasNonBackgroundPixel(surface, (0, 10, width, 90), game.config.black)


def test_draw_highlights_the_selected_row(pygameGame):
    game = pygameGame
    screen = _makeShopScreen(game)
    upgrades = listUpgrades()

    screen.draw(upgrades, selectedIndex=1, shopMessage=None)

    surface = game.gameDisplay
    highlightColor = (60, 60, 60)
    selectedRowY = 100 + 1 * 60  # startY + selectedIndex * rowHeight, from draw()
    assert tuple(surface.get_at((30, selectedRowY)))[:3] == highlightColor

    # a different row should not be highlighted
    unselectedRowY = 100 + 0 * 60
    assert tuple(surface.get_at((30, unselectedRowY)))[:3] != highlightColor


def test_draw_shows_purchase_confirmation_message(pygameGame):
    game = pygameGame
    screen = _makeShopScreen(game)
    upgrades = listUpgrades()

    withoutMessage = game.gameDisplay
    screen.draw(upgrades, selectedIndex=0, shopMessage=None)
    width, height = withoutMessage.get_size()
    hintY = 100 + len(upgrades) * 60 + 10
    messageBand = (0, hintY + 15, width, 20)
    assert not regionHasNonBackgroundPixel(
        withoutMessage, messageBand, game.config.black
    )

    screen.draw(
        upgrades, selectedIndex=0, shopMessage="Purchased Head Start for 10 currency."
    )
    assert regionHasNonBackgroundPixel(game.gameDisplay, messageBand, game.config.black)


def test_run_navigates_purchases_and_exits_on_escape(pygameGame, monkeypatch):
    game = pygameGame
    monkeypatch.setattr(game.pygame.time, "delay", lambda ms: None)
    screen = _makeShopScreen(game)
    upgrades = listUpgrades()
    game.saveManager.data["currency"] = 100

    # all three land in the same event batch, so run() drains them in a
    # single while-loop iteration: move selection down, purchase the newly
    # selected upgrade, then close the shop.
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))

    screen.run()

    purchased = upgrades[1]
    assert purchased["id"] in game.saveManager.data["purchasedUpgrades"]
    assert game.saveManager.data["currency"] == 100 - purchased["cost"]


def test_run_does_not_purchase_when_already_owned(pygameGame, monkeypatch):
    game = pygameGame
    monkeypatch.setattr(game.pygame.time, "delay", lambda ms: None)
    screen = _makeShopScreen(game)
    upgrades = listUpgrades()
    game.saveManager.data["currency"] = 100
    game.saveManager.data["purchasedUpgrades"] = [upgrades[0]["id"]]

    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))

    screen.run()

    assert game.saveManager.data["purchasedUpgrades"] == [upgrades[0]["id"]]
    assert game.saveManager.data["currency"] == 100


def test_run_calls_onQuit_on_quit_event(pygameGame):
    game = pygameGame
    quitCalled = False

    def stubOnQuit():
        nonlocal quitCalled
        quitCalled = True
        # the real onQuit (Ophidian.quitApplication) calls the builtin
        # quit(), which is what actually breaks out of run() for a QUIT
        # event - the loop itself never flips viewingShop to False for it.
        raise SystemExit

    screen = _makeShopScreen(game, onQuit=stubOnQuit)
    pygame.event.post(pygame.event.Event(pygame.QUIT))

    with pytest.raises(SystemExit):
        screen.run()

    assert quitCalled
