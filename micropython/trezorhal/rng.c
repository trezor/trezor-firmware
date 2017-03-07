#include STM32_HAL_H

static RNG_HandleTypeDef rng_handle = {
    .State = HAL_RNG_STATE_RESET,
    .Instance = RNG,
};

int rng_init(void) {
    __HAL_RCC_RNG_CLK_ENABLE();
    HAL_RNG_Init(&rng_handle);
    return 0;
}

uint32_t rng_get(void) {
    return HAL_RNG_GetRandomNumber(&rng_handle);
}
