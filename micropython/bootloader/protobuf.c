#include <string.h>
#include "protobuf.h"

void pb_start(PB_CTX *ctx, uint16_t msg_id)
{
    memset(ctx->buf, 0, sizeof(ctx->buf));
    ctx->buf[0] = '?';
    ctx->buf[1] = '#';
    ctx->buf[2] = '#';
    ctx->buf[3] = (msg_id >> 8) & 0xFF;
    ctx->buf[4] = msg_id & 0xFF;
    ctx->pos = 9;
    ctx->len = 0;
}

void pb_end(PB_CTX *ctx)
{
    ctx->buf[5] = (ctx->len >> 24) & 0xFF;
    ctx->buf[6] = (ctx->len >> 16) & 0xFF;
    ctx->buf[7] = (ctx->len >> 8) & 0xFF;
    ctx->buf[8] = ctx->len & 0xFF;
    // align to 64 bytes
    ctx->pos += (-ctx->pos) & 63;
}

inline static void pb_append(PB_CTX *ctx, uint8_t b)
{
    ctx->buf[ctx->pos] = b;
    ctx->pos++;
    if (ctx->pos % 64 == 0) {
        ctx->buf[ctx->pos] = '?';
        ctx->pos++;
    }
    ctx->len++;
}

static void pb_varint(PB_CTX *ctx, uint32_t val)
{
    for (;;) {
        if (val < 0x80) {
            pb_append(ctx, val & 0x7F);
            break;
        } else {
            pb_append(ctx, (val & 0x7F) | 0x80);
            val >>= 7;
        }
    }
}

void pb_add_bool(PB_CTX *ctx, uint32_t field_number, bool val)
{
    field_number = (field_number << 3) | 0;
    pb_varint(ctx, field_number);
    pb_append(ctx, val);
}

void pb_add_string(PB_CTX *ctx, uint32_t field_number, const char *val)
{
    field_number = (field_number << 3) | 2;
    pb_varint(ctx, field_number);
    size_t len = strlen(val);
    pb_varint(ctx, len);
    for (size_t i = 0; i < len; i++) {
        pb_append(ctx, val[i]);
    }
}

void pb_add_varint(PB_CTX *ctx, uint32_t field_number, uint32_t val)
{
    field_number = (field_number << 3) | 0;
    pb_varint(ctx, field_number);
    pb_varint(ctx, val);
}
