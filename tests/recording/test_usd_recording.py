"""--record (recording/usd_recording.py). What UsdRecording hands the recorder
is checked against a stand-in usd_recorder module, so it runs everywhere; the
tests against real stages are skipped when the optional usd-recorder package
(requirements-record.txt) is not installed."""

import builtins
import sys
import types

import pytest

import ophidian
from food.food import Food
from lib.pyenvlib.entity import Entity
from ophidian import Ophidian, parseArguments
from powerup.powerup import PowerUp, PowerUpType
from recording.usd_recording import UsdRecording, kindOf
from snake.snakePart import SnakePart
from textui.textrenderer import TextRenderer


class _FakeRecorder:
    """Stands in for usd_recorder.Recorder, keeping what it is handed, so
    UsdRecording's own bookkeeping is checked where usd-recorder (Python 3.10
    or newer) is not installed."""

    def __init__(self, path, time_codes_per_second):
        self.path = path
        self.timeCodesPerSecond = time_codes_per_second
        self.frames = []
        self.closed = False

    def record(self, frame, entities, extras):
        self.frames.append((frame, entities, extras))

    def close(self):
        self.closed = True


@pytest.fixture
def fakeUsdRecorder(monkeypatch):
    module = types.ModuleType("usd_recorder")
    module.Recorder = _FakeRecorder
    monkeypatch.setitem(sys.modules, "usd_recorder", module)
    return module


def _makeGame(monkeypatch, tmp_path, recordPath=None):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True, recordPath=recordPath)


def _advance(game, ticks):
    """One tick the way both UI loops take it: the move, then endOfTick's
    bookkeeping (without its sleep)."""
    for _ in range(ticks):
        game.moveSelectedSnakePart()
        game.advanceTick()


def _entityPrims(stage):
    return [prim for prim in stage.Traverse() if prim.HasAttribute("recorder:id")]


def test_no_record_argument_records_nothing(tmp_path, monkeypatch):
    assert parseArguments([]).record is None
    game = _makeGame(monkeypatch, tmp_path)

    _advance(game, 3)

    assert game.recording is None
    assert list(tmp_path.glob("*.usda")) == []


def test_record_argument_takes_a_path():
    assert parseArguments(["--record", "run.usda"]).record == "run.usda"
    assert parseArguments(["--text-ui", "--record", "run.usda"]).text_ui is True


def test_without_usd_recorder_recording_explains_what_to_install(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "usd_recorder", None)

    assert not UsdRecording.isAvailable()
    with pytest.raises(RuntimeError, match="requirements-record.txt"):
        UsdRecording(str(tmp_path / "run.usda"))


def test_with_usd_recorder_importable_recording_is_available(fakeUsdRecorder):
    assert UsdRecording.isAvailable()


def test_the_recorder_writes_to_the_path_at_ten_time_codes_per_second(
    fakeUsdRecorder, tmp_path
):
    path = str(tmp_path / "run.usda")

    recording = UsdRecording(path)

    assert recording.recorder.path == path
    assert recording.recorder.timeCodesPerSecond == 10
    assert recording.getTicksRecorded() == 0


def test_kind_of_names_each_entity_on_the_board():
    game = types.SimpleNamespace(selectedSnakePart=SnakePart((0, 255, 0)))

    assert kindOf(game.selectedSnakePart, game) == "head"
    assert kindOf(SnakePart((0, 200, 0)), game) == "body"
    assert kindOf(Food((255, 0, 0)), game) == "food"
    assert kindOf(PowerUp(PowerUpType.SPEED), game) == "powerUp"
    assert kindOf(Entity("rock"), game) == "Entity"


def test_ids_are_numbered_in_the_order_entities_first_appear(fakeUsdRecorder):
    recording = UsdRecording("run.usda")
    first, second = Food((255, 0, 0)), Food((255, 0, 0))

    assert recording.recordedId(first) == 0
    assert recording.recordedId(second) == 1
    assert recording.recordedId(first) == 0


def test_record_tick_hands_every_entity_and_the_run_to_the_recorder(
    fakeUsdRecorder, tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path, recordPath=str(tmp_path / "run.usda"))
    game.score = 12.0
    recording = game.recording

    recording.recordTick(game)

    (frame, entities, extras) = recording.recorder.frames[0]
    assert frame == 0
    assert extras == {
        "level": game.level,
        "tick": game.tick,
        "length": len(game.snakeParts),
        "score": 12,
    }
    assert isinstance(extras["score"], int)
    onBoard = [
        (location, entity)
        for location in game.environment.getGrid().getLocations().values()
        for entity in location.getEntities().values()
    ]
    assert len(entities) == len(onBoard)
    for location, entity in onBoard:
        recorded = entities[recording.recordedId(entity)]
        assert recorded["position"] == (location.getX(), location.getY(), 0)
        assert recorded["color"] == tuple(c / 255 for c in entity.getColor())
        assert recorded["kind"] == kindOf(entity, game)


def test_an_entity_keeps_its_id_from_tick_to_tick(
    fakeUsdRecorder, tmp_path, monkeypatch
):
    game = _makeGame(monkeypatch, tmp_path, recordPath=str(tmp_path / "run.usda"))
    head = game.selectedSnakePart

    _advance(game, 2)

    frames = game.recording.recorder.frames
    assert [frame for frame, _, _ in frames] == [0, 1]
    headId = game.recording.recordedId(head)
    assert frames[0][1][headId]["kind"] == "head"
    assert frames[1][1][headId]["kind"] == "head"
    assert [extras["tick"] for _, _, extras in frames] == [0, 1]


def test_a_paused_tick_reaches_no_recorder(fakeUsdRecorder, tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path, recordPath=str(tmp_path / "run.usda"))
    _advance(game, 1)
    game.paused = True

    game.advanceTick()

    assert len(game.recording.recorder.frames) == 1
    assert game.recording.getTicksRecorded() == 1


def test_finish_recording_closes_once_and_reports_the_ticks(
    fakeUsdRecorder, tmp_path, monkeypatch, capsys
):
    path = str(tmp_path / "run.usda")
    game = _makeGame(monkeypatch, tmp_path, recordPath=path)
    _advance(game, 3)
    recorder = game.recording.recorder

    game.finishRecording()
    game.finishRecording()

    assert recorder.closed
    assert game.recording is None
    assert capsys.readouterr().out.count(f"Recorded 3 ticks to {path}") == 1


def test_each_tick_records_the_board(tmp_path, monkeypatch):
    pytest.importorskip("usd_recorder")
    from pxr import Usd, UsdGeom

    path = tmp_path / "run.usda"
    game = _makeGame(monkeypatch, tmp_path, recordPath=str(path))

    _advance(game, 3)
    headLocation = game.getLocation(game.selectedSnakePart)
    game.finishRecording()

    stage = Usd.Stage.Open(str(path))
    assert (stage.GetStartTimeCode(), stage.GetEndTimeCode()) == (0, 2)
    assert stage.GetTimeCodesPerSecond() == UsdRecording.TIME_CODES_PER_SECOND
    kinds = {}
    for prim in _entityPrims(stage):
        kinds.setdefault(prim.GetAttribute("extras:kind").Get(2), []).append(prim)
    assert len(kinds["head"]) == 1
    assert len(kinds.get("food", [])) + len(kinds.get("powerUp", [])) >= 1
    head = kinds["head"][0]
    assert tuple(head.GetAttribute("xformOp:translate").Get(2)) == (
        headLocation.getX(),
        headLocation.getY(),
        0,
    )
    colour = UsdGeom.Gprim(head.GetChild("geom")).GetDisplayColorAttr().Get(2)[0]
    assert tuple(round(c * 255) for c in colour) == tuple(
        game.selectedSnakePart.getColor()
    )
    world = stage.GetDefaultPrim()
    assert world.GetAttribute("extras:tick").Get(2) == 2
    assert world.GetAttribute("extras:level").Get(2) == game.level
    assert world.GetAttribute("extras:length").Get(2) == len(game.snakeParts)


def test_a_paused_frame_is_not_recorded(tmp_path, monkeypatch):
    pytest.importorskip("usd_recorder")
    game = _makeGame(monkeypatch, tmp_path, recordPath=str(tmp_path / "run.usda"))

    _advance(game, 2)
    game.paused = True
    game.advanceTick()

    assert game.recording.getTicksRecorded() == 2


def test_a_new_run_keeps_the_recording_going(tmp_path, monkeypatch):
    pytest.importorskip("usd_recorder")
    from pxr import Usd

    path = tmp_path / "run.usda"
    game = _makeGame(monkeypatch, tmp_path, recordPath=str(path))
    _advance(game, 2)
    firstHead = game.selectedSnakePart

    # a collision or a level change starts the run's tick counter again
    game.initialize()
    _advance(game, 2)
    game.finishRecording()

    stage = Usd.Stage.Open(str(path))
    assert (stage.GetStartTimeCode(), stage.GetEndTimeCode()) == (0, 3)
    world = stage.GetDefaultPrim()
    assert [world.GetAttribute("extras:tick").Get(t) for t in range(4)] == [0, 1, 0, 1]
    heads = [
        p for p in _entityPrims(stage) if p.GetAttribute("extras:kind").Get(3) == "head"
    ]
    assert len(heads) == 2
    first = [p for p in heads if p.GetAttribute("visibility").Get(1) == "inherited"]
    assert len(first) == 1
    # the first run's head is gone from the board once the new run starts
    assert first[0].GetAttribute("visibility").Get(2) == "invisible"
    assert firstHead is not game.selectedSnakePart


def test_quitting_writes_the_recording(tmp_path, monkeypatch):
    pytest.importorskip("usd_recorder")
    path = tmp_path / "run.usda"
    game = _makeGame(monkeypatch, tmp_path, recordPath=str(path))
    _advance(game, 2)
    monkeypatch.setattr(Ophidian, "printObituaryToConsole", lambda self: None)
    monkeypatch.setattr(Ophidian, "renderObituaryScreen", lambda self: None)
    monkeypatch.setattr(Ophidian, "displayStatsInConsole", lambda self: None)
    monkeypatch.setattr(ophidian, "quit", lambda: None, raising=False)
    monkeypatch.setattr(builtins, "quit", lambda: None, raising=False)

    game.quitApplication()

    assert path.read_text().startswith("#usda 1.0")
    assert game.recording is None
