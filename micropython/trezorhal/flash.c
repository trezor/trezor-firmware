#include STM32_HAL_H

int flash_init(void) {
    // Enable the flash IRQ, which is used to also call our storage IRQ handler
    // It needs to go at a higher priority than all those components that rely on
    // the flash storage (eg higher than USB MSC).
    HAL_NVIC_SetPriority(FLASH_IRQn, 2, 0);
    HAL_NVIC_EnableIRQ(FLASH_IRQn);

    return 0;
}

void FLASH_IRQHandler(void) {
    // This calls the real flash IRQ handler, if needed
    /*
    uint32_t flash_cr = FLASH->CR;
    if ((flash_cr & FLASH_IT_EOP) || (flash_cr & FLASH_IT_ERR)) {
        HAL_FLASH_IRQHandler();
    }
    */
    // This call the storage IRQ handler, to check if the flash cache needs flushing
    // storage_irq_handler();
}
