#ifndef CURVE25519_H
#define CURVE25519_H

#include <stdint.h>

typedef uint8_t u8;

void curve25519_scalarmult(u8 *result, const u8 *secret, const u8 *basepoint);
void curve25519_publickey(u8 *public, const u8 *secret);

#endif  // CURVE25519_H
