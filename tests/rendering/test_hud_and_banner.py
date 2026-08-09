import time

from conftest import regionHasNonBackgroundPixel

from ophidian import POWER_UP_INDICATOR_METER_WIDTH
from powerup.powerup import (
    PowerUpType,
    getPowerUpDefinition,
    getPowerUpDurationSeconds,
)


def _meterSamplePoints(surface):
    """The x of each end of a first power-up indicator's meter, and its y.

    Derived from the drawn geometry rather than restated as pixel literals,
    so moving the meter fails these tests where it moved instead of as an
    unexplained color mismatch. The first indicator's label sits on the row
    the upgrades line would have taken (63) when no upgrades are owned, and
    drawPowerUpIndicator puts the meter 9px below that.
    """
    width, _ = surface.get_size()
    meterLeft = width // 2 - POWER_UP_INDICATOR_METER_WIDTH // 2
    return meterLeft + 1, meterLeft + POWER_UP_INDICATOR_METER_WIDTH - 2, 63 + 9 + 1


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


def _capturedHudText(game, monkeypatch):
    """Every string drawHud hands to graphik, in draw order.

    The pixel-region assertions elsewhere in this file can only tell that
    *something* was drawn on a row; the score line's whole point is what it
    says, so it is captured instead.
    """
    drawn = []
    monkeypatch.setattr(
        game.graphik,
        "drawText",
        lambda text, *args: drawn.append(text),
    )
    game.drawHud()
    return drawn


def test_draw_hud_renders_the_score(pygameGame, monkeypatch):
    # regression test: the score was read in three places, none of which the
    # graphical UI drew, so a player there had no way to see it until the run
    # ended (see issue #124)
    game = pygameGame
    game.saveManager.data["currency"] = 42
    game.score = 125

    assert "Score: 125 | Currency: 42" in _capturedHudText(game, monkeypatch)


def test_draw_hud_annotates_the_score_while_a_multiplier_runs(pygameGame, monkeypatch):
    # the same annotation the text UI's stats block shows, so a doubled bite
    # is visible in both UIs rather than only through the power-up countdown
    game = pygameGame
    game.saveManager.data["currency"] = 0
    game.score = 120
    game.activatePowerUp(PowerUpType.SCORE_MULTIPLIER)

    assert "Score: 120 (x2) | Currency: 0" in _capturedHudText(game, monkeypatch)


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
    # takes the (now free) second line rather than leaving a blank row, and
    # nothing is drawn in the band the next indicator down would occupy
    assert regionHasNonBackgroundPixel(surface, (0, 55, width, 15), game.config.white)
    assert not regionHasNonBackgroundPixel(
        surface, (0, 80, width, 25), game.config.white
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
    assert regionHasNonBackgroundPixel(surface, (0, 79, width, 15), game.config.white)


def test_draw_hud_draws_a_duration_meter_under_each_power_up_label(pygameGame):
    # the "visual timer" half of issue #72: the countdown text alone only
    # steps once a second, while the meter drains continuously
    game = pygameGame
    game.saveManager.data["purchasedUpgrades"] = []
    game.secondWindAvailableThisRun = False
    game.activatePowerUp(PowerUpType.SPEED)
    surface = game.gameDisplay
    surface.fill(game.config.white)

    game.drawHud()

    # a freshly activated power-up fills its whole meter, so both ends of
    # the track carry the power-up's own color rather than the empty gray
    startX, endX, meterY = _meterSamplePoints(surface)
    speedColor = getPowerUpDefinition(PowerUpType.SPEED)["color"]
    assert tuple(surface.get_at((startX, meterY)))[:3] == speedColor
    assert tuple(surface.get_at((endX, meterY)))[:3] == speedColor


def test_draw_hud_drains_the_duration_meter_as_a_power_up_runs_out(
    pygameGame, monkeypatch
):
    game = pygameGame
    game.saveManager.data["purchasedUpgrades"] = []
    game.secondWindAvailableThisRun = False
    game.activatePowerUp(PowerUpType.SPEED)
    endTime = game.activePowerUps.expiresAt[PowerUpType.SPEED]
    duration = getPowerUpDurationSeconds(PowerUpType.SPEED)
    monkeypatch.setattr("powerup.active.time.time", lambda: endTime - duration / 4)
    surface = game.gameDisplay
    surface.fill(game.config.white)

    game.drawHud()

    # a quarter of the duration left: the left end is still filled, and the
    # far end has fallen back to the empty track
    startX, endX, meterY = _meterSamplePoints(surface)
    speedColor = getPowerUpDefinition(PowerUpType.SPEED)["color"]
    assert tuple(surface.get_at((startX, meterY)))[:3] == speedColor
    assert tuple(surface.get_at((endX, meterY)))[:3] == game.config.gray


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
