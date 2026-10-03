import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from lib.trace_client import TraceClient
from reporting import usage
from reporting.usage import (
    APPLICATION,
    DEFAULT_ENDPOINT,
    DEFAULT_KEY,
    DETAILS_URL,
    FIRST_RUN_NOTICE,
    FIRST_RUN_NOTICE_OFF_BY_ENVIRONMENT,
    UNKNOWN_VERSION,
    createUsageReporter,
    defaultUsageReportingSettings,
    firstRunNotice,
    installIdFile,
    readVersion,
)


def _stubServer(received):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            received["path"] = self.path
            received["authorization"] = self.headers.get("Authorization")
            received["body"] = json.loads(self.rfile.read(length))
            self.send_response(201)
            self.send_header("Content-Length", "0")
            self.end_headers()
            received["arrived"].set()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_default_settings_are_on_and_point_at_the_production_service():
    settings = defaultUsageReportingSettings()
    assert settings == {
        "enabled": True,
        "endpoint": DEFAULT_ENDPOINT,
        "key": DEFAULT_KEY,
    }
    assert DEFAULT_ENDPOINT == "https://trace.danielstephenson.dev"
    assert DEFAULT_KEY.strip() == DEFAULT_KEY and DEFAULT_KEY


def test_default_settings_are_a_fresh_dict_each_time():
    # a shared dict would let one save's edits leak into the next test/save
    assert defaultUsageReportingSettings() is not defaultUsageReportingSettings()


def test_application_is_the_name_the_key_was_issued_for():
    assert APPLICATION == "ophidian"


def test_version_comes_from_version_txt_at_the_repository_root():
    assert os.path.basename(usage.VERSION_FILE) == "version.txt"
    with open(usage.VERSION_FILE) as f:
        expected = f.read().strip()
    assert expected, "version.txt is empty"
    assert readVersion() == expected


def test_missing_or_empty_version_file_means_an_unknown_version(tmp_path, monkeypatch):
    absent = os.path.join(tmp_path, "absent.txt")
    assert readVersion(absent) is None
    empty = tmp_path / "version.txt"
    empty.write_text("\n")
    assert readVersion(str(empty)) is None

    monkeypatch.setattr(usage, "VERSION_FILE", absent)
    assert readVersion() is None
    # the client requires a version; a missing file must not stop startup,
    # and the events say "unknown" rather than a made-up number
    received = {"arrived": threading.Event()}
    server = _stubServer(received)
    try:
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        reporter = createUsageReporter(
            {"enabled": True, "endpoint": endpoint, "key": "test-key"}
        )
        reporter.report("startup")
        assert received["arrived"].wait(5), "the startup event never arrived"
        reporter.close()
    finally:
        server.shutdown()
    assert received["body"]["tags"] == {
        "version": UNKNOWN_VERSION,
        "install": reporter.install_id,
    }
    assert UNKNOWN_VERSION == "unknown"


def test_disabled_settings_yield_a_reporter_that_sends_nothing():
    for settings in (
        None,
        "not a dict",
        {"enabled": False, "endpoint": DEFAULT_ENDPOINT, "key": "k"},
        {"enabled": "true", "endpoint": DEFAULT_ENDPOINT, "key": "k"},
        {"enabled": True, "endpoint": DEFAULT_ENDPOINT, "key": ""},
        {"enabled": True, "endpoint": DEFAULT_ENDPOINT, "key": None},
    ):
        reporter = createUsageReporter(settings)
        assert isinstance(reporter, TraceClient)
        assert reporter.enabled is False, settings
        reporter.report("startup")  # must be a harmless no-op
        reporter.close()


def test_enabled_settings_report_under_the_program_name_to_the_configured_endpoint():
    received = {"arrived": threading.Event()}
    server = _stubServer(received)
    try:
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        reporter = createUsageReporter(
            {"enabled": True, "endpoint": endpoint, "key": "test-key"},
            version="9.9.9",
        )
        assert reporter.enabled is True
        reporter.report("startup")
        assert received["arrived"].wait(5), "the startup event never arrived"
        reporter.close()
    finally:
        server.shutdown()

    assert received["path"] == "/api/metrics"
    assert received["authorization"] == "Bearer test-key"
    assert received["body"] == {
        "application": "ophidian",
        "name": "startup",
        "tags": {"version": "9.9.9", "install": reporter.install_id},
    }
    with open(installIdFile()) as f:
        assert f.readline().strip() == reporter.install_id


def test_every_event_carries_the_version_from_version_txt():
    received = {"arrived": threading.Event()}
    server = _stubServer(received)
    try:
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        reporter = createUsageReporter(
            {"enabled": True, "endpoint": endpoint, "key": "test-key"}
        )
        reporter.report("run-ended", tags={"cause": "quit"})
        assert received["arrived"].wait(5), "the run-ended event never arrived"
        reporter.close()
    finally:
        server.shutdown()

    assert received["body"] == {
        "application": "ophidian",
        "name": "run-ended",
        "tags": {
            "cause": "quit",
            "version": readVersion(),
            "install": reporter.install_id,
        },
    }


def test_the_installation_id_is_kept_under_the_user_data_dir_and_reused(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(usage.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    settings = {"enabled": True, "endpoint": DEFAULT_ENDPOINT, "key": "k"}
    first = createUsageReporter(settings)
    second = createUsageReporter(settings)
    first.close()
    second.close()
    path = tmp_path / "xdg" / "ophidian" / "trace-install-id"
    assert first.install_id and first.install_id == path.read_text().strip()
    assert second.install_id == first.install_id


def test_trace_install_id_wins_over_the_file(monkeypatch):
    monkeypatch.setenv("TRACE_INSTALL_ID", "pinned-id")
    reporter = createUsageReporter(
        {"enabled": True, "endpoint": DEFAULT_ENDPOINT, "key": "k"}
    )
    reporter.close()
    assert reporter.install_id == "pinned-id"
    assert not os.path.exists(installIdFile())


def test_no_installation_id_file_when_reporting_is_off(monkeypatch):
    createUsageReporter({"enabled": False, "endpoint": DEFAULT_ENDPOINT, "key": "k"})
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    createUsageReporter({"enabled": True, "endpoint": DEFAULT_ENDPOINT, "key": "k"})
    monkeypatch.delenv("DO_NOT_TRACK")
    monkeypatch.setenv("TRACE_USAGE_REPORTING", "off")
    createUsageReporter({"enabled": True, "endpoint": DEFAULT_ENDPOINT, "key": "k"})
    assert not os.path.exists(installIdFile())


def test_installation_id_file_follows_the_platform(monkeypatch):
    monkeypatch.setenv("HOME", "/h")
    monkeypatch.setenv("APPDATA", "/appdata")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(usage.sys, "platform", "linux")
    assert installIdFile() == os.path.join(
        "/h", ".local", "share", "ophidian", "trace-install-id"
    )
    monkeypatch.setattr(usage.sys, "platform", "darwin")
    assert installIdFile() == os.path.join(
        "/h", "Library", "Application Support", "ophidian", "trace-install-id"
    )
    monkeypatch.setattr(usage.sys, "platform", "win32")
    assert installIdFile() == os.path.join("/appdata", "ophidian", "trace-install-id")


def test_disabled_reason_says_why_the_reporter_sends_nothing():
    assert createUsageReporter(None).disabled_reason == "config"
    assert (
        createUsageReporter(
            {"enabled": False, "endpoint": DEFAULT_ENDPOINT, "key": "k"}
        ).disabled_reason
        == "config"
    )
    assert (
        createUsageReporter(
            {"enabled": True, "endpoint": DEFAULT_ENDPOINT, "key": ""}
        ).disabled_reason
        == "no key"
    )
    assert (
        createUsageReporter(
            {"enabled": True, "endpoint": DEFAULT_ENDPOINT, "key": "k"}
        ).disabled_reason
        is None
    )


def test_environment_opt_out_wins_over_an_enabled_save(monkeypatch):
    for variable, value in (("DO_NOT_TRACK", "1"), ("TRACE_USAGE_REPORTING", "off")):
        monkeypatch.delenv("DO_NOT_TRACK", raising=False)
        monkeypatch.delenv("TRACE_USAGE_REPORTING", raising=False)
        monkeypatch.setenv(variable, value)
        received = {"arrived": threading.Event()}
        server = _stubServer(received)
        try:
            endpoint = "http://127.0.0.1:%d" % server.server_address[1]
            reporter = createUsageReporter(
                {"enabled": True, "endpoint": endpoint, "key": "test-key"}
            )
            assert reporter.enabled is False, variable
            assert reporter.disabled_reason == "environment", variable
            reporter.report("startup")
            reporter.report("run-ended", tags={"cause": "quit"})
            reporter.close()
            assert not received["arrived"].wait(0.5), "%s=%s still sent an event" % (
                variable,
                value,
            )
        finally:
            server.shutdown()
        assert "body" not in received


def test_first_run_notice_is_one_line_and_names_every_switch():
    assert "\n" not in FIRST_RUN_NOTICE
    assert FIRST_RUN_NOTICE.startswith(
        "Usage reporting is on: ophidian sends a startup event"
    )
    assert "https://trace.danielstephenson.dev" in FIRST_RUN_NOTICE
    assert '"usageReporting": {"enabled": false} in save.json' in FIRST_RUN_NOTICE
    assert "TRACE_USAGE_REPORTING=off" in FIRST_RUN_NOTICE
    assert DETAILS_URL in FIRST_RUN_NOTICE
    assert DETAILS_URL == "https://github.com/Stephenson-Software/trace#usage-reporting"


def test_first_run_notice_says_off_when_the_environment_opted_out(monkeypatch):
    assert firstRunNotice() == FIRST_RUN_NOTICE
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    assert firstRunNotice() == FIRST_RUN_NOTICE_OFF_BY_ENVIRONMENT
    assert "\n" not in FIRST_RUN_NOTICE_OFF_BY_ENVIRONMENT
    assert FIRST_RUN_NOTICE_OFF_BY_ENVIRONMENT.startswith(
        "Usage reporting is off (environment)"
    )
    assert DETAILS_URL in FIRST_RUN_NOTICE_OFF_BY_ENVIRONMENT


def test_the_browser_build_never_reports_and_starts_no_thread(monkeypatch):
    # a pygbag build cannot run the client's sending thread, so even a block
    # that says on yields the no-op client there
    monkeypatch.setattr(usage.sys, "platform", "emscripten")
    threadsBefore = threading.active_count()

    reporter = createUsageReporter(defaultUsageReportingSettings())

    assert reporter.enabled is False
    assert threading.active_count() == threadsBefore
    reporter.report("startup")  # still returns at once and never raises
    assert firstRunNotice() == usage.FIRST_RUN_NOTICE_OFF_IN_BROWSER
