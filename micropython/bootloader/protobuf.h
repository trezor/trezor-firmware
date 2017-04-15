#ifndef __PROTOBUF_H__
#define __PROTOBUF_H__

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint8_t buf[64];
    uint32_t size;
} PB_CTX;

void pb_start(PB_CTX *ctx, uint16_t msg_id);
const uint8_t *pb_build(PB_CTX *ctx);

void pb_add_bool(PB_CTX *ctx, const char *id, bool val);
void pb_add_string(PB_CTX *ctx, const char *id, const char *val);
void pb_add_varint(PB_CTX *ctx, const char *id, uint32_t val);

#endif
