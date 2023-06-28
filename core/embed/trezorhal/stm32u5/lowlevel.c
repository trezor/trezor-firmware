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

#include STM32_HAL_H

#include "lowlevel.h"
#include "flash.h"
#include "model.h"

#pragma GCC optimize( \
    "no-stack-protector")  // applies to all functions in this file

#if PRODUCTION
#define WANT_RDP_LEVEL (OB_RDP_LEVEL_2)
#define WANT_WRP_PAGE_START 1
#define WANT_WRP_PAGE_END 6
#else
#define WANT_RDP_LEVEL (OB_RDP_LEVEL_0)
#endif

// BOR LEVEL 0: Reset level threshold is around 1.7 V
#define WANT_BOR_LEVEL (OB_BOR_LEVEL_0)

#define FLASH_OPTR_VALUE                                              \
  ((WANT_RDP_LEVEL << FLASH_OPTR_RDP_Pos) | FLASH_OPTR_nRST_STDBY |   \
   FLASH_OPTR_nRST_STOP | FLASH_OPTR_IWDG_SW | FLASH_OPTR_IWDG_STOP | \
   FLASH_OPTR_IWDG_STDBY | FLASH_OPTR_WWDG_SW | FLASH_OPTR_DUALBANK | \
   FLASH_OPTR_nSWBOOT0 | FLASH_OPTR_nBOOT0 | FLASH_OPTR_PA15_PUPEN |  \
   FLASH_OPTR_BKPRAM_ECC | FLASH_OPTR_SRAM3_ECC | FLASH_OPTR_TZEN |   \
   FLASH_OPTR_SRAM_RST | WANT_BOR_LEVEL)

// TODO set values according to MCU variant
#define FALSH_SECBOOTADD0R_VALUE \
  ((BOARDLOADER_START & 0xFFFFFF80) | FLASH_SECBOOTADD0R_BOOT_LOCK | 0x7C)
#define FLASH_SECWM1R1_VALUE              \
  (0 << FLASH_SECWM1R1_SECWM1_PSTRT_Pos | \
   0xff << FLASH_SECWM1R1_SECWM1_PEND_Pos | 0xFF00FF00)
#define FLASH_SECWM1R2_VALUE \
  (1 << FLASH_SECWM1R2_HDP1_PEND_Pos | FLASH_SECWM1R2_HDP1EN | 0x7F007F00)
#define FLASH_SECWM2R1_VALUE              \
  (0 << FLASH_SECWM1R1_SECWM1_PSTRT_Pos | \
   0xff << FLASH_SECWM1R1_SECWM1_PEND_Pos | 0xFF00FF00)
#define FLASH_SECWM2R2_VALUE (0x7F007F00)

secbool flash_check_option_bytes(void) {
  flash_wait_and_clear_status_flags();
  // check values stored in flash interface registers
  if (FLASH->OPTR !=
      FLASH_OPTR_VALUE) {  // ignore bits 0 and 1 because they are control bits
    return secfalse;
  }

  if (FLASH->SECBOOTADD0R != FALSH_SECBOOTADD0R_VALUE) {
    return secfalse;
  }

#if PRODUCTION
  if (FLASH->WRP1AR != (WANT_WRP_PAGE_START | (WANT_WRP_PAGE_END << 16))) {
    return secfalse;
  }
#else
  // TODO set values according to MCU variant
  if (FLASH->WRP1AR != 0xFF00FFFF) {
    return secfalse;
  }
#endif

  // TODO set values according to MCU variant
  if (FLASH->WRP1BR != 0xFF00FFFF) {
    return secfalse;
  }
  // TODO set values according to MCU variant
  if (FLASH->WRP2AR != 0xFF00FFFF) {
    return secfalse;
  }
  // TODO set values according to MCU variant
  if (FLASH->WRP2BR != 0xFF00FFFF) {
    return secfalse;
  }

  return sectrue;
}

void flash_lock_option_bytes(void) {
  FLASH->NSCR |= FLASH_NSCR_OPTLOCK;  // lock the option bytes
}

void flash_unlock_option_bytes(void) {
  if ((FLASH->NSCR & FLASH_NSCR_OPTLOCK) == 0) {
    return;  // already unlocked
  }
  // reference RM0090 section 3.7.2
  // write the special sequence to unlock
  FLASH->OPTKEYR = FLASH_OPTKEY1;
  FLASH->OPTKEYR = FLASH_OPTKEY2;
  while (FLASH->NSCR & FLASH_NSCR_OPTLOCK)
    ;  // wait until the flash option control register is unlocked
}

uint32_t flash_set_option_bytes(void) {
  if (flash_unlock_write() != sectrue) {
    return 0;
  }
  flash_wait_and_clear_status_flags();
  flash_unlock_option_bytes();
  flash_wait_and_clear_status_flags();

  FLASH->OPTR =
      FLASH_OPTR_VALUE;  // WARNING: dev board safe unless you compile for
  // PRODUCTION or change this value!!!

  FLASH->SECBOOTADD0R = FALSH_SECBOOTADD0R_VALUE;

#if PRODUCTION
  FLASH->WRP1AR = WANT_WRP_PAGE_START | (WANT_WRP_PAGE_END << 16);
  // TODO set values according to MCU variant
  FLASH->WRP1BR = 0xFF00FFFF;
  FLASH->WRP2AR = 0xFF00FFFF FLASH->WRP2BR = 0xFF00FFFF
#endif

      FLASH_WaitForLastOperation(HAL_MAX_DELAY);

  FLASH->NSCR |= FLASH_NSCR_OPTSTRT;
  uint32_t result =
      flash_wait_and_clear_status_flags();  // wait until changes are committed

  FLASH_WaitForLastOperation(HAL_MAX_DELAY);

  FLASH->NSCR |= FLASH_NSCR_OBL_LAUNCH;  // begin committing changes to flash
  result =
      flash_wait_and_clear_status_flags();  // wait until changes are committed
  flash_lock_option_bytes();

  if (flash_lock_write() != sectrue) {
    return 0;
  }
  return result;
}

secbool flash_configure_option_bytes(void) {
  if (sectrue == flash_check_option_bytes()) {
    return sectrue;  // we DID NOT have to change the option bytes
  }

  do {
    flash_set_option_bytes();
  } while (sectrue != flash_check_option_bytes());

  return secfalse;  // notify that we DID have to change the option bytes
}

secbool flash_check_sec_area_ob(void) {
  flash_wait_and_clear_status_flags();
  // check values stored in flash interface registers

  if (FLASH->SECWM1R1 != FLASH_SECWM1R1_VALUE) {
    return secfalse;
  }
  if (FLASH->SECWM1R2 != FLASH_SECWM1R2_VALUE) {
    return secfalse;
  }
  if (FLASH->SECWM2R1 != FLASH_SECWM2R1_VALUE) {
    return secfalse;
  }
  if (FLASH->SECWM2R2 != FLASH_SECWM2R2_VALUE) {
    return secfalse;
  }

  return sectrue;
}

uint32_t flash_set_sec_area_ob(void) {
  if (flash_unlock_write() != sectrue) {
    return 0;
  }
  flash_wait_and_clear_status_flags();
  flash_unlock_option_bytes();
  flash_wait_and_clear_status_flags();

  FLASH->SECWM1R1 = FLASH_SECWM1R1_VALUE;
  FLASH->SECWM1R2 = FLASH_SECWM1R2_VALUE;

  FLASH->SECWM2R1 = FLASH_SECWM2R1_VALUE;
  FLASH->SECWM2R2 = FLASH_SECWM2R2_VALUE;

  FLASH_WaitForLastOperation(HAL_MAX_DELAY);

  FLASH->NSCR |= FLASH_NSCR_OPTSTRT;
  uint32_t result =
      flash_wait_and_clear_status_flags();  // wait until changes are committed

  FLASH_WaitForLastOperation(HAL_MAX_DELAY);

  FLASH->NSCR |= FLASH_NSCR_OBL_LAUNCH;  // begin committing changes to flash
  result =
      flash_wait_and_clear_status_flags();  // wait until changes are committed
  flash_lock_option_bytes();

  if (flash_lock_write() != sectrue) {
    return 0;
  }
  return result;
}

secbool flash_configure_sec_area_ob(void) {
  if (sectrue == flash_check_sec_area_ob()) {
    return sectrue;  // we DID NOT have to change the option bytes
  }

  do {
    flash_set_sec_area_ob();
  } while (sectrue != flash_check_sec_area_ob());

  return secfalse;  // notify that we DID have to change the option bytes
}

void periph_init(void) {
  // STM32U5xx HAL library initialization:
  //  - configure the Flash prefetch, instruction and data caches
  //  - configure the Systick to generate an interrupt each 1 msec
  //  - set NVIC Group Priority to 4
  //  - global MSP (MCU Support Package) initialization
  HAL_Init();

  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  /** Initializes the common periph clock
   */
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_LTDC | RCC_PERIPHCLK_DSI;
  PeriphClkInit.DsiClockSelection = RCC_DSICLKSOURCE_PLL3;
  PeriphClkInit.LtdcClockSelection = RCC_LTDCCLKSOURCE_PLL3;
  PeriphClkInit.PLL3.PLL3Source = RCC_PLLSOURCE_HSE;
  PeriphClkInit.PLL3.PLL3M = 4;
  PeriphClkInit.PLL3.PLL3N = 125;
  PeriphClkInit.PLL3.PLL3P = 8;
  PeriphClkInit.PLL3.PLL3Q = 2;
  PeriphClkInit.PLL3.PLL3R = 24;
  PeriphClkInit.PLL3.PLL3RGE = RCC_PLLVCIRANGE_0;
  PeriphClkInit.PLL3.PLL3FRACN = 0;
  PeriphClkInit.PLL3.PLL3ClockOut = RCC_PLL3_DIVP | RCC_PLL3_DIVR;
  HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit);

  /** Enable instruction cache in 1-way (direct mapped cache)
   */
  HAL_ICACHE_ConfigAssociativityMode(ICACHE_1WAY);

  // Enable GPIO clocks
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();

  // enable the PVD (programmable voltage detector).
  // select the "2.8V" threshold (level 5).
  // this detector will be active regardless of the
  // flash option byte BOR setting.
  //  __HAL_RCC_PWR_CLK_ENABLE();
  //  PWR_PVDTypeDef pvd_config;
  //  pvd_config.PVDLevel = PWR_PVDLEVEL_5;
  //  pvd_config.Mode = PWR_PVD_MODE_IT_RISING_FALLING;
  //  HAL_PWR_ConfigPVD(&pvd_config);
  //  HAL_PWR_EnablePVD();
  //  NVIC_EnableIRQ(PVD_PVM_IRQn);
}

secbool reset_flags_check(void) {
#if PRODUCTION
  // this is effective enough that it makes development painful, so only use it
  // for production. check the reset flags to assure that we arrive here due to
  // a regular full power-on event, and not as a result of a lesser reset.
  if ((RCC->CSR & (RCC_CSR_LPWRRSTF | RCC_CSR_WWDGRSTF | RCC_CSR_IWDGRSTF |
                   RCC_CSR_SFTRSTF | RCC_CSR_PINRSTF | RCC_CSR_BORRSTF |
                   RCC_CSR_OBLRSTF)) != (RCC_CSR_PINRSTF | RCC_CSR_BORRSTF)) {
    return secfalse;
  }
#endif
  return sectrue;
}

void reset_flags_reset(void) {
  RCC->CSR |= RCC_CSR_RMVF;  // clear the reset flags
}
