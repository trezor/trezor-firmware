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

#ifdef USE_EXT_FLASH

#include <string.h>

#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <rtl/strutils.h>
#include <sys/ext_flash.h>

#include "prodtest_error_codes.h"

// Maximum number of bytes transferred in a single read command.
#define EXT_FLASH_CMD_READ_MAX 4096

// ============================================================================
// ext-flash-erase  chip | sector <addr> | block <addr>
// ============================================================================

static void prodtest_ext_flash_erase(cli_t* cli) {
  if (cli_arg_count(cli) < 1 || cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  const char* type = cli_nth_arg(cli, 0);

  bool is_chip = strcmp(type, "chip") == 0;
  bool is_sector = strcmp(type, "sector") == 0;
  bool is_block = strcmp(type, "block") == 0;

  if (!is_chip && !is_sector && !is_block) {
    cli_error_arg(cli, "Unknown erase type '%s'. Use: chip, sector, or block.",
                  type);
    return;
  }

  if (is_chip) {
    if (cli_arg_count(cli) != 1) {
      cli_error_arg(cli, "Chip erase takes no address argument.");
      return;
    }
    cli_trace(cli, "Erasing entire chip (%d KB)...",
              (int)(EXT_FLASH_SIZE / 1024));
    if (!ext_flash_erase_chip()) {
      cli_error(cli, PRODTEST_ERR_EXT_FLASH_ERASE_CHIP, "Chip erase failed.");
      return;
    }
  } else {
    if (cli_arg_count(cli) != 2) {
      cli_error_arg(cli, "Address required for sector/block erase.");
      return;
    }
    uint32_t addr = 0;
    if (!cstr_parse_uint32(cli_nth_arg(cli, 1), 0, &addr)) {
      cli_error_arg(cli, "Expecting addr (decimal or 0x-prefixed hex).");
      return;
    }
    if (is_sector) {
      cli_trace(cli, "Erasing %d KB sector at 0x%08X...",
                (int)(EXT_FLASH_SECTOR_SIZE / 1024), (unsigned int)addr);
      if (!ext_flash_erase_sector(addr)) {
        cli_error(cli, PRODTEST_ERR_EXT_FLASH_ERASE_SECTOR,
                  "Sector erase failed at 0x%08X.", (unsigned int)addr);
        return;
      }
    } else {
      cli_trace(cli, "Erasing %d KB block at 0x%08X...",
                (int)(EXT_FLASH_BLOCK_SIZE / 1024), (unsigned int)addr);
      if (!ext_flash_erase_block(addr)) {
        cli_error(cli, PRODTEST_ERR_EXT_FLASH_ERASE_BLOCK,
                  "Block erase failed at 0x%08X.", (unsigned int)addr);
        return;
      }
    }
  }

  cli_ok(cli, "");
}

// ============================================================================
// ext-flash-program  <addr> <hexdata>
//
// Address must be page-aligned (EXT_FLASH_PAGE_SIZE = 256 B).
// The target area must be pre-erased (all 0xFF) before programming.
// Maximum data length per call is one page (256 bytes).
// ============================================================================

static void prodtest_ext_flash_program(cli_t* cli) {
  if (cli_arg_count(cli) != 2) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t addr = 0;
  if (!cli_arg_uint32(cli, "addr", &addr)) {
    cli_error_arg(cli, "Expecting addr (decimal or 0x-prefixed hex).");
    return;
  }

  if (addr % EXT_FLASH_PAGE_SIZE != 0) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_PROGRAM_ADDR,
              "Address 0x%08X is not page-aligned (page = %d B).",
              (unsigned int)addr, (int)EXT_FLASH_PAGE_SIZE);
    return;
  }

  static uint8_t buf[EXT_FLASH_PAGE_SIZE];
  size_t len = 0;
  if (!cli_arg_hex(cli, "hexdata", buf, sizeof(buf), &len)) {
    cli_error_arg(cli, "Failed to decode hex data (max %d bytes).",
                  (int)EXT_FLASH_PAGE_SIZE);
    return;
  }

  if (!ext_flash_write_page(addr, buf, (uint32_t)len)) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_PROGRAM,
              "Write failed at 0x%08X.", (unsigned int)addr);
    return;
  }

  cli_ok(cli, "%d bytes written at 0x%08X.", (int)len, (unsigned int)addr);
}

// ============================================================================
// ext-flash-read  <addr> <len>
//
// Indirect (command-based) read. Maximum length per call is
// EXT_FLASH_CMD_READ_MAX bytes.
// ============================================================================

static void prodtest_ext_flash_read(cli_t* cli) {
  if (cli_arg_count(cli) != 2) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t addr = 0;
  if (!cli_arg_uint32(cli, "addr", &addr)) {
    cli_error_arg(cli, "Expecting addr (decimal or 0x-prefixed hex).");
    return;
  }

  uint32_t len = 0;
  if (!cli_arg_uint32(cli, "len", &len) || len == 0 ||
      len > EXT_FLASH_CMD_READ_MAX) {
    cli_error_arg(cli, "Expecting len in range 1-%d.", EXT_FLASH_CMD_READ_MAX);
    return;
  }

  static uint8_t buf[EXT_FLASH_CMD_READ_MAX];
  if (!ext_flash_read(addr, buf, len)) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_READ,
              "Read failed at 0x%08X.", (unsigned int)addr);
    return;
  }

  size_t offset = 0;
  while (offset < len) {
    size_t row = MIN(16, len - offset);
    char hex[16 * 2 + 1];
    cstr_encode_hex(hex, sizeof(hex), &buf[offset], row);
    cli_trace(cli, "%08X: %s", (unsigned int)(addr + offset), hex);
    offset += row;
  }

  cli_ok_hexdata(cli, buf, len);
}

// ============================================================================
// ext-flash-read-mmap  <addr> <len>
//
// Read via memory-mapped (XIP) mode. The flash is temporarily mapped at
// EXT_FLASH_MMAP_BASE; indirect operations (write/erase) are unavailable
// while mmap is active. Maximum length per call is EXT_FLASH_CMD_READ_MAX.
// ============================================================================

static void prodtest_ext_flash_read_mmap(cli_t* cli) {
  if (cli_arg_count(cli) != 2) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t addr = 0;
  if (!cli_arg_uint32(cli, "addr", &addr)) {
    cli_error_arg(cli, "Expecting addr (decimal or 0x-prefixed hex).");
    return;
  }

  uint32_t len = 0;
  if (!cli_arg_uint32(cli, "len", &len) || len == 0 ||
      len > EXT_FLASH_CMD_READ_MAX) {
    cli_error_arg(cli, "Expecting len in range 1-%d.", EXT_FLASH_CMD_READ_MAX);
    return;
  }

  if (!ext_flash_mmap_enable()) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_MMAP_ENABLE,
              "Failed to enable memory-mapped mode.");
    return;
  }

  static uint8_t buf[EXT_FLASH_CMD_READ_MAX];
  memcpy(buf, (const uint8_t*)(uintptr_t)(EXT_FLASH_MMAP_BASE + addr), len);
  ext_flash_mmap_disable();

  size_t offset = 0;
  while (offset < len) {
    size_t row = MIN(16, len - offset);
    char hex[16 * 2 + 1];
    cstr_encode_hex(hex, sizeof(hex), &buf[offset], row);
    cli_trace(cli, "%08X: %s", (unsigned int)(addr + offset), hex);
    offset += row;
  }

  cli_ok_hexdata(cli, buf, len);
}

// ============================================================================
// ext-flash-test  [addr]
//
// End-to-end NvM self-test.  Exercises every layer of the driver stack in
// eight numbered steps and reports pass/fail for each:
//
//   [1/8] init          — verify JEDEC ID + enable quad mode + set DRV_100
//   [2/8] drive-strength — SR3 R/W: write 50%, restore to 100%
//   [3/8] erase         — 4 KB sector erase
//   [4/8] verify erase  — indirect read of first page, expect all 0xFF
//   [5/8] write         — page-program (256 B incrementing pattern, 0x32 1-1-4)
//   [6/8] read indirect — quad read (0xEB 1-4-4), compare to pattern
//   [7/8] read mmap     — XIP read via EXT_FLASH_MMAP_BASE, compare
//   [8/8] read slow     — single-wire read (0x03 1-1-1), cross-checks write path
//
// Optional <addr> selects the sector to use (aligned down to sector boundary).
// Defaults to the last sector (0x1FF000) to stay clear of demo-rotating
// sectors 1–15.  The sector is left erased on success.
// ============================================================================

#define EXT_FLASH_TEST_ADDR_DEFAULT (EXT_FLASH_SIZE - EXT_FLASH_SECTOR_SIZE)

static void prodtest_ext_flash_test(cli_t* cli) {
  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t test_addr = EXT_FLASH_TEST_ADDR_DEFAULT;
  if (cli_arg_count(cli) == 1) {
    if (!cli_arg_uint32(cli, "addr", &test_addr)) {
      cli_error_arg(cli, "Expecting addr (decimal or 0x-prefixed hex).");
      return;
    }
    test_addr &= ~((uint32_t)EXT_FLASH_SECTOR_SIZE - 1);
  }

  cli_trace(cli, "Test sector: 0x%08X  (%d KB sector, %d B page)",
            (unsigned int)test_addr,
            (int)(EXT_FLASH_SECTOR_SIZE / 1024),
            (int)EXT_FLASH_PAGE_SIZE);

  // [1/8] Init — verifies JEDEC ID (0x1F8601), sets QE bit
  cli_trace(cli, "[1/8] init...");
  if (!ext_flash_init()) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_INIT,
              "[1/8] init: FAIL (JEDEC ID mismatch or SPI error)");
    return;
  }
  cli_trace(cli, "[1/8] init: OK  (JEDEC ID verified, QE enabled)");

  // [2/8] Drive-strength reconfigure — exercises SR3 read-modify-write
  cli_trace(cli, "[2/8] drive-strength reconfigure...");
  if (!ext_flash_set_drive_strength(EXT_FLASH_SR3_DRV_50)) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_DRV_STR_WRITE,
              "[2/8] drive-strength: set 50%% FAIL (SR3 write error)");
    return;
  }
  if (!ext_flash_set_drive_strength(EXT_FLASH_SR3_DRV_100)) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_DRV_STR_RESTORE,
              "[2/8] drive-strength: restore 100%% FAIL (SR3 write error)");
    return;
  }
  cli_trace(cli, "[2/8] drive-strength: OK  (SR3 R/W verified, restored to 100%%)");

  // [3/8] Erase sector
  {
    uint8_t sr1 = 0, sr2 = 0, sr3 = 0;
    ext_flash_read_status(&sr1, &sr2, &sr3);
    cli_trace(cli, "[3/8] erase sector...  (mmap=%d SR1=0x%02X SR2=0x%02X SR3=0x%02X)",
              (int)ext_flash_is_mmap_enabled(), sr1, sr2, sr3);
  }
  if (!ext_flash_erase_sector(test_addr)) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_ERASE,
              "[3/8] erase: FAIL");
    return;
  }
  cli_trace(cli, "[3/8] erase: OK");

  // [4/8] Verify erased — first page must read back as all 0xFF
  cli_trace(cli, "[4/8] verify erase...");
  {
    static uint8_t vbuf[EXT_FLASH_PAGE_SIZE];
    if (!ext_flash_read(test_addr, vbuf, EXT_FLASH_PAGE_SIZE)) {
      cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_VERIFY_ERASE_READ,
                "[4/8] verify erase: read FAIL");
      return;
    }
    for (int i = 0; i < (int)EXT_FLASH_PAGE_SIZE; i++) {
      if (vbuf[i] != 0xFF) {
        cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_VERIFY_ERASE_DATA,
                  "[4/8] verify erase: [%d]=0x%02X expected 0xFF", i, vbuf[i]);
        return;
      }
    }
  }
  cli_trace(cli, "[4/8] verify erase: OK  (%d B all 0xFF)",
            (int)EXT_FLASH_PAGE_SIZE);

  // [5/8] Write page — incrementing pattern (byte[i] = i), cmd 0x32 1-1-4
  cli_trace(cli, "[5/8] write page...");
  static uint8_t wbuf[EXT_FLASH_PAGE_SIZE];
  for (int i = 0; i < (int)EXT_FLASH_PAGE_SIZE; i++) {
    wbuf[i] = (uint8_t)i;
  }
  if (!ext_flash_write_page(test_addr, wbuf, EXT_FLASH_PAGE_SIZE)) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_WRITE,
              "[5/8] write: FAIL");
    return;
  }
  cli_trace(cli, "[5/8] write: OK  (%d B pattern 0x00..0xFF, cmd 0x32 1-1-4)",
            (int)EXT_FLASH_PAGE_SIZE);

  // [6/8] Read indirect — quad read, cmd 0xEB 1-4-4
  cli_trace(cli, "[6/8] read indirect...");
  {
    static uint8_t rbuf[EXT_FLASH_PAGE_SIZE];
    if (!ext_flash_read(test_addr, rbuf, EXT_FLASH_PAGE_SIZE)) {
      cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_READ_INDIRECT,
                "[6/8] read indirect: FAIL");
      return;
    }
    for (int i = 0; i < (int)EXT_FLASH_PAGE_SIZE; i++) {
      if (rbuf[i] != wbuf[i]) {
        cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_READ_INDIRECT_DATA,
                  "[6/8] read indirect: mismatch at [%d] got=0x%02X want=0x%02X",
                  i, rbuf[i], wbuf[i]);
        return;
      }
    }
  }
  cli_trace(cli, "[6/8] read indirect: OK  (cmd 0xEB 1-4-4)");

  // [7/8] Read memory-mapped — XIP via EXT_FLASH_MMAP_BASE
  cli_trace(cli, "[7/8] read mmap...");
  if (!ext_flash_mmap_enable()) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_READ_MMAP,
              "[7/8] read mmap: mmap_enable FAIL");
    return;
  }
  {
    const volatile uint8_t* mptr =
        (const volatile uint8_t*)(uintptr_t)(EXT_FLASH_MMAP_BASE + test_addr);
    int first_bad = -1;
    uint8_t first_got = 0;
    for (int i = 0; i < (int)EXT_FLASH_PAGE_SIZE; i++) {
      if (mptr[i] != wbuf[i] && first_bad < 0) {
        first_bad = i;
        first_got = mptr[i];
      }
    }
    ext_flash_mmap_disable();
    if (first_bad >= 0) {
      cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_READ_MMAP_DATA,
                "[7/8] read mmap: mismatch at [%d] got=0x%02X want=0x%02X",
                first_bad, first_got, wbuf[first_bad]);
      return;
    }
  }
  cli_trace(cli, "[7/8] read mmap: OK  (XIP 0xEB 1-4-4)");

  // [8/8] Read slow — single-wire standard read, cmd 0x03 1-1-1
  // Cross-checks the write path independently of the quad-read path.
  cli_trace(cli, "[8/8] read slow (1-1-1)...");
  {
    static uint8_t sbuf[EXT_FLASH_PAGE_SIZE];
    if (!ext_flash_read_slow_debug(test_addr, sbuf, EXT_FLASH_PAGE_SIZE)) {
      cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_READ_SLOW,
                "[8/8] read slow: FAIL");
      return;
    }
    for (int i = 0; i < (int)EXT_FLASH_PAGE_SIZE; i++) {
      if (sbuf[i] != wbuf[i]) {
        cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_READ_SLOW_DATA,
                  "[8/8] read slow: mismatch at [%d] got=0x%02X want=0x%02X",
                  i, sbuf[i], wbuf[i]);
        return;
      }
    }
  }
  cli_trace(cli, "[8/8] read slow: OK  (cmd 0x03 1-1-1)");

  // Leave the sector erased for the next run
  ext_flash_erase_sector(test_addr);

  cli_ok(cli, "NvM test PASS");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "ext-flash-erase",
  .func = prodtest_ext_flash_erase,
  .info = "Erase external flash: whole chip, 64 KB block, or 4 KB sector",
  .args = "chip | sector <addr> | block <addr>"
);

PRODTEST_CLI_CMD(
  .name = "ext-flash-program",
  .func = prodtest_ext_flash_program,
  .info = "Write one page (≤256 B) to external flash (addr must be page-aligned, area pre-erased)",
  .args = "<addr> <hexdata>"
);

PRODTEST_CLI_CMD(
  .name = "ext-flash-read",
  .func = prodtest_ext_flash_read,
  .info = "Read bytes from external flash via indirect (command) mode",
  .args = "<addr> <len>"
);

PRODTEST_CLI_CMD(
  .name = "ext-flash-read-mmap",
  .func = prodtest_ext_flash_read_mmap,
  .info = "Read bytes from external flash via memory-mapped (XIP) mode",
  .args = "<addr> <len>"
);

PRODTEST_CLI_CMD(
  .name = "ext-flash-test",
  .func = prodtest_ext_flash_test,
  .info = "End-to-end NvM self-test: init, SR3 reconfigure, erase, write, indirect/mmap/slow read",
  .args = "[addr]"
);

// clang-format on

#endif  // USE_EXT_FLASH
