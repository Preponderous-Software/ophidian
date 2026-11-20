"""Ophidian's board as a 3D scene, as plain data.

buildScene() reads a game's state and returns what to draw: boxes, spheres
and capsules on a raised board, screen text, a camera and a few lights. It
never imports Strata, so the mapping can be tested without a GPU; renderer.py
turns a Scene into Strata calls.

World axes follow the Primordial Rise Strata client: x runs along the grid's
columns, z along its rows (row 0 is the far edge, away from a camera that
sits south of the board), y is up. One cell is one world unit, and the board
is centred on the origin.
"""

import math
from controls.keybindings import (
    STRATA_CONTROLS_HINT,
    DIRECTION_DOWN,
    DIRECTION_LEFT,
    DIRECTION_RIGHT,
    DIRECTION_UP,
)
from food.food import Food
from powerup.powerup import PowerUp
from snake.snakePart import SnakePart

# Shape kinds, matching Strata's PRIMITIVE_* values without importing them.
CUBE, CAPSULE, CYLINDER, SPHERE = 0, 1, 2, 3

BED_TOP = 0.0  # y of the tiles' top face
TILE_HEIGHT = 0.18
SEGMENT_HEIGHT = 0.5
HEAD_HEIGHT = 0.62

# Unit steps on the board (dx, dz) for each direction.
DIRECTION_STEPS = {
    DIRECTION_UP: (0, -1),
    DIRECTION_LEFT: (-1, 0),
    DIRECTION_DOWN: (0, 1),
    DIRECTION_RIGHT: (1, 0),
}

# Moss tiles, as on the Primordial Rise board: dark enough that any snake
# colour (the default one is random) stands out against them.
TILE_LIGHT = (0.22, 0.38, 0.17)
TILE_DARK = (0.18, 0.32, 0.14)
FRAME_COLOR = (0.36, 0.22, 0.12)
COLLISION_TINT = (0.85, 0.18, 0.15)
EYE_WHITE = (0.97, 0.97, 0.95)
PUPIL = (0.05, 0.05, 0.06)
TEXT_COLOR = (0.97, 0.96, 0.92, 1.0)
DIM_TEXT_COLOR = (0.82, 0.80, 0.74, 1.0)
# How long a run shows the controls line before it hides (about 9 s at the
# default 0.15 s tick). It comes back whenever the game is paused.
CONTROLS_HINT_TICKS = 60
# small enough that the whole controls line fits a 900-pixel window
CONTROLS_HINT_SIZE = 11
CLEAR_COLOR = (0.10, 0.12, 0.16, 1.0)


# The scene description and the board/piece helpers are graphik's 3D grid
# view (preponderous.graphik.grid3d); this module only says what ophidian's
# board looks like and where its pieces stand.
from preponderous.graphik.grid3d import (  # noqa: E402  (re-exported names)
    Camera,
    GridBoard,
    Label,
    Light,
    Panel,
    Piece,
    PieceStyle,
    Scene,
    Shape,
    Theme,
    fitCamera,
    rgba,
    shade,
)
from preponderous.graphik.grid3d import cellCenter as _gridCellCenter  # noqa: E402
from preponderous.graphik.grid3d import rgb255 as rgb  # noqa: E402


def _headEyes(piece, x, z, baseY):
    """Two eyes on the face the head moves towards, one either side."""
    dx, dz = piece.facing
    sideX, sideZ = -dz, dx
    eyeY = baseY + HEAD_HEIGHT * 0.72
    shapes = []
    for side in (-1, 1):
        ex = x + dx * 0.30 + sideX * 0.2 * side
        ez = z + dz * 0.30 + sideZ * 0.2 * side
        shapes.append(
            Shape(SPHERE, (ex, eyeY, ez), (0.22, 0.22, 0.22), rgba(EYE_WHITE))
        )
        shapes.append(
            Shape(
                SPHERE,
                (ex + dx * 0.09, eyeY + 0.02, ez + dz * 0.09),
                (0.11, 0.11, 0.11),
                rgba(PUPIL),
            )
        )
    return shapes


# Ophidian's look. Piece colours come from the game (the snake's colour is
# random per run), so the styles' own colours are only defaults.
THEME = Theme(
    tile=TILE_LIGHT,
    alternate=TILE_DARK,
    tileHeight=TILE_HEIGHT,
    frame=FRAME_COLOR,
    pieces={
        "head": PieceStyle(SPHERE, height=HEAD_HEIGHT, size=0.92, extras=_headEyes),
        "body": PieceStyle(
            SPHERE, height=SEGMENT_HEIGHT, size=0.78, tones=(0.92, 0.78)
        ),
        "food": PieceStyle(SPHERE, height=0.56, size=0.56, lift=0.04, glow=(2.2, 1.6)),
        "powerup": PieceStyle(
            CAPSULE, height=0.7, size=0.42, lift=0.1, glow=(2.6, 2.4)
        ),
        "block": PieceStyle(CUBE, height=0.8, size=0.9),
    },
)


def cellCenter(x, y, columns, rows):
    """World (x, z) of the middle of grid cell (x, y)."""
    return _gridCellCenter(x, y, columns, rows)


def projectToScreen(camera, point, width, height):
    """Where a world point lands in the window, in pixels from the top-left,
    or None when it's behind the camera. The same right-handed look-at and
    OpenGL perspective the renderer asks Strata for (up is +y); Strata 0.7.0
    has no projection call of its own, so it's done here."""
    import math

    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    def cross(a, b):
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    def unit(a):
        length = math.sqrt(dot(a, a))
        return (a[0] / length, a[1] / length, a[2] / length)

    forward = unit(sub(camera.target, camera.eye))
    right = unit(cross(forward, (0.0, 1.0, 0.0)))
    up = cross(right, forward)
    offset = sub(point, camera.eye)
    depth = dot(offset, forward)
    if depth <= 0:
        return None
    focal = 1.0 / math.tan(math.radians(camera.fovDegrees) / 2.0)
    aspect = width / float(height)
    ndcX = focal / aspect * dot(offset, right) / depth
    ndcY = focal * dot(offset, up) / depth
    return ((ndcX + 1.0) / 2.0 * width, (1.0 - ndcY) / 2.0 * height)


def headScreenPosition(game, width, height):
    """The middle of the snake's head in the window, for aiming a tap."""
    grid = game.environment.getGrid()
    columns, rows = grid.getColumns(), grid.getRows()
    location = game.getLocation(game.selectedSnakePart)
    if location == -1:
        return None
    x, z = cellCenter(location.getX(), location.getY(), columns, rows)
    camera = cameraFor(columns, rows, width / float(height))
    return projectToScreen(camera, (x, BED_TOP + 0.4, z), width, height)


def cameraFor(columns, rows, aspect=1.0):
    """A camera south of the board, tilted down about 55 degrees, far enough
    back that the whole board and its frame fit (graphik's fitCamera)."""
    return fitCamera(columns, rows, aspect)


def boardShapes(columns, rows, collision=False):
    """The board's tiles and frame, tinted red after a collision."""
    return GridBoard(columns, rows, THEME).boardShapes(
        tint=COLLISION_TINT if collision else None
    )


def snakePieces(cells, direction, color):
    """grid3d pieces for a snake whose cells run head first, as grid
    (column, row) pairs: a tapering body, chained so neighbours are bridged,
    and a brighter head looking the way it moves."""
    pieces = []
    count = len(cells)
    facing = DIRECTION_STEPS.get(direction, (0, 1))
    for index, (column, row) in enumerate(cells):
        if index == 0:
            headColor = tuple(min(1.0, c * 1.15 + 0.06) for c in color[:3])
            style, scale, tint = "head", 1.0, headColor
        else:
            style = "body"
            scale = 1.0 - 0.35 * (index / max(1, count - 1))
            tint = tuple(color[:3])
        pieces.append(
            Piece(
                ("snake", index),
                column,
                row,
                style,
                scale=scale,
                color=tint,
                chain="snake",
                link=index,
                facing=facing,
            )
        )
    # body first, head (and its eyes) last, as the pre-graphik view drew them
    return pieces[1:] + pieces[:1]


def snakeShapes(cells, direction, color):
    """Shapes for a snake whose cells run head first, as world (x, z) pairs.

    Strata's primitives can't be rotated, so the body is built from spheres
    scaled into flattened ellipsoids: one per segment, tapering towards the
    tail, and a stretched one bridging each pair of neighbouring segments so
    the body reads as one creature. The head is larger and brighter, with
    two eyes looking the way it moves.
    """
    gridCells = [(round(x), round(z)) for x, z in cells]
    pieces = snakePieces(gridCells, direction, color)
    positions = {("snake", i): cell for i, cell in enumerate(cells)}
    shapes, _ = GridBoard(1, 1, THEME).pieceShapes(pieces, positions)
    return shapes


def pickupPiece(entity, column, row):
    """A food item, a power-up or another entity standing on a cell."""
    if isinstance(entity, PowerUp):
        style = "powerup"
    elif isinstance(entity, Food):
        style = "food"
    else:
        style = "block"
    return Piece(
        ("entity", id(entity)), column, row, style, color=rgb(entity.getColor())
    )


def entityCells(game):
    """(entity, gridX, gridY) for every entity on the board."""
    grid = game.environment.getGrid()
    found = []
    for locationId in grid.getLocations():
        location = grid.getLocation(locationId)
        for entityId in location.getEntities():
            found.append(
                (location.getEntity(entityId), location.getX(), location.getY())
            )
    return found


def snakeCells(game, columns, rows):
    """World (x, z) of each snake part, head first; parts not on the board are skipped."""
    grid = game.environment.getGrid()
    cells = []
    for part in game.snakeParts:
        locationId = part.getLocationID()
        if locationId is None:
            continue
        location = grid.getLocation(locationId)
        cells.append(cellCenter(location.getX(), location.getY(), columns, rows))
    return cells


def snakeGridCells(game):
    """Grid (column, row) of each snake part, head first; parts not on the
    board are skipped."""
    grid = game.environment.getGrid()
    cells = []
    for part in game.snakeParts:
        locationId = part.getLocationID()
        if locationId is None:
            continue
        location = grid.getLocation(locationId)
        cells.append((location.getX(), location.getY()))
    return cells


def fitText(text, width, pixelSize, margin=18):
    """Cut text to what fits across `width` pixels. Strata's built-in font
    is monospaced, about one pixel size wide per character."""
    room = max(4, int((width - 2 * margin) / pixelSize))
    return text if len(text) <= room else text[: room - 3] + "..."


def durationMeter(fractionRemaining, cells=10):
    """A power-up's time left as an ASCII bar, e.g. [######----]. ASCII
    because Strata's built-in font may not have the text UI's block
    characters."""
    filled = max(0, min(cells, round(fractionRemaining * cells)))
    return "[" + "#" * filled + "-" * (cells - filled) + "]"


def hudOverlay(game, width, height):
    """Screen text, and the panels behind it, for the game's current state."""
    shop = getattr(game, "strataShop", None)
    if shop is not None:
        # The shop replaces the HUD: Strata draws every panel before any
        # text, so HUD text would otherwise show through the shop's backdrop.
        return shop.overlay(width, height, Label, Panel, fitText)
    currency = game.saveManager.data.get("currency", 0)
    labels = [
        Label(game.getScoreLabel(), 18, 16, 26),
        Label(
            f"Level {game.level}  Length {len(game.snakeParts)}  Currency {currency}",
            18,
            50,
            18,
            DIM_TEXT_COLOR,
        ),
    ]
    # The same readout the 2D and text HUDs keep on screen: owned upgrades
    # in play, then each running power-up with its seconds and a meter.
    lineY = 78
    upgrades = game.getActiveUpgradesSummary()
    if upgrades:
        labels.append(
            Label(
                fitText(" | ".join(upgrades), width, 14), 18, lineY, 14, DIM_TEXT_COLOR
            )
        )
        lineY += 22
    for status in game.getActivePowerUpStatuses():
        labels.append(
            Label(
                "[{}] {}: {}s {}".format(
                    status["symbol"],
                    status["label"],
                    math.ceil(status["secondsRemaining"]),
                    durationMeter(status["fractionRemaining"]),
                ),
                18,
                lineY,
                14,
                rgba(rgb(status["color"])) if status.get("color") else TEXT_COLOR,
            )
        )
        lineY += 22
    panels = []
    showControls = game.paused or game.tick < CONTROLS_HINT_TICKS
    if showControls:
        labels.append(
            Label(
                fitText(STRATA_CONTROLS_HINT, width, CONTROLS_HINT_SIZE),
                18,
                height - 26,
                CONTROLS_HINT_SIZE,
                DIM_TEXT_COLOR,
            )
        )
    banner = getattr(game, "strataBanner", None)
    if banner:
        bannerY = height - 58 if showControls else height - 40
        labels.append(
            Label(fitText(banner, width, 18), 18, bannerY, 18, DIM_TEXT_COLOR)
        )
    if game.paused:
        text = "Paused (space to resume)"
        panels.append(
            Panel(
                width / 2 - 14 * len(text) / 2 - 20,
                height / 2 - 14,
                14 * len(text) + 40,
                52,
            )
        )
        labels.append(Label(text, width / 2 - 14 * len(text) / 2, height / 2, 26))
    overlay = [
        fitText(line, width, 18, margin=40)
        for line in (getattr(game, "strataOverlayLines", None) or [])
    ]
    if overlay:
        panels.append(
            Panel(20, 90, width - 40, 28 * len(overlay) + 24, (0.05, 0.03, 0.03, 0.78))
        )
        for index, line in enumerate(overlay):
            labels.append(Label(line, 40, 106 + 28 * index, 18))
    return labels, panels


def buildScene(game, width=900, height=700):
    """Everything to draw for the game's current state, as a graphik grid3d
    Scene: the board, the snake and pickups as pieces, and the HUD."""
    grid = game.environment.getGrid()
    columns, rows = grid.getColumns(), grid.getRows()
    pieces = [
        pickupPiece(entity, gx, gy)
        for entity, gx, gy in entityCells(game)
        if not isinstance(entity, SnakePart)
    ]
    head = game.selectedSnakePart
    pieces += snakePieces(
        snakeGridCells(game), head.getDirection(), rgb(head.getColor())
    )
    labels, panels = hudOverlay(game, width, height)
    return GridBoard(columns, rows, THEME).scene(
        pieces,
        labels=labels,
        panels=panels,
        aspect=width / float(height),
        tint=COLLISION_TINT if game.collision else None,
    )
