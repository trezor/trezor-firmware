/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

// clang-format off

/*
 * stream_inflate  -  tiny inflate library with output streaming
 *
 * Copyright (c) 2003 by Joergen Ibsen / Jibz
 * All Rights Reserved
 * http://www.ibsensoftware.com/
 *
 * Copyright (c) 2014 by Paul Sokolovsky
 *
 * Copyright (c) 2016 by Pavol Rusnak
 *
 * This software is provided 'as-is', without any express
 * or implied warranty.  In no event will the authors be
 * held liable for any damages arising from the use of
 * this software.
 *
 * Permission is granted to anyone to use this software
 * for any purpose, including commercial applications,
 * and to alter it and redistribute it freely, subject to
 * the following restrictions:
 *
 * 1. The origin of this software must not be
 *    misrepresented; you must not claim that you
 *    wrote the original software. If you use this
 *    software in a product, an acknowledgment in
 *    the product documentation would be appreciated
 *    but is not required.
 *
 * 2. Altered source versions must be plainly marked
 *    as such, and must not be misrepresented as
 *    being the original software.
 *
 * 3. This notice may not be removed or altered from
 *    any source distribution.
 */

#include "inflate.h"

// maximum possible window size (in bits) used during compression/deflate
#define SINF_WBITS     10

#define SINF_OK         0
#define SINF_ERROR    (-3)

typedef struct {
   uint16_t table[16];  /* table of code length counts */
   uint16_t trans[288]; /* code -> symbol translation table */
} SINF_TREE;

typedef struct {
   const uint8_t *source;
   uint32_t sourcelen;
   uint32_t tag;
   uint32_t bitcount;
   uint8_t cbuf[1 << SINF_WBITS];
   int cbufi;
   SINF_TREE ltree; /* dynamic length/symbol tree */
   SINF_TREE dtree; /* dynamic distance tree */
   void (* write)(uint8_t byte, uint32_t pos, void *userdata);
   void *userdata;
   uint32_t written;
} SINF_CTX;

/* --------------------------------------------------- *
 * -- uninitialized global data (static structures) -- *
 * --------------------------------------------------- */

static const uint8_t SINF_LENGTH_BITS[30] = {
   0, 0, 0, 0, 0, 0, 0, 0,
   1, 1, 1, 1, 2, 2, 2, 2,
   3, 3, 3, 3, 4, 4, 4, 4,
   5, 5, 5, 5
};
static const uint16_t SINF_LENGTH_BASE[30] = {
   3, 4, 5, 6, 7, 8, 9, 10,
   11, 13, 15, 17, 19, 23, 27, 31,
   35, 43, 51, 59, 67, 83, 99, 115,
   131, 163, 195, 227, 258
};

static const uint8_t SINF_DIST_BITS[30] = {
   0, 0, 0, 0, 1, 1, 2, 2,
   3, 3, 4, 4, 5, 5, 6, 6,
   7, 7, 8, 8, 9, 9, 10, 10,
   11, 11, 12, 12, 13, 13
};
static const uint16_t SINF_DIST_BASE[30] = {
   1, 2, 3, 4, 5, 7, 9, 13,
   17, 25, 33, 49, 65, 97, 129, 193,
   257, 385, 513, 769, 1025, 1537, 2049, 3073,
   4097, 6145, 8193, 12289, 16385, 24577
};

/* special ordering of code length codes */
static const uint8_t SINF_CLCIDX[] = {
   16, 17, 18, 0, 8, 7, 9, 6,
   10, 5, 11, 4, 12, 3, 13, 2,
   14, 1, 15
};

/* ----------------------- *
 * -- utility functions -- *
 * ----------------------- */

static void sinf_write(SINF_CTX *ctx, uint8_t byte)
{
    ctx->cbuf[ctx->cbufi] = byte;
    ctx->cbufi = (ctx->cbufi + 1) % (1 << SINF_WBITS);
    ctx->write(byte, ctx->written, ctx->userdata);
    ctx->written++;
}

/* build the fixed huffman trees */
static void sinf_build_fixed_trees(SINF_TREE *lt, SINF_TREE *dt)
{
   int i;

   /* build fixed length tree */
   for (i = 0; i < 7; ++i) lt->table[i] = 0;

   lt->table[7] = 24;
   lt->table[8] = 152;
   lt->table[9] = 112;

   for (i = 0; i < 24; ++i) lt->trans[i] = 256 + i;
   for (i = 0; i < 144; ++i) lt->trans[24 + i] = i;
   for (i = 0; i < 8; ++i) lt->trans[24 + 144 + i] = 280 + i;
   for (i = 0; i < 112; ++i) lt->trans[24 + 144 + 8 + i] = 144 + i;

   /* build fixed distance tree */
   for (i = 0; i < 5; ++i) dt->table[i] = 0;

   dt->table[5] = 32;

   for (i = 0; i < 32; ++i) dt->trans[i] = i;
}

/* given an array of code lengths, build a tree */
static void sinf_build_tree(SINF_TREE *t, const uint8_t *lengths, uint32_t num)
{
   uint16_t offs[16];
   uint32_t i, sum;

   /* clear code length count table */
   for (i = 0; i < 16; ++i) t->table[i] = 0;

   /* scan symbol lengths, and sum code length counts */
   for (i = 0; i < num; ++i) t->table[lengths[i]]++;

   t->table[0] = 0;

   /* compute offset table for distribution sort */
   for (sum = 0, i = 0; i < 16; ++i)
   {
      offs[i] = sum;
      sum += t->table[i];
   }

   /* create code->symbol translation table (symbols sorted by code) */
   for (i = 0; i < num; ++i)
   {
      if (lengths[i]) t->trans[offs[lengths[i]]++] = i;
   }
}

/* ---------------------- *
 * -- decode functions -- *
 * ---------------------- */

/* get one bit from source stream */
static int sinf_getbit(SINF_CTX *ctx)
{
   uint32_t bit;

   /* check if tag is empty */
   if (!ctx->bitcount--)
   {
      /* load next tag */
      ctx->tag = *ctx->source++;
      ctx->bitcount = 7;
   }

   /* shift bit out of tag */
   bit = ctx->tag & 0x01;
   ctx->tag >>= 1;

   return bit;
}

/* read a num bit value from a stream and add base */
static uint32_t sinf_read_bits(SINF_CTX *ctx, int num, int base)
{
   uint32_t val = 0;

   /* read num bits */
   if (num)
   {
      uint32_t limit = 1 << (num);
      uint32_t mask;

      for (mask = 1; mask < limit; mask *= 2)
         if (sinf_getbit(ctx)) val += mask;
   }

   return val + base;
}

/* given a data stream and a tree, decode a symbol */
static int sinf_decode_symbol(SINF_CTX *ctx, SINF_TREE *t)
{
   int sum = 0, cur = 0, len = 0;

   /* get more bits while code value is above sum */
   do {

      cur = 2*cur + sinf_getbit(ctx);

      ++len;

      sum += t->table[len];
      cur -= t->table[len];

   } while (cur >= 0);

   return t->trans[sum + cur];
}

/* given a data stream, decode dynamic trees from it */
static void sinf_decode_trees(SINF_CTX *ctx, SINF_TREE *lt, SINF_TREE *dt)
{
   uint8_t lengths[288+32];
   uint32_t hlit, hdist, hclen;
   uint32_t i, num, length;

   /* get 5 bits HLIT (257-286) */
   hlit = sinf_read_bits(ctx, 5, 257);

   /* get 5 bits HDIST (1-32) */
   hdist = sinf_read_bits(ctx, 5, 1);

   /* get 4 bits HCLEN (4-19) */
   hclen = sinf_read_bits(ctx, 4, 4);

   for (i = 0; i < 19; ++i) lengths[i] = 0;

   /* read code lengths for code length alphabet */
   for (i = 0; i < hclen; ++i)
   {
      /* get 3 bits code length (0-7) */
      uint32_t clen = sinf_read_bits(ctx, 3, 0);

      lengths[SINF_CLCIDX[i]] = clen;
   }

   /* build code length tree, temporarily use length tree */
   sinf_build_tree(lt, lengths, 19);

   /* decode code lengths for the dynamic trees */
   for (num = 0; num < hlit + hdist; )
   {
      int sym = sinf_decode_symbol(ctx, lt);

      switch (sym)
      {
      case 16:
         /* copy previous code length 3-6 times (read 2 bits) */
         {
            uint8_t prev = lengths[num - 1];
            for (length = sinf_read_bits(ctx, 2, 3); length; --length)
            {
               lengths[num++] = prev;
            }
         }
         break;
      case 17:
         /* repeat code length 0 for 3-10 times (read 3 bits) */
         for (length = sinf_read_bits(ctx, 3, 3); length; --length)
         {
            lengths[num++] = 0;
         }
         break;
      case 18:
         /* repeat code length 0 for 11-138 times (read 7 bits) */
         for (length = sinf_read_bits(ctx, 7, 11); length; --length)
         {
            lengths[num++] = 0;
         }
         break;
      default:
         /* values 0-15 represent the actual code lengths */
         lengths[num++] = sym;
         break;
      }
   }

   /* build dynamic trees */
   sinf_build_tree(lt, lengths, hlit);
   sinf_build_tree(dt, lengths + hlit, hdist);
}

/* ----------------------------- *
 * -- block inflate functions -- *
 * ----------------------------- */

/* given a stream and two trees, inflate a block of data */
static int sinf_inflate_block_data(SINF_CTX *ctx, SINF_TREE *lt, SINF_TREE *dt)
{
   while (1)
   {
      int sym = sinf_decode_symbol(ctx, lt);

      /* check for end of block */
      if (sym == 256)
      {
         return SINF_OK;
      }

      if (sym < 256)
      {
         sinf_write(ctx, sym);
      } else {

         uint32_t length, offs, i;
         int dist;

         sym -= 257;

         /* possibly get more bits from length code */
         length = sinf_read_bits(ctx, SINF_LENGTH_BITS[sym], SINF_LENGTH_BASE[sym]);

         dist = sinf_decode_symbol(ctx, dt);

         /* possibly get more bits from distance code */
         offs = sinf_read_bits(ctx, SINF_DIST_BITS[dist], SINF_DIST_BASE[dist]);

         /* copy match */
         for (i = 0; i < length; ++i)
         {
            sinf_write(ctx, ctx->cbuf[(ctx->cbufi + (1 << SINF_WBITS) - offs) % (1 << SINF_WBITS)]);
         }
      }
   }
}

/* inflate an uncompressed block of data */
static int sinf_inflate_uncompressed_block(SINF_CTX *ctx)
{
   uint32_t length, invlength;
   uint32_t i;

   /* get length */
   length = ctx->source[1];
   length = 256*length + ctx->source[0];

   /* get one's complement of length */
   invlength = ctx->source[3];
   invlength = 256*invlength + ctx->source[2];

   /* check length */
   if (length != (~invlength & 0x0000ffff)) return SINF_ERROR;

   ctx->source += 4;

   /* copy block */
   for (i = length; i; --i) sinf_write(ctx, *ctx->source++);

   /* make sure we start next block on a byte boundary */
   ctx->bitcount = 0;

   return SINF_OK;
}

/* inflate a block of data compressed with fixed huffman trees */
static int sinf_inflate_fixed_block(SINF_CTX *ctx)
{
   /* build fixed huffman trees */
   sinf_build_fixed_trees(&ctx->ltree, &ctx->dtree);

   /* decode block using fixed trees */
   return sinf_inflate_block_data(ctx, &ctx->ltree, &ctx->dtree);
}

/* inflate a block of data compressed with dynamic huffman trees */
static int sinf_inflate_dynamic_block(SINF_CTX *ctx)
{
   /* decode trees from stream */
   sinf_decode_trees(ctx, &ctx->ltree, &ctx->dtree);

   /* decode block using decoded trees */
   return sinf_inflate_block_data(ctx, &ctx->ltree, &ctx->dtree);
}

/* ---------------------- *
 * -- public functions -- *
 * ---------------------- */

/* inflate stream from source */
int sinf_inflate(const uint8_t *data, uint32_t datalen, void (*write_callback)(uint8_t byte, uint32_t pos, void *userdata), void *userdata)
{
   SINF_CTX ctx;
   int bfinal;

   /* initialise data */
   ctx.bitcount = 0;
   ctx.cbufi = 0;
   ctx.source = data;
   ctx.sourcelen = datalen;
   ctx.write = write_callback;
   ctx.userdata = userdata;
   ctx.written = 0;

   do {

      uint32_t btype;
      int res;

      /* read final block flag */
      bfinal = sinf_getbit(&ctx);

      /* read block type (2 bits) */
      btype = sinf_read_bits(&ctx, 2, 0);

      /* decompress block */
      switch (btype)
      {
      case 0:
         /* decompress uncompressed block */
         res = sinf_inflate_uncompressed_block(&ctx);
         break;
      case 1:
         /* decompress block with fixed huffman trees */
         res = sinf_inflate_fixed_block(&ctx);
         break;
      case 2:
         /* decompress block with dynamic huffman trees */
         res = sinf_inflate_dynamic_block(&ctx);
         break;
      default:
         return SINF_ERROR;
      }

      if (res != SINF_OK) return SINF_ERROR;

   } while (!bfinal);

   return SINF_OK;
}
