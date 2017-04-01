#include <string.h>

#include "blake2s.h"
#include "ed25519-donna/ed25519.h"

#include "common.h"
#include "crypto.h"

bool parse_header(const uint8_t *data, uint32_t *codelen, uint8_t *sigmask, uint8_t *sig)
{
    uint32_t magic;
    memcpy(&magic, data, 4);
    if (magic != 0x465A5254) return false; // TRZF

    uint32_t hdrlen;
    memcpy(&hdrlen, data + 4, 4);
    if (hdrlen != HEADER_SIZE) return false;

    uint32_t expiry;
    memcpy(&expiry, data + 8, 4);
    if (expiry != 0) return false;

    uint32_t clen;
    memcpy(&clen, data + 12, 4);
    if (clen + hdrlen < 4 * 1024) return false;
    if (clen + hdrlen > 7 * 128 * 1024) return false;
    if ((clen + hdrlen) % 512 != 0) return false;

    if (codelen) {
        *codelen = clen;
    }

    uint32_t version;
    memcpy(&version, data + 16, 4);

    // uint8_t reserved[427];

    if (sigmask) {
        memcpy(sigmask, data + 0x01BF, 1);
    }

    if (sig) {
        memcpy(sig, data + 0x01C0, 64);
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
    uint8_t sigmask;
    uint8_t sig[64];
    if (!parse_header(start, &codelen, &sigmask, sig)) {
        return false;
    }

    uint8_t hash[BLAKE2S_DIGEST_LENGTH];
    BLAKE2S_CTX ctx;
    blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
    blake2s_Update(&ctx, start, 256 - 65);
    for (int i = 0; i < 65; i++) {
        blake2s_Update(&ctx, (const uint8_t *)"\x00", 1);
    }
    blake2s_Update(&ctx, start + 256, codelen);
    blake2s_Final(&ctx, hash, BLAKE2S_DIGEST_LENGTH);

    const uint8_t *pub = get_pubkey(sigmask);

    // TODO: remove debug skip of unsigned
    if (!pub) return true;
    // end

    return pub && (0 == ed25519_sign_open(hash, BLAKE2S_DIGEST_LENGTH, *(const ed25519_public_key *)pub, *(const ed25519_signature *)sig));
}
