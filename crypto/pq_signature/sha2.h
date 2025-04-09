#ifndef SHA2_H
#define SHA2_H

#include <stddef.h>
#include <stdint.h>

/* The incremental API allows hashing of individual input blocks; these blocks
    must be exactly 64 bytes each.
    Use the 'finalize' functions for any remaining bytes (possibly over 64). */

#define PQC_SHA256CTX_BYTES 40
/* Structure for the incremental API */
typedef struct {
    uint8_t *ctx;
} sha224ctx;

/* Structure for the incremental API */
typedef struct {
    uint8_t *ctx;
} sha256ctx;

#define PQC_SHA512CTX_BYTES 72
/* Structure for the incremental API */
typedef struct {
    uint8_t *ctx;
} sha384ctx;

/* Structure for the incremental API */
typedef struct {
    uint8_t *ctx;
} sha512ctx;

/* ====== SHA224 API ==== */

/**
 * Initialize the incremental hashing API.
 *
 * Can't be called multiple times.
 */
void sha224_inc_init(sha224ctx *state);

/**
 * Copy the hashing state
 */
void sha224_inc_ctx_clone(sha224ctx *stateout, const sha224ctx *statein);

/**
 * Absorb blocks
 */
void sha224_inc_blocks(sha224ctx *state, const uint8_t *in, size_t inblocks);

/**
 * Finalize and obtain the digest
 *
 * If applicable, this function will free the memory associated with the sha224ctx.
 *
 * If not calling this function, call `sha224_inc_ctx_release`
 */
void sha224_inc_finalize(uint8_t *out, sha224ctx *state, const uint8_t *in, size_t inlen);

/**
 * Destroy the state. Make sure to use this, as this API may not always be stack-based.
 */
void sha224_inc_ctx_release(sha224ctx *state);

/**
 * All-in-one sha224 function
 */
void sha224(uint8_t *out, const uint8_t *in, size_t inlen);

/* ====== SHA256 API ==== */

/**
 * Initialize the incremental hashing API
 */
void sha256_inc_init(sha256ctx *state);

/**
 * Copy the hashing state
 */
void sha256_inc_ctx_clone(sha256ctx *stateout, const sha256ctx *statein);

/**
 * Absorb blocks
 */
void sha256_inc_blocks(sha256ctx *state, const uint8_t *in, size_t inblocks);

/**
 * Finalize and obtain the digest
 *
 * If applicable, this function will free the memory associated with the sha256ctx.
 */
void sha256_inc_finalize(uint8_t *out, sha256ctx *state, const uint8_t *in, size_t inlen);

/**
 * Destroy the state. Make sure to use this, as this API may not always be stack-based.
 */
void sha256_inc_ctx_release(sha256ctx *state);

/**
 * All-in-one sha256 function
 */
void sha256(uint8_t *out, const uint8_t *in, size_t inlen);

/* ====== SHA384 API ==== */

/**
 * Initialize the incremental hashing API
 */
void sha384_inc_init(sha384ctx *state);

/**
 * Copy the hashing state
 */
void sha384_inc_ctx_clone(sha384ctx *stateout, const sha384ctx *statein);

/**
 * Absorb blocks
 */
void sha384_inc_blocks(sha384ctx *state, const uint8_t *in, size_t inblocks);

/**
 * Finalize and obtain the digest.
 *
 * If applicable, this function will free the memory associated with the sha384ctx.
 */
void sha384_inc_finalize(uint8_t *out, sha384ctx *state, const uint8_t *in, size_t inlen);

/**
 * Destroy the state. Make sure to use this if not calling finalize, as this API may not always be stack-based.
 */
void sha384_inc_ctx_release(sha384ctx *state);

/**
 * All-in-one sha384 function
 */
void sha384(uint8_t *out, const uint8_t *in, size_t inlen);

/* ====== SHA512 API ==== */

/**
 * Initialize the incremental hashing API
 */
void sha512_inc_init(sha512ctx *state);

/**
 * Copy the hashing state
 */
void sha512_inc_ctx_clone(sha512ctx *stateout, const sha512ctx *statein);

/**
 * Absorb blocks
 */
void sha512_inc_blocks(sha512ctx *state, const uint8_t *in, size_t inblocks);

/**
 * Finalize and obtain the digest
 *
 * If applicable, this function will free the memory associated with the sha512ctx.
 */
void sha512_inc_finalize(uint8_t *out, sha512ctx *state, const uint8_t *in, size_t inlen);

/**
 * Destroy the state. Make sure to use this if not calling finalize, as this API may not always be stack-based.
 */
void sha512_inc_ctx_release(sha512ctx *state);

/**
 * All-in-one sha512 function
 */
void sha512(uint8_t *out, const uint8_t *in, size_t inlen);

#endif
