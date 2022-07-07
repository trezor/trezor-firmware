/// Trezor Crypto headers, implemented in `trezor-crypto-lib`, included from rust project.

#ifndef TREZOR_CRYPTO_ED25519_H
#define TREZOR_CRYPTO_ED25519_H

#include <stdint.h>
#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef unsigned char ed25519_signature[64];
typedef unsigned char ed25519_public_key[32];
typedef unsigned char ed25519_secret_key[32];

typedef unsigned char curved25519_key[32];

typedef unsigned char ed25519_cosi_signature[32];


// Ed25519 standard functions (Sha2_512)
void ed25519_publickey(const ed25519_secret_key sk, ed25519_public_key pk);

int ed25519_sign_open(const unsigned char *m, size_t mlen, const ed25519_public_key pk, const ed25519_signature RS);

void ed25519_sign(const unsigned char *m, size_t mlen, const ed25519_secret_key sk, ed25519_signature RS);

void curved25519_scalarmult_basepoint(ed25519_public_key res, const ed25519_secret_key sk);


// Extensions, ported from trezor donna

/// Derive extended public key from secret key
void ed25519_publickey_ext(const ed25519_secret_key skext, ed25519_public_key pk);

/// Sign using extended public key
void ed25519_sign_ext(const unsigned char *m, size_t mlen, const ed25519_secret_key sk, const ed25519_secret_key skext, ed25519_signature RS);

/// Scalar multiplication with the provided basepoint
void curve25519_scalarmult(curved25519_key mypublic, const curved25519_key secret, const curved25519_key basepoint);

/// COSI combine public keys (ed25519 point addition)
int ed25519_cosi_combine_publickeys(ed25519_public_key res, const ed25519_public_key *pks, size_t n);

// Not yet implemented COSI methods
#if 0

void ed25519_cosi_combine_signatures(ed25519_signature res, const ed25519_public_key R, const ed25519_cosi_signature *sigs, size_t n);

void ed25519_cosi_sign(const unsigned char *m, size_t mlen, const ed25519_secret_key sk, const ed25519_secret_key nonce, const ed25519_public_key R, const ed25519_public_key pk, ed25519_signature sig);

#endif

// Ed25519 with Keccak512

void ed25519_publickey_keccak(const ed25519_secret_key sk, ed25519_public_key pk);

int ed25519_sign_open_keccak(const unsigned char *m, size_t mlen, const ed25519_public_key pk, const ed25519_signature RS);

void ed25519_sign_keccak(const unsigned char *m, size_t mlen, const ed25519_secret_key sk, ed25519_signature RS);

int ed25519_scalarmult_keccak(ed25519_public_key res, const ed25519_secret_key sk, const ed25519_public_key pk);

void curved25519_scalarmult_basepoint_keccak(ed25519_public_key res, const ed25519_secret_key sk);


// Ed25519 with Sha3_512

void ed25519_publickey_sha3(const ed25519_secret_key sk, ed25519_public_key pk);

int ed25519_sign_open_sha3(const unsigned char *m, size_t mlen, const ed25519_public_key pk, const ed25519_signature RS);

void ed25519_sign_sha3(const unsigned char *m, size_t mlen, const ed25519_secret_key sk, ed25519_signature RS);

int ed25519_scalarmult_sha3(ed25519_public_key res, const ed25519_secret_key sk, const ed25519_public_key pk);

void curved25519_scalarmult_basepoint_sha3(ed25519_public_key res, const ed25519_secret_key sk);

#if 0
// Keccak512 hasher impl

// keccak512_ctx_t context object size must match rust object
// which _should_ be consistent with `repr(C)` but, is not ideal...
// TODO: work out whether there is a better way to propagate this..?
const size_t KECCAK512_CTX_SIZE = 280;

typedef uint8_t keccak512_ctx_t[KECCAK512_CTX_SIZE];

void keccak512_init(keccak512_ctx_t* ctx);
void keccak512_update(keccak512_ctx_t* ctx, const unsigned char *in, size_t inlen);
void keccak512_finalize(keccak512_ctx_t* ctx, uint8_t *md);

void keccak512_hash(const unsigned char *in, size_t inlen, char* hash);


// Sha3 hasher impl

// sha3_512_ctx_t context object size must match rust object
// which _should_ be consistent with `repr(C)` but, is not ideal...
// TODO: work out whether there is a better way to propagate this..?
const size_t SHA3_512_CTX_SIZE = 280;

typedef uint8_t sha3_512_ctx_t[SHA3_512_CTX_SIZE];

void sha3_512_init(sha3_512_ctx_t* ctx);
void sha3_512_update(sha3_512_ctx_t* ctx, const unsigned char *in, size_t inlen);
void sha3_512_finalize(sha3_512_ctx_t* ctx, uint8_t *md);

void sha3_512_hash(const unsigned char *in, size_t inlen, char* hash);

#endif

#ifdef __cplusplus
}
#endif

#endif
