#!/usr/bin/sh

# Calls Jlink script which configures T3W1 TZEN and SECBOOTADD0 option bytes
JLinkExe -device STM32U5G9ZJ -if SWD -speed 4000 -autoconnect 1 -jlinkscriptfile ob_config.JlinkScript
