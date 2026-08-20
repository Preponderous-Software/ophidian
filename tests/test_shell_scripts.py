"""The top-level shell scripts, as a fresh clone finds them (issue #135).

Each script documents itself as `./<name>.sh`, which only works when the
file carries a real shebang and the executable bit. `test.sh` is also the
project's only verification gate, so the interpreter it reaches for has to
be one that satisfies the requirement README states rather than whatever
`python` happens to mean on the machine.
"""

import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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


def test_every_script_opens_with_a_real_shebang():
    for name in SCRIPTS:
        assert _read(name).startswith("#!/bin/bash\n"), name


def test_every_script_is_executable():
    for name in SCRIPTS:
        assert os.access(os.path.join(REPO_ROOT, name), os.X_OK), name


def test_python_is_only_ever_run_through_the_resolved_interpreter():
    # the resolver names python3/python as candidates; every line that
    # actually runs something has to go through what it settled on.
    for name in PYTHON_CALLING_SCRIPTS:
        for line in _uncommentedLines(name):
            if not re.search(r"-m pytest|src/ophidian\.py", line):
                continue
            assert line.strip().startswith('"$PYTHON" '), (name, line)


def test_the_python_calling_scripts_resolve_an_interpreter_first():
    for name in PYTHON_CALLING_SCRIPTS:
        body = _read(name)
        assert "resolvePython()" in body, name
        assert re.search(r"^resolvePython$", body, re.MULTILINE), name


def test_interpreter_resolution_honors_the_python_override():
    for name in PYTHON_CALLING_SCRIPTS:
        assert 'if [ -n "$PYTHON" ]; then' in _read(name), name


def test_interpreter_resolution_enforces_the_documented_minimum_version():
    documented = re.search(r"Python (\d+)\.(\d+) or newer", _read("README.md"))
    assert documented is not None
    minimum = "(%s, %s)" % documented.groups()

    for name in PYTHON_CALLING_SCRIPTS:
        body = _read(name)
        assert "sys.exit(sys.version_info < %s)" % minimum in body, name
        assert "for candidate in python3 python; do" in body, name


def test_interpreter_resolution_fails_loudly_when_nothing_qualifies():
    for name in PYTHON_CALLING_SCRIPTS:
        body = _read(name)
        assert "No Python 3.8 or newer interpreter found." in body, name
        assert "exit 1" in body, name
