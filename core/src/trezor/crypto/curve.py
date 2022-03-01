from trezorcrypto import curve25519, ed25519, nist256p1, secp256k1  # noqa: F401
if False:
	from trezorcrypto import bip340
else:
	bip340 = object()