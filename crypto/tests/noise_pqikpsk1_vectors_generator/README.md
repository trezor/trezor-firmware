# Test vector generator for Noise_pqIKpsk1_XWing_AESGCM_SHA256

Generates the cross-implementation test vectors used by
`test_noise_pqikpsk1_vectors` in `crypto/tests/test_check.c`.

The generator is built on [clatter](https://github.com/jmlepisto/clatter), an
independent Rust implementation of PQNoise (eprint 2022/539), extended with an
X-Wing KEM adapter (draft-connolly-cfrg-xwing-kem-10) based on RustCrypto
`ml-kem`, `x25519-dalek` and `sha3`.  The adapter self-checks against the
official X-Wing test vectors from Appendix C of the draft before generating
anything.

Since the whole cryptographic stack (Noise state machine, ML-KEM, X25519,
SHA-3, AES-GCM, SHA-256) is disjoint from the trezor-crypto one, a bit-exact
match of the handshake messages, handshake hash and transport ciphertexts
cross-validates both implementations.

Usage:

```
cargo run > vectors.txt
```

The output is formatted as C struct initializers to be pasted into the
`vectors[]` table in `test_noise_pqikpsk1_vectors`.
