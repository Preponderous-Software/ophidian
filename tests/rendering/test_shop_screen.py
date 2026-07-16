from conftest import regionHasNonBackgroundPixel

from progression.shop import listUpgrades
from ui.shop_screen import PygameShopScreen


def _makeShopScreen(game):
    return PygameShopScreen(
        game.pygame,
        game.graphik,
        lambda: game.gameDisplay,
        game.config,
        game.saveManager,
        game.quitApplication,
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
    assert not regionHasNonBackgroundPixel(withoutMessage, messageBand, game.config.black)

    screen.draw(upgrades, selectedIndex=0, shopMessage="Purchased Head Start for 10 currency.")
    assert regionHasNonBackgroundPixel(game.gameDisplay, messageBand, game.config.black)
