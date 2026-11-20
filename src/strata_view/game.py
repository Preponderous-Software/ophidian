"""Ophidian played in a 3D Strata window (desktop only).

StrataOphidian is the ordinary game with a different face: it runs the same
rules as the text UI (no pygame display; keys go through the text UI's key
tables), but draws each frame with Strata instead of printing to a terminal.
Nothing about how a tick plays changes - the view only reads game state.
"""

import contextlib
import math
import time

import textui.textrenderer as textrenderer
from controls.keybindings import (
    RESTART_SENTINEL,
    STRATA_SCANCODE_ACTIONS,
    STRATA_SCANCODE_KEYS,
    SWIPE_THRESHOLD_PIXELS,
    directionTowards,
)
from ophidian import Ophidian
from progression.obituary import formatObituaryScreen
from strata_view import StrataUnavailable
from strata_view.scene import buildScene, headScreenPosition
from strata_view.shop import StrataShop


class _SilentTextRenderer(textrenderer.TextRenderer):
    """The text UI's renderer with the terminal left alone: no raw mode, no
    printing. StrataOphidian draws everything itself."""

    def enableRawMode(self):
        pass

    def disableRawMode(self):
        pass

    def clearScreen(self):
        pass

    def renderGrid(self, *args, **kwargs):
        pass

    def renderMessage(self, *args, **kwargs):
        pass

    def renderObituary(self, *args, **kwargs):
        pass

    def renderStats(self, *args, **kwargs):
        pass

    def renderHud(self, *args, **kwargs):
        pass

    def renderPauseNotice(self, *args, **kwargs):
        pass

    def renderControls(self, *args, **kwargs):
        pass


@contextlib.contextmanager
def _silentTextRenderer():
    original = textrenderer.TextRenderer
    textrenderer.TextRenderer = _SilentTextRenderer
    try:
        yield
    finally:
        textrenderer.TextRenderer = original


class StrataOphidian(Ophidian):
    def __init__(self, renderer=None, recordPath=None):
        with _silentTextRenderer():
            super().__init__(useTextUI=True, recordPath=recordPath)
        self.renderer = renderer
        self.strataBanner = None
        self.strataOverlayLines = None
        self.strataFrameMs = []
        # the upgrade shop while it's open (see openShop), and when it opened
        self.strataShop = None
        self.strataShopOpenedAt = None

    # -- drawing

    def renderFrame(self, present=True):
        if self.renderer is None:
            return
        started = time.perf_counter()
        scene = buildScene(self, self.renderer.width, self.renderer.height)
        self.renderer.draw(scene)
        if present:
            self.renderer.present()
        self.strataFrameMs.append((time.perf_counter() - started) * 1000.0)

    def renderCollisionFrame(self):
        """The death frame: the board tinted red, with the obituary over it."""
        if self.lastObituary is not None:
            self.strataOverlayLines = formatObituaryScreen(
                self.lastObituary, self.saveManager.data["lifetimeStats"]
            )
        self.renderFrame()

    def holdFrame(self, seconds):
        """Keeps the window responsive while a frame is held (the collision
        frame), redrawing it rather than sleeping on a frozen window."""
        if self.renderer is None or not self.renderer.isWindow:
            self.strataOverlayLines = None
            return
        until = time.monotonic() + seconds
        while time.monotonic() < until and self.running:
            for event in self.renderer.pollEvents():
                if event.type == self.renderer.strata.EVENT_QUIT:
                    self.running = False
            self.renderFrame()
            time.sleep(1 / 60)
        self.strataOverlayLines = None

    # -- one tick, shared by the window loop and the snapshot tool

    def playTick(self):
        """One step of the game, as runTextUI plays it, minus its terminal I/O."""
        if not self.paused:
            self.updatePowerUps()
            self.moveSelectedSnakePart()
        self.strataBanner = self.uiBanner.current()
        self.advanceTick()

    def handleScancode(self, scancode):
        if self.strataShop is not None:
            if not self.strataShop.handleScancode(scancode):
                self.closeShop()
                # like a restart: show the board before it moves again
                return RESTART_SENTINEL
            return None
        if scancode in STRATA_SCANCODE_ACTIONS:
            return self.performAction(STRATA_SCANCODE_ACTIONS[scancode])
        key = STRATA_SCANCODE_KEYS.get(scancode)
        if key is None:
            return None
        return self.handleKeyDownEvent(key)

    def initializeGameDisplay(self):
        """F11 (ACTION_TOGGLE_FULLSCREEN) flips config.fullscreen and calls
        this, as in the 2D window; here it switches the Strata window."""
        if self.renderer is None or not self.renderer.isWindow:
            return
        if not self.renderer.setFullscreen(self.config.fullscreen):
            # Strata before the release that added strata_set_fullscreen
            self.config.fullscreen = False
            self.uiBanner.pushNow(
                "Fullscreen needs a newer Strata library than this one."
            )
            self.strataBanner = self.uiBanner.current()

    def handleStrataPointer(self, downAt, upAt):
        """Mouse or touch steering, as the 2D window has it
        (Ophidian.handlePointerGesture): a swipe turns the way it travelled,
        a tap turns towards where it landed, measured from the snake's head
        as it appears on screen. The camera looks north across the board, so
        screen right is east and screen up is north, as in 2D."""
        if self.strataShop is not None:
            return
        dx = upAt[0] - downAt[0]
        dy = upAt[1] - downAt[1]
        if math.hypot(dx, dy) < SWIPE_THRESHOLD_PIXELS:
            head = headScreenPosition(self, self.renderer.width, self.renderer.height)
            if head is None:
                return
            dx = upAt[0] - head[0]
            dy = upAt[1] - head[1]
        direction = directionTowards(dx, dy)
        if direction is not None:
            self.setDirectionIfAllowed(direction)

    # -- the upgrade shop, drawn over the board (strata_view/shop.py)

    def openShop(self):
        """The 3D window's shop: the same upgrades, keys and purchase rule as
        the 2D and terminal shops, drawn over the board. The board is held
        while it's open (runStrataWindow skips ticks)."""
        self.strataShop = StrataShop(self.saveManager)
        self.strataShopOpenedAt = time.time()

    def closeShop(self):
        """Closes the shop and gives power-ups back the time it was open,
        as the other UIs' shops do (restorePowerUpTimeSpentAway)."""
        self.strataShop = None
        if self.strataShopOpenedAt is not None:
            self.restorePowerUpTimeSpentAway(self.strataShopOpenedAt)
        self.strataShopOpenedAt = None

    # -- the window loop

    def runStrataWindow(self):
        strata = self.renderer.strata
        nextTick = time.monotonic()
        pointerDownAt = None
        while self.running:
            for event in self.renderer.pollEvents():
                if event.type == strata.EVENT_QUIT:
                    self.running = False
                elif event.type == strata.EVENT_KEY_DOWN and not event.repeat:
                    if self.handleScancode(event.scancode) is not None:
                        # a restart: show the fresh board before moving it
                        nextTick = time.monotonic() + self.config.tickSpeed
                elif event.type == strata.EVENT_MOUSE_BUTTON_DOWN and event.button == 1:
                    pointerDownAt = (event.x, event.y)
                elif event.type == strata.EVENT_MOUSE_BUTTON_UP and event.button == 1:
                    if pointerDownAt is not None:
                        self.handleStrataPointer(pointerDownAt, (event.x, event.y))
                    pointerDownAt = None
                elif event.type == strata.EVENT_RESIZED:
                    self.renderer.resize(event.width, event.height)
            if not self.running:
                break
            now = time.monotonic()
            if self.strataShop is not None:
                # the board is held while the shop is open
                nextTick = now + self.config.tickSpeed
            elif now >= nextTick:
                self.playTick()
                nextTick = now + (
                    self.config.tickSpeed
                    if self.paused or self.config.limitTickSpeed
                    else 0
                )
            self.renderFrame()
            time.sleep(1 / 120)
        self.quitApplication()


def runStrataGame(recordPath=None):
    from strata_view.renderer import StrataRenderer

    try:
        renderer = StrataRenderer(window=True, title="Ophidian (3D)")
    except ImportError:
        raise StrataUnavailable(
            "the strata-engine package isn't installed; the README's 3D "
            "section says how to add it"
        )
    except Exception as error:  # no display, no GPU driver, unsupported platform
        raise StrataUnavailable("no Strata window could be opened: %s" % error)
    try:
        StrataOphidian(renderer=renderer, recordPath=recordPath).runStrataWindow()
    finally:
        renderer.close()
