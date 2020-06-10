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

/*
Random delay interrupts (RDI) is a contermeasure agains side channel attacks. It
consists of an interrupt handler that is supposed to be called every millisecond
or so. The handler waits for a random number of cpu ticks that is a sample of so
called floating mean distribution. That means that the number is the sum of two
numbers generated uniformly at random in the interval [0, 255]. The first number
is generated freshly for each call of the handler, the other number is supposed
to be refreshed when the device performs an operation that leaks the current
state of the execution flow, such as sending or receiving an usb packet.

See Differential Power Analysis in the Presence of Hardware Countermeasures by
Christophe Clavier, Jean-Sebastien Coron, Nora Dabbous and Efficient Use of
Random Delays in Embedded Software by Michael Tunstall, Olivier Benoit:
https://link.springer.com/content/pdf/10.1007%2F3-540-44499-8_20.pdf
https://link.springer.com/content/pdf/10.1007%2F978-3-540-72354-7_3.pdf
*/

#include "rdi.h"

#include <stdbool.h>

#include "chacha_drbg.h"
#include "common.h"
#include "memzero.h"
#include "rand.h"
#include "secbool.h"

#define BUFFER_LENGTH 64
#define RESEED_INTERVAL 65536

static CHACHA_DRBG_CTX drbg_ctx;
static uint8_t buffer[BUFFER_LENGTH];
static size_t buffer_index;
static uint8_t session_delay;
static bool refresh_session_delay;
static secbool rdi_disabled = sectrue;

static void rdi_reseed(void) {
  uint8_t entropy[CHACHA_DRBG_SEED_LENGTH];
  random_buffer(entropy, CHACHA_DRBG_SEED_LENGTH);
  chacha_drbg_reseed(&drbg_ctx, entropy);
}

static void buffer_refill(void) {
  chacha_drbg_generate(&drbg_ctx, buffer, BUFFER_LENGTH);
}

static uint32_t random8(void) {
  buffer_index += 1;
  if (buffer_index >= BUFFER_LENGTH) {
    buffer_refill();
    if (RESEED_INTERVAL != 0 && drbg_ctx.reseed_counter > RESEED_INTERVAL)
      rdi_reseed();
    buffer_index = 0;
  }
  return buffer[buffer_index];
}

void rdi_refresh_session_delay(void) {
  if (rdi_disabled == secfalse)  // if rdi enabled
    refresh_session_delay = true;
}

void rdi_handler(uint32_t uw_tick) {
  if (rdi_disabled == secfalse) {  // if rdi enabled
    if (refresh_session_delay) {
      session_delay = random8();
      refresh_session_delay = false;
    }

    uint32_t delay = random8() + session_delay;

    // wait (30 + delay) ticks
    asm volatile(
        "ldr r0, %0;"  // r0 = delay
        "loop:"
        "subs r0, $3;"  // r0 -= 3
        "bhs loop;"     // if (r0 >= 3): goto loop
        // loop (delay // 3) times
        // every loop takes 3 ticks
        // r0 == (delay % 3) - 3
        "add r0, $3;"  // r0 += 3
        // r0 == delay % 3
        "and r0, r0, $3;"  // r0 %= 4, make sure that 0 <= r0 < 4
        "ldr r1, =table;"  // r1 = &table
        "tbb [r1, r0];"    // jump 2*r1[r0] bytes forward, that is goto wait_r0
        "base:"
        "table:"  // table of branch lengths
        ".byte (wait_0 - base)/2;"
        ".byte (wait_1 - base)/2;"
        ".byte (wait_2 - base)/2;"
        ".byte (wait_2 - base)/2;"  // next instruction must be 2-byte aligned
        "wait_2:"
        "add r0, $1;"  // wait one tick
        "wait_1:"
        "add r0, $1;"  // wait one tick
        "wait_0:"
        :
        : "m"(delay)
        : "r0", "r1");
  } else {  // if rdi disabled or rdi_disabled corrupted
    ensure(rdi_disabled, "Fault detected");
  }
}

void rdi_start(void) {
  if (rdi_disabled == sectrue) {  // if rdi disabled
    uint8_t entropy[CHACHA_DRBG_SEED_LENGTH];
    random_buffer(entropy, CHACHA_DRBG_SEED_LENGTH);
    chacha_drbg_init(&drbg_ctx, entropy);
    buffer_refill();
    buffer_index = 0;
    refresh_session_delay = true;
    rdi_disabled = secfalse;
  }
}

void rdi_stop(void) {
  if (rdi_disabled == secfalse) {  // if rdi enabled
    rdi_disabled = sectrue;
    session_delay = 0;
    memzero(&drbg_ctx, sizeof(drbg_ctx));
  }
}
