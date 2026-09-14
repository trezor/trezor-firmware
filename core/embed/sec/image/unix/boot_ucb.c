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

#include <trezor_rtl.h>

#include <sec/boot_header.h>
#include <sec/boot_ucb.h>
#include <sec/image_hash_conf.h>
#include <sys/flash.h>

#define BOOT_UCB_MAGIC 0x5A8C7BF3

// The UCB is a handoff to the boardloader, which the emulator does not have: it
// boots the bootloader directly. So nothing here ever installs a staged image.
// The block is still written for real, into the emulated BOOTUCB_AREA, so the
// arming path is exercised end to end and an emulator boardloader could later
// read it.
//
// The one thing that cannot carry over is the address fields. They are DEVICE
// flash addresses, and the emulator's flash is an mmap at an address the kernel
// chose, so what lands in those uint32_t fields is a narrowed host pointer --
// meaningless, but also unread. The `hash` and `magic` are exact, which is what
// makes the written block worth checking.
//
// No MPU reconfiguration, unlike the stm32 implementation: there is no MPU, and
// the mapping is writable throughout.

secbool boot_ucb_write(const void* header, uint32_t code_address) {
  const boot_header_auth_t* hdr = (const boot_header_auth_t*)header;

  boot_ucb_t ucb = {
      .magic = BOOT_UCB_MAGIC,
      .header_address = (uint32_t)(uintptr_t)header,
      .code_address = code_address,
  };

  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, (const uint8_t*)hdr, hdr->header_size);
  IMAGE_HASH_FINAL(&ctx, ucb.hash);

  if (sectrue != flash_area_erase(&BOOTUCB_AREA, NULL)) {
    return secfalse;
  }
  if (sectrue != flash_unlock_write()) {
    return secfalse;
  }
  if (sectrue !=
      flash_area_write_data(&BOOTUCB_AREA, 0, (const void*)&ucb, sizeof(ucb))) {
    return secfalse;
  }
  ensure(flash_lock_write(), NULL);

  return sectrue;
}

secbool boot_ucb_erase(void) {
  secbool result = flash_area_is_erased(&BOOTUCB_AREA);
  if (sectrue != result) {
    result = flash_area_erase(&BOOTUCB_AREA, NULL);
  }
  return result;
}
