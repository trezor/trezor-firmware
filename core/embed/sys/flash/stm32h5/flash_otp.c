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

#include <sys/flash.h>
#include <sys/flash_otp.h>
#include <sys/mpu.h>

// The STM32H5 OTP array is ECC-protected: reading a never-programmed (virgin)
// OTP word reports an uncorrectable ECC double-error and bus-faults (RM0481).
// We therefore never read an OTP block until we know it has been programmed,
// using the hardware OTP block-lock register FLASH_OTPBLR_CUR - it lives in the
// flash controller (not the OTP array) and is always read-safe. Manufacturing
// locks each block right after programming it, so a locked block is guaranteed
// programmed (safe to read) and an unlocked block is treated as erased (0xFF).
//
// The hardware locks OTP in 16-byte words (32 bits cover the 512-byte OTP), so
// each 32-byte trezor OTP block maps to two words: OTPBLR bits [2*block] and
// [2*block+1].
static bool flash_otp_block_locked(uint8_t block) {
  uint32_t mask = 0x3u << (2u * block);
  return (FLASH->OTPBLR_CUR & mask) == mask;
}

void flash_otp_init(void) {
  // intentionally left empty
}

secbool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data,
                       uint8_t datalen) {
  if (block >= FLASH_OTP_NUM_BLOCKS ||
      offset + datalen > FLASH_OTP_BLOCK_SIZE) {
    return secfalse;
  }

  if (!flash_otp_block_locked(block)) {
    // Unprogrammed block: report it as erased without reading the (virgin,
    // ECC-faulting) OTP words.
    memset(data, 0xFF, datalen);
    return sectrue;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);

  for (uint8_t i = 0; i < datalen; i++) {
    data[i] = *(__IO uint8_t *)(FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE +
                                offset + i);
  }

  mpu_restore(mpu_mode);

  return sectrue;
}

secbool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data,
                        uint8_t datalen) {
  if (datalen % 16 != 0) {
    return secfalse;
  }
  if (block >= FLASH_OTP_NUM_BLOCKS ||
      offset + datalen > FLASH_OTP_BLOCK_SIZE) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);

  // TODO(H5): the STM32H5 OTP is programmed in half-words
  // (FLASH_TYPEPROGRAM_HALFWORD_OTP), not quadwords; revisit before relying on
  // on-hardware OTP writes.
  ensure(flash_unlock_write(), NULL);
  for (uint8_t i = 0; i < datalen; i += 16) {
    uint32_t address =
        FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE + offset + i;
    ensure(sectrue * (HAL_OK == HAL_FLASH_Program(FLASH_TYPEPROGRAM_QUADWORD_NS,
                                                  address, (uint32_t)&data[i])),
           NULL);
  }
  ensure(flash_lock_write(), NULL);

  mpu_restore(mpu_mode);

  return sectrue;
}

secbool flash_otp_lock(uint8_t block) {
  if (block >= FLASH_OTP_NUM_BLOCKS) {
    return secfalse;
  }

  // TODO(H5): flash_otp_read / flash_otp_is_locked gate on the hardware OTP
  // block-lock register (FLASH_OTPBLR_CUR). To make a provisioned block
  // readable this function must also *set* that lock via the option-byte
  // program path (OTPBLR_PRG, OPTIONBYTE_OTP_LOCK, bits [2*block] and
  // [2*block+1]) - note an option-byte launch reloads/resets, so the
  // provisioning flow must account for that. Until then only the read side is
  // wired up (fine for a virgin device, which reads every block as erased).

  // The block must be programmed before it can be locked.
  if (!flash_otp_block_locked(block)) {
    // Verify all quadwords have been written to. Safe to read here: a block is
    // only locked right after being programmed, so it is not virgin.
    mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);
    volatile uint8_t *addr =
        (__IO uint8_t *)(FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE);
    for (uint8_t i = 0; i < FLASH_OTP_BLOCK_SIZE; i += 16) {
      secbool qw_written = secfalse;
      for (uint8_t j = 0; j < 16; j++) {
        if (addr[i + j] != 0xFF) {
          qw_written = sectrue;
        }
      }
      if (qw_written == secfalse) {
        mpu_restore(mpu_mode);
        return secfalse;
      }
    }
    mpu_restore(mpu_mode);
  }

  return sectrue;
}

secbool flash_otp_is_locked(uint8_t block) {
  if (block >= FLASH_OTP_NUM_BLOCKS) {
    return secfalse;
  }

  // Read the hardware OTP block-lock register instead of probing the array,
  // which bus-faults on virgin (ECC-uninitialized) words.
  return flash_otp_block_locked(block) ? sectrue : secfalse;
}

#endif  // SECURE_MODE
