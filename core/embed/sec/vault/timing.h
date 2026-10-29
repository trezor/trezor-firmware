/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stdint.h>

/* Per-phase cycle counts of one vault syscall. Built only with
 * TREZOR_VAULT_TIMING=1 and logged by the vault module at info level; the
 * emulator has no cycle counter and reports zeros. Private to the vault. */
typedef struct {
  uint32_t unwrap; /* record keys through vault_kek */
  uint32_t expand; /* AES key schedules */
  uint32_t record; /* sealing and opening records */
  uint32_t records;
} vault_timing_t;

#ifdef VAULT_TIMING
extern vault_timing_t vault_timing;
#if defined(TREZOR_EMULATOR) || defined(VAULT_TEST)
static inline uint32_t vault_cycles(void) { return 0; }
#else
#include <trezor_bsp.h>
static inline uint32_t vault_cycles(void) {
  if (!(DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk)) {
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
  }
  return DWT->CYCCNT;
}
#endif
#define VAULT_TIMING_ADD(field, start) \
  (vault_timing.field += vault_cycles() - (start))
#else
static inline uint32_t vault_cycles(void) { return 0; }
#define VAULT_TIMING_ADD(field, start) ((void)(start))
#endif
