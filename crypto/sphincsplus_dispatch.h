/**
 * SPHINCS+ runtime dispatch for all 12 SLH-DSA parameter sets.
 *
 * Each variant is compiled with namespaced symbols (spx_{name}_*).
 * This dispatch table maps variant IDs (48-59) to function pointers
 * so the MicroPython binding can call the correct variant at runtime.
 */

#ifndef __SPHINCSPLUS_DISPATCH_H__
#define __SPHINCSPLUS_DISPATCH_H__

#include <stddef.h>
#include <stdint.h>

/* Largest n across the 12 parameter sets; secret key is 4*n, seed 3*n. */
#define SPX_MAX_N 32

typedef struct {
  int (*seed_keypair)(uint8_t *pk, uint8_t *sk, const uint8_t *seed);
  int (*sign)(uint8_t *sig, size_t *siglen, const uint8_t *m, size_t mlen,
              const uint8_t *sk);
  int (*verify)(const uint8_t *sig, size_t siglen, const uint8_t *m,
                size_t mlen, const uint8_t *pk);
  unsigned long long (*sig_bytes_fn)(void);
  unsigned long long (*pk_bytes_fn)(void);
  size_t pk_bytes;
  size_t sig_bytes;
  uint8_t spx_n; /* 16, 24, or 32 */
} spx_variant_t;

/**
 * Get variant descriptor by ID.
 *
 * @param variant_id  SPHINCS+ / SLH-DSA variant ID (48-59)
 * @return            Pointer to variant struct, or NULL if invalid
 */
const spx_variant_t *spx_get_variant(int variant_id);

#endif
