#include STM32_HAL_H

int flash_init(void) {
    // Enable the flash IRQ, which is used to also call our storage IRQ handler
    // It needs to go at a higher priority than all those components that rely on
    // the flash storage (eg higher than USB MSC).
    HAL_NVIC_SetPriority(FLASH_IRQn, 2, 0);
    HAL_NVIC_EnableIRQ(FLASH_IRQn);

    return 0;
}
