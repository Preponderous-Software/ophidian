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
# How far the body fades from the neck to the tip of the tail: a bright
# segment darkens by this much, a dark one (the Obsidian skin) lightens
# towards TAIL_LIGHT instead, so the gradient reads on the moss either way.
TAIL_FADE = 0.38
TAIL_LIGHT = (0.55, 0.56, 0.60)
DARK_LUMINANCE = 0.22
# A power-up's HUD line is written in the power-up's colour (as the 2D meter
# fills in it), lifted towards white until it is at least this bright, so a
# dark one (the speed boost's pure blue) still reads on the dark backdrop.
HUD_TEXT_MIN_LUMINANCE = 0.5
# The 2D window holds its obituary screen this long (Ophidian.renderObituaryScreen).
OBITUARY_SCREEN_SECONDS = 1.5
OBITUARY_TEXT_SIZE = 16
OBITUARY_LINE_HEIGHT = 24
OBITUARY_BACKDROP = (0.02, 0.02, 0.03, 0.94)
# The line the game prints when a run dies (Ophidian.moveEntity); the 3D
# window shows it over the red board.
COLLISION_CAPTION = "The ophidian collides with itself and ceases to be."
# The level-progress bar along the bottom, as in the 2D window (20 pixels
# there): red below half the share that ends the level, yellow below it,
# green once it's reached.
PROGRESS_BAR_HEIGHT = 16
PROGRESS_BACKDROP = (0.0, 0.0, 0.0, 0.85)
PROGRESS_RED = (1.0, 0.0, 0.0, 0.9)
PROGRESS_YELLOW = (1.0, 1.0, 0.0, 0.9)
PROGRESS_GREEN = (0.0, 1.0, 0.0, 0.9)
# the mark on the bar where the level ends
PROGRESS_GOAL_WIDTH = 4
PROGRESS_GOAL_COLOR = (1.0, 1.0, 1.0, 1.0)
BANNER_SIZE = 18
BANNER_LINE_HEIGHT = 24
# Below this width (a phone held upright, in the browser's 3D view) the HUD
# shrinks lines that would run off the window, gives the progress share a
# row of its own and wraps the controls line, rather than cutting text off.
NARROW_WIDTH = 560
SMALLEST_TEXT = 9
# how far HUD text keeps from the browser page's 2D/3D button
BUTTON_GAP = 8


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
    cellScreenPosition,
    centredLabel,
    fitCamera,
    fitText,
    projectToScreen,
    rgba,
    shade,
    wrapText,
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


FOOD_HEIGHT = 0.56
STEM_COLOR = (0.36, 0.22, 0.10)
LEAF_COLOR = (0.42, 0.85, 0.30)


def _foodStem(piece, x, z, baseY):
    """A stem and a leaf on top of a piece of food. A segment the food grows
    wears the food's colour (as in 2D), so without them the food on the board
    and a body that has eaten read as the same red spheres; with them the
    food reads as fruit at a glance."""
    top = baseY + FOOD_HEIGHT
    return [
        Shape(CYLINDER, (x, top + 0.07, z), (0.09, 0.24, 0.09), rgba(STEM_COLOR)),
        Shape(
            SPHERE, (x + 0.14, top + 0.08, z), (0.30, 0.08, 0.16), rgba(LEAF_COLOR)
        ),
    ]


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
        "food": PieceStyle(
            SPHERE,
            height=FOOD_HEIGHT,
            size=0.56,
            lift=0.04,
            glow=(2.2, 1.6),
            extras=_foodStem,
        ),
        "powerup": PieceStyle(
            CAPSULE, height=0.7, size=0.42, lift=0.1, glow=(2.6, 2.4)
        ),
        "block": PieceStyle(CUBE, height=0.8, size=0.9),
    },
)


def cellCenter(x, y, columns, rows):
    """World (x, z) of the middle of grid cell (x, y)."""
    return _gridCellCenter(x, y, columns, rows)


def headScreenPosition(game, width, height):
    """The middle of the snake's head in the window, for aiming a tap."""
    grid = game.environment.getGrid()
    columns, rows = grid.getColumns(), grid.getRows()
    location = game.getLocation(game.selectedSnakePart)
    if location == -1:
        return None
    camera = cameraFor(columns, rows, width / float(height))
    return cellScreenPosition(
        camera,
        GridBoard(columns, rows, THEME),
        location.getX(),
        location.getY(),
        width,
        height,
        y=BED_TOP + 0.4,
    )


def cameraFor(columns, rows, aspect=1.0):
    """A camera south of the board, tilted down about 55 degrees, far enough
    back that the whole board and its frame fit (graphik's fitCamera)."""
    return fitCamera(columns, rows, aspect)


def boardShapes(columns, rows, collision=False):
    """The board's tiles and frame, tinted red after a collision."""
    return GridBoard(columns, rows, THEME).boardShapes(
        tint=COLLISION_TINT if collision else None
    )


def luminance(color):
    r, g, b = color[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def readableOnDark(color, minimum=HUD_TEXT_MIN_LUMINANCE):
    """`color` (0-1 r, g, b) mixed with white just enough to reach `minimum`
    luminance, so it reads on the window's dark backdrop; a colour already
    that bright is left as it is. Its hue stays recognisable."""
    color = tuple(color[:3])
    have = luminance(color)
    if have >= minimum:
        return color
    amount = (minimum - have) / max(1e-6, 1.0 - have)
    return tuple(c + (1.0 - c) * amount for c in color)


def bodyShade(color, fraction):
    """A body segment's colour `fraction` (0 at the neck, 1 at the tip) of
    the way down the tail: the segment's own colour, fading so the body reads
    as running from the head to the tail. Bright colours darken; dark ones
    (the Obsidian skin) lighten instead, so the tail never sinks into the
    board."""
    fraction = max(0.0, min(1.0, fraction))
    amount = TAIL_FADE * fraction
    color = tuple(color[:3])
    if luminance(color) < DARK_LUMINANCE:
        return tuple(c + (light - c) * amount for c, light in zip(color, TAIL_LIGHT))
    return shade(color, 1.0 - amount)


def snakePieces(cells, direction, color, colors=None):
    """grid3d pieces for a snake whose cells run head first, as grid
    (column, row) pairs: a tapering body, chained so neighbours are bridged,
    and a brighter head looking the way it moves.

    `color` is the head's colour (the selected skin). `colors`, when given,
    is each part's own colour, head first, as the 2D window paints them: the
    body a run starts with wears the skin, and each segment grown since
    wears the colour of the food that grew it. Either way the body fades
    from the neck to the tail (bodyShade)."""
    pieces = []
    count = len(cells)
    facing = DIRECTION_STEPS.get(direction, (0, 1))
    for index, (column, row) in enumerate(cells):
        if index == 0:
            headColor = tuple(min(1.0, c * 1.15 + 0.06) for c in color[:3])
            style, scale, tint = "head", 1.0, headColor
        else:
            style = "body"
            fraction = index / max(1, count - 1)
            scale = 1.0 - 0.35 * fraction
            own = colors[index] if colors is not None else color
            # the neck in its full colour, the tip of the tail fully faded
            tint = bodyShade(own, (index - 1) / max(1, count - 2))
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
    # the entity's own id, not id(): a new pickup must never inherit an
    # eaten one's id (and slide over from where it stood)
    return Piece(
        ("entity", entity.getID()), column, row, style, color=rgb(entity.getColor())
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
    return [cell for cell, _ in snakeGridParts(game)]


def snakeGridParts(game):
    """((column, row), 0-1 colour) of each snake part, head first; parts not
    on the board are skipped."""
    grid = game.environment.getGrid()
    parts = []
    for part in game.snakeParts:
        locationId = part.getLocationID()
        if locationId is None:
            continue
        location = grid.getLocation(locationId)
        parts.append(((location.getX(), location.getY()), rgb(part.getColor())))
    return parts


def durationMeter(fractionRemaining, cells=10):
    """A power-up's time left as an ASCII bar, e.g. [######----]. ASCII
    because Strata's built-in font may not have the text UI's block
    characters."""
    filled = max(0, min(cells, round(fractionRemaining * cells)))
    return "[" + "#" * filled + "-" * (cells - filled) + "]"


def wrapToWindow(lines, width, pixelSize, margin=40):
    """Word-wrap lines to the window, as the 2D obituary screen does (issue
    #139: a cut line lost the ophidian's name or its cause of death).
    Strata's font is monospaced, one pixel size per character (graphik's
    wrapText measures it so)."""
    return wrapText(list(lines), max(pixelSize * 4, width - 2 * margin), pixelSize)


def obituaryScreenOverlay(lines, footer, width, height, keepClear=None):
    """The 3D obituary screen: the same lines as the 2D one (the obituary,
    then the lifetime chronicle), wrapped and centred on a dark backdrop
    over the whole window, and a footer saying what happens next. The
    lines stay below `keepClear` (the page's 2D/3D button), if given."""
    size, step = OBITUARY_TEXT_SIZE, OBITUARY_LINE_HEIGHT
    inset = keepClear[1] + keepClear[3] + BUTTON_GAP if keepClear else 0
    wrapped = wrapToWindow(lines, width, size)
    # the footer wraps too (a phone is narrower than the line)
    footerLines = wrapToWindow([footer], width, size) if footer else [""]
    room = max(1, int((height - inset - (2 + len(footerLines)) * step) / step))
    if len(wrapped) > room:
        wrapped = wrapped[: room - 1] + ["..."]
    footerLines = footerLines if footer else []
    shown = wrapped + ([""] + footerLines if footer else [])
    top = max(inset, height / 2 - len(shown) * step / 2)
    labels = []
    for index, line in enumerate(shown):
        if not line:
            continue
        isFooter = index >= len(shown) - len(footerLines)
        color = DIM_TEXT_COLOR if footer and isFooter else TEXT_COLOR
        # centred across the window, its top on the line
        labels.append(
            centredLabel(line, width / 2, top + index * step, size, color, rise=0)
        )
    return labels, [Panel(0, 0, width, height, OBITUARY_BACKDROP)]


def levelProgress(game):
    """(share of the board the snake fills, share that ends the level), as
    the 2D window's progress bar and the text UI's "Progress" line read it."""
    cells = len(game.environment.grid.getLocations())
    return len(game.snakeParts) / cells, game.config.levelProgressPercentageRequired


def progressColor(fraction, required):
    """The 2D progress bar's colour rule (Ophidian.runPygameFrames)."""
    if fraction < required / 2:
        return PROGRESS_RED
    if fraction < required:
        return PROGRESS_YELLOW
    return PROGRESS_GREEN


def progressOverlay(game, width, height):
    """The level-progress bar across the bottom of the window, as in 2D.
    The share itself is written at the top right (progressText), as the
    text UI prints it, where it reads on any bar colour."""
    fraction, required = levelProgress(game)
    top = height - PROGRESS_BAR_HEIGHT
    panels = [Panel(0, top, width, PROGRESS_BAR_HEIGHT, PROGRESS_BACKDROP)]
    filled = width * max(0.0, min(1.0, fraction))
    if filled > 0:
        panels.append(
            Panel(
                0, top, filled, PROGRESS_BAR_HEIGHT, progressColor(fraction, required)
            )
        )
    # where the level ends, so the bar shows how far there is to go (as 2D)
    goal = width * max(0.0, min(1.0, required))
    panels.append(
        Panel(
            goal - PROGRESS_GOAL_WIDTH / 2,
            top,
            PROGRESS_GOAL_WIDTH,
            PROGRESS_BAR_HEIGHT,
            PROGRESS_GOAL_COLOR,
        )
    )
    return [], panels


def progressText(game):
    fraction, required = levelProgress(game)
    return "Progress {}%/{}%".format(int(fraction * 100), int(round(required * 100)))


def bannerLines(banner, width):
    """The story banner, word-wrapped to the window rather than cut, so the
    whole line can be read (the 2D banner shows it whole too)."""
    return wrapToWindow([banner], width, BANNER_SIZE, margin=18)


def fitSize(text, width, pixelSize, margin=18, smallest=SMALLEST_TEXT):
    """The largest pixel size up to `pixelSize` at which `text` fits across
    `width` (Strata's font is one pixel size wide per character), but never
    below `smallest`."""
    room = (width - 2 * margin) / max(1, len(text))
    return max(smallest, min(pixelSize, int(room)))


def obituaryScreenLines(game):
    """(lines, footer) for the 3D obituary screen: the 2D screen's lines
    (formatObituaryScreen) and what happens next."""
    from progression.obituary import formatObituaryScreen

    lines = formatObituaryScreen(
        game.lastObituary, game.saveManager.data["lifetimeStats"]
    )
    if not game.running:
        footer = None  # the window is closing
    elif game.collision and game.config.restartUponCollision:
        footer = "A new run begins in a moment."
    elif game.collision:
        footer = "The run is over."
    else:
        footer = None
    return lines, footer


def overlapsArea(x, y, textWidth, textHeight, area, gap=BUTTON_GAP):
    """True when a box of text at (x, y) comes within `gap` of `area`
    ((x, y, width, height), the page's 2D/3D button), or never for None."""
    if area is None:
        return False
    ax, ay, aw, ah = area
    return (
        x < ax + aw + gap
        and x + textWidth > ax - gap
        and y < ay + ah + gap
        and y + textHeight > ay - gap
    )


def sizeBeside(text, x, y, pixelSize, area, smallest=SMALLEST_TEXT):
    """The pixel size, up to `pixelSize`, at which a line at (x, y) ends
    before `area` (the page's button), if it would otherwise run under it."""
    if not overlapsArea(x, y, pixelSize * len(text), pixelSize, area):
        return pixelSize
    room = area[0] - BUTTON_GAP - x
    return max(smallest, min(pixelSize, int(room / max(1, len(text)))))


def hudOverlay(game, width, height):
    """Screen text, and the panels behind it, for the game's current state.

    A game may set `strataControlsHint` to its own controls line (the
    browser's names swipes and taps and has no quit key), and
    `strataKeepClear` to the area (x, y, width, height) of a button over the
    view (the browser page's 2D/3D button), which the text then stays out
    from under."""
    keepClear = getattr(game, "strataKeepClear", None)
    screen = getattr(game, "strataObituaryScreen", None)
    if screen is not None:
        # replaces the HUD, as the 2D obituary screen replaces the board
        lines, footer = screen
        return obituaryScreenOverlay(lines, footer, width, height, keepClear)
    shop = getattr(game, "strataShop", None)
    if shop is not None:
        # The shop replaces the HUD: Strata draws every panel before any
        # text, so HUD text would otherwise show through the shop's backdrop.
        return shop.overlay(width, height, Label, Panel, fitText, keepClear)
    narrow = width < NARROW_WIDTH
    currency = game.saveManager.data.get("currency", 0)
    stats = f"Level {game.level}  Length {len(game.snakeParts)}  Currency {currency}"
    score = game.getScoreLabel()
    scoreSize = fitSize(score, width, 26) if narrow else 26
    statsSize = fitSize(stats, width, 18) if narrow else 18
    labels = [
        Label(score, 18, 16, sizeBeside(score, 18, 16, scoreSize, keepClear)),
        Label(
            stats,
            18,
            50,
            sizeBeside(stats, 18, 50, statsSize, keepClear),
            DIM_TEXT_COLOR,
        ),
    ]
    # the share of the board filled, beside the score: the number the
    # progress bar along the bottom draws, as the text UI prints it
    progress = progressText(game)
    lineY = 78
    if narrow:
        # no room beside the score on a phone: a row of its own
        labels.append(Label(progress, 18, lineY, 14, DIM_TEXT_COLOR))
        lineY += 22
    else:
        # its right edge at the window's margin, or left of the button
        right = width - 18
        if overlapsArea(
            right - 18 * len(progress), 22, 18 * len(progress), 18, keepClear
        ):
            right = keepClear[0] - BUTTON_GAP
        labels.append(
            Label(progress, right - 18 * len(progress), 22, 18, DIM_TEXT_COLOR)
        )
    # The same readout the 2D and text HUDs keep on screen: owned upgrades
    # in play, then each running power-up with its seconds and a meter.
    upgrades = game.getActiveUpgradesSummary()
    if upgrades and narrow:
        # one or more rows on a phone, rather than cut
        for line in _joinHintLines(upgrades, width - 36, 14):
            labels.append(Label(line, 18, lineY, 14, DIM_TEXT_COLOR))
            lineY += 22
    elif upgrades:
        labels.append(
            Label(
                fitText(" | ".join(upgrades), width, 14), 18, lineY, 14, DIM_TEXT_COLOR
            )
        )
        lineY += 22
    for status in game.getActivePowerUpStatuses():
        line = "[{}] {}: {}s {}".format(
            status["symbol"],
            status["label"],
            math.ceil(status["secondsRemaining"]),
            durationMeter(status["fractionRemaining"]),
        )
        labels.append(
            Label(
                line,
                18,
                lineY,
                fitSize(line, width, 14) if narrow else 14,
                (
                    rgba(readableOnDark(rgb(status["color"])))
                    if status.get("color")
                    else TEXT_COLOR
                ),
            )
        )
        lineY += 22
    progressLabels, panels = progressOverlay(game, width, height)
    labels += progressLabels
    # what sits above the progress bar, from the bottom up: the controls
    # line, then the story banner
    bottom = height - PROGRESS_BAR_HEIGHT - 6
    showControls = game.paused or game.tick < CONTROLS_HINT_TICKS
    if showControls:
        hint = getattr(game, "strataControlsHint", None) or STRATA_CONTROLS_HINT
        if narrow:
            # wrapped at its " | " breaks rather than cut, so every control
            # can be read on a phone
            hintLines = _joinHintLines(hint.split(" | "), width - 36)
        else:
            hintLines = [fitText(hint, width, CONTROLS_HINT_SIZE)]
        for line in reversed(hintLines):
            bottom -= 20
            labels.append(Label(line, 18, bottom, CONTROLS_HINT_SIZE, DIM_TEXT_COLOR))
    banner = getattr(game, "strataBanner", None)
    if banner:
        lines = bannerLines(banner, width)
        top = bottom - 8 - BANNER_LINE_HEIGHT * len(lines)
        for index, line in enumerate(lines):
            labels.append(
                Label(
                    line,
                    18,
                    top + BANNER_LINE_HEIGHT * index,
                    BANNER_SIZE,
                    DIM_TEXT_COLOR,
                )
            )
    if game.paused and narrow:
        text = "Paused (space to resume)"
        size = fitSize(text, width, 26, margin=30)
        textWidth = size * len(text)
        panels.append(
            Panel(width / 2 - textWidth / 2 - 12, height / 2 - 14, textWidth + 24, 52)
        )
        labels.append(Label(text, width / 2 - textWidth / 2, height / 2, size))
    elif game.paused:
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
    overlay = wrapToWindow(getattr(game, "strataOverlayLines", None) or [], width, 18)
    # below the HUD's lines (score, level, upgrades, running power-ups), so
    # it covers none of them
    top = max(90, lineY + 4)
    room = max(1, int((height - top - 60) / 28))
    if len(overlay) > room:
        overlay = overlay[: room - 1] + ["..."]
    if overlay:
        panels.append(
            Panel(20, top, width - 40, 28 * len(overlay) + 24, (0.05, 0.03, 0.03, 0.78))
        )
        for index, line in enumerate(overlay):
            labels.append(Label(line, 40, top + 16 + 28 * index, 18))
    return labels, panels


def _joinHintLines(parts, maxWidth, size=CONTROLS_HINT_SIZE):
    """Packs a line's parts (a control, an upgrade) back together with " | "
    into as few lines as fit across maxWidth at `size`."""
    lines = []
    for part in parts:
        candidate = part if not lines else lines[-1] + " | " + part
        if lines and len(candidate) * size <= maxWidth:
            lines[-1] = candidate
        else:
            lines.append(part)
    return lines


def boardPieces(game):
    """Every piece on the board this tick, as grid3d Pieces with ids that stay
    the same from tick to tick (so an Animator can slide them): the pickups,
    then the snake."""
    pieces = [
        pickupPiece(entity, gx, gy)
        for entity, gx, gy in entityCells(game)
        if not isinstance(entity, SnakePart)
    ]
    head = game.selectedSnakePart
    parts = snakeGridParts(game)
    pieces += snakePieces(
        [cell for cell, _ in parts],
        head.getDirection(),
        rgb(head.getColor()),
        colors=[color for _, color in parts],
    )
    return pieces


def buildScene(game, width=900, height=700, positions=None):
    """Everything to draw for the game's current state, as a graphik grid3d
    Scene: the board, the snake and pickups as pieces, and the HUD.
    `positions` maps piece ids to world (x, z) for this frame (a grid3d
    Animator's, sliding pieces between ticks); pieces without one stand on
    their cells."""
    grid = game.environment.getGrid()
    columns, rows = grid.getColumns(), grid.getRows()
    pieces = boardPieces(game)
    labels, panels = hudOverlay(game, width, height)
    return GridBoard(columns, rows, THEME).scene(
        pieces,
        positions=positions,
        labels=labels,
        panels=panels,
        aspect=width / float(height),
        tint=COLLISION_TINT if game.collision else None,
    )
