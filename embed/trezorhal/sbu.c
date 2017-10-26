/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include STM32_HAL_H

#include "sbu.h"

void sbu_init(void) {
    GPIO_InitTypeDef GPIO_InitStructure;

    // SBU1/PA2 SBU2/PA3
    GPIO_InitStructure.Pin = GPIO_PIN_2 | GPIO_PIN_3;
    GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStructure.Pull = GPIO_NOPULL;
    GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_2, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, GPIO_PIN_RESET);
}

void sbu_set(secbool sbu1, secbool sbu2) {
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_2, sbu1 == sectrue ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, sbu2 == sectrue ? GPIO_PIN_SET : GPIO_PIN_RESET);
}
