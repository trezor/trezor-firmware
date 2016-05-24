#!/usr/bin/env python2
bl = open('bl.bin').read()
fw = open('fw.bin').read()
combined = bl + fw[:256] + (32768-256)*'\x00' + fw[256:]

open('combined.bin', 'w').write(combined)

print 'bootloader : %d bytes' % len(bl)
print 'firmware   : %d bytes' % len(fw)
print 'combined   : %d bytes' % len(combined)
