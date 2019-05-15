#!/bin/bash
cd "$(dirname "$0")"
cd ..

export SDL_VIDEODRIVER=dummy
export TREZOR_UDP_IP=0.0.0.0

source emu.sh
