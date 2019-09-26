#ifndef _ORACLE_H_
#define _ORACLE_H_

#include "../sha2.h"
#include "definitions.h"

void sha256_oracle_update_gej(SHA256_CTX *oracle, const secp256k1_gej *gej);

void sha256_oracle_update_pt(SHA256_CTX *oracle, const point_t *pt);

void sha256_oracle_update_sk(SHA256_CTX *oracle, const secp256k1_scalar *sk);

void sha256_oracle_create(SHA256_CTX *oracle, uint8_t *out32);

#endif  //_ORACLE_H_