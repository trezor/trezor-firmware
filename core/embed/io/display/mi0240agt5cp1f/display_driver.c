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

// AVNet (Multi-Inno) MI0240AGT-5CP1-F
// 2.4" TFT, 240(RGB)x320, controller ST7789V2, connected via 4-line 8-bit
// serial (SPI) interface (IM[2:0] = 1,1,0).
//
// This is a self-contained SPI display driver (like vg-2864), not a
// display_i8080 panel, since the module is wired for SPI rather than the
// parallel i8080 bus that the other panels on this board use.
//
// Register sequence reused from the (same ST7789 family, same 240x320
// resolution) i8080 dem240320b1 panel - see
// display/i8080/panels/dem240320b1.c. Note that the other panels already
// supported on this board (lx200b4501ctp03, lx240d4508ctp05) are GC9307-based
// despite the superficial similarity, so their register values do not apply
// here.
//
// Checked against the module's own datasheet (MI0240AGT-5CP1-F Ver 1.0,
// Multi-Inno): it confirms the ST7789V2 controller, the 240x320 resolution,
// SPI as a supported interface, and (via the IM[3:0] mode-select table) that
// IM[2:0] = 1,1,0 is indeed 4-line 8-bit serial mode - but, like the
// dem240320b1 module, it does not publish a register init table, so it can't
// independently confirm the gamma/VCOM/porch/inversion values below. The
// ST7789V2 controller datasheet itself only lists generic silicon-reset
// (power-on) defaults for those registers, which are not panel-tuned and are
// not a better source than the values below (borrowed from a same-controller
// panel already tuned against real hardware). No public reference for this
// exact part number exists either. These values remain a reasonable
// starting point pending validation on real hardware.

#pragma GCC optimize ("O0")

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/backlight.h>
#include <io/display.h>
#include <rtl/sizedefs.h>
#include <sys/mpu.h>

#ifdef USE_TRUSTZONE
#include <sys/trustzone.h>
#endif

#ifdef USE_CONSUMPTION_MASK
#include <sec/consumption_mask.h>
#endif

#ifdef KERNEL_MODE

#if (DISPLAY_RESX != 240) || (DISPLAY_RESY != 320)
#error "Incompatible display resolution"
#endif

// Hardware requires physical frame buffer alignment
#ifdef USE_TRUSTZONE
#define PHYSICAL_FRAME_BUFFER_ALIGNMENT TZ_SRAM_ALIGNMENT
#else
#define PHYSICAL_FRAME_BUFFER_ALIGNMENT 4
#endif

// 2 bytes per pixel (RGB565)
#define FRAME_BUFFER_SIZE                            \
  ALIGN_UP_CONST(DISPLAY_RESX *DISPLAY_RESY * 2, \
                 PHYSICAL_FRAME_BUFFER_ALIGNMENT)

static __attribute__((section(".fb1"),
                      aligned(PHYSICAL_FRAME_BUFFER_ALIGNMENT))) uint8_t
    g_framebuf[FRAME_BUFFER_SIZE];

// Display driver context.
typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // SPI driver instance
  SPI_HandleTypeDef spi;
  // Frame buffer (RGB565)
  uint8_t *framebuf;
  // Current display orientation (0, 90, 180 or 270)
  int orientation_angle;
} display_driver_t;

// Display driver instance
static display_driver_t g_display_driver = {
    .initialized = false,
};

// ST7789V2 command set (subset used by this driver)
#define ST7789V2_SLPOUT 0x11
#define ST7789V2_INVON 0x21
#define ST7789V2_DISPON 0x29
#define ST7789V2_CASET 0x2A
#define ST7789V2_RASET 0x2B
#define ST7789V2_RAMWR 0x2C
#define ST7789V2_MADCTL 0x36
#define ST7789V2_COLMOD 0x3A
#define ST7789V2_RAMCTRL 0xB0
#define ST7789V2_PORCTRL 0xB2
#define ST7789V2_VCOMS 0xBB
#define ST7789V2_LCMCTRL 0xC0
#define ST7789V2_VDVVRHEN 0xC2
#define ST7789V2_VRHS 0xC3
#define ST7789V2_VDVS 0xC4
#define ST7789V2_FRCTRL2 0xC6
#define ST7789V2_PWCTRL1 0xD0
#define ST7789V2_PVGAMCTRL 0xE0
#define ST7789V2_NVGAMCTRL 0xE1

// MADCTL rotation bits (ST7789V2 manual, section 8.12)
#define MADCTL_MV (1 << 5)
#define MADCTL_MX (1 << 6)
#define MADCTL_MY (1 << 7)

// Configures SPI driver/controller
static bool display_init_spi(display_driver_t *drv) {
  drv->spi.Instance = DISPLAY_SPI;
  drv->spi.State = HAL_SPI_STATE_RESET;
  // TODO: conservative default, may need tuning against real hardware
  drv->spi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;
  drv->spi.Init.Direction = SPI_DIRECTION_2LINES;
  drv->spi.Init.CLKPhase = SPI_PHASE_1EDGE;
  drv->spi.Init.CLKPolarity = SPI_POLARITY_LOW;
  drv->spi.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  drv->spi.Init.CRCPolynomial = 7;
  drv->spi.Init.DataSize = SPI_DATASIZE_8BIT;
  drv->spi.Init.FirstBit = SPI_FIRSTBIT_MSB;
  // CS is a plain bit-banged GPIO (no NSS alternate function routed to it)
  drv->spi.Init.NSS = SPI_NSS_SOFT;
  drv->spi.Init.TIMode = SPI_TIMODE_DISABLE;
  drv->spi.Init.Mode = SPI_MODE_MASTER;

  return (HAL_OK == HAL_SPI_Init(&drv->spi)) ? true : false;
}

// Sends specified number of bytes to the display via SPI interface
//
// `len` must not exceed 65535 (HAL_SPI_Transmit's `Size` is a uint16_t) -
// callers with larger buffers must split the transfer into chunks.
static void display_send_bytes(display_driver_t *drv, const uint8_t *data,
                               size_t len) {
  if (HAL_OK != HAL_SPI_Transmit(&drv->spi, (uint8_t *)data, len, 1000)) {
    // TODO: error
    return;
  }
  while (HAL_SPI_STATE_READY != HAL_SPI_GetState(&drv->spi)) {
  }
}

// Sends a single command byte (DC low)
static void st7789v2_cmd(display_driver_t *drv, uint8_t cmd) {
  HAL_GPIO_WritePin(DISPLAY_DC_PORT, DISPLAY_DC_PIN, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(DISPLAY_SPI_CS_PORT, DISPLAY_SPI_CS_PIN, GPIO_PIN_RESET);
  display_send_bytes(drv, &cmd, 1);
  HAL_GPIO_WritePin(DISPLAY_SPI_CS_PORT, DISPLAY_SPI_CS_PIN, GPIO_PIN_SET);
}

// Sends data bytes following a command (DC high)
static void st7789v2_data(display_driver_t *drv, const uint8_t *data,
                          size_t len) {
  HAL_GPIO_WritePin(DISPLAY_DC_PORT, DISPLAY_DC_PIN, GPIO_PIN_SET);
  HAL_GPIO_WritePin(DISPLAY_SPI_CS_PORT, DISPLAY_SPI_CS_PIN, GPIO_PIN_RESET);
  display_send_bytes(drv, data, len);
  HAL_GPIO_WritePin(DISPLAY_SPI_CS_PORT, DISPLAY_SPI_CS_PIN, GPIO_PIN_SET);
}

static void st7789v2_data1(display_driver_t *drv, uint8_t byte) {
  st7789v2_data(drv, &byte, 1);
}

// Register values below are the same as the i8080 dem240320b1 panel (same
// ST7789 controller family, same 240x320 resolution) - see comment at the
// top of this file. Gamma / VCOM / porch / inversion values may need tuning
// against real hardware.
static void st7789v2_init_seq(display_driver_t *drv) {
  // Memory Data Access Control (MADCTL): default orientation. This panel's
  // column scan direction is reversed relative to the controller's native
  // (MX=0) reference - MY alone was a true 180-degree rotation of correct
  // (not a mirror), and MX|MY together over-corrected to a horizontal
  // mirror, so MX alone is the "upright" default. See the matching 0/180
  // swap in display_set_orientation() below.
  st7789v2_cmd(drv, ST7789V2_MADCTL);
  st7789v2_data1(drv, MADCTL_MX);

  // Interface Pixel Format: 16 bits/pixel (RGB565)
  st7789v2_cmd(drv, ST7789V2_COLMOD);
  st7789v2_data1(drv, 0x05);

  // RAM Control: set ENDIAN=1 (Little Endian, D3 of 2nd parameter). Our
  // framebuffer stores each RGB565 pixel as a native little-endian uint16_t
  // and display_sync_with_fb() sends its bytes as-is (low byte first), but
  // the controller's power-on default (ENDIAN=0) expects the high byte
  // first - that mismatch, not a subpixel wiring/color-order issue, was the
  // actual root cause of the earlier color-channel-swap and gradient-stripe
  // bugs (see git history for the abandoned MADCTL_BGR/software-swap
  // workaround this replaced). 1st parameter 0x00 selects RM=0 (RAM access
  // from MCU interface) / DM=00 (MCU interface mode) - both already the
  // reset default, spelled out here since they must accompany the 2nd
  // parameter in the same command. See ST7789V2 datasheet section 9.2.1,
  // "RAMCTRL (B0h): RAM Control".
  st7789v2_cmd(drv, ST7789V2_RAMCTRL);
  {
    static const uint8_t d[2] = {0x00, 0xC8};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Column Address Set: 0 .. 239
  st7789v2_cmd(drv, ST7789V2_CASET);
  {
    static const uint8_t d[4] = {0x00, 0x00, 0x00, 0xEF};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Row Address Set: 0 .. 319
  st7789v2_cmd(drv, ST7789V2_RASET);
  {
    static const uint8_t d[4] = {0x00, 0x00, 0x01, 0x3F};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Porch Setting
  st7789v2_cmd(drv, ST7789V2_PORCTRL);
  {
    static const uint8_t d[5] = {0x0C, 0x0C, 0x00, 0x33, 0x33};
    st7789v2_data(drv, d, sizeof(d));
  }

  // VCOM Setting
  st7789v2_cmd(drv, ST7789V2_VCOMS);
  st7789v2_data1(drv, 0x1F);

  // LCMCTRL: LCM Control
  st7789v2_cmd(drv, ST7789V2_LCMCTRL);
  st7789v2_data1(drv, 0x20);

  // VDV and VRH Command Enable
  st7789v2_cmd(drv, ST7789V2_VDVVRHEN);
  st7789v2_data1(drv, 0x01);

  // VRH Set (4.3V)
  st7789v2_cmd(drv, ST7789V2_VRHS);
  st7789v2_data1(drv, 0x0F);

  // VDV Setting
  st7789v2_cmd(drv, ST7789V2_VDVS);
  st7789v2_data1(drv, 0x20);

  // Frame Rate Control in Normal Mode (column inversion)
  st7789v2_cmd(drv, ST7789V2_FRCTRL2);
  st7789v2_data1(drv, 0xEF);

  // Display Inversion On (panel is normally black)
  st7789v2_cmd(drv, ST7789V2_INVON);

  // PWCTRL1: Power Control 1
  st7789v2_cmd(drv, ST7789V2_PWCTRL1);
  {
    static const uint8_t d[2] = {0xA4, 0xA1};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Positive voltage gamma correction
  st7789v2_cmd(drv, ST7789V2_PVGAMCTRL);
  {
    static const uint8_t d[14] = {0xD0, 0x0A, 0x10, 0x0A, 0x0A, 0x26, 0x36,
                                  0x34, 0x4D, 0x18, 0x13, 0x14, 0x2F, 0x34};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Negative voltage gamma correction
  st7789v2_cmd(drv, ST7789V2_NVGAMCTRL);
  {
    static const uint8_t d[14] = {0xD0, 0x0A, 0x10, 0x0A, 0x09, 0x26, 0x36,
                                  0x53, 0x4C, 0x18, 0x14, 0x14, 0x2F, 0x34};
    st7789v2_data(drv, d, sizeof(d));
  }
}

// Must stay under HAL_SPI_Transmit's uint16_t `Size` limit (65535).
#define MAX_CHUNK 32768

// Copies the frame buffer to the display via SPI interface
static void display_sync_with_fb(display_driver_t *drv) {
  mpu_set_active_fb(drv->framebuf, FRAME_BUFFER_SIZE);

  st7789v2_cmd(drv, ST7789V2_RAMWR);

  HAL_GPIO_WritePin(DISPLAY_DC_PORT, DISPLAY_DC_PIN, GPIO_PIN_SET);
  HAL_GPIO_WritePin(DISPLAY_SPI_CS_PORT, DISPLAY_SPI_CS_PIN, GPIO_PIN_RESET);

  // Sent as-is, no byte-swap needed - RAMCTRL.ENDIAN is set to Little Endian
  // in st7789v2_init_seq() to match our framebuf's native pixel byte order.
  const uint8_t *src = drv->framebuf;
  size_t remaining = FRAME_BUFFER_SIZE;
  while (remaining > 0) {
    size_t n = (remaining < MAX_CHUNK) ? remaining : MAX_CHUNK;
    display_send_bytes(drv, src, n);
    src += n;
    remaining -= n;
  }

  HAL_GPIO_WritePin(DISPLAY_SPI_CS_PORT, DISPLAY_SPI_CS_PIN, GPIO_PIN_SET);

  mpu_set_active_fb(NULL, 0);
}

bool display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(display_driver_t));
  drv->framebuf = g_framebuf;

  if (mode == DISPLAY_RESET_CONTENT) {
    DISPLAY_SPI_CLK_EN();
    DISPLAY_SPI_SCK_CLK_EN();
    DISPLAY_SPI_MOSI_CLK_EN();
    DISPLAY_SPI_CS_CLK_EN();
    __HAL_RCC_GPIOF_CLK_ENABLE();  // DC (WRX)
    __HAL_RCC_GPIOG_CLK_ENABLE();  // RST

    GPIO_InitTypeDef GPIO_InitStructure = {0};

#ifdef DISPLAY_PWR_PIN
    // Enable the display power supply (load switch) before reset. Without
    // this the whole module - including the backlight - stays unpowered.
    GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStructure.Pull = GPIO_NOPULL;
    GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStructure.Alternate = 0;
    GPIO_InitStructure.Pin = DISPLAY_PWR_PIN;
    HAL_GPIO_WritePin(DISPLAY_PWR_PORT, DISPLAY_PWR_PIN, GPIO_PIN_RESET);
    HAL_GPIO_Init(DISPLAY_PWR_PORT, &GPIO_InitStructure);
#endif

    // CS, DC, RST: plain push-pull outputs
    GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStructure.Pull = GPIO_NOPULL;
    GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStructure.Alternate = 0;

    GPIO_InitStructure.Pin = DISPLAY_SPI_CS_PIN;
    HAL_GPIO_WritePin(DISPLAY_SPI_CS_PORT, DISPLAY_SPI_CS_PIN,
                      GPIO_PIN_SET);  // deselected
    HAL_GPIO_Init(DISPLAY_SPI_CS_PORT, &GPIO_InitStructure);

    GPIO_InitStructure.Pin = DISPLAY_DC_PIN;
    HAL_GPIO_WritePin(DISPLAY_DC_PORT, DISPLAY_DC_PIN,
                      GPIO_PIN_RESET);  // command mode
    HAL_GPIO_Init(DISPLAY_DC_PORT, &GPIO_InitStructure);

    GPIO_InitStructure.Pin = DISPLAY_RST_PIN;
    HAL_GPIO_WritePin(DISPLAY_RST_PORT, DISPLAY_RST_PIN, GPIO_PIN_RESET);
    HAL_GPIO_Init(DISPLAY_RST_PORT, &GPIO_InitStructure);

    // IM[2:0] = 1,1,0 selects 4-line 8-bit serial I/F (ST7789V2 manual,
    // section 6.2). These are latched at reset, so must be driven to their
    // final level before the reset pulse below.
    GPIO_InitStructure.Pin = DISPLAY_SPI_IM0_PIN;
    HAL_GPIO_WritePin(DISPLAY_SPI_IM0_PORT, DISPLAY_SPI_IM0_PIN,
                      GPIO_PIN_RESET);
    HAL_GPIO_Init(DISPLAY_SPI_IM0_PORT, &GPIO_InitStructure);

    GPIO_InitStructure.Pin = DISPLAY_SPI_IM1_PIN;
    HAL_GPIO_WritePin(DISPLAY_SPI_IM1_PORT, DISPLAY_SPI_IM1_PIN, GPIO_PIN_SET);
    HAL_GPIO_Init(DISPLAY_SPI_IM1_PORT, &GPIO_InitStructure);

    GPIO_InitStructure.Pin = DISPLAY_SPI_IM2_PIN;
    HAL_GPIO_WritePin(DISPLAY_SPI_IM2_PORT, DISPLAY_SPI_IM2_PIN, GPIO_PIN_SET);
    HAL_GPIO_Init(DISPLAY_SPI_IM2_PORT, &GPIO_InitStructure);

    // SCK, MOSI: SPI2 alternate function (note SCK and MOSI use different
    // AFs on this MCU - see comment in devkit.h)
    GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStructure.Alternate = DISPLAY_SPI_PIN_AF;
    GPIO_InitStructure.Pin = DISPLAY_SPI_SCK_PIN;
    HAL_GPIO_Init(DISPLAY_SPI_SCK_PORT, &GPIO_InitStructure);

    GPIO_InitStructure.Alternate = DISPLAY_SPI_MOSI_AF;
    GPIO_InitStructure.Pin = DISPLAY_SPI_MOSI_PIN;
    HAL_GPIO_Init(DISPLAY_SPI_MOSI_PORT, &GPIO_InitStructure);

    // Initialize SPI controller
    display_init_spi(drv);

    // Hardware reset. Max wait time for hardware reset is 120 milliseconds.
    HAL_Delay(10);
    HAL_GPIO_WritePin(DISPLAY_RST_PORT, DISPLAY_RST_PIN, GPIO_PIN_SET);
    HAL_Delay(120);

    st7789v2_init_seq(drv);

    st7789v2_cmd(drv, ST7789V2_SLPOUT);
    HAL_Delay(5);  // need to wait 5 milliseconds after "sleep out" before
                   // sending any new commands
    st7789v2_cmd(drv, ST7789V2_DISPON);

    // g_framebuf is already zeroed (BSS) at this point in boot; the actual
    // write to it must stay inside display_sync_with_fb()'s
    // mpu_set_active_fb() window below - an unguarded memset here faults
    // (MPU region for the framebuffer isn't active yet at this point).
    display_sync_with_fb(drv);

    backlight_init(BACKLIGHT_RESET, 1.0f);
  } else {
    display_init_spi(drv);
    backlight_init(BACKLIGHT_RETAIN, 1.0f);
  }

  gfx_bitblt_init();

  drv->initialized = true;
  return true;
}

void display_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  mpu_set_active_fb(NULL, 0);

  gfx_bitblt_deinit();

  backlight_deinit(mode == DISPLAY_RESET_CONTENT ? BACKLIGHT_RESET
                                                 : BACKLIGHT_RETAIN);

  drv->initialized = false;
}

#ifdef USE_TRUSTZONE
void display_set_unpriv_access(bool unpriv) {
  tz_set_sram_unpriv((uint32_t)g_framebuf, FRAME_BUFFER_SIZE, unpriv);
}
#endif  // USE_TRUSTZONE

#ifdef USE_SUSPEND
// This driver has no display-based (touch) wakeup path, so the power
// manager's suspend/resume framework does not drive the display off/on here
// (that is gated on touch-wakeup). These are minimal hooks so the framework
// links; the display state is preserved across the CPU's low-power stop.
void display_suspend(display_wakeup_params_t *wakeup_params) {
  if (wakeup_params != NULL) {
    memset(wakeup_params, 0, sizeof(*wakeup_params));
  }
}

void display_resume(const display_wakeup_params_t *wakeup_params) {
  (void)wakeup_params;
}
#endif  // USE_SUSPEND

bool display_set_backlight(uint8_t level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return false;
  }

  return backlight_set(level);
}

uint8_t display_get_backlight(void) { return backlight_get(); }

int display_set_orientation(int angle) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  if (angle != drv->orientation_angle) {
    if (angle == 0 || angle == 90 || angle == 180 || angle == 270) {
      drv->orientation_angle = angle;

      // 0/180 are swapped relative to the "textbook" ST7789V2 bits (MX
      // alone / MY alone instead of 0 / MX|MY) to match this panel's
      // reversed column scan direction - see st7789v2_init_seq() above.
      // 90/270 are still the textbook values and haven't been verified
      // against real hardware yet.
      uint8_t madctl = 0;
      switch (angle) {
        case 90:
          madctl = MADCTL_MV | MADCTL_MX;
          break;
        case 180:
          madctl = MADCTL_MY;
          break;
        case 270:
          madctl = MADCTL_MV | MADCTL_MY;
          break;
        default:
          madctl = MADCTL_MX;
          break;
      }

      st7789v2_cmd(drv, ST7789V2_MADCTL);
      st7789v2_data1(drv, madctl);

      display_sync_with_fb(drv);
    }
  }

  return drv->orientation_angle;
}

int display_get_orientation(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->orientation_angle;
}

bool display_get_frame_buffer(display_fb_info_t *fb) {
  display_driver_t *drv = &g_display_driver;

  memset(fb, 0, sizeof(display_fb_info_t));

  if (!drv->initialized) {
    return false;
  }

  fb->ptr = &drv->framebuf[0];
  fb->size = FRAME_BUFFER_SIZE;
  fb->stride = DISPLAY_RESX * 2;
  // Enable access to the frame buffer from the unprivileged code
  mpu_set_active_fb(fb->ptr, fb->size);
  return true;
}

void display_refresh(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

#if defined USE_CONSUMPTION_MASK && !defined BOARDLOADER
  // This is an intentional randomization of the consumption masking algorithm
  // after every change on the display
  consumption_mask_randomize();
#endif

  // Disable access to the frame buffer from the unprivileged code
  mpu_set_active_fb(NULL, 0);

  // Copy the frame buffer to the display
  display_sync_with_fb(drv);
}

void display_fill(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = &(((uint8_t *)fb.ptr)[fb.stride * bb_new.dst_y]);
  bb_new.dst_stride = fb.stride;

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_dst_y(&bb_new, fb.size)) {
    return;
  }

  gfx_rgb565_fill(&bb_new);
}

void display_copy_rgb565(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = &(((uint8_t *)fb.ptr)[fb.stride * bb_new.dst_y]);
  bb_new.dst_stride = fb.stride;

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_src_x(&bb_new, 16) ||
      !gfx_bitblt_check_dst_y(&bb_new, fb.size)) {
    return;
  }

  gfx_rgb565_copy_rgb565(&bb_new);
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = &(((uint8_t *)fb.ptr)[fb.stride * bb_new.dst_y]);
  bb_new.dst_stride = fb.stride;

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_src_x(&bb_new, 1) ||
      !gfx_bitblt_check_dst_y(&bb_new, fb.size)) {
    return;
  }

  gfx_rgb565_copy_mono1p(&bb_new);
}

#endif  // KERNEL_MODE
