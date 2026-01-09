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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sec/image.h>
#include <sys/bootutils.h>
#include <sys/flash.h>
#include <sys/flash_otp.h>

#include "fw_check.h"
#include "version_check.h"

#ifdef TREZOR_EMULATOR
#include "emulator.h"
#endif

secbool check_vendor_header_lock(const vendor_header *vhdr) {
  uint8_t lock[FLASH_OTP_BLOCK_SIZE];
  ensure(flash_otp_read(FLASH_OTP_BLOCK_VENDOR_HEADER_LOCK, 0, lock,
                        FLASH_OTP_BLOCK_SIZE),
         NULL);
  if (0 ==
      memcmp(lock,
             "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF"
             "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF",
             FLASH_OTP_BLOCK_SIZE)) {
    return sectrue;
  }
  uint8_t hash[32];
  vendor_header_hash(vhdr, hash);
  return sectrue * (0 == memcmp(lock, hash, 32));
}

void fw_check(fw_info_t *fw_info) {
  memset(fw_info, 0, sizeof(*fw_info));

  const image_header *hdr = NULL;

  // detect whether the device contains a valid firmware
  volatile secbool vhdr_present = secfalse;
  volatile secbool vhdr_keys_ok = secfalse;
  volatile secbool vhdr_lock_ok = secfalse;
  volatile secbool img_hdr_ok = secfalse;
  volatile secbool model_ok = secfalse;
  volatile secbool signatures_ok = secfalse;
  volatile secbool version_ok = secfalse;
  volatile secbool secmon_valid = secfalse;

  vhdr_present =
      read_vendor_header((const uint8_t *)FIRMWARE_START, &fw_info->vhdr);

  if (sectrue == vhdr_present) {
    vhdr_keys_ok = check_vendor_header_keys(&fw_info->vhdr);
  }

  if (sectrue == vhdr_keys_ok) {
    vhdr_lock_ok = check_vendor_header_lock(&fw_info->vhdr);
  }

  if (sectrue == vhdr_lock_ok) {
    hdr = read_image_header(
        (const uint8_t *)(size_t)(FIRMWARE_START + fw_info->vhdr.hdrlen),
        FIRMWARE_IMAGE_MAGIC, FIRMWARE_MAXSIZE);
    if (hdr ==
        (const image_header *)(size_t)(FIRMWARE_START + fw_info->vhdr.hdrlen)) {
      img_hdr_ok = sectrue;
    }
  }
  if (sectrue == img_hdr_ok) {
    model_ok = check_image_model(hdr);
  }

  if (sectrue == model_ok) {
    signatures_ok = check_image_header_sig(
        hdr, fw_info->vhdr.vsig_m, fw_info->vhdr.vsig_n, fw_info->vhdr.vpub);
  }

  if (sectrue == signatures_ok) {
    version_ok = check_firmware_min_version(hdr->monotonic);
  }

  if (sectrue == version_ok) {
    fw_info->header_present = version_ok;
  }

#ifdef USE_SECMON_VERIFICATION
  size_t secmon_start = (size_t)IMAGE_CODE_ALIGN(
      FIRMWARE_START + fw_info->vhdr.hdrlen + IMAGE_HEADER_SIZE);

  const secmon_header_t *secmon_hdr =
      read_secmon_header((const uint8_t *)secmon_start, FIRMWARE_MAXSIZE);

  volatile secbool secmon_header_present = secfalse;
  volatile secbool secmon_model_valid = secfalse;
  volatile secbool secmon_header_sig_valid = secfalse;
  volatile secbool secmon_contents_valid = secfalse;

  if (sectrue == fw_info->header_present) {
    secmon_header_present =
        secbool_and(fw_info->header_present, (secmon_hdr != NULL) * sectrue);
  }

  if (sectrue == secmon_header_present) {
    secmon_model_valid =
        secbool_and(secmon_header_present, check_secmon_model(secmon_hdr));
  }

  if (sectrue == secmon_model_valid) {
    secmon_header_sig_valid =
        secbool_and(secmon_model_valid, check_secmon_header_sig(secmon_hdr));
  }

  if (sectrue == secmon_header_sig_valid) {
    secmon_contents_valid = secbool_and(
        secmon_header_sig_valid,
        check_secmon_contents(secmon_hdr, secmon_start - FIRMWARE_START,
                              &FIRMWARE_AREA));
    secmon_valid = secmon_contents_valid;
  }

#else
  secmon_valid = fw_info->header_present;
#endif

  if (sectrue == secmon_valid) {
    ensure_firmware_min_version(hdr->monotonic);
    fw_info->firmware_present = check_image_contents(
        hdr, IMAGE_HEADER_SIZE + fw_info->vhdr.hdrlen, &FIRMWARE_AREA);
    fw_info->firmware_present_backup = fw_info->firmware_present;
  }

  fw_info->hdr = hdr;
}
