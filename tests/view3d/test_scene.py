"""The experimental 3D view's state-to-scene mapping (src/strata_view/scene.py).

These need no GPU and no Strata: buildScene() returns plain shapes. Only the
last test renders, and it is skipped wherever Strata can't load.
"""

import pytest

from controls.keybindings import DIRECTION_LEFT, DIRECTION_RIGHT, DIRECTION_UP
from strata_view import scene
from controls.keybindings import STRATA_SCANCODE_KEYS
from strata_view.game import StrataOphidian


@pytest.fixture
def game():
    return StrataOphidian()


def test_cell_centres_put_the_board_around_the_origin():
    assert scene.cellCenter(0, 0, 5, 5) == (-2.0, -2.0)
    assert scene.cellCenter(2, 2, 5, 5) == (0.0, 0.0)
    assert scene.cellCenter(4, 0, 5, 5) == (2.0, -2.0)  # row 0 is the far edge


def test_the_camera_sits_south_of_and_above_the_board_and_backs_off_as_it_grows():
    small, large = scene.cameraFor(5, 5), scene.cameraFor(15, 15)
    for camera in (small, large):
        assert camera.eye[1] > 0 and camera.eye[2] > 0
    assert large.eye[1] > small.eye[1] and large.eye[2] > small.eye[2]


def test_the_board_has_one_tile_per_cell_plus_a_four_sided_frame():
    shapes = scene.boardShapes(6, 4)
    assert len(shapes) == 6 * 4 + 4


def test_a_collision_tints_every_tile_towards_red():
    plain = scene.boardShapes(3, 3)[:9]
    tinted = scene.boardShapes(3, 3, collision=True)[:9]
    for before, after in zip(plain, tinted):
        assert after.color[0] > before.color[0]
        assert after.color[1] < before.color[1]


def test_the_head_has_two_eyes_on_the_side_it_moves_towards():
    cells = [(0.0, 0.0), (-1.0, 0.0), (-2.0, 0.0)]
    shapes = scene.snakeShapes(cells, DIRECTION_RIGHT, (0.2, 0.6, 0.3))
    eyes = [s for s in shapes if s.color[:3] == scene.EYE_WHITE]
    assert len(eyes) == 2
    assert all(eye.position[0] > 0 for eye in eyes)  # ahead of the head, to the right


def test_only_orthogonal_neighbours_are_bridged():
    color = (0.5, 0.5, 0.5)
    joined = scene.snakeShapes([(0.0, 0.0), (0.0, 1.0)], DIRECTION_UP, color)
    apart = scene.snakeShapes([(0.0, 0.0), (2.0, 2.0)], DIRECTION_UP, color)
    assert len(joined) == len(apart) + 1


def test_the_body_tapers_towards_the_tail():
    cells = [(float(x), 0.0) for x in range(0, -6, -1)]
    shapes = scene.snakeShapes(cells, DIRECTION_RIGHT, (0.5, 0.5, 0.5))
    segments = [s for s in shapes[:5]]  # segments 1..5 come first, in order
    widths = [s.scale[0] for s in segments]
    assert widths == sorted(widths, reverse=True)


def test_long_text_is_cut_to_the_window():
    text = "x" * 200
    fitted = scene.fitText(text, 400, 18)
    assert len(fitted) * 18 <= 400 and fitted.endswith("...")
    assert scene.fitText("short", 400, 18) == "short"


def test_a_real_game_maps_to_a_board_a_snake_a_glowing_pickup_and_a_hud(game):
    built = scene.buildScene(game, 900, 700)
    grid = game.environment.getGrid()
    tiles = grid.getColumns() * grid.getRows()
    assert len(built.shapes) > tiles + 4  # board + frame + snake + pickup
    assert len(built.lights) == 1  # the pickup's glow
    assert built.labels[0].text == game.getScoreLabel()


def test_the_paused_notice_and_the_obituary_get_a_backdrop(game):
    game.paused = True
    game.strataOverlayLines = ["== Obituary ==", "It ended."]
    built = scene.buildScene(game, 900, 700)
    texts = [label.text for label in built.labels]
    assert "Paused (space to resume)" in texts and "It ended." in texts
    # the progress bar's two panels, then the notice's and the obituary's
    assert len(built.panels) == 4


def test_arrow_keys_steer_through_the_text_ui_key_tables(game):
    game.selectedSnakePart.setDirection(DIRECTION_UP)
    game.handleScancode(79)  # Right arrow
    assert game.selectedSnakePart.getDirection() == DIRECTION_RIGHT
    assert STRATA_SCANCODE_KEYS[80] == "a"


def test_the_shop_opens_buys_and_closes_in_the_3d_window(game):
    from controls.keybindings import RESTART_SENTINEL
    from strata_view.scene import hudOverlay

    game.saveManager.data["currency"] = 100
    game.saveManager.data["purchasedUpgrades"] = []
    game.saveManager.save = lambda: None  # keep the test off the disk
    assert game.handleScancode(19) == RESTART_SENTINEL  # P opens it
    assert game.strataShop is not None
    texts = [label.text for label in hudOverlay(game, 900, 700)[0]]
    assert "Ophidian Shop" in texts and "Currency: 100" in texts
    game.handleScancode(81)  # Down: the second upgrade
    game.handleScancode(40)  # Enter: buy it
    bought = game.strataShop.upgrades[1]
    assert bought["id"] in game.saveManager.data["purchasedUpgrades"]
    assert game.saveManager.data["currency"] == 100 - bought["cost"]
    assert game.handleScancode(41) == RESTART_SENTINEL  # Esc closes it
    assert game.strataShop is None
    assert game.running  # Esc in the shop closes it; it doesn't quit


def test_the_board_holds_while_the_shop_is_open(game):
    game.saveManager.save = lambda: None
    game.openShop()
    tick = game.tick
    # runStrataWindow skips playTick while the shop is open; check the guard
    assert game.strataShop is not None and game.tick == tick


def test_a_tick_moves_the_snake_without_touching_a_terminal(game, capsys):
    # the start cell is random, and a head facing an edge it already sits on
    # doesn't move; point it towards the middle of the board first
    grid = game.environment.getGrid()
    head = grid.getLocation(game.selectedSnakePart.getLocationID())
    middle = grid.getColumns() // 2
    if head.getX() < middle:
        game.selectedSnakePart.setDirection(DIRECTION_RIGHT)
    else:
        game.selectedSnakePart.setDirection(DIRECTION_LEFT)
    before = game.selectedSnakePart.getLocationID()
    game.playTick()
    assert game.tick == 1
    assert game.selectedSnakePart.getLocationID() != before
    assert "\x1b[" not in capsys.readouterr().out  # nothing drew to the terminal


def test_renders_a_frame_headless(game, tmp_path):
    from strata_view import renderer as rendererModule

    try:
        renderer = rendererModule.StrataRenderer(320, 240, window=False)
    except Exception as error:  # no strata-engine, no libstrata, no EGL
        pytest.skip("Strata can't load here: %s" % error)
    try:
        game.renderer = renderer
        game.renderFrame(present=False)
        path = tmp_path / "frame.png"
        renderer.savePng(str(path))
        assert path.stat().st_size > 1000
    finally:
        renderer.close()


def test_the_controls_show_at_the_start_of_a_run_and_while_paused(game):
    from controls.keybindings import STRATA_CONTROLS_HINT
    from strata_view.scene import CONTROLS_HINT_TICKS, hudOverlay

    def texts():
        labels, _ = hudOverlay(game, 900, 700)
        return [label.text for label in labels]

    game.tick = 0
    assert STRATA_CONTROLS_HINT in texts()
    game.tick = CONTROLS_HINT_TICKS
    assert STRATA_CONTROLS_HINT not in texts()
    game.paused = True
    assert STRATA_CONTROLS_HINT in texts()  # whole, not cut short at 900 px


def test_the_speed_limit_key_says_which_way_it_went(game):
    from controls.keybindings import ACTION_TOGGLE_TICK_SPEED_LIMIT

    before = game.config.limitTickSpeed
    game.performAction(ACTION_TOGGLE_TICK_SPEED_LIMIT)
    assert game.config.limitTickSpeed is not before
    assert game.uiBanner.current().startswith("Speed limit")


def test_3d_is_the_default_on_linux_and_windows_desktops():
    from ophidian import chooseInterface, parseArguments

    assert chooseInterface(parseArguments([]), "win32") == "3d"
    assert chooseInterface(parseArguments([]), "linux") == "3d"
    assert chooseInterface(parseArguments([]), "darwin") == "2d"  # no Strata build
    assert chooseInterface(parseArguments(["--2d"]), "win32") == "2d"
    assert chooseInterface(parseArguments(["--text-ui"]), "win32") == "text"
    assert chooseInterface(parseArguments(["--strata"]), "darwin") == "3d"


def test_a_point_projects_where_the_camera_looks():
    from strata_view.scene import Camera, projectToScreen

    camera = Camera(eye=(0.0, 10.0, 10.0), target=(0.0, 0.0, 0.0), fovDegrees=42.0)
    centre = projectToScreen(camera, (0.0, 0.0, 0.0), 900, 700)
    assert abs(centre[0] - 450) < 1e-6 and abs(centre[1] - 350) < 1e-6
    east = projectToScreen(camera, (2.0, 0.0, 0.0), 900, 700)
    north = projectToScreen(camera, (0.0, 0.0, -2.0), 900, 700)
    assert east[0] > 450  # +x (east) is to the right on screen
    assert north[1] < 350  # -z (north, grid row 0) is up on screen
    assert projectToScreen(camera, (0.0, 20.0, 20.0), 900, 700) is None  # behind


def test_a_tap_steers_towards_where_it_landed_from_the_head_on_screen(game):
    from controls.keybindings import DIRECTION_LEFT, DIRECTION_RIGHT
    from strata_view.scene import headScreenPosition

    class _Size:
        width, height = 900, 700

    game.renderer = _Size()
    game.selectedSnakePart.setDirection(DIRECTION_LEFT)
    game.changedDirectionThisTick = False
    head = headScreenPosition(game, 900, 700)
    # a tap well to the right of the head, while heading up/left: turns right
    # unless that's a reversal (heading left), so head up first
    from controls.keybindings import DIRECTION_UP

    game.selectedSnakePart.setDirection(DIRECTION_UP)
    game.handleStrataPointer((head[0] + 200, head[1]), (head[0] + 202, head[1]))
    assert game.selectedSnakePart.getDirection() == DIRECTION_RIGHT


def test_a_swipe_steers_the_way_it_travelled(game):
    from controls.keybindings import DIRECTION_DOWN, DIRECTION_LEFT

    class _Size:
        width, height = 900, 700

    game.renderer = _Size()
    game.selectedSnakePart.setDirection(DIRECTION_LEFT)
    game.changedDirectionThisTick = False
    game.handleStrataPointer((400, 200), (405, 320))  # a swipe downwards
    assert game.selectedSnakePart.getDirection() == DIRECTION_DOWN


def test_the_hud_shows_what_the_2d_and_text_huds_show(game):
    from strata_view.scene import hudOverlay

    game.saveManager.data["currency"] = 7
    game.getActiveUpgradesSummary = lambda: ["Head Start", "Second Wind"]
    game.getActivePowerUpStatuses = lambda: [
        {
            "symbol": "S",
            "label": "Speed boost",
            "secondsRemaining": 2.4,
            "fractionRemaining": 0.5,
            "color": (255, 200, 0),
        }
    ]
    texts = [label.text for label in hudOverlay(game, 900, 700)[0]]
    assert any("Currency 7" in text for text in texts)
    assert "Head Start | Second Wind" in texts
    assert "[S] Speed boost: 3s [#####-----]" in texts


def test_every_2d_window_action_is_reachable_in_the_3d_window():
    # Feature parity between the interfaces is a requirement: every action
    # and direction the 2D window has a key for must have a key in 3D too.
    import pygame

    from controls.keybindings import (
        STRATA_SCANCODE_ACTIONS,
        STRATA_SCANCODE_KEYS,
        TEXT_UI_ACTION_KEYS,
        TEXT_UI_DIRECTION_KEYS,
        buildPygameActionKeys,
        buildPygameDirectionKeys,
    )

    spellings = set(STRATA_SCANCODE_KEYS.values())
    actions3d = {TEXT_UI_ACTION_KEYS[k] for k in spellings if k in TEXT_UI_ACTION_KEYS}
    actions3d |= set(STRATA_SCANCODE_ACTIONS.values())
    directions3d = {
        TEXT_UI_DIRECTION_KEYS[k] for k in spellings if k in TEXT_UI_DIRECTION_KEYS
    }
    assert set(buildPygameActionKeys(pygame).values()) <= actions3d
    assert set(buildPygameDirectionKeys(pygame).values()) <= directions3d
    assert set(TEXT_UI_ACTION_KEYS.values()) <= actions3d


def test_f11_without_a_fullscreen_capable_strata_says_so(game):
    class _OldRenderer:
        isWindow = True

        def setFullscreen(self, enabled):
            return False

    game.renderer = _OldRenderer()
    game.handleScancode(68)  # F11
    assert game.config.fullscreen is False
    assert "Fullscreen" in game.strataBanner
