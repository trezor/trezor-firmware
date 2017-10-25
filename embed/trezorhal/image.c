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

bool image_parse_header(const uint8_t * const data, const uint32_t magic, const uint32_t maxsize, image_header * const hdr)
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

    // uint8_t reserved[427];

    memcpy(&hdr->sigmask, data + 0x01BF, 1);

    memcpy(hdr->sig, data + 0x01C0, 64);

    return true;
}

bool image_check_signature(const uint8_t *data, const image_header *hdr, uint8_t key_m, uint8_t key_n, const uint8_t * const *keys)
{
    uint8_t hash[BLAKE2S_DIGEST_LENGTH];
    BLAKE2S_CTX ctx;
    blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
    blake2s_Update(&ctx, data, IMAGE_HEADER_SIZE - 65);
    for (int i = 0; i < 65; i++) {
        blake2s_Update(&ctx, (const uint8_t *)"\x00", 1);
    }
    blake2s_Update(&ctx, data + IMAGE_HEADER_SIZE, hdr->codelen);
    blake2s_Final(&ctx, hash, BLAKE2S_DIGEST_LENGTH);

    ed25519_public_key pub;
    if (!compute_pubkey(key_m, key_n, keys, hdr->sigmask, pub)) return false;

    return 0 == ed25519_sign_open(hash, BLAKE2S_DIGEST_LENGTH, pub, *(const ed25519_signature *)hdr->sig);
}

bool vendor_parse_header(const uint8_t * const data, vendor_header * const vhdr)
{
    memcpy(&vhdr->magic, data, 4);
    if (vhdr->magic != 0x565A5254) return false; // TRZV

    memcpy(&vhdr->hdrlen, data + 4, 4);
    // TODO: sanity check hdr->hdrlen as it is used as a src to memcpy below

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

    // uint8_t reserved[427];

    memcpy(&vhdr->sigmask, data + vhdr->hdrlen - 65, 1);

    memcpy(vhdr->sig, data + vhdr->hdrlen - 64, 64);

    return true;
}

bool vendor_check_signature(const uint8_t *data, const vendor_header *vhdr, uint8_t key_m, uint8_t key_n, const uint8_t * const *keys)
{
    uint8_t hash[BLAKE2S_DIGEST_LENGTH];
    BLAKE2S_CTX ctx;
    blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
    blake2s_Update(&ctx, data, vhdr->hdrlen - 65);
    for (int i = 0; i < 65; i++) {
        blake2s_Update(&ctx, (const uint8_t *)"\x00", 1);
    }
    blake2s_Final(&ctx, hash, BLAKE2S_DIGEST_LENGTH);

    ed25519_public_key pub;
    if (!compute_pubkey(key_m, key_n, keys, vhdr->sigmask, pub)) return false;

    return 0 == ed25519_sign_open(hash, BLAKE2S_DIGEST_LENGTH, pub, *(const ed25519_signature *)vhdr->sig);
}
