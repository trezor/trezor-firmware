#include STM32_HAL_H

static RNG_HandleTypeDef rng_handle = {
    .State = HAL_RNG_STATE_RESET,
    .Instance = RNG,
};

void rng_init(RNG_HandleTypeDef *rng) {

    // Enable RNG clock
    __HAL_RCC_RNG_CLK_ENABLE();

    // Init RNG handle
    HAL_RNG_Init(rng);
}

uint32_t rng_get(void) {
    if (rng_handle.State == HAL_RNG_STATE_RESET) {
        rng_init(&rng_handle);
    }

    return HAL_RNG_GetRandomNumber(&rng_handle);
}
