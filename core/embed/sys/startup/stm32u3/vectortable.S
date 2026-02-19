 .syntax unified

 .text

#ifdef KERNEL_MODE

  .global default_handler
  .type default_handler, STT_FUNC
default_handler:
  b Default_IRQHandler

  .macro add_handler symbol_name:req
    .word \symbol_name
    .weak \symbol_name
    .thumb_set \symbol_name, default_handler
  .endm

  // Reference:
  // STM32U385xx IRQ order from vendor/cmsis_device_u3/Include/stm32u385xx.h
  .section .vector_table, "a"
vector_table:
  .word _stack_section_end // defined in linker script
  add_handler reset_handler
    add_handler NMI_Handler
    add_handler HardFault_Handler
    add_handler MemManage_Handler
    add_handler BusFault_Handler
    add_handler UsageFault_Handler
    add_handler SecureFault_Handler
    add_handler architecture_reserved_handler
    add_handler architecture_reserved_handler
    add_handler architecture_reserved_handler
    add_handler SVC_Handler
    add_handler DebugMon_Handler
    add_handler architecture_reserved_handler
    add_handler PendSV_Handler
    add_handler SysTick_Handler

    // External interrupts (STM32U3xx specific)
    add_handler WWDG_IRQHandler
    add_handler PVD_PVM_IRQHandler
    add_handler RTC_IRQHandler
    add_handler RTC_S_IRQHandler
    add_handler TAMP_IRQHandler
    add_handler RAMCFG_IRQHandler
    add_handler FLASH_IRQHandler
    add_handler FLASH_S_IRQHandler
    add_handler GTZC_IRQHandler
    add_handler RCC_IRQHandler
    add_handler RCC_S_IRQHandler
    add_handler EXTI0_IRQHandler
    add_handler EXTI1_IRQHandler
    add_handler EXTI2_IRQHandler
    add_handler EXTI3_IRQHandler
    add_handler EXTI4_IRQHandler
    add_handler EXTI5_IRQHandler
    add_handler EXTI6_IRQHandler
    add_handler EXTI7_IRQHandler
    add_handler EXTI8_IRQHandler
    add_handler EXTI9_IRQHandler
    add_handler EXTI10_IRQHandler
    add_handler EXTI11_IRQHandler
    add_handler EXTI12_IRQHandler
    add_handler EXTI13_IRQHandler
    add_handler EXTI14_IRQHandler
    add_handler EXTI15_IRQHandler
    add_handler IWDG_IRQHandler
    add_handler SAES_IRQHandler
    add_handler GPDMA1_Channel0_IRQHandler
    add_handler GPDMA1_Channel1_IRQHandler
    add_handler GPDMA1_Channel2_IRQHandler
    add_handler GPDMA1_Channel3_IRQHandler
    add_handler GPDMA1_Channel4_IRQHandler
    add_handler GPDMA1_Channel5_IRQHandler
    add_handler GPDMA1_Channel6_IRQHandler
    add_handler GPDMA1_Channel7_IRQHandler
    add_handler ADC1_IRQHandler
    add_handler DAC1_IRQHandler
    add_handler FDCAN1_IT0_IRQHandler
    add_handler FDCAN1_IT1_IRQHandler
    add_handler TIM1_BRK_TERR_IERR_IRQHandler
    add_handler TIM1_UP_IRQHandler
    add_handler TIM1_TRG_COM_DIR_IDX_IRQHandler
    add_handler TIM1_CC_IRQHandler
    add_handler TIM2_IRQHandler
    add_handler TIM3_IRQHandler
    add_handler TIM4_IRQHandler
    add_handler architecture_reserved_handler // 48 not used on U3
    add_handler TIM6_IRQHandler
    add_handler TIM7_IRQHandler
    add_handler architecture_reserved_handler // 51 not used on U3
    add_handler architecture_reserved_handler // 52 not used on U3
    add_handler I3C1_EV_IRQHandler
    add_handler I3C1_ER_IRQHandler
    add_handler I2C1_EV_IRQHandler
    add_handler I2C1_ER_IRQHandler
    add_handler I2C2_EV_IRQHandler
    add_handler I2C2_ER_IRQHandler
    add_handler SPI1_IRQHandler
    add_handler SPI2_IRQHandler
    add_handler USART1_IRQHandler
    add_handler architecture_reserved_handler // 62 not used on U3
    add_handler USART3_IRQHandler
    add_handler UART4_IRQHandler
    add_handler UART5_IRQHandler
    add_handler LPUART1_IRQHandler
    add_handler LPTIM1_IRQHandler
    add_handler LPTIM2_IRQHandler
    add_handler TIM15_IRQHandler
    add_handler TIM16_IRQHandler
    add_handler TIM17_IRQHandler
    add_handler COMP_IRQHandler
    add_handler USB_FS_IRQHandler
    add_handler CRS_IRQHandler
    add_handler architecture_reserved_handler // 75 not used on U3
    add_handler OCTOSPI1_IRQHandler
    add_handler architecture_reserved_handler // 77 not used on U3
    add_handler SDMMC1_IRQHandler
    add_handler architecture_reserved_handler // 79 not used on U3
    add_handler GPDMA1_Channel8_IRQHandler
    add_handler GPDMA1_Channel9_IRQHandler
    add_handler GPDMA1_Channel10_IRQHandler
    add_handler GPDMA1_Channel11_IRQHandler
    add_handler architecture_reserved_handler // 84 not used on U3
    add_handler architecture_reserved_handler // 85 not used on U3
    add_handler architecture_reserved_handler // 86 not used on U3
    add_handler architecture_reserved_handler // 87 not used on U3
    add_handler I2C3_EV_IRQHandler
    add_handler I2C3_ER_IRQHandler
    add_handler SAI1_IRQHandler
    add_handler architecture_reserved_handler // 91 not used on U3
    add_handler TSC_IRQHandler
    add_handler AES_IRQHandler
    add_handler RNG_IRQHandler
    add_handler FPU_IRQHandler
    add_handler HASH_IRQHandler
    add_handler PKA_IRQHandler
    add_handler LPTIM3_IRQHandler
    add_handler SPI3_IRQHandler
    add_handler I3C2_EV_IRQHandler
    add_handler I3C2_ER_IRQHandler
    add_handler architecture_reserved_handler // 102 not used on U3
    add_handler architecture_reserved_handler // 103 not used on U3
    add_handler architecture_reserved_handler // 104 not used on U3
    add_handler architecture_reserved_handler // 105 not used on U3
    add_handler architecture_reserved_handler // 106 not used on U3
    add_handler ICACHE_IRQHandler
    add_handler architecture_reserved_handler // 108 not used on U3
    add_handler architecture_reserved_handler // 109 not used on U3
    add_handler LPTIM4_IRQHandler
    add_handler architecture_reserved_handler // 111 not used on U3
    add_handler ADF1_IRQHandler
    add_handler ADC2_IRQHandler
    add_handler architecture_reserved_handler // 114 not used on U3
    add_handler architecture_reserved_handler // 115 not used on U3
    add_handler architecture_reserved_handler // 116 not used on U3
    add_handler architecture_reserved_handler // 117 not used on U3
    add_handler architecture_reserved_handler // 118 not used on U3
    add_handler architecture_reserved_handler // 119 not used on U3
    add_handler architecture_reserved_handler // 120 not used on U3
    add_handler architecture_reserved_handler // 121 not used on U3
    add_handler architecture_reserved_handler // 122 not used on U3
    add_handler PWR_IRQHandler
    add_handler PWR_S_IRQHandler

#else

  .section .vector_table, "a"
vector_table:
  .word reset_handler
  .word _stack_section_start
  .word _stack_section_size
  .word _tls_section_start
  .word _tls_section_size
#ifdef USE_APP_LOADING
  .word coreapp_api_get
#else
  .word 0
#endif
#if USE_STORAGE_HWKEY
  .word saes_unpriv_input
  .word saes_unpriv_output
  .word saes_unpriv_callback
#else
  .word 0
  .word 0
  .word 0
#endif

#endif

  .end
