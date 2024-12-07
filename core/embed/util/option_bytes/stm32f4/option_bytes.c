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

#include <sys/mpu.h>
#include <util/flash_otp.h>
#include <util/option_bytes.h>

#ifdef KERNEL_MODE

#pragma GCC optimize( \
    "no-stack-protector")  // applies to all functions in this file

#if PRODUCTION
#define WANT_RDP_LEVEL (OB_RDP_LEVEL_2)
#define WANT_WRP_SECTORS (OB_WRP_SECTOR_0 | OB_WRP_SECTOR_1 | OB_WRP_SECTOR_2)
#else
#define WANT_RDP_LEVEL (OB_RDP_LEVEL_0)
#define WANT_WRP_SECTORS (0)
#endif

// BOR LEVEL 3: Reset level threshold is around 2.5 V
#define WANT_BOR_LEVEL (OB_BOR_LEVEL3)

// reference RM0090 section 3.9.10; SPRMOD is 0 meaning PCROP disabled.; DB1M is
// 0 because we use 2MB dual-bank; BFB2 is 0 allowing boot from flash;
#define FLASH_OPTCR_VALUE                                                   \
  ((((~WANT_WRP_SECTORS) << FLASH_OPTCR_nWRP_Pos) & FLASH_OPTCR_nWRP_Msk) | \
   (WANT_RDP_LEVEL << FLASH_OPTCR_RDP_Pos) | FLASH_OPTCR_nRST_STDBY |       \
   FLASH_OPTCR_nRST_STOP | FLASH_OPTCR_WDG_SW | WANT_BOR_LEVEL)

// reference RM0090 section 3.7.1 table 16
#define OPTION_BYTES_RDP_USER_VALUE                            \
  ((uint16_t)((WANT_RDP_LEVEL << FLASH_OPTCR_RDP_Pos) |        \
              FLASH_OPTCR_nRST_STDBY | FLASH_OPTCR_nRST_STOP | \
              FLASH_OPTCR_WDG_SW | WANT_BOR_LEVEL))
#define OPTION_BYTES_BANK1_WRP_VALUE ((uint16_t)((~WANT_WRP_SECTORS) & 0xFFFU))
#define OPTION_BYTES_BANK2_WRP_VALUE ((uint16_t)0xFFFU)

// reference RM0090 section 3.7.1 table 16. use 16 bit pointers because the top
// 48 bits are all reserved.
#define OPTION_BYTES_RDP_USER (*(volatile uint16_t* const)0x1FFFC000U)
#define OPTION_BYTES_BANK1_WRP (*(volatile uint16_t* const)0x1FFFC008U)
#define OPTION_BYTES_BANK2_WRP (*(volatile uint16_t* const)0x1FFEC008U)

#define FLASH_STATUS_ALL_FLAGS                                            \
  (FLASH_SR_RDERR | FLASH_SR_PGSERR | FLASH_SR_PGPERR | FLASH_SR_PGAERR | \
   FLASH_SR_WRPERR | FLASH_SR_SOP | FLASH_SR_EOP)

static uint32_t flash_wait_and_clear_status_flags(void) {
  while (FLASH->SR & FLASH_SR_BSY)
    ;  // wait for all previous flash operations to complete
  const uint32_t result =
      FLASH->SR & FLASH_STATUS_ALL_FLAGS;  // get the current status flags
  FLASH->SR |= FLASH_STATUS_ALL_FLAGS;     // clear all status flags
  return result;
}

secbool flash_check_option_bytes(void) {
  flash_wait_and_clear_status_flags();
  // check values stored in flash interface registers
  if ((FLASH->OPTCR & ~3) !=
      FLASH_OPTCR_VALUE) {  // ignore bits 0 and 1 because they are control bits
    return secfalse;
  }
  if (FLASH->OPTCR1 != FLASH_OPTCR1_nWRP) {
    return secfalse;
  }

  mpu_mode_t mode = mpu_reconfig(MPU_MODE_FLASHOB);
  // check values stored in flash memory
  if ((OPTION_BYTES_RDP_USER & ~3) !=
      OPTION_BYTES_RDP_USER_VALUE) {  // bits 0 and 1 are unused
    mpu_reconfig(mode);
    return secfalse;
  }
  if ((OPTION_BYTES_BANK1_WRP & 0xCFFFU) !=
      OPTION_BYTES_BANK1_WRP_VALUE) {  // bits 12 and 13 are unused
    mpu_reconfig(mode);
    return secfalse;
  }
  if ((OPTION_BYTES_BANK2_WRP & 0xFFFU) !=
      OPTION_BYTES_BANK2_WRP_VALUE) {  // bits 12, 13, 14, and 15 are unused
    mpu_reconfig(mode);
    return secfalse;
  }

  mpu_reconfig(mode);

  return sectrue;
}

void flash_lock_option_bytes(void) {
  FLASH->OPTCR |= FLASH_OPTCR_OPTLOCK;  // lock the option bytes
}

void flash_unlock_option_bytes(void) {
  if ((FLASH->OPTCR & FLASH_OPTCR_OPTLOCK) == 0) {
    return;  // already unlocked
  }
  // reference RM0090 section 3.7.2
  // write the special sequence to unlock
  FLASH->OPTKEYR = FLASH_OPT_KEY1;
  FLASH->OPTKEYR = FLASH_OPT_KEY2;
  while (FLASH->OPTCR & FLASH_OPTCR_OPTLOCK)
    ;  // wait until the flash option control register is unlocked
}

uint32_t flash_set_option_bytes(void) {
  // reference RM0090 section 3.7.2
  flash_wait_and_clear_status_flags();
  flash_unlock_option_bytes();
  flash_wait_and_clear_status_flags();
  FLASH->OPTCR1 =
      FLASH_OPTCR1_nWRP;  // no write protection on any sectors in bank 2
  FLASH->OPTCR =
      FLASH_OPTCR_VALUE;  // WARNING: dev board safe unless you compile for
                          // PRODUCTION or change this value!!!
  FLASH->OPTCR |= FLASH_OPTCR_OPTSTRT;  // begin committing changes to flash
  const uint32_t result =
      flash_wait_and_clear_status_flags();  // wait until changes are committed
  flash_lock_option_bytes();
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

#endif  // #ifdef KERNEL_MODE
