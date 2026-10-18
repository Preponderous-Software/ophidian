"""--record (recording/usd_recording.py) against real stages; skipped when the
optional usd-recorder package (requirements-record.txt) is not installed."""

import builtins
import sys

import pytest

import ophidian
from ophidian import Ophidian, parseArguments
from recording.usd_recording import UsdRecording
from textui.textrenderer import TextRenderer


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
