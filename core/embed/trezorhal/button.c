#include STM32_HAL_H
#include "button.h"

#define BTN_PIN_LEFT GPIO_PIN_5
#define BTN_PIN_RIGHT GPIO_PIN_2

void button_init(void) {
  __HAL_RCC_GPIOC_CLK_ENABLE();

  GPIO_InitTypeDef GPIO_InitStructure;

  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = BTN_PIN_LEFT | BTN_PIN_RIGHT;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);
}

uint32_t button_read(void) {
  static char last_left = 0, last_right = 0;
  char left = (GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOC, BTN_PIN_LEFT));
  char right = (GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOC, BTN_PIN_RIGHT));
  if (last_left != left) {
    last_left = left;
    if (left) {
      return BTN_EVT_DOWN | BTN_LEFT;
    } else {
      return BTN_EVT_UP | BTN_LEFT;
    }
  }
  if (last_right != right) {
    last_right = right;
    if (right) {
      return BTN_EVT_DOWN | BTN_RIGHT;
    } else {
      return BTN_EVT_UP | BTN_RIGHT;
    }
  }
  return 0;
}
