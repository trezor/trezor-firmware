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

#include <trezor_rtl.h>

#include <sec/optiga.h>
#include <sec/optiga_commands.h>
#include <sec/optiga_init.h>
#include <sec/optiga_transport.h>
#include <sec/secret_keys.h>
#include <sys/systick.h>

#include "memzero.h"

#ifdef USE_DBG_CONSOLE
#include <sys/dbg_console.h>
#endif

#if defined(USE_DBG_CONSOLE) && defined(USE_OPTIGA_LOGGING)
#include <inttypes.h>
#if 1  // color log
#define OPTIGA_LOG_FORMAT \
  "%d.%03d \x1b[35moptiga\x1b[0m \x1b[32mDEBUG\x1b[0m %s: "
#else
#define OPTIGA_LOG_FORMAT "%d.%03d optiga DEBUG %s: "
#endif
static void optiga_log_hex(const char *prefix, const uint8_t *data,
                           size_t data_size) {
  ticks_t now = hal_ticks_ms();
  uint32_t sec = now / 1000;
  uint32_t msec = now % 1000;
  dbg_console_printf(OPTIGA_LOG_FORMAT, sec, msec, prefix);
  for (size_t i = 0; i < data_size; i++) {
    dbg_console_printf("%02x", data[i]);
  }
  dbg_console_printf("\n");
}
#endif

optiga_result optiga_init() {
  optiga_transport_power_up();
  return optiga_transport_open_channel();
}

void optiga_deinit() {
  optiga_transport_close_channel();
  optiga_transport_power_down();
}

void optiga_close_channel() { optiga_transport_close_channel(); }

void optiga_power_down() { optiga_transport_power_down(); }

void optiga_init_and_configure(void) {
#if defined(USE_DBG_CONSOLE) && defined(USE_OPTIGA_LOGGING)
  // command log is relatively quiet so we enable it in debug builds
  optiga_command_set_log_hex(optiga_log_hex);
  // transport log can be spammy, uncomment if you want it:
  // optiga_transport_set_log_hex(optiga_log_hex);
#endif

  optiga_init();

  uint8_t secret[OPTIGA_PAIRING_SECRET_SIZE] = {0};
  secbool secret_ok = secret_key_optiga_pairing(secret);

  if (sectrue == secret_ok) {
    // If the shielded connection cannot be established, reset Optiga and
    // continue without it. In this case, OID_KEY_FIDO and OID_KEY_DEV cannot be
    // used, which means device and FIDO attestation will not work.
    if (optiga_sec_chan_handshake(secret, sizeof(secret)) != OPTIGA_SUCCESS) {
      optiga_soft_reset();
    }
  }
  memzero(secret, sizeof(secret));
  ensure(sectrue * (optiga_open_application() == OPTIGA_SUCCESS),
         "Cannot initialize optiga.");
}

#endif  // SECURE_MODE

#ifdef KERNEL_MODE

#include <sec/optiga.h>
#include <sec/optiga_commands.h>
#include <sec/optiga_init.h>
#include <sys/irq.h>

#ifdef USE_RTC

#include <sys/rtc.h>
#include <sys/rtc_scheduler.h>

uint32_t rtc_wakeup_event_id = 0;

void optiga_rtc_wakeup_callback(void *context) {
  optiga_power_down();
  rtc_wakeup_event_id = 0;
}

static void optiga_schedule_power_down(uint32_t power_down_time_s) {
  uint32_t current_timestamp;
  rtc_get_timestamp(&current_timestamp);

  if (!rtc_schedule_wakeup_event(current_timestamp + power_down_time_s,
                                 optiga_rtc_wakeup_callback, NULL,
                                 &rtc_wakeup_event_id)) {
    // Failed to schedule RTC event, deinit optiga right away
    optiga_power_down();
  }
}

#endif

void optiga_suspend() {
#ifdef USE_RTC

  uint8_t sec;
  bool status = optiga_read_sec(&sec);

  optiga_close_channel();

  if (status && sec > OPTIGA_SEC_SUSPEND_THR) {
    // Optiga SEC is high, schedule power down after certain time
    // to make sure SEC has enough time to decrease.
    uint32_t power_down_time_s =
        ((sec - OPTIGA_SEC_SUSPEND_THR) * OPTIGA_T_MAX_MS) / 1000;
    optiga_schedule_power_down(power_down_time_s);

  } else {
    optiga_power_down();
  }

#else

  optiga_deinit();

#endif  // USE_RTC
}

void optiga_resume() {
#ifdef USE_RTC

  if (rtc_wakeup_event_id != 0) {
    rtc_cancel_wakeup_event(rtc_wakeup_event_id);
    rtc_wakeup_event_id = 0;
    optiga_power_down();
  }

#endif

  optiga_init_and_configure();
}

#endif  // KERNEL_MODE
