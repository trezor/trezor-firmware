#include "optiga_hal.h"
#include "common.h"
#include TREZOR_BOARD

void optiga_hal_init(void) {
  // init reset pin
  GPIO_InitTypeDef GPIO_InitStructure;
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = GPIO_PIN_9;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
  // perform reset on every initialization
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_9, GPIO_PIN_RESET);
  hal_delay(10);
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_9, GPIO_PIN_SET);
  // warm reset startup time min 15ms
  hal_delay(20);
}

void optiga_reset(void) {
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_9, GPIO_PIN_RESET);
  hal_delay(10);
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_9, GPIO_PIN_SET);
  // warm reset startup time min 15ms
  hal_delay(20);
}
