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
#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <libtropic.h>

#include <memzero.h>
#include <sec/rng_strong.h>
#include <sec/tropic.h>
#include <sys/systick.h>

typedef struct {
  bool initialized;
  SPI_HandleTypeDef spi;
} tropic01_hal_driver_t;

static tropic01_hal_driver_t g_tropic01_hal_driver = {.initialized = false};

static tropic_ui_progress_t ui_progress = NULL;

void tropic_set_ui_progress(tropic_ui_progress_t f) { ui_progress = f; }

void tropic01_reset(void) {
  HAL_GPIO_WritePin(TROPIC01_SPI_NSS_PORT, TROPIC01_SPI_NSS_PIN,
                    GPIO_PIN_RESET);
  HAL_GPIO_WritePin(TROPIC01_PWR_PORT, TROPIC01_PWR_PIN, GPIO_PIN_SET);
  systick_delay_ms(10);
  HAL_GPIO_WritePin(TROPIC01_PWR_PORT, TROPIC01_PWR_PIN, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(TROPIC01_SPI_NSS_PORT, TROPIC01_SPI_NSS_PIN, GPIO_PIN_SET);
}

lt_ret_t lt_port_init(lt_l2_state_t *s2) {
  tropic01_hal_driver_t *drv = &g_tropic01_hal_driver;

  if (drv->initialized) {
    return LT_OK;
  }

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  TROPIC01_INT_CLK_EN();
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = TROPIC01_INT_PIN;
  HAL_GPIO_Init(TROPIC01_INT_PORT, &GPIO_InitStructure);
  HAL_GPIO_WritePin(TROPIC01_INT_PORT, TROPIC01_INT_PIN, GPIO_PIN_RESET);

  TROPIC01_PWR_CLK_EN();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = TROPIC01_PWR_PIN;
  HAL_GPIO_Init(TROPIC01_PWR_PORT, &GPIO_InitStructure);
  HAL_GPIO_WritePin(TROPIC01_PWR_PORT, TROPIC01_PWR_PIN, GPIO_PIN_RESET);

  TROPIC01_SPI_NSS_EN();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = TROPIC01_SPI_NSS_PIN;
  HAL_GPIO_Init(TROPIC01_SPI_NSS_PORT, &GPIO_InitStructure);
  HAL_GPIO_WritePin(TROPIC01_SPI_NSS_PORT, TROPIC01_SPI_NSS_PIN, GPIO_PIN_SET);

  systick_delay_ms(10);

  // spi pins
  TROPIC01_SPI_SCK_EN();
  TROPIC01_SPI_MISO_EN();
  TROPIC01_SPI_MOSI_EN();
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = TROPIC01_SPI_PIN_AF;
  GPIO_InitStructure.Pin = TROPIC01_SPI_SCK_PIN;
  HAL_GPIO_Init(TROPIC01_SPI_SCK_PORT, &GPIO_InitStructure);

  GPIO_InitStructure.Pin = TROPIC01_SPI_SCK_PIN;
  HAL_GPIO_Init(TROPIC01_SPI_SCK_PORT, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = TROPIC01_SPI_MISO_PIN;
  HAL_GPIO_Init(TROPIC01_SPI_MISO_PORT, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = TROPIC01_SPI_MOSI_PIN;
  HAL_GPIO_Init(TROPIC01_SPI_MOSI_PORT, &GPIO_InitStructure);

  TROPIC01_SPI_CLK_EN();
  TROPIC01_SPI_FORCE_RESET();
  TROPIC01_SPI_RELEASE_RESET();

  drv->spi.Instance = TROPIC01_SPI;
  drv->spi.Init.Mode = SPI_MODE_MASTER;
  drv->spi.Init.Direction = SPI_DIRECTION_2LINES;
  drv->spi.Init.DataSize = SPI_DATASIZE_8BIT;
  drv->spi.Init.CLKPolarity = SPI_POLARITY_LOW;
  drv->spi.Init.CLKPhase = SPI_PHASE_1EDGE;
  drv->spi.Init.NSS = SPI_NSS_HARD_OUTPUT;
  drv->spi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;
  drv->spi.Init.FirstBit = SPI_FIRSTBIT_MSB;
  drv->spi.Init.TIMode = SPI_TIMODE_DISABLE;
  drv->spi.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  drv->spi.Init.CRCPolynomial = 0;

  HAL_SPI_Init(&drv->spi);

  drv->initialized = true;

  return LT_OK;
}

lt_ret_t lt_port_deinit(lt_l2_state_t *s2) {
  tropic01_hal_driver_t *drv = &g_tropic01_hal_driver;

  if (drv->spi.Instance != NULL) {
    HAL_SPI_DeInit(&drv->spi);
  }

  TROPIC01_SPI_FORCE_RESET();
  TROPIC01_SPI_RELEASE_RESET();
  TROPIC01_SPI_CLK_DIS();

  HAL_GPIO_DeInit(TROPIC01_INT_PORT, TROPIC01_INT_PIN);
  HAL_GPIO_DeInit(TROPIC01_SPI_NSS_PORT, TROPIC01_SPI_NSS_PIN);
  HAL_GPIO_DeInit(TROPIC01_SPI_SCK_PORT, TROPIC01_SPI_SCK_PIN);
  HAL_GPIO_DeInit(TROPIC01_SPI_MISO_PORT, TROPIC01_SPI_MISO_PIN);
  HAL_GPIO_DeInit(TROPIC01_SPI_MOSI_PORT, TROPIC01_SPI_MOSI_PIN);
  HAL_GPIO_DeInit(TROPIC01_PWR_PORT, TROPIC01_PWR_PIN);

  drv->initialized = false;

  return LT_OK;
}

lt_ret_t lt_port_spi_csn_low(lt_l2_state_t *s2) {
  UNUSED(s2);

  HAL_GPIO_WritePin(TROPIC01_SPI_NSS_PORT, TROPIC01_SPI_NSS_PIN,
                    GPIO_PIN_RESET);

  return LT_OK;
}

lt_ret_t lt_port_spi_csn_high(lt_l2_state_t *s2) {
  UNUSED(s2);

  HAL_GPIO_WritePin(TROPIC01_SPI_NSS_PORT, TROPIC01_SPI_NSS_PIN, GPIO_PIN_SET);

  return LT_OK;
}

lt_ret_t lt_port_spi_transfer(lt_l2_state_t *s2, uint8_t offset,
                              uint16_t tx_len, uint32_t timeout_ms) {
  tropic01_hal_driver_t *drv = &g_tropic01_hal_driver;

  if (offset + tx_len > TR01_L1_LEN_MAX) {
    return LT_L1_DATA_LEN_ERROR;
  }
  int ret = HAL_SPI_TransmitReceive(&drv->spi, s2->buff + offset,
                                    s2->buff + offset, tx_len, timeout_ms);
  if (ret != HAL_OK) {
    return LT_FAIL;
  }

  return LT_OK;
}

lt_ret_t lt_port_delay(lt_l2_state_t *s2, uint32_t ms) {
  UNUSED(s2);

  systick_delay_ms(ms);

  if (ui_progress != NULL) {
    ui_progress();
  }

  return LT_OK;
}

lt_ret_t lt_port_random_bytes(lt_l2_state_t *s2, void *buff, size_t count) {
  (void)s2;

  rng_fill_buffer((uint8_t *)buff, count);

  return LT_OK;
}

void lt_secure_memzero(void *const ptr, const size_t count) {
  memzero(ptr, count);
}

#endif
