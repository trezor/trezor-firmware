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

#include <cmsis_compiler.h>

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <rtl/strutils.h>
#include <sys/ext_flash.h>

#ifdef USE_EXT_FLASH_OTFDEC
#include <sec/ext_flash_otfdec.h>
#endif

#include "prodtest_error_codes.h"

// Maximum bytes transferred in a single read or program CLI command.
#define EXT_FLASH_CMD_READ_MAX  4096u
#define EXT_FLASH_CMD_WRITE_MAX EXT_FLASH_PAGE_SIZE

// ============================================================================
// ext-flash-erase  chip | sector <addr> | halfblock <addr> | block <addr>
// ============================================================================

static void prodtest_ext_flash_erase(cli_t* cli) {
  if (cli_arg_count(cli) < 1 || cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  const char* type = cli_nth_arg(cli, 0);

  bool is_chip      = strcmp(type, "chip") == 0;
  bool is_sector    = strcmp(type, "sector") == 0;
  bool is_halfblock = strcmp(type, "halfblock") == 0;
  bool is_block     = strcmp(type, "block") == 0;

  if (!is_chip && !is_sector && !is_halfblock && !is_block) {
    cli_error_arg(
        cli, "Unknown erase type '%s'. Use: chip, sector, halfblock, or block.",
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
    if (!ext_flash_erase(0, EXT_FLASH_ERASE_CHIP)) {
      cli_error(cli, PRODTEST_ERR_EXT_FLASH_ERASE_CHIP, "Chip erase failed.");
      return;
    }
  } else {
    if (cli_arg_count(cli) != 2) {
      cli_error_arg(cli, "Address required for sector/halfblock/block erase.");
      return;
    }
    uint32_t addr = 0;
    if (!cstr_parse_uint32(cli_nth_arg(cli, 1), 0, &addr)) {
      cli_error_arg(cli, "Expecting addr (decimal or 0x-prefixed hex).");
      return;
    }
    if (addr >= EXT_FLASH_SIZE) {
      cli_error_arg(cli, "Address 0x%08X is outside flash (%d KB).",
                    (unsigned int)addr, (int)(EXT_FLASH_SIZE / 1024));
      return;
    }

    if (is_sector) {
      cli_trace(cli, "Erasing %d KB sector at 0x%08X...",
                (int)(EXT_FLASH_SECTOR_SIZE / 1024), (unsigned int)addr);
      if (!ext_flash_erase(addr, EXT_FLASH_ERASE_SECTOR)) {
        cli_error(cli, PRODTEST_ERR_EXT_FLASH_ERASE_SECTOR,
                  "Sector erase failed at 0x%08X.", (unsigned int)addr);
        return;
      }
    } else if (is_halfblock) {
      cli_trace(cli, "Erasing %d KB half-block at 0x%08X...",
                (int)(EXT_FLASH_HALFBLOCK_SIZE / 1024), (unsigned int)addr);
      if (!ext_flash_erase(addr, EXT_FLASH_ERASE_HALFBLOCK)) {
        cli_error(cli, PRODTEST_ERR_EXT_FLASH_ERASE_HALFBLOCK,
                  "Half-block erase failed at 0x%08X.", (unsigned int)addr);
        return;
      }
    } else {
      cli_trace(cli, "Erasing %d KB block at 0x%08X...",
                (int)(EXT_FLASH_BLOCK_SIZE / 1024), (unsigned int)addr);
      if (!ext_flash_erase(addr, EXT_FLASH_ERASE_BLOCK)) {
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
// Write up to one page (256 B) to external flash at any byte address.
// ext_flash_write() handles page-boundary splits internally.
// The target area must be pre-erased (all 0xFF).
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

  static uint8_t buf[EXT_FLASH_CMD_WRITE_MAX];
  size_t len = 0;
  if (!cli_arg_hex(cli, "hexdata", buf, sizeof(buf), &len)) {
    cli_error_arg(cli, "Failed to decode hex data (max %d bytes).",
                  (int)EXT_FLASH_CMD_WRITE_MAX);
    return;
  }

  if (addr >= EXT_FLASH_SIZE || (uint32_t)len > EXT_FLASH_SIZE - addr) {
    cli_error_arg(cli, "Range 0x%08X+%d exceeds flash size (%d KB).",
                  (unsigned int)addr, (int)len, (int)(EXT_FLASH_SIZE / 1024));
    return;
  }

  if (!ext_flash_write(addr, buf, (uint32_t)len)) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_PROGRAM,
              "Write failed at 0x%08X.", (unsigned int)addr);
    return;
  }

  cli_ok(cli, "%d bytes written at 0x%08X.", (int)len, (unsigned int)addr);
}

// ============================================================================
// ext-flash-read  <addr> <len>
//
// Read bytes from external flash via memory-mapped (XIP) mode, which is
// always active after init.  Maximum length per call is EXT_FLASH_CMD_READ_MAX.
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

  if (addr >= EXT_FLASH_SIZE || len > EXT_FLASH_SIZE - addr) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_READ,
              "Range 0x%08X+%d exceeds flash size (%d KB).",
              (unsigned int)addr, (int)len, (int)(EXT_FLASH_SIZE / 1024));
    return;
  }

  static uint8_t buf[EXT_FLASH_CMD_READ_MAX];
  memcpy(buf, (const uint8_t*)(uintptr_t)(EXT_FLASH_MMAP_BASE + addr), len);

  size_t offset = 0;
  while (offset < len) {
    size_t row = MIN(16, len - offset);
    char hex[16 * 2 + 1];
    cstr_encode_hex(hex, sizeof(hex), &buf[offset], row);
    cli_trace(cli, "%08X: %s", (unsigned int)(addr + offset), hex);
    offset += row;
  }

  cli_ok(cli, "");
}

// ============================================================================
// ext-flash-read-raw  <addr> <len>
//
// Read bytes from external flash via the indirect SPI path, bypassing the
// memory-mapped (XIP) window entirely.  Because the CPU never reads through
// the OCTOSPI mmap aperture, OTFDEC decryption does NOT apply and the bytes
// returned are the raw ciphertext stored on the chip.
//
// Contrast with ext-flash-read (XIP/mmap, OTFDEC decrypts on-the-fly):
//   ext-flash-read     addr len  →  plaintext  (through OTFDEC)
//   ext-flash-read-raw addr len  →  ciphertext (raw chip bytes)
// ============================================================================

static void prodtest_ext_flash_read_raw(cli_t* cli) {
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

  if (addr >= EXT_FLASH_SIZE || len > EXT_FLASH_SIZE - addr) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_READ,
              "Range 0x%08X+%d exceeds flash size (%d KB).",
              (unsigned int)addr, (int)len, (int)(EXT_FLASH_SIZE / 1024));
    return;
  }

  // ext_flash_read() requires mmap to be off (it issues direct SPI commands).
  // Disable mmap for the duration of the read, then restore it.
  bool was_mmap = ext_flash_is_mmap_enabled();
  if (was_mmap) ext_flash_mmap_disable();

  static uint8_t buf[EXT_FLASH_CMD_READ_MAX];
  bool ok = ext_flash_read(addr, buf, len);

  if (was_mmap) ext_flash_mmap_enable();

  if (!ok) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_READ,
              "Indirect read failed at 0x%08X.", (unsigned int)addr);
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

  cli_ok(cli, "");
}

// ============================================================================
// ext-flash-test  [addr]
//
// Comprehensive production test that verifies:
//  - all OSPI signal lines are connected (CS, CLK, IO0-IO3)
//  - quad-SPI operation at full 100 MHz
//  - data integrity under four stress patterns chosen to catch common defects:
//      p0  0x00         all bits programmed — detects float-high IO lines
//      p1  0x55         01010101 — even-bit coupling
//      p2  0xAA         10101010 — odd-bit coupling (p1+p2 = full bit toggle)
//      p3  walking-1    1<<(i&7) — detects shorted/stuck bit lines
//  - SR3 read-modify-write path (drive strength)
//  - explicit indirect quad read (cmd 0xEB 1-4-4)
//  - single-wire slow read (cmd 0x03 1-1-1), exercising IO0/IO1 only
//
// Seven steps:
//   [1/7] init          — deinit + fresh init: JEDEC ID, QE bit verified
//   [2/7] drive-strength — SR3 R/W via explicit indirect mode
//   [3/7] erase          — 4 KB sector, mmap toggled internally
//   [4/7] verify erase   — mmap read, all 0xFF (OTFDEC inactive)
//   [5/7] write patterns — 4 pages via explicit indirect mode
//   [6/7] verify patterns — mmap read vs. expected patterns (OTFDEC inactive)
//   [7/7] verify indirect — quad + slow read vs. expected patterns
//
// Optional <addr> selects the test sector (snapped to sector boundary).
// Defaults to the last sector to avoid colliding with demo sectors 1–15.
// The sector is left erased on success.
// ============================================================================

#define EXT_FLASH_TEST_ADDR_DEFAULT  (EXT_FLASH_SIZE - EXT_FLASH_SECTOR_SIZE)
#define TEST_PAGES  4u

static void fill_page_pattern(uint8_t* buf, uint32_t page_idx) {
  for (uint32_t i = 0; i < EXT_FLASH_PAGE_SIZE; i++) {
    switch (page_idx) {
      case 0:  buf[i] = 0x00u; break;
      case 1:  buf[i] = 0x55u; break;
      case 2:  buf[i] = 0xAAu; break;
      default: buf[i] = (uint8_t)(1u << (i & 7u)); break;
    }
  }
}

static const char* pattern_name(uint32_t page_idx) {
  switch (page_idx) {
    case 0:  return "0x00 (all-zeros)";
    case 1:  return "0x55 (01010101)";
    case 2:  return "0xAA (10101010)";
    default: return "walking-1";
  }
}

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
    test_addr &= ~((uint32_t)EXT_FLASH_SECTOR_SIZE - 1u);
    if (test_addr >= EXT_FLASH_SIZE) {
      cli_error_arg(cli, "Address 0x%08X is outside flash (%d KB).",
                    (unsigned int)test_addr, (int)(EXT_FLASH_SIZE / 1024));
      return;
    }
  }

  cli_trace(cli, "Test sector 0x%08X  (%d KB sector, %d B pages)",
            (unsigned int)test_addr,
            (int)(EXT_FLASH_SECTOR_SIZE / 1024),
            (int)EXT_FLASH_PAGE_SIZE);

#ifdef USE_EXT_FLASH_OTFDEC
  // Ensure OTFDEC is inactive so mmap reads return raw flash data.
  ext_flash_otfdec_deinit();
#endif

  // [1/7] Fresh init — deinit any prior state, then initialise from scratch.
  cli_trace(cli, "[1/7] init...");
  ext_flash_deinit();
  if (!ext_flash_init()) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_INIT,
              "[1/7] init: FAIL (JEDEC mismatch or OSPI error)");
    return;
  }
  cli_trace(cli, "[1/7] init: OK  (JEDEC 0x1F8601, QE=1, mmap enabled)");

  // [2/7] Drive-strength reconfigure — exercises SR3 R/W.
  //       Indirect register-access commands require mmap to be disabled.
  cli_trace(cli, "[2/7] drive-strength...");
  ext_flash_mmap_disable();
  {
    uint8_t sr1 = 0, sr2 = 0, sr3 = 0;
    ext_flash_read_status(&sr1, &sr2, &sr3);
    cli_trace(cli, "      SR1=0x%02X SR2=0x%02X SR3=0x%02X", sr1, sr2, sr3);
    if (!ext_flash_set_drive_strength(EXT_FLASH_SR3_DRV_50)) {
      ext_flash_mmap_enable();
      cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_DRV_STR_WRITE,
                "[2/7] drive-strength: set 50%% FAIL (SR3 write error)");
      return;
    }
    if (!ext_flash_set_drive_strength(EXT_FLASH_SR3_DRV_75)) {
      ext_flash_mmap_enable();
      cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_DRV_STR_RESTORE,
                "[2/7] drive-strength: restore 75%% FAIL (SR3 write error)");
      return;
    }
  }
  ext_flash_mmap_enable();
  cli_trace(cli, "[2/7] drive-strength: OK  (SR3 R/W verified, restored to 75%%)");

  // [3/7] Erase sector — ext_flash_erase() handles mmap toggle internally.
  cli_trace(cli, "[3/7] erase sector...");
  if (!ext_flash_erase(test_addr, EXT_FLASH_ERASE_SECTOR)) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_ERASE, "[3/7] erase: FAIL");
    return;
  }
  cli_trace(cli, "[3/7] erase: OK");

  // [4/7] Verify erased — mmap read; OTFDEC inactive so raw 0xFF bytes from
  // erased flash are returned.
  cli_trace(cli, "[4/7] verify erase...");
  {
    const volatile uint8_t *mptr =
        (const volatile uint8_t *)(uintptr_t)(EXT_FLASH_MMAP_BASE + test_addr);
    for (uint32_t i = 0; i < EXT_FLASH_PAGE_SIZE; i++) {
      uint8_t val = mptr[i];
      if (val != 0xFFu) {
        cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_VERIFY_ERASE_DATA,
                  "[4/7] verify erase: [%u]=0x%02X expected 0xFF",
                  (unsigned int)i, val);
        return;
      }
    }
  }
  cli_trace(cli, "[4/7] verify erase: OK  (%d B all 0xFF)",
            (int)EXT_FLASH_PAGE_SIZE);

  // [5/7] Write 4 stress patterns — single mmap_disable/enable bracket
  //       around all page-program commands for efficiency.
  cli_trace(cli, "[5/7] write patterns (%u pages)...", (unsigned int)TEST_PAGES);
  {
    static uint8_t wbuf[EXT_FLASH_PAGE_SIZE];
    ext_flash_mmap_disable();
    for (uint32_t p = 0; p < TEST_PAGES; p++) {
      fill_page_pattern(wbuf, p);
      uint32_t paddr = test_addr + p * EXT_FLASH_PAGE_SIZE;
      if (!ext_flash_write_page(paddr, wbuf, EXT_FLASH_PAGE_SIZE)) {
        ext_flash_mmap_enable();
        cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_WRITE,
                  "[5/7] write: page %u (%s) FAIL at 0x%08X",
                  (unsigned int)p, pattern_name(p), (unsigned int)paddr);
        return;
      }
      cli_trace(cli, "      page %u: %s -> 0x%08X",
                (unsigned int)p, pattern_name(p), (unsigned int)paddr);
    }
    ext_flash_mmap_enable();
  }
  cli_trace(cli, "[5/7] write patterns: OK");

  // [6/7] Verify patterns via mmap read; OTFDEC inactive so raw programmed
  // bytes are compared directly via the XIP window.
  cli_trace(cli, "[6/7] verify patterns (mmap)...");
  {
    static uint8_t expected[EXT_FLASH_PAGE_SIZE];
    for (uint32_t p = 0; p < TEST_PAGES; p++) {
      uint32_t paddr = test_addr + p * EXT_FLASH_PAGE_SIZE;
      const volatile uint8_t *mptr =
          (const volatile uint8_t *)(uintptr_t)(EXT_FLASH_MMAP_BASE + paddr);
      fill_page_pattern(expected, p);
      for (uint32_t i = 0; i < EXT_FLASH_PAGE_SIZE; i++) {
        uint8_t val = mptr[i];
        if (val != expected[i]) {
          cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_PATTERN_MMAP_DATA,
                    "[6/7] verify: page %u (%s) [%u] got=0x%02X want=0x%02X",
                    (unsigned int)p, pattern_name(p),
                    (unsigned int)i, val, expected[i]);
          return;
        }
      }
      cli_trace(cli, "      page %u (%s): OK", (unsigned int)p, pattern_name(p));
    }
  }
  cli_trace(cli, "[6/7] verify patterns: OK  (mmap XIP read)");

  // [7/7] Verify via indirect quad read (cmd 0xEB 1-4-4) of all pages,
  //       then via single-wire slow read (cmd 0x03 1-1-1) of page 0.
  //       Page 0 pattern is 0x00 — simple and unambiguous for slow read.
  cli_trace(cli, "[7/7] verify indirect...");
  {
    static uint8_t rbuf[EXT_FLASH_PAGE_SIZE];
    static uint8_t expected[EXT_FLASH_PAGE_SIZE];
    ext_flash_mmap_disable();

    for (uint32_t p = 0; p < TEST_PAGES; p++) {
      uint32_t paddr = test_addr + p * EXT_FLASH_PAGE_SIZE;
      if (!ext_flash_read(paddr, rbuf, EXT_FLASH_PAGE_SIZE)) {
        ext_flash_mmap_enable();
        cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_PATTERN_INDIRECT,
                  "[7/7] indirect read: page %u FAIL", (unsigned int)p);
        return;
      }
      fill_page_pattern(expected, p);
      for (uint32_t i = 0; i < EXT_FLASH_PAGE_SIZE; i++) {
        if (rbuf[i] != expected[i]) {
          ext_flash_mmap_enable();
          cli_error(cli, PRODTEST_ERR_EXT_FLASH_TEST_PATTERN_INDIRECT_DATA,
                    "[7/7] indirect: page %u (%s) [%u] got=0x%02X want=0x%02X",
                    (unsigned int)p, pattern_name(p),
                    (unsigned int)i, rbuf[i], expected[i]);
          return;
        }
      }
    }
    cli_trace(cli, "      quad indirect (cmd 0xEB 1-4-4): all %u pages OK",
              (unsigned int)TEST_PAGES);

    ext_flash_mmap_enable();
  }
  cli_trace(cli, "[7/7] verify indirect: OK");

  // Leave the sector erased for the next run.
  ext_flash_erase(test_addr, EXT_FLASH_ERASE_SECTOR);

  cli_ok(cli, "NvM test PASS");
}

// ============================================================================
// ext-flash-otfdec-load  <addr> <hexdata>
//
// Initialises OTFDEC1 (zero nonce, version 0), encrypts <hexdata> for storage
// at ext-flash offset <addr> using OTFDEC1 cipher mode, programs the resulting
// ciphertext into external flash, and leaves OTFDEC1 active.
//
// Requirements:
//   - Target area must be pre-erased (use ext-flash-erase first).
//   - addr must be 16-byte aligned; hex data length must be a multiple of 16.
//
// After this command OTFDEC remains active: ext-flash-read returns plaintext
// via the XIP window.  Use ext-flash-otfdec-exec to execute the loaded code
// (it reinits OTFDEC then deinits after the call).  Run ext-flash-test to
// automatically deactivate OTFDEC and verify raw flash state.
// ============================================================================

#ifdef USE_EXT_FLASH_OTFDEC

// ---------------------------------------------------------------------------
// Callback context for the XIP demo function.
//
// ext-flash-otfdec-exec fills this in SRAM before branching into external
// flash.  The XIP function (loaded by ext-flash-otfdec-load) receives a
// pointer to it in R0 and uses it to call back into internal flash, then
// writes its result to the 'result' field.
//
// Struct layout (must match xip_demo_fn.S):
//   +0   magic    — 0xD0C0DE00, sanity-checks SRAM is reachable
//   +4   compute  — fn ptr into internal flash; called as compute(input)
//   +8   result   — written by XIP code, read after return
//   +12  input    — argument passed to compute()
// ---------------------------------------------------------------------------

typedef uint32_t (*xip_compute_fn_t)(uint32_t);

typedef struct {
  uint32_t          magic;
  xip_compute_fn_t  compute;
  volatile uint32_t result;
  uint32_t          input;
} xip_ctx_t;

// Iterative Fibonacci in internal flash.  Called by the XIP demo function via
// a function pointer stored in xip_ctx_t.  noinline keeps a callable symbol.
static uint32_t __attribute__((noinline)) xip_demo_compute(uint32_t x) {
  x &= 0x1Fu;
  if (x <= 1u) return x;
  uint32_t a = 0, b = 1;
  for (uint32_t i = 2u; i <= x; i++) {
    uint32_t c = a + b;
    a = b;
    b = c;
  }
  return b;
}

static xip_ctx_t g_xip_ctx;

static void prodtest_ext_flash_otfdec_load(cli_t* cli) {
  if (cli_arg_count(cli) != 2) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t addr = 0;
  if (!cli_arg_uint32(cli, "addr", &addr)) {
    cli_error_arg(cli, "Expecting addr (decimal or 0x-prefixed hex).");
    return;
  }

  if (addr & 15u) {
    cli_error_arg(cli, "addr must be 16-byte aligned (got 0x%08X).",
                  (unsigned int)addr);
    return;
  }

  static uint8_t plaintext[EXT_FLASH_CMD_WRITE_MAX];
  static uint8_t ciphertext[EXT_FLASH_CMD_WRITE_MAX];
  size_t len = 0;
  if (!cli_arg_hex(cli, "hexdata", plaintext, sizeof(plaintext), &len)) {
    cli_error_arg(cli, "Failed to decode hex data (max %d bytes).",
                  (int)EXT_FLASH_CMD_WRITE_MAX);
    return;
  }

  if (len & 15u) {
    cli_error_arg(cli, "Data length must be a multiple of 16 bytes (got %d).",
                  (int)len);
    return;
  }

  if (addr >= EXT_FLASH_SIZE || (uint32_t)len > EXT_FLASH_SIZE - addr) {
    cli_error_arg(cli, "Range 0x%08X+%d exceeds flash size (%d KB).",
                  (unsigned int)addr, (int)len, (int)(EXT_FLASH_SIZE / 1024));
    return;
  }

  uint32_t nonce[2] = {0, 0};
  if (sectrue != ext_flash_otfdec_init(nonce, 0)) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_PROGRAM, "OTFDEC init failed.");
    return;
  }

  cli_trace(cli, "Encrypting %d bytes for flash offset 0x%08X...",
            (int)len, (unsigned int)addr);

  if (!ext_flash_otfdec_cipher(addr, plaintext, (uint32_t)len, ciphertext)) {
    ext_flash_otfdec_deinit();
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_PROGRAM, "OTFDEC cipher failed.");
    return;
  }

  cli_trace(cli, "Programming ciphertext to flash at 0x%08X...",
            (unsigned int)addr);
  if (!ext_flash_write(addr, ciphertext, (uint32_t)len)) {
    ext_flash_otfdec_deinit();
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_PROGRAM,
              "Flash write failed at 0x%08X.", (unsigned int)addr);
    return;
  }

  // Leave OTFDEC active so subsequent ext-flash-read returns plaintext via XIP.
  cli_ok(cli, "%d bytes encrypted and programmed at 0x%08X.",
         (int)len, (unsigned int)addr);
}

// ============================================================================
// ext-flash-otfdec-exec  <addr>
//
// Calls the Thumb-2 function located at EXT_FLASH_MMAP_BASE + addr.
// OTFDEC1 decrypts the fetched instructions on-the-fly so the CPU executes
// the original plaintext code.  The function must have prototype void(*)(void).
// ============================================================================

static void prodtest_ext_flash_otfdec_exec(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t addr = 0;
  if (!cli_arg_uint32(cli, "addr", &addr)) {
    cli_error_arg(cli, "Expecting addr (decimal or 0x-prefixed hex).");
    return;
  }

  if (addr >= EXT_FLASH_SIZE) {
    cli_error_arg(cli, "Address 0x%08X is outside flash (%d KB).",
                  (unsigned int)addr, (int)(EXT_FLASH_SIZE / 1024));
    return;
  }

  // Deinit any existing OTFDEC state (idempotent), then reinit with zero
  // nonce so the key and region are freshly loaded before XIP execution.
  ext_flash_otfdec_deinit();
  uint32_t nonce[2] = {0, 0};
  if (sectrue != ext_flash_otfdec_init(nonce, 0)) {
    cli_error(cli, PRODTEST_ERR_EXT_FLASH_PROGRAM, "OTFDEC init failed.");
    return;
  }

  // Fill in the callback context in SRAM before branching into external flash.
  // The XIP function receives &g_xip_ctx in R0 and calls g_xip_ctx.compute()
  // from internal flash, writing the return value to g_xip_ctx.result.
  g_xip_ctx.magic   = 0xD0C0DE00u;
  g_xip_ctx.compute = xip_demo_compute;
  g_xip_ctx.result  = 0;
  g_xip_ctx.input   = 20;  // fib(20) = 6765

  cli_trace(cli, "Jumping to OTFDEC-decrypted code at 0x%08X (mmap+0x%08X)...",
            (unsigned int)(EXT_FLASH_MMAP_BASE + addr), (unsigned int)addr);

  // Flush I-cache so the CPU fetches the freshly written ciphertext from flash
  // (decrypted on-the-fly by OTFDEC) rather than any stale cached line.
  HAL_ICACHE_Invalidate();
  __DSB();
  __ISB();

  // Bit 0 set: Thumb-2 branch target (required on ARMv8-M).
  // The XIP function receives &g_xip_ctx in R0 and calls back into the
  // internal-flash xip_demo_compute() via the function pointer in the struct.
  typedef void (*fn_t)(xip_ctx_t *);
  fn_t fn = (fn_t)((uintptr_t)(EXT_FLASH_MMAP_BASE + addr) | 1u);
  fn(&g_xip_ctx);

  ext_flash_otfdec_deinit();
  cli_trace(cli, "XIP returned; fib(%u) = %u (0x%08X)",
            (unsigned int)g_xip_ctx.input,
            (unsigned int)g_xip_ctx.result,
            (unsigned int)g_xip_ctx.result);
  cli_ok(cli, "Returned from 0x%08X.", (unsigned int)(EXT_FLASH_MMAP_BASE + addr));
}

#endif  // USE_EXT_FLASH_OTFDEC

// clang-format off

PRODTEST_CLI_CMD(
  .name = "ext-flash-erase",
  .func = prodtest_ext_flash_erase,
  .info = "Erase external flash: chip, 64 KB block, 32 KB half-block, or 4 KB sector",
  .args = "chip | sector <addr> | block <addr>"
);

PRODTEST_CLI_CMD(
  .name = "ext-flash-program",
  .func = prodtest_ext_flash_program,
  .info = "Write up to 256 B to external flash (any byte address, area pre-erased)",
  .args = "<addr> <hexdata>"
);

PRODTEST_CLI_CMD(
  .name = "ext-flash-read",
  .func = prodtest_ext_flash_read,
  .info = "Read bytes from external flash via memory-mapped (XIP) mode",
  .args = "<addr> <len>"
);

PRODTEST_CLI_CMD(
  .name = "ext-flash-read-raw",
  .func = prodtest_ext_flash_read_raw,
  .info = "Read raw ciphertext from ext flash via indirect SPI (bypasses OTFDEC/XIP)",
  .args = "<addr> <len>"
);

PRODTEST_CLI_CMD(
  .name = "ext-flash-test",
  .func = prodtest_ext_flash_test,
  .info = "Production NvM test: pin connectivity, 100 MHz quad-SPI, stress patterns, SR3 R/W",
  .args = "[addr]"
);

#ifdef USE_EXT_FLASH_OTFDEC

PRODTEST_CLI_CMD(
  .name = "ext-flash-otfdec-load",
  .func = prodtest_ext_flash_otfdec_load,
  .info = "Init OTFDEC, encrypt data via OTFDEC1 cipher and program to ext flash (area pre-erased); OTFDEC stays active",
  .args = "<addr> <hexdata>"
);

PRODTEST_CLI_CMD(
  .name = "ext-flash-otfdec-exec",
  .func = prodtest_ext_flash_otfdec_exec,
  .info = "Init OTFDEC, call Thumb-2 code at EXT_FLASH_MMAP_BASE+addr (R0=callback ctx with fn ptr into internal flash), report result, deinit",
  .args = "<addr>"
);

#endif  // USE_EXT_FLASH_OTFDEC

// clang-format on

#endif  // USE_EXT_FLASH
