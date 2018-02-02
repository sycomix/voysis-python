#!/bin/bash
# Removes the temporary dir created from tox.sh

HERE=${PWD##*/} 
echo "Removing workdir /tmp/${HERE}"
rm -rf "/tmp/${HERE}"
