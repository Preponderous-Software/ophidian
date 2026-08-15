"""Power-up timers across a shop visit (issue #132).

The shop blocks the run loop for as long as the player browses, and power-up
deadlines are wall-clock, so without the credit these tests assert a boost is
simply consumed by the act of checking a balance. Pausing already settles the
same debt (tests/test_ophidian_pause.py); this is the other thing that stops
the board.
"""

import time

from controls.keybindings import RESTART_SENTINEL
from powerup.powerup import PowerUpType
from textui.textrenderer import TextRenderer

from ophidian import Ophidian


def _makeGame(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True)


def _freezeClock(monkeypatch, clock):
    monkeypatch.setattr(time, "time", lambda: clock[0])


def test_the_text_shop_gives_back_the_time_it_took(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    clock = [1000.0]
    _freezeClock(monkeypatch, clock)
    game.activePowerUps.activate(PowerUpType.SPEED, 5.0)

    # a minute spent reading upgrade descriptions
    monkeypatch.setattr(
        Ophidian, "openTextShop", lambda self: clock.__setitem__(0, clock[0] + 60.0)
    )

    game.openShop()

    assert game.activePowerUps.remainingSeconds(PowerUpType.SPEED) == 5.0


def test_the_pygame_shop_gives_back_the_time_it_took(tmp_path, monkeypatch):
    # the graphical shop blocks in its own event loop rather than on stdin,
    # but it blocks the run loop for just as long
    game = _makeGame(monkeypatch, tmp_path)
    game.config.useTextUI = False
    clock = [1000.0]
    _freezeClock(monkeypatch, clock)
    game.activePowerUps.activate(PowerUpType.INVINCIBILITY, 3.0)

    monkeypatch.setattr(
        Ophidian, "runPygameShop", lambda self: clock.__setitem__(0, clock[0] + 30.0)
    )

    game.openShop()

    assert game.activePowerUps.remainingSeconds(PowerUpType.INVINCIBILITY) == 3.0


def test_the_shop_key_gives_back_the_time_the_shop_took(tmp_path, monkeypatch):
    # the credit has to survive the route the player actually takes, not just
    # a direct openShop() call
    game = _makeGame(monkeypatch, tmp_path)
    clock = [1000.0]
    _freezeClock(monkeypatch, clock)
    game.activePowerUps.activate(PowerUpType.SPEED, 5.0)
    monkeypatch.setattr(
        Ophidian, "openTextShop", lambda self: clock.__setitem__(0, clock[0] + 60.0)
    )

    assert game.handleKeyDownEvent("p") == RESTART_SENTINEL

    assert game.activePowerUps.remainingSeconds(PowerUpType.SPEED) == 5.0


def test_a_shop_visit_no_longer_expires_a_power_up_outright(tmp_path, monkeypatch):
    # what the player saw before: the boost was not merely shortened, it was
    # gone on the first frame after the shop closed
    game = _makeGame(monkeypatch, tmp_path)
    clock = [1000.0]
    _freezeClock(monkeypatch, clock)
    game.activePowerUps.activate(PowerUpType.SPEED, 5.0)
    monkeypatch.setattr(
        Ophidian, "openTextShop", lambda self: clock.__setitem__(0, clock[0] + 60.0)
    )

    game.openShop()
    game.updatePowerUps()

    assert game.activePowerUps.isActive(PowerUpType.SPEED) is True


def test_a_shop_visit_from_a_held_run_is_not_credited_twice(tmp_path, monkeypatch):
    # pausedAt was recorded before the shop opened, so togglePause() will
    # shift by a span that already contains the visit - crediting it here as
    # well would hand the player back a boost longer than it ever was
    game = _makeGame(monkeypatch, tmp_path)
    clock = [1000.0]
    _freezeClock(monkeypatch, clock)
    game.activePowerUps.activate(PowerUpType.SPEED, 5.0)
    monkeypatch.setattr(
        Ophidian, "openTextShop", lambda self: clock.__setitem__(0, clock[0] + 60.0)
    )

    game.togglePause()
    game.openShop()
    game.togglePause()

    assert game.activePowerUps.remainingSeconds(PowerUpType.SPEED) == 5.0


def test_the_shop_leaves_a_run_with_no_power_ups_alone(tmp_path, monkeypatch):
    # the credit is bookkeeping on timers that exist; it must not invent one
    game = _makeGame(monkeypatch, tmp_path)
    clock = [1000.0]
    _freezeClock(monkeypatch, clock)
    monkeypatch.setattr(
        Ophidian, "openTextShop", lambda self: clock.__setitem__(0, clock[0] + 60.0)
    )

    game.openShop()

    assert game.activePowerUps.statuses() == []
