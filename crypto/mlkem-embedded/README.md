# mlkem-embedded

Vendored copy of the ML-KEM implementation from the archived
[pq-code-package/mlkem-c-embedded](https://github.com/pq-code-package/mlkem-c-embedded)
project, commit `bfc7cf826aaec934cf3f6213592fbb6036be4018`, licensed under
Apache-2.0 or CC0-1.0 (see the LICENSE files in the subdirectories).

The implementation is optimized for a small memory footprint: the matrix A is
sampled on the fly and never stored, and temporary polynomials are aliased
aggressively, so the stack usage of every operation stays in the low
kilobytes. This is the reason this implementation is used instead of
mlkem-native, whose stack usage is an order of magnitude higher.

Only the portable C crypto core (`mlkem/` and `fips202/`) is vendored; the
upstream HAL, build system and tests are not.

Local modifications against the upstream commit:

1. `mlkem/indcpa.c`: the seed expansion in key generation computes
   `(rho, sigma) = G(d || k)` as required by the final FIPS 203 (Algorithm 13,
   K-PKE.KeyGen). Upstream implements the initial public draft, which computes
   `G(d)`. With this one-byte fix the implementation produces byte-identical
   keys, ciphertexts and shared secrets to mlkem-native v2.0.0 for ML-KEM-768
   and ML-KEM-512 (verified on fixed seeds, including implicit-rejection
   values).
2. `fips202/keccakf1600.c`: the broken endianness detection (which failed to
   build on non-ARM platforms and always selected the byte-wise path on ARM)
   is replaced by unconditional use of the endian-agnostic byte-wise path.
3. `mlkem/randombytes.h`: added; declares the `randombytes()` interface
   expected by the upstream code. The implementation is provided by the
   including compilation unit (see `crypto/mlkem_embedded.c`).
4. `mlkem/symmetric.h`, `mlkem/symmetric-shake.c`: the `fips202.h` include
   uses a relative path, so no extra include directory is needed.

The FIPS 203, Section 7.2 modulus check of encapsulation keys is intentionally
not part of the vendored code; it is implemented by the wrapper in
`crypto/mlkem_embedded.c`.
