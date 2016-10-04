#ifndef __BOOTLOADER_CRYPTO_H__
#define __BOOTLOADER_CRYPTO_H__

#include <stdint.h>
#include <stdbool.h>

#include "sha2.h"

void hash_flash(uint8_t hash[SHA256_DIGEST_LENGTH]);
bool ed25519_verify(const uint8_t *msg, uint32_t msglen, uint8_t *pubkey, uint8_t *signature);

#endif
