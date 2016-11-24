#!/bin/bash

if [ -d python-trezor ]; then
    cd python-trezor ; git pull ; cd ..
else
    git clone https://github.com/trezor/python-trezor.git
fi

# run emulator

cd ../src
../vendor/micropython/unix/micropython -O0 main.py &
UPY_PID=$!

sleep 1

cd ../tests/python-trezor/tests
export PYTHONPATH=".."

error=0

for i in \
    test_msg_cipherkeyvalue.py \
    test_msg_estimatetxsize.py \
    test_msg_ethereum_getaddress.py \
    test_msg_getaddress.py \
    test_msg_getpublickey.py \
    test_msg_signmessage.py \
    test_msg_signtx.py \
    test_msg_verifymessage.py \
    ; do
        if ! python2 $i ; then
            error=1
            break
        fi
done

# kill emulator
kill $UPY_PID

exit $error
