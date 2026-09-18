// SPDX-License-Identifier: Apache-2.0 or CC0-1.0
#ifndef PARAMS_H
#define PARAMS_H

#ifndef MLKEM_K
#define MLKEM_K 3   /* Change this for different security strengths */
#endif

/* Don't change parameters below this line */
#if   (MLKEM_K == 2)
#define MLKEM_NAMESPACE(s) pqcrystals_mlkem512_ref_##s
#elif (MLKEM_K == 3)
#define MLKEM_NAMESPACE(s) pqcrystals_mlkem768_ref_##s
#elif (MLKEM_K == 4)
#define MLKEM_NAMESPACE(s) pqcrystals_mlkem1024_ref_##s
#else
#error "MLKEM_K must be in {2,3,4}"
#endif

#define MLKEM_N 256
#define MLKEM_Q 3329

#define MLKEM_SYMBYTES 32   /* size in bytes of hashes, and seeds */
#define MLKEM_SSBYTES  32   /* size in bytes of shared key */

#define MLKEM_POLYBYTES     384
#define MLKEM_POLYVECBYTES  (MLKEM_K * MLKEM_POLYBYTES)

#if MLKEM_K == 2
#define MLKEM_ETA1 3
#define MLKEM_POLYCOMPRESSEDBYTES    128
#define MLKEM_POLYVECCOMPRESSEDBYTES (MLKEM_K * 320)
#elif MLKEM_K == 3
#define MLKEM_ETA1 2
#define MLKEM_POLYCOMPRESSEDBYTES    128
#define MLKEM_POLYVECCOMPRESSEDBYTES (MLKEM_K * 320)
#elif MLKEM_K == 4
#define MLKEM_ETA1 2
#define MLKEM_POLYCOMPRESSEDBYTES    160
#define MLKEM_POLYVECCOMPRESSEDBYTES (MLKEM_K * 352)
#endif

#define MLKEM_ETA2 2

#define MLKEM_INDCPA_MSGBYTES       (MLKEM_SYMBYTES)
#define MLKEM_INDCPA_PUBLICKEYBYTES (MLKEM_POLYVECBYTES + MLKEM_SYMBYTES)
#define MLKEM_INDCPA_SECRETKEYBYTES (MLKEM_POLYVECBYTES)
#define MLKEM_INDCPA_BYTES          (MLKEM_POLYVECCOMPRESSEDBYTES + MLKEM_POLYCOMPRESSEDBYTES)

#define MLKEM_PUBLICKEYBYTES  (MLKEM_INDCPA_PUBLICKEYBYTES)
/* 32 bytes of additional space to save H(pk) */
#define MLKEM_SECRETKEYBYTES  (MLKEM_INDCPA_SECRETKEYBYTES + MLKEM_INDCPA_PUBLICKEYBYTES + 2*MLKEM_SYMBYTES)
#define MLKEM_CIPHERTEXTBYTES (MLKEM_INDCPA_BYTES)

#endif
