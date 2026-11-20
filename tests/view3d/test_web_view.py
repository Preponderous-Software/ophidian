"""The browser's 3D view (src/strata_view/web.py), without a browser.

WebOphidian runs against the headless pygame driver and a stand-in page
whose grid relay is graphik's RecordingRelay, which keeps every message the
game sends; graphik's wire decoder reads them back. pygbag's own pieces
(the page's toggle and window) are the stand-in's.
"""

import asyncio
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402
from preponderous.graphik.grid3d import Unavailable  # noqa: E402
from preponderous.graphik.grid3d import web as grid3dweb  # noqa: E402

from controls.keybindings import (  # noqa: E402
    DIRECTION_DOWN,
    DIRECTION_LEFT,
    DIRECTION_RIGHT,
    DIRECTION_UP,
    WEB_CONTROLS_HINT,
)
from ophidian import Ophidian  # noqa: E402
from strata_view import scene  # noqa: E402
from strata_view.web import WebOphidian, unavailableMessage  # noqa: E402

PHONE = (390, 844)


class Page:
    """The page around the game: a 3D toggle, a size and a grid relay."""

    def __init__(self, size=PHONE, failOpen=None, relayState="ready", button=None):
        self.on = False
        self.size_ = size
        self.button = button
        self.failOpen = failOpen
        self.relay = grid3dweb.RecordingRelay(state=relayState)
        self.toggles = []
        self.opened = 0

    def wants3D(self):
        return self.on

    def set3D(self, on, reason=""):
        self.toggles.append((bool(on), reason))
        self.on = bool(on)

    def size(self):
        return self.size_

    def buttonArea(self):
        return self.button

    def openView(self, width, height):
        if self.failOpen:
            raise Unavailable(self.failOpen)
        self.opened += 1
        self.relay = grid3dweb.RecordingRelay(state=self.relay.status)
        return grid3dweb.Grid3DWebView.open(width, height, relay=self.relay)


@pytest.fixture
def page():
    return Page()


@pytest.fixture
def game(page, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    game = WebOphidian(page=page)
    game.saveManager.save = lambda: None  # keep the test off the disk
    try:
        yield game
    finally:
        pygame.quit()


def decoded(page, kind=None):
    messages = [grid3dweb.decode(m) for m in page.relay.messages]
    return [body for k, body in messages if kind is None or k == kind]


def hudText(page):
    huds = decoded(page, grid3dweb.HUD)
    return " / ".join(label["text"] for label in huds[-1]["labels"]) if huds else ""


def playFrames(game, monkeypatch, frames):
    """Runs the 2D loop for len(frames) frames, each frame's pygame events
    given (plus whatever was posted), without waiting between them."""
    frames = list(frames)
    realGet = pygame.event.get

    def get():
        posted = realGet()
        if not frames:
            game.running = False
            return posted
        return frames.pop(0) + posted

    monkeypatch.setattr(pygame.event, "get", get)
    monkeypatch.setattr(game, "quitApplication", lambda: None)

    monkeypatch.setattr(game, "tickDelay", lambda: 0)
    realSleep = asyncio.sleep
    monkeypatch.setattr(asyncio, "sleep", lambda seconds=0, *a: realSleep(0))
    game.running = True
    asyncio.run(game.runPygameUI())


def stopMoving(game, monkeypatch):
    """The snake stays put (the start cell is random; a frame's move could
    otherwise kill it or eat something), but direction changes still land."""
    monkeypatch.setattr(game, "moveSelectedSnakePart", lambda: None)


# -- the 2D game is untouched while the toggle is off


def test_nothing_is_sent_and_no_view_opens_while_the_toggle_is_off(
    game, page, monkeypatch
):
    stopMoving(game, monkeypatch)
    playFrames(game, monkeypatch, [[], []])

    assert game.view3d is None
    assert page.opened == 0
    assert page.relay.messages == []


def test_the_browser_game_is_the_2d_game():
    assert issubclass(WebOphidian, Ophidian)


# -- switching views


def test_turning_the_toggle_on_opens_the_view_and_sends_a_whole_frame(game, page):
    page.on = True
    game.update3D()

    assert game.view3d is not None
    assert (game.view3d.width, game.view3d.height) == PHONE
    kinds = [grid3dweb.decode(m)[0] for m in page.relay.messages]
    assert kinds[:3] == [grid3dweb.BOARD, grid3dweb.VIEW, grid3dweb.PIECES]
    assert grid3dweb.PIECES in kinds[3:] and kinds[-1] == grid3dweb.HUD
    pieces = decoded(page, grid3dweb.PIECES)[-1]
    # the head is the last piece; with one segment and a pickup, two anchors
    assert len(pieces["anchors"]) == len(scene.boardPieces(game))


def test_an_unchanged_frame_sends_nothing_more(game, page):
    page.on = True
    game.update3D()
    sent = len(page.relay.messages)

    game.update3D()

    assert len(page.relay.messages) == sent


def test_turning_the_toggle_off_closes_the_view_and_on_again_resends_it(game, page):
    page.on = True
    game.update3D()
    first = page.relay

    page.on = False
    game.update3D()

    assert game.view3d is None
    assert first.closed

    page.on = True
    game.update3D()

    assert page.opened == 2
    assert grid3dweb.BOARD in [grid3dweb.decode(m)[0] for m in page.relay.messages]


def test_a_view_that_cannot_open_leaves_2d_and_says_why(game):
    game.page = Page(failOpen="no WebGL 2 in this browser")
    game.page.on = True

    game.update3D()

    assert game.view3d is None
    assert game.page.toggles == [(False, "no WebGL 2 in this browser")]
    assert game.uiBanner.current() == (
        "No 3D view here (no WebGL 2 in this browser). The 2D view stays."
    )


def test_a_view_that_fails_while_loading_goes_back_to_2d_and_says_why(game, page):
    page.on = True
    game.update3D()
    # the page's toggle turns itself off when the relay fails to load
    page.relay.status = "failed:over the size gate (5 MB > 4 MB)"
    page.on = False

    game.update3D()

    assert game.view3d is None
    assert "over the size gate" in game.uiBanner.current()


def test_the_unavailable_message_is_plain_words():
    assert unavailableMessage("the engine failed.") == (
        "No 3D view here (the engine failed). The 2D view stays."
    )


# -- the HUD


def test_the_3d_hud_shows_the_2d_readouts_and_the_browser_controls(
    game, page, monkeypatch
):
    stopMoving(game, monkeypatch)
    page.on = True
    game.uiBanner.pushNow("Speed limit off: the snake runs as fast as it can.")
    playFrames(game, monkeypatch, [[]])

    text = hudText(page)
    assert "Level 1" in text and "Currency" in text and "Progress" in text
    assert "Speed limit off" in text  # the banner the 2D strip shows
    # the browser's controls line: swipes and taps, and no quit key
    for part in WEB_CONTROLS_HINT.split(" | "):
        assert part in text
    assert "Q quit" not in text
    # the progress bar's panels
    assert decoded(page, grid3dweb.HUD)[-1]["panels"]


def test_every_label_fits_a_phone(game, page):
    from powerup.powerup import PowerUpType

    game.saveManager.data["purchasedUpgrades"] = ["head_start", "second_wind"]
    game.activatePowerUp(PowerUpType.INVINCIBILITY)
    game.paused = True
    game.strataBanner = "A long story line about the ophidian that has to wrap."
    labels, _ = scene.hudOverlay(game, *PHONE)

    for label in labels:
        assert label.x >= 0
        assert label.x + label.pixelSize * len(label.text) <= PHONE[0], label.text
        assert not label.text.endswith("..."), label.text  # nothing cut


def test_the_shop_fits_a_phone_without_cutting_text(game):
    from strata_view.shop import StrataShop
    from preponderous.graphik.grid3d import Label, Panel, fitText

    shop = StrataShop(game.saveManager)
    shop.message = "Not enough currency for Second Wind (costs 25, you have 0)."
    labels, _ = shop.overlay(*PHONE, Label, Panel, fitText)

    for label in labels:
        assert label.x >= 0
        assert label.x + label.pixelSize * len(label.text) <= PHONE[0], label.text
        assert not label.text.endswith("...")
    text = " ".join(label.text for label in labels)
    assert "Ophidian Shop" in text and "you have 0)." in text


def test_the_wide_hud_keeps_its_desktop_layout(game):
    labels, _ = scene.hudOverlay(game, 900, 700)
    progress = [label for label in labels if label.text.startswith("Progress")][0]

    # beside the score, at the top right, as the desktop window has it
    assert progress.y == 22
    assert progress.x > 450


def test_pausing_shows_in_the_3d_hud(game, page):
    page.on = True
    game.handleKeyDownEvent(pygame.K_SPACE)
    game.update3D()

    assert "Paused" in hudText(page)


def test_a_resize_relays_out_the_hud(game, page):
    page.on = True
    game.update3D()
    page.relay.events.append(
        {"type": grid3dweb.EVENT_RESIZED, "width": 844, "height": 390}
    )

    game.update3D()

    assert (game.view3d.width, game.view3d.height) == (844, 390)
    assert decoded(page)[-1].keys() >= {"labels"}


# -- pieces


def test_a_skin_change_resends_the_pieces_even_while_paused(game, page):
    page.on = True
    game.paused = True
    game.update3D()
    before = len(decoded(page, grid3dweb.PIECES))
    game.selectedSnakePart.setColor((1, 2, 3))

    game.update3D()

    assert len(decoded(page, grid3dweb.PIECES)) == before + 1


def test_pieces_slide_for_a_tick_and_not_at_all_without_the_speed_limit(game, page):
    page.on = True
    game.update3D()
    game.config.limitTickSpeed = True
    game.selectedSnakePart.setColor((10, 20, 30))
    game.update3D()
    assert decoded(page, grid3dweb.PIECES)[-1]["tickSeconds"] == pytest.approx(
        game.config.tickSpeed
    )

    game.config.limitTickSpeed = False
    game.selectedSnakePart.setColor((30, 20, 10))
    game.update3D()
    assert decoded(page, grid3dweb.PIECES)[-1]["tickSeconds"] == 0.0


def test_a_restart_snaps_the_new_board_into_place(game, page):
    page.on = True
    game.update3D()

    game.restartRun()
    game.update3D()

    assert decoded(page, grid3dweb.PIECES)[-1]["tickSeconds"] == 0.0
    anchors = decoded(page, grid3dweb.PIECES)[-1]["anchors"]
    assert all((a[0], a[1]) == (a[2], a[3]) for a in anchors)


# -- the pointer: swipes and taps on the 3D view


def press(page, down, up, pointer="touch"):
    page.relay.events += [
        {
            "type": grid3dweb.EVENT_MOUSE_BUTTON_DOWN,
            "button": 1,
            "x": down[0],
            "y": down[1],
            "pointer": pointer,
        },
        {
            "type": grid3dweb.EVENT_MOUSE_BUTTON_UP,
            "button": 1,
            "x": up[0],
            "y": up[1],
            "pointer": pointer,
        },
    ]


@pytest.mark.parametrize(
    "travel, facing, expected",
    [
        ((0, -120), DIRECTION_LEFT, DIRECTION_UP),
        ((0, 120), DIRECTION_LEFT, DIRECTION_DOWN),
        ((-120, 0), DIRECTION_UP, DIRECTION_LEFT),
        ((120, 0), DIRECTION_UP, DIRECTION_RIGHT),
    ],
)
def test_a_swipe_on_the_3d_view_steers_the_way_it_travelled(
    game, page, monkeypatch, travel, facing, expected
):
    stopMoving(game, monkeypatch)
    page.on = True
    game.update3D()
    game.selectedSnakePart.setDirection(facing)
    start = (195, 500)
    press(page, start, (start[0] + travel[0], start[1] + travel[1]))

    # this frame reads the relay; the 2D loop's handler takes it next frame
    game.update3D()
    playFrames(game, monkeypatch, [[]])

    assert game.selectedSnakePart.getDirection() == expected


@pytest.mark.parametrize(
    "offset, facing, expected",
    [
        ((0, -80), DIRECTION_LEFT, DIRECTION_UP),
        ((0, 80), DIRECTION_LEFT, DIRECTION_DOWN),
        ((-80, 0), DIRECTION_UP, DIRECTION_LEFT),
        ((80, 0), DIRECTION_UP, DIRECTION_RIGHT),
    ],
)
def test_a_tap_on_the_3d_view_steers_from_the_head_as_drawn_in_3d(
    game, page, monkeypatch, offset, facing, expected
):
    stopMoving(game, monkeypatch)
    page.on = True
    game.update3D()
    game.selectedSnakePart.setDirection(facing)
    # where the view draws the head (its camera keeps the phone's HUD clear)
    location = game.getLocation(game.selectedSnakePart)
    head = game.view3d.cellScreenPosition(location.getX(), location.getY(), y=0.4)
    tap = (head[0] + offset[0], head[1] + offset[1])
    press(page, tap, tap)

    game.update3D()
    playFrames(game, monkeypatch, [[]])

    assert game.selectedSnakePart.getDirection() == expected


def test_a_tap_is_bound_by_the_2d_rules_no_reversing_into_the_neck(
    game, page, monkeypatch
):
    stopMoving(game, monkeypatch)
    page.on = True
    game.update3D()
    game.selectedSnakePart.setDirection(DIRECTION_UP)
    head = scene.headScreenPosition(game, *PHONE)
    press(page, (head[0], head[1] + 80), (head[0], head[1] + 80))

    game.update3D()
    playFrames(game, monkeypatch, [[]])

    assert game.selectedSnakePart.getDirection() == DIRECTION_UP


def test_presses_before_the_3d_view_draws_are_2d_presses(game, monkeypatch):
    # until the relay is ready its canvas lets presses through to the 2D
    # canvas, whose coordinates the 2D rule reads
    game.page = Page(relayState="loading")
    game.page.on = True
    game.update3D()
    calls = []
    monkeypatch.setattr(
        Ophidian, "handlePointerGesture", lambda self, d, u: calls.append((d, u))
    )

    game.handlePointerGesture((1, 2), (3, 4))

    assert calls == [((1, 2), (3, 4))]


# -- the shop


def shopFrames(game, monkeypatch, keys):
    frames = [[pygame.event.Event(pygame.KEYDOWN, key=k)] if k else [] for k in keys]
    monkeypatch.setattr(pygame.event, "get", lambda: frames.pop(0) if frames else [])
    realSleep = asyncio.sleep
    monkeypatch.setattr(asyncio, "sleep", lambda seconds=0, *a: realSleep(0))
    asyncio.run(game.runPygameShop())


def test_the_shop_shows_in_3d_and_buys_with_the_2d_keys(game, page, monkeypatch):
    page.on = True
    game.update3D()
    game.saveManager.data["currency"] = 100
    seen = []
    realShow = game.showShopIn3D

    def recordShop(*args):
        realShow(*args)
        seen.append(hudText(page))

    monkeypatch.setattr(game, "showShopIn3D", recordShop)

    shopFrames(game, monkeypatch, [None, pygame.K_RETURN, pygame.K_ESCAPE])

    assert "Ophidian Shop" in seen[0] and "Currency: 100" in seen[0]
    assert any("Purchased" in text for text in seen)
    assert game.saveManager.data["currency"] < 100
    assert game.saveManager.data["purchasedUpgrades"]
    # closed: the board's HUD again
    assert game.strataShop is None
    assert "Ophidian Shop" not in hudText(page)


def test_the_shop_can_be_switched_to_3d_while_it_is_open(game, page, monkeypatch):
    frames = [[], [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)]]

    def get():
        page.on = True  # pressed while the shop is up
        return frames.pop(0) if frames else []

    monkeypatch.setattr(pygame.event, "get", get)
    realSleep = asyncio.sleep
    monkeypatch.setattr(asyncio, "sleep", lambda seconds=0, *a: realSleep(0))

    asyncio.run(game.runPygameShop())

    assert game.view3d is not None
    huds = [
        " ".join(l["text"] for l in h["labels"]) for h in decoded(page, grid3dweb.HUD)
    ]
    assert any("Ophidian Shop" in h for h in huds)


# -- death


def dieNow(game):
    """Points the head into its own body and moves it."""
    game.spawnStartingSegments(3)
    game.secondWindAvailableThisRun = False
    head = game.selectedSnakePart
    grid, location = game.getLocationAndGrid(head)
    neck = game.snakeParts[1]
    neckLocation = game.getLocation(neck)
    for direction in (DIRECTION_UP, DIRECTION_LEFT, DIRECTION_DOWN, DIRECTION_RIGHT):
        if game.getLocationDirection(direction, grid, location) is neckLocation:
            game.moveEntity(head, direction)
            return
    raise AssertionError("no neck beside the head")


def test_dying_holds_the_red_board_and_obituary_in_3d_as_in_2d(game, page, monkeypatch):
    page.on = True
    game.update3D()
    game.deferFrameHolds = True
    game.config.restartUponCollision = True

    dieNow(game)

    # the 2D game set aside its collision frame and obituary screen; each
    # carries the 3D picture of the same moment
    assert len(game.heldFrames) == 2
    collision, obituary = (held[2] for held in game.heldFrames)
    assert collision[0][2] == scene.COLLISION_TINT
    # wrapped to the phone's width, so read as one text
    assert scene.COLLISION_CAPTION in " ".join(label.text for label in collision[2])
    obituaryText = " ".join(label.text for label in obituary[2])
    assert "A new run begins in a moment." in obituaryText

    realSleep = asyncio.sleep
    monkeypatch.setattr(asyncio, "sleep", lambda seconds=0, *a: realSleep(0))
    shown = []
    realPicture = game.show3DPicture
    monkeypatch.setattr(
        game, "show3DPicture", lambda p: (realPicture(p), shown.append(hudText(page)))
    )
    asyncio.run(game.replayHeldFrames())

    assert "collides with" in shown[0]
    assert "A new run begins" in shown[1]
    boards = decoded(page, grid3dweb.BOARD)
    tinted = [
        b for b in boards if b["shapes"][0]["color"][0] > b["shapes"][0]["color"][1]
    ]
    assert tinted
    # after the hold, the new run's board goes whole, its pieces snapped
    game.update3D()
    assert decoded(page, grid3dweb.PIECES)[-1]["tickSeconds"] == 0.0


def test_dying_with_3d_off_holds_only_the_2d_frames(game, monkeypatch):
    game.deferFrameHolds = True
    dieNow(game)

    assert [held[2] for held in game.heldFrames] == [None, None]


# -- the entry point


def test_main_runs_the_web_game_in_a_browser_and_the_2d_game_elsewhere():
    import importlib.util

    path = os.path.join(os.path.dirname(__file__), "..", "..", "src", "main.py")
    source = open(path).read()
    namespace = {}
    # everything but the last line, which starts the game
    exec(compile(source.replace("asyncio.run(main())", ""), path, "exec"), namespace)

    assert namespace["chooseGame"]("emscripten") is WebOphidian
    assert namespace["chooseGame"]("linux") is Ophidian
    assert importlib.util.find_spec("strata_view.web") is not None


# -- the page's 2D/3D button, which the 3D text keeps clear of

# where graphik's template puts the button on a 390-pixel phone (top right)
PHONE_BUTTON = (326, 8, 56, 36)


def underButton(labels, area):
    return [
        label.text
        for label in labels
        if scene.overlapsArea(
            label.x,
            label.y,
            label.pixelSize * len(label.text),
            label.pixelSize,
            area,
            0,
        )
    ]


def test_opening_the_view_reads_where_the_button_is(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    page = Page(button=PHONE_BUTTON)
    game = WebOphidian(page=page)
    try:
        page.on = True
        game.update3D()
        assert game.strataKeepClear == PHONE_BUTTON

        # a rotated phone: the button moves with the page's right edge
        page.button = (780, 8, 56, 36)
        page.relay.events.append(
            {"type": grid3dweb.EVENT_RESIZED, "width": 844, "height": 390}
        )
        game.update3D()
        assert game.strataKeepClear == (780, 8, 56, 36)
    finally:
        pygame.quit()


def test_the_shop_title_moves_below_the_button_on_a_phone(game):
    from preponderous.graphik.grid3d import Label, Panel, fitText
    from strata_view.shop import SHOP_TITLE, StrataShop

    shop = StrataShop(game.saveManager)
    shop.message = "Purchased Head Start."
    labels, _ = shop.overlay(*PHONE, Label, Panel, fitText, PHONE_BUTTON)

    assert underButton(labels, PHONE_BUTTON) == []
    title = [label for label in labels if label.text == SHOP_TITLE][0]
    assert title.y >= PHONE_BUTTON[1] + PHONE_BUTTON[3]
    # the rest still fits the phone, nothing cut
    for label in labels:
        assert 0 <= label.x and label.x + label.pixelSize * len(label.text) <= PHONE[0]
    assert labels[-1].y + labels[-1].pixelSize < PHONE[1]


def test_the_shop_keeps_its_layout_where_the_button_is_out_of_the_way(game):
    from preponderous.graphik.grid3d import Label, Panel, fitText
    from strata_view.shop import SHOP_TITLE, StrataShop

    shop = StrataShop(game.saveManager)
    plain, _ = shop.overlay(900, 700, Label, Panel, fitText)
    beside, _ = shop.overlay(900, 700, Label, Panel, fitText, (836, 8, 56, 36))

    assert [(lb.text, lb.x, lb.y) for lb in plain] == [
        (lb.text, lb.x, lb.y) for lb in beside
    ]
    assert [lb for lb in plain if lb.text == SHOP_TITLE][0].y == 22


def test_the_shop_in_the_hud_keeps_clear_of_the_button(game, page):
    from strata_view.shop import StrataShop

    game.strataKeepClear = PHONE_BUTTON
    game.strataShop = StrataShop(game.saveManager)
    labels, _ = scene.hudOverlay(game, *PHONE)

    assert "Ophidian Shop" in [label.text for label in labels]
    assert underButton(labels, PHONE_BUTTON) == []


def test_a_long_score_ends_before_the_button_on_a_phone(game, monkeypatch):
    monkeypatch.setattr(game, "getScoreLabel", lambda: "12345 (x2 score)")
    game.strataKeepClear = PHONE_BUTTON
    labels, _ = scene.hudOverlay(game, *PHONE)

    assert underButton(labels, PHONE_BUTTON) == []
    assert labels[0].text == "12345 (x2 score)"


def test_the_wide_hud_puts_the_progress_share_left_of_the_button(game):
    button = (836, 8, 56, 36)
    game.strataKeepClear = button
    labels, _ = scene.hudOverlay(game, 900, 700)
    progress = [label for label in labels if label.text.startswith("Progress")][0]

    assert underButton(labels, button) == []
    assert progress.y == 22 and progress.x > 450
    assert progress.x + progress.pixelSize * len(progress.text) <= button[0]


def test_the_obituary_screen_stays_below_the_button(game):
    lines = ["The ophidian, a long-lived serpent, ceased to be."] * 60
    labels, _ = scene.obituaryScreenOverlay(
        lines, "A new run begins in a moment.", *PHONE, PHONE_BUTTON
    )

    assert underButton(labels, PHONE_BUTTON) == []
    assert all(label.y + label.pixelSize <= PHONE[1] for label in labels)


def test_without_a_button_the_hud_is_as_before(game):
    # the desktop 3D window has no page button: nothing moves
    plain = scene.hudOverlay(game, *PHONE)[0]
    game.strataKeepClear = None
    assert [(lb.text, lb.x, lb.y) for lb in scene.hudOverlay(game, *PHONE)[0]] == [
        (lb.text, lb.x, lb.y) for lb in plain
    ]


def test_a_page_starting_in_3d_gets_the_3d_view_on_the_first_frame(
    tmp_path, monkeypatch
):
    # graphik's page starts in 3D: the toggle is on before the game runs
    monkeypatch.chdir(tmp_path)
    page = Page()
    page.on = True
    game = WebOphidian(page=page)
    try:
        game.update3D()
        assert game.view3d is not None and page.opened == 1
        assert {grid3dweb.BOARD, grid3dweb.PIECES, grid3dweb.HUD} <= {
            kind for kind, _ in (grid3dweb.decode(m) for m in page.relay.messages)
        }
    finally:
        pygame.quit()


# -- the on-screen keys on a touch screen (graphik's TouchKeys)


class TouchPage(Page):
    """A phone's page: a touch screen."""

    def __init__(self, size=PHONE, **kwargs):
        super().__init__(size=size, **kwargs)
        self.fitted = 0

    def touchScreen(self):
        return True

    def fitCanvas(self):
        self.fitted += 1


@pytest.fixture
def phone(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    page = TouchPage()
    game = WebOphidian(page=page)
    game.saveManager.save = lambda: None
    try:
        yield game, page
    finally:
        pygame.quit()


def slotCentre(slot):
    return (int(slot.x + slot.width / 2), int(slot.y + slot.height / 2))


def slots2D(game):
    width, height = game.screen2D.get_size()
    scale, portrait = game.scale2D()
    return {
        s.label: s
        for s in game.activeTouchKeys().layout(width, height, scale, portrait)
    }


def tap2D(position):
    return [
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=1),
        pygame.event.Event(pygame.MOUSEBUTTONUP, pos=position, button=1),
    ]


def slots3D(game):
    view = game.view3d
    return {s.label: s for s in game.activeTouchKeys().layout(view.width, view.height)}


def test_the_keys_name_every_keyboard_only_action():
    from controls.keybindings import TOUCH_BOARD_KEYS, TOUCH_SHOP_KEYS

    board = {key for _, key in TOUCH_BOARD_KEYS}
    assert board == {"space", "p", "r", "c", "l"}  # pause, shop, restart, skin, speed
    assert {key for _, key in TOUCH_SHOP_KEYS} == {"up", "down", "return", "escape"}


def test_without_a_touch_screen_there_are_no_keys(game, page):
    assert game.screen2D is None
    assert game.gameDisplay.get_size() == (
        game.config.displayWidth,
        game.config.displayHeight,
    )
    page.on = True
    game.update3D()
    assert "Pause" not in hudText(page)
    assert game.touchBand3D() == 0


def test_on_a_touch_screen_the_2d_window_has_room_for_the_bar_below_the_game(phone):
    game, page = phone
    width, height = game.config.displayWidth, game.config.displayHeight
    assert game.gameDisplay.get_size() == (width, height)  # the game's part
    assert game.screen2D.get_size() == (width, height + game.band2D)
    assert game.band2D > 0 and page.fitted == 1
    scale, portrait = game.scale2D()
    assert portrait
    for slot in slots2D(game).values():
        # below the game's part, and a finger's size on the phone
        assert slot.y >= height
        assert slot.width * scale >= 44 - 1e-6 and slot.height * scale >= 44 - 1e-6
    # a press on the board is still a gesture, and lands on the game's part
    game.handlePointerDown((100, 100))
    assert game.pointerDownAt == (100, 100)


def test_the_2d_bar_is_drawn_under_the_game(phone, monkeypatch):
    game, page = phone
    stopMoving(game, monkeypatch)
    playFrames(game, monkeypatch, [[]])
    keys = game.activeTouchKeys()
    width, height = game.screen2D.get_size()
    assert game.screen2D.get_at((1, height - 1))[:3] == keys.barColor
    pause = slots2D(game)["Pause"]
    assert game.screen2D.get_at((int(pause.x) + 2, int(pause.y) + 2))[:3] == keys.color


def test_tapping_the_pause_and_speed_keys_in_2d(phone, monkeypatch):
    game, page = phone
    stopMoving(game, monkeypatch)
    keys = slots2D(game)
    game.config.limitTickSpeed = True
    # each tap is a frame; the key it posts is read the frame after
    playFrames(
        game,
        monkeypatch,
        [tap2D(slotCentre(keys["Pause"])), [], tap2D(slotCentre(keys["Speed"])), []],
    )
    assert game.paused and game.config.limitTickSpeed is False
    # a tap on a key never steers the snake
    assert game.pointerDownAt is None


def test_tapping_the_retry_key_restarts_the_run(phone, monkeypatch):
    game, page = phone
    stopMoving(game, monkeypatch)
    restarts = []
    monkeypatch.setattr(game, "restartRun", lambda: restarts.append(1))
    playFrames(game, monkeypatch, [tap2D(slotCentre(slots2D(game)["Retry"])), []])
    assert restarts == [1]


def test_tapping_the_skin_key_cycles_the_skin(phone, monkeypatch):
    game, page = phone
    stopMoving(game, monkeypatch)
    cycled = []
    monkeypatch.setattr(game, "cycleSelectedCosmetic", lambda: cycled.append(1))
    playFrames(game, monkeypatch, [tap2D(slotCentre(slots2D(game)["Skin"])), []])
    assert cycled == [1]


def test_tapping_the_shop_key_opens_the_shop(phone, monkeypatch):
    game, page = phone
    stopMoving(game, monkeypatch)
    opened = []

    async def visit():
        opened.append(1)
        game.shopRequested = False

    monkeypatch.setattr(game, "visitPygameShop", visit)
    playFrames(game, monkeypatch, [tap2D(slotCentre(slots2D(game)["Shop"])), [], []])
    assert opened == [1]


def test_the_shops_keys_navigate_buy_and_close_it_in_2d(phone, monkeypatch):
    game, page = phone
    game.saveManager.data["currency"] = 1000
    game.shopOpen = True  # the shop's keys are the bar's while it is open
    keys = slots2D(game)
    game.shopOpen = False
    taps = [slotCentre(keys[label]) for label in ("Down", "Buy", "Close")]
    realGet = pygame.event.get

    def get(*args):
        # each frame of the shop's loop: what was posted, then the next tap
        return realGet() + (tap2D(taps.pop(0)) if taps else [])

    monkeypatch.setattr(pygame.event, "get", get)
    realSleep = asyncio.sleep
    monkeypatch.setattr(asyncio, "sleep", lambda seconds=0, *a: realSleep(0))
    asyncio.run(game.runPygameShop())
    assert game.saveManager.data["currency"] < 1000
    assert game.saveManager.data["purchasedUpgrades"]
    assert not game.shopOpen and not taps


def test_on_a_touch_screen_the_3d_view_frames_the_board_above_the_keys(phone):
    game, page = phone
    page.on = True
    game.update3D()
    view = game.view3d
    band = game.touchBand3D()
    assert band >= 44
    top, bottom = view.insets
    assert bottom > band  # the bar, the progress bar and the controls line
    # the board's near edge stands above all of it
    from preponderous.graphik.grid3d import projectToScreen

    grid = game.environment.getGrid()
    columns, rows = grid.getColumns(), grid.getRows()
    camera = view.camera()
    for x in (-columns / 2 - 0.35, columns / 2 + 0.35):
        for z in (-rows / 2 - 0.35, rows / 2 + 0.35):
            sx, sy = projectToScreen(camera, (x, -0.18, z), view.width, view.height)
            assert top - 1 <= sy <= view.height - bottom + 1
            assert 0 <= sx <= view.width
    # the camera the page was sent is that one
    sent = decoded(page, grid3dweb.VIEW)[-1]
    assert sent["eye"] == pytest.approx(camera.eye, abs=1e-4)


def test_the_3d_hud_carries_the_keys_and_keeps_its_text_above_them(phone):
    game, page = phone
    page.on = True
    game.update3D()
    hud = decoded(page, grid3dweb.HUD)[-1]
    texts = [label["text"] for label in hud["labels"]]
    for label in ("Pause", "Shop", "Retry", "Skin", "Speed"):
        assert label in texts
    assert "Swipe or tap to steer" in texts
    band = game.touchBand3D()
    keyLabels = set(slots3D(game))
    for label in hud["labels"]:
        if label["text"] not in keyLabels:
            assert label["y"] + label["pixelSize"] <= PHONE[1] - band, label["text"]


@pytest.mark.parametrize(
    "label, check",
    [
        ("Pause", lambda g: g.paused),
        ("Speed", lambda g: g.config.limitTickSpeed is False),
    ],
)
def test_tapping_a_3d_key_does_what_its_key_does(phone, monkeypatch, label, check):
    game, page = phone
    stopMoving(game, monkeypatch)
    game.config.limitTickSpeed = True
    page.on = True
    game.update3D()
    position = slotCentre(slots3D(game)[label])
    press(page, position, position)

    game.update3D()  # reads the tap, posts the key
    playFrames(game, monkeypatch, [[]])

    assert check(game)
    assert game.pointerDownAt is None and not game.swallowRelease


def test_tapping_the_3d_retry_skin_and_shop_keys(phone, monkeypatch):
    game, page = phone
    stopMoving(game, monkeypatch)
    calls = []
    monkeypatch.setattr(game, "restartRun", lambda: calls.append("r"))
    monkeypatch.setattr(game, "cycleSelectedCosmetic", lambda: calls.append("c"))

    async def visit():
        calls.append("p")
        game.shopRequested = False

    monkeypatch.setattr(game, "visitPygameShop", visit)
    page.on = True
    game.update3D()
    for label in ("Retry", "Skin", "Shop"):
        position = slotCentre(slots3D(game)[label])
        press(page, position, position)
        game.update3D()
        playFrames(game, monkeypatch, [[], []])
    assert calls == ["r", "c", "p"]


def test_a_key_tap_in_3d_does_not_steer_and_a_swipe_after_it_still_does(
    phone, monkeypatch
):
    game, page = phone
    stopMoving(game, monkeypatch)
    page.on = True
    game.update3D()
    game.selectedSnakePart.setDirection(DIRECTION_LEFT)
    position = slotCentre(slots3D(game)["Skin"])
    press(page, position, position)
    game.update3D()
    playFrames(game, monkeypatch, [[]])
    assert game.selectedSnakePart.getDirection() == DIRECTION_LEFT
    press(page, (195, 500), (195, 380))
    game.update3D()
    playFrames(game, monkeypatch, [[]])
    assert game.selectedSnakePart.getDirection() == DIRECTION_UP


def test_the_shops_keys_navigate_buy_and_close_it_in_3d(phone, monkeypatch):
    game, page = phone
    game.saveManager.data["currency"] = 1000
    page.on = True
    game.update3D()
    realSleep = asyncio.sleep
    monkeypatch.setattr(asyncio, "sleep", lambda seconds=0, *a: realSleep(0))
    game.shopOpen = True
    keys = slots3D(game)
    game.shopOpen = False
    for label in ("Down", "Buy", "Close"):
        position = slotCentre(keys[label])
        press(page, position, position)
    frames = []
    realShow = game.showShopIn3D

    def show(*args):
        frames.append(hudText(page))
        realShow(*args)

    monkeypatch.setattr(game, "showShopIn3D", show)
    asyncio.run(game.runPygameShop())
    assert game.saveManager.data["currency"] < 1000
    assert game.saveManager.data["purchasedUpgrades"]
    assert not game.shopOpen
    # while it was open, the bar showed the shop's keys
    assert any("Buy" in text and "Close" in text for text in frames)
    assert "Pause" in hudText(page)  # the board's keys are back
