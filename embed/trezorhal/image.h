#ifndef __TREZORHAL_IMAGE_H__
#define __TREZORHAL_IMAGE_H__

#include <stdint.h>
#include "secbool.h"

#define BOARDLOADER_START  0x08000000
#define BOOTLOADER_START   0x08020000
#define FIRMWARE_START     0x08040000

#define IMAGE_HEADER_SIZE  0x400
#define IMAGE_SIG_SIZE     65
#define IMAGE_CHUNK_SIZE   (128 * 1024)

typedef struct {
    uint32_t magic;
    uint32_t hdrlen;
    uint32_t expiry;
    uint32_t codelen;
    uint32_t version;
    // uint8_t reserved[12];
    uint8_t hashes[512];
    // uint8_t reserved[415];
    uint8_t sigmask;
    uint8_t sig[64];
} image_header;

#define MAX_VENDOR_PUBLIC_KEYS 8

typedef struct {
    uint32_t magic;
    uint32_t hdrlen;
    uint32_t expiry;
    uint16_t version;
    uint8_t vsig_m;
    uint8_t vsig_n;
    uint8_t vtrust;
    // uint8_t reserved[15];
    const uint8_t *vpub[MAX_VENDOR_PUBLIC_KEYS];
    uint8_t vstr_len;
    const uint8_t *vstr;
    const uint8_t *vimg;
    uint8_t sigmask;
    uint8_t sig[64];
} vendor_header;

secbool load_image_header(const uint8_t * const data, const uint32_t magic, const uint32_t maxsize, uint8_t key_m, uint8_t key_n, const uint8_t * const *keys, image_header * const hdr);

secbool load_vendor_header(const uint8_t * const data, uint8_t key_m, uint8_t key_n, const uint8_t * const *keys, vendor_header * const vhdr);

secbool check_image_contents(const image_header * const hdr, uint32_t firstskip, const uint8_t *sectors, int blocks);

#endif
