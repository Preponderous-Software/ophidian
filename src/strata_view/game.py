"""Ophidian played in a 3D Strata window (desktop only).

StrataOphidian is the ordinary game with a different face: it runs the same
rules as the text UI (no pygame display; keys go through the text UI's key
tables), but draws each frame with Strata instead of printing to a terminal.
Nothing about how a tick plays changes - the view only reads game state.

Pieces glide: each game tick hands the board's pieces to a grid3d Animator
(syncPieces), and every frame draws them where the Animator has slid them to
by then, so the snake moves smoothly at any frame rate while the rules still
step a whole cell per tick.
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
from preponderous.graphik.grid3d import Animator
from progression.obituary import formatObituaryScreen
from strata_view import StrataUnavailable
from strata_view.scene import (
    COLLISION_CAPTION,
    OBITUARY_SCREEN_SECONDS,
    boardPieces,
    buildScene,
    cellCenter,
    headScreenPosition,
    obituaryScreenLines,
)
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
    def __init__(
        self, renderer=None, recordPath=None, reducedMotion=False, clock=time.monotonic
    ):
        # set before super().__init__, whose initialize() marks a snap
        self.strataSnapPieces = True
        with _silentTextRenderer():
            super().__init__(useTextUI=True, recordPath=recordPath)
        self.renderer = renderer
        self.clock = clock
        self.strataBanner = None
        self.strataOverlayLines = None
        # (lines, footer) while the obituary screen is up (renderObituaryScreen)
        self.strataObituaryScreen = None
        # the window was closed while a death was on screen (holdWindow)
        self.strataClosedOnDeath = False
        self.strataFrameMs = []
        # slides pieces between ticks; reducedMotion puts them straight on
        # their cells instead
        self.strataMotion = Animator(self.cellCenter, reducedMotion=reducedMotion)
        self.syncPieces(snap=True)
        # the upgrade shop while it's open (see openShop), and when it opened
        self.strataShop = None
        self.strataShopOpenedAt = None

    # -- motion between ticks

    def cellCenter(self, column, row):
        grid = self.environment.getGrid()
        return cellCenter(column, row, grid.getColumns(), grid.getRows())

    def initialize(self):
        """A new run or level: the next pieces go straight onto their cells
        rather than sliding over from the old board."""
        super().initialize()
        self.strataSnapPieces = True

    def syncPieces(self, snap=False, tickSeconds=0.0):
        """Hands this tick's pieces to the Animator, which slides each one
        from where it was drawn to its cell over `tickSeconds`. A piece that
        is new this tick (a fresh pickup, the segment a meal grew) appears
        on its cell; one that moved further than a cell jumps; `snap` (and a
        pending restart or new level) puts every piece on its cell."""
        snap = snap or self.strataSnapPieces
        self.strataSnapPieces = False
        self.strataMotion.update(
            boardPieces(self), self.clock(), 0.0 if snap else tickSeconds, snap=snap
        )

    def piecePositions(self, now=None):
        """Where each piece is drawn at `now` (default: the clock's now)."""
        if self.strataSnapPieces:
            # restarted since the last tick (the R key, the shop): show the
            # new board as it stands
            self.syncPieces(snap=True)
        return self.strataMotion.positions(self.clock() if now is None else now)

    def tickSeconds(self):
        """How long until the next tick, which is how long a slide takes:
        none with the speed limit off, when ticks come as fast as frames."""
        return self.config.tickSpeed if self.config.limitTickSpeed else 0.0

    # -- drawing

    def renderFrame(self, present=True, now=None):
        if self.renderer is None:
            return
        started = time.perf_counter()
        scene = buildScene(
            self,
            self.renderer.width,
            self.renderer.height,
            positions=self.piecePositions(now),
        )
        self.renderer.draw(scene)
        if present:
            self.renderer.present()
        self.strataFrameMs.append((time.perf_counter() - started) * 1000.0)

    def renderCollisionFrame(self):
        """The death frame, as the 2D window has it: the board turned red,
        held for 20 ticks before the obituary screen. Here the game's own
        death line and the obituary are written over it as well."""
        lines = [COLLISION_CAPTION]
        if self.lastObituary is not None:
            lines += [""] + formatObituaryScreen(
                self.lastObituary, self.saveManager.data["lifetimeStats"]
            )
        self.strataOverlayLines = lines
        self.renderFrame()

    def obituaryScreen(self):
        """(lines, footer) for the obituary screen: the 2D screen's lines
        (formatObituaryScreen) and what happens next."""
        return obituaryScreenLines(self)

    def renderObituaryScreen(self):
        """The 2D window's obituary screen, in 3D: after a death (once the
        red collision frame has been held) and on the way out, the obituary
        and lifetime chronicle over the whole window for 1.5 seconds. The
        base class skips it in text mode, which this window runs the rules
        in, so it is drawn here."""
        if self.lastObituary is None:
            return
        self.strataObituaryScreen = self.obituaryScreen()
        self.renderFrame()
        self.holdWindow(OBITUARY_SCREEN_SECONDS, whileRunning=False)
        self.strataObituaryScreen = None

    def holdFrame(self, seconds):
        """Keeps the window responsive while a frame is held (the collision
        frame), redrawing it rather than sleeping on a frozen window."""
        self.holdWindow(seconds)
        self.strataOverlayLines = None

    def holdWindow(self, seconds, whileRunning=True):
        """Redraws for `seconds`, answering the window's close button. A
        hold that is part of quitting (whileRunning=False) runs its time out
        even though the game has stopped."""
        if self.renderer is None or not self.renderer.isWindow:
            return
        until = time.monotonic() + seconds
        while time.monotonic() < until and (self.running or not whileRunning):
            for event in self.renderer.pollEvents():
                if event.type == self.renderer.strata.EVENT_QUIT:
                    if self.collision:
                        # the run on screen is already recorded; see
                        # quitApplication
                        self.strataClosedOnDeath = True
                    if not self.running:
                        return  # closing again while it closes: go now
                    self.running = False
            self.renderFrame()
            time.sleep(1 / 60)

    # -- one tick, shared by the window loop and the snapshot tool

    def playTick(self):
        """One step of the game, as runTextUI plays it, minus its terminal I/O."""
        if not self.paused:
            self.updatePowerUps()
            self.moveSelectedSnakePart()
        self.strataBanner = self.uiBanner.current()
        self.advanceTick()
        self.syncPieces(tickSeconds=self.tickSeconds())

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

    def quitApplication(self):
        """Leaving, as in the base game, except after the window was closed
        on a death: that run was recorded when it died, and the new run
        started behind the death screens was never played, so nothing more
        is recorded and no second obituary is shown."""
        if self.strataClosedOnDeath:
            self.collision = True  # the base skips recording a run then
        super().quitApplication()

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


def runStrataGame(recordPath=None, reducedMotion=False):
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
        StrataOphidian(
            renderer=renderer, recordPath=recordPath, reducedMotion=reducedMotion
        ).runStrataWindow()
    finally:
        renderer.close()
