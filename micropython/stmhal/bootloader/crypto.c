#include <string.h>

#include "sha2.h"
#include "ed25519-donna/ed25519.h"

#include "crypto.h"

#define FLASH_BASE 0x08000000

void hash_flash(uint8_t hash[SHA256_DIGEST_LENGTH])
{
     sha256_Raw((const uint8_t *)FLASH_BASE, 1024*1024, hash);
}

bool ed25519_verify(const uint8_t *msg, uint32_t msglen, const uint8_t *pubkey, const uint8_t *signature)
{
    return (0 == ed25519_sign_open(msg, msglen, *(const ed25519_public_key *)pubkey, *(const ed25519_signature *)signature));
}

bool parse_header(const uint8_t *data, uint32_t *codelen)
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

    memcpy(codelen, data + 12, 4);
    // stage 2 (+header) must fit into sectors 4...11 - see docs/memory.md for more info
    if (*codelen + hdrlen < 4 * 1024) return false;
    if (*codelen + hdrlen > 64 * 1024 + 7 * 128 * 1024) return false;
    if ((*codelen + hdrlen) % 512 != 0) return false;

    uint32_t version;
    memcpy(&version, data + 16, 4);

    // uint8_t reserved[171];

    uint8_t sigidx;
    memcpy(&sigidx, data + 0x00BF, 1);

    uint8_t sig[64];
    memcpy(sig, data + 0x00C0, 64);

    return true;
}

bool check_signature(void)
{
    uint8_t hash[SHA256_DIGEST_LENGTH];
    hash_flash(hash);

    const uint8_t *pub = (const uint8_t *)"0123456789ABCDEF0123456789ABCDEF";
    const uint8_t *sig = (const uint8_t *)"0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF";
    return ed25519_verify(hash, SHA256_DIGEST_LENGTH, pub, sig);
}
