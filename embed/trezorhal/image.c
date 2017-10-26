#include <string.h>

#include "blake2s.h"
#include "ed25519-donna/ed25519.h"

#include "common.h"
#include "image.h"

static bool compute_pubkey(uint8_t sig_m, uint8_t sig_n, const uint8_t * const *pub, uint8_t sigmask, ed25519_public_key res)
{
    if (!sig_m || !sig_n) return false;
    if (sig_m > sig_n) return false;

    // discard bits higher than sig_n
    sigmask &= ((1 << sig_n) - 1);

    // remove if number of set bits in sigmask is not equal to sig_m
    if (__builtin_popcount(sigmask) != sig_m) return false;

    ed25519_public_key keys[sig_m];
    int j = 0;
    for (int i = 0; i < sig_n; i++) {
        if ((1 << i) & sigmask) {
            memcpy(keys[j], pub[i], 32);
            j++;
        }
    }

    return 0 == ed25519_cosi_combine_publickeys(res, keys, sig_m);
}

bool load_image_header(const uint8_t * const data, const uint32_t magic, const uint32_t maxsize, uint8_t key_m, uint8_t key_n, const uint8_t * const *keys, image_header * const hdr)
{
    memcpy(&hdr->magic, data, 4);
    if (hdr->magic != magic) return false;

    memcpy(&hdr->hdrlen, data + 4, 4);
    if (hdr->hdrlen != IMAGE_HEADER_SIZE) return false;

    memcpy(&hdr->expiry, data + 8, 4);
    // TODO: expiry mechanism needs to be ironed out before production or those
    // devices won't accept expiring bootloaders (due to boardloader write protection).
    if (hdr->expiry != 0) return false;

    memcpy(&hdr->codelen, data + 12, 4);
    if (hdr->codelen > (maxsize - hdr->hdrlen)) return false;
    if ((hdr->hdrlen + hdr->codelen) < 4 * 1024) return false;
    if ((hdr->hdrlen + hdr->codelen) % 512 != 0) return false;

    memcpy(&hdr->version, data + 16, 4);

    memcpy(hdr->hashes, data + 32, 512);

    memcpy(&hdr->sigmask, data + IMAGE_HEADER_SIZE - IMAGE_SIG_SIZE, 1);

    memcpy(hdr->sig, data + IMAGE_HEADER_SIZE - IMAGE_SIG_SIZE + 1, IMAGE_SIG_SIZE - 1);

    // check header signature

    uint8_t hash[BLAKE2S_DIGEST_LENGTH];
    BLAKE2S_CTX ctx;
    blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
    blake2s_Update(&ctx, data, IMAGE_HEADER_SIZE - IMAGE_SIG_SIZE);
    for (int i = 0; i < IMAGE_SIG_SIZE; i++) {
        blake2s_Update(&ctx, (const uint8_t *)"\x00", 1);
    }
    blake2s_Final(&ctx, hash, BLAKE2S_DIGEST_LENGTH);

    ed25519_public_key pub;
    if (!compute_pubkey(key_m, key_n, keys, hdr->sigmask, pub)) return false;

    return 0 == ed25519_sign_open(hash, BLAKE2S_DIGEST_LENGTH, pub, *(const ed25519_signature *)hdr->sig);
}

bool load_vendor_header(const uint8_t * const data, uint8_t key_m, uint8_t key_n, const uint8_t * const *keys, vendor_header * const vhdr)
{
    memcpy(&vhdr->magic, data, 4);
    if (vhdr->magic != 0x565A5254) return false; // TRZV

    memcpy(&vhdr->hdrlen, data + 4, 4);
    if (vhdr->hdrlen > 64 * 1024) return false;

    memcpy(&vhdr->expiry, data + 8, 4);
    if (vhdr->expiry != 0) return false;

    memcpy(&vhdr->version, data + 12, 2);

    memcpy(&vhdr->vsig_m, data + 14, 1);
    memcpy(&vhdr->vsig_n, data + 15, 1);
    memcpy(&vhdr->vtrust, data + 16, 1);

    if (vhdr->vsig_n > MAX_VENDOR_PUBLIC_KEYS) {
        return false;
    }

    for (int i = 0; i < vhdr->vsig_n; i++) {
        vhdr->vpub[i] = data + 32 + i * 32;
    }
    for (int i = vhdr->vsig_n; i < MAX_VENDOR_PUBLIC_KEYS; i++) {
        vhdr->vpub[i] = 0;
    }

    memcpy(&vhdr->vstr_len, data + 32 + vhdr->vsig_n * 32, 1);

    vhdr->vstr = data + 32 + vhdr->vsig_n * 32 + 1;

    vhdr->vimg = data + 32 + vhdr->vsig_n * 32 + 1 + vhdr->vstr_len;
    // align to 4 bytes
    vhdr->vimg += (-(uintptr_t)vhdr->vimg) & 3;

    memcpy(&vhdr->sigmask, data + vhdr->hdrlen - IMAGE_SIG_SIZE, 1);

    memcpy(vhdr->sig, data + vhdr->hdrlen - IMAGE_SIG_SIZE + 1, IMAGE_SIG_SIZE - 1);

    // check header signature

    uint8_t hash[BLAKE2S_DIGEST_LENGTH];
    BLAKE2S_CTX ctx;
    blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
    blake2s_Update(&ctx, data, vhdr->hdrlen - IMAGE_SIG_SIZE);
    for (int i = 0; i < IMAGE_SIG_SIZE; i++) {
        blake2s_Update(&ctx, (const uint8_t *)"\x00", 1);
    }
    blake2s_Final(&ctx, hash, BLAKE2S_DIGEST_LENGTH);

    ed25519_public_key pub;
    if (!compute_pubkey(key_m, key_n, keys, vhdr->sigmask, pub)) return false;

    return 0 == ed25519_sign_open(hash, BLAKE2S_DIGEST_LENGTH, pub, *(const ed25519_signature *)vhdr->sig);
}

static bool check_hash(const uint8_t * const hash, const uint8_t * const data, int len)
{
    uint8_t h[BLAKE2S_DIGEST_LENGTH];
    blake2s(data, len, h, BLAKE2S_DIGEST_LENGTH);
    return 0 == memcmp(h, hash, BLAKE2S_DIGEST_LENGTH);
}

#define MIN(a,b) ((a) < (b) ? (a) : (b))

bool check_image_contents(const image_header * const hdr, const uint8_t * const data, int maxblocks)
{
    int remaining = hdr->codelen;
    if (!check_hash(hdr->hashes, data + IMAGE_HEADER_SIZE, MIN(remaining, IMAGE_CHUNK_SIZE - IMAGE_HEADER_SIZE))) {
        return false;
    }
    int block = 1;
    remaining -= IMAGE_CHUNK_SIZE - IMAGE_HEADER_SIZE;
    while (remaining > 0) {
        if (block >= maxblocks) {
            return false;
        }
        if (!check_hash(hdr->hashes + block * 32, data + block * IMAGE_CHUNK_SIZE, MIN(remaining, IMAGE_CHUNK_SIZE))) {
            return false;
        }
        block++;
        remaining -= IMAGE_CHUNK_SIZE;
    }
    return true;
}
