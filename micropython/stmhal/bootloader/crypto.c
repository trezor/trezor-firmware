#include <string.h>

#include "sha2.h"
#include "ed25519-donna/ed25519.h"

#include "crypto.h"

/*
void hash_flash(uint8_t hash[SHA256_DIGEST_LENGTH])
{
     sha256_Raw((const uint8_t *)FLASH_BASE, 1024*1024, hash);
}

bool ed25519_verify(const uint8_t *msg, uint32_t msglen, uint8_t *pubkey, uint8_t *signature)
{
    return (0 == ed25519_sign_open(msg, msglen, *(const ed25519_public_key *)pubkey, *(const ed25519_signature *)signature));
}
*/

bool check_header(const uint8_t *data)
{
    uint32_t magic;
    memcpy(&magic, data, 4);
    if (magic != 0x425A5254) return false; // TRZB

    uint32_t hdrlen;
    memcpy(&hdrlen, data + 4, 4);
    if (hdrlen != 256) return false;

    uint32_t expiry;
    memcpy(&expiry, data + 8, 4);
    if (expiry != 0) return false;

    uint32_t codelen;
    memcpy(&codelen, data + 12, 4);
    if (codelen != 64 * 1024) return false;

    uint32_t version;
    memcpy(&version, data + 16, 4);

    // uint8_t reserved[171];

    uint8_t sigidx;
    memcpy(&sigidx, data + 0x00BF, 1);

    uint8_t sig[64];
    memcpy(sig, data + 0x00C0, 64);

    // TODO: check signature

    return true;
}
