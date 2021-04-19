#!/usr/bin/env bash

cd $(dirname "$0") || exit
towncrier build --draft --version unreleased
