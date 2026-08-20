#!/bin/bash
# Usage: ./test.sh

resolvePython() {
    # pick an interpreter that meets the requirement in README.md, since
    # `python` is Python 2 on some systems and absent on others. PYTHON can be
    # set beforehand to override the choice - a virtualenv interpreter, say.
    if [ -n "$PYTHON" ]; then
        return
    fi
    for candidate in python3 python; do
        if command -v "$candidate" > /dev/null 2>&1 &&
            "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 8))' \
                > /dev/null 2>&1; then
            PYTHON="$candidate"
            return
        fi
    done
    echo "No Python 3.8 or newer interpreter found. Install one, or set PYTHON to the path of one."
    exit 1
}

resolvePython

# generate coverage file named "cov.xml"
"$PYTHON" -m pytest --verbose -vv --cov=src --cov-report=term-missing --cov-report=xml:cov.xml
