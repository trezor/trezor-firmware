#include <string.h>

#include "blake2s.h"
#include "ed25519-donna/ed25519.h"

#include "common.h"
#include "image.h"

static const uint8_t * const SATOSHILABS_PUBKEYS[] = {
    (const uint8_t *)"\xdb\x99\x5f\xe2\x51\x69\xd1\x41\xca\xb9\xbb\xba\x92\xba\xa0\x1f\x9f\x2e\x1e\xce\x7d\xf4\xcb\x2a\xc0\x51\x90\xf3\x7f\xcc\x1f\x9d",
    (const uint8_t *)"\x21\x52\xf8\xd1\x9b\x79\x1d\x24\x45\x32\x42\xe1\x5f\x2e\xab\x6c\xb7\xcf\xfa\x7b\x6a\x5e\xd3\x00\x97\x96\x0e\x06\x98\x81\xdb\x12",
    (const uint8_t *)"\x22\xfc\x29\x77\x92\xf0\xb6\xff\xc0\xbf\xcf\xdb\x7e\xdb\x0c\x0a\xa1\x4e\x02\x5a\x36\x5e\xc0\xe3\x42\xe8\x6e\x38\x29\xcb\x74\xb6",
    (const uint8_t *)"\xd7\x59\x79\x3b\xbc\x13\xa2\x81\x9a\x82\x7c\x76\xad\xb6\xfb\xa8\xa4\x9a\xee\x00\x7f\x49\xf2\xd0\x99\x2d\x99\xb8\x25\xad\x2c\x48",
    (const uint8_t *)"\x63\x55\x69\x1c\x17\x8a\x8f\xf9\x10\x07\xa7\x47\x8a\xfb\x95\x5e\xf7\x35\x2c\x63\xe7\xb2\x57\x03\x98\x4c\xf7\x8b\x26\xe2\x1a\x56",
};

static bool compute_pubkey(const vendor_header *vhdr, uint8_t sigmask, ed25519_public_key res)
{
    uint8_t vsig_m;
    uint8_t vsig_n;
    const uint8_t * const *vpub;

    if (vhdr) {
        vsig_m = vhdr->vsig_m;
        vsig_n = vhdr->vsig_n;
        vpub = vhdr->vpub;
    } else {
        vsig_m = 1;
        vsig_n = 5;
        vpub = SATOSHILABS_PUBKEYS;
    }

    if (!vsig_m || !vsig_n) return false;
    if (vsig_m > vsig_n) return false;

    // discard bits higher than vsig_n
    sigmask &= ((1 << vsig_n) - 1);

    // remove if number of set bits in sigmask is not equal to vsig_m
    if (__builtin_popcount(sigmask) != vsig_m) return false;

    ed25519_public_key keys[vsig_m];
    int j = 0;
    for (int i = 0; i < vsig_n; i++) {
        if ((1 << i) & sigmask) {
            memcpy(keys[j], vpub[i], 32);
            j++;
        }
    }

    return 0 == ed25519_cosi_combine_publickeys(res, keys, vsig_m);
}

bool image_parse_header(const uint8_t *data, uint32_t magic, uint32_t maxsize, image_header *hdr)
{
    if (!hdr) {
        image_header h;
        hdr = &h;
    }

    memcpy(&hdr->magic, data, 4);
    if (hdr->magic != magic) return false;

    memcpy(&hdr->hdrlen, data + 4, 4);
    if (hdr->hdrlen != HEADER_SIZE) return false;

    memcpy(&hdr->expiry, data + 8, 4);
    if (hdr->expiry != 0) return false;

    memcpy(&hdr->codelen, data + 12, 4);
    if (hdr->hdrlen + hdr->codelen < 4 * 1024) return false;
    if (hdr->hdrlen + hdr->codelen > maxsize) return false;
    if ((hdr->hdrlen + hdr->codelen) % 512 != 0) return false;

    memcpy(&hdr->version, data + 16, 4);

    // uint8_t reserved[427];

    memcpy(&hdr->sigmask, data + 0x01BF, 1);

    memcpy(hdr->sig, data + 0x01C0, 64);

    return true;
}

bool image_check_signature(const uint8_t *data, const image_header *hdr, const vendor_header *vhdr)
{
    uint8_t hash[BLAKE2S_DIGEST_LENGTH];
    BLAKE2S_CTX ctx;
    blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
    blake2s_Update(&ctx, data, HEADER_SIZE - 65);
    for (int i = 0; i < 65; i++) {
        blake2s_Update(&ctx, (const uint8_t *)"\x00", 1);
    }
    blake2s_Update(&ctx, data + HEADER_SIZE, hdr->codelen);
    blake2s_Final(&ctx, hash, BLAKE2S_DIGEST_LENGTH);

    ed25519_public_key pub;
    if (!compute_pubkey(vhdr, hdr->sigmask, pub)) return false;

    return 0 == ed25519_sign_open(hash, BLAKE2S_DIGEST_LENGTH, pub, *(const ed25519_signature *)hdr->sig);
}

bool vendor_parse_header(const uint8_t *data, vendor_header *vhdr)
{
    if (!vhdr) {
        vendor_header h;
        vhdr = &h;
    }

    memcpy(&vhdr->magic, data, 4);
    if (vhdr->magic != 0x565A5254) return false; // TRZV

    memcpy(&vhdr->hdrlen, data + 4, 4);

    memcpy(&vhdr->expiry, data + 8, 4);
    if (vhdr->expiry != 0) return false;

    memcpy(&vhdr->version, data + 12, 2);

    memcpy(&vhdr->vsig_m, data + 14, 1);
    memcpy(&vhdr->vsig_n, data + 15, 1);

    if (vhdr->vsig_n > MAX_VENDOR_PUBLIC_KEYS) {
        return false;
    }

    for (int i = 0; i < vhdr->vsig_n; i++) {
        vhdr->vpub[i] = data + 16 + i * 32;
    }
    for (int i = vhdr->vsig_n; i < MAX_VENDOR_PUBLIC_KEYS; i++) {
        vhdr->vpub[i] = 0;
    }

    memcpy(&vhdr->vstr_len, data + 16 + vhdr->vsig_n * 32, 1);

    vhdr->vstr = data + 16 + vhdr->vsig_n * 32 + 1;

    vhdr->vimg = data + 16 + vhdr->vsig_n * 32 + 1 + vhdr->vstr_len;
    // align to 4 bytes
    vhdr->vimg += (-(uintptr_t)vhdr->vimg) & 3;

    // uint8_t reserved[427];

    memcpy(&vhdr->sigmask, data + vhdr->hdrlen - 65, 1);

    memcpy(vhdr->sig, data + vhdr->hdrlen - 64, 64);

    return true;
}

bool vendor_check_signature(const uint8_t *data, const vendor_header *vhdr)
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
    if (!compute_pubkey(NULL, vhdr->sigmask, pub)) return false;

    return 0 == ed25519_sign_open(hash, BLAKE2S_DIGEST_LENGTH, pub, *(const ed25519_signature *)vhdr->sig);
}
