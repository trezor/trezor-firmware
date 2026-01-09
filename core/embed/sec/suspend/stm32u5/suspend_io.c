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

#ifdef SECURE_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sec/suspend_io.h>
#include <sys/irq.h>

#ifdef USE_STORAGE_HWKEY
#include <sec/secure_aes.h>
#endif

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

void suspend_cpu(void) {
  // Disable interrupts by setting PRIMASK to 1.
  //
  // The system can wake up, but interrupts will not be processed until
  // PRIMASK is cleared again. This is necessary to restore the system clock
  // immediately after exiting STOP2 mode.

  irq_key_t irq_key = irq_lock();

  // The PWR clock is disabled after system initialization.
  // Re-enable it before writing to PWR registers.
  __HAL_RCC_PWR_CLK_ENABLE();

  // Enter STOP2 low-power mode
  HAL_PWREx_EnterSTOP2Mode(PWR_STOPENTRY_WFI);

  // Disable PWR clock after use
  __HAL_RCC_PWR_CLK_DISABLE();

  // Recover system clock
  SystemInit();

  irq_unlock(irq_key);
}

void suspend_secure_drivers() {
#ifdef USE_STORAGE_HWKEY
  secure_aes_deinit();
#endif
#ifdef USE_TROPIC
  tropic_deinit();
#endif
}

void resume_secure_drivers() {
#ifdef USE_STORAGE_HWKEY
  secure_aes_init();
#endif
#ifdef USE_TROPIC
  tropic_init();
#endif
}

#endif  // SECURE_MODE
