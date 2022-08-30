#!/usr/bin/env sh
set -eux

pip install flit
flit install --symlink
