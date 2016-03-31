#!/bin/bash
cd `dirname $0`/src

../vendor/micropython/unix/micropython -O0 -X heapsize=100000 main.py
