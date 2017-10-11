#include STM32_HAL_H

#include "pendsv.h"
#include "rng.h"

const uint8_t AHBPrescTable[16] = {0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 6, 7, 8, 9};
const uint8_t APBPrescTable[8] = {0, 0, 0, 0, 1, 2, 3, 4};

uint32_t SystemCoreClock = 168000000;

void SystemInit(void)
{
    // set flash wait states for an increasing HCLK frequency -- reference RM0090 section 3.5.1
    FLASH->ACR = FLASH_ACR_LATENCY_5WS;
    // configure main PLL; assumes HSE is 8 MHz; this should evaluate to 0x27402a04 -- reference RM0090 section 7.3.2
    RCC->PLLCFGR = (RCC_PLLCFGR_RST_VALUE & ~RCC_PLLCFGR_PLLQ & ~RCC_PLLCFGR_PLLSRC & ~RCC_PLLCFGR_PLLP & ~RCC_PLLCFGR_PLLN & ~RCC_PLLCFGR_PLLM)
                   | (7 << RCC_PLLCFGR_PLLQ_Pos)   // Q = 7
                   | RCC_PLLCFGR_PLLSRC_HSE        // PLLSRC = HSE
                   | (0 << RCC_PLLCFGR_PLLP_Pos)   // P = 2 (two bits, 00 means PLLP = 2)
                   | (168 << RCC_PLLCFGR_PLLN_Pos) // N = 168
                   | (4 << RCC_PLLCFGR_PLLM_Pos);  // M = 4
    // enable clock security system, HSE clock, and main PLL
    RCC->CR |= RCC_CR_CSSON | RCC_CR_HSEON | RCC_CR_PLLON;
    // wait until PLL and HSE ready
    while((RCC->CR & (RCC_CR_PLLRDY | RCC_CR_HSERDY)) != (RCC_CR_PLLRDY | RCC_CR_HSERDY));
    // APB2=2, APB1=4, AHB=1, system clock = main PLL
    RCC->CFGR = RCC_CFGR_PPRE2_DIV2 | RCC_CFGR_PPRE1_DIV4 | RCC_CFGR_HPRE_DIV1 | RCC_CFGR_SW_PLL;
    // wait until PLL is system clock
    while((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL);
    // turn off the HSI as it is now unused (it will be turned on again automatically if a clock security failure occurs)
    RCC->CR &= ~RCC_CR_HSION;
    // init the TRNG peripheral
    rng_init();
    // enable full access to the fpu coprocessor
    #if (__FPU_PRESENT == 1) && (__FPU_USED == 1)
        SCB->CPACR |= ((3UL << 10*2)|(3UL << 11*2));  /* set CP10 and CP11 Full Access */
    #endif
}

void PendSV_Handler(void) {
    pendsv_isr_handler();
}

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

    // Right now we have the storage and DMA controllers to process during
    // this interrupt and we use custom dispatch handlers.  If this needs to
    // be generalised in the future then a dispatch table can be used as
    // follows: ((void(*)(void))(systick_dispatch[uwTick & 0xf]))();

    // if (STORAGE_IDLE_TICK(uwTick)) {
    //     NVIC->STIR = FLASH_IRQn;
    // }

    // if (DMA_IDLE_ENABLED() && DMA_IDLE_TICK(uwTick)) {
    //     dma_idle_handler(uwTick);
    // }
}

