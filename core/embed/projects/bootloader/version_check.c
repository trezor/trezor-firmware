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

#include <sec/monoctr.h>
#include "model_version.h"
#include "version_check.h"

// The way monoctr encodes its counters, not the uint8_t the value travels in,
// is what caps them at MONOCTR_MAX_VALUE. monoctr_write rejects anything above
// that, so at runtime the version would simply fail to be stored -- and the
// read-back checks below would then fail the ensure() and halt the device with
// a downgrade-protection error on a perfectly good image. Catch it here
// instead, at build time, for every model.
_Static_assert(BOOTLOADER_MONOTONIC_VERSION <= MONOCTR_MAX_VALUE,
               "BOOTLOADER_MONOTONIC_VERSION exceeds what monoctr can store");
_Static_assert(FIRMWARE_MONOTONIC_VERSION <= MONOCTR_MAX_VALUE,
               "FIRMWARE_MONOTONIC_VERSION exceeds what monoctr can store");
#ifdef SECMON_MONOTONIC_VERSION  // only models with a secmon define it
_Static_assert(SECMON_MONOTONIC_VERSION <= MONOCTR_MAX_VALUE,
               "SECMON_MONOTONIC_VERSION exceeds what monoctr can store");
#endif

void ensure_bootloader_min_version(void) {
  monoctr_write(MONOCTR_BOOTLOADER_VERSION, BOOTLOADER_MONOTONIC_VERSION);
  uint8_t val = 0;
  ensure(monoctr_read(MONOCTR_BOOTLOADER_VERSION, &val), NULL);
  ensure(sectrue * (val == BOOTLOADER_MONOTONIC_VERSION),
         "Bootloader downgrade protection");
}

secbool check_firmware_min_version(uint8_t check_version) {
  uint8_t min_version = 0;
  ensure(monoctr_read(MONOCTR_FIRMWARE_VERSION, &min_version), "monoctr read");

  return (check_version >= min_version) * sectrue;
}

void ensure_firmware_min_version(uint8_t version) {
  monoctr_write(MONOCTR_FIRMWARE_VERSION, version);
  uint8_t val = 0;
  ensure(monoctr_read(MONOCTR_FIRMWARE_VERSION, &val), NULL);
  ensure(sectrue * (val == version), "Firmware downgrade protection");
}

secbool check_secmon_min_version(uint8_t check_version) {
  uint8_t min_version = 0;
  ensure(monoctr_read(MONOCTR_SECMON_VERSION, &min_version), "monoctr read");

  return (check_version >= min_version) * sectrue;
}

void ensure_secmon_min_version(uint8_t version) {
  monoctr_write(MONOCTR_SECMON_VERSION, version);
  uint8_t val = 0;
  ensure(monoctr_read(MONOCTR_SECMON_VERSION, &val), NULL);
  ensure(sectrue * (val == version), "Secmon downgrade protection");
}
