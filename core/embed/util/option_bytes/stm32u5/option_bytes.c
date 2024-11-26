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
#include <trezor_rtl.h>

#ifdef KERNEL_MODE

#include <util/flash.h>
#include <util/option_bytes.h>

#pragma GCC optimize( \
    "no-stack-protector")  // applies to all functions in this file

#if PRODUCTION
#define WANT_RDP_LEVEL (OB_RDP_LEVEL_2)
#define WANT_WRP_PAGE_START 2
#define WANT_WRP_PAGE_END 7
#else
#define WANT_RDP_LEVEL (OB_RDP_LEVEL_0)
#endif

#ifdef VDD_3V3
// BOR LEVEL 0: Reset level threshold is around 2.8 V
#define WANT_BOR_LEVEL (OB_BOR_LEVEL_4)
#elif VDD_1V8
// BOR LEVEL 0: Reset level threshold is around 1.7 V
#define WANT_BOR_LEVEL (OB_BOR_LEVEL_0)
#else
#error "VDD_3V3 or VDD_1V8 must be defined"
#endif

#if defined STM32U5A9xx | defined STM32U5G9xx
#define WRP_DEFAULT_VALUE 0xFF00FFFF
#define SEC_WM1R1_DEFAULT_VALUE 0xFF00FF00
#define SEC_WM1R2_DEFAULT_VALUE 0x7F007F00
#define SEC_AREA_2_PAGE_START 0xFF
#define SEC_AREA_2_PAGE_END 0x00
#elif defined STM32U585xx
#define WRP_DEFAULT_VALUE 0xFF80FFFF
#define SEC_WM1R1_DEFAULT_VALUE 0xFF80FF80
#define SEC_WM1R2_DEFAULT_VALUE 0x7F807F80
#define SEC_AREA_2_PAGE_START 0x7F
#define SEC_AREA_2_PAGE_END 0x00
#else
#error Unknown MCU
#endif

_Static_assert(SECRET_SECTOR_START == 0, "secret sector start must be 0");
#define SEC_AREA_1_PAGE_START SECRET_SECTOR_START
#define HDP_AREA_1_PAGE_END SECRET_SECTOR_END
#define SEC_AREA_1_PAGE_END BOARDLOADER_SECTOR_END

#define WRP_LOCKED_VALUE                                       \
  ((WRP_DEFAULT_VALUE &                                        \
    ~(FLASH_WRP1AR_UNLOCK_Msk | FLASH_WRP1AR_WRP1A_PSTRT_Msk | \
      FLASH_WRP1AR_WRP1A_PEND_Msk)) |                          \
   (WANT_WRP_PAGE_START << FLASH_WRP1AR_WRP1A_PSTRT_Pos) |     \
   (WANT_WRP_PAGE_END << FLASH_WRP1AR_WRP1A_PEND_Pos))

#define FLASH_OPTR_VALUE                                                \
  (FLASH_OPTR_TZEN | FLASH_OPTR_PA15_PUPEN | FLASH_OPTR_nBOOT0 |        \
   FLASH_OPTR_SRAM3_ECC | FLASH_OPTR_BKPRAM_ECC | FLASH_OPTR_DUALBANK | \
   FLASH_OPTR_WWDG_SW | FLASH_OPTR_IWDG_STOP | FLASH_OPTR_IWDG_STDBY |  \
   FLASH_OPTR_IWDG_SW | FLASH_OPTR_SRAM_RST | FLASH_OPTR_nRST_SHDW |    \
   FLASH_OPTR_nRST_STDBY | FLASH_OPTR_nRST_STOP | WANT_BOR_LEVEL |      \
   (WANT_RDP_LEVEL << FLASH_OPTR_RDP_Pos))

#define FALSH_SECBOOTADD0R_VALUE \
  ((BOARDLOADER_START & 0xFFFFFF80) | FLASH_SECBOOTADD0R_BOOT_LOCK | 0x7C)

#define FLASH_SECWM1R1_VALUE                                  \
  (SEC_AREA_1_PAGE_START << FLASH_SECWM1R1_SECWM1_PSTRT_Pos | \
   SEC_AREA_1_PAGE_END << FLASH_SECWM1R1_SECWM1_PEND_Pos |    \
   SEC_WM1R1_DEFAULT_VALUE)
#define FLASH_SECWM1R2_VALUE                             \
  (HDP_AREA_1_PAGE_END << FLASH_SECWM1R2_HDP1_PEND_Pos | \
   FLASH_SECWM1R2_HDP1EN | SEC_WM1R2_DEFAULT_VALUE)

#define FLASH_SECWM2R1_VALUE                                  \
  (SEC_AREA_2_PAGE_START << FLASH_SECWM1R1_SECWM1_PSTRT_Pos | \
   SEC_AREA_2_PAGE_END << FLASH_SECWM1R1_SECWM1_PEND_Pos |    \
   SEC_WM1R1_DEFAULT_VALUE)
#define FLASH_SECWM2R2_VALUE (SEC_WM1R2_DEFAULT_VALUE)

#define FLASH_STATUS_ALL_FLAGS \
  (FLASH_NSSR_PGSERR | FLASH_NSSR_PGAERR | FLASH_NSSR_WRPERR | FLASH_NSSR_EOP)

static uint32_t flash_wait_and_clear_status_flags(void) {
  while (FLASH->NSSR & FLASH_NSSR_BSY)
    ;  // wait for all previous flash operations to complete

  uint32_t result =
      FLASH->NSSR & FLASH_STATUS_ALL_FLAGS;  // get the current status flags
  FLASH->NSSR |= FLASH_STATUS_ALL_FLAGS;     // clear all status flags

#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)
  while (FLASH->SECSR & FLASH_SECSR_BSY)
    ;  // wait for all previous flash operations to complete
  result |=
      FLASH->SECSR & FLASH_STATUS_ALL_FLAGS;  // get the current status flags
  FLASH->SECSR |= FLASH_STATUS_ALL_FLAGS;     // clear all status flags
#endif
  return result;
}

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
  if (FLASH->WRP1AR != WRP_LOCKED_VALUE) {
    return secfalse;
  }
#else
  if (FLASH->WRP1AR != WRP_DEFAULT_VALUE) {
    return secfalse;
  }
#endif

  if (FLASH->WRP1BR != WRP_DEFAULT_VALUE) {
    return secfalse;
  }
  if (FLASH->WRP2AR != WRP_DEFAULT_VALUE) {
    return secfalse;
  }
  if (FLASH->WRP2BR != WRP_DEFAULT_VALUE) {
    return secfalse;
  }

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

  FLASH->SECBOOTADD0R = FALSH_SECBOOTADD0R_VALUE;

  FLASH->SECWM1R1 = FLASH_SECWM1R1_VALUE;
  FLASH->SECWM1R2 = FLASH_SECWM1R2_VALUE;

  FLASH->SECWM2R1 = FLASH_SECWM2R1_VALUE;
  FLASH->SECWM2R2 = FLASH_SECWM2R2_VALUE;

#if PRODUCTION
  FLASH->WRP1AR = WRP_LOCKED_VALUE;
#else
  FLASH->WRP1AR = WRP_DEFAULT_VALUE;
#endif
  FLASH->WRP1BR = WRP_DEFAULT_VALUE;
  FLASH->WRP2AR = WRP_DEFAULT_VALUE;
  FLASH->WRP2BR = WRP_DEFAULT_VALUE;

  // Set the OEM keys to the default value
  // In case these are for any reason set, we will reset them to the default
  // while locking the device, to ensure that there is no ability to reverse the
  // RDP. These keys are write-only, so the only way to check that the keys are
  // not set is through OEMxLOCK bits in FLASH->NSSR register. These bits are
  // unset only if the keys are written to 0xFFFFFFFF.
  FLASH->OEM1KEYR1 = 0xFFFFFFFF;
  FLASH->OEM1KEYR2 = 0xFFFFFFFF;
  FLASH->OEM2KEYR1 = 0xFFFFFFFF;
  FLASH->OEM2KEYR2 = 0xFFFFFFFF;

  FLASH->OPTR =
      FLASH_OPTR_VALUE;  // WARNING: dev board safe unless you compile for
  // PRODUCTION or change this value!!!

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

void check_oem_keys(void) {
  ensure(((FLASH->NSSR & FLASH_NSSR_OEM1LOCK) == 0) * sectrue, "OEM1 KEY SET");
  ensure(((FLASH->NSSR & FLASH_NSSR_OEM2LOCK) == 0) * sectrue, "OEM2 KEY SET");
}

secbool flash_configure_option_bytes(void) {
  if (sectrue == flash_check_option_bytes()) {
    return sectrue;  // we DID NOT have to change the option bytes
  }

  do {
    flash_set_option_bytes();
  } while (sectrue != flash_check_option_bytes());

  check_oem_keys();

  return secfalse;  // notify that we DID have to change the option bytes
}

#endif  // #ifdef KERNEL_MODE
