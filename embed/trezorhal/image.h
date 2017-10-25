#ifndef __TREZORHAL_IMAGE_H__
#define __TREZORHAL_IMAGE_H__

#include <stdint.h>
#include <stdbool.h>

#define BOARDLOADER_START  0x08000000
#define BOOTLOADER_START   0x08020000
#define FIRMWARE_START     0x08040000
#define IMAGE_HEADER_SIZE  0x200

typedef struct {
    uint32_t magic;
    uint32_t hdrlen;
    uint32_t expiry;
    uint32_t codelen;
    uint32_t version;
    // uint8_t reserved[427];
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
    // uint8_t reserved[16];
    const uint8_t *vpub[MAX_VENDOR_PUBLIC_KEYS];
    uint8_t vstr_len;
    const uint8_t *vstr;
    const uint8_t *vimg;
    uint8_t sigmask;
    uint8_t sig[64];
} vendor_header;

bool image_parse_header(const uint8_t * const data, const uint32_t magic, const uint32_t maxsize, image_header * const hdr);

bool image_check_signature(const uint8_t *data, const image_header *hdr, uint8_t key_m, uint8_t key_n, const uint8_t * const *keys);

bool vendor_parse_header(const uint8_t * const data, vendor_header * const vhdr);

bool vendor_check_signature(const uint8_t *data, const vendor_header *vhdr, uint8_t key_m, uint8_t key_n, const uint8_t * const *keys);

#endif
