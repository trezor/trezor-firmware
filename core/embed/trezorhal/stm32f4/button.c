
#include "stdbool.h"

#include STM32_HAL_H
#include "button.h"

static void init_btn(GPIO_TypeDef *port, uint16_t pin) {
  GPIO_InitTypeDef GPIO_InitStructure;

  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = pin;
  HAL_GPIO_Init(port, &GPIO_InitStructure);
}

#ifdef BTN_LEFT_CLK_ENA
static bool last_left = 0;
bool button_state_left(void) { return last_left; }
#endif

#ifdef BTN_RIGHT_CLK_ENA
static bool last_right = 0;
bool button_state_right(void) { return last_right; }
#endif

#ifdef BTN_POWER_CLK_ENA
static bool last_power = 0;
bool button_state_power(void) { return last_power; }
#endif

void button_init(void) {
#ifdef BTN_LEFT_CLK_ENA
  BTN_LEFT_CLK_ENA();
  init_btn(BTN_LEFT_PORT, BTN_LEFT_PIN);
#endif

#ifdef BTN_RIGHT_CLK_ENA
  BTN_RIGHT_CLK_ENA();
  init_btn(BTN_RIGHT_PORT, BTN_RIGHT_PIN);
#endif

#ifdef BTN_POWER_CLK_ENA
  BTN_POWER_CLK_ENA();
  init_btn(BTN_POWER_PORT, BTN_POWER_PIN);
#endif
}

uint32_t button_read(void) {
#ifdef BTN_LEFT_CLK_ENA
  bool left = (GPIO_PIN_RESET == HAL_GPIO_ReadPin(BTN_LEFT_PORT, BTN_LEFT_PIN));
  if (last_left != left) {
    last_left = left;
    if (left) {
      return BTN_EVT_DOWN | BTN_LEFT;
    } else {
      return BTN_EVT_UP | BTN_LEFT;
    }
  }
#endif
#ifdef BTN_RIGHT_CLK_ENA
  bool right =
      (GPIO_PIN_RESET == HAL_GPIO_ReadPin(BTN_RIGHT_PORT, BTN_RIGHT_PIN));
  if (last_right != right) {
    last_right = right;
    if (right) {
      return BTN_EVT_DOWN | BTN_RIGHT;
    } else {
      return BTN_EVT_UP | BTN_RIGHT;
    }
  }
#endif
#ifdef BTN_POWER_CLK_ENA
  bool power =
      (GPIO_PIN_RESET == HAL_GPIO_ReadPin(BTN_POWER_PORT, BTN_POWER_PIN));
  if (last_power != power) {
    last_power = power;
    if (power) {
      return BTN_EVT_DOWN | BTN_POWER;
    } else {
      return BTN_EVT_UP | BTN_POWER;
    }
  }
#endif

  return 0;
}
