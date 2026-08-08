import time

from conftest import regionHasNonBackgroundPixel

from powerup.powerup import PowerUpType


def test_draw_ui_message_renders_notify_banner(pygameGame):
    game = pygameGame

    game.notify("Test banner message")
    game.drawUiMessage()

    surface = game.gameDisplay
    width, _ = surface.get_size()
    assert tuple(surface.get_at((5, 5)))[:3] == game.config.black  # banner strip fill
    assert regionHasNonBackgroundPixel(surface, (0, 0, width, 30), game.config.black)


def test_draw_ui_message_is_a_noop_with_no_pending_message(pygameGame):
    game = pygameGame
    # __init__ already queued a "enters <biome>" notify() during
    # initialize() - clear it to set up the true empty-queue precondition
    game.uiBanner.queue.clear()
    game.uiBanner.expiresAt = None
    surface = game.gameDisplay
    surface.fill(game.config.white)

    game.drawUiMessage()

    width, _ = surface.get_size()
    assert not regionHasNonBackgroundPixel(
        surface, (0, 0, width, 30), game.config.white
    )


def test_draw_hud_renders_currency_and_owned_upgrades(pygameGame):
    game = pygameGame
    game.saveManager.data["currency"] = 42
    game.saveManager.data["purchasedUpgrades"] = ["head_start"]
    surface = game.gameDisplay
    surface.fill(game.config.white)  # matches the real frame's fill-before-draw

    game.drawHud()

    width, _ = surface.get_size()
    assert regionHasNonBackgroundPixel(surface, (0, 35, width, 15), game.config.white)
    assert regionHasNonBackgroundPixel(surface, (0, 55, width, 15), game.config.white)


def test_draw_hud_omits_upgrades_line_when_none_owned(pygameGame):
    game = pygameGame
    game.saveManager.data["currency"] = 0
    game.saveManager.data["purchasedUpgrades"] = []
    surface = game.gameDisplay
    surface.fill(game.config.white)  # matches the real frame's fill-before-draw

    game.drawHud()

    width, _ = surface.get_size()
    # currency line still renders...
    assert regionHasNonBackgroundPixel(surface, (0, 35, width, 15), game.config.white)
    # ...but the upgrades line is skipped entirely when nothing is owned
    assert not regionHasNonBackgroundPixel(
        surface, (0, 55, width, 15), game.config.white
    )


def test_draw_hud_renders_power_up_line_while_one_is_active(pygameGame):
    # a power-up's activation banner expires well before the power-up
    # itself does, so the HUD has to carry the remainder (issue #114)
    game = pygameGame
    game.saveManager.data["purchasedUpgrades"] = ["head_start"]
    game.activatePowerUp(PowerUpType.SPEED)
    surface = game.gameDisplay
    surface.fill(game.config.white)  # matches the real frame's fill-before-draw

    game.drawHud()

    width, _ = surface.get_size()
    # third line, below the upgrades line this run does own
    assert regionHasNonBackgroundPixel(surface, (0, 73, width, 15), game.config.white)


def test_draw_hud_moves_power_up_line_up_when_no_upgrades_are_owned(pygameGame):
    game = pygameGame
    game.saveManager.data["purchasedUpgrades"] = []
    game.secondWindAvailableThisRun = False
    game.activatePowerUp(PowerUpType.SPEED)
    surface = game.gameDisplay
    surface.fill(game.config.white)  # matches the real frame's fill-before-draw

    game.drawHud()

    width, _ = surface.get_size()
    # takes the (now free) second line rather than leaving a blank row
    assert regionHasNonBackgroundPixel(surface, (0, 55, width, 15), game.config.white)
    assert not regionHasNonBackgroundPixel(
        surface, (0, 73, width, 15), game.config.white
    )


def test_draw_hud_gives_each_running_power_up_its_own_line(pygameGame):
    game = pygameGame
    game.saveManager.data["purchasedUpgrades"] = []
    game.secondWindAvailableThisRun = False
    game.activatePowerUp(PowerUpType.SPEED)
    game.activatePowerUp(PowerUpType.INVINCIBILITY)
    surface = game.gameDisplay
    surface.fill(game.config.white)  # matches the real frame's fill-before-draw

    game.drawHud()

    width, _ = surface.get_size()
    assert regionHasNonBackgroundPixel(surface, (0, 55, width, 15), game.config.white)
    assert regionHasNonBackgroundPixel(surface, (0, 73, width, 15), game.config.white)


def test_draw_hud_omits_power_up_line_when_none_is_running(pygameGame):
    game = pygameGame
    game.saveManager.data["purchasedUpgrades"] = []
    game.secondWindAvailableThisRun = False
    surface = game.gameDisplay
    surface.fill(game.config.white)  # matches the real frame's fill-before-draw

    game.drawHud()

    width, _ = surface.get_size()
    assert not regionHasNonBackgroundPixel(
        surface, (0, 55, width, 15), game.config.white
    )


def test_draw_hud_omits_power_up_line_for_one_with_no_time_left(pygameGame):
    # updatePowerUps() only clears an expired power-up on the next tick, so
    # it stays readable for one frame - don't draw "Speed boost: 0s"
    game = pygameGame
    game.saveManager.data["purchasedUpgrades"] = []
    game.secondWindAvailableThisRun = False
    game.activatePowerUp(PowerUpType.SPEED)
    game.activePowerUps.expiresAt[PowerUpType.SPEED] = time.time() - 1
    surface = game.gameDisplay
    surface.fill(game.config.white)  # matches the real frame's fill-before-draw

    game.drawHud()

    width, _ = surface.get_size()
    assert not regionHasNonBackgroundPixel(
        surface, (0, 55, width, 15), game.config.white
    )
