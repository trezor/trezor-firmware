#include STM32_HAL_H
#include "button.h"

#if defined TREZOR_MODEL_1
#define BTN_LEFT_PIN GPIO_PIN_5
#define BTN_LEFT_PORT GPIOC
#define BTN_LEFT_CLK_ENA __HAL_RCC_GPIOC_CLK_ENABLE
#define BTN_RIGHT_PIN GPIO_PIN_2
#define BTN_RIGHT_PORT GPIOC
#define BTN_RIGHT_CLK_ENA __HAL_RCC_GPIOC_CLK_ENABLE
#elif defined TREZOR_MODEL_R
#define BTN_LEFT_PIN GPIO_PIN_0
#define BTN_LEFT_PORT GPIOA
#define BTN_LEFT_CLK_ENA __HAL_RCC_GPIOA_CLK_ENABLE
#define BTN_RIGHT_PIN GPIO_PIN_15
#define BTN_RIGHT_PORT GPIOE
#define BTN_RIGHT_CLK_ENA __HAL_RCC_GPIOE_CLK_ENABLE
#else
#error Unknown Trezor model
#endif


#define DELAY_PRESSED 20
#define DELAY_RELEASED 50

#define DELAY_BOTH_PRESSED 0  //must be zero for proper function
#define DELAY_BOTH_RELEASED 100



extern __IO uint32_t uwTick;

typedef enum {
    BUTTON_RELEASED = 0,
    BUTTON_PRESSED_WAIT,
    BUTTON_PRESSED,
    BUTTON_RELEASED_WAIT,
}button_state_t;

typedef struct {
    button_state_t state;
    uint32_t ticks;
    uint32_t event;
    uint32_t wait_pressed;
    uint32_t wait_released;
}button_t;


static button_t btn_left = {BUTTON_RELEASED, 0, BTN_LEFT, DELAY_PRESSED, DELAY_RELEASED};
static button_t btn_right = {BUTTON_RELEASED, 0, BTN_RIGHT, DELAY_PRESSED, DELAY_RELEASED};
static button_t btn_both = {BUTTON_RELEASED, 0, BTN_BOTH, DELAY_BOTH_PRESSED, DELAY_BOTH_RELEASED};



uint32_t process_button(button_t * btn, bool act) {
  uint32_t event = 0;

  uint32_t diff_ticks = 0;

  if (uwTick > btn->ticks) {
    diff_ticks = uwTick - btn->ticks;
  } else {
    diff_ticks = btn->ticks - uwTick;
  }

  switch (btn->state) {
    case BUTTON_RELEASED:
      if (act) {
        if (btn->wait_pressed != 0) {
          btn->state = BUTTON_PRESSED_WAIT;
          btn->ticks = uwTick;
        } else {
          event = btn->event | BTN_EVT_DOWN;
          btn->state = BUTTON_PRESSED;
        }
      }
      break;
    case BUTTON_PRESSED_WAIT:
      if (!act) {
        btn->state = BUTTON_RELEASED;
      } else {
        if (diff_ticks > btn->wait_pressed) {
          event = btn->event | BTN_EVT_DOWN;
          btn->state = BUTTON_PRESSED;
        }
      }
      break;
    case BUTTON_PRESSED:
      if (!act) {
        if (btn->wait_released != 0) {
          btn->state = BUTTON_RELEASED_WAIT;
          btn->ticks = uwTick;
        } else {
          event = btn->event | BTN_EVT_UP;
          btn->state = BUTTON_RELEASED;
        }
      }
      break;
    case BUTTON_RELEASED_WAIT:
      if (act) {
        btn->state = BUTTON_PRESSED;
      } else {
        if (diff_ticks > btn->wait_released) {
          event = btn->event | BTN_EVT_UP;
          btn->state = BUTTON_RELEASED;
        }
      }
      break;
    default:
      break;
  }

  return event;
}



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
  uint32_t event = 0;

  bool left_act = GPIO_PIN_RESET == HAL_GPIO_ReadPin(BTN_LEFT_PORT, BTN_LEFT_PIN);
  bool right_act = GPIO_PIN_RESET == HAL_GPIO_ReadPin(BTN_RIGHT_PORT, BTN_RIGHT_PIN);

  if (btn_both.state == BUTTON_RELEASED) {
    event = process_button(&btn_left, left_act);
    if (event != 0) {
      return event;
    }
    event = process_button(&btn_right,right_act);
    if (event != 0) {
      return event;
    }

    // enter pressed wait state on both buttons, stop evaluating single buttons
//    if (btn_left.state == BUTTON_PRESSED_WAIT && btn_right.state == BUTTON_PRESSED_WAIT) {
//      process_button(&btn_both, left_act && right_act);
//    }
    if (btn_left.state != BUTTON_RELEASED && btn_right.state != BUTTON_RELEASED) {
      event = process_button(&btn_both, true);
      btn_left.state = BUTTON_RELEASED;
      btn_right.state = BUTTON_RELEASED;

      if (event != 0) {
        return event;
      }
    }
  }
  else {
    event = process_button(&btn_both, left_act || right_act);
    if (btn_both.state == BUTTON_RELEASED) {
      btn_left.state = BUTTON_RELEASED;
      btn_right.state = BUTTON_RELEASED;
    }
  }

  return event;
}

bool button_state_left(void) { return (btn_left.state == BUTTON_PRESSED || btn_left.state == BUTTON_RELEASED_WAIT); }

bool button_state_right(void) { return (btn_right.state == BUTTON_PRESSED || btn_right.state == BUTTON_RELEASED_WAIT); }

bool button_state_both(void) { return (btn_both.state == BUTTON_PRESSED || btn_both.state == BUTTON_RELEASED_WAIT); }
