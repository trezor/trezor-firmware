#!/bin/bash

if [ \! -d device_tests ]; then
    curl -s -L https://github.com/trezor/python-trezor/archive/master.tar.gz | tar -xvz --strip-components=2 python-trezor-master/tests/device_tests
fi

# run emulator

cd ../src
../build/unix/micropython -O0 main.py >/dev/null &
UPY_PID=$!

sleep 1

cd ../tests/device_tests

error=0

: '
not passing:

    test_bip32_speed.py \
    test_debuglink.py \
    test_msg_applysettings.py \
    test_msg_clearsession.py \
    test_msg_changepin.py \
    test_msg_ethereum_signtx.py \
    test_msg_getaddress_show.py \
    test_msg_loaddevice_xprv.py \
    test_msg_ping.py \
    test_msg_resetdevice.py \
    test_msg_recoverydevice.py \
    test_msg_signtx_segwit.py \
    test_msg_signtx_zcash.py \
    test_multisig_change.py \
    test_multisig.py \
    test_protect_call.py \
    test_protection_levels.py \
'

for i in \
    test_basic.py \
    test_msg_cipherkeyvalue.py \
    test_msg_ethereum_getaddress.py \
    test_msg_getaddress.py \
    test_msg_getentropy.py \
    test_msg_getpublickey.py \
    test_msg_loaddevice.py \
    test_msg_signidentity.py \
    test_msg_signmessage.py \
    test_msg_signtx.py \
    test_msg_verifymessage.py \
    test_msg_wipedevice.py \
    test_op_return.py \
    test_zerosig.py \
    ; do

        if pytest -q $i ; then
           results+=("OK   $i")
        else
           results+=("FAIL $i")
           error=1
        fi

done

# kill emulator
kill $UPY_PID

echo
echo 'Summary:'
printf '%s\n' "${results[@]}"
exit $error
