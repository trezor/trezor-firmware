#!/bin/sh
DEVICE=${1:-/dev/ttyACM0}
socat -u $DEVICE,rawer - | ts "[%b %d %H:%M:%.S]"
