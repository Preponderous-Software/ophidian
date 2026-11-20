"""Ophidian's 3D view in the browser (the arcade's pygbag build).

The browser game is the 2D game, Ophidian's async pygame loop, and the
page's 2D/3D button (graphik's pygbag template) only changes how it is
shown. The page starts in 3D, as the desktop does, unless the player chose
2D there before (or the address says ?view=2d). While 3D is on, WebOphidian sends what the desktop 3D window draws
(strata_view.scene: the board, the snake and pickups, the HUD) to the page's
Strata grid relay through graphik's Grid3DWebView, once a frame of the 2D
loop. The rules, keys, timers and screens stay the 2D game's own, so the
view can be switched either way in the middle of a run, and every 2D
control works in 3D:

- keys reach pygame's own SDL whichever view shows (it listens on the whole
  page), so the 2D loop reads them as always;
- the mouse and touch land on the relay's canvas while the 3D view shows, so
  they are read from the relay, turned into pygame events (graphik's
  toPygameEvents) and posted to pygame's queue, where the 2D loop's own
  handler reads them in the same place in the frame as a 2D press; a tap is
  aimed from the snake's head where the 3D view draws it;
- the shop, the collision frame and the obituary screen, which the 2D game
  draws on its own canvas, are drawn in 3D too (StrataShop's overlay, the
  red board with the death line, the obituary over the board), for as long
  as the 2D game shows them.

If the 3D view can't start, the 2D view stays and the page and the banner
say why; a page in 2D downloads nothing of the 3D view until it is asked
for. The 3D HUD, the
shop and the obituary screen keep their text out from under the page's
2D/3D button (graphik's buttonArea()).
"""

import asyncio
import math

from controls.keybindings import (
    SWIPE_THRESHOLD_PIXELS,
    WEB_CONTROLS_HINT,
    directionTowards,
)
from ophidian import Ophidian
from preponderous.graphik.grid3d import GridBoard, Unavailable
from preponderous.graphik.grid3d import web as grid3dweb
from strata_view.scene import (
    COLLISION_CAPTION,
    COLLISION_TINT,
    THEME,
    boardPieces,
    headScreenPosition,
    hudOverlay,
    obituaryScreenLines,
)
from strata_view.shop import StrataShop
from ui.shop_screen import PygameShopScreen

VIEW_TITLE = "Ophidian (3D)"
# the 3D view's size gate: Strata's relay is about 1.4 MB; anything far
# bigger than that is not the file this build was made with
MAX_3D_BYTES = 4000000


class BrowserPage:
    """The page around the game under pygbag: its 3D toggle, its size and
    its grid relay (graphik's grid3d.web)."""

    def wants3D(self):
        return grid3dweb.wants3D()

    def set3D(self, on, reason=""):
        grid3dweb.set3D(on, reason)

    def size(self):
        window = _platformWindow()
        return int(window.innerWidth), int(window.innerHeight)

    def buttonArea(self):
        """Where the page's 2D/3D button is, (x, y, width, height), for the
        3D HUD to keep its text out from under it."""
        return grid3dweb.buttonArea()

    def openView(self, width, height):
        return grid3dweb.Grid3DWebView.open(
            width, height, title=VIEW_TITLE, maxBytes=MAX_3D_BYTES
        )


def _platformWindow():
    import platform  # pygbag's, not the standard library's

    return platform.window


def unavailableMessage(reason):
    """The banner when the 3D view can't load, in words a player can act on."""
    return "No 3D view here ({}). The 2D view stays.".format(
        str(reason).strip().rstrip(".") or "it could not load"
    )


class _ShopScreenIn3D(PygameShopScreen):
    """The 2D shop, which also shows itself in the 3D view while that is on:
    the same loop, keys and purchase rule, so the two can't drift."""

    def __init__(self, game, *args):
        super().__init__(*args)
        self.game = game

    def draw(self, upgrades, selectedIndex, shopMessage=None):
        super().draw(upgrades, selectedIndex, shopMessage)
        self.game.showShopIn3D(upgrades, selectedIndex, shopMessage)


class WebOphidian(Ophidian):
    """The browser game, with the page's 3D view when the player asks."""

    def __init__(self, page=None, **kwargs):
        # set before super().__init__, whose initialize() marks a snap
        self.page = page if page is not None else BrowserPage()
        self.view3d = None
        self.forget3D()
        # what the 3D HUD shows that the 2D game draws itself (hudOverlay)
        self.strataBanner = None
        self.strataShop = None
        self.strataOverlayLines = None
        self.strataObituaryScreen = None
        self.strataControlsHint = WEB_CONTROLS_HINT
        # the page's 2D/3D button, which the 3D HUD keeps clear of
        self.strataKeepClear = None
        # the 3D picture of a frame the 2D game is about to hold (holdFrame)
        self.pending3D = None
        super().__init__(**kwargs)

    # -- the toggle

    def forget3D(self):
        """Forgets what the 3D view was last sent, so it is all sent again."""
        self.sent3DBoard = None
        self.sent3DPieces = None
        self.sent3DHud = None
        self.snap3D = True

    def follow3DToggle(self):
        """Opens or closes the 3D view to match the page's toggle."""
        wanted = self.page.wants3D()
        if wanted and self.view3d is None:
            self.open3D()
        elif not wanted and self.view3d is not None:
            self.close3D()

    def open3D(self):
        try:
            width, height = self.page.size()
            self.view3d = self.page.openView(width, height)
        except Unavailable as reason:
            self.view3d = None
            self.page.set3D(False, str(reason))
            self.uiBanner.pushNow(unavailableMessage(reason))
            return
        self.readButtonArea()
        self.forget3D()

    def readButtonArea(self):
        """Where the page's 2D/3D button is now (read on opening and on a
        resize, as the page lays it out)."""
        area = getattr(self.page, "buttonArea", None)
        self.strataKeepClear = area() if area is not None else None

    def close3D(self):
        """Back to the 2D view; if the 3D view failed to load, the banner
        says why."""
        view, self.view3d = self.view3d, None
        reason = view.failure()
        view.close()
        if reason:
            self.uiBanner.pushNow(unavailableMessage(reason))

    # -- one frame

    async def endOfTickAsync(self):
        """After the 2D frame is drawn and before its wait: the 3D view
        follows the toggle, is sent this frame and hands over its input."""
        self.update3D()
        await super().endOfTickAsync()

    def update3D(self):
        self.follow3DToggle()
        if self.view3d is None:
            return
        self.read3DInput()
        self.draw3D()

    def read3DInput(self):
        """The relay's resizes, and its mouse and touch presses posted to
        pygame's queue for the 2D loop's handler."""
        view = self.view3d
        events = view.pollEvents()
        for event in events:
            if event.type == grid3dweb.EVENT_RESIZED and event.width and event.height:
                view.resize(event.width, event.height)
                self.readButtonArea()
                self.sent3DHud = None
        presses = [
            e
            for e in events
            if e.type
            in (grid3dweb.EVENT_MOUSE_BUTTON_DOWN, grid3dweb.EVENT_MOUSE_BUTTON_UP)
        ]
        for event in grid3dweb.toPygameEvents(presses, self.pygame, fingers=False):
            self.pygame.event.post(event)

    def handlePointerGesture(self, downAt, upAt):
        """A press on the 3D view is the 2D rule (Ophidian.
        handlePointerGesture) with the head where the 3D view draws it: a
        swipe turns the way it travelled, a tap towards where it landed.
        The camera looks north across the board, so screen right is east
        and screen up is north, as in 2D."""
        if not self.pointerOn3D():
            return super().handlePointerGesture(downAt, upAt)
        dx = upAt[0] - downAt[0]
        dy = upAt[1] - downAt[1]
        if math.hypot(dx, dy) < SWIPE_THRESHOLD_PIXELS:
            head = headScreenPosition(self, self.view3d.width, self.view3d.height)
            if head is None:
                return
            dx = upAt[0] - head[0]
            dy = upAt[1] - head[1]
        direction = directionTowards(dx, dy)
        if direction is not None:
            self.setDirectionIfAllowed(direction)

    def pointerOn3D(self):
        """True while presses come from the 3D view's canvas: it takes the
        pointer once it is drawing, and until then presses reach the 2D
        canvas, in its own coordinates."""
        return self.view3d is not None and self.view3d.ready

    def draw3D(self):
        """Sends the 3D view what changed since the last frame: the board
        (a new level, the red collision tint), the pieces, the HUD."""
        view = self.view3d
        grid = self.environment.getGrid()
        tint = COLLISION_TINT if self.collision else None
        board = (grid.getColumns(), grid.getRows(), tint)
        if board != self.sent3DBoard:
            view.setBoard(GridBoard(board[0], board[1], THEME), tint=tint)
            self.sent3DBoard = board
            self.sent3DPieces = None
            self.snap3D = True
        pieces = boardPieces(self)
        if pieces != self.sent3DPieces or self.snap3D:
            view.setPieces(pieces, tickSeconds=self.slideSeconds(), snap=self.snap3D)
            self.sent3DPieces = pieces
            self.snap3D = False
        self.sendHud(*hudOverlay(self, view.width, view.height))

    def sendHud(self, labels, panels):
        hud = grid3dweb.encodeHud(labels, panels)
        if hud != self.sent3DHud:
            self.view3d.setLabels(labels, panels)
            self.sent3DHud = hud

    def slideSeconds(self):
        """How long a piece slides to its next cell: until the next tick,
        or not at all with the speed limit off (a tick every frame)."""
        return self.config.tickSpeed if self.config.limitTickSpeed else 0.0

    def initialize(self):
        """A new run or level: its pieces appear on their cells rather than
        sliding over from the old board."""
        super().initialize()
        self.snap3D = True

    # -- what the 2D game draws on its own canvas, drawn in 3D as well

    def drawUiMessage(self):
        width, _ = self.gameDisplay.get_size()
        self.strataBanner = self.uiBanner.draw(
            self.graphik, width, self.config.black, self.config.white
        )

    async def runPygameShop(self):
        """The 2D shop (its loop, keys and rule), shown in 3D too."""
        try:
            await _ShopScreenIn3D(
                self,
                self.pygame,
                self.graphik,
                lambda: self.gameDisplay,
                self.config,
                self.saveManager,
                self.quitApplication,
            ).run()
        finally:
            self.strataShop = None
            if self.view3d is not None:
                self.draw3D()

    def showShopIn3D(self, upgrades, selectedIndex, message):
        """One frame of the shop in the 3D view (StrataShop's layout of the
        2D shop's state). The view follows the toggle here too, so the shop
        can be switched between views while it is open."""
        self.follow3DToggle()
        if self.view3d is None:
            self.strataShop = None
            return
        shop = StrataShop(self.saveManager)
        shop.upgrades = upgrades
        shop.selectedIndex = selectedIndex
        shop.message = message
        self.strataShop = shop
        # the shop answers keys only, as in 2D; presses on the 3D view are
        # read (so a resize is followed) and dropped
        self.view3d.pollEvents()
        self.draw3D()

    def renderCollisionFrame(self):
        """The 2D death frame, and the 3D one held with it: the red board
        with the death line and the obituary over it."""
        super().renderCollisionFrame()
        if self.view3d is not None and self.lastObituary is not None:
            lines = [COLLISION_CAPTION, ""] + obituaryScreenLines(self)[0]
            self.pending3D = self.picture3D(overlayLines=lines)

    def renderObituaryScreen(self):
        """The 2D obituary screen, and the same lines over the 3D board."""
        if self.view3d is not None and self.lastObituary is not None:
            self.pending3D = self.picture3D(obituary=obituaryScreenLines(self))
        super().renderObituaryScreen()

    def picture3D(self, overlayLines=None, obituary=None):
        """What the 3D view shows of this moment, kept to show later (the
        2D loop shows held frames after the board has moved on)."""
        grid = self.environment.getGrid()
        self.strataOverlayLines, self.strataObituaryScreen = overlayLines, obituary
        try:
            labels, panels = hudOverlay(self, self.view3d.width, self.view3d.height)
        finally:
            self.strataOverlayLines = self.strataObituaryScreen = None
        tint = COLLISION_TINT if self.collision else None
        return (
            (grid.getColumns(), grid.getRows(), tint),
            boardPieces(self),
            labels,
            panels,
        )

    def holdFrame(self, seconds):
        super().holdFrame(seconds)
        picture, self.pending3D = self.pending3D, None
        if self.deferFrameHolds and self.heldFrames:
            frame, held = self.heldFrames[-1][:2]
            self.heldFrames[-1] = (frame, held, picture)

    async def replayHeldFrames(self):
        """The 2D loop's held frames (the collision frame, the obituary
        screen), each shown in the 3D view as well for as long."""
        if not self.heldFrames:
            return
        while self.heldFrames:
            held = self.heldFrames.pop(0)
            frame, seconds = held[:2]
            picture = held[2] if len(held) > 2 else None
            self.gameDisplay.blit(frame, (0, 0))
            self.pygame.display.update()
            if picture is not None and self.view3d is not None:
                self.show3DPicture(picture)
            await asyncio.sleep(seconds)
        # the board has moved on (a new run): send it whole
        self.snap3D = True

    def show3DPicture(self, picture):
        (columns, rows, tint), pieces, labels, panels = picture
        view = self.view3d
        view.setBoard(GridBoard(columns, rows, THEME), tint=tint)
        view.setPieces(pieces, snap=True)
        self.sent3DBoard, self.sent3DPieces = (columns, rows, tint), pieces
        self.sendHud(labels, panels)
