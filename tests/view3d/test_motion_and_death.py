"""The 3D window's motion between ticks, the snake's colours and its death
screens (src/strata_view/game.py and scene.py). No GPU needed: positions and
overlays are plain data, and the clock is a stand-in."""

import pytest

from controls.keybindings import DIRECTION_DOWN, DIRECTION_LEFT, DIRECTION_RIGHT
from controls.keybindings import DIRECTION_UP
from progression.obituary import formatObituaryScreen
from snake.snakePart import SnakePart
from strata_view import scene
from strata_view.game import StrataOphidian

TICK = 0.2


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def makeGame(**kwargs):
    clock = Clock()
    game = StrataOphidian(clock=clock, **kwargs)
    game.config.tickSpeed = TICK
    game.config.limitTickSpeed = True
    game.saveManager.save = lambda: None  # keep the test off the disk
    return game, clock


def headId(game):
    return ("snake", 0)


def pointHeadIntoTheBoard(game):
    """A direction with a free cell ahead of the head (the start cell is
    random, and a head facing the wall it stands on doesn't move)."""
    head = game.selectedSnakePart
    grid, location = game.getLocationAndGrid(head)
    for direction in (DIRECTION_RIGHT, DIRECTION_LEFT, DIRECTION_DOWN, DIRECTION_UP):
        ahead = game.getLocationDirection(direction, grid, location)
        if ahead != -1 and not any(
            isinstance(ahead.getEntity(e), SnakePart) for e in ahead.getEntities()
        ):
            head.setDirection(direction)
            for entityId in list(ahead.getEntities().keys()):
                ahead.removeEntity(ahead.getEntity(entityId))
            return
    pytest.skip("the head has nowhere to go")


def headCell(game):
    location = game.getLocation(game.selectedSnakePart)
    return game.cellCenter(location.getX(), location.getY())


# -- motion


def test_the_head_slides_from_its_old_cell_to_its_new_one_over_a_tick():
    game, clock = makeGame()
    pointHeadIntoTheBoard(game)
    before = headCell(game)
    game.playTick()
    after = headCell(game)
    assert before != after
    assert game.piecePositions(clock.now)[headId(game)] == pytest.approx(before)
    halfway = ((before[0] + after[0]) / 2, (before[1] + after[1]) / 2)
    clock.now += TICK / 2
    assert game.piecePositions()[headId(game)] == pytest.approx(halfway)
    clock.now += TICK
    assert game.piecePositions()[headId(game)] == pytest.approx(after)


def test_reduced_motion_moves_a_whole_cell_at_once():
    game, clock = makeGame(reducedMotion=True)
    pointHeadIntoTheBoard(game)
    game.playTick()
    assert game.piecePositions(clock.now)[headId(game)] == pytest.approx(headCell(game))


def test_with_the_speed_limit_off_nothing_slides():
    # ticks come as fast as frames, so a slide would never be seen to finish
    game, clock = makeGame()
    game.config.limitTickSpeed = False
    pointHeadIntoTheBoard(game)
    game.playTick()
    assert game.piecePositions(clock.now)[headId(game)] == pytest.approx(headCell(game))


def test_a_new_pickup_appears_on_its_cell():
    game, clock = makeGame()
    game.playTick()
    for entity, column, row in scene.entityCells(game):
        if not isinstance(entity, SnakePart):
            game.removeEntity(entity)
    game.spawnPickup()
    game.syncPieces(tickSeconds=TICK)
    (entity, column, row) = [
        found
        for found in scene.entityCells(game)
        if not isinstance(found[0], SnakePart)
    ][0]
    position = game.piecePositions(clock.now)[("entity", entity.getID())]
    assert position == game.cellCenter(column, row)


def test_a_grown_segment_appears_on_its_cell_instead_of_sliding_in():
    game, clock = makeGame()
    head = game.selectedSnakePart
    game.spawnSnakePart(head.getTail(), (255, 0, 0))
    game.syncPieces(tickSeconds=TICK)
    newest = len(game.snakeParts) - 1
    location = game.getLocation(game.snakeParts[newest])
    assert game.piecePositions(clock.now)[("snake", newest)] == game.cellCenter(
        location.getX(), location.getY()
    )


def test_a_restart_or_a_new_level_puts_every_piece_straight_on_its_cell():
    game, clock = makeGame()
    pointHeadIntoTheBoard(game)
    game.playTick()  # mid-slide from here
    game.restartRun()  # the R key; a new level goes through initialize() too
    positions = game.piecePositions(clock.now)
    for piece in scene.boardPieces(game):
        assert positions[piece.id] == game.cellCenter(piece.column, piece.row)


def test_a_frame_draws_pieces_where_the_animator_has_them():
    game, clock = makeGame()
    pointHeadIntoTheBoard(game)
    before = headCell(game)
    game.playTick()
    built = scene.buildScene(game, 900, 700, positions=game.piecePositions(clock.now))
    heads = [s for s in built.shapes if s.scale[1] == scene.HEAD_HEIGHT]
    assert (heads[0].position[0], heads[0].position[2]) == pytest.approx(before)


# -- colours


def test_the_body_fades_from_the_neck_to_the_tail_in_each_parts_own_colour():
    skin = (0.2, 0.6, 0.9)
    eaten = (1.0, 0.0, 0.0)
    cells = [(x, 0) for x in range(5, 0, -1)]
    pieces = scene.snakePieces(
        cells, DIRECTION_RIGHT, skin, colors=[skin, skin, skin, eaten, eaten]
    )
    body = {p.link: p.color for p in pieces if p.style == "body"}
    assert body[1] == pytest.approx(skin)  # the neck wears the skin as it is
    assert body[2][2] < body[1][2]  # and it darkens down the tail
    assert body[3][0] > body[3][1]  # a segment grown from food keeps its red
    assert body[4][0] < body[3][0]


def test_a_dark_skin_lightens_towards_the_tail_so_it_stays_visible():
    obsidian = scene.rgb((40, 40, 45))
    tail = scene.bodyShade(obsidian, 1.0)
    assert scene.luminance(tail) > scene.luminance(obsidian)


def test_changing_skin_recolours_the_head_as_in_2d():
    game, _ = makeGame()
    game.saveManager.data["unlockedCosmetics"] = ["default", "frost"]
    game.saveManager.data["selectedCosmetic"] = "default"
    game.cycleSelectedCosmetic()
    head = [p for p in scene.boardPieces(game) if p.style == "head"][0]
    frost = scene.rgb((137, 207, 240))
    assert head.color == pytest.approx(tuple(min(1.0, c * 1.15 + 0.06) for c in frost))


# -- death


def blockTheWayAhead(game):
    head = game.selectedSnakePart
    grid, location = game.getLocationAndGrid(head)
    for direction in range(4):
        ahead = game.getLocationDirection(direction, grid, location)
        if ahead != -1:
            head.setDirection(direction)
            break
    for entityId in list(ahead.getEntities().keys()):
        ahead.removeEntity(ahead.getEntity(entityId))
    blocker = SnakePart((1, 1, 1))
    game.environment.addEntityToLocation(blocker, ahead)
    game.snakeParts.append(blocker)
    game.secondWindAvailableThisRun = False
    return head


def test_a_death_shows_the_red_board_then_the_2d_windows_obituary_screen():
    game, _ = makeGame()
    frames = []

    def recordFrame(present=True, now=None):
        labels, _ = scene.hudOverlay(game, 900, 700)
        frames.append((game.collision, [label.text for label in labels]))

    game.renderFrame = recordFrame
    head = blockTheWayAhead(game)
    game.moveEntity(head, head.getDirection())

    expected = formatObituaryScreen(
        game.lastObituary, game.saveManager.data["lifetimeStats"]
    )
    (redBoard, redTexts), (screen, screenTexts) = frames
    assert redBoard and scene.COLLISION_CAPTION in " ".join(redTexts)
    assert screen  # still the run that died, before the new one starts
    # every obituary line is on the screen (wrapped, never cut), and the
    # footer says what happens next
    shown = " ".join(screenTexts)
    for line in expected:
        for word in line.split():
            assert word in shown
    assert "A new run begins in a moment." in screenTexts
    assert game.getScoreLabel() not in screenTexts  # it replaces the HUD
    # and then the new run is on, with nothing left over the board
    assert not game.collision
    assert game.strataObituaryScreen is None and game.strataOverlayLines is None


def test_without_restart_upon_collision_the_screen_says_the_run_is_over():
    game, _ = makeGame()
    game.config.restartUponCollision = False
    screens = []
    game.renderFrame = lambda present=True, now=None: screens.append(
        game.strataObituaryScreen
    )
    head = blockTheWayAhead(game)
    game.moveEntity(head, head.getDirection())
    assert screens[-1][1] == "The run is over."
    assert not game.running


def test_quitting_shows_the_obituary_screen_as_the_2d_window_does(monkeypatch):
    import builtins

    game, _ = makeGame()
    screens = []
    game.renderFrame = lambda present=True, now=None: screens.append(
        game.strataObituaryScreen
    )
    monkeypatch.setattr(builtins, "quit", lambda: None)
    game.running = False
    game.quitApplication()
    lines, footer = screens[-1]
    assert lines == formatObituaryScreen(
        game.lastObituary, game.saveManager.data["lifetimeStats"]
    )
    assert footer is None


def test_the_obituary_screen_wraps_long_lines_to_the_window():
    line = "Apep the Coiled, " + "who ate and ate, " * 12 + "died of hubris."
    labels, panels = scene.obituaryScreenOverlay([line], "next", 500, 700)
    texts = [label.text for label in labels]
    assert len(texts) > 2
    assert texts[0].startswith("Apep") and "hubris." in texts[-2]
    assert all(len(text) * scene.OBITUARY_TEXT_SIZE <= 500 for text in texts)
    assert panels[0].width == 500 and panels[0].height == 700


def test_closing_the_window_on_a_death_records_only_the_run_that_died(monkeypatch):
    import builtins
    import strata_view.game as gameModule

    class Event:
        type = "quit"

    class Window:
        isWindow = True
        width, height = 900, 700

        class strata:
            EVENT_QUIT = "quit"

        def __init__(self):
            self.events = [Event()]

        def pollEvents(self):
            events, self.events = self.events, []
            return events

    game, _ = makeGame()
    game.renderer = Window()
    monkeypatch.setattr(game, "renderFrame", lambda present=True, now=None: None)
    monkeypatch.setattr(gameModule.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(gameModule, "OBITUARY_SCREEN_SECONDS", 0.0)
    monkeypatch.setattr(builtins, "quit", lambda: None)
    recorded = []
    record = game.recordCurrentRun
    monkeypatch.setattr(
        game,
        "recordCurrentRun",
        lambda cause, **kwargs: recorded.append(cause) or record(cause, **kwargs),
    )
    head = blockTheWayAhead(game)
    game.moveEntity(head, head.getDirection())  # the close arrives mid-hold
    assert not game.running
    game.quitApplication()
    assert recorded == ["collision"]  # not a "quit" for the unplayed new run


def test_the_hud_has_the_2d_windows_level_progress_bar():
    game, _ = makeGame()
    cells = len(game.environment.grid.getLocations())
    required = game.config.levelProgressPercentageRequired
    width, height = 900, 700
    for count, color in (
        (1, scene.PROGRESS_RED),
        (int(cells * required * 0.75), scene.PROGRESS_YELLOW),
        (cells, scene.PROGRESS_GREEN),
    ):
        game.snakeParts = [game.selectedSnakePart] * count
        labels, panels = scene.hudOverlay(game, width, height)
        backdrop, fill, goal = [
            p for p in panels if p.y == height - scene.PROGRESS_BAR_HEIGHT
        ]
        assert backdrop.width == width
        # the mark where the level ends
        assert goal.x + goal.width / 2 == pytest.approx(width * required)
        assert goal.color == scene.PROGRESS_GOAL_COLOR
        assert fill.width == pytest.approx(width * min(1.0, count / cells))
        assert fill.color == color
        text = "Progress {}%/{}%".format(int(count / cells * 100), int(required * 100))
        assert text in [label.text for label in labels]


def test_the_story_banner_is_wrapped_to_the_window_rather_than_cut():
    game, _ = makeGame()
    game.strataBanner = (
        "Apep enters The Sunken Grove. Mossy roots coil around still, black water."
    )
    labels, _ = scene.hudOverlay(game, 500, 700)
    lines = [  # the banner sits along the bottom; the HUD's lines along the top
        l.text for l in labels if l.pixelSize == scene.BANNER_SIZE and l.y > 350
    ]
    assert len(lines) > 1
    assert " ".join(lines) == game.strataBanner
    assert all(len(line) * scene.BANNER_SIZE <= 500 for line in lines)
    # above the controls line, which sits above the progress bar
    hint = [l for l in labels if l.text.startswith("Arrows")][0]
    assert max(l.y for l in labels if l.text in lines) < hint.y
    assert hint.y < 700 - scene.PROGRESS_BAR_HEIGHT
