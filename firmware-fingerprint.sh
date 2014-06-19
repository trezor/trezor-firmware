#!/bin/bash

MAGIC=`head -c +4 $1`

if [ "x$MAGIC" != "xTRZR" ]; then
    echo "Missing magic characters 'TRZR', invalid firmware"
    exit 1
fi

echo "---------------------"
echo "Firmware fingerprint:"
tail -c +257 $1 | sha256sum
