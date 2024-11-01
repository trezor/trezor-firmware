#ifndef TREZORHAL_HASH_PROCESSOR_H_
#define TREZORHAL_HASH_PROCESSOR_H_

#include <trezor_types.h>

#ifdef KERNEL_MODE

#define HASH_SHA256_BUFFER_SIZE 4

typedef struct {
  uint32_t length;                         /*!< nb bytes in buffer */
  uint8_t buffer[HASH_SHA256_BUFFER_SIZE]; /*!< data being processed */
} hash_sha256_context_t;

#ifdef KERNEL_MODE

// Initialize the hash processor
void hash_processor_init(void);

#endif

// Calculate SHA256 hash of data
// for best performance, data should be 32-bit aligned - as this allows DMA to
// be used
void hash_processor_sha256_calc(const uint8_t *data, uint32_t len,
                                uint8_t *hash);

// Initialize the hash context
// This serves for calculating hashes of multiple data blocks
void hash_processor_sha256_init(hash_sha256_context_t *ctx);

// Feed the hash next chunk of data
void hash_processor_sha256_update(hash_sha256_context_t *ctx,
                                  const uint8_t *data, uint32_t len);

// Finalize the hash calculation, retrieve the digest
void hash_processor_sha256_final(hash_sha256_context_t *ctx, uint8_t *output);

#endif  // KERNEL_MODE

#endif
