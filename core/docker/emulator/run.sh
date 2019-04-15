#!/bin/bash
cd "$(dirname "$0")"
cd ..

export TREZOR_UDP_IP=0.0.0.0

source emu.sh
