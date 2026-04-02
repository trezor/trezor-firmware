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
#include <rfal_chip.h>
#include <st25r3916.h>
#include <rtl/cli.h>
#include <sys/systick.h>

static nfc_dev_info_t dev_info = {0};

#define NFC_REG_READ_MAX_LEN 32U

static void prodtest_nfc_read_reg(cli_t* cli) {
  uint32_t reg = 0;
  uint32_t len = 1;
  uint8_t values[NFC_REG_READ_MAX_LEN] = {0};

  if (cli_arg_count(cli) < 1 || cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  if (!cli_arg_uint32(cli, "reg", &reg)) {
    cli_error_arg(cli, "Expecting register address (dec or 0xHEX).");
    return;
  }

  if (cli_has_arg(cli, "len") && !cli_arg_uint32(cli, "len", &len)) {
    cli_error_arg(cli, "Expecting length argument.");
    return;
  }

  if (reg > 0xFFU) {
    cli_error_arg(cli, "Register address must be in range 0x00..0xFF.");
    return;
  }

  if (len == 0U || len > NFC_REG_READ_MAX_LEN || (reg + len - 1U) > 0xFFU) {
    cli_error_arg(cli, "Length must be 1..32 and stay within 0xFF register space.");
    return;
  }

  nfc_status_t ret = nfc_init();
  if (ret != NFC_OK) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC init failed");
    goto cleanup;
  }

  ReturnCode rfal_ret =
      rfalChipReadReg((uint16_t)reg, values, (uint8_t)len);
  if (rfal_ret != RFAL_ERR_NONE) {
    cli_error(cli, CLI_ERROR, "NFC register read failed (%u)",
              (unsigned)rfal_ret);
    goto cleanup;
  }

  cli_ok_hexdata(cli, values, len);

cleanup:
  nfc_deinit();
}

static void prodtest_nfc_read_regs_all(cli_t* cli) {
  t_st25r3916Regs reg_dump = {0};

  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  nfc_status_t ret = nfc_init();
  if (ret != NFC_OK) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC init failed");
    goto cleanup;
  }

  ReturnCode rfal_ret = st25r3916GetRegsDump(&reg_dump);
  if (rfal_ret != RFAL_ERR_NONE) {
    cli_error(cli, CLI_ERROR, "NFC register dump failed (%u)",
              (unsigned)rfal_ret);
    goto cleanup;
  }

  cli_trace(cli, "ST25R3916 registers - Space A");
  for (size_t i = 0; i < sizeof(reg_dump.RsA); i += 8U) {
    cli_trace(cli,
              "A %02X: %02X %02X %02X %02X %02X %02X %02X %02X",
              (unsigned)i, (unsigned)reg_dump.RsA[i + 0U],
              (unsigned)reg_dump.RsA[i + 1U], (unsigned)reg_dump.RsA[i + 2U],
              (unsigned)reg_dump.RsA[i + 3U], (unsigned)reg_dump.RsA[i + 4U],
              (unsigned)reg_dump.RsA[i + 5U], (unsigned)reg_dump.RsA[i + 6U],
              (unsigned)reg_dump.RsA[i + 7U]);
  }

  cli_trace(cli, "ST25R3916 registers - Space B (dump order)");
  for (size_t i = 0; i < sizeof(reg_dump.RsB); i += 8U) {
    size_t rem = sizeof(reg_dump.RsB) - i;
    if (rem >= 8U) {
      cli_trace(cli,
                "B %02X: %02X %02X %02X %02X %02X %02X %02X %02X",
                (unsigned)i, (unsigned)reg_dump.RsB[i + 0U],
                (unsigned)reg_dump.RsB[i + 1U],
                (unsigned)reg_dump.RsB[i + 2U],
                (unsigned)reg_dump.RsB[i + 3U],
                (unsigned)reg_dump.RsB[i + 4U],
                (unsigned)reg_dump.RsB[i + 5U],
                (unsigned)reg_dump.RsB[i + 6U],
                (unsigned)reg_dump.RsB[i + 7U]);
    } else {
      for (size_t j = i; j < sizeof(reg_dump.RsB); j++) {
        cli_trace(cli, "B %02X: %02X", (unsigned)j,
                  (unsigned)reg_dump.RsB[j]);
      }
    }
  }

  cli_ok(cli, "");

cleanup:
  nfc_deinit();
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
    cli_error(cli, CLI_ERROR_FATAL, "NFC init failed");
    goto cleanup;
  } else {
    if (timeout_set) {
      cli_trace(cli, "NFC activated in reader mode for %d ms.", timeout);
    } else {
      cli_trace(cli, "NFC activated in reader mode");
    }
  }

  nfc_register_tech(NFC_POLLER_TECH_A | NFC_POLLER_TECH_B | NFC_POLLER_TECH_F |
                    NFC_POLLER_TECH_V);
  nfc_activate_stm();

  nfc_event_t nfc_event;
  uint32_t expire_time = ticks_timeout(timeout);

  while (true) {
    if (timeout_set && ticks_expired(expire_time)) {
      cli_error(cli, CLI_ERROR_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    nfc_status_t nfc_status = nfc_get_event(&nfc_event);

    if (nfc_status != NFC_OK) {
      cli_error(cli, CLI_ERROR, "NFC error");
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
          cli_error(cli, CLI_ERROR_ABORT, "NFC ERROR Unexpected");
          goto cleanup;
      }

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
    cli_error(cli, CLI_ERROR_FATAL, "NFC init failed");
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
      cli_error(cli, CLI_ERROR, "NFC error");
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
    cli_error(cli, CLI_ERROR_FATAL, "NFC init failed");
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
      cli_error(cli, CLI_ERROR_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    nfc_status_t nfc_status = nfc_get_event(&nfc_event);

    if (nfc_status != NFC_OK) {
      cli_error(cli, CLI_ERROR_FATAL, "NFC error");
      goto cleanup;
    }

    if (nfc_event == NFC_EVENT_ACTIVATED) {
      nfc_dev_read_info(&dev_info);

      if (dev_info.type != NFC_DEV_TYPE_A) {
        cli_error(cli, CLI_ERROR_ABORT, "Only NFC type A cards supported");
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
  .name = "nfc-read-reg",
  .func = prodtest_nfc_read_reg,
  .info = "Read one or more ST25R3916 registers",
  .args = "<reg> [<len>]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-read-regs-all",
  .func = prodtest_nfc_read_regs_all,
  .info = "Read and print all ST25R3916 registers",
  .args = ""
);

#endif  // USE_NFC
