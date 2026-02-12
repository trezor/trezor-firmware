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

#pragma GCC optimize ("O0")

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#ifdef KERNEL_MODE

#include <io/display.h>
#include <sys/mpu.h>
#include <sys/systick.h>

#include "display_internal.h"

typedef enum {
  DISPLAY_SLOW_MODE = 0,
  DISPLAY_FAST_MODE  
} display_panel_mode_t;

typedef enum {
  DISPLAY_EP_SPI_TX_CMD,
  DISPLAY_EP_SPI_TX_RX_DATA
} display_spi_tx_rx_type_t;

typedef enum {
  DISPLAY_DEINIT = 0x00,
  DISPLAY_IO_INIT,
  DISPLAY_SPI_INIT,
  DISPLAY_PANEL_INIT,
} display_state_t;

// Display driver context.
typedef struct {
  // Set if the driver is initialized
  bool initialized;

  // Current state of the display driver state machine
  display_state_t state;

  // SPI driver
  SPI_HandleTypeDef hspi;

  // Partial/fast refresh counter for decision whether to perform full or
  // partial/fast refresh in the next update
  display_panel_mode_t panel_mode;
  uint8_t partial_fast_refresh_ctr;

  // Pointer to the frame buffer
  uint16_t *framebuf;

  // Current display orientation (0, 90, 180, 270)
  int orientation_angle;

  // Current backlight level ranging from 0 to 255
  uint8_t backlight_level;

} display_driver_t;

// Display driver instance
static display_driver_t g_display_driver = {
    .initialized = false,
    .state = DISPLAY_DEINIT,
};

static bool display_panel_init(display_panel_mode_t mode);
static bool display_panel_deinit(bool reset_content);

static inline bool display_spi_dc_set(display_spi_tx_rx_type_t tx_type) {
  if (DISPLAY_EP_SPI_TX_CMD == tx_type) {
    HAL_GPIO_WritePin(DISPLAY_EP_DC_PORT, DISPLAY_EP_DC_PIN, GPIO_PIN_RESET);
  } else if (DISPLAY_EP_SPI_TX_RX_DATA == tx_type) {
    HAL_GPIO_WritePin(DISPLAY_EP_DC_PORT, DISPLAY_EP_DC_PIN, GPIO_PIN_SET);
  } else {
    // Invalid type, do nothing
    return false;
  }

  return true;
}

static inline uint8_t display_pixel_2_byte_encode(display_color_t px1,
                                                  display_color_t px2,
                                                  display_color_t px3,
                                                  display_color_t px4) {
  // Combine four pixels into a single byte
  return ((((uint8_t)px1 & 0x3U) << 6) | (((uint8_t)px2 & 0x3U) << 4) |
          (((uint8_t)px3 & 0x3U) << 2) | ((uint8_t)px4 & 0x3U));
}

static inline uint8_t display_img_color_decode(uint8_t color_in) {
  uint8_t color_out = img_color_lut[color_in & 0x3U];
  color_out |= img_color_lut[(color_in >> 2) & 0x3U] << 2;
  color_out |= img_color_lut[(color_in >> 4) & 0x3U] << 4;
  color_out |= img_color_lut[(color_in >> 6) & 0x3U] << 6;

  return color_out;
}

static inline bool display_partial_update_possible(uint16_t x, uint16_t y,
                                                   uint16_t w, uint16_t h) {
  display_driver_t *drv = &g_display_driver;

  bool partial_fast_refresh_ctr_overflow =
      (drv->partial_fast_refresh_ctr >= DISPLAY_PARTIAL_FAST_REFRESH_THRESHOLD);
  bool full_screen_used =
      ((x == 0) && (y == 0) && (w == DISPLAY_WIDTH) && (h == DISPLAY_HEIGHT));

  return !(partial_fast_refresh_ctr_overflow || full_screen_used);
}

static bool display_busy_wait(uint32_t timeout_ms) {
  display_driver_t *drv = &g_display_driver;

  if (drv->state < DISPLAY_SPI_INIT) {
    return false;  // Not initialized enough to check busy state
  }

  uint32_t timeout_ms_stamp = ticks_timeout(timeout_ms);

  while (HAL_GPIO_ReadPin(DISPLAY_EP_BUSY_PORT, DISPLAY_EP_BUSY_PIN) ==
         GPIO_PIN_RESET) {
    if ((timeout_ms != TIMEOUT_BUSY_MS_NONE) &&
        ticks_expired(timeout_ms_stamp)) {
      return false;  // Timeout
    }
  }

  return true;  // Not busy anymore
}

static bool display_io_init(void) {
  display_driver_t *drv = &g_display_driver;

  if (drv->state != DISPLAY_DEINIT) {
    return false;  // Invalid state, should be deinit
  }

  // Enable GPIO clocks
  DISPLAY_EP_BUSY_CLK_ENA();
  DISPLAY_EP_RESET_CLK_ENA();
  DISPLAY_EP_DC_CLK_ENA();
  DISPLAY_EP_SPI_MISO_CLK_EN();
  DISPLAY_EP_SPI_MOSI_CLK_EN();
  DISPLAY_EP_SPI_SCK_CLK_EN();
  DISPLAY_EP_SPI_NSS_CLK_EN();

  // Configure GPIO pins
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  // RESET pin
  HAL_GPIO_WritePin(DISPLAY_EP_RESET_PORT, DISPLAY_EP_RESET_PIN,
                    GPIO_PIN_RESET);
  GPIO_InitStruct.Pin = DISPLAY_EP_RESET_PIN;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(DISPLAY_EP_RESET_PORT, &GPIO_InitStruct);
 
  // DC pin
  HAL_GPIO_WritePin(DISPLAY_EP_DC_PORT, DISPLAY_EP_DC_PIN, GPIO_PIN_RESET);
  GPIO_InitStruct.Pin = DISPLAY_EP_DC_PIN;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(DISPLAY_EP_DC_PORT, &GPIO_InitStruct);

  // BUSY pin
  GPIO_InitStruct.Pin = DISPLAY_EP_BUSY_PIN;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLUP; // Busy active low => use pull-up
  // SPI can use this pin as SPI_RDY
  GPIO_InitStruct.Alternate = DISPLAY_EP_SPI_PIN_AF;
  HAL_GPIO_Init(DISPLAY_EP_BUSY_PORT, &GPIO_InitStruct);

  // SPI MISO pin (not used, but configured as input with PU to avoid floating)
  GPIO_InitStruct.Pin = DISPLAY_EP_SPI_MISO_PIN;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLUP;
  HAL_GPIO_Init(DISPLAY_EP_SPI_MISO_PORT, &GPIO_InitStruct);

  // SPI MOSI pin
  GPIO_InitStruct.Pin = DISPLAY_EP_SPI_MOSI_PIN;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  HAL_GPIO_Init(DISPLAY_EP_SPI_MOSI_PORT, &GPIO_InitStruct);

  // SPI SCK pin
  GPIO_InitStruct.Pin = DISPLAY_EP_SPI_SCK_PIN;
  HAL_GPIO_Init(DISPLAY_EP_SPI_SCK_PORT, &GPIO_InitStruct);

  // SPI NSS pin
  GPIO_InitStruct.Pin = DISPLAY_EP_SPI_NSS_PIN;
  HAL_GPIO_Init(DISPLAY_EP_SPI_NSS_PORT, &GPIO_InitStruct);

  drv->state = DISPLAY_IO_INIT;

  return true;
}

static bool display_io_deinit(void) {
  display_driver_t *drv = &g_display_driver;

  if (drv->state != DISPLAY_IO_INIT) {
    return false;  // Invalid state, should be IO initialized
  }

  HAL_GPIO_DeInit(DISPLAY_EP_RESET_PORT, DISPLAY_EP_RESET_PIN);
  HAL_GPIO_DeInit(DISPLAY_EP_DC_PORT, DISPLAY_EP_DC_PIN);
  HAL_GPIO_DeInit(DISPLAY_EP_BUSY_PORT, DISPLAY_EP_BUSY_PIN);
  HAL_GPIO_DeInit(DISPLAY_EP_SPI_MISO_PORT, DISPLAY_EP_SPI_MISO_PIN);
  HAL_GPIO_DeInit(DISPLAY_EP_SPI_MOSI_PORT, DISPLAY_EP_SPI_MOSI_PIN);
  HAL_GPIO_DeInit(DISPLAY_EP_SPI_SCK_PORT, DISPLAY_EP_SPI_SCK_PIN);
  HAL_GPIO_DeInit(DISPLAY_EP_SPI_NSS_PORT, DISPLAY_EP_SPI_NSS_PIN);

  drv->state = DISPLAY_DEINIT;

  return true;
}

static bool display_spi_init(void) {
  display_driver_t* drv = &g_display_driver;

  if (drv->state != DISPLAY_IO_INIT) {
    return false;  // Invalid state, should be IO initialized
  }

  DISPLAY_EP_SPI_CLK_EN();
  DISPLAY_EP_SPI_CLK_CFG(DISPLAY_EP_SPI_CLK_SRC);
  DISPLAY_EP_SPI_FORCE_RESET();
  DISPLAY_EP_SPI_RELEASE_RESET();

  drv->hspi.Instance = DISPLAY_EP_SPI_INSTANCE;
  drv->hspi.Init.Mode = SPI_MODE_MASTER;
  // Simplex, TX only, MISO not used; half-duplex to be considered if read
  // operation is also needed; e.g. 1kOhm to be inserted in the interconnection
  // of MCU-display
  drv->hspi.Init.Direction = SPI_DIRECTION_1LINE; //SPI_DIRECTION_2LINES_TXONLY;
  drv->hspi.Init.DataSize = SPI_DATASIZE_8BIT;
  drv->hspi.Init.CLKPolarity = SPI_POLARITY_LOW;
  drv->hspi.Init.CLKPhase = SPI_PHASE_1EDGE;
  drv->hspi.Init.NSS = SPI_NSS_HARD_OUTPUT;
  // 160/64 = 2.5MHz, safe for 4-wire SPI
  drv->hspi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_64;
  drv->hspi.Init.FirstBit = SPI_FIRSTBIT_MSB;
  drv->hspi.Init.TIMode = SPI_TIMODE_DISABLE;
  drv->hspi.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  drv->hspi.Init.NSSPMode = SPI_NSS_PULSE_ENABLE;
  drv->hspi.Init.NSSPolarity = SPI_NSS_POLARITY_LOW;
  drv->hspi.Init.FifoThreshold = SPI_FIFO_THRESHOLD_01DATA;
  drv->hspi.Init.MasterSSIdleness = SPI_MASTER_SS_IDLENESS_01CYCLE;
  drv->hspi.Init.MasterInterDataIdleness =
      SPI_MASTER_INTERDATA_IDLENESS_01CYCLE;
  drv->hspi.Init.MasterReceiverAutoSusp = SPI_MASTER_RX_AUTOSUSP_ENABLE;
  drv->hspi.Init.MasterKeepIOState = SPI_MASTER_KEEP_IO_STATE_ENABLE;
  drv->hspi.Init.IOSwap = SPI_IO_SWAP_DISABLE;
  // SPI_RDY can be enabled, IO is preconfigured
  drv->hspi.Init.ReadyMasterManagement = SPI_RDY_MASTER_MANAGEMENT_INTERNALLY;
  drv->hspi.Init.ReadyPolarity = SPI_RDY_POLARITY_HIGH;

  HAL_StatusTypeDef status = HAL_SPI_Init(&drv->hspi);

  if (status != HAL_OK) {
    return false;
  }

  drv->state = DISPLAY_SPI_INIT;

  return true;
}

static bool display_spi_deinit(void) {
  display_driver_t* drv = &g_display_driver;

  if (drv->state != DISPLAY_SPI_INIT) {
    return false;  // Invalid state, should be SPI initialized
  }

  if (HAL_OK != HAL_SPI_DeInit(&drv->hspi)) {
    return false;
  }

  DISPLAY_EP_SPI_CLK_DIS();

  drv->state = DISPLAY_IO_INIT;

  return true;
}

static bool display_spi_transmit(display_spi_tx_rx_type_t tx_type,
                                 const uint8_t* data, size_t size) {
  display_driver_t* drv = &g_display_driver;

  if (drv->state < DISPLAY_SPI_INIT) {
    return false;  // Not initialized enough to transmit
  }

  if (!display_spi_dc_set(tx_type)) {
    return false;
  }

  // Wait until not busy before transmitting and transmit data over SPI
  if (!display_busy_wait(TIMEOUT_BUSY_MS_MAX) ||
      (HAL_OK != HAL_SPI_Transmit(&drv->hspi, data, size, 100))) {
    return false;
  }

  return true;
}

static bool display_spi_receive(uint8_t* data, size_t size) {
  display_driver_t* drv = &g_display_driver;

  if (drv->state < DISPLAY_SPI_INIT) {
    return false;  // Not initialized enough to receive
  }

  display_spi_dc_set(DISPLAY_EP_SPI_TX_RX_DATA);

  // Wait until not busy before receiving and receive data over SPI
  if (!display_busy_wait(TIMEOUT_BUSY_MS_MAX) ||
      (HAL_OK != HAL_SPI_Receive(&drv->hspi, data, size, 100))) {
    return false;
  }

  return true;
}

static void display_panel_power_off(void) {
  display_driver_t* drv = &g_display_driver;

  if (drv->state != DISPLAY_PANEL_INIT) {
    return;  // Not initialized enough to perform panel power-off
  }

  // Power off sequence
  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x02}, 1);
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, (uint8_t[]){0x00}, 1);
  display_busy_wait(1000);
}

static void display_panel_power_on(void) {
  display_driver_t* drv = &g_display_driver;

  if (drv->state < DISPLAY_SPI_INIT) {
    return;  // Not initialized enough to perform panel power-on
  }

  // Power on sequence
  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x04}, 1);
  display_busy_wait(1000);
}

static void display_panel_deep_sleep(void) {
  display_driver_t* drv = &g_display_driver;

  if (drv->state != DISPLAY_PANEL_INIT) {
    return;  // Not initialized enough to perform panel deep sleep
  }

  // Deep sleep
  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x07}, 1);
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, (uint8_t[]){0xA5}, 1);
  display_busy_wait(1000);
}

static void display_panel_window_set(uint16_t x, uint16_t y, uint16_t w,
                                     uint16_t h, bool partial_update_mode) {
  display_driver_t* drv = &g_display_driver;

  if (drv->state != DISPLAY_PANEL_INIT) {
    return;  // Not initialized enough to perform panel refresh
  }

  // Set partial window for subsequent data update, the actual update is
  // triggered by display_panel_refresh()
  uint8_t cmd_data[9] = {0};

  // Set partial window X start and end
  cmd_data[0] = x / 256;
  cmd_data[1] = x % 256;
  cmd_data[2] = (x + w - 1) / 256;
  cmd_data[3] = (x + w - 1) % 256;

  // Set partial window Y start and end
  cmd_data[4] = y / 256;
  cmd_data[5] = y % 256;
  cmd_data[6] = (y + h - 1) / 256;
  cmd_data[7] = (y + h - 1) % 256;

  if (partial_update_mode) {
    // Enable partial window setting
    cmd_data[8] = 0x01;
  }

  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x83}, 1);
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, cmd_data, 9);
}

static void display_panel_refresh(bool partial_update_mode) {
  display_driver_t* drv = &g_display_driver;

  if (drv->state != DISPLAY_PANEL_INIT) {
    return;  // Not initialized enough to perform panel refresh
  }
  
  // 0x97 for partial update - border shall be left in the previous state
  // (floating), 0x37 for full update
  uint8_t param = partial_update_mode ? 0x97 : 0x37;

  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x50}, 1);
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, &param, 1);

#if 0
    // Data stop
    uint8_t data_stop;
    display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x11}, 1);
    display_spi_receive(&data_stop, 1);
    UNUSED(data_stop);
#else
  // Display Update Control
  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x12}, 1);
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, (uint8_t[]){0x00}, 1);
  display_busy_wait(1000);
#endif

  if (partial_update_mode || drv->panel_mode == DISPLAY_FAST_MODE) {
    drv->partial_fast_refresh_ctr++;

    if (drv->partial_fast_refresh_ctr >=
        DISPLAY_PARTIAL_FAST_REFRESH_THRESHOLD) {
      display_panel_deinit(false);
      display_panel_init(DISPLAY_SLOW_MODE);
    }
  } else if (drv->panel_mode == DISPLAY_SLOW_MODE) {
    drv->partial_fast_refresh_ctr = 0;
  }
}

static bool display_panel_init(display_panel_mode_t mode) {
  display_driver_t* drv = &g_display_driver;

  if (drv->state != DISPLAY_SPI_INIT) {
    return false;  // Not initialized enough to init panel
  }

  systick_delay_ms(20);
  HAL_GPIO_WritePin(DISPLAY_EP_RESET_PORT, DISPLAY_EP_RESET_PIN,
                    GPIO_PIN_RESET);
  systick_delay_ms(50);
  HAL_GPIO_WritePin(DISPLAY_EP_RESET_PORT, DISPLAY_EP_RESET_PIN, GPIO_PIN_SET);
  systick_delay_ms(50);

  // Panel controller revision read-out
  uint32_t panel_controller_revision;
  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x70}, 1);
  display_spi_receive((uint8_t*)&panel_controller_revision, 3);
  UNUSED(panel_controller_revision);

  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x4D}, 1);
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, (uint8_t[]){0x78}, 1);

  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x00}, 1);  // PSR
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, (uint8_t[]){0x0F, 0x29}, 2);

  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x06}, 1);  // BTST_P
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA,
                       (uint8_t[]){0x0D, 0x12, 0x30, 0x20, 0x19, 0x2A, 0x22},
                       7);  // 47uH

  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x50}, 1);  // CDI
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, (uint8_t[]){0x37}, 1);

  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x61}, 1);  // TRES
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA,
                       (uint8_t[]){DISPLAY_WIDTH / 256, DISPLAY_WIDTH % 256,
                                   DISPLAY_HEIGHT / 256, DISPLAY_HEIGHT % 256},
                       4);

  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0xE9}, 1);
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, (uint8_t[]){0x01}, 1);

  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x30}, 1);
  display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, (uint8_t[]){0x08}, 1);

  if (mode == DISPLAY_FAST_MODE) {
    // FAST mode update (12 s)
    display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0xE0}, 1);
    display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, (uint8_t[]){0x02}, 1);

    display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0xE6}, 1);
    display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, (uint8_t[]){0x5D}, 1);

    display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0xA5}, 1);
    display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, (uint8_t[]){0x00}, 1);
    display_busy_wait(1000);
  }

  display_panel_power_on();

  drv->panel_mode = mode;

  drv->state = DISPLAY_PANEL_INIT;

  return true;
}

static bool display_panel_deinit(bool reset_content) {
  display_driver_t *drv = &g_display_driver;

  if (drv->state != DISPLAY_PANEL_INIT) {
    return false;  // Not initialized enough to deinit panel
  }

  if (reset_content) {
    display_panel_window_set(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, false);

    display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x10}, 1);

    uint8_t byte =
        display_pixel_2_byte_encode(DISPLAY_COLOR_WHITE, DISPLAY_COLOR_WHITE,
                                    DISPLAY_COLOR_WHITE, DISPLAY_COLOR_WHITE);

    for(int i = 0; i < DISPLAY_BYTES; i++)
    {
      display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, &byte, 1);
    }
  
    display_panel_refresh(false);    
  }

  display_panel_power_off();
  display_panel_deep_sleep();

  // Panel deinit does not affect SPI and IO initialization, so just move back
  // to SPI init state
  drv->state = DISPLAY_SPI_INIT;  

  return true;
}

static void display_color_fill(display_color_t color) {
  display_driver_t *drv = &g_display_driver;

  if (drv->state < DISPLAY_SPI_INIT) {
    return;
  }

  display_panel_init(DISPLAY_FAST_MODE);

  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x10}, 1);

  uint8_t byte = display_pixel_2_byte_encode(color, color, color, color);

  for(int i = 0; i < DISPLAY_BYTES; i++)
  {
    display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, &byte, 1);
  }

  display_panel_refresh(false);

  display_panel_deinit(false);
}

static void display_img_show(const uint8_t* img_data, uint16_t x, uint16_t y,
                             uint16_t w, uint16_t h) {
  display_driver_t* drv = &g_display_driver;

  if (drv->state < DISPLAY_SPI_INIT) {
    return;
  }

  if (img_data == NULL) {
    return;
  }
  
  display_panel_init(DISPLAY_FAST_MODE);

  bool partial_update_mode = display_partial_update_possible(x, y, w, h);
  display_panel_window_set(x, y, w, h, partial_update_mode);

  display_spi_transmit(DISPLAY_EP_SPI_TX_CMD, (uint8_t[]){0x10}, 1);

  for (int i = y; i < (y + h); i++) {
    for (int j = x / PIXELS_PER_BYTE; j < (x + w) / PIXELS_PER_BYTE; j++) {
      uint8_t img_data_tmp = display_img_color_decode(
          img_data[i * DISPLAY_WIDTH / PIXELS_PER_BYTE + j]);
      display_spi_transmit(DISPLAY_EP_SPI_TX_RX_DATA, &img_data_tmp, 1);
    }
  }

  display_panel_refresh(partial_update_mode);

  display_panel_deinit(false);
}

bool display_ep_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(display_driver_t));

  display_io_init();

  if (!display_spi_init()) {
    goto cleanup;
  }

  if (!display_panel_init(DISPLAY_FAST_MODE)) {
    goto cleanup;
  }

  drv->initialized = true;

  return true;

cleanup:
  display_ep_deinit(DISPLAY_RESET_CONTENT);
  return false;  
}

void display_ep_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  bool reset_content = (mode == DISPLAY_RESET_CONTENT);
  display_panel_deinit(reset_content);

  display_spi_deinit();
  display_io_deinit();

  drv->initialized = false;
}

void display_ep_demo(void) {
  display_color_fill(DISPLAY_COLOR_BLACK);
  systick_delay_ms(2000);  
  display_color_fill(DISPLAY_COLOR_WHITE);
  systick_delay_ms(2000);  
  display_color_fill(DISPLAY_COLOR_RED);
  systick_delay_ms(2000);  
  display_color_fill(DISPLAY_COLOR_YELLOW);
  systick_delay_ms(2000);

  display_img_show(test_img, 0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT);
  systick_delay_ms(2000);
  display_color_fill(DISPLAY_COLOR_WHITE);
  display_img_show(test_img, 0, 0, DISPLAY_WIDTH/2, DISPLAY_HEIGHT/2);
  systick_delay_ms(2000);
  display_color_fill(DISPLAY_COLOR_WHITE);
  display_img_show(test_img, DISPLAY_WIDTH/2, DISPLAY_HEIGHT/2, DISPLAY_WIDTH/2,
                   DISPLAY_HEIGHT/2);

  while (1) {
    continue;
  }
}

#if 0
bool display_set_backlight(uint8_t level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return false;
  }

  // Just emulation, not doing anything
  drv->backlight_level = level;
  return true;
}

uint8_t display_get_backlight(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->backlight_level;
}

int display_set_orientation(int angle) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  if (angle == 0 || angle == 90 || angle == 180 || angle == 270) {
    // Just emulation, not doing anything
    drv->orientation_angle = angle;
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
  } else {
    fb->ptr = (void *)drv->framebuf;
    fb->size = FRAME_BUFFER_SIZE;
    fb->stride = DISPLAY_RESX * sizeof(uint16_t);
    // Enable access to the frame buffer from the unprivileged code
    mpu_set_active_fb(fb->ptr, FRAME_BUFFER_SIZE);
    return true;
  }
}

void display_refresh(void) {
  // Do nothing as using just a single frame buffer

  // Disable access to the frame buffer from the unprivileged code
  mpu_set_active_fb(NULL, 0);
}

void display_fill(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = drv->framebuf + (DISPLAY_RESX * bb_new.dst_y);
  bb_new.dst_stride = DISPLAY_RESX * sizeof(uint16_t);

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_dst_y(&bb_new, FRAME_BUFFER_SIZE)) {
    return;
  }

  gfx_rgb565_fill(&bb_new);
}

void display_copy_rgb565(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = drv->framebuf + (DISPLAY_RESX * bb_new.dst_y);
  bb_new.dst_stride = DISPLAY_RESX * sizeof(uint16_t);

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_src_x(&bb_new, 16) ||
      !gfx_bitblt_check_dst_y(&bb_new, FRAME_BUFFER_SIZE)) {
    return;
  }

  gfx_rgb565_copy_rgb565(&bb_new);
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = drv->framebuf + (DISPLAY_RESX * bb_new.dst_y);
  bb_new.dst_stride = DISPLAY_RESX * sizeof(uint16_t);

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_src_x(&bb_new, 1) ||
      !gfx_bitblt_check_dst_y(&bb_new, FRAME_BUFFER_SIZE)) {
    return;
  }

  gfx_rgb565_copy_mono1p(&bb_new);
}
#endif

#endif
