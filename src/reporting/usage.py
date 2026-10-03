import os
import sys

from lib.trace_client import TraceClient, environment_opts_out

# @author Daniel McCoy Stephenson
# @since September 11th, 2026

# The name this program's key was issued for. It is the `application` field
# of every event, and the trace server rejects a key used under any other.
APPLICATION = "ophidian"

DEFAULT_ENDPOINT = "https://trace.danielstephenson.dev"

# Bundled with the game the way a plugin bundles its key in config.yml: it
# only lets the game post usage events under its own name, nothing else.
DEFAULT_KEY = "P2kWGUhAW4-5LIvQ8L0P8qs3unOPXTulkyikLGpsulI"

# version.txt at the repository root is what run.sh prints as the current
# version, so it is the version every event carries too.
VERSION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "version.txt",
)

# Where what is sent, what is not, and every opt-out are written up.
DETAILS_URL = "https://github.com/Stephenson-Software/trace#usage-reporting"

# Shown once, the first time the game starts with a save that predates the
# usageReporting block (or with no save at all); SaveManager then writes the
# block so it is never shown again. Printed rather than queued on the banner:
# the banner is a single 30px line and this would not fit.
FIRST_RUN_NOTICE = (
    "Usage reporting is on: ophidian sends a startup event (program name and "
    "version) and a run-ended event (how the run ended and the version), each "
    "with a random installation ID, to "
    "https://trace.danielstephenson.dev - nothing about you. "
    'Turn it off with "usageReporting": {"enabled": false} in save.json, or '
    "for every trace-reporting program with the environment variable "
    "TRACE_USAGE_REPORTING=off. Details: " + DETAILS_URL
)

# What the first run says instead when TRACE_USAGE_REPORTING=off or
# DO_NOT_TRACK=1 is already set: the save still gets its block, but claiming
# reporting is on would be untrue.
FIRST_RUN_NOTICE_OFF_BY_ENVIRONMENT = (
    "Usage reporting is off (environment). Details: " + DETAILS_URL
)


# What the first run says in the browser build, which never reports.
FIRST_RUN_NOTICE_OFF_IN_BROWSER = (
    "Usage reporting is off in the browser build. Details: " + DETAILS_URL
)


def runningInBrowser():
    """True for a pygbag build running in a web browser. The trace client
    sends from a thread of its own, and a pygbag build has no threads, so
    nothing is reported from there at all."""
    return sys.platform == "emscripten"


def firstRunNotice():
    """The line the first run prints: FIRST_RUN_NOTICE, unless the
    environment has already opted out of usage reporting, or this is the
    browser build, which never reports."""
    if runningInBrowser():
        return FIRST_RUN_NOTICE_OFF_IN_BROWSER
    if environment_opts_out():
        return FIRST_RUN_NOTICE_OFF_BY_ENVIRONMENT
    return FIRST_RUN_NOTICE


def defaultUsageReportingSettings():
    """The usageReporting block a fresh save.json gets. Reporting is on by
    default; the block is where a player turns it off."""
    return {
        "enabled": True,
        "endpoint": DEFAULT_ENDPOINT,
        "key": DEFAULT_KEY,
    }


def installIdFile():
    """Where this installation's random ID (the tag ``install`` on every
    event) is kept: ``<user data dir>/ophidian/trace-install-id``, the user
    data dir being %APPDATA% on Windows, ~/Library/Application Support on
    macOS and $XDG_DATA_HOME (or ~/.local/share) elsewhere. The client only
    reads or creates it when reporting is on; deleting it resets the ID."""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", "").strip() or os.path.join(
            home, "AppData", "Roaming"
        )
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", "").strip() or os.path.join(
            home, ".local", "share"
        )
    return os.path.join(base, APPLICATION.lower(), "trace-install-id")


# What every event carries as its version when version.txt is missing or
# empty: the client requires a non-blank version, and a missing file must
# never stop the game from starting.
UNKNOWN_VERSION = "unknown"


def readVersion(path=None):
    """The game's version as version.txt states it, or None if the file is
    missing or empty."""
    try:
        with open(path or VERSION_FILE, "r") as f:
            version = f.read().strip()
    except OSError:
        return None
    return version or None


def createUsageReporter(settings, version=None):
    """Builds the client the game reports through, from the usageReporting
    block of the save data. Every event it sends carries ``version`` (by
    default the one in version.txt, or UNKNOWN_VERSION without one) as the
    tag ``version``, and a random installation ID as the tag ``install``:
    the TRACE_INSTALL_ID environment variable when set, otherwise the one
    kept in installIdFile(). The client resolves both only after its own
    opt-out checks, so a disabled reporter never creates the file.

    Every path through here yields a client whose report() returns at once
    and never raises, so nothing about reporting can stop a run: a block
    that is missing, malformed, disabled, or without a key gives the
    no-op client.

    The client is always built through TraceClient, even when the block
    says off, because the client checks the TRACE_USAGE_REPORTING and
    DO_NOT_TRACK environment variables before anything in the block and
    records why it is off in disabled_reason ("environment", "config" or
    "no key").

    The browser build always gets the no-op client (runningInBrowser).
    """
    if runningInBrowser():
        # before TraceClient is built at all: an enabled client would start
        # its sending thread, which a pygbag build cannot run
        return TraceClient.disabled()
    if not isinstance(settings, dict):
        settings = {}
        enabled = False
    else:
        enabled = settings.get("enabled", True) is True
    endpoint = settings.get("endpoint") or DEFAULT_ENDPOINT
    if not isinstance(endpoint, str):
        endpoint, enabled = DEFAULT_ENDPOINT, False
    key = settings.get("key")
    if not isinstance(key, str):
        key = None
    if not isinstance(version, str) or not version.strip():
        version = readVersion() or UNKNOWN_VERSION
    try:
        return TraceClient(
            endpoint,
            APPLICATION,
            version,
            key=key,
            enabled=enabled,
            install_id=os.environ.get("TRACE_INSTALL_ID"),
            install_id_file=installIdFile(),
        )
    except ValueError:
        return TraceClient.disabled()
