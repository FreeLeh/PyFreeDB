#!/usr/bin/env sh
autoflake --in-place --remove-all-unused-imports -r src/
autoflake --in-place --remove-all-unused-imports -r tests/
isort .
black .
