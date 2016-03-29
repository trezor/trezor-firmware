#!/bin/bash

cd `dirname $0`/src

../vendor/micropython/unix/micropython main.py
