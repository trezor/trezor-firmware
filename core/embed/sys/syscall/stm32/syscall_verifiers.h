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

#pragma once

#ifdef KERNEL

// ---------------------------------------------------------------------
#include <sys/sysevent.h>

void sysevents_poll__verified(const sysevents_t *awaited,
                              sysevents_t *signalled, uint32_t deadline);

ssize_t syshandle_read__verified(syshandle_t handle, void *buffer,
                                 size_t buffer_size);

ssize_t syshandle_write__verified(syshandle_t handle, const void *data,
                                  size_t data_size);

// ---------------------------------------------------------------------
#include <sys/systask.h>

void system_exit__verified(int exit_code);

void system_exit_error__verified(const char *title, size_t title_len,
                                 const char *message, size_t message_len,
                                 const char *footer, size_t footer_len);

void system_exit_fatal__verified(const char *message, size_t message_len,
                                 const char *file, size_t file_len, int line);

// ---------------------------------------------------------------------
#ifdef USE_DBG_CONSOLE

#include <sys/dbg_console.h>

ssize_t dbg_console_read__verified(void *buffer, size_t buffer_size);

ssize_t dbg_console_write__verified(const void *data, size_t data_size);

#endif

// ---------------------------------------------------------------------
#ifdef USE_DBG_CONSOLE

#include <rtl/logging.h>

bool syslog_start_record__verified(const log_source_t *source,
                                   log_level_t level);

ssize_t syslog_write_chunk__verified(const char *text, size_t text_len,
                                     bool end_record);

bool syslog_set_filter__verified(const char *module_name, log_level_t level);

#endif  // USE_DBG_CONSOLE

// ---------------------------------------------------------------------

#ifdef USE_IPC

#include <sys/ipc.h>

bool ipc_register__verified(systask_id_t origin, void *buffer, size_t size);

bool ipc_try_receive__verified(ipc_message_t *msg);

void ipc_message_free__verified(ipc_message_t *msg);

bool ipc_send__verified(systask_id_t remote, uint32_t fn, const void *data,
                        size_t data_size);

#endif  // USE_IPC

// ---------------------------------------------------------------------
#include <sys/bootutils.h>

void reboot_and_upgrade__verified(const uint8_t hash[32]);

// ---------------------------------------------------------------------

#include <util/boot_image.h>

bool boot_image_check__verified(const boot_image_t *image);

void boot_image_replace__verified(const boot_image_t *image);

// ---------------------------------------------------------------------
#include <io/display.h>

#ifdef FRAMEBUFFER
bool display_get_frame_buffer__verified(display_fb_info_t *fb);
#endif

void display_fill__verified(const gfx_bitblt_t *bb);

void display_copy_rgb565__verified(const gfx_bitblt_t *bb);

// ---------------------------------------------------------------------
#include <io/usb.h>

void usb_get_state__verified(usb_state_t *state);

secbool usb_start__verified(const usb_start_params_t *params);

// ---------------------------------------------------------------------

#ifdef USE_SD_CARD

#include <io/sdcard.h>

secbool __wur sdcard_read_blocks__verified(uint32_t *dest, uint32_t block_num,
                                           uint32_t num_blocks);

secbool __wur sdcard_write_blocks__verified(const uint32_t *src,
                                            uint32_t block_num,
                                            uint32_t num_blocks);

#endif  // USE_SD_CARD

// ---------------------------------------------------------------------
#include <util/unit_properties.h>

void unit_properties_get__verified(unit_properties_t *props);

bool unit_properties_get_sn__verified(uint8_t *device_sn,
                                      size_t max_device_sn_size,
                                      size_t *device_sn_size);

// ---------------------------------------------------------------------
#ifdef USE_OPTIGA

#include <sec/optiga.h>

optiga_sign_result __wur optiga_sign__verified(
    uint8_t index, const uint8_t *digest, size_t digest_size,
    uint8_t *signature, size_t max_sig_size, size_t *sig_size);

bool __wur optiga_cert_size__verified(uint8_t index, size_t *cert_size);

bool __wur optiga_read_cert__verified(uint8_t index, uint8_t *cert,
                                      size_t max_cert_size, size_t *cert_size);

bool __wur optiga_read_sec__verified(uint8_t *sec);

#endif  // USE_OPTIGA

// ---------------------------------------------------------------------
#include <sec/secret_keys.h>

secbool secret_key_delegated_identity__verified(
    uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]);

// ---------------------------------------------------------------------
#include <sec/storage.h>

void storage_setup__verified(PIN_UI_WAIT_CALLBACK callback);

secbool storage_unlock__verified(const uint8_t *pin, size_t pin_len,
                                 const uint8_t *ext_salt);

secbool storage_change_pin__verified(const uint8_t *oldpin, size_t oldpin_len,
                                     const uint8_t *newpin, size_t newpin_len,
                                     const uint8_t *old_ext_salt,
                                     const uint8_t *new_ext_salt);

void storage_ensure_not_wipe_code__verified(const uint8_t *pin, size_t pin_len);

secbool storage_change_wipe_code__verified(const uint8_t *pin, size_t pin_len,
                                           const uint8_t *ext_salt,
                                           const uint8_t *wipe_code,
                                           size_t wipe_code_len);

secbool storage_get__verified(const uint16_t key, void *val,
                              const uint16_t max_len, uint16_t *len);

secbool storage_set__verified(const uint16_t key, const void *val,
                              const uint16_t len);

secbool storage_next_counter__verified(const uint16_t key, uint32_t *count);

// ---------------------------------------------------------------------
#include <sec/rng.h>

void rng_fill_buffer__verified(void *buffer, size_t buffer_size);

bool rng_fill_buffer_strong__verified(void *buffer, size_t buffer_size);

// ---------------------------------------------------------------------
#include <util/translations.h>

bool translations_write__verified(const uint8_t *data, uint32_t offset,
                                  uint32_t len);

const uint8_t *translations_read__verified(uint32_t *len, uint32_t offset);

// ---------------------------------------------------------------------
#include <util/fwutils.h>

int firmware_hash_start__verified(const uint8_t *challenge,
                                  size_t challenge_len);

int firmware_hash_continue__verified(uint8_t *hash, size_t hash_len);

secbool firmware_get_vendor__verified(char *buff, size_t buff_size);

// ---------------------------------------------------------------------
#ifdef USE_BLE

#include <io/ble.h>

bool ble_enter_pairing_mode__verified(const uint8_t *name, size_t name_len);

bool ble_allow_pairing__verified(const uint8_t *pairing_code);

void ble_get_state__verified(ble_state_t *state);

bool ble_get_event__verified(ble_event_t *event);

bool ble_write__verified(const uint8_t *data, size_t len);

secbool ble_read__verified(uint8_t *data, size_t len);

void ble_set_name__verified(const uint8_t *name, size_t len);

bool ble_unpair__verified(const bt_le_addr_t *addr);

uint8_t ble_get_bond_list__verified(bt_le_addr_t *bonds, size_t count);

#endif

// ---------------------------------------------------------------------
#ifdef USE_NRF

#include <io/nrf.h>

bool nrf_update_required__verified(const uint8_t *data, size_t len);

bool nrf_update__verified(const uint8_t *data, size_t len);

#endif
// ---------------------------------------------------------------------

#ifdef USE_POWER_MANAGER

#include <sys/power_manager.h>

pm_status_t pm_get_state__verified(pm_state_t *status);

bool pm_get_events__verified(pm_event_t *event);

pm_status_t pm_suspend__verified(wakeup_flags_t *wakeup_reason);

#endif

// ---------------------------------------------------------------------
#ifdef USE_HW_JPEG_DECODER

#include <gfx/jpegdec.h>

jpegdec_state_t jpegdec_process__verified(jpegdec_input_t *input);

bool jpegdec_get_info__verified(jpegdec_image_t *image);

bool jpegdec_get_slice_rgba8888__verified(void *rgba8888,
                                          jpegdec_slice_t *slice);

bool jpegdec_get_slice_mono8__verified(void *mono8, jpegdec_slice_t *slice);

#endif  // USE_HW_JPEG_DECODER

// ---------------------------------------------------------------------
#ifdef USE_DMA2D

#include <gfx/dma2d_bitblt.h>

bool dma2d_rgb565_fill__verified(const gfx_bitblt_t *bb);

bool dma2d_rgb565_copy_mono4__verified(const gfx_bitblt_t *bb);

bool dma2d_rgb565_copy_rgb565__verified(const gfx_bitblt_t *bb);

bool dma2d_rgb565_blend_mono4__verified(const gfx_bitblt_t *bb);

bool dma2d_rgb565_blend_mono8__verified(const gfx_bitblt_t *bb);

bool dma2d_rgba8888_fill__verified(const gfx_bitblt_t *bb);

bool dma2d_rgba8888_copy_mono4__verified(const gfx_bitblt_t *bb);

bool dma2d_rgba8888_copy_rgb565__verified(const gfx_bitblt_t *bb);

bool dma2d_rgba8888_copy_rgba8888__verified(const gfx_bitblt_t *bb);

bool dma2d_rgba8888_blend_mono4__verified(const gfx_bitblt_t *bb);

bool dma2d_rgba8888_blend_mono8__verified(const gfx_bitblt_t *bb);

#endif

// ---------------------------------------------------------------------
#ifdef USE_BUTTON

#include <io/button.h>

bool button_get_event__verified(button_event_t *event);

#endif

// ---------------------------------------------------------------------
#ifdef USE_TROPIC

bool tropic_ping__verified(const uint8_t *msg_out, uint8_t *msg_in,
                           uint16_t msg_len);

bool tropic_ecc_key_generate__verified(uint16_t slot_index);

bool tropic_ecc_sign__verified(uint16_t key_slot_index, const uint8_t *dig,
                               uint16_t dig_len, uint8_t *sig);

bool tropic_data_read__verified(uint16_t udata_slot, uint8_t *data,
                                uint16_t *size);

#endif

#ifdef USE_APP_LOADING

#include <util/app_loader.h>

bool app_task_spawn__verified(const app_hash_t *hash, systask_id_t *task_id);

bool app_task_get_pminfo__verified(systask_id_t task_id,
                                   systask_postmortem_t *pminfo);

app_cache_image_t *app_cache_create_image__verified(const app_hash_t *hash,
                                                    size_t image_size);

bool app_cache_write_image__verified(app_cache_image_t *image, uintptr_t offset,
                                     const void *data, size_t data_size);

#endif

#endif  // KERNEL
