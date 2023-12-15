#ifndef LIB_IMAGE_HASH_H_
#define LIB_IMAGE_HASH_H_

#include "model.h"
#include TREZOR_BOARD

#ifdef IMAGE_HASH_SHA256
#include "sha2.h"
#define IMAGE_HASH_DIGEST_LENGTH SHA256_DIGEST_LENGTH
#ifdef USE_HASH_PROCESSOR
#include "hash_processor.h"
#define IMAGE_HASH_CTX hash_sha265_context_t
#define IMAGE_HASH_INIT hash_processor_sha256_init
#define IMAGE_HASH_UPDATE hash_processor_sha256_update
#define IMAGE_HASH_FINAL hash_processor_sha256_final
#define IMAGE_HASH_CALC hash_processor_sha256_calc
#else
#define IMAGE_HASH_CTX SHA256_CTX
#define IMAGE_HASH_INIT sha256_Init
#define IMAGE_HASH_UPDATE sha256_Update
#define IMAGE_HASH_FINAL sha256_Final
#define IMAGE_HASH_CALC sha256_Raw
#endif

#elif defined IMAGE_HASH_BLAKE2S
#include "blake2s.h"
#define IMAGE_HASH_DIGEST_LENGTH BLAKE2S_DIGEST_LENGTH

static inline void _blake2s_Calc(const uint8_t *data, size_t len,
                                 uint8_t *hash) {
  blake2s(data, len, hash, BLAKE2S_DIGEST_LENGTH);
}
static inline void _blake2s_Init(BLAKE2S_CTX *ctx) {
  blake2s_Init(ctx, BLAKE2S_DIGEST_LENGTH);
}
static inline void _blake2s_Final(BLAKE2S_CTX *ctx, void *out) {
  blake2s_Final(ctx, out, BLAKE2S_DIGEST_LENGTH);
}

#define IMAGE_HASH_CTX BLAKE2S_CTX
#define IMAGE_HASH_INIT _blake2s_Init
#define IMAGE_HASH_UPDATE blake2s_Update
#define IMAGE_HASH_FINAL _blake2s_Final
#define IMAGE_HASH_CALC _blake2s_Calc

#else
#error "IMAGE_HASH_SHA256 or IMAGE_HASH_BLAKE2S must be defined"
#endif

#endif
