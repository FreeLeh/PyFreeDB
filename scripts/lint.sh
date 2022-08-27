#!/usr/bin/env bash
set -eux

autoflake -c --remove-all-unused-imports -r src/
autoflake -c --remove-all-unused-imports -r tests/
isort --check .
black --check .
mypy src/
mypy tests/
