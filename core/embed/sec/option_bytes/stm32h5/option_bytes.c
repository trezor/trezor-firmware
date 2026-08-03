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

#ifdef SECURE_MODE

#include <sec/option_bytes.h>
#include <sys/flash.h>

#pragma GCC optimize( \
    "no-stack-protector")  // applies to all functions in this file

// STM32H5 option-byte configuration.
//
// This mirrors the STM32U5 behaviour: the firmware itself programs the
// security-critical option bytes to the expected values and re-launches them
// (which resets the device), rather than relying on external provisioning.
//
// The STM32H5 uses a "product state" life cycle instead of RDP levels. This
// driver deliberately KEEPS the product state at its factory default of Open
// (0xED) — the dev-board equivalent of the U5 non-PRODUCTION RDP level 0, which
// keeps SWD/debug and re-flashing available. It therefore never writes the
// product-state byte (the most brick-prone option byte). It only programs the
// option bytes that are NOT set by default and that the secure monitor needs:
//
//   * TZEN  = enabled (0xB4) — turns on TrustZone secure access.
//   * Secure watermark (bank 1) covering the secret + boardloader sectors.
//   * HDP (bank 1) covering the secret sectors (hidden via SBS HDPL at runtime).
//   * Secure boot address = BOARDLOADER_START.
//
// The register encodings (TZEN redundancy, watermark/HDP sector ranges) are
// applied through the ST HAL so the magic values are encoded correctly.
//
// !!! HARDWARE WARNING !!!
// The first run on a fresh board ENABLES TrustZone and performs an option-byte
// launch (device reset). Verify these values against RM0517 and the board
// before flashing. While the product state stays Open the board remains fully
// recoverable with STM32CubeProgrammer if anything is misconfigured.
//
// TODO(H5): a PRODUCTION build should additionally move the product state to
// Closed (0x72) and enable WRP/boot-lock, gated behind `#if PRODUCTION` as on
// the U5 — those values must be validated on hardware first.

// Secure watermark / HDP sector ranges (bank 1).
#define WMSEC_SECTOR_START SECRET_SECTOR_START
#define WMSEC_SECTOR_END BOARDLOADER_SECTOR_END
#define HDP_SECTOR_START SECRET_SECTOR_START
#define HDP_SECTOR_END SECRET_SECTOR_END

static secbool flash_check_option_bytes(void) {
  // The secure monitor requires TrustZone to be enabled. Since the programming
  // path below sets TZEN together with the secure watermark, HDP and secure
  // boot address in a single option-byte launch, TZEN is a sufficient proxy for
  // "already configured".
  if ((FLASH->OPTSR2_CUR & FLASH_OPTSR2_TZEN_Msk) != OB_TZEN_ENABLE) {
    return secfalse;
  }
  return sectrue;
}

static void flash_set_option_bytes(void) {
  HAL_FLASH_Unlock();
  HAL_FLASH_OB_Unlock();

  FLASH_OBProgramInitTypeDef ob = {0};

  // Enable TrustZone (TZEN = 0xB4).
  ob.OptionType = OPTIONBYTE_USER;
  ob.USERType = OB_USER_TZEN;
  ob.USERConfig = OB_TZEN_ENABLE;
  HAL_FLASHEx_OBProgram(&ob);

  // Secure watermark, bank 1: secret + boardloader sectors are secure.
  memset(&ob, 0, sizeof(ob));
  ob.OptionType = OPTIONBYTE_WMSEC;
  ob.Banks = FLASH_BANK_1;
  ob.WMSecStartSector = WMSEC_SECTOR_START;
  ob.WMSecEndSector = WMSEC_SECTOR_END;
  HAL_FLASHEx_OBProgram(&ob);

  // Hide-protection area, bank 1: the secret sectors. The area is actually
  // hidden at runtime by advancing the HDPL (see sec/secret/stm32h5).
  memset(&ob, 0, sizeof(ob));
  ob.OptionType = OPTIONBYTE_HDP;
  ob.Banks = FLASH_BANK_1;
  ob.HDPStartSector = HDP_SECTOR_START;
  ob.HDPEndSector = HDP_SECTOR_END;
  HAL_FLASHEx_OBProgram(&ob);

  // Secure boot address = boardloader.
  memset(&ob, 0, sizeof(ob));
  ob.OptionType = OPTIONBYTE_BOOTADDR;
  ob.BootConfig = OB_BOOT_SEC;
  ob.BootAddr = BOARDLOADER_START;
  HAL_FLASHEx_OBProgram(&ob);

  // Commit the option bytes. This resets the device, so execution normally does
  // not return past this point (mirrors the U5 OBL_LAUNCH behaviour).
  HAL_FLASH_OB_Launch();

  HAL_FLASH_OB_Lock();
  HAL_FLASH_Lock();
}

void option_bytes_check_oem_keys(void) {
  // The STM32H5 has no OEM1/OEM2 RDP-regression keys; access/debug is governed
  // by the product-state life cycle and Debug Authentication instead. Nothing
  // to check here.
}

secbool option_bytes_configure(void) {
  if (sectrue == flash_check_option_bytes()) {
    return sectrue;  // we DID NOT have to change the option bytes
  }

  do {
    flash_set_option_bytes();  // resets the device on the first launch
  } while (sectrue != flash_check_option_bytes());

  option_bytes_check_oem_keys();

  return secfalse;  // notify that we DID have to change the option bytes
}

#endif  // SECURE_MODE
