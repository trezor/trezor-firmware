#ifndef _TYPES_H_
#define _TYPES_H_

#define USE_BASIC_CONFIG
#include "lib/secp256k1-zkp/include/secp256k1.h"
#include "lib/secp256k1-zkp/src/basic-config.h"
#include "lib/secp256k1-zkp/src/field.h"
#include "lib/secp256k1-zkp/src/group.h"
#include "lib/secp256k1-zkp/src/scalar.h"

#include "lib/vec.h"

#define DIGEST_LENGTH 32
#define N_BYTES 32
#define N_BITS (N_BYTES << 3)
// #define N_BITS_PER_LEVEL 4
#define N_BITS_PER_LEVEL 2
#define N_POINTS_PER_LEVEL (1 << N_BITS_PER_LEVEL)  // 16
#define N_LEVELS (N_BITS / N_BITS_PER_LEVEL)
#define MASTER_NONCE_SLOT 0
#define MAX_NONCE_SLOT 255

#define KIDV_SCHEME_V0 0
#define KIDV_SCHEME_V1 1
#define KIDV_SCHEME_BB21 2
#define KIDV_SCHEME_SUB_KEY_BITS 24U
#define KIDV_SCHEME_SUB_KEY_MASK \
  ((((uint32_t)1U) << KIDV_SCHEME_SUB_KEY_BITS) - 1)

#define _COUNT_OF(_Array) (sizeof(_Array) / sizeof(_Array[0]))
#define _FOURCC_CONST(a, b, c, d)                                            \
  ((uint32_t)((((((uint8_t)a << 8) | (uint8_t)b) << 8) | (uint8_t)c) << 8) | \
   (uint8_t)d)
#define _ARRAY_ELEMENT_SAFE(arr, index) \
  ((arr)[(((index) < _COUNT_OF(arr)) ? (index) : (_COUNT_OF(arr) - 1))])
#define _FOURCC_FROM(name)                                                    \
  _FOURCC_CONST(_ARRAY_ELEMENT_SAFE(#name, 0), _ARRAY_ELEMENT_SAFE(#name, 1), \
                _ARRAY_ELEMENT_SAFE(#name, 2), _ARRAY_ELEMENT_SAFE(#name, 3))

#define static_assert(condition)((void)sizeof(char[1 - 2 * !(condition)]))
#ifndef UNUSED
#define UNUSED(x) (void)(x)
#endif

typedef struct {
  uint8_t x[DIGEST_LENGTH];
  uint8_t y;
} point_t;

typedef uint8_t scalar_packed_t[32];

typedef struct {
  uint32_t Comission;
  uint32_t Coinbase;
  uint32_t Regular;
  uint32_t Change;
  uint32_t Kernel;
  uint32_t Kernel2;
  uint32_t Identity;
  uint32_t ChildKey;
  uint32_t Bbs;
  uint32_t Decoy;
  uint32_t Treasury;
} key_types_t;

typedef struct {
  secp256k1_gej *G_pts;
  secp256k1_gej *J_pts;
  secp256k1_gej *H_pts;
} generators_t;

typedef struct {
  key_types_t key;
  generators_t generator;
} context_t;

typedef struct {
  secp256k1_scalar cofactor;
  // according to rfc5869
  uint8_t generator_secret[DIGEST_LENGTH];
} HKdf_t;

#pragma pack(push, 1)
typedef struct {
  uint8_t secret[DIGEST_LENGTH];
  point_t pkG;
  point_t pkJ;
} HKdf_pub_packed_t;
#pragma pack(pop)

typedef struct {
  secp256k1_gej nonce_pub;
  secp256k1_scalar k;
} ecc_signature_t;

typedef struct {
  uint64_t idx;
  uint32_t type;
  uint32_t sub_idx;
} key_id_t;

typedef struct {
  key_id_t id;
  uint64_t value;
} key_idv_t;
typedef vec_t(key_idv_t) kidv_vec_t;

#pragma pack(push, 1)
typedef struct {
  uint8_t idx[8];
  uint8_t type[4];
  uint8_t sub_idx[4];
} packed_key_id_t;
#pragma pack(pop)

#pragma pack(push, 1)
typedef struct {
  packed_key_id_t id;
  uint8_t value[8];
} packed_key_idv_t;
#pragma pack(pop)

secp256k1_gej *get_generator_G(void);

secp256k1_gej *get_generator_J(void);

secp256k1_gej *get_generator_H(void);

secp256k1_gej *get_generator_ipp(size_t i, size_t j, size_t z);

secp256k1_gej *get_generator_get1_minus(void);

secp256k1_gej *get_generator_dot_ipp(void);

#endif  //_TYPES_H_
