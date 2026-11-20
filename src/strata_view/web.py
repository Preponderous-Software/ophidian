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

On a touch screen (graphik's touchScreen(): a phone, a tablet) the actions
only a keyboard could reach - pause, the shop, restart, the skin, the speed
limit, and in the shop up, down, buy and close - are on-screen keys along
the bottom (graphik's TouchKeys, the keybindings' TOUCH_*_KEYS), in both
views: a tap on one posts the key it names to pygame's queue, so the 2D
loop's own handler (or the shop's) does the rest. In 3D the keys are part
of the HUD and the board is framed above them (the view's insets); in 2D the
canvas is made taller by the bar's height and the game draws on the part
above it (a subsurface), so the bar never covers the board.

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
    TOUCH_BOARD_KEYS,
    TOUCH_CONTROLS_HINT,
    TOUCH_SHOP_KEYS,
    WEB_CONTROLS_HINT,
    directionTowards,
)
from ophidian import Ophidian
from preponderous.graphik import Graphik
from preponderous.graphik.grid3d import BED_TOP, GridBoard, TouchKeys, Unavailable
from preponderous.graphik.grid3d import web as grid3dweb
from strata_view.scene import (
    COLLISION_CAPTION,
    COLLISION_TINT,
    NARROW_WIDTH,
    PROGRESS_BAR_HEIGHT,
    THEME,
    boardPieces,
    hudOverlay,
    obituaryScreenLines,
)
from strata_view.shop import StrataShop
from ui.shop_screen import PygameShopScreen

VIEW_TITLE = "Ophidian (3D)"
# the 3D view's size gate: Strata's relay is about 1.4 MB; anything far
# bigger than that is not the file this build was made with
MAX_3D_BYTES = 4000000
# The 3D HUD's lines at the top (score, level and length, progress; on a
# phone each on a row of its own), which the board is framed below, on a
# narrow window and a wide one.
HUD_TOP_NARROW, HUD_TOP_WIDE = 100, 72
# Under the board, above any on-screen keys: the progress bar and the
# controls line (one line on a touch screen, where the keys are buttons;
# wrapped to three on a phone without them).
HINT_LINE = 20


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

    def touchScreen(self):
        """Whether the page is on a touch screen, where the game shows its
        on-screen keys."""
        return grid3dweb.touchScreen()

    def fitCanvas(self):
        """Has pygbag fit its canvas to the display's new shape (it does so
        only when the page is resized)."""
        _platformWindow().eval("window.dispatchEvent(new Event('resize'))")

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
        self.game.drawTouchKeys2D()
        self.game.showShopIn3D(upgrades, selectedIndex, shopMessage)

    def handleOtherEvent(self, event):
        """A press on the shop's on-screen keys in 2D (in 3D they are read
        from the relay, showShopIn3D)."""
        if event.type == self.pygame.MOUSEBUTTONDOWN and not self.game.pointerOn3D():
            self.game.pressTouchKey2D(event.pos)


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
        # the on-screen keys of a touch screen: the board's, and the shop's
        # while it is open
        self.boardKeys = TouchKeys(TOUCH_BOARD_KEYS)
        self.shopKeys = TouchKeys(TOUCH_SHOP_KEYS)
        self.shopOpen = False
        self.touch = self.readTouch()
        if self.touch:
            self.strataControlsHint = TOUCH_CONTROLS_HINT
        # the 2D window with the bar below the game's part (touch screens
        # only), the bar's height and the Graphik that draws it
        self.screen2D = None
        self.band2D = 0
        self.barGraphik = None
        # a press that went down on an on-screen key in 3D: its release is
        # the key's too, not a gesture
        self.swallowRelease = False
        super().__init__(**kwargs)

    # -- the on-screen keys (touch screens)

    def readTouch(self):
        ask = getattr(self.page, "touchScreen", None)
        return bool(ask()) if ask is not None else False

    def activeTouchKeys(self):
        return self.shopKeys if self.shopOpen else self.boardKeys

    def initializeGameDisplay(self):
        """On a touch screen, the 2D window is the game's size plus the bar
        of on-screen keys below it, and the game draws on the part above
        (self.gameDisplay, a subsurface), so the bar never covers it."""
        if not self.touch or self.config.useTextUI:
            super().initializeGameDisplay()
            return
        width, height = self.config.displayWidth, self.config.displayHeight
        pageWidth, pageHeight = self.page.size()
        self.band2D = max(
            keys.below(width, height, pageWidth, pageHeight)[0]
            for keys in (self.boardKeys, self.shopKeys)
        )
        # not RESIZABLE: under pygbag that is given a square of the page's
        # choosing, which would lose the bar's room
        self.screen2D = self.pygame.display.set_mode((width, height + self.band2D))
        self.gameDisplay = self.screen2D.subsurface((0, 0, width, height))
        self.barGraphik = Graphik(self.screen2D)
        fit = getattr(self.page, "fitCanvas", None)
        if fit is not None:
            try:
                fit()
            except Exception as error:  # the canvas keeps its shape
                print("Warning: could not fit the canvas to the page:", error)

    def scale2D(self):
        """(CSS pixels per 2D canvas pixel, portrait) as the page fits the
        canvas."""
        pageWidth, pageHeight = self.page.size()
        width, height = self.screen2D.get_size()
        return (
            min(pageWidth / float(width), pageHeight / float(height)),
            pageHeight > pageWidth,
        )

    def drawTouchKeys2D(self):
        """The bar of on-screen keys under the 2D game (touch screens)."""
        if self.screen2D is None:
            return
        keys = self.activeTouchKeys()
        width, height = self.screen2D.get_size()
        scale, portrait = self.scale2D()
        self.barGraphik.drawRectangle(
            0, height - self.band2D, width, self.band2D, keys.barColor
        )
        keys.draw(self.barGraphik, width, height, scale, portrait)
        self.pygame.display.update((0, height - self.band2D, width, self.band2D))

    def pressTouchKey2D(self, position):
        """A press on the 2D bar: its key posted to pygame's queue (or the
        next page of keys). True when the press was on the bar."""
        if self.screen2D is None:
            return False
        width, height = self.screen2D.get_size()
        scale, portrait = self.scale2D()
        pressed = self.activeTouchKeys().press(
            position, width, height, self.pygame, scale, portrait
        )
        if pressed is None:
            return False
        self.drawTouchKeys2D()
        return True

    def pressTouchKey3D(self, position):
        """A press on the 3D view's bar, as pressTouchKey2D."""
        if not self.touch or self.view3d is None:
            return False
        view = self.view3d
        pressed = self.activeTouchKeys().press(
            position, view.width, view.height, self.pygame
        )
        if pressed is None:
            return False
        self.sent3DHud = None  # the bar is drawn again (More turns a page)
        return True

    def touchBand3D(self):
        view = self.view3d
        if not self.touch or view is None:
            return 0
        return self.activeTouchKeys().bandHeight(view.width, view.height)

    def handlePointerDown(self, position):
        """A press on the 2D bar is a key's; any other is the 2D game's (a
        swipe or a tap that steers). Presses on the 3D view's bar never get
        here (read3DInput)."""
        if not self.pointerOn3D() and self.pressTouchKey2D(position):
            self.pointerDownAt = None
            return
        super().handlePointerDown(position)

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
        """After the 2D frame is drawn and before its wait: the 2D bar of
        on-screen keys is drawn, and the 3D view follows the toggle, is sent
        this frame and hands over its input."""
        self.drawTouchKeys2D()
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
        pygame's queue for the 2D loop's handler; a press on the on-screen
        keys posts its key instead."""
        view = self.view3d
        events = view.pollEvents()
        self.touch = self.readTouch()  # a laptop's touch screen, once touched
        for event in events:
            if event.type == grid3dweb.EVENT_RESIZED and event.width and event.height:
                view.resize(event.width, event.height)
                self.readButtonArea()
                self.sent3DHud = None
        presses = []
        for event in events:
            if event.type == grid3dweb.EVENT_MOUSE_BUTTON_DOWN:
                if self.pressTouchKey3D((event.x, event.y)):
                    self.swallowRelease = True
                    continue
            elif event.type == grid3dweb.EVENT_MOUSE_BUTTON_UP:
                if self.swallowRelease:
                    self.swallowRelease = False
                    continue
            else:
                continue
            presses.append(event)
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
            location = self.getLocation(self.selectedSnakePart)
            if location == -1:
                return
            # where the view draws the head, with its camera (and insets)
            head = self.view3d.cellScreenPosition(
                location.getX(), location.getY(), y=BED_TOP + 0.4
            )
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
        self.frameBoard3D()
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
        self.sendHud(*self.hudFor(view.width, view.height))

    def frameBoard3D(self):
        """Where the board stands: below the HUD and above the progress bar,
        the controls line and any on-screen keys, on a phone (portrait) or a
        touch screen; framed as on the desktop otherwise."""
        view = self.view3d
        width, height = view.width, view.height
        if not (self.touch or height > width):
            view.setInsets()
            return
        top = HUD_TOP_NARROW if width < NARROW_WIDTH else HUD_TOP_WIDE
        hintLines = 1 if self.touch else 3
        bottom = self.touchBand3D() + PROGRESS_BAR_HEIGHT + 6 + HINT_LINE * hintLines
        view.setInsets(top=top, bottom=bottom)

    def hudFor(self, width, height):
        """The 3D HUD (strata_view.scene's), laid out above any on-screen
        keys."""
        return hudOverlay(self, width, height - self.touchBand3D())

    def sendHud(self, labels, panels):
        if self.touch and self.view3d is not None:
            view = self.view3d
            keyLabels, keyPanels = self.activeTouchKeys().overlay(
                view.width, view.height
            )
            labels, panels = list(labels) + keyLabels, list(panels) + keyPanels
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
        self.shopOpen = True
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
            self.shopOpen = False
            self.strataShop = None
            self.drawTouchKeys2D()
            if self.view3d is not None:
                self.sent3DHud = None
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
        # the shop answers keys only, as in 2D: a press on the 3D view is
        # dropped, unless it is on the shop's on-screen keys
        for event in self.view3d.pollEvents():
            if event.type == grid3dweb.EVENT_MOUSE_BUTTON_DOWN:
                self.swallowRelease = self.pressTouchKey3D((event.x, event.y))
            elif event.type == grid3dweb.EVENT_MOUSE_BUTTON_UP:
                self.swallowRelease = False
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
            labels, panels = self.hudFor(self.view3d.width, self.view3d.height)
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
