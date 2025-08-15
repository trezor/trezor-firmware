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
