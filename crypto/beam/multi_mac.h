#ifndef _MULTI_MAC_H_
#define _MULTI_MAC_H_

#include "definitions.h"

// #define MULTI_MAC_CASUAL_MAX_ODD 31 // (1 << 5) - 1
#define MULTI_MAC_CASUAL_MAX_ODD 1
#define MULTI_MAC_CASUAL_COUNT \
  2  // (MULTI_MAC_CASUAL_MAX_ODD >> 1) + 2 // we need a single even: x2
// #define MULTI_MAC_PREPARED_MAX_ODD  0xff // 255
#define MULTI_MAC_PREPARED_MAX_ODD 1
#define MULTI_MAC_PREPARED_COUNT 1  // (MULTI_MAC_PREPARED_MAX_ODD >> 1) + 1

typedef struct {
  uint32_t next_item;
  uint32_t odd;
} _multi_mac_fast_aux_t;

typedef struct {
  secp256k1_gej pt[MULTI_MAC_CASUAL_COUNT];
  secp256k1_scalar k;
  uint32_t prepared;
  _multi_mac_fast_aux_t aux;
} multi_mac_casual_t;

typedef struct {
  secp256k1_gej pt[MULTI_MAC_PREPARED_COUNT];
} multi_mac_prepared_t;

typedef struct {
  multi_mac_casual_t *casual;
  uint32_t n_casual;

  multi_mac_prepared_t **prepared;
  secp256k1_scalar *k_prepared;
  _multi_mac_fast_aux_t *aux_prepared;
  uint32_t n_prepared;
} multi_mac_t;

void multi_mac_with_bufs_alloc(multi_mac_t *mm, int max_casual,
                               int max_prepared);

void multi_mac_with_bufs_free(multi_mac_t *mm);

void multi_mac_reset(multi_mac_t *mm);

void multi_mac_casual_init_new(multi_mac_casual_t *casual,
                               const secp256k1_gej *p);

void multi_mac_casual_init(multi_mac_casual_t *casual, const secp256k1_gej *p,
                           const secp256k1_scalar *k);

void multi_mac_fast_aux_schedule(_multi_mac_fast_aux_t *aux,
                                 const secp256k1_scalar *k,
                                 unsigned int iBitsRemaining,
                                 unsigned int nMaxOdd, unsigned int *pTbl,
                                 unsigned int iThisEntry);

void multi_mac_calculate(multi_mac_t *mm, secp256k1_gej *res);

#endif  // _MULTI_MAC_H_