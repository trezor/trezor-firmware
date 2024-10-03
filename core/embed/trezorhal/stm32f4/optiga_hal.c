#include "optiga_hal.h"
#include "common.h"
#include TREZOR_BOARD
#include STM32_HAL_H

#ifdef KERNEL_MODE

void optiga_hal_init(void) {
  OPTIGA_RST_CLK_EN();
  // init reset pin
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = OPTIGA_RST_PIN;
  HAL_GPIO_Init(OPTIGA_RST_PORT, &GPIO_InitStructure);
  // perform reset on every initialization
  HAL_GPIO_WritePin(OPTIGA_RST_PORT, OPTIGA_RST_PIN, GPIO_PIN_RESET);
  hal_delay(10);
  HAL_GPIO_WritePin(OPTIGA_RST_PORT, OPTIGA_RST_PIN, GPIO_PIN_SET);
  // warm reset startup time min 15ms
  hal_delay(20);
}

void optiga_reset(void) {
  HAL_GPIO_WritePin(OPTIGA_RST_PORT, OPTIGA_RST_PIN, GPIO_PIN_RESET);
  hal_delay(10);
  HAL_GPIO_WritePin(OPTIGA_RST_PORT, OPTIGA_RST_PIN, GPIO_PIN_SET);
  // warm reset startup time min 15ms
  hal_delay(20);
}

#endif  // KERNEL_MODE
