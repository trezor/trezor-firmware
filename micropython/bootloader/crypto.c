#include <string.h>

#include "sha2.h"
#include "ed25519-donna/ed25519.h"

#include "crypto.h"

#define FLASH_BASE 0x08000000

bool parse_header(const uint8_t *data, uint32_t *codelen, uint8_t *sigidx, uint8_t *sig)
{
    uint32_t magic;
    memcpy(&magic, data, 4);
    if (magic != 0x4C5A5254) return false; // TRZL

    uint32_t hdrlen;
    memcpy(&hdrlen, data + 4, 4);
    if (hdrlen != 256) return false;

    uint32_t expiry;
    memcpy(&expiry, data + 8, 4);
    if (expiry != 0) return false;

    uint32_t clen;
    memcpy(&clen, data + 12, 4);
    // stage 2 (+header) must fit into sectors 4...11 - see docs/memory.md for more info
    if (clen + hdrlen < 4 * 1024) return false;
    if (clen + hdrlen > 64 * 1024 + 7 * 128 * 1024) return false;
    if ((clen + hdrlen) % 512 != 0) return false;

    if (codelen) {
        *codelen = clen;
    }

    uint32_t version;
    memcpy(&version, data + 16, 4);

    // uint8_t reserved[171];

    if (sigidx) {
        memcpy(sigidx, data + 0x00BF, 1);
    }

    if (sig) {
        memcpy(sig, data + 0x00C0, 64);
    }

    return true;
}

#define KEYMASK(A, B, C) ((1 << (A - 1)) | (1 << (B - 1)) | (1 << (C - 1)))

const uint8_t *get_pubkey(uint8_t index)
{
    switch (index) {
        case KEYMASK(1, 2, 3):
            return (const uint8_t *)"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
        case KEYMASK(1, 2, 4):
            return (const uint8_t *)"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
        case KEYMASK(1, 2, 5):
            return (const uint8_t *)"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
        case KEYMASK(1, 3, 4):
            return (const uint8_t *)"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
        case KEYMASK(1, 3, 5):
            return (const uint8_t *)"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
        case KEYMASK(1, 4, 5):
            return (const uint8_t *)"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
        case KEYMASK(2, 3, 4):
            return (const uint8_t *)"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
        case KEYMASK(2, 3, 5):
            return (const uint8_t *)"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
        case KEYMASK(2, 4, 5):
            return (const uint8_t *)"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
        case KEYMASK(3, 4, 5):
            return (const uint8_t *)"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
        default:
            return NULL;
    }
}

bool check_signature(const uint8_t *start)
{
    uint32_t codelen;
    uint8_t sigidx;
    uint8_t sig[64];
    if (!parse_header(start, &codelen, &sigidx, sig)) {
        return false;
    }

    uint8_t hash[SHA256_DIGEST_LENGTH];
    SHA256_CTX ctx;
    sha256_Init(&ctx);
    sha256_Update(&ctx, start, 256 - 65);
    for (int i = 0; i < 65; i++) {
        sha256_Update(&ctx, (const uint8_t *)"\x00", 1);
    }
    sha256_Update(&ctx, start + 256, codelen);
    sha256_Final(&ctx, hash);

    const uint8_t *pub = get_pubkey(sigidx);

    return pub && (0 == ed25519_sign_open(hash, SHA256_DIGEST_LENGTH, *(const ed25519_public_key *)pub, *(const ed25519_signature *)sig));
}
