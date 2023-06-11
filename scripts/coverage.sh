#!/bin/sh
set -e
# coverage run --branch --context=ut --include="yellowbox_kraft/*" -m pytest tests/unittest "$@"
coverage run --branch --context=blackbox --include="yellowbox_kraft/*" -m pytest tests/blackbox "$@"
coverage html
coverage report -m
coverage xml