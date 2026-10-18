from food.food import Food
from powerup.powerup import PowerUp
from snake.snakePart import SnakePart

REQUIREMENTS_HINT = "pip install -r requirements-record.txt"


class UsdRecording:
    """Records a session's history as a time-sampled OpenUSD stage (.usda)
    with usd-recorder (https://github.com/Preponderous-Software/usd-recorder).

    Only used when the game is started with `--record <path>`. usd-recorder
    (and usd-core, which it depends on) is an optional dependency, imported
    only then; it needs Python 3.10 or newer.

    One time code per tick the game advances, counted across the whole
    session: a run's own tick counter starts again at 0 after a collision or
    a level change, so it is recorded alongside as the `tick` extra, with the
    level, length and score. Every entity on the board is recorded at its
    grid coordinates (x, y, 0) in the colour the game draws it with, and with
    its kind: `head`, `body`, `food` or `powerUp`.
    """

    TIME_CODES_PER_SECOND = 10

    @staticmethod
    def isAvailable():
        try:
            import usd_recorder  # noqa: F401
        except ImportError:
            return False
        return True

    def __init__(self, path):
        try:
            from usd_recorder import Recorder
        except ImportError as error:
            raise RuntimeError(
                "recording needs the optional usd-recorder package: "
                + REQUIREMENTS_HINT
            ) from error
        self.path = path
        self.recorder = Recorder(path, time_codes_per_second=self.TIME_CODES_PER_SECOND)
        # pyenvlib ids are UUIDs; the stage numbers entities in the order
        # they first appear
        self.recordedIds = {}
        self.frame = 0

    def getTicksRecorded(self):
        return self.frame

    def recordTick(self, game):
        """Records the board as it is at the end of the game's current tick."""
        entities = {}
        for location in game.environment.getGrid().getLocations().values():
            for entity in location.getEntities().values():
                entities[self.recordedId(entity)] = {
                    "position": (location.getX(), location.getY(), 0),
                    "color": tuple(channel / 255 for channel in entity.getColor()),
                    "kind": kindOf(entity, game),
                }
        self.recorder.record(
            self.frame,
            entities=entities,
            extras={
                "level": game.level,
                "tick": game.tick,
                "length": len(game.snakeParts),
                "score": int(game.score),
            },
        )
        self.frame += 1

    def close(self):
        """Writes the stage and returns its path."""
        self.recorder.close()
        return self.path

    def recordedId(self, entity):
        entityId = entity.getID()
        if entityId not in self.recordedIds:
            self.recordedIds[entityId] = len(self.recordedIds)
        return self.recordedIds[entityId]


def kindOf(entity, game):
    if entity is game.selectedSnakePart:
        return "head"
    if isinstance(entity, SnakePart):
        return "body"
    if isinstance(entity, PowerUp):
        return "powerUp"
    if isinstance(entity, Food):
        return "food"
    return type(entity).__name__
