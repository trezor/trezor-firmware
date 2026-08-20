#!/bin/sh
# Capture the device debug console (VCP) to stdout, timestamped.
#
# The device drops off the USB bus on every power cycle and on every reboot
# (see `ci/hardware_tests/device/device.py`), which makes `socat` exit. Keep
# reconnecting so that a capture started *before* flashing survives the power
# cycles that follow and still records what the firmware prints on its first
# boot - including an RSOD, which is otherwise never captured anywhere.
DEVICE=${1:-/dev/ttyACM0}

while true; do
  [ -e "$DEVICE" ] && socat -u "$DEVICE",rawer - 2>/dev/null
  sleep 0.5
done | ts "[%b %d %H:%M:%.S]"
