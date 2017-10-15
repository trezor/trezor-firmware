#include STM32_HAL_H

#include "rng.h"

const uint8_t AHBPrescTable[16] = {0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 6, 7, 8, 9};
const uint8_t APBPrescTable[8] = {0, 0, 0, 0, 1, 2, 3, 4};

uint32_t SystemCoreClock = 168000000U;

#pragma GCC optimize("no-stack-protector") // applies to all functions in this file

void SystemInit(void)
{
    // set flash wait states for an increasing HCLK frequency -- reference RM0090 section 3.5.1
    FLASH->ACR = FLASH_ACR_LATENCY_5WS;
    // wait until the new wait state config takes effect -- per section 3.5.1 guidance
    while ((FLASH->ACR & FLASH_ACR_LATENCY) != FLASH_ACR_LATENCY_5WS);
    // configure main PLL; assumes HSE is 8 MHz; this should evaluate to 0x27402a04 -- reference RM0090 section 7.3.2
    RCC->PLLCFGR = (RCC_PLLCFGR_RST_VALUE & ~RCC_PLLCFGR_PLLQ & ~RCC_PLLCFGR_PLLSRC & ~RCC_PLLCFGR_PLLP & ~RCC_PLLCFGR_PLLN & ~RCC_PLLCFGR_PLLM)
                   | (7U << RCC_PLLCFGR_PLLQ_Pos)   // Q = 7
                   | RCC_PLLCFGR_PLLSRC_HSE        // PLLSRC = HSE
                   | (0U << RCC_PLLCFGR_PLLP_Pos)   // P = 2 (two bits, 00 means PLLP = 2)
                   | (168U << RCC_PLLCFGR_PLLN_Pos) // N = 168
                   | (4U << RCC_PLLCFGR_PLLM_Pos);  // M = 4
    // enable clock security system, HSE clock, and main PLL
    RCC->CR |= RCC_CR_CSSON | RCC_CR_HSEON | RCC_CR_PLLON;
    // wait until PLL and HSE ready
    while((RCC->CR & (RCC_CR_PLLRDY | RCC_CR_HSERDY)) != (RCC_CR_PLLRDY | RCC_CR_HSERDY));
    // APB2=2, APB1=4, AHB=1, system clock = main PLL
    const uint32_t cfgr = RCC_CFGR_PPRE2_DIV2 | RCC_CFGR_PPRE1_DIV4 | RCC_CFGR_HPRE_DIV1 | RCC_CFGR_SW_PLL;
    RCC->CFGR = cfgr;
    // wait until PLL is system clock and also verify that the pre-scalers were set
    while(RCC->CFGR != (RCC_CFGR_SWS_PLL | cfgr));
    // turn off the HSI as it is now unused (it will be turned on again automatically if a clock security failure occurs)
    RCC->CR &= ~RCC_CR_HSION;
    // wait until ths HSI is off
    while((RCC->CR & RCC_CR_HSION) == RCC_CR_HSION);
    // init the TRNG peripheral
    rng_init();
    // set CP10 and CP11 to enable full access to the fpu coprocessor; ARMv7-M Architecture Reference Manual section B3.2.20
    SCB->CPACR |= ((3U << 22) | (3U << 20));
}

volatile uint32_t uwTick = 0;

void SysTick_Handler(void)
{
    // this is a millisecond tick counter that wraps after approximately
    // 49.71 days = (0xffffffff / (24 * 60 * 60 * 1000))
    uwTick++;
}
