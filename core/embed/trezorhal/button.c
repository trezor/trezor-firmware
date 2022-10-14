#include STM32_HAL_H
#include "button.h"
#include TREZOR_BOARD

static char last_left = 0, last_right = 0;

void button_init(void) {
  BTN_LEFT_CLK_ENA();
  BTN_RIGHT_CLK_ENA();

  GPIO_InitTypeDef GPIO_InitStructure;

  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = BTN_LEFT_PIN;
  HAL_GPIO_Init(BTN_LEFT_PORT, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = BTN_RIGHT_PIN;
  HAL_GPIO_Init(BTN_RIGHT_PORT, &GPIO_InitStructure);
}

uint32_t button_read(void) {
  char left = (GPIO_PIN_RESET == HAL_GPIO_ReadPin(BTN_LEFT_PORT, BTN_LEFT_PIN));
  char right =
      (GPIO_PIN_RESET == HAL_GPIO_ReadPin(BTN_RIGHT_PORT, BTN_RIGHT_PIN));
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

char button_state_left(void) { return last_left; }

char button_state_right(void) { return last_right; }
