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

#include "random_delays.h"

#include <stdbool.h>

#include "chacha_drbg.h"
#include "common.h"
#include "drbg.h"
#include "memzero.h"
#include "rand.h"

// from util.s
extern void shutdown(void);

#define BUFFER_LENGTH 64

static uint8_t session_delay;
static bool refresh_session_delay;
static secbool rdi_disabled = sectrue;

static uint32_t random8(void) {
  static size_t buffer_index = 0;
  static uint8_t buffer[BUFFER_LENGTH];

  if (buffer_index == 0) {
    drbg_generate(buffer, sizeof(buffer));
  }

  uint8_t value = buffer[buffer_index];
  memzero(&buffer[buffer_index], 1);
  buffer_index = (buffer_index + 1) % sizeof(buffer);
  return value;
}

void rdi_refresh_session_delay(void) {
  if (rdi_disabled == secfalse)  // if rdi enabled
    refresh_session_delay = true;
}

static void wait(uint32_t delay) {
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
}

void rdi_handler(uint32_t uw_tick) {
  if (rdi_disabled == secfalse) {  // if rdi enabled
    if (refresh_session_delay) {
      session_delay = random8();
      refresh_session_delay = false;
    }

    wait(random8() + session_delay);

  } else {  // if rdi disabled or rdi_disabled corrupted
    ensure(rdi_disabled, "Fault detected");
  }
}

void rdi_start(void) {
  if (rdi_disabled == sectrue) {  // if rdi disabled
    refresh_session_delay = true;
    rdi_disabled = secfalse;
  }
}

void rdi_stop(void) {
  if (rdi_disabled == secfalse) {  // if rdi enabled
    rdi_disabled = sectrue;
    session_delay = 0;
  }
}

/*
 * Generates a delay of random length. Use this to protect sensitive code
 * against fault injection.
 */
void wait_random(void) {
  int wait = random8();
  volatile int i = 0;
  volatile int j = wait;
  while (i < wait) {
    if (i + j != wait) {
      shutdown();
    }
    ++i;
    --j;
  }
  // Double-check loop completion.
  if (i != wait || j != 0) {
    shutdown();
  }
}
