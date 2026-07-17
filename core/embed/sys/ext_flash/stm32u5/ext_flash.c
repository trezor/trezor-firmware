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

// External NvM driver for AT25SF161B (16 Mbit, 2 MB NOR flash) connected via
// OCTOSPI1 in Quad-SPI mode on STM32U5.
//
// The driver operates in polling mode (no DMA, no interrupts).  It supports:
//   - Read         Fast Read Quad I/O  cmd 0xEB  1-4-4  mode byte + 4 dummy
//   - Page program Quad Page Program   cmd 0x32  1-1-4
//   - Sector erase 4 KB               cmd 0x20  (no quad variant in AT25SF161B)
//   - Block erase  64 KB              cmd 0xD8
//   - Chip erase                      cmd 0xC7
//   - Memory-mapped (XIP) read-only mode via HAL_OSPI_MemoryMapped
//
// On init the driver verifies QE=1 in SR2 (factory default for AT25SF161B) so
// that IO2/IO3 are active for quad transfers.

#ifdef KERNEL_MODE

#include <string.h>

#include <sys/ext_flash.h>
#include <sys/logging.h>
#include <sys/mpu.h>
#include <trezor_bsp.h>
#include <trezor_rtl.h>

LOG_DECLARE(ext_flash);

// ---------------------------------------------------------------------------
// AT25SF161B command set
// ---------------------------------------------------------------------------

#define CMD_WRITE_ENABLE      0x06
#define CMD_WRITE_DISABLE     0x04
#define CMD_READ_SR1          0x05
#define CMD_READ_SR2          0x35
#define CMD_WRITE_SR2         0x31  // writes Status Register 2 (1 byte)
#define CMD_READ_SR3          0x15
#define CMD_WRITE_SR3         0x11  // writes Status Register 3 (1 byte)
#define CMD_READ_JEDEC_ID     0x9F
#define CMD_READ              0x03  // 1-1-1: standard slow read, no dummy cycles
#define CMD_FAST_READ_QUAD_IO 0xEB  // 1-4-4: addr+mode+data on 4 lines, 4 dummy cycles
#define CMD_QUAD_PAGE_PROGRAM 0x32  // 1-1-4: addr on 1 line, data on 4 lines
#define CMD_SECTOR_ERASE_4K   0x20
#define CMD_BLOCK_ERASE_64K   0xD8
#define CMD_CHIP_ERASE        0xC7

// AT25SF161B JEDEC ID
#define JEDEC_MANUFACTURER_ID 0x1Fu
#define JEDEC_DEVICE_TYPE     0x86u
#define JEDEC_CAPACITY        0x01u

// Status register bits
#define SR1_BUSY      0x01u
#define SR1_WEL       0x02u
#define SR2_QE        0x02u  // Quad Enable — factory default 1 on AT25SF161B

// SR3 DRV[1:0] mask — bits 6:5.  Values are EXT_FLASH_SR3_DRV_* from ext_flash.h.
#define SR3_DRV_MASK  0x60u

// ---------------------------------------------------------------------------
// OSPI configuration
// ---------------------------------------------------------------------------

// DeviceSize = log2(flash_bytes) - 1 = log2(2 097 152) = 21
// The HAL decrements the value by 1, so we pass 21 to HAL_OSPI_Init.
#define OSPI_DEVICE_SIZE_BITS 21

// Prescaler: OSPI_CLK = kernel_clk / (prescaler + 1).
// Kernel clock source: PLL2Q = 100 MHz, switched to OCTOSPISEL in startup_init.c
// when the board header defines USE_PLL2_FOR_OSPI (PLL2: VCO=200 MHz, DIVQ=2).
// 100 MHz / (99 + 1) = 1 MHz — safe for initial bring-up without signal-integrity
// validation. Raise to prescaler=0 (100 MHz) once series resistors are fitted and
// waveforms are verified with a logic analyser.
#define OSPI_CLK_PRESCALER 0

// CS must stay high at least 20 ns (tCSH, DS Table 13.4).
// At 100 MHz: 1 cycle = 10 ns.  3 cycles = 30 ns gives a safe 10 ns margin
// above the minimum; 2 cycles would be right at the limit.
#define OSPI_CS_HIGH_CYCLES 3

// Dummy cycles for CMD_FAST_READ_QUAD_IO (0xEB) after the 8-bit mode byte.
// AT25SF161B DS section 7.5: 4 dummy cycles at up to 108 MHz in SDR quad mode.
// NOTE: re-verify this against the DS section 7.5 waveform on the production PCB
// at the final clock frequency and trace lengths — add cycles if read errors appear.
#define OSPI_READ_DUMMY_CYCLES 4

// Per-operation HAL timeouts (milliseconds). DS Table 13.5 worst-case values:
//   Page program (256 B): 1.8 ms  → 10 ms
//   Sector erase  (4 kB): 220 ms  → 500 ms
//   Block erase  (64 kB): 700 ms  → 2000 ms
//   Chip erase:           11 s    → 15000 ms
#define TIMEOUT_CMD_MS          HAL_OSPI_TIMEOUT_DEFAULT_VALUE  // 5 s
#define TIMEOUT_PAGE_PROGRAM_MS 10
#define TIMEOUT_SECTOR_ERASE_MS 500
#define TIMEOUT_BLOCK_ERASE_MS  2000
#define TIMEOUT_CHIP_ERASE_MS   15000

// ---------------------------------------------------------------------------
// Driver state
// ---------------------------------------------------------------------------

typedef struct {
  OSPI_HandleTypeDef hospi;
  bool initialized;
  bool mmap_enabled;
  mpu_mode_t mmap_prev_mode;
} ext_flash_driver_t;

static ext_flash_driver_t g_drv;

// ---------------------------------------------------------------------------
// GPIO helpers
// ---------------------------------------------------------------------------

static void gpio_init(void) {
  GPIO_InitTypeDef gpio = {0};
  gpio.Mode  = GPIO_MODE_AF_PP;
  gpio.Pull  = GPIO_NOPULL;
  // VERY_HIGH is required for 100 MHz OSPI operation on STM32U5.
  // WARNING: ensure 22-33 Ω series resistors are fitted on CLK and IO0-IO3
  // and validate signal integrity with a logic analyser before use.
  gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;

  EXT_FLASH_CLK_CLK_EN();
  gpio.Alternate = EXT_FLASH_CLK_AF;
  gpio.Pin = EXT_FLASH_CLK_PIN;
  HAL_GPIO_Init(EXT_FLASH_CLK_PORT, &gpio);

  EXT_FLASH_NCS_CLK_EN();
  gpio.Alternate = EXT_FLASH_NCS_AF;
  gpio.Pin = EXT_FLASH_NCS_PIN;
  HAL_GPIO_Init(EXT_FLASH_NCS_PORT, &gpio);

  EXT_FLASH_IO0_CLK_EN();
  gpio.Alternate = EXT_FLASH_IO0_AF;
  gpio.Pin = EXT_FLASH_IO0_PIN;
  HAL_GPIO_Init(EXT_FLASH_IO0_PORT, &gpio);

  EXT_FLASH_IO1_CLK_EN();
  gpio.Alternate = EXT_FLASH_IO1_AF;
  gpio.Pin = EXT_FLASH_IO1_PIN;
  HAL_GPIO_Init(EXT_FLASH_IO1_PORT, &gpio);

  EXT_FLASH_IO2_CLK_EN();
  gpio.Alternate = EXT_FLASH_IO2_AF;
  gpio.Pin = EXT_FLASH_IO2_PIN;
  HAL_GPIO_Init(EXT_FLASH_IO2_PORT, &gpio);

  EXT_FLASH_IO3_CLK_EN();
  gpio.Alternate = EXT_FLASH_IO3_AF;
  gpio.Pin = EXT_FLASH_IO3_PIN;
  HAL_GPIO_Init(EXT_FLASH_IO3_PORT, &gpio);
}

static void gpio_deinit(void) {
  HAL_GPIO_DeInit(EXT_FLASH_CLK_PORT, EXT_FLASH_CLK_PIN);
  HAL_GPIO_DeInit(EXT_FLASH_NCS_PORT, EXT_FLASH_NCS_PIN);
  HAL_GPIO_DeInit(EXT_FLASH_IO0_PORT, EXT_FLASH_IO0_PIN);
  HAL_GPIO_DeInit(EXT_FLASH_IO1_PORT, EXT_FLASH_IO1_PIN);
  HAL_GPIO_DeInit(EXT_FLASH_IO2_PORT, EXT_FLASH_IO2_PIN);
  HAL_GPIO_DeInit(EXT_FLASH_IO3_PORT, EXT_FLASH_IO3_PIN);
}

// ---------------------------------------------------------------------------
// OSPI + OCTOSPIM initialisation
// ---------------------------------------------------------------------------

static bool ospi_init(ext_flash_driver_t *drv) {
  OSPI_HandleTypeDef *h = &drv->hospi;

  EXT_FLASH_OSPI_CLK_ENABLE();

  h->Instance                 = EXT_FLASH_OSPI_INSTANCE;
  h->Init.FifoThreshold       = 1;
  h->Init.DualQuad            = HAL_OSPI_DUALQUAD_DISABLE;
  h->Init.MemoryType          = HAL_OSPI_MEMTYPE_MICRON;
  h->Init.DeviceSize          = OSPI_DEVICE_SIZE_BITS;
  h->Init.ChipSelectHighTime  = OSPI_CS_HIGH_CYCLES;
  h->Init.FreeRunningClock    = HAL_OSPI_FREERUNCLK_DISABLE;
  h->Init.ClockMode           = HAL_OSPI_CLOCK_MODE_0;
  h->Init.WrapSize            = HAL_OSPI_WRAP_NOT_SUPPORTED;
  h->Init.ClockPrescaler      = OSPI_CLK_PRESCALER;
  // AT25SF161B samples on rising CLK edge (SPI Mode 0). HALFCYCLE would move
  // the latch to the falling edge — which is after CS deasserts for short
  // transactions and causes all-zero reads. Keep NONE.
  h->Init.SampleShifting      = HAL_OSPI_SAMPLE_SHIFTING_NONE;
  h->Init.DelayHoldQuarterCycle = HAL_OSPI_DHQC_DISABLE;
  h->Init.ChipSelectBoundary  = 0;
  h->Init.DelayBlockBypass    = HAL_OSPI_DELAY_BLOCK_BYPASSED;
  h->Init.MaxTran             = 0;
  h->Init.Refresh             = 0;

  return HAL_OSPI_Init(h) == HAL_OK;
}

static bool ospim_config(ext_flash_driver_t *drv) {
  OSPIM_CfgTypeDef cfg = {0};

  cfg.ClkPort    = 1;
  cfg.NCSPort    = 1;
  cfg.IOLowPort  = HAL_OSPIM_IOPORT_1_LOW;
  cfg.IOHighPort = HAL_OSPIM_IOPORT_NONE;
  cfg.DQSPort    = 0;
  cfg.Req2AckTime = 1;

  return HAL_OSPIM_Config(&drv->hospi, &cfg, TIMEOUT_CMD_MS) == HAL_OK;
}

// ---------------------------------------------------------------------------
// Low-level command helpers
// ---------------------------------------------------------------------------

static bool cmd_no_data(ext_flash_driver_t *drv, uint8_t cmd) {
  OSPI_RegularCmdTypeDef c = {0};
  c.OperationType     = HAL_OSPI_OPTYPE_COMMON_CFG;
  c.FlashId           = HAL_OSPI_FLASH_ID_1;
  c.Instruction       = cmd;
  c.InstructionMode   = HAL_OSPI_INSTRUCTION_1_LINE;
  c.InstructionSize   = HAL_OSPI_INSTRUCTION_8_BITS;
  c.InstructionDtrMode = HAL_OSPI_INSTRUCTION_DTR_DISABLE;
  c.AddressMode       = HAL_OSPI_ADDRESS_NONE;
  c.AlternateBytesMode = HAL_OSPI_ALTERNATE_BYTES_NONE;
  c.DataMode          = HAL_OSPI_DATA_NONE;
  c.DummyCycles       = 0;
  c.DQSMode           = HAL_OSPI_DQS_DISABLE;
  c.SIOOMode          = HAL_OSPI_SIOO_INST_EVERY_CMD;
  return HAL_OSPI_Command(&drv->hospi, &c, TIMEOUT_CMD_MS) == HAL_OK;
}

static bool cmd_read_1line(ext_flash_driver_t *drv, uint8_t cmd, uint8_t *buf,
                            uint32_t len) {
  OSPI_RegularCmdTypeDef c = {0};
  c.OperationType     = HAL_OSPI_OPTYPE_COMMON_CFG;
  c.FlashId           = HAL_OSPI_FLASH_ID_1;
  c.Instruction       = cmd;
  c.InstructionMode   = HAL_OSPI_INSTRUCTION_1_LINE;
  c.InstructionSize   = HAL_OSPI_INSTRUCTION_8_BITS;
  c.InstructionDtrMode = HAL_OSPI_INSTRUCTION_DTR_DISABLE;
  c.AddressMode       = HAL_OSPI_ADDRESS_NONE;
  c.AlternateBytesMode = HAL_OSPI_ALTERNATE_BYTES_NONE;
  c.DataMode          = HAL_OSPI_DATA_1_LINE;
  c.NbData            = len;
  c.DataDtrMode       = HAL_OSPI_DATA_DTR_DISABLE;
  c.DummyCycles       = 0;
  c.DQSMode           = HAL_OSPI_DQS_DISABLE;
  c.SIOOMode          = HAL_OSPI_SIOO_INST_EVERY_CMD;

  if (HAL_OSPI_Command(&drv->hospi, &c, TIMEOUT_CMD_MS) != HAL_OK) {
    return false;
  }
  return HAL_OSPI_Receive(&drv->hospi, buf, TIMEOUT_CMD_MS) == HAL_OK;
}

static bool cmd_write_sr_byte(ext_flash_driver_t *drv, uint8_t cmd, uint8_t val) {
  OSPI_RegularCmdTypeDef c = {0};
  c.OperationType     = HAL_OSPI_OPTYPE_COMMON_CFG;
  c.FlashId           = HAL_OSPI_FLASH_ID_1;
  c.Instruction       = cmd;
  c.InstructionMode   = HAL_OSPI_INSTRUCTION_1_LINE;
  c.InstructionSize   = HAL_OSPI_INSTRUCTION_8_BITS;
  c.InstructionDtrMode = HAL_OSPI_INSTRUCTION_DTR_DISABLE;
  c.AddressMode       = HAL_OSPI_ADDRESS_NONE;
  c.AlternateBytesMode = HAL_OSPI_ALTERNATE_BYTES_NONE;
  c.DataMode          = HAL_OSPI_DATA_1_LINE;
  c.NbData            = 1;
  c.DataDtrMode       = HAL_OSPI_DATA_DTR_DISABLE;
  c.DummyCycles       = 0;
  c.DQSMode           = HAL_OSPI_DQS_DISABLE;
  c.SIOOMode          = HAL_OSPI_SIOO_INST_EVERY_CMD;

  if (HAL_OSPI_Command(&drv->hospi, &c, TIMEOUT_CMD_MS) != HAL_OK) {
    return false;
  }
  return HAL_OSPI_Transmit(&drv->hospi, &val, TIMEOUT_CMD_MS) == HAL_OK;
}

static bool cmd_with_addr(ext_flash_driver_t *drv, uint8_t cmd, uint32_t addr) {
  OSPI_RegularCmdTypeDef c = {0};
  c.OperationType     = HAL_OSPI_OPTYPE_COMMON_CFG;
  c.FlashId           = HAL_OSPI_FLASH_ID_1;
  c.Instruction       = cmd;
  c.InstructionMode   = HAL_OSPI_INSTRUCTION_1_LINE;
  c.InstructionSize   = HAL_OSPI_INSTRUCTION_8_BITS;
  c.InstructionDtrMode = HAL_OSPI_INSTRUCTION_DTR_DISABLE;
  c.Address           = addr;
  c.AddressMode       = HAL_OSPI_ADDRESS_1_LINE;
  c.AddressSize       = HAL_OSPI_ADDRESS_24_BITS;
  c.AddressDtrMode    = HAL_OSPI_ADDRESS_DTR_DISABLE;
  c.AlternateBytesMode = HAL_OSPI_ALTERNATE_BYTES_NONE;
  c.DataMode          = HAL_OSPI_DATA_NONE;
  c.DummyCycles       = 0;
  c.DQSMode           = HAL_OSPI_DQS_DISABLE;
  c.SIOOMode          = HAL_OSPI_SIOO_INST_EVERY_CMD;
  return HAL_OSPI_Command(&drv->hospi, &c, TIMEOUT_CMD_MS) == HAL_OK;
}

static bool wait_not_busy(ext_flash_driver_t *drv, uint32_t timeout_ms) {
  uint32_t deadline = HAL_GetTick() + timeout_ms;
  uint8_t sr1 = 0xFF;

  do {
    if (!cmd_read_1line(drv, CMD_READ_SR1, &sr1, 1)) {
      LOG_ERR("wait_not_busy: SR1 read failed (hospi err=0x%08lx)",
              (unsigned long)drv->hospi.ErrorCode);
      return false;
    }
    if (!(sr1 & SR1_BUSY)) {
      return true;
    }
  } while ((int32_t)(HAL_GetTick() - deadline) < 0);

  LOG_ERR("wait_not_busy: timed out after %ums, last SR1=0x%02X",
          (unsigned)timeout_ms, sr1);
  return false;
}

static bool write_enable(ext_flash_driver_t *drv) {
  if (!cmd_no_data(drv, CMD_WRITE_ENABLE)) {
    LOG_ERR("write_enable: WREN command failed");
    return false;
  }

  uint8_t sr1 = 0;
  if (!cmd_read_1line(drv, CMD_READ_SR1, &sr1, 1)) {
    LOG_ERR("write_enable: SR1 read failed");
    return false;
  }

  if (!(sr1 & SR1_WEL)) {
    LOG_ERR("write_enable: WEL not set after WREN (SR1=0x%02X)", sr1);
    return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// JEDEC ID check and Quad Enable setup
// ---------------------------------------------------------------------------

static void log_jedec_id(ext_flash_driver_t *drv) {
  uint8_t id[3] = {0};
  if (!cmd_read_1line(drv, CMD_READ_JEDEC_ID, id, 3)) {
    LOG_ERR("jedec_id: read failed");
    return;
  }
  LOG_INF("jedec_id: 0x%02X 0x%02X 0x%02X (expect 0x1F 0x86 0x01)",
          id[0], id[1], id[2]);
  if (id[0] != JEDEC_MANUFACTURER_ID || id[1] != JEDEC_DEVICE_TYPE ||
      id[2] != JEDEC_CAPACITY) {
    LOG_ERR("jedec_id: unexpected ID");
  }
}

static bool enable_quad_mode(ext_flash_driver_t *drv) {
  uint8_t sr1 = 0, sr2 = 0;

  if (!cmd_read_1line(drv, CMD_READ_SR1, &sr1, 1) ||
      !cmd_read_1line(drv, CMD_READ_SR2, &sr2, 1)) {
    LOG_ERR("enable_quad_mode: SR read failed");
    return false;
  }

  LOG_INF("enable_quad_mode: SR1=0x%02X SR2=0x%02X", sr1, sr2);

  if (sr2 & SR2_QE) {
    return true;
  }

  if (!write_enable(drv)) {
    LOG_ERR("enable_quad_mode: write_enable failed");
    return false;
  }

  sr2 |= SR2_QE;
  if (!cmd_write_sr_byte(drv, CMD_WRITE_SR2, sr2)) {
    LOG_ERR("enable_quad_mode: WRITE SR2 failed");
    return false;
  }

  if (!wait_not_busy(drv, 50)) {
    LOG_ERR("enable_quad_mode: timed out");
    return false;
  }
  LOG_INF("enable_quad_mode: QE set OK");
  return true;
}

// Read SR3 and log the current IO drive strength.  Does not modify the
// register — call set_drive_strength() explicitly if a different setting
// is needed for the target PCB.
static void log_drive_strength(ext_flash_driver_t *drv) {
  uint8_t sr3 = 0;
  if (!cmd_read_1line(drv, CMD_READ_SR3, &sr3, 1)) {
    LOG_ERR("drive_strength: SR3 read failed");
    return;
  }
  // DRV[1:0]: 00=100%/30pF  01=75%/22pF  10=50%/15pF  11=Auto/7pF
  LOG_INF("drive_strength: SR3=0x%02X DRV[1:0]=%u (00=30pF,01=22pF,10=15pF,11=7pF)",
          sr3, (unsigned)((sr3 & SR3_DRV_MASK) >> 5));
}

// Set IO drive strength.  Pass an EXT_FLASH_SR3_DRV_* constant from ext_flash.h.
// WARNING: higher drive on unmatched PCB traces causes ringing and read
// corruption.  Validate with a logic analyser before changing from the
// factory default (EXT_FLASH_SR3_DRV_AUTO).  Install 22-33 Ω series resistors
// on IO lines before using EXT_FLASH_SR3_DRV_50 or higher.
bool ext_flash_set_drive_strength(uint8_t drv_bits) {
  ext_flash_driver_t *drv = &g_drv;

  if (!drv->initialized) {
    return false;
  }

  uint8_t sr3 = 0;
  if (!cmd_read_1line(drv, CMD_READ_SR3, &sr3, 1)) {
    LOG_ERR("set_drive_strength: SR3 read failed");
    return false;
  }

  uint8_t new_sr3 = (sr3 & ~SR3_DRV_MASK) | (drv_bits & SR3_DRV_MASK);
  if (new_sr3 == sr3) {
    return true;
  }

  if (!write_enable(drv)) {
    LOG_ERR("set_drive_strength: write_enable failed");
    return false;
  }

  if (!cmd_write_sr_byte(drv, CMD_WRITE_SR3, new_sr3)) {
    LOG_ERR("set_drive_strength: WRITE SR3 failed");
    return false;
  }

  if (!wait_not_busy(drv, 50)) {
    LOG_ERR("set_drive_strength: timed out");
    return false;
  }

  log_drive_strength(drv);
  return true;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

bool ext_flash_init(void) {
  ext_flash_driver_t *drv = &g_drv;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(*drv));

  gpio_init();

  if (!ospi_init(drv)) {
    LOG_ERR("ext_flash_init: ospi_init failed");
    goto fail;
  }

  if (!ospim_config(drv)) {
    LOG_ERR("ext_flash_init: ospim_config failed");
    goto fail;
  }

  log_jedec_id(drv);

  if (!enable_quad_mode(drv)) {
    LOG_ERR("ext_flash_init: enable_quad_mode failed");
    goto fail;
  }

  // Set flash output drive to 100 % (30 pF) for 100 MHz operation.
  // Factory default is Auto (7 pF) which is insufficient at this clock rate.
  if (!ext_flash_set_drive_strength(EXT_FLASH_SR3_DRV_100)) {
    LOG_ERR("ext_flash_init: set drive strength failed");
    goto fail;
  }

  drv->initialized = true;
  return true;

fail:
  HAL_OSPI_DeInit(&drv->hospi);
  gpio_deinit();
  EXT_FLASH_OSPI_FORCE_RESET();
  EXT_FLASH_OSPI_RELEASE_RESET();
  EXT_FLASH_OSPI_CLK_DISABLE();
  return false;
}

bool ext_flash_is_mmap_enabled(void) {
  return g_drv.mmap_enabled;
}

bool ext_flash_read_status(uint8_t *sr1, uint8_t *sr2, uint8_t *sr3) {
  ext_flash_driver_t *drv = &g_drv;
  if (!drv->initialized || drv->mmap_enabled) return false;
  if (sr1 && !cmd_read_1line(drv, CMD_READ_SR1, sr1, 1)) return false;
  if (sr2 && !cmd_read_1line(drv, CMD_READ_SR2, sr2, 1)) return false;
  if (sr3 && !cmd_read_1line(drv, CMD_READ_SR3, sr3, 1)) return false;
  return true;
}

void ext_flash_deinit(void) {
  ext_flash_driver_t *drv = &g_drv;

  if (!drv->initialized) {
    return;
  }

  if (drv->mmap_enabled) {
    ext_flash_mmap_disable();
  }

  HAL_OSPI_DeInit(&drv->hospi);
  gpio_deinit();

  EXT_FLASH_OSPI_FORCE_RESET();
  EXT_FLASH_OSPI_RELEASE_RESET();
  EXT_FLASH_OSPI_CLK_DISABLE();

  drv->initialized = false;
}

bool ext_flash_read(uint32_t addr, uint8_t *buf, uint32_t len) {
  ext_flash_driver_t *drv = &g_drv;

  if (!drv->initialized || drv->mmap_enabled || len == 0) {
    return false;
  }

  // Fast Read Quad I/O (0xEB): 1-4-4 mode.
  // Mode byte 0xFF: M5=M4=1, avoids XIP/continuous-read entry (requires M5=1,M4=0).
  OSPI_RegularCmdTypeDef c = {0};
  c.OperationType      = HAL_OSPI_OPTYPE_COMMON_CFG;
  c.FlashId            = HAL_OSPI_FLASH_ID_1;
  c.Instruction        = CMD_FAST_READ_QUAD_IO;
  c.InstructionMode    = HAL_OSPI_INSTRUCTION_1_LINE;
  c.InstructionSize    = HAL_OSPI_INSTRUCTION_8_BITS;
  c.InstructionDtrMode = HAL_OSPI_INSTRUCTION_DTR_DISABLE;
  c.Address            = addr;
  c.AddressMode        = HAL_OSPI_ADDRESS_4_LINES;
  c.AddressSize        = HAL_OSPI_ADDRESS_24_BITS;
  c.AddressDtrMode     = HAL_OSPI_ADDRESS_DTR_DISABLE;
  c.AlternateBytes     = 0xFF;
  c.AlternateBytesMode = HAL_OSPI_ALTERNATE_BYTES_4_LINES;
  c.AlternateBytesSize = HAL_OSPI_ALTERNATE_BYTES_8_BITS;
  c.DataMode           = HAL_OSPI_DATA_4_LINES;
  c.DataDtrMode        = HAL_OSPI_DATA_DTR_DISABLE;
  c.DummyCycles        = OSPI_READ_DUMMY_CYCLES;
  c.DQSMode            = HAL_OSPI_DQS_DISABLE;
  c.SIOOMode           = HAL_OSPI_SIOO_INST_EVERY_CMD;

  // With NbData=1 the last nibble arrives at the CS-deassertion boundary and
  // is intermittently lost. Read 2 bytes and discard the extra one.
  if (len == 1) {
    uint8_t tmp[2];
    c.NbData = 2;
    if (HAL_OSPI_Command(&drv->hospi, &c, TIMEOUT_CMD_MS) != HAL_OK) {
      return false;
    }
    if (HAL_OSPI_Receive(&drv->hospi, tmp, TIMEOUT_CMD_MS) != HAL_OK) {
      return false;
    }
    buf[0] = tmp[0];
    return true;
  }

  c.NbData = len;
  if (HAL_OSPI_Command(&drv->hospi, &c, TIMEOUT_CMD_MS) != HAL_OK) {
    return false;
  }
  return HAL_OSPI_Receive(&drv->hospi, buf, TIMEOUT_CMD_MS) == HAL_OK;
}

bool ext_flash_read_slow_debug(uint32_t addr, uint8_t *buf, uint32_t len) {
  ext_flash_driver_t *drv = &g_drv;

  if (!drv->initialized || drv->mmap_enabled || len == 0) {
    return false;
  }

  // Standard Read (0x03): 1-1-1 mode, no dummy cycles, max ~50 MHz.
  // Bypasses IO2/IO3 entirely — useful for bring-up when quad lines are suspect.
  OSPI_RegularCmdTypeDef c = {0};
  c.OperationType      = HAL_OSPI_OPTYPE_COMMON_CFG;
  c.FlashId            = HAL_OSPI_FLASH_ID_1;
  c.Instruction        = CMD_READ;
  c.InstructionMode    = HAL_OSPI_INSTRUCTION_1_LINE;
  c.InstructionSize    = HAL_OSPI_INSTRUCTION_8_BITS;
  c.InstructionDtrMode = HAL_OSPI_INSTRUCTION_DTR_DISABLE;
  c.Address            = addr;
  c.AddressMode        = HAL_OSPI_ADDRESS_1_LINE;
  c.AddressSize        = HAL_OSPI_ADDRESS_24_BITS;
  c.AddressDtrMode     = HAL_OSPI_ADDRESS_DTR_DISABLE;
  c.AlternateBytesMode = HAL_OSPI_ALTERNATE_BYTES_NONE;
  c.DataMode           = HAL_OSPI_DATA_1_LINE;
  c.DataDtrMode        = HAL_OSPI_DATA_DTR_DISABLE;
  c.DummyCycles        = 0;
  c.DQSMode            = HAL_OSPI_DQS_DISABLE;
  c.SIOOMode           = HAL_OSPI_SIOO_INST_EVERY_CMD;
  c.NbData             = len;

  if (HAL_OSPI_Command(&drv->hospi, &c, TIMEOUT_CMD_MS) != HAL_OK) {
    return false;
  }
  return HAL_OSPI_Receive(&drv->hospi, buf, TIMEOUT_CMD_MS) == HAL_OK;
}

bool ext_flash_write_page(uint32_t addr, const uint8_t *buf, uint32_t len) {
  ext_flash_driver_t *drv = &g_drv;

  if (!drv->initialized || drv->mmap_enabled || len == 0 ||
      len > EXT_FLASH_PAGE_SIZE) {
    return false;
  }

  if (!write_enable(drv)) {
    return false;
  }

  OSPI_RegularCmdTypeDef c = {0};
  c.OperationType      = HAL_OSPI_OPTYPE_COMMON_CFG;
  c.FlashId            = HAL_OSPI_FLASH_ID_1;
  c.Instruction        = CMD_QUAD_PAGE_PROGRAM;
  c.InstructionMode    = HAL_OSPI_INSTRUCTION_1_LINE;
  c.InstructionSize    = HAL_OSPI_INSTRUCTION_8_BITS;
  c.InstructionDtrMode = HAL_OSPI_INSTRUCTION_DTR_DISABLE;
  c.Address            = addr;
  c.AddressMode        = HAL_OSPI_ADDRESS_1_LINE;
  c.AddressSize        = HAL_OSPI_ADDRESS_24_BITS;
  c.AddressDtrMode     = HAL_OSPI_ADDRESS_DTR_DISABLE;
  c.AlternateBytesMode = HAL_OSPI_ALTERNATE_BYTES_NONE;
  c.DataMode           = HAL_OSPI_DATA_4_LINES;
  c.NbData             = len;
  c.DataDtrMode        = HAL_OSPI_DATA_DTR_DISABLE;
  c.DummyCycles        = 0;
  c.DQSMode            = HAL_OSPI_DQS_DISABLE;
  c.SIOOMode           = HAL_OSPI_SIOO_INST_EVERY_CMD;

  if (HAL_OSPI_Command(&drv->hospi, &c, TIMEOUT_CMD_MS) != HAL_OK) {
    return false;
  }
  if (HAL_OSPI_Transmit(&drv->hospi, (uint8_t *)buf, TIMEOUT_CMD_MS) != HAL_OK) {
    return false;
  }
  return wait_not_busy(drv, TIMEOUT_PAGE_PROGRAM_MS);
}

bool ext_flash_erase_sector(uint32_t addr) {
  ext_flash_driver_t *drv = &g_drv;

  if (!drv->initialized || drv->mmap_enabled) {
    LOG_ERR("erase_sector: not ready (init=%d mmap=%d)", drv->initialized,
            drv->mmap_enabled);
    return false;
  }

  if (!write_enable(drv)) {
    LOG_ERR("erase_sector: write_enable failed");
    return false;
  }

  uint32_t aligned = addr & ~((uint32_t)(EXT_FLASH_SECTOR_SIZE - 1));
  if (!cmd_with_addr(drv, CMD_SECTOR_ERASE_4K, aligned)) {
    LOG_ERR("erase_sector: command failed at 0x%08X", (unsigned int)aligned);
    return false;
  }
  if (!wait_not_busy(drv, TIMEOUT_SECTOR_ERASE_MS)) {
    LOG_ERR("erase_sector: timed out at 0x%08X", (unsigned int)aligned);
    return false;
  }
  return true;
}

bool ext_flash_erase_block(uint32_t addr) {
  ext_flash_driver_t *drv = &g_drv;

  if (!drv->initialized || drv->mmap_enabled) {
    return false;
  }

  if (!write_enable(drv)) {
    LOG_ERR("erase_block: write_enable failed");
    return false;
  }

  uint32_t aligned = addr & ~((uint32_t)(EXT_FLASH_BLOCK_SIZE - 1));
  if (!cmd_with_addr(drv, CMD_BLOCK_ERASE_64K, aligned)) {
    LOG_ERR("erase_block: command failed at 0x%08X", (unsigned int)aligned);
    return false;
  }
  if (!wait_not_busy(drv, TIMEOUT_BLOCK_ERASE_MS)) {
    LOG_ERR("erase_block: timed out at 0x%08X", (unsigned int)aligned);
    return false;
  }
  return true;
}

bool ext_flash_erase_chip(void) {
  ext_flash_driver_t *drv = &g_drv;

  if (!drv->initialized || drv->mmap_enabled) {
    return false;
  }

  if (!write_enable(drv)) {
    LOG_ERR("erase_chip: write_enable failed");
    return false;
  }

  if (!cmd_no_data(drv, CMD_CHIP_ERASE)) {
    LOG_ERR("erase_chip: command failed");
    return false;
  }
  if (!wait_not_busy(drv, TIMEOUT_CHIP_ERASE_MS)) {
    LOG_ERR("erase_chip: timed out");
    return false;
  }
  return true;
}

bool ext_flash_mmap_enable(void) {
  ext_flash_driver_t *drv = &g_drv;

  if (!drv->initialized) {
    return false;
  }

  if (drv->mmap_enabled) {
    return true;
  }

  drv->mmap_prev_mode = mpu_reconfig(MPU_MODE_UNUSED_FLASH);

  OSPI_RegularCmdTypeDef cmd = {0};
  cmd.OperationType      = HAL_OSPI_OPTYPE_READ_CFG;
  cmd.FlashId            = HAL_OSPI_FLASH_ID_1;
  cmd.Instruction        = CMD_FAST_READ_QUAD_IO;
  cmd.InstructionMode    = HAL_OSPI_INSTRUCTION_1_LINE;
  cmd.InstructionSize    = HAL_OSPI_INSTRUCTION_8_BITS;
  cmd.InstructionDtrMode = HAL_OSPI_INSTRUCTION_DTR_DISABLE;
  cmd.AddressMode        = HAL_OSPI_ADDRESS_4_LINES;
  cmd.AddressSize        = HAL_OSPI_ADDRESS_24_BITS;
  cmd.AddressDtrMode     = HAL_OSPI_ADDRESS_DTR_DISABLE;
  cmd.AlternateBytes     = 0xFF;
  cmd.AlternateBytesMode = HAL_OSPI_ALTERNATE_BYTES_4_LINES;
  cmd.AlternateBytesSize = HAL_OSPI_ALTERNATE_BYTES_8_BITS;
  cmd.DataMode           = HAL_OSPI_DATA_4_LINES;
  cmd.DataDtrMode        = HAL_OSPI_DATA_DTR_DISABLE;
  cmd.DummyCycles        = OSPI_READ_DUMMY_CYCLES;
  cmd.DQSMode            = HAL_OSPI_DQS_DISABLE;
  cmd.SIOOMode           = HAL_OSPI_SIOO_INST_EVERY_CMD;

  if (HAL_OSPI_Command(&drv->hospi, &cmd, TIMEOUT_CMD_MS) != HAL_OK) {
    mpu_restore(drv->mmap_prev_mode);
    return false;
  }

  // HAL requires a write-config slot even for a read-only memory-mapped window.
  cmd.OperationType      = HAL_OSPI_OPTYPE_WRITE_CFG;
  cmd.Instruction        = CMD_QUAD_PAGE_PROGRAM;
  cmd.AddressMode        = HAL_OSPI_ADDRESS_1_LINE;  // 0x32 is 1-1-4
  cmd.AlternateBytesMode = HAL_OSPI_ALTERNATE_BYTES_NONE;
  cmd.DummyCycles        = 0;

  if (HAL_OSPI_Command(&drv->hospi, &cmd, TIMEOUT_CMD_MS) != HAL_OK) {
    mpu_restore(drv->mmap_prev_mode);
    return false;
  }

  OSPI_MemoryMappedTypeDef mmap = {0};
  mmap.TimeOutActivation = HAL_OSPI_TIMEOUT_COUNTER_DISABLE;

  if (HAL_OSPI_MemoryMapped(&drv->hospi, &mmap) != HAL_OK) {
    mpu_restore(drv->mmap_prev_mode);
    return false;
  }

  drv->mmap_enabled = true;
  return true;
}

void ext_flash_mmap_disable(void) {
  ext_flash_driver_t *drv = &g_drv;

  if (!drv->initialized || !drv->mmap_enabled) {
    return;
  }

  HAL_OSPI_Abort(&drv->hospi);
  drv->mmap_enabled = false;
  mpu_restore(drv->mmap_prev_mode);
}

#endif  // KERNEL_MODE
