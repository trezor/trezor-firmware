#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Please provide filename as argument"
    exit 1
fi

MAGIC=`head -c +4 $1`

if [ "x$MAGIC" != "xTRZR" ]; then
    echo "Missing magic characters 'TRZR', invalid firmware"
    exit 1
fi

echo "---------------------"
echo "Firmware fingerprint:"
tail -c +257 $1 | sha256sum
