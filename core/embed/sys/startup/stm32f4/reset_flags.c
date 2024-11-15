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

secbool reset_flags_check(void) {
#if PRODUCTION
  // this is effective enough that it makes development painful, so only use it
  // for production. check the reset flags to assure that we arrive here due to
  // a regular full power-on event, and not as a result of a lesser reset.
  if ((RCC->CSR & (RCC_CSR_LPWRRSTF | RCC_CSR_WWDGRSTF | RCC_CSR_IWDGRSTF |
                   RCC_CSR_SFTRSTF | RCC_CSR_PORRSTF | RCC_CSR_PINRSTF |
                   RCC_CSR_BORRSTF)) !=
      (RCC_CSR_PORRSTF | RCC_CSR_PINRSTF | RCC_CSR_BORRSTF)) {
    return secfalse;
  }
#endif
  return sectrue;
}

void reset_flags_reset(void) {
  RCC->CSR |= RCC_CSR_RMVF;  // clear the reset flags
}

#endif
