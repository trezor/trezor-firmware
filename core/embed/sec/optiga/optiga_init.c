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
