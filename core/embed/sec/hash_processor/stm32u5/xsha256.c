#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sec/xsha256.h>

static void xsha256_write_block(const uint8_t* block, size_t block_size) {
  size_t ofs = 0;

  while (!__HAL_HASH_GET_FLAG(HASH_FLAG_DINIS)) {
    // wait until we can write whole block
  };

  while (ofs < block_size) {
    HASH->DIN = ((uint32_t*)block)[ofs / 4];
    ofs += 4;
  }

  // !@# fix: we are reading bytes beyond block_size
}

static void xsha256_save_state(xsha256_ctx_t* ctx) {
  while (!__HAL_HASH_GET_FLAG(HASH_FLAG_DINIS)) {
    // wait until we can write whole block
  };

#if XSHA256_CONTEXT_SAVING
  for (size_t i = 0; i < 38; i++) {
    ctx->state[i] = HASH->CSR[i];
  }

  ctx->state_valid = true;
#endif
}

static void xsha256_restore_state(xsha256_ctx_t* ctx) {
  HASH->CR = HASH_CR_ALGO_0 | HASH_CR_ALGO_1 | HASH_CR_DATATYPE_1;
  HASH->CR |= HASH_CR_INIT;

#if XSHA256_CONTEXT_SAVING
  if (ctx->state_valid) {
    for (size_t i = 0; i < 38; i++) {
      HASH->CSR[i] = ctx->state[i];
    }
  }
#endif
}

void xsha256_init(xsha256_ctx_t* ctx) {
  memset(ctx, 0, sizeof(*ctx));

  __HAL_RCC_HASH_CLK_ENABLE();

  ctx->q_exp = 64 + 4;
}

void xsha256_update(xsha256_ctx_t* ctx, const uint8_t* in, size_t inlen) {
  xsha256_restore_state(ctx);

  // if there is any data left in ctx->q, fill it to 64 bytes and process it
  if (ctx->q_size > 0) {
    size_t to_copy = MIN(ctx->q_exp - ctx->q_size, inlen);
    memcpy((uint8_t*)ctx->q + ctx->q_size, in, to_copy);
    in += to_copy;
    inlen -= to_copy;
    ctx->q_size += to_copy;
  }

  if (ctx->q_size == ctx->q_exp) {
    // write ctx->q to HASH->DIN
    xsha256_write_block((uint8_t*)ctx->q, ctx->q_size);
    ctx->q_exp = 64;
    ctx->q_size = 0;
  }

  while (inlen >= ctx->q_exp) {
    xsha256_write_block(in, ctx->q_exp);
    in += ctx->q_exp;
    inlen -= ctx->q_exp;
    ctx->q_exp = 64;
  }

  if (inlen > 0) {
    // store remaining data in ctx->q
    memcpy((uint8_t*)ctx->q, in, inlen);
    ctx->q_size = inlen;
  }

  while (__HAL_HASH_GET_FLAG(HASH_FLAG_BUSY)) {
    // wait until processing is done
  }

  if (ctx->q_exp == 64) {
    // Save state only if we have processed at least one full block
    xsha256_save_state(ctx);
  }
}

void xsha256_digest(xsha256_ctx_t* ctx, uint8_t* out) {
  xsha256_restore_state(ctx);

  xsha256_write_block((uint8_t*)ctx->q, ctx->q_size);

  uint32_t last_word_bits = 8 * (ctx->q_size % sizeof(uint32_t));

  ctx->q_size = 0;

  HASH->STR =
      (HASH->STR & ~HASH_STR_NBLW_Msk) | (last_word_bits << HASH_STR_NBLW_Pos);
  HASH->STR |= HASH_STR_DCAL;

  // Wait until digest calculation is complete
  while (!__HAL_HASH_GET_FLAG(HASH_FLAG_DCIS)) {
    // wait
  }

  // Read the digest
  uint32_t* out_alias = (uint32_t*)out;
  out_alias[0] = __REV(HASH->HR[0]);
  out_alias[1] = __REV(HASH->HR[1]);
  out_alias[2] = __REV(HASH->HR[2]);
  out_alias[3] = __REV(HASH->HR[3]);
  out_alias[4] = __REV(HASH->HR[4]);
  out_alias[5] = __REV(HASH_DIGEST->HR[5]);
  out_alias[6] = __REV(HASH_DIGEST->HR[6]);
  out_alias[7] = __REV(HASH_DIGEST->HR[7]);
}

void xsha256_final(xsha256_ctx_t* ctx, uint8_t* out, const uint8_t* in,
                   size_t inlen) {
  xsha256_restore_state(ctx);

  // if there is any data left in ctx->q, fill it to 64 bytes and process it
  if (ctx->q_size > 0) {
    size_t to_copy = MIN(ctx->q_exp - ctx->q_size, inlen);
    memcpy((uint8_t*)ctx->q + ctx->q_size, in, to_copy);
    in += to_copy;
    inlen -= to_copy;
    ctx->q_size += to_copy;
  }

  if (ctx->q_size == ctx->q_exp) {
    // write ctx->q to HASH->DIN
    xsha256_write_block((uint8_t*)ctx->q, ctx->q_size);
    ctx->q_exp = 64;
    ctx->q_size = 0;
  }

  while (inlen >= ctx->q_exp) {
    xsha256_write_block(in, ctx->q_exp);
    in += ctx->q_exp;
    inlen -= ctx->q_exp;
    ctx->q_exp = 64;
  }

  if (inlen > 0) {
    // store remaining data in ctx->q
    memcpy((uint8_t*)ctx->q, in, inlen);
    ctx->q_size = inlen;
  }

  while (__HAL_HASH_GET_FLAG(HASH_FLAG_BUSY)) {
    // wait until processing is done
  }

  xsha256_write_block((uint8_t*)ctx->q, ctx->q_size);

  uint32_t last_word_bits = 8 * (ctx->q_size % sizeof(uint32_t));

  ctx->q_size = 0;

  HASH->STR =
      (HASH->STR & ~HASH_STR_NBLW_Msk) | (last_word_bits << HASH_STR_NBLW_Pos);
  HASH->STR |= HASH_STR_DCAL;

  // Wait until digest calculation is complete
  while (!__HAL_HASH_GET_FLAG(HASH_FLAG_DCIS)) {
    // wait
  }

  // Read the digest
  uint32_t* out_alias = (uint32_t*)out;
  out_alias[0] = __REV(HASH->HR[0]);
  out_alias[1] = __REV(HASH->HR[1]);
  out_alias[2] = __REV(HASH->HR[2]);
  out_alias[3] = __REV(HASH->HR[3]);
  out_alias[4] = __REV(HASH->HR[4]);
  out_alias[5] = __REV(HASH_DIGEST->HR[5]);
  out_alias[6] = __REV(HASH_DIGEST->HR[6]);
  out_alias[7] = __REV(HASH_DIGEST->HR[7]);
}
