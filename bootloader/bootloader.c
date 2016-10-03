#include STM32_HAL_H

#include "display.h"
#include "bootloader_ui.h"

// ### from main.c

void flash_error(int n) {
    for (int i = 0; i < n; i++) {
        // blink(on)
        HAL_Delay(250);
        // blink(off)
        HAL_Delay(250);
    }
}

void __attribute__((noreturn)) __fatal_error(const char *msg) {
    for (volatile uint32_t delay = 0; delay < 10000000; delay++) {
    }
    // TODO: printf("FATAL ERROR: %s\n", msg);
    for (;;) {
        __WFI();
    }
}

void nlr_jump_fail(void *val) {
    __fatal_error("FATAL: uncaught exception");
}

void SystemClock_Config(void);

// ### from stm32_it.c

/**
  * @brief  This function handles SysTick Handler.
  * @param  None
  * @retval None
  */
void SysTick_Handler(void) {
    // Instead of calling HAL_IncTick we do the increment here of the counter.
    // This is purely for efficiency, since SysTick is called 1000 times per
    // second at the highest interrupt priority.
    // Note: we don't need uwTick to be declared volatile here because this is
    // the only place where it can be modified, and the code is more efficient
    // without the volatile specifier.
    extern uint32_t uwTick;
    uwTick += 1;

    // Read the systick control regster. This has the side effect of clearing
    // the COUNTFLAG bit, which makes the logic in sys_tick_get_microseconds
    // work properly.
    SysTick->CTRL;

#if 0
    // Right now we have the storage and DMA controllers to process during
    // this interrupt and we use custom dispatch handlers.  If this needs to
    // be generalised in the future then a dispatch table can be used as
    // follows: ((void(*)(void))(systick_dispatch[uwTick & 0xf]))();

    if (STORAGE_IDLE_TICK(uwTick)) {
        NVIC->STIR = FLASH_IRQn;
    }

    if (DMA_IDLE_ENABLED() && DMA_IDLE_TICK(uwTick)) {
        dma_idle_handler(uwTick);
    }
#endif
}

// ###

int main(void) {

    HAL_Init();

    SystemClock_Config();

    __GPIOA_CLK_ENABLE();
    __GPIOB_CLK_ENABLE();
    __GPIOC_CLK_ENABLE();
    __GPIOD_CLK_ENABLE();

    display_init();
    display_clear();

    screen_welcome();

    for (;;) {
        display_backlight(255);
        HAL_Delay(250);
        display_backlight(0);
        HAL_Delay(250);
    }

    __fatal_error("end");

    return 0;
}
