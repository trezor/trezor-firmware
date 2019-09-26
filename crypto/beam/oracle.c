#include "oracle.h"
#include "internal.h"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "beam/lib/secp256k1-zkp/src/field_impl.h"
#include "beam/lib/secp256k1-zkp/src/group_impl.h"
#include "beam/lib/secp256k1-zkp/src/scalar_impl.h"
#pragma GCC diagnostic pop

void sha256_oracle_update_gej(SHA256_CTX *oracle, const secp256k1_gej *gej) {
  point_t pt;
  export_gej_to_point(gej, &pt);
  sha256_oracle_update_pt(oracle, &pt);
}

void sha256_oracle_update_pt(SHA256_CTX *oracle, const point_t *pt) {
  sha256_Update(oracle, pt->x, 32);
  sha256_write_8(oracle, pt->y);
}

void sha256_oracle_update_sk(SHA256_CTX *oracle, const secp256k1_scalar *sk) {
  uint8_t sk_bytes[32];
  memset(sk_bytes, 0, 32);
  secp256k1_scalar_get_b32(sk_bytes, sk);
  sha256_Update(oracle, sk_bytes, 32);
}

void sha256_oracle_create(SHA256_CTX *oracle, uint8_t *out32) {
  SHA256_CTX new_oracle;
  memcpy(&new_oracle, oracle, sizeof(SHA256_CTX));
  sha256_Final(&new_oracle, out32);
  sha256_Update(oracle, out32, 32);
}