#TREZOR Core API

Syntax used below is a valid Python function declaration with type hints defined in [PEP 0484](https://www.python.org/dev/peps/pep-0484/).

##trezor.crypto

###trezor.crypto.base58

@src/trezor/crypto/base58.py

###trezor.crypto.bip39

@extmod/modtrezorcrypto/modtrezorcrypto-bip39.h

###trezor.crypto.curve

####trezor.crypto.curve.ed25519

@extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h

####trezor.crypto.curve.nist256p1

@extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h

####trezor.crypto.curve.secp256k1

@extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h

###trezor.crypto.hashlib

####trezor.crypto.hashlib.ripemd160

@extmod/modtrezorcrypto/modtrezorcrypto-ripemd160.h

####trezor.crypto.hashlib.sha256

@extmod/modtrezorcrypto/modtrezorcrypto-sha256.h

####trezor.crypto.hashlib.sha512

@extmod/modtrezorcrypto/modtrezorcrypto-sha512.h

####trezor.crypto.hashlib.sha3_256

@extmod/modtrezorcrypto/modtrezorcrypto-sha3-256.h

####trezor.crypto.hashlib.sha3_512

@extmod/modtrezorcrypto/modtrezorcrypto-sha3-512.h

###trezor.crypto.hmac

@src/trezor/crypto/hmac.py

##trezor.msg

@extmod/modtrezormsg/modtrezormsg.c

##trezor.ui

@src/trezor/ui.py

###trezor.ui.display

@extmod/modtrezorui/modtrezorui-display.h

###trezor.utils

@extmod/modtrezorutils/modtrezorutils.c
