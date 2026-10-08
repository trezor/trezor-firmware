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
#include <sys/systick.h>

#include "prodtest_error_codes.h"

static nfc_dev_info_t dev_info = {0};

// #ifndef ELEM_SWAP(a, b)
#define ELEM_SWAP(a, b)       \
  {                           \
    register uint8_t t = (a); \
    (a) = (b);                \
    (b) = t;                  \
  }
// #endif

uint8_t kth_smallest(uint8_t a[], uint16_t n, uint16_t k) {
  uint64_t i, j, l, m;
  uint8_t x;
  l = 0;
  m = n - 1;
  while (l < m) {
    x = a[k];
    i = l;
    j = m;
    do {
      while (a[i] < x) i++;
      while (x < a[j]) j--;
      if (i <= j) {
        ELEM_SWAP(a[i], a[j]);
        i++;
        j--;
      }
    } while (i <= j);
    if (j < k) l = i;
    if (k < i) m = j;
  }
  return a[k];
}

#define wirth_median(a, n) \
  kth_smallest(a, n, (((n) & 1) ? ((n) / 2) : (((n) / 2) - 1)))

static nfc_status_t nfc_print_antenna_info(cli_t* cli) {
  bool tx_en = false;
  // int8_t wu_i = 0;
  // int8_t wu_q = 0;
  int8_t sense_adc = 0;
  // uint16_t rssi = 0;
  uint8_t amp = 0;
  uint8_t phase = 0;

  nfc_status_t ret = nfc_get_tx_en(&tx_en);
  if (ret != NFC_OK) {
    cli_error(cli, PRODTEST_ERR_NFC_UNEXPECTED, "NFC TX_EN error");
    return NFC_ERROR;
  }

  // TODO: reduce the gain before using it
  // the result is saturated +/- 95
  // ret = nfc_get_wu_i_q(false, &wu_i, &wu_q);
  // if (ret != NFC_OK) {
  //   cli_error(cli, PRODTEST_ERR_NFC_UNEXPECTED, "NFC WU I/Q error");
  //   return NFC_ERROR;
  // }

#define NUM_CALIBRATION_SAMPLES 16
  uint8_t amp_array[NUM_CALIBRATION_SAMPLES] = {0};
  uint8_t phase_array[NUM_CALIBRATION_SAMPLES] = {0};
  for (uint8_t idx = 0; idx < NUM_CALIBRATION_SAMPLES; idx++) {
    ret = nfc_amp_phase_calibration(&amp_array[idx], &phase_array[idx]);
    if (ret != NFC_OK) {
      cli_error(cli, PRODTEST_ERR_NFC_UNEXPECTED,
                "NFC Amplitude/Phase calibration error");
      return NFC_ERROR;
    }
  }
  amp = wirth_median(amp_array, NUM_CALIBRATION_SAMPLES);
  phase = wirth_median(phase_array, NUM_CALIBRATION_SAMPLES);

  if (!tx_en) {
    uint8_t sense_array[NUM_CALIBRATION_SAMPLES] = {0};
    for (uint8_t idx = 0; idx < NUM_CALIBRATION_SAMPLES; idx++) {
      ret = nfc_get_sense_rf(&sense_adc);
      if (ret != NFC_OK) {
        cli_error(cli, PRODTEST_ERR_NFC_UNEXPECTED, "NFC Sense RF error");
        return NFC_ERROR;
      }
    }
    sense_adc = wirth_median(sense_array, NUM_CALIBRATION_SAMPLES);
  }

  // if (tx_en) {
  //   ret = nfc_get_rssi(&rssi);
  //   if (ret != NFC_OK) {
  //     cli_error(cli, PRODTEST_ERR_NFC_UNEXPECTED, "NFC RSSI error");
  //     return NFC_ERROR;
  //   }
  // }

  cli_trace(cli, " TX_en=%03d; Amp=%03d; || Phase=%03d; Sense=%03d", tx_en, amp,
            phase, sense_adc);

#define ST25R210_ANT_REV_B_AMP_REF 235
#define ST25R210_ANT_REV_B_PHASE_REF 118

  if (amp < ST25R210_ANT_REV_B_AMP_REF / 2) {
    cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_ERROR,
              "NFC antenna amplitude is too low - antenna may be disconnected "
              "or damaged");

    return NFC_ERROR;
  }

  if (((phase - ST25R210_ANT_REV_B_PHASE_REF) <
           -(ST25R210_ANT_REV_B_PHASE_REF * 0.15) ||
       (phase - ST25R210_ANT_REV_B_PHASE_REF) >
           (ST25R210_ANT_REV_B_PHASE_REF * 0.15)) ||
      ((amp - ST25R210_ANT_REV_B_AMP_REF) <
           -(ST25R210_ANT_REV_B_AMP_REF * 0.15) ||
       (amp - ST25R210_ANT_REV_B_AMP_REF) >
           (ST25R210_ANT_REV_B_AMP_REF * 0.15))) {
    cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_ERROR,
              "NFC antenna amplitude or phase is out of range - "
              "antenna may be detuned");
    return NFC_ERROR;
  }

  // TODO: repeate amp and phase checks with GPIO_MOS off

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

  // nfc_print_antenna_info(cli);

  if (NFC_OK != nfc_activate_stm()) {
    cli_error(cli, PRODTEST_ERR_NFC_ACTIVATION, "NFC activation failed");
    goto cleanup;
  }

  nfc_print_antenna_info(cli);

  // uint8_t regs[4] = {0};
  // ret = nfc_read_regs(&regs[0]);
  // cli_trace(
  //     cli, "ret=%d; reg[0]=0x%02X, reg[1]=0x%02X, reg[2]=0x%02X,
  //     reg[3]=0x%02X", ret, regs[0], regs[1], regs[2], regs[3]);

  nfc_event_t nfc_event;
  uint32_t expire_time = ticks_timeout(timeout);
  uint32_t counter = 1;

  while (true) {
    if (timeout_set && ticks_expired(expire_time)) {
      cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    // if (counter == 1000) {
    //   counter = 1;
    //   ret = nfc_read_regs(&regs[0]);
    //   cli_trace(
    //       cli,
    //       "ret=%d; reg[0]=0x%02X, reg[1]=0x%02X, reg[2]=0x%02X,
    //       reg[3]=0x%02X", ret, regs[0], regs[1], regs[2], regs[3]);
    // } else {
    //   counter++;
    // }

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
      counter = 1;

      if (timeout_set) {
        nfc_dev_deactivate();
        cli_trace(cli, "NFC reader mode over");
        break;
      }

      systick_delay_ms(100);
      nfc_dev_deactivate();
    } else if (counter++ % 1500 == 0) {
      nfc_print_antenna_info(cli);
      counter = 1;
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

  uint8_t test_array[10] = {100, 101, 102, 103, 124, 135, 6, 107, 118, 119};

  float median = wirth_median(test_array, 10);
  cli_trace(cli, "median test =  %d.%02d", (int)median,
            (int)(median * 100) % 100);

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

  for (uint8_t init_cnt = 0; init_cnt < 5; init_cnt++) {
    nfc_print_antenna_info(cli);
    systick_delay_ms(200);
  }

  if (NFC_OK != nfc_activate_stm()) {
    cli_error(cli, PRODTEST_ERR_NFC_ACTIVATION, "NFC activation failed");
    goto cleanup;
  }

  // nfc_event_t nfc_event;
  uint32_t expire_time = ticks_timeout(timeout);
  // uint32_t counter = 1;

  while (true) {
    if (timeout_set && ticks_expired(expire_time)) {
      cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    // nfc_status_t nfc_status = nfc_get_event(&nfc_event);

    // if (nfc_status != NFC_OK) {
    //   cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_ERROR, "NFC error");
    //   goto cleanup;
    // }
    nfc_print_antenna_info(cli);

    if (cli_aborted(cli)) {
      goto cleanup;
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
