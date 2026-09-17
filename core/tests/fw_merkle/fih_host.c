/*
 * FIH runtime symbols for the host founder-verification harnesses.
 *
 * Mirrors boot/bootutil/src/fault_injection_hardening.c, whose fih_panic_loop()
 * is Cortex-M assembly; on the host a panic aborts instead of spinning.
 * Keep the constants in step with mcuboot's copy.
 */
#include <stdio.h>
#include <stdlib.h>

#include "bootutil/fault_injection_hardening.h"

#ifdef FIH_ENABLE_DOUBLE_VARS
volatile int _fih_mask = _FIH_MASK_VALUE;
#endif

fih_ret FIH_SUCCESS = FIH_POSITIVE_VALUE;
fih_ret FIH_FAILURE = FIH_NEGATIVE_VALUE;
fih_ret FIH_NO_BOOTABLE_IMAGE = FIH_CONST1;
fih_ret FIH_BOOT_HOOK_REGULAR = FIH_CONST2;

#ifdef FIH_ENABLE_CFI

#ifdef FIH_ENABLE_DOUBLE_VARS
fih_int _fih_cfi_ctr = {0, 0 ^ _FIH_MASK_VALUE};
#else
fih_int _fih_cfi_ctr = {0};
#endif

fih_int fih_cfi_get_and_increment(void) {
  fih_int saved = _fih_cfi_ctr;
  _fih_cfi_ctr = fih_int_encode(fih_int_decode(saved) + 1);
  return saved;
}

void fih_cfi_validate(fih_int saved) {
  if (fih_int_decode(saved) != fih_int_decode(_fih_cfi_ctr)) {
    FIH_PANIC;
  }
}

void fih_cfi_decrement(void) {
  _fih_cfi_ctr = fih_int_encode(fih_int_decode(_fih_cfi_ctr) - 1);
}

#endif /* FIH_ENABLE_CFI */

#ifdef FIH_ENABLE_GLOBAL_FAIL
/* A FIH panic on the host means the harness itself is wrong: abort, never spin.
 */
__attribute__((used)) __attribute__((noinline)) __attribute__((noreturn)) void
fih_panic_loop(void) {
  fprintf(stderr,
          "FAIL: FIH_PANIC -- CFI counter mismatch or double-var "
          "tamper detected in the host harness\n");
  abort();
}
#endif
