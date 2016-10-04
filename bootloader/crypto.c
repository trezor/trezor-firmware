#include "crypto.h"

#include "ed25519-donna/ed25519.h"

#include "cmsis/stm32f405xx.h"

void hash_flash(uint8_t hash[SHA256_DIGEST_LENGTH])
{
     sha256_Raw((const uint8_t *)FLASH_BASE, 1024*1024, hash);
}

bool ed25519_verify(const uint8_t *msg, uint32_t msglen, uint8_t *pubkey, uint8_t *signature)
{
    return (0 == ed25519_sign_open(msg, msglen, *(const ed25519_public_key *)pubkey, *(const ed25519_signature *)signature));
}
