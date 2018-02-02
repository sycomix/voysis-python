#!/bin/bash
# This script is a wrapper for tox to get around an issue with the shebang length
# https://github.com/pypa/pip/issues/1773
set -e

HERE=${PWD##*/} 
echo "Using workdir /tmp/${HERE}"
~/.local/bin/tox --workdir "/tmp/${HERE}" "$@"
exit $?
