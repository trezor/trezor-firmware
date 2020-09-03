#!/usr/bin/env bash

if [ $# -ne 1 ]
  then
    echo "Usage: $0 [model]"
    exit 1
fi

nix-shell --run "pipenv run trezorctl list | grep '$1' | cut -d' ' -f1 | tr -d '\n'"
