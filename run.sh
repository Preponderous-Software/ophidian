#!/bin/bash
# Usage: ./run.sh

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

getLatest() {
    # get the latest version of the code
    echo "Pulling latest version of code from GitHub"
    git pull
    echo ""
}

printBranchStatus() {
    # print the current branch
    echo "Current branch: $(git branch --show-current)"
    echo ""
}

printVersion() {
    # print the current version
    echo "Current version: $(cat version.txt)"
    echo ""
}

# checkDependencies() {
#     # check that dependencies are installed
#     echo "Checking dependencies"
#     if ! command -v python &> /dev/null
#     then
#         echo "Python could not be found. Download it from https://www.python.org/downloads/"
#         exit
#     fi
#     if ! command -v pip &> /dev/null
#     then
#         echo "Pip could not be found. Download it from https://pip.pypa.io/en/stable/installation/ or run 'python -m ensurepip' in a terminal"
#         exit
#     fi
#     pip install pygame --pre --quiet
#     pip install -r requirements.txt --quiet
#     echo ""
# }

runTests() {
    # run tests
    echo "Running tests"
    "$PYTHON" -m pytest
    echo ""
}

startProgram() {
    # start program
    echo "Starting program"
    "$PYTHON" src/ophidian.py > output.txt
}

# main
resolvePython
getLatest
printBranchStatus
printVersion
# checkDependencies
runTests
startProgram