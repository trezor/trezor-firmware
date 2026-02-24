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

#include <trezor_bsp.h>
#include <trezor_model.h>

#include <sec/hdp.h>
#include <sys/irq.h>

#include "sys/mpu.h"

#ifdef BOARDLOADER
__attribute__((section(".hdp"), naked, noreturn, no_stack_protector)) void
hdp_close_helper(uint32_t vectbl_addr) {
  __asm__ volatile(
      /*
         R0 contains vectbl_addr (first argument of naked function).
         Set HDP area extension to cover SECRET + BOOTLOADER sections.
         We use R1 and R2 as scratch registers.
      */
      "LDR      R1, =0x50022000    \n"  // FLASH_R_BASE_S
      "LDR      R2, =%[SECHDPEXTR_VAL] \n"
      "STR      R2, [R1, #0xC8]   \n"  // FLASH_SECHDPEXTR offset is 0xC8
                                       // (secure)

      /*
         Now we need to get CloseExitHDPExt address from RSSLIB_PFUNC.
         R0 still contains vectbl_addr because we only touched R1 and R2.
      */
      "LDR      R12, =%[RSSLIB_PFUNC_VAL] \n"
      "LDR      R12, [R12, #0x2C]  \n"  // CloseExitHDPExt is at offset 0x2C
                                        // (0x0C + 0x20)

      "MOV      R1, R0             \n"  // VectorTableAddr
      "LDR      R0, =%[HDP_AREA]   \n"  // HdpArea
      "LDR      R2, =0xD6D6D6D6    \n"  // CloseBound

      "BX       R12                \n"  // Jump to RSS service

      :  // no output
      : [RSSLIB_PFUNC_VAL] "i"(RSSLIB_PFUNC_BASE), [HDP_AREA] "i"(1UL),
        [SECHDPEXTR_VAL] "i"((HDP_SECTOR_END + 1)
                             << FLASH_SECHDPEXTR_HDP1_EXT_Pos)
      : "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9", "r10",
        "r11", "r12", "cc");
}
#else
// hdp_close_helper is not accessible directly outside of BOARDLOADER.
// We jump to HDP_START address instead.
#endif

void hdp_close(void) {
  irq_key_t key = irq_lock();
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_DISABLED);

  uint32_t current_msp;
  __asm__ volatile("MRS %0, msp" : "=r"(current_msp));

  uint32_t mocked_vectbl[2] __attribute__((aligned(8)));
  mocked_vectbl[0] = current_msp;  // Capture current MSP

  // We use a volatile pointer to the label and a dummy conditional branch
  // to prevent the compiler from optimizing out the label or giving it
  // a wrong address (like the beginning of the function).
  void *volatile return_label_ptr = &&hdp_close_return;

  // Dummy condition that is never true but forces the compiler to keep the
  // label
  if (__builtin_expect(current_msp == 0, 0)) {
    goto hdp_close_return;
  }

  mocked_vectbl[1] =
      (uint32_t)return_label_ptr | 1;  // Mocked Reset Handler (with Thumb bit)

  // Use a pointer for the vector table and ensure the compiler treats it as
  // a memory operand that's modified.
  uint32_t vectbl_addr = (uint32_t)mocked_vectbl;

  __asm__ volatile(
      "MOV      R0, %[VECTBL]      \n"
      "LDR      R1, =%[HDP_START_VAL]\n"
      "ORRS     R1, #1             \n"  // Set Thumb bit
      "BLX      R1                 \n"
      :
      : [VECTBL] "r"(vectbl_addr), [HDP_START_VAL] "i"(HDP_START),
        "m"(mocked_vectbl)
      : "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9", "r10",
        "r11", "r12", "memory", "cc");

hdp_close_return:
  mpu_restore(mode);
  irq_unlock(key);
}
