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

#ifdef SECMON

#include <trezor_rtl.h>

#include <sec/random_delays.h>
#include <sec/rng.h>
#include <sec/secret.h>
#include <sec/secret_keys.h>
#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/irq.h>
#include <sys/system.h>
#include <util/board_capabilities.h>
#include <util/fwutils.h>
#include <util/unit_properties.h>

#ifdef USE_BACKUP_RAM
#include <sys/backup_ram.h>
#endif

#ifdef USE_OPTIGA
#include <sec/optiga.h>
#include <sec/optiga_init.h>
#endif

#ifdef USE_SUSPEND
#include <sys/suspend_io.h>
#endif

#include <util/boot_image.h>

#include "smcall_numbers.h"
#include "smcall_probe.h"
#include "smcall_verifiers.h"

__attribute((no_stack_protector)) void smcall_handler(uint32_t *args,
                                                      uint32_t smcall) {
  switch (smcall) {
    case SMCALL_BOOTARGS_SET: {
      boot_command_t command = args[0];
      const void *args_ptr = (const void *)args[1];
      size_t args_len = args[2];
      bootargs_set__verified(command, args_ptr, args_len);
    } break;

    case SMCALL_BOOTARGS_GET_ARGS: {
      boot_args_t *boot_args = (boot_args_t *)args[0];
      bootargs_get_args__verified(boot_args);
    } break;

    case SMCALL_BOOT_IMAGE_CHECK: {
      const boot_image_t *image = (const boot_image_t *)args[0];
      args[0] = boot_image_check__verified(image);
    } break;

    case SMCALL_BOOT_IMAGE_REPLACE: {
      const boot_image_t *image = (const boot_image_t *)args[0];
      boot_image_replace__verified(image);
    } break;

    case SMCALL_GET_BOARD_NAME: {
      args[0] = get_board_name();
    } break;

    case SMCALL_GET_BOARDLOADER_VERSION: {
      boardloader_version_t *version = (boardloader_version_t *)args[0];
      get_boardloader_version(version);
    } break;

    case SMCALL_REBOOT_DEVICE: {
      reboot_device();
    } break;

    case SMCALL_REBOOT_TO_BOOTLOADER: {
      reboot_to_bootloader();
    } break;

    case SMCALL_REBOOT_AND_UPGRADE: {
      const uint8_t *hash = (const uint8_t *)args[0];
      reboot_and_upgrade__verified(hash);
    } break;

    case SMCALL_REBOOT_TO_OFF: {
      reboot_to_off();
    } break;

    case SMCALL_REBOOT_WITH_RSOD: {
      const systask_postmortem_t *pminfo =
          (const systask_postmortem_t *)args[0];
      reboot_with_rsod__verified(pminfo);
    } break;

#ifdef USE_SUSPEND
    case SMCALL_SUSPEND_CPU: {
      suspend_cpu();
    } break;

    case SMCALL_SUSPEND_SECURE_DRIVERS: {
      suspend_secure_drivers();
    } break;

    case SMCALL_RESUME_SECURE_DRIVERS: {
      resume_secure_drivers();
    } break;
#endif  // USE_SUSPEND

    case SMCALL_UNIT_PROPERTIES_GET: {
      unit_properties_t *props = (unit_properties_t *)args[0];
      unit_properties_get__verified(props);
    } break;

    case SMCALL_UNIT_PROPERTIES_GET_SN: {
      uint8_t *device_sn = (uint8_t *)args[0];
      size_t max_device_sn_size = args[1];
      size_t *device_sn_size = (size_t *)args[2];
      args[0] = unit_properties_get_sn__verified(device_sn, max_device_sn_size,
                                                 device_sn_size);
    } break;

#ifdef LOCKABLE_BOOTLOADER
    case SMCALL_SECRET_BOOTLOADER_LOCKED: {
      args[0] = secret_bootloader_locked();
    } break;
#endif

#ifdef USE_NRF_AUTH
    case SMCALL_SECRET_VALIDATE_NRF_PAIRING: {
      const uint8_t *message = (const uint8_t *)args[0];
      size_t message_len = args[1];
      const uint8_t *mac = (const uint8_t *)args[2];
      size_t mac_len = args[3];
      args[0] = secret_validate_nrf_pairing__verified(message, message_len, mac,
                                                      mac_len);
    } break;
#endif  // USE_NRF_AUTH

    case SMCALL_WAIT_RANDOM: {
      wait_random();
    } break;

    case SMCALL_RANDOM_DELAYS_REFRESH_RDI: {
      random_delays_refresh_rdi();
    } break;

#ifdef USE_OPTIGA
    case SMCALL_OPTIGA_SIGN: {
      uint8_t index = args[0];
      const uint8_t *digest = (const uint8_t *)args[1];
      size_t digest_size = args[2];
      uint8_t *signature = (uint8_t *)args[3];
      size_t max_sig_size = args[4];
      size_t *sig_size = (size_t *)args[5];
      args[0] = optiga_sign__verified(index, digest, digest_size, signature,
                                      max_sig_size, sig_size);
    } break;

    case SMCALL_OPTIGA_CERT_SIZE: {
      uint8_t index = args[0];
      size_t *cert_size = (size_t *)args[1];
      args[0] = optiga_cert_size__verified(index, cert_size);
    } break;

    case SMCALL_OPTIGA_READ_CERT: {
      uint8_t index = args[0];
      uint8_t *cert = (uint8_t *)args[1];
      size_t max_cert_size = args[2];
      size_t *cert_size = (size_t *)args[3];
      args[0] =
          optiga_read_cert__verified(index, cert, max_cert_size, cert_size);
    } break;

    case SMCALL_OPTIGA_READ_SEC: {
      uint8_t *sec = (uint8_t *)args[0];
      args[0] = optiga_read_sec__verified(sec);
    } break;

    case SMCALL_OPTIGA_CLOSE_CHANNEL: {
      optiga_close_channel();
    } break;

    case SMCALL_OPTIGA_POWER_DOWN: {
      optiga_power_down();
    } break;

    case SMCALL_OPTIGA_INIT_AND_CONFIGURE: {
      optiga_init_and_configure();
    } break;

#if PYOPT == 0
    case SMCALL_OPTIGA_SET_SEC_MAX: {
      optiga_set_sec_max();
    } break;
#endif
#endif  // USE_OPTIGA

    case SMCALL_SECRET_KEYS_GET_DELEGATED_IDENTITY_KEY: {
      uint16_t rotation_index = args[0];
      uint8_t *dest = (uint8_t *)args[1];
      args[0] = secret_key_delegated_identity__verified(rotation_index, dest);
    } break;

    case SMCALL_STORAGE_SETUP: {
      PIN_UI_WAIT_CALLBACK callback = (PIN_UI_WAIT_CALLBACK)args[0];
      storage_setup__verified(callback);
    } break;

    case SMCALL_STORAGE_WIPE: {
      storage_wipe();
    } break;

    case SMCALL_STORAGE_IS_UNLOCKED: {
      args[0] = storage_is_unlocked();
    } break;

    case SMCALL_STORAGE_LOCK: {
      storage_lock();
    } break;

    case SMCALL_STORAGE_UNLOCK: {
      const uint8_t *pin = (const uint8_t *)args[0];
      size_t pin_len = args[1];
      const uint8_t *ext_salt = (const uint8_t *)args[2];
      args[0] = storage_unlock__verified(pin, pin_len, ext_salt);
    } break;

    case SMCALL_STORAGE_HAS_PIN: {
      args[0] = storage_has_pin();
    } break;

    case SMCALL_STORAGE_PIN_FAILS_INCREASE: {
      args[0] = storage_pin_fails_increase();
    } break;

    case SMCALL_STORAGE_GET_PIN_REM: {
      args[0] = storage_get_pin_rem();
    } break;

    case SMCALL_STORAGE_CHANGE_PIN: {
      const uint8_t *oldpin = (const uint8_t *)args[0];
      size_t oldpin_len = args[1];
      const uint8_t *newpin = (const uint8_t *)args[2];
      size_t newpin_len = args[3];
      const uint8_t *old_ext_salt = (const uint8_t *)args[4];
      const uint8_t *new_ext_salt = (const uint8_t *)args[5];
      args[0] = storage_change_pin__verified(
          oldpin, oldpin_len, newpin, newpin_len, old_ext_salt, new_ext_salt);
    } break;

    case SMCALL_STORAGE_ENSURE_NOT_WIPE_CODE: {
      const uint8_t *pin = (const uint8_t *)args[0];
      size_t pin_len = args[1];
      storage_ensure_not_wipe_code__verified(pin, pin_len);
    } break;

    case SMCALL_STORAGE_HAS_WIPE_CODE: {
      args[0] = storage_has_wipe_code();
    } break;

    case SMCALL_STORAGE_CHANGE_WIPE_CODE: {
      const uint8_t *pin = (const uint8_t *)args[0];
      size_t pin_len = args[1];
      const uint8_t *ext_salt = (const uint8_t *)args[2];
      const uint8_t *wipe_code = (const uint8_t *)args[3];
      size_t wipe_code_len = args[4];
      args[0] = storage_change_wipe_code__verified(pin, pin_len, ext_salt,
                                                   wipe_code, wipe_code_len);
    } break;

    case SMCALL_STORAGE_HAS: {
      uint16_t key = (uint16_t)args[0];
      args[0] = storage_has(key);
    } break;

    case SMCALL_STORAGE_GET: {
      uint16_t key = (uint16_t)args[0];
      void *val = (void *)args[1];
      uint16_t max_len = (uint16_t)args[2];
      uint16_t *len = (uint16_t *)args[3];
      args[0] = storage_get__verified(key, val, max_len, len);
    } break;

    case SMCALL_STORAGE_SET: {
      uint16_t key = (uint16_t)args[0];
      const void *val = (const void *)args[1];
      uint16_t len = (uint16_t)args[2];
      args[0] = storage_set__verified(key, val, len);
    } break;

    case SMCALL_STORAGE_DELETE: {
      uint16_t key = (uint16_t)args[0];
      args[0] = storage_delete(key);
    } break;

    case SMCALL_STORAGE_SET_COUNTER: {
      uint16_t key = (uint16_t)args[0];
      uint32_t count = args[1];
      args[0] = storage_set_counter(key, count);
    } break;

    case SMCALL_STORAGE_NEXT_COUNTER: {
      uint16_t key = (uint16_t)args[0];
      uint32_t *count = (uint32_t *)args[1];
      args[0] = storage_next_counter__verified(key, count);
    } break;

    case SMCALL_RNG_FILL_BUFFER: {
      uint8_t *buffer = (uint8_t *)args[0];
      size_t buffer_size = args[1];
      rng_fill_buffer__verified(buffer, buffer_size);
    } break;

    case SMCALL_RNG_FILL_BUFFER_STRONG: {
      uint8_t *buffer = (uint8_t *)args[0];
      size_t buffer_size = args[1];
      args[0] = rng_fill_buffer_strong__verified(buffer, buffer_size);
    } break;

    case SMCALL_FIRMWARE_GET_VENDOR: {
      char *buff = (char *)args[0];
      size_t buff_size = args[1];
      args[0] = firmware_get_vendor__verified(buff, buff_size);
    } break;

    case SMCALL_FIRMWARE_HASH_START: {
      const uint8_t *challenge = (const uint8_t *)args[0];
      size_t challenge_len = args[1];
      args[0] = firmware_hash_start__verified(challenge, challenge_len);
    } break;

    case SMCALL_FIRMWARE_HASH_CONTINUE: {
      uint8_t *hash = (uint8_t *)args[0];
      size_t hash_len = args[1];
      args[0] = firmware_hash_continue__verified(hash, hash_len);
    } break;

#ifdef USE_TROPIC
    case SMCALL_TROPIC_PING: {
      const uint8_t *msg_out = (const uint8_t *)args[0];
      uint8_t *msg_in = (uint8_t *)args[1];
      uint16_t msg_len = (uint16_t)args[2];
      args[0] = tropic_ping__verified(msg_out, msg_in, msg_len);
    } break;

    case SMCALL_TROPIC_ECC_KEY_GENERATE: {
      uint16_t slot_index = (uint16_t)args[0];
      args[0] = tropic_ecc_key_generate__verified(slot_index);
    } break;

    case SMCALL_TROPIC_ECC_SIGN: {
      uint16_t key_slot_index = (uint16_t)args[0];
      const uint8_t *dig = (const uint8_t *)args[1];
      uint16_t dig_len = (uint16_t)args[2];
      uint8_t *sig = (uint8_t *)args[3];
      args[0] = tropic_ecc_sign__verified(key_slot_index, dig, dig_len, sig);
    } break;

    case SMCALL_TROPIC_DATA_READ: {
      uint16_t udata_slot = (uint16_t)args[0];
      uint8_t *data = (uint8_t *)args[1];
      uint16_t *size = (uint16_t *)args[2];
      args[0] = tropic_data_read__verified(udata_slot, data, size);
    } break;
#endif

#ifdef USE_BACKUP_RAM
    case SMCALL_BACKUP_RAM_SEARCH: {
      uint16_t min_key = (uint16_t)args[0];
      args[0] = backup_ram_search(min_key);
    } break;

    case SMCALL_BACKUP_RAM_READ: {
      uint16_t key = (uint16_t)args[0];
      void *buffer = (void *)args[1];
      size_t buffer_size = (size_t)args[2];
      size_t *data_size = (size_t *)args[3];
      args[0] = backup_ram_read__verified(key, buffer, buffer_size, data_size);
    } break;

    case SMCALL_BACKUP_RAM_WRITE: {
      uint16_t key = (uint16_t)args[0];
      backup_ram_item_type_t type = (backup_ram_item_type_t)args[1];
      const void *data = (const void *)args[2];
      size_t data_size = (size_t)args[3];
      args[0] = backup_ram_write__verified(key, type, data, data_size);
    } break;
#endif  // USE_BACKUP_RAM

    default:
      system_exit_fatal("Invalid smcall", __FILE__, __LINE__);
      break;
  }
}

__attribute__((cmse_nonsecure_entry)) void smcall_invoke(
    smcall_args_t *args, smcall_number_t smcall) {
  if (!probe_write_access(args, sizeof(*args))) {
    system_exit_fatal("Invalid smcall args", __FILE__, __LINE__);
  }

  smcall_handler(args->arg, smcall);
}

#endif  // SECMON
