#!/usr/bin/python
from TrezorCrypto import HDNode

x = HDNode('xpub6BcjTvRCYD4VvFQ8whztSXhbNyhS56eTd5P3g9Zvd3zPEeUeL5CUqBYX8NSd1b6Thitr8bZcSnesmXZH7KerMcc4tUkenBShYCtQ1L8ebVe')

y = x.public_ckd(0)

for i in range(1000):
	z = y.public_ckd(i)
	print i, z.address()
