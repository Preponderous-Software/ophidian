"""Renders real Ophidian game states with the 3D Strata view, headless.

Plays the actual game for a number of ticks from a fixed seed, steering the
snake towards the nearest pickup (a simple autopilot so the snake survives
and grows), and saves a PNG of chosen ticks.

    python3 tools/strata_snapshot.py --out shots/ --ticks 0 25 60

Runs from a temporary working directory so the game's save.json is not
touched, and with usage reporting off.
"""

import argparse
import os
import random
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)
os.environ.setdefault("DO_NOT_TRACK", "1")
os.environ.setdefault("TRACE_USAGE_REPORTING", "off")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
if sys.platform.startswith("linux"):
    # Linux renders headless through EGL with no window. On Windows, Strata's
    # headless engine is a hidden SDL window, which the dummy driver can't make.
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def steerTowardsPickup(game):
    """Turn towards the nearest pickup, avoiding the snake's own body."""
    from controls.keybindings import (
        DIRECTION_DOWN,
        DIRECTION_LEFT,
        DIRECTION_RIGHT,
        DIRECTION_UP,
    )
    from snake.snakePart import SnakePart

    grid = game.environment.getGrid()
    head = grid.getLocation(game.selectedSnakePart.getLocationID())
    targets = []
    for locationId in grid.getLocations():
        location = grid.getLocation(locationId)
        for entityId in location.getEntities():
            if not isinstance(location.getEntity(entityId), SnakePart):
                targets.append(location)
    if not targets:
        return
    target = min(
        targets, key=lambda l: abs(l.getX() - head.getX()) + abs(l.getY() - head.getY())
    )
    steps = {
        DIRECTION_UP: (0, -1),
        DIRECTION_DOWN: (0, 1),
        DIRECTION_LEFT: (-1, 0),
        DIRECTION_RIGHT: (1, 0),
    }
    columns, rows = grid.getColumns(), grid.getRows()

    def free(direction):
        dx, dy = steps[direction]
        x, y = head.getX() + dx, head.getY() + dy
        if not (0 <= x < columns and 0 <= y < rows):
            return False
        location = grid.getLocationByCoordinates(x, y)  # -1 when there is none
        if location == -1:
            return False
        return not any(
            isinstance(location.getEntity(e), SnakePart) for e in location.getEntities()
        )

    def distanceAfter(direction):
        dx, dy = steps[direction]
        return abs(head.getX() + dx - target.getX()) + abs(
            head.getY() + dy - target.getY()
        )

    # the game never lets the snake reverse, even at length 1
    opposite = {
        DIRECTION_UP: DIRECTION_DOWN,
        DIRECTION_DOWN: DIRECTION_UP,
        DIRECTION_LEFT: DIRECTION_RIGHT,
        DIRECTION_RIGHT: DIRECTION_LEFT,
    }
    current = game.selectedSnakePart.getDirection()
    options = sorted(
        (d for d in steps if free(d) and d != opposite[current]), key=distanceAfter
    )
    if options:
        game.setDirectionIfAllowed(options[0])


def saveDeathScreens(game, renderer, out):
    """The two frames a death shows, as the game draws them: the red board
    with the obituary over it, then the obituary screen. The run is recorded
    into the temporary save, as a real death would be."""
    game.syncPieces(snap=True)  # every piece on its cell
    game.collision = True
    game.recordCurrentRun("collision", presentedByRenderer=True)
    game.renderCollisionFrame()
    path = os.path.join(out, "ophidian-death-1-collision.png")
    renderer.savePng(path)
    print(path)
    game.strataOverlayLines = None
    game.strataObituaryScreen = game.obituaryScreen()
    game.renderFrame(present=False)
    path = os.path.join(out, "ophidian-death-2-obituary.png")
    renderer.savePng(path)
    print(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="strata-shots")
    parser.add_argument("--ticks", type=int, nargs="+", default=[0, 30, 70])
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--height", type=int, default=700)
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument(
        "--slide",
        type=float,
        default=1.0,
        help="how far through its slide between ticks to draw each piece "
        "(0 = where it was a tick ago, 1 = on its cell)",
    )
    parser.add_argument(
        "--obituary",
        action="store_true",
        help="also save the death screens: the red collision frame and the "
        "obituary screen, for the run as it stands after the last tick",
    )
    args = parser.parse_args(argv)

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    random.seed(args.seed)
    os.chdir(tempfile.mkdtemp(prefix="ophidian-strata-"))

    from strata_view.game import StrataOphidian
    from strata_view.renderer import StrataRenderer

    renderer = StrataRenderer(args.width, args.height, window=False)
    try:
        # the game's clock runs one tick per tick played, as in the window,
        # so pieces slide as they do there however fast this loop runs
        clock = [0.0]
        game = StrataOphidian(renderer=renderer, clock=lambda: clock[0])
        if args.level != 1:
            game.level = args.level
            game.initialize()
        wanted = sorted(set(args.ticks))
        tick = 0
        for stop in wanted:
            while tick < stop and game.running:
                steerTowardsPickup(game)
                game.playTick()
                clock[0] += game.tickSeconds()
                tick += 1
            # the frame `--slide` of the way through the last tick's slide
            motion = game.strataMotion
            game.renderFrame(
                present=False, now=motion.startedAt + motion.tickSeconds * args.slide
            )
            path = os.path.join(out, "ophidian-tick-%03d.png" % stop)
            renderer.savePng(path)
            print(
                "%s  length %d  score %s  level %d"
                % (path, len(game.snakeParts), game.score, game.level)
            )
        if args.obituary:
            saveDeathScreens(game, renderer, out)
        times = game.strataFrameMs
        if times:
            print(
                "render ms per frame: first %.1f, median of the rest %.1f"
                % (times[0], sorted(times[1:] or times)[len(times[1:] or times) // 2])
            )
    finally:
        renderer.close()


if __name__ == "__main__":
    main()
