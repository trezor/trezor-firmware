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

#include STM32_HAL_H

#define OLED_BUFSIZE (DISPLAY_RESX * DISPLAY_RESY / 8)
#define OLED_OFFSET(x, y) (OLED_BUFSIZE - 1 - (x) - ((y) / 8) * DISPLAY_RESX)
#define OLED_MASK(x, y) (1 << (7 - (y) % 8))

#define OLED_SETCONTRAST 0x81
#define OLED_DISPLAYALLON_RESUME 0xA4
#define OLED_DISPLAYALLON 0xA5
#define OLED_NORMALDISPLAY 0xA6
#define OLED_INVERTDISPLAY 0xA7
#define OLED_DISPLAYOFF 0xAE
#define OLED_DISPLAYON 0xAF
#define OLED_SETDISPLAYOFFSET 0xD3
#define OLED_SETCOMPINS 0xDA
#define OLED_SETVCOMDETECT 0xDB
#define OLED_SETDISPLAYCLOCKDIV 0xD5
#define OLED_SETPRECHARGE 0xD9
#define OLED_SETMULTIPLEX 0xA8
#define OLED_SETLOWCOLUMN 0x00
#define OLED_SETHIGHCOLUMN 0x10
#define OLED_SETSTARTLINE 0x40
#define OLED_MEMORYMODE 0x20
#define OLED_COMSCANINC 0xC0
#define OLED_COMSCANDEC 0xC8
#define OLED_SEGREMAP 0xA0
#define OLED_CHARGEPUMP 0x8D

#define OLED_DC_PORT GPIOB
#define OLED_DC_PIN GPIO_PIN_0  // PB0 | Data/Command
#define OLED_CS_PORT GPIOA
#define OLED_CS_PIN GPIO_PIN_4  // PA4 | SPI Select
#define OLED_RST_PORT GPIOB
#define OLED_RST_PIN GPIO_PIN_1  // PB1 | Reset display

static uint8_t OLED_BUFFER[OLED_BUFSIZE];

static struct {
  struct {
    uint16_t x, y;
  } start;
  struct {
    uint16_t x, y;
  } end;
  struct {
    uint16_t x, y;
  } pos;
} PIXELWINDOW;

void PIXELDATA(uint16_t c) {
  if (PIXELWINDOW.pos.x <= PIXELWINDOW.end.x &&
      PIXELWINDOW.pos.y <= PIXELWINDOW.end.y) {
    // set to white if highest bits of all R, G, B values are set to 1
    // bin(10000 100000 10000) = hex(0x8410)
    // otherwise set to black
    if (c & 0x8410) {
      OLED_BUFFER[OLED_OFFSET(PIXELWINDOW.pos.x, PIXELWINDOW.pos.y)] |=
          OLED_MASK(PIXELWINDOW.pos.x, PIXELWINDOW.pos.y);
    } else {
      OLED_BUFFER[OLED_OFFSET(PIXELWINDOW.pos.x, PIXELWINDOW.pos.y)] &=
          ~OLED_MASK(PIXELWINDOW.pos.x, PIXELWINDOW.pos.y);
    }
  }
  PIXELWINDOW.pos.x++;
  if (PIXELWINDOW.pos.x > PIXELWINDOW.end.x) {
    PIXELWINDOW.pos.x = PIXELWINDOW.start.x;
    PIXELWINDOW.pos.y++;
  }
}

static void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1,
                               uint16_t y1) {
  PIXELWINDOW.start.x = x0;
  PIXELWINDOW.start.y = y0;
  PIXELWINDOW.end.x = x1;
  PIXELWINDOW.end.y = y1;
  PIXELWINDOW.pos.x = x0;
  PIXELWINDOW.pos.y = y0;
}

static void display_set_orientation(int degrees) { display_refresh(); }

static void display_set_backlight(int val) {}

SPI_HandleTypeDef spi_handle;

static inline void spi_send(const uint8_t *data, int len) {
  HAL_Delay(1);
  if (HAL_OK != HAL_SPI_Transmit(&spi_handle, (uint8_t *)data, len, 1000)) {
    // TODO: error
    return;
  }
  while (HAL_SPI_STATE_READY != HAL_SPI_GetState(&spi_handle)) {
  }
}

void display_init(void) {
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_SPI1_CLK_ENABLE();

  GPIO_InitTypeDef GPIO_InitStructure;

  // set GPIO for OLED display
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = GPIO_PIN_4;
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = GPIO_PIN_0 | GPIO_PIN_4;
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0 | GPIO_PIN_4, GPIO_PIN_RESET);
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

  // enable SPI 1 for OLED display
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = GPIO_AF5_SPI1;
  GPIO_InitStructure.Pin = GPIO_PIN_5 | GPIO_PIN_7;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  spi_handle.Instance = SPI1;
  spi_handle.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;
  spi_handle.Init.Direction = SPI_DIRECTION_2LINES;
  spi_handle.Init.CLKPhase = SPI_PHASE_1EDGE;
  spi_handle.Init.CLKPolarity = SPI_POLARITY_LOW;
  spi_handle.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  spi_handle.Init.CRCPolynomial = 7;
  spi_handle.Init.DataSize = SPI_DATASIZE_8BIT;
  spi_handle.Init.FirstBit = SPI_FIRSTBIT_MSB;
  spi_handle.Init.NSS = SPI_NSS_HARD_OUTPUT;
  spi_handle.Init.TIMode = SPI_TIMODE_DISABLE;
  spi_handle.Init.Mode = SPI_MODE_MASTER;
  if (HAL_OK != HAL_SPI_Init(&spi_handle)) {
    // TODO: error
    return;
  }

  // initialize display

  static const uint8_t s[25] = {OLED_DISPLAYOFF,
                                OLED_SETDISPLAYCLOCKDIV,
                                0x80,
                                OLED_SETMULTIPLEX,
                                0x3F,  // 128x64
                                OLED_SETDISPLAYOFFSET,
                                0x00,
                                OLED_SETSTARTLINE | 0x00,
                                OLED_CHARGEPUMP,
                                0x14,
                                OLED_MEMORYMODE,
                                0x00,
                                OLED_SEGREMAP | 0x01,
                                OLED_COMSCANDEC,
                                OLED_SETCOMPINS,
                                0x12,  // 128x64
                                OLED_SETCONTRAST,
                                0xCF,
                                OLED_SETPRECHARGE,
                                0xF1,
                                OLED_SETVCOMDETECT,
                                0x40,
                                OLED_DISPLAYALLON_RESUME,
                                OLED_NORMALDISPLAY,
                                OLED_DISPLAYON};

  HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_RESET);  // set to CMD
  HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);    // SPI deselect

  // Reset the LCD
  HAL_GPIO_WritePin(OLED_RST_PORT, OLED_RST_PIN, GPIO_PIN_SET);
  HAL_Delay(40);
  HAL_GPIO_WritePin(OLED_RST_PORT, OLED_RST_PIN, GPIO_PIN_RESET);
  HAL_Delay(400);
  HAL_GPIO_WritePin(OLED_RST_PORT, OLED_RST_PIN, GPIO_PIN_SET);

  // init
  HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_RESET);  // SPI select
  spi_send(s, 25);
  HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);  // SPI deselect

  display_clear();
  display_refresh();
}

static inline uint8_t reverse_byte(uint8_t b) {
  b = (b & 0xF0) >> 4 | (b & 0x0F) << 4;
  b = (b & 0xCC) >> 2 | (b & 0x33) << 2;
  b = (b & 0xAA) >> 1 | (b & 0x55) << 1;
  return b;
}

static void rotate_oled_buffer(void) {
  for (int i = 0; i < OLED_BUFSIZE / 2; i++) {
    uint8_t b = OLED_BUFFER[i];
    OLED_BUFFER[i] = reverse_byte(OLED_BUFFER[OLED_BUFSIZE - i]);
    OLED_BUFFER[OLED_BUFSIZE - i] = reverse_byte(b);
  }
}

void display_refresh(void) {
  static const uint8_t s[3] = {OLED_SETLOWCOLUMN | 0x00,
                               OLED_SETHIGHCOLUMN | 0x00,
                               OLED_SETSTARTLINE | 0x00};

  HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_RESET);  // SPI select
  spi_send(s, 3);
  HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);  // SPI deselect

  HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_SET);    // set to DATA
  HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_RESET);  // SPI select
  if (DISPLAY_ORIENTATION == 180) {  // rotate buffer if needed
    rotate_oled_buffer();
  }
  spi_send(OLED_BUFFER, OLED_BUFSIZE);
  if (DISPLAY_ORIENTATION == 180) {  // rotate buffer back to original position
    rotate_oled_buffer();
  }
  HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);    // SPI deselect
  HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_RESET);  // set to CMD
}

const char *display_save(const char *prefix) { return NULL; }

void display_clear_save(void) {}
