#!/bin/bash

if [ \! -d device_tests ]; then
    curl -s -L https://github.com/trezor/python-trezor/archive/master.tar.gz | tar -xvz --strip-components=2 python-trezor-master/tests/device_tests
fi

cd device_tests

pytest \
    -k-multisig \
    --ignore test_bip32_speed.py \
    --ignore test_cosi.py \
    --ignore test_debuglink.py \
    --ignore test_msg_applysettings.py \
    --ignore test_msg_changepin.py \
    --ignore test_msg_clearsession.py \
    --ignore test_msg_ethereum_signmessage.py \
    --ignore test_msg_ethereum_signtx.py \
    --ignore test_msg_ethereum_verifymessage.py \
    --ignore test_msg_getaddress_segwit_native.py \
    --ignore test_msg_getaddress_segwit.py \
    --ignore test_msg_getaddress_show.py \
    --ignore test_msg_loaddevice_xprv.py \
    --ignore test_msg_loaddevice.py \
    --ignore test_msg_nem_getaddress.py \
    --ignore test_msg_nem_signtx.py \
    --ignore test_msg_ping.py \
    --ignore test_msg_recoverydevice_dryrun.py \
    --ignore test_msg_recoverydevice.py \
    --ignore test_msg_resetdevice_skipbackup.py \
    --ignore test_msg_resetdevice.py \
    --ignore test_msg_signmessage_segwit.py \
    --ignore test_msg_signtx_bch.py \
    --ignore test_msg_signtx_segwit_native.py \
    --ignore test_msg_signtx_segwit.py \
    --ignore test_msg_signtx_zcash.py \
    --ignore test_msg_verifymessage_segwit.py \
    --ignore test_multisig_change.py \
    --ignore test_multisig.py \
    --ignore test_protect_call.py \
    --ignore test_protection_levels.py
