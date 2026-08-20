"""The top-level shell scripts, as a fresh clone finds them (issue #135).

Each script documents itself as `./<name>.sh`, which only works when the
file carries a real shebang and the executable bit. `test.sh` is also the
project's only verification gate, so the interpreter it reaches for has to
be one that satisfies the requirement README states rather than whatever
`python` happens to mean on the machine.

The interpreter resolver is exercised for real rather than pattern-matched:
its function body is lifted out of the script under test and run against
fake `python3`/`python` executables that report whatever version a case
needs. Running the scripts whole is not an option here - `test.sh` runs the
suite, and this file is in it.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# resolved up front, since the resolver cases hand bash a PATH holding
# nothing but their own fake interpreters. Absent bash there is nothing to
# say about a bash script, so those cases skip rather than error out.
BASH = shutil.which("bash")
requiresBash = pytest.mark.skipif(BASH is None, reason="bash is not installed")

SCRIPTS = ["test.sh", "run.sh", "format.sh"]
PYTHON_CALLING_SCRIPTS = ["test.sh", "run.sh"]


def _read(name):
    with open(os.path.join(REPO_ROOT, name)) as handle:
        return handle.read()


def _uncommentedLines(name):
    return [
        line
        for line in _read(name).splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _documentedMinimumVersion():
    documented = re.search(r"Python (\d+)\.(\d+) or newer", _read("README.md"))
    assert documented is not None, "README no longer states a minimum Python version"
    return tuple(int(part) for part in documented.groups())


def _writeExecutable(path, body):
    with open(path, "w") as handle:
        handle.write(body)
    os.chmod(path, 0o755)


def _fakeInterpreter(binDirectory, name, version):
    """An interpreter that answers the resolver's probe as `version` would."""
    _writeExecutable(
        os.path.join(binDirectory, name),
        '#!/bin/bash\nexec "%s" -c "import sys\nsys.version_info = %r\n$2"\n'
        % (sys.executable, version),
    )


def _runResolver(tmp_path, script, versions, override=None):
    """Run `script`'s resolver alone, seeing only the given fake interpreters.

    Returns the completed process; stdout is the interpreter it settled on.
    """
    resolver = re.search(r"^resolvePython\(\) \{$.*?^\}$", _read(script), re.M | re.S)
    assert resolver is not None, "%s no longer defines resolvePython" % script

    # a fresh directory per call, so a test may resolve more than once
    # without an earlier call's fake interpreters still being on PATH.
    caseDirectory = tempfile.mkdtemp(dir=str(tmp_path))
    binDirectory = os.path.join(caseDirectory, "bin")
    os.mkdir(binDirectory)
    for name, version in versions.items():
        _fakeInterpreter(binDirectory, name, version)

    harness = os.path.join(caseDirectory, "resolver.sh")
    _writeExecutable(harness, '%s\nresolvePython\necho "$PYTHON"\n' % resolver.group())

    environment = {"PATH": binDirectory}
    if override is not None:
        environment["PYTHON"] = override
    return subprocess.run(
        [BASH, harness], capture_output=True, text=True, env=environment
    )


def test_every_script_opens_with_a_real_shebang():
    for name in SCRIPTS:
        assert _read(name).startswith("#!/bin/bash\n"), name


def test_every_script_is_executable():
    for name in SCRIPTS:
        assert os.access(os.path.join(REPO_ROOT, name), os.X_OK), name


@requiresBash
def test_every_script_is_valid_bash():
    for name in SCRIPTS:
        checked = subprocess.run(
            [BASH, "-n", os.path.join(REPO_ROOT, name)],
            capture_output=True,
            text=True,
        )
        assert checked.returncode == 0, (name, checked.stderr)


def test_python_is_only_ever_run_through_the_resolved_interpreter():
    # the resolver names python3/python as candidates; every line that
    # actually runs something has to go through what it settled on.
    for name in PYTHON_CALLING_SCRIPTS:
        for line in _uncommentedLines(name):
            if not re.search(r"-m pytest|src/ophidian\.py", line):
                continue
            assert line.strip().startswith('"$PYTHON" '), (name, line)


def test_the_python_calling_scripts_resolve_before_running_anything():
    # a function definition takes effect without running, so the statement
    # that has to come first is the top-level call to resolvePython.
    for name in PYTHON_CALLING_SCRIPTS:
        statements = [
            line
            for line in _uncommentedLines(name)
            if not line.startswith((" ", "\t")) and line not in ("}",)
            if not line.endswith("{")
        ]
        assert statements[0] == "resolvePython", (name, statements)


@requiresBash
@pytest.mark.parametrize("script", PYTHON_CALLING_SCRIPTS)
def test_the_newest_qualifying_candidate_is_preferred(script, tmp_path):
    resolved = _runResolver(
        tmp_path, script, {"python3": (3, 10, 0), "python": (3, 12, 0)}
    )

    assert resolved.returncode == 0, resolved.stderr
    assert resolved.stdout.strip() == "python3"


@requiresBash
@pytest.mark.parametrize("script", PYTHON_CALLING_SCRIPTS)
def test_a_python_2_fallback_is_taken_only_when_it_qualifies(script, tmp_path):
    resolved = _runResolver(tmp_path, script, {"python": (2, 7, 18)})

    assert resolved.returncode == 1
    assert "No Python 3.8 or newer interpreter found." in resolved.stdout


@requiresBash
@pytest.mark.parametrize("script", PYTHON_CALLING_SCRIPTS)
def test_python_is_used_when_python3_is_absent(script, tmp_path):
    resolved = _runResolver(tmp_path, script, {"python": (3, 11, 0)})

    assert resolved.returncode == 0, resolved.stderr
    assert resolved.stdout.strip() == "python"


@requiresBash
@pytest.mark.parametrize("script", PYTHON_CALLING_SCRIPTS)
def test_the_documented_minimum_version_is_the_one_enforced(script, tmp_path):
    minimum = _documentedMinimumVersion()
    justBelow = (minimum[0], minimum[1] - 1, 0)

    rejected = _runResolver(tmp_path, script, {"python3": justBelow})
    accepted = _runResolver(tmp_path, script, {"python3": minimum + (0,)})

    assert rejected.returncode == 1, rejected.stdout
    assert accepted.returncode == 0, accepted.stderr
    assert accepted.stdout.strip() == "python3"


@requiresBash
@pytest.mark.parametrize("script", PYTHON_CALLING_SCRIPTS)
def test_a_preset_python_is_honored_without_probing(script, tmp_path):
    resolved = _runResolver(
        tmp_path, script, {"python3": (3, 10, 0)}, override="/opt/venv/bin/python"
    )

    assert resolved.returncode == 0, resolved.stderr
    assert resolved.stdout.strip() == "/opt/venv/bin/python"


@requiresBash
@pytest.mark.parametrize("script", PYTHON_CALLING_SCRIPTS)
def test_no_candidate_at_all_fails_with_an_actionable_message(script, tmp_path):
    resolved = _runResolver(tmp_path, script, {})

    assert resolved.returncode == 1
    assert "No Python 3.8 or newer interpreter found." in resolved.stdout
    assert "set PYTHON" in resolved.stdout
