/**
 * SPHINCS+ runtime dispatch for all 12 SLH-DSA parameter sets.
 */

#include "sphincsplus_dispatch.h"

/* Forward declarations for all 12 namespaced variants.
 * These symbols are defined by the spx_*.c wrapper files. */

#define DECLARE_VARIANT(prefix) \
    extern int prefix##_seed_keypair(uint8_t *, uint8_t *, const uint8_t *); \
    extern int prefix##_sign(uint8_t *, size_t *, const uint8_t *, size_t, const uint8_t *); \
    extern int prefix##_verify(const uint8_t *, size_t, const uint8_t *, size_t, const uint8_t *);

DECLARE_VARIANT(spx_sha2_128f)
DECLARE_VARIANT(spx_sha2_128s)
DECLARE_VARIANT(spx_sha2_192f)
DECLARE_VARIANT(spx_sha2_192s)
DECLARE_VARIANT(spx_sha2_256f)
DECLARE_VARIANT(spx_sha2_256s)
DECLARE_VARIANT(spx_shake_128f)
DECLARE_VARIANT(spx_shake_128s)
DECLARE_VARIANT(spx_shake_192f)
DECLARE_VARIANT(spx_shake_192s)
DECLARE_VARIANT(spx_shake_256f)
DECLARE_VARIANT(spx_shake_256s)

#define VARIANT_ENTRY(prefix, n_val, pk_val, sig_val) \
    { prefix##_seed_keypair, prefix##_sign, prefix##_verify, \
      pk_val, sig_val, n_val }

/* Variant table indexed by (variant_id - 48).
 * IDs: 48=sha2-128f, 49=sha2-128s, 50=sha2-192f, 51=sha2-192s,
 *      52=sha2-256f, 53=sha2-256s, 54=shake-128f, 55=shake-128s,
 *      56=shake-192f, 57=shake-192s, 58=shake-256f, 59=shake-256s */
static const spx_variant_t variant_table[12] = {
    VARIANT_ENTRY(spx_sha2_128f,   16, 32, 17088),  /* 48 */
    VARIANT_ENTRY(spx_sha2_128s,   16, 32, 7856),   /* 49 */
    VARIANT_ENTRY(spx_sha2_192f,   24, 48, 35664),  /* 50 */
    VARIANT_ENTRY(spx_sha2_192s,   24, 48, 16224),  /* 51 */
    VARIANT_ENTRY(spx_sha2_256f,   32, 64, 49856),  /* 52 */
    VARIANT_ENTRY(spx_sha2_256s,   32, 64, 29792),  /* 53 */
    VARIANT_ENTRY(spx_shake_128f,  16, 32, 17088),  /* 54 */
    VARIANT_ENTRY(spx_shake_128s,  16, 32, 7856),   /* 55 */
    VARIANT_ENTRY(spx_shake_192f,  24, 48, 35664),  /* 56 */
    VARIANT_ENTRY(spx_shake_192s,  24, 48, 16224),  /* 57 */
    VARIANT_ENTRY(spx_shake_256f,  32, 64, 49856),  /* 58 */
    VARIANT_ENTRY(spx_shake_256s,  32, 64, 29792),  /* 59 */
};

const spx_variant_t *spx_get_variant(int variant_id) {
    int idx = variant_id - 48;
    if (idx < 0 || idx >= 12) {
        return (void *)0;
    }
    return &variant_table[idx];
}
