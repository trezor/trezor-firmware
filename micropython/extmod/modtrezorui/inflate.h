#ifndef __INFLATE_H__
#define __INFLATE_H__

#include <stdint.h>

int sinf_inflate(const uint8_t *data, uint32_t datalen, void (*write_callback)(uint8_t byte, uint32_t pos, void *userdata), void *userdata);

#endif
