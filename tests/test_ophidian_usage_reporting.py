import json
import os

import ophidian
from ophidian import Ophidian
from progression import save
from reporting.usage import (
    FIRST_RUN_NOTICE,
    FIRST_RUN_NOTICE_OFF_BY_ENVIRONMENT,
    defaultUsageReportingSettings,
)
from textui.textrenderer import TextRenderer


class _RecordingReporter:
    """Stands in for the TraceClient: remembers what the game reports."""

    def __init__(self):
        self.reports = []
        self.closed = False

    def report(self, name, value=None, tags=None):
        self.reports.append((name, value, dict(tags or {})))

    def close(self, timeout=None):
        self.closed = True


def _makeGame(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # DEFAULT_SAVE_PATH was fixed at import time, so chdir alone would leave
    # SaveManager() reading and writing the repository's own save.json
    monkeypatch.setattr(save, "DEFAULT_SAVE_PATH", os.path.join(tmp_path, "save.json"))
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True)


def _recordReporters(monkeypatch):
    built = []

    def create(settings):
        built.append(settings)
        reporter = _RecordingReporter()
        built[-1] = (settings, reporter)
        return reporter

    monkeypatch.setattr(ophidian, "createUsageReporter", create)
    return built


def test_startup_is_reported_once(tmp_path, monkeypatch):
    built = _recordReporters(monkeypatch)

    game = _makeGame(monkeypatch, tmp_path)

    assert len(built) == 1
    settings, reporter = built[0]
    assert settings == defaultUsageReportingSettings()
    assert game.usageReporter is reporter
    # the version rides on every event, added by the client itself
    assert reporter.reports == [("startup", None, {})]


def test_reporter_is_built_from_the_saves_usage_reporting_block(tmp_path, monkeypatch):
    built = _recordReporters(monkeypatch)
    optedOut = dict(defaultUsageReportingSettings(), enabled=False)
    with open(os.path.join(tmp_path, "save.json"), "w") as f:
        json.dump({"usageReporting": optedOut}, f)

    _makeGame(monkeypatch, tmp_path)

    assert built[0][0] == optedOut


def test_every_run_end_is_reported_with_its_cause_only(tmp_path, monkeypatch):
    built = _recordReporters(monkeypatch)
    game = _makeGame(monkeypatch, tmp_path)
    reporter = built[0][1]
    monkeypatch.setattr(Ophidian, "printObituaryToConsole", lambda self: None)

    game.recordCurrentRun("collision", presentedByRenderer=True)
    game.restartRun()

    runEnded = [r for r in reporter.reports if r[0] == "run-ended"]
    assert runEnded == [
        ("run-ended", None, {"cause": "collision"}),
        ("run-ended", None, {"cause": "restart"}),
    ]
    # nothing that could identify a player or machine rides along
    for _, _, tags in reporter.reports:
        assert set(tags) <= {"version", "cause"}


def test_quitting_reports_the_run_and_closes_the_reporter(tmp_path, monkeypatch):
    built = _recordReporters(monkeypatch)
    game = _makeGame(monkeypatch, tmp_path)
    reporter = built[0][1]
    monkeypatch.setattr(Ophidian, "printObituaryToConsole", lambda self: None)
    monkeypatch.setattr(Ophidian, "renderObituaryScreen", lambda self: None)
    monkeypatch.setattr(Ophidian, "displayStatsInConsole", lambda self: None)
    monkeypatch.setattr(ophidian, "quit", lambda: None, raising=False)
    import builtins

    monkeypatch.setattr(builtins, "quit", lambda: None, raising=False)

    game.quitApplication()

    assert ("run-ended", None, {"cause": "quit"}) in reporter.reports
    assert reporter.closed is True


def test_first_run_notice_is_printed_once_and_then_saved_away(
    tmp_path, monkeypatch, capsys
):
    _makeGame(monkeypatch, tmp_path)
    first = capsys.readouterr().out
    assert first.count(FIRST_RUN_NOTICE) == 1

    with open(os.path.join(tmp_path, "save.json")) as f:
        saved = json.load(f)
    assert saved["usageReporting"] == defaultUsageReportingSettings()

    _makeGame(monkeypatch, tmp_path)
    second = capsys.readouterr().out
    assert FIRST_RUN_NOTICE not in second


def test_first_run_notice_also_shows_for_a_save_that_predates_it(
    tmp_path, monkeypatch, capsys
):
    with open(os.path.join(tmp_path, "save.json"), "w") as f:
        json.dump({"currency": 7}, f)

    game = _makeGame(monkeypatch, tmp_path)

    assert capsys.readouterr().out.count(FIRST_RUN_NOTICE) == 1
    assert game.saveManager.data["currency"] == 7
    with open(os.path.join(tmp_path, "save.json")) as f:
        assert json.load(f)["usageReporting"]["enabled"] is True


def test_an_opted_out_save_gets_no_notice(tmp_path, monkeypatch, capsys):
    with open(os.path.join(tmp_path, "save.json"), "w") as f:
        json.dump({"usageReporting": {"enabled": False}}, f)

    _makeGame(monkeypatch, tmp_path)

    assert FIRST_RUN_NOTICE not in capsys.readouterr().out


def test_first_run_under_an_environment_opt_out_says_reporting_is_off(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("TRACE_USAGE_REPORTING", "off")

    _makeGame(monkeypatch, tmp_path)

    out = capsys.readouterr().out
    assert FIRST_RUN_NOTICE not in out
    assert out.count(FIRST_RUN_NOTICE_OFF_BY_ENVIRONMENT) == 1
    # the environment never rewrites the save: the block is still the default
    with open(os.path.join(tmp_path, "save.json")) as f:
        assert json.load(f)["usageReporting"] == defaultUsageReportingSettings()
