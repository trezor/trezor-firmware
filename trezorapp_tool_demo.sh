#!/usr/bin/env bash
echo "*** This is trezorapp_tool demo ***"

TOOL="core/tools/trezor_core_tools/trezorapp_tool.py"
APPS_DIR="test_apps"

echo ">>> Create 10 apps of with app_ring=0"
$TOOL generate-apps -t 10 -r 0 -o $APPS_DIR

echo ">>> Create 20 apps of with app_ring=1"
$TOOL generate-apps -t 20 -r 1 -o $APPS_DIR

echo ">>> Create 40 apps of with app_ring=2"
$TOOL generate-apps -t 40 -r 2 -o $APPS_DIR

echo ">>> Build roopackets and app-proofs"
$TOOL build-rootpackets  $APPS_DIR -o

echo ">>> Add timestamps to roopackets"
$TOOL timestamp rootpacket_12.tmr
$TOOL timestamp rootpacket_0.tmr

echo ">>> Sign roopackets"
$TOOL sign rootpacket_0-timestamped.tmr
$TOOL sign rootpacket_12-timestamped.tmr

echo ">>> Verify signed rootpackets, should pass"
$TOOL verify rootpacket_0-timestamped-signed.tmr
$TOOL verify rootpacket_12-timestamped-signed.tmr

echo ">>> Verify unsigned rootpackets, should fail"
$TOOL verify rootpacket_0-timestamped.tmr
$TOOL verify rootpacket_12-timestamped.tmr

echo ">>> Show signed rootpackets"
$TOOL show rootpacket_0-timestamped-signed.tmr
$TOOL show rootpacket_12-timestamped-signed.tmr

echo ">>> Verify an app against its proof and the rootpacket root, should pass"
$TOOL verify-app $APPS_DIR/app_r2_00.tapp $APPS_DIR/app_r2_00.proof rootpacket_12-timestamped-signed.tmr