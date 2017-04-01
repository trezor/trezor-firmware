#ifndef __TREZORHAL_IMAGE_H__
#define __TREZORHAL_IMAGE_H__

#include <stdint.h>
#include <stdbool.h>

#include "image_options.h"

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

typedef struct {
    uint32_t magic;
    uint32_t hdrlen;
    uint32_t expiry;
    uint16_t version;
    uint8_t vsig_m;
    uint8_t vsig_n;
    const uint8_t *vpub[8];
    uint8_t vstr_len;
    const uint8_t *vstr;
    const uint8_t *vimg;
    uint8_t sigmask;
    uint8_t sig[64];
} vendor_header;

bool image_parse_header(const uint8_t *data, image_header *header);

bool image_check_signature(const uint8_t *data, const vendor_header *vhdr);

bool vendor_parse_header(const uint8_t *data, vendor_header *header);

bool vendor_check_signature(const uint8_t *data);

#endif
