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
    ctx->size = 9;
}

const uint8_t *pb_build(PB_CTX *ctx)
{
    ctx->buf[5] = (ctx->size >> 24) & 0xFF;
    ctx->buf[6] = (ctx->size >> 16) & 0xFF;
    ctx->buf[7] = (ctx->size >> 8) & 0xFF;
    ctx->buf[8] = ctx->size & 0xFF;
    return ctx->buf;
}

static void pb_add_id(PB_CTX *ctx, const char *id)
{
    size_t len = strlen(id);
    memcpy(ctx->buf + ctx->size, id, len);
    ctx->buf[ctx->size] += len;
}

void pb_add_bool(PB_CTX *ctx, const char *id, bool val)
{
    pb_add_id(ctx, id);
    ctx->buf[ctx->size] = val;
    ctx->size++;
}

void pb_add_string(PB_CTX *ctx, const char *id, const char *val)
{
    pb_add_varint(ctx, id, strlen(val));
    size_t len = strlen(val);
    memcpy(ctx->buf + ctx->size, val, len);
    ctx->buf[ctx->size] += len;
}

void pb_add_varint(PB_CTX *ctx, const char *id, uint32_t val)
{
    pb_add_id(ctx, id);
    for (;;) {
        if (val < 0x80) {
            ctx->buf[ctx->size] = val;
            ctx->size++;
            break;
        } else {
            ctx->buf[ctx->size] = (val & 0x7F) | 0x80;
            ctx->size++;
            val >>= 7;
        }
    }
}
