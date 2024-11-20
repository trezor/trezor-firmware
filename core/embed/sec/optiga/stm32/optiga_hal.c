#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sec/optiga_hal.h>
#include <sys/systick.h>

#ifdef KERNEL_MODE

void optiga_hal_init(void) {
  GPIO_InitTypeDef GPIO_InitStructure = {0};

  OPTIGA_RST_CLK_EN();
  // init reset pin
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = OPTIGA_RST_PIN;
  HAL_GPIO_Init(OPTIGA_RST_PORT, &GPIO_InitStructure);

#ifdef OPTIGA_PWR_PIN
  OPTIGA_PWR_CLK_EN();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = OPTIGA_PWR_PIN;
  HAL_GPIO_Init(OPTIGA_PWR_PORT, &GPIO_InitStructure);
  HAL_GPIO_WritePin(OPTIGA_PWR_PORT, OPTIGA_PWR_PIN, GPIO_PIN_RESET);
  hal_delay(10);
#endif

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
