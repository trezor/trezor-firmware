#ifndef __PROTOBUF_H__
#define __PROTOBUF_H__

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint8_t buf[128];
    uint32_t pos;
    uint32_t len;
} PB_CTX;

void pb_start(PB_CTX *ctx, uint16_t msg_id);
void pb_end(PB_CTX *ctx);

void pb_add_bool(PB_CTX *ctx, uint32_t field_number, bool val);
void pb_add_string(PB_CTX *ctx, uint32_t field_number, const char *val);
void pb_add_varint(PB_CTX *ctx, uint32_t field_number, uint32_t val);

bool pb_parse_header(const uint8_t *buf, uint16_t *msg_id, uint32_t *msg_size);

#endif
