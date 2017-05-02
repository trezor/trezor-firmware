#ifndef __PROTOBUF_H__
#define __PROTOBUF_H__

#include <stdint.h>
#include <stdbool.h>

#define PB_HEADER_LEN 9

typedef struct {
    uint8_t buf[128];
    uint32_t pos;
    uint32_t len;
} PB_CTX;

void pb_start(PB_CTX *ctx, uint16_t msg_id);
void pb_end(PB_CTX *ctx);

void pb_add_bool(PB_CTX *ctx, uint32_t field_number, bool val);
void pb_add_bytes(PB_CTX *ctx, uint32_t field_number, const uint8_t *val, uint32_t len);
void pb_add_string(PB_CTX *ctx, uint32_t field_number, const char *val);
void pb_add_varint(PB_CTX *ctx, uint32_t field_number, uint32_t val);

bool pb_parse_header(const uint8_t *buf, uint16_t *msg_id, uint32_t *msg_size);
uint32_t pb_read_varint(const uint8_t *buf, uint32_t *num);

#endif
