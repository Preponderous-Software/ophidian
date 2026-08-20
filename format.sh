#!/bin/bash
# Usage: ./format.sh

# src/lib holds vendored copies of graphik and py_env_lib and is left alone by
# both tools (see issue #120). black reads its exclusion from pyproject.toml;
# autoflake has no config file support, so it is told here.
black src
black tests
autoflake --in-place --remove-all-unused-imports --remove-unused-variables --exclude lib -r src
autoflake --in-place --remove-all-unused-imports --remove-unused-variables -r tests
