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

#ifdef USE_NFC

#include <trezor_rtl.h>

#include <io/nfc.h>
#include <rtl/cli.h>
#include <stdint.h>
#include <sys/systick.h>

#include "prodtest_error_codes.h"

static nfc_dev_info_t dev_info = {0};

/* Sorts v[0..n-1] IN PLACE (insertion sort) and returns the trimmed mean in
 * plain LSB (rounded, 0..255). k = samples dropped on each side; k = (n-1)/2
 * returns the median (for even n, the rounded mean of the two middle samples).
 * Returns 0xFFFF on invalid arguments (n == 0, n > 16, 2k >= n). */
static inline uint16_t trimmed_mean(uint8_t* v, uint8_t n, uint8_t k) {
  if (n == 0u || n > 16u || 2u * k >= n) return 0xFFFFu;
  for (uint8_t i = 1u; i < n; i++) { /* insertion sort */
    uint8_t x = v[i];
    int j = (int)i - 1;
    while (j >= 0 && v[j] > x) {
      v[j + 1] = v[j];
      j--;
    }
    v[j + 1] = x;
  }
  uint32_t sum = 0u;
  for (uint8_t i = k; i < n - k; i++) sum += v[i];
  uint32_t cnt = n - 2u * k;
  return (uint16_t)((sum + cnt / 2u) / cnt); /* rounded, plain LSB */
}

static nfc_status_t nfc_print_antenna_info(cli_t* cli) {
  bool tx_en = false;
  uint16_t rssi = 0;

  nfc_status_t ret = nfc_get_tx_en(&tx_en);
  if (ret != NFC_OK) {
    cli_error(cli, PRODTEST_ERR_NFC_UNEXPECTED, "NFC TX_EN error");
    return NFC_ERROR;
  }

  if (tx_en) {
    ret = nfc_get_rssi(&rssi);
    if (ret != NFC_OK) {
      cli_error(cli, PRODTEST_ERR_NFC_UNEXPECTED, "NFC RSSI error");
      return NFC_ERROR;
    }
    cli_trace(cli, " TX_en=%d; RSSI=%03d", tx_en, rssi);
  }

  return NFC_OK;
}

static void prodtest_nfc_read_card(cli_t* cli) {
  uint32_t timeout = 0;
  bool timeout_set = false;
  memset(&dev_info, 0, sizeof(dev_info));

  if (cli_has_arg(cli, "timeout")) {
    if (!cli_arg_uint32(cli, "timeout", &timeout)) {
      cli_error_arg(cli, "Expecting timeout argument.");
      return;
    }
    timeout_set = true;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  nfc_status_t ret = nfc_init();

  if (ret != NFC_OK) {
    cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_INIT, "NFC init failed");
    goto cleanup;
  } else {
    if (timeout_set) {
      cli_trace(cli, "NFC activated in reader mode for %d ms.", timeout);
    } else {
      cli_trace(cli, "NFC activated in reader mode");
    }
  }

  if (NFC_OK != nfc_register_tech(NFC_POLLER_TECH_A | NFC_POLLER_TECH_B)) {
    cli_error(cli, PRODTEST_ERR_NFC_TECH_REG, "NFC tech registration failed");
    goto cleanup;
  }

  if (NFC_OK != nfc_activate_stm()) {
    cli_error(cli, PRODTEST_ERR_NFC_ACTIVATION, "NFC activation failed");
    goto cleanup;
  }

  nfc_event_t nfc_event;
  uint32_t expire_time = ticks_timeout(timeout);

  while (true) {
    if (timeout_set && ticks_expired(expire_time)) {
      cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    nfc_status_t nfc_status = nfc_get_event(&nfc_event);

    if (nfc_status != NFC_OK) {
      cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_ERROR, "NFC error");
      goto cleanup;
    }

    if (nfc_event == NFC_EVENT_ACTIVATED) {
      nfc_dev_read_info(&dev_info);

      cli_trace(cli, "NFC card detected.");

      switch (dev_info.type) {
        case NFC_DEV_TYPE_A:
          cli_trace(cli, "NFC Type A: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_B:
          cli_trace(cli, "NFC Type B: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_F:
          cli_trace(cli, "NFC Type F: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_V:
          cli_trace(cli, "NFC Type V: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_ST25TB:
          cli_trace(cli, "NFC Type ST25TB: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_AP2P:
          cli_trace(cli, "NFC Type AP2P: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_UNKNOWN:
          cli_trace(cli, "NFC Type UNKNOWN");
          break;
        default:
          cli_error(cli, PRODTEST_ERR_NFC_UNEXPECTED, "NFC ERROR Unexpected");
          goto cleanup;
      }

      nfc_print_antenna_info(cli);
      if (timeout_set) {
        nfc_dev_deactivate();
        cli_trace(cli, "NFC reader mode over");
        break;
      }

      systick_delay_ms(100);
      nfc_dev_deactivate();
    }

    if (cli_aborted(cli)) {
      goto cleanup;
    }

    systick_delay_ms(1);
  }

  cli_ok(cli, "");

cleanup:
  nfc_deinit();
}

static void prodtest_nfc_emulate_card(cli_t* cli) {
  uint32_t timeout = 0;
  bool timeout_set = false;

  if (cli_has_arg(cli, "timeout")) {
    if (!cli_arg_uint32(cli, "timeout", &timeout)) {
      cli_error_arg(cli, "Expecting timeout argument.");
      return;
    }
    timeout_set = true;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  nfc_status_t ret = nfc_init();

  if (ret != NFC_OK) {
    cli_error(cli, PRODTEST_ERR_NFC_EMULATE_INIT, "NFC init failed");
    goto cleanup;
  } else {
    if (timeout_set) {
      cli_trace(cli, "Emulation started for %d ms", timeout);
    } else {
      cli_trace(cli, "Emulation started");
    }
  }

  nfc_register_tech(NFC_CARD_EMU_TECH_A);
  nfc_activate_stm();

  uint32_t expire_time = ticks_timeout(timeout);
  nfc_event_t nfc_event;

  while (!timeout_set || !ticks_expired(expire_time)) {
    nfc_status_t nfc_status = nfc_get_event(&nfc_event);

    if (nfc_status != NFC_OK) {
      cli_error(cli, PRODTEST_ERR_NFC_EMULATE_ERROR, "NFC error");
      goto cleanup;
    }

    if (cli_aborted(cli)) {
      goto cleanup;
    }
    systick_delay_ms(1);
  }

  cli_trace(cli, "Emulation over");

  cli_ok(cli, "");

cleanup:
  nfc_deinit();
}

static void prodtest_nfc_write_card(cli_t* cli) {
  uint32_t timeout = 0;
  bool timeout_set = false;
  memset(&dev_info, 0, sizeof(dev_info));

  if (cli_has_arg(cli, "timeout")) {
    if (!cli_arg_uint32(cli, "timeout", &timeout)) {
      cli_error_arg(cli, "Expecting timeout argument.");
      return;
    }
    timeout_set = true;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  nfc_status_t ret = nfc_init();

  if (ret != NFC_OK) {
    cli_error(cli, PRODTEST_ERR_NFC_WRITE_CARD_INIT, "NFC init failed");
    goto cleanup;
  } else {
    if (timeout_set) {
      cli_trace(cli,
                "NFC reader on, put the card on the reader (timeout %d ms)",
                timeout);
    } else {
      cli_trace(cli, "NFC reader on, put the card on the reader");
    }
  }

  nfc_register_tech(NFC_POLLER_TECH_A | NFC_POLLER_TECH_B | NFC_POLLER_TECH_F |
                    NFC_POLLER_TECH_V);
  nfc_activate_stm();

  nfc_event_t nfc_event;
  uint32_t expire_time = ticks_timeout(timeout);

  while (true) {
    if (timeout_set && ticks_expired(expire_time)) {
      cli_error(cli, PRODTEST_ERR_NFC_WRITE_CARD_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    nfc_status_t nfc_status = nfc_get_event(&nfc_event);

    if (nfc_status != NFC_OK) {
      cli_error(cli, PRODTEST_ERR_NFC_WRITE_CARD_ERROR, "NFC error");
      goto cleanup;
    }

    if (nfc_event == NFC_EVENT_ACTIVATED) {
      nfc_dev_read_info(&dev_info);

      if (dev_info.type != NFC_DEV_TYPE_A) {
        cli_error(cli, PRODTEST_ERR_NFC_TYPE_A_ONLY,
                  "Only NFC type A cards supported");
        goto cleanup;
      }

      cli_trace(cli, "Writing URI to NFC tag %s", dev_info.uid);
      nfc_dev_write_ndef_uri();

      if (timeout_set) {
        nfc_dev_deactivate();
        cli_trace(cli, "NFC reader mode over");
        break;
      }

      systick_delay_ms(100);
      nfc_dev_deactivate();
    }

    if (cli_aborted(cli)) {
      goto cleanup;
    }

    systick_delay_ms(1);
  }

  cli_ok(cli, "");

cleanup:
  nfc_deinit();
}

static void prodtest_nfc_self_test(cli_t* cli) {
  uint32_t timeout = 0;
  bool timeout_set = false;
  memset(&dev_info, 0, sizeof(dev_info));

  if (cli_has_arg(cli, "timeout")) {
    if (!cli_arg_uint32(cli, "timeout", &timeout)) {
      cli_error_arg(cli, "Expecting timeout argument.");
      return;
    }
    timeout_set = true;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  nfc_status_t ret = nfc_init();

  if (ret != NFC_OK) {
    cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_INIT, "NFC init failed");
    goto cleanup;
  } else {
    if (timeout_set) {
      cli_trace(cli, "NFC activated in self-test mode for %d ms.", timeout);
    } else {
      cli_trace(cli, "NFC activated in self-test mode");
    }
  }

  if (NFC_OK != nfc_register_tech(NFC_POLLER_TECH_A | NFC_POLLER_TECH_B)) {
    cli_error(cli, PRODTEST_ERR_NFC_TECH_REG, "NFC tech registration failed");
    goto cleanup;
  }

  if (NFC_OK != nfc_activate_stm()) {
    cli_error(cli, PRODTEST_ERR_NFC_ACTIVATION, "NFC activation failed");
    goto cleanup;
  }

  uint32_t expire_time = ticks_timeout(timeout);

  while (true) {
    if (timeout_set && ticks_expired(expire_time)) {
      cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    if (cli_aborted(cli)) {
      goto cleanup;
    }

#define ST25R210_AMP_PAHASE_CALIBRATION_SAMPLES 16
#define ST25R210_ANT_REV_B_AMP_REF 235
#define ST25R210_ANT_REV_B_PHASE_REF 118
#define ST25R210_ANT_REV_B_AMP_PHASE_TOLERANCE 0.15f

    uint8_t amp_array[ST25R210_AMP_PAHASE_CALIBRATION_SAMPLES] = {0};
    uint8_t phase_array[ST25R210_AMP_PAHASE_CALIBRATION_SAMPLES] = {0};
    uint8_t amp = 0;
    uint8_t phase = 0;
    for (uint8_t idx = 0; idx < ST25R210_AMP_PAHASE_CALIBRATION_SAMPLES;
         idx++) {
      ret = nfc_amp_phase_calibration(&amp_array[idx], &phase_array[idx]);
      if (ret != NFC_OK) {
        cli_error(cli, PRODTEST_ERR_NFC_UNEXPECTED,
                  "NFC Amplitude/Phase calibration error");
        goto cleanup;
      }
    }

    amp = trimmed_mean(
        amp_array, ST25R210_AMP_PAHASE_CALIBRATION_SAMPLES,
        (uint8_t)((ST25R210_AMP_PAHASE_CALIBRATION_SAMPLES - 1u) / 2u));
    phase = trimmed_mean(
        phase_array, ST25R210_AMP_PAHASE_CALIBRATION_SAMPLES,
        (uint8_t)((ST25R210_AMP_PAHASE_CALIBRATION_SAMPLES - 1u) / 2u));

    cli_trace(cli, " Amp=%03d; Phase=%03d", amp, phase);

    if (amp < ST25R210_ANT_REV_B_AMP_REF / 2) {
      cli_error(
          cli, PRODTEST_ERR_NFC_READ_CARD_ERROR,
          "NFC antenna amplitude is too low - antenna may be disconnected "
          "or damaged");
    } else {
      uint8_t amp_diff = (amp > ST25R210_ANT_REV_B_AMP_REF)
                             ? (amp - ST25R210_ANT_REV_B_AMP_REF)
                             : (ST25R210_ANT_REV_B_AMP_REF - amp);
      uint8_t phase_diff = (phase > ST25R210_ANT_REV_B_PHASE_REF)
                               ? (phase - ST25R210_ANT_REV_B_PHASE_REF)
                               : (ST25R210_ANT_REV_B_PHASE_REF - phase);
      if ((phase_diff > (ST25R210_ANT_REV_B_PHASE_REF *
                         ST25R210_ANT_REV_B_AMP_PHASE_TOLERANCE)) ||
          (amp_diff > (ST25R210_ANT_REV_B_AMP_REF *
                       ST25R210_ANT_REV_B_AMP_PHASE_TOLERANCE))) {
        cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_ERROR,
                  "NFC antenna amplitude or phase is out of 15%% range - "
                  "antenna may be detuned");
      }
    }

    systick_delay_ms(500);
  }

  cli_ok(cli, "");

cleanup:
  nfc_deinit();
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "nfc-read-card",
  .func = prodtest_nfc_read_card,
  .info = "Activate NFC in reader mode",
  .args = "[<timeout>]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-emulate-card",
  .func = prodtest_nfc_emulate_card,
  .info = "Activate NFC in card emulation (CE) mode",
  .args = "[<timeout>]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-write-card",
  .func = prodtest_nfc_write_card,
  .info = "Activate NFC in reader mode and write a URI to the attached card",
  .args = "[<timeout>]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-self-test",
  .func = prodtest_nfc_self_test,
  .info = "Activate NFC in self-test mode",
  .args = "[<timeout>]"
);

#endif  // USE_NFC
