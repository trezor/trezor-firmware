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

#include <trezor_types.h>

#include <sys/linker_utils.h>

__attribute((naked, no_stack_protector)) void clear_unused_stack(void) {
  __asm__ volatile(
      "    MOV     R0, #0              \n"
      "    LDR     R1, =%[sstack]      \n"
      "1:                              \n"
      "    STR     R0, [R1], #4        \n"
      "    CMP     R1, SP              \n"
      "    BNE     1b                  \n"
      "    BX      LR                  \n"
      :  // no output
      : [sstack] "i"((uint32_t)&_stack_section_start)
      :  // no clobber
  );
}
