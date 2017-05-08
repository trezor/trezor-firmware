# trezor-crypto

[![Build Status](https://travis-ci.org/trezor/trezor-crypto.svg?branch=master)](https://travis-ci.org/trezor/trezor-crypto) [![gitter](https://badges.gitter.im/trezor/community.svg)](https://gitter.im/trezor/community)

Heavily optimized cryptography algorithms for embedded devices.

These include:
- AES/Rijndael encryption/decryption
- Big Number (256 bit) Arithmetics
- BIP32 Hierarchical Deterministic Wallets
- BIP39 Mnemonic code
- ECDSA signing/verifying (supports secp256k1 and nist256p1 curves,
  uses RFC6979 for deterministic signatures)
- ECDSA public key derivation
- Base58 address representation
- Ed25519 signing/verifying
- ECDH using secp256k1, nist256p1 and Curve25519
- HMAC-SHA256 and HMAC-SHA512
- PBKDF2
- RIPEMD-160
- SHA1
- SHA2-256/SHA2-512
- SHA3/Keccak
- BLAKE2s/BLAKE2b
- unit tests (using Check - check.sf.net; in tests.c)
- tests against OpenSSL (in test-openssl.c)

Distibuted under MIT License.

## Some parts of the library come from external sources:

- AES: https://github.com/BrianGladman/aes
- Base58: https://github.com/luke-jr/libbase58
- BLAKE2s/BLAKE2b: https://github.com/BLAKE2/BLAKE2
- RIPEMD-160: https://github.com/ARMmbed/mbedtls
- SHA1/SHA2: http://www.aarongifford.com/computers/sha.html
- SHA3: https://github.com/rhash/RHash
- Curve25519: https://github.com/agl/curve25519-donna
- Ed25519: https://github.com/floodyberry/ed25519-donna
