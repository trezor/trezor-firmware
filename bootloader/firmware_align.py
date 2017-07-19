#!/usr/bin/env python
import sys
import os

fn = sys.argv[1]
fs = os.stat(fn).st_size
if fs > 32768:
	raise Exception('bootloader has to be smaller than 32768 bytes')
with open(fn, 'ab') as f:
	f.write(b'\xFF' * (32768 - fs))
	f.close()
