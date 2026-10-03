import os
import sys

SRC_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"
)
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

import urllib.parse
import urllib.request

import pytest

from lib.trace_client import TraceClient
import ophidian


@pytest.fixture(autouse=True)
def _neverReportUsageFromTests(monkeypatch, tmp_path):
    """Keeps the suite off the production trace server.

    Reporting is on by default, so every Ophidian(...) a test builds would
    otherwise post a real startup event. Two layers: the game gets a no-op
    reporter (a test that wants to see what is reported swaps in its own
    recording one), and urllib refuses any host but loopback, which is where
    tests/lib/test_trace_client.py's stub server listens.
    """
    monkeypatch.setattr(
        ophidian, "createUsageReporter", lambda settings: TraceClient.disabled()
    )
    # The machine running the tests may itself have opted out of usage
    # reporting; every test starts from a clean environment and sets what
    # it needs.
    monkeypatch.delenv("TRACE_USAGE_REPORTING", raising=False)
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.delenv("TRACE_INSTALL_ID", raising=False)
    # An enabled reporter keeps its installation ID under the user data dir;
    # point every candidate for that dir into the test's own tmp_path.
    for variable in ("HOME", "USERPROFILE", "APPDATA", "XDG_DATA_HOME"):
        monkeypatch.setenv(variable, str(tmp_path / "userdata"))

    realUrlopen = urllib.request.urlopen

    def loopbackOnly(request, *args, **kwargs):
        url = (
            request.full_url if isinstance(request, urllib.request.Request) else request
        )
        host = urllib.parse.urlparse(url).hostname
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise RuntimeError("tests must not reach " + str(host))
        return realUrlopen(request, *args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", loopbackOnly)
