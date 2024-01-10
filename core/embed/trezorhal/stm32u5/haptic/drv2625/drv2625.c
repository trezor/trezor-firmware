#include "drv2625_lib.h"
#include "haptic.h"

#include <stdbool.h>

#include STM32_HAL_H

#include "i2c.h"
#include TREZOR_BOARD
#include HAPTIC_ACTUATOR

#define DRV2625_I2C_ADDRESS (0x5A << 1)

#define DRV2625_REG_CHIPID 0x00
#define DRV2625_REG_STATUS 0x01
#define DRV2625_REG_MODE 0x07
#define DRV2625_REG_MODE_RTP 0
#define DRV2625_REG_MODE_WAVEFORM 0x01
#define DRV2625_REG_MODE_DIAG 0x02
#define DRV2625_REG_MODE_AUTOCAL 0x03
#define DRV2625_REG_MODE_TRGFUNC_PULSE 0x00
#define DRV2625_REG_MODE_TRGFUNC_ENABLE 0x04
#define DRV2625_REG_MODE_TRGFUNC_INTERRUPT 0x08

#define DRV2625_REG_LRAERM 0x08
#define DRV2625_REG_LRAERM_LRA 0x80
#define DRV2625_REG_LRAERM_OPENLOOP 0x40
#define DRV2625_REG_LRAERM_AUTO_BRK_OL 0x10
#define DRV2625_REG_LRAERM_AUTO_BRK_STBY 0x08

#define DRV2625_REG_LIBRARY 0x0D  ///< Waveform library selection register
#define DRV2625_REG_LIBRARY_OPENLOOP 0x40
#define DRV2625_REG_LIBRARY_GAIN_100 0x00
#define DRV2625_REG_LIBRARY_GAIN_75 0x01
#define DRV2625_REG_LIBRARY_GAIN_50 0x02
#define DRV2625_REG_LIBRARY_GAIN_25 0x03

#define DRV2625_REG_RTP 0x0E  ///< RTP input register

#define DRV2625_REG_WAVESEQ1 0x0F  ///< Waveform sequence register 1
#define DRV2625_REG_WAVESEQ2 0x10  ///< Waveform sequence register 2
#define DRV2625_REG_WAVESEQ3 0x11  ///< Waveform sequence register 3
#define DRV2625_REG_WAVESEQ4 0x12  ///< Waveform sequence register 4
#define DRV2625_REG_WAVESEQ5 0x13  ///< Waveform sequence register 5
#define DRV2625_REG_WAVESEQ6 0x14  ///< Waveform sequence register 6
#define DRV2625_REG_WAVESEQ7 0x15  ///< Waveform sequence register 7
#define DRV2625_REG_WAVESEQ8 0x16  ///< Waveform sequence register 8

#define DRV2625_REG_GO 0x0C  ///< Go register
#define DRV2625_REG_GO_GO 0x01

#define DRV2625_REG_OD_CLAMP 0x20

#define DRV2625_REG_LRA_WAVE_SHAPE 0x2C
#define DRV2625_REG_LRA_WAVE_SHAPE_SINE 0x01

#define DRV2625_REG_OL_LRA_PERIOD_LO 0x2F
#define DRV2625_REG_OL_LRA_PERIOD_HI 0x2E

#if defined ACTUATOR_CLOSED_LOOP
#define LIB_SEL 0x00
#define LOOP_SEL 0x00
#elif defined ACTUATOR_OPEN_LOOP
#define LIB_SEL DRV2625_REG_LIBRARY_OPENLOOP
#define LOOP_SEL DRV2625_REG_LRAERM_OPENLOOP
#else
#error "Must define either CLOSED_LOOP or OPEN_LOOP"
#endif

#if defined ACTUATOR_LRA
#define LRA_ERM_SEL DRV2625_REG_LRAERM_LRA
#elif defined ACTUATOR_ERM
#define LRA_ERM_SEL 0x00
#else
#error "Must define either LRA or ERM"
#endif

#define PRESS_EFFECT_AMPLITUDE 25
#define PRESS_EFFECT_DURATION 10

#define PRODTEST_EFFECT_AMPLITUDE 127

static bool set_reg(uint8_t addr, uint8_t value) {
  uint8_t data[] = {addr, value};
  return i2c_transmit(DRV2625_I2C_INSTANCE, DRV2625_I2C_ADDRESS, data,
                      sizeof(data), 1) == HAL_OK;
}

void haptic_calibrate(void) {
  set_reg(DRV2625_REG_MODE, DRV2625_REG_MODE_AUTOCAL);
  HAL_Delay(1);
  set_reg(DRV2625_REG_GO, DRV2625_REG_GO_GO);

  HAL_Delay(3000);
}

void haptic_init(void) {
  // select library
  set_reg(DRV2625_REG_LIBRARY, LIB_SEL | DRV2625_REG_LIBRARY_GAIN_25);
  set_reg(DRV2625_REG_LRAERM,
          LRA_ERM_SEL | LOOP_SEL | DRV2625_REG_LRAERM_AUTO_BRK_OL);

  set_reg(DRV2625_REG_OD_CLAMP, ACTUATOR_OD_CLAMP);

  set_reg(DRV2625_REG_LRA_WAVE_SHAPE, DRV2625_REG_LRA_WAVE_SHAPE_SINE);

  set_reg(DRV2625_REG_OL_LRA_PERIOD_LO, ACTUATOR_LRA_PERIOD & 0xFF);
  set_reg(DRV2625_REG_OL_LRA_PERIOD_HI, ACTUATOR_LRA_PERIOD >> 8);

  GPIO_InitTypeDef GPIO_InitStructure;
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = GPIO_PIN_8;
  GPIO_InitStructure.Alternate = GPIO_AF14_TIM16;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

  TIM_HandleTypeDef TIM_Handle;
  __HAL_RCC_TIM16_CLK_ENABLE();
  TIM_Handle.State = HAL_TIM_STATE_RESET;
  TIM_Handle.Instance = TIM16;
  TIM_Handle.Init.Period = 0;
  TIM_Handle.Init.Prescaler = SystemCoreClock / 10000;
  TIM_Handle.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  TIM_Handle.Init.CounterMode = TIM_COUNTERMODE_UP;
  TIM_Handle.Init.RepetitionCounter = 0;
  HAL_TIM_PWM_Init(&TIM_Handle);

  TIM_OC_InitTypeDef TIM_OC_InitStructure;
  TIM_OC_InitStructure.OCMode = TIM_OCMODE_PWM2;
  TIM_OC_InitStructure.OCPolarity = TIM_OCPOLARITY_HIGH;
  TIM_OC_InitStructure.Pulse = 1;
  TIM_OC_InitStructure.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  TIM_OC_InitStructure.OCFastMode = TIM_OCFAST_DISABLE;
  HAL_TIM_PWM_ConfigChannel(&TIM_Handle, &TIM_OC_InitStructure, TIM_CHANNEL_1);

  HAL_TIM_OC_Start(&TIM_Handle, TIM_CHANNEL_1);

  TIM16->CR1 |= TIM_CR1_OPM;
  TIM16->BDTR |= TIM_BDTR_MOE;
}

static bool haptic_play_RTP(int8_t amplitude, uint16_t duration_ms) {
  if (!set_reg(DRV2625_REG_MODE,
               DRV2625_REG_MODE_RTP | DRV2625_REG_MODE_TRGFUNC_ENABLE)) {
    return false;
  }

  if (!set_reg(DRV2625_REG_RTP, (uint8_t)amplitude)) {
    return false;
  }

  if (duration_ms > 6500) {
    duration_ms = 6500;
  }
  if (duration_ms == 0) {
    return true;
  }

  TIM16->CNT = 1;
  TIM16->CCR1 = 1;
  TIM16->ARR = duration_ms * 10;
  TIM16->CR1 |= TIM_CR1_CEN;

  return true;
}

static void haptic_play_lib(drv2625_lib_effect_t effect) {
  set_reg(DRV2625_REG_MODE, DRV2625_REG_MODE_WAVEFORM);
  set_reg(DRV2625_REG_WAVESEQ1, effect);
  set_reg(DRV2625_REG_WAVESEQ2, 0);
  set_reg(DRV2625_REG_GO, DRV2625_REG_GO_GO);
}

void haptic_play(haptic_effect_t effect) {
  switch (effect) {
    case HAPTIC_BUTTON_PRESS:
      haptic_play_RTP(PRESS_EFFECT_AMPLITUDE, PRESS_EFFECT_DURATION);
      break;
    case HAPTIC_ALERT:
      haptic_play_lib(ALERT_750MS_100);
      break;
    case HAPTIC_HOLD_TO_CONFIRM:
      haptic_play_lib(TRANSITION_RAMP_UP_SHORT_SMOOTH_1);
      break;
    default:
      break;
  }
}

bool haptic_test(uint16_t duration_ms) {
  return haptic_play_RTP(PRODTEST_EFFECT_AMPLITUDE, duration_ms);
}
