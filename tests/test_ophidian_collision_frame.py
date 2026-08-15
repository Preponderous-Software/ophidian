"""The frame a run dies on, in both UIs (issue #133).

The graphical UI has always repainted the board red and followed it with an
obituary screen. The text UI reported nothing at all: initialize() clears the
collision flag and replaces the board before runTextUI() renders again, so the
collision branch of TextRenderer.renderGrid was unreachable under the default
restartUponCollision, and the console copies of the death message and obituary
are wiped by the next clearScreen(). These assert the two now report a death at
the same point in the sequence - the drift behind PRs #92, #95 and #99.
"""

import time

from textui.textrenderer import TextRenderer

from ophidian import Ophidian
from progression.obituary import formatObituaryScreen
from snake.snakePart import SnakePart


def _makeGame(monkeypatch, tmp_path, useTextUI=True):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    game = Ophidian(useTextUI=True)
    game.config.useTextUI = useTextUI
    return game


def _blockTheWayAhead(game):
    """Parks a segment on the cell the head is about to enter.

    Returns the head, so the caller can drive it into the block itself.
    """
    head = game.selectedSnakePart
    grid, location = game.getLocationAndGrid(head)
    ahead = game.getLocationDirection(head.getDirection(), grid, location)
    if ahead == -1:
        # the head spawned against the wall it was facing; any other
        # direction with a cell behind it will do
        for direction in range(4):
            candidate = game.getLocationDirection(direction, grid, location)
            if candidate != -1:
                head.setDirection(direction)
                ahead = candidate
                break
    for entityId in list(ahead.getEntities().keys()):
        ahead.removeEntity(ahead.getEntity(entityId))
    blocker = SnakePart((1, 1, 1))
    game.environment.addEntityToLocation(blocker, ahead)
    game.snakeParts.append(blocker)
    # the paid-for near-miss would otherwise absorb the first collision
    game.secondWindAvailableThisRun = False
    return head


def test_the_text_ui_renders_the_board_the_run_died_on(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    monkeypatch.setattr(TextRenderer, "renderObituary", lambda self, lines: None)
    rendered = []
    monkeypatch.setattr(
        TextRenderer,
        "renderGrid",
        lambda self, environment, snakeParts, collision: rendered.append(
            (environment, collision)
        ),
    )
    head = _blockTheWayAhead(game)
    board = game.environment

    game.moveEntity(head, head.getDirection())

    # the board as it stood at the moment of death, flagged as such - not the
    # replacement one initialize() puts up immediately afterwards
    assert rendered == [(board, True)]
    assert game.environment is not board


def test_the_text_ui_prints_the_obituary_with_that_board(tmp_path, monkeypatch):
    # the terminal has no second screen to give the epitaph, so it belongs to
    # the death frame; the graphical UI shows its own screen after the pause
    game = _makeGame(monkeypatch, tmp_path)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    monkeypatch.setattr(TextRenderer, "renderGrid", lambda self, *args: None)
    rendered = []
    monkeypatch.setattr(
        TextRenderer, "renderObituary", lambda self, lines: rendered.append(lines)
    )
    head = _blockTheWayAhead(game)

    game.moveEntity(head, head.getDirection())

    assert len(rendered) == 1
    assert rendered[0] == formatObituaryScreen(
        game.lastObituary, game.saveManager.data["lifetimeStats"]
    )
    assert "== Obituary ==" in rendered[0]


def test_the_death_frame_is_presented_before_the_pause_that_follows_it(
    tmp_path, monkeypatch
):
    # a pause with nothing new on screen is indistinguishable from a hang -
    # the point of the pause is to give the player time to read this frame
    game = _makeGame(monkeypatch, tmp_path)
    events = []
    monkeypatch.setattr(time, "sleep", lambda seconds: events.append("sleep"))
    monkeypatch.setattr(
        TextRenderer, "renderGrid", lambda self, *args: events.append("grid")
    )
    monkeypatch.setattr(
        TextRenderer, "renderObituary", lambda self, lines: events.append("obituary")
    )
    head = _blockTheWayAhead(game)

    game.moveEntity(head, head.getDirection())

    assert events == ["grid", "obituary", "sleep"]


def test_the_graphical_death_frame_is_unchanged(tmp_path, monkeypatch):
    # the text UI's half was added by routing both through one dispatch, so
    # the graphical half has to come out the other side doing exactly what it
    # did: repaint the board while the collision flag still reddens it
    game = _makeGame(monkeypatch, tmp_path, useTextUI=False)
    events = []
    monkeypatch.setattr(
        Ophidian,
        "drawEnvironment",
        lambda self: events.append(("draw", self.collision)),
    )

    class FakeDisplay:
        def update(self):
            events.append("update")

    class FakePygame:
        display = FakeDisplay()

    game.pygame = FakePygame()

    game.renderCollisionFrame()

    assert events == [("draw", False), "update"]


def test_the_text_death_frame_does_not_touch_pygame(tmp_path, monkeypatch):
    # text mode never imports pygame at all, so reaching for it here would
    # not be a cosmetic mistake but a crash on the last frame of every run
    game = _makeGame(monkeypatch, tmp_path)
    monkeypatch.setattr(TextRenderer, "renderGrid", lambda self, *args: None)
    monkeypatch.setattr(TextRenderer, "renderObituary", lambda self, lines: None)

    assert game.pygame is None

    game.renderCollisionFrame()
