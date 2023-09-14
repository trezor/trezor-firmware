#ifndef _TREZOR_R_V3_H
#define _TREZOR_R_V3_H

#define HSE_8MHZ

#define USE_BUTTON 1
#define USE_SBU 1

#include "displays/ug-2828tswig01.h"

#define BTN_LEFT_PIN GPIO_PIN_0
#define BTN_LEFT_PORT GPIOA
#define BTN_LEFT_CLK_ENA __HAL_RCC_GPIOA_CLK_ENABLE
#define BTN_RIGHT_PIN GPIO_PIN_15
#define BTN_RIGHT_PORT GPIOE
#define BTN_RIGHT_CLK_ENA __HAL_RCC_GPIOE_CLK_ENABLE

#endif  //_TREZOR_R_V3_H
