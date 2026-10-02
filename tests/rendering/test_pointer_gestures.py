"""Touch steering (a phone has no keyboard): a swipe steers the way it
travelled, a tap steers towards where it landed from the snake's head, and
both obey the same rules as a direction key."""

import asyncio

import pygame

from controls.keybindings import (
    DIRECTION_DOWN,
    DIRECTION_RIGHT,
    DIRECTION_UP,
    SWIPE_THRESHOLD_PIXELS,
)
from ophidian import Ophidian


def _headCentre(game):
    location = game.getLocation(game.selectedSnakePart)
    return (
        (location.getX() + 0.5) * game.locationWidth,
        (location.getY() + 0.5) * game.locationHeight,
    )


def _travelling(game, direction):
    game.selectedSnakePart.setDirection(direction)
    game.changedDirectionThisTick = False


def test_a_swipe_steers_the_way_it_travelled(pygameGame):
    game = pygameGame
    _travelling(game, DIRECTION_UP)

    game.handlePointerGesture((100, 100), (100 + SWIPE_THRESHOLD_PIXELS + 20, 110))

    assert game.selectedSnakePart.getDirection() == DIRECTION_RIGHT


def test_a_swipe_anywhere_on_screen_ignores_where_the_head_is(pygameGame):
    # a swipe that starts and ends far to the left of the head still turns
    # down when it travelled down
    game = pygameGame
    _travelling(game, DIRECTION_RIGHT)

    game.handlePointerGesture((0, 0), (0, SWIPE_THRESHOLD_PIXELS + 1))

    assert game.selectedSnakePart.getDirection() == DIRECTION_DOWN


def test_a_tap_steers_towards_where_it_landed_from_the_head(pygameGame):
    game = pygameGame
    _travelling(game, DIRECTION_RIGHT)
    headX, headY = _headCentre(game)
    tap = (headX + 2, headY - game.locationHeight)

    game.handlePointerGesture(tap, tap)

    assert game.selectedSnakePart.getDirection() == DIRECTION_UP


def test_a_gesture_cannot_reverse_the_snake_into_its_neck(pygameGame):
    game = pygameGame
    _travelling(game, DIRECTION_RIGHT)

    game.handlePointerGesture((200, 100), (100, 100))

    assert game.selectedSnakePart.getDirection() == DIRECTION_RIGHT


def test_a_gesture_is_one_turn_per_tick_like_a_key(pygameGame):
    game = pygameGame
    _travelling(game, DIRECTION_RIGHT)

    game.handlePointerGesture((100, 200), (100, 100))  # up
    game.handlePointerGesture((200, 100), (100, 100))  # then left: refused

    assert game.selectedSnakePart.getDirection() == DIRECTION_UP


def test_the_pygame_loop_steers_from_a_mouse_press_and_release(pygameGame, monkeypatch):
    # a touch reaches pygame as a mouse press in a browser; the loop pairs
    # the down and the up into one gesture before it moves the snake
    game = pygameGame
    _travelling(game, DIRECTION_RIGHT)
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)
    eventFrames = [
        [
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(100, 300), button=1),
            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(100, 200), button=1),
        ]
    ]
    monkeypatch.setattr(
        pygame.event, "get", lambda: eventFrames.pop(0) if eventFrames else []
    )
    moves = []

    def recordMoveAndStop(self, entity, direction):
        moves.append(direction)
        self.running = False

    monkeypatch.setattr(Ophidian, "moveEntity", recordMoveAndStop)

    asyncio.run(game.runPygameUI())

    assert moves == [DIRECTION_UP]
    assert game.pointerDownAt is None


def test_a_release_without_a_press_does_not_steer(pygameGame, monkeypatch):
    # e.g. the press that dismissed the browser's click-to-start overlay
    game = pygameGame
    _travelling(game, DIRECTION_RIGHT)
    monkeypatch.setattr(Ophidian, "quitApplication", lambda self: None)
    eventFrames = [[pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(0, 0), button=1)]]
    monkeypatch.setattr(
        pygame.event, "get", lambda: eventFrames.pop(0) if eventFrames else []
    )
    monkeypatch.setattr(
        Ophidian,
        "moveEntity",
        lambda self, entity, direction: setattr(self, "running", False),
    )

    asyncio.run(game.runPygameUI())

    assert game.selectedSnakePart.getDirection() == DIRECTION_RIGHT
