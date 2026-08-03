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

#include <sys/reset_flags.h>

#ifdef KERNEL_MODE

// Unlike the U5 (which reports reset causes in RCC->CSR), the STM32H5 has a
// dedicated reset status register RCC->RSR. There is also no OBLRSTF flag.
secbool reset_flags_check(void) {
#if PRODUCTION
  // this is effective enough that it makes development painful, so only use it
  // for production. check the reset flags to assure that we arrive here due to
  // a regular full power-on event, and not as a result of a lesser reset.
  if ((RCC->RSR & (RCC_RSR_LPWRRSTF | RCC_RSR_WWDGRSTF | RCC_RSR_IWDGRSTF |
                   RCC_RSR_SFTRSTF | RCC_RSR_PINRSTF | RCC_RSR_BORRSTF)) !=
      (RCC_RSR_PINRSTF | RCC_RSR_BORRSTF)) {
    return secfalse;
  }
#endif
  return sectrue;
}

void reset_flags_reset(void) {
  RCC->RSR |= RCC_RSR_RMVF;  // clear the reset flags
}

#endif
