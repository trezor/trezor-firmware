#!/bin/sh
for i in *.py; do
   echo
    ../../vendor/micropython/unix/micropython $i
done
