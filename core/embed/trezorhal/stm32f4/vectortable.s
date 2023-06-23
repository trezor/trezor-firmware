  .syntax unified

  .text

  .global default_handler
  .type default_handler, STT_FUNC
default_handler:
  b shutdown_privileged

  .macro add_handler symbol_name:req
    .word \symbol_name
    .weak \symbol_name
    .thumb_set \symbol_name, default_handler
  .endm

  // Reference:
  // Table 62 - STM32F427 Reference manual (RM0090)
  // Section B1.5 - ARMv7-M Architecture Reference Manual
  .section .vector_table, "a"
vector_table:
  .word main_stack_base // defined in linker script
  add_handler reset_handler
  add_handler NMI_Handler
  add_handler HardFault_Handler
  add_handler MemManage_Handler
  add_handler BusFault_Handler
  add_handler UsageFault_Handler
  add_handler architecture_reserved_handler
  add_handler architecture_reserved_handler
  add_handler architecture_reserved_handler
  add_handler architecture_reserved_handler
  add_handler SVC_Handler
  add_handler DebugMon_Handler
  add_handler architecture_reserved_handler
  add_handler PendSV_Handler
  add_handler SysTick_Handler
  add_handler WWDG_IRQHandler
  add_handler PVD_IRQHandler
  add_handler TAMP_STAMP_IRQHandler
  add_handler RTC_WKUP_IRQHandler
  add_handler FLASH_IRQHandler
  add_handler RCC_IRQHandler
  add_handler EXTI0_IRQHandler
  add_handler EXTI1_IRQHandler
  add_handler EXTI2_IRQHandler
  add_handler EXTI3_IRQHandler
  add_handler EXTI4_IRQHandler
  add_handler DMA1_Stream0_IRQHandler
  add_handler DMA1_Stream1_IRQHandler
  add_handler DMA1_Stream2_IRQHandler
  add_handler DMA1_Stream3_IRQHandler
  add_handler DMA1_Stream4_IRQHandler
  add_handler DMA1_Stream5_IRQHandler
  add_handler DMA1_Stream6_IRQHandler
  add_handler ADC_IRQHandler
  add_handler CAN1_TX_IRQHandler
  add_handler CAN1_RX0_IRQHandler
  add_handler CAN1_RX1_IRQHandler
  add_handler CAN1_SCE_IRQHandler
  add_handler EXTI9_5_IRQHandler
  add_handler TIM1_BRK_TIM9_IRQHandler
  add_handler TIM1_UP_TIM10_IRQHandler
  add_handler TIM1_TRG_COM_TIM11_IRQHandler
  add_handler TIM1_CC_IRQHandler
  add_handler TIM2_IRQHandler
  add_handler TIM3_IRQHandler
  add_handler TIM4_IRQHandler
  add_handler I2C1_EV_IRQHandler
  add_handler I2C1_ER_IRQHandler
  add_handler I2C2_EV_IRQHandler
  add_handler I2C2_ER_IRQHandler
  add_handler SPI1_IRQHandler
  add_handler SPI2_IRQHandler
  add_handler USART1_IRQHandler
  add_handler USART2_IRQHandler
  add_handler USART3_IRQHandler
  add_handler EXTI15_10_IRQHandler
  add_handler RTC_Alarm_IRQHandler
  add_handler OTG_FS_WKUP_IRQHandler
  add_handler TIM8_BRK_TIM12_IRQHandler
  add_handler TIM8_UP_TIM13_IRQHandler
  add_handler TIM8_TRG_COM_TIM14_IRQHandler
  add_handler TIM8_CC_IRQHandler
  add_handler DMA1_Stream7_IRQHandler
  add_handler FSMC_IRQHandler
  add_handler SDIO_IRQHandler
  add_handler TIM5_IRQHandler
  add_handler SPI3_IRQHandler
  add_handler UART4_IRQHandler
  add_handler UART5_IRQHandler
  add_handler TIM6_DAC_IRQHandler
  add_handler TIM7_IRQHandler
  add_handler DMA2_Stream0_IRQHandler
  add_handler DMA2_Stream1_IRQHandler
  add_handler DMA2_Stream2_IRQHandler
  add_handler DMA2_Stream3_IRQHandler
  add_handler DMA2_Stream4_IRQHandler
  add_handler ETH_IRQHandler
  add_handler ETH_WKUP_IRQHandler
  add_handler CAN2_TX_IRQHandler
  add_handler CAN2_RX0_IRQHandler
  add_handler CAN2_RX1_IRQHandler
  add_handler CAN2_SCE_IRQHandler
  add_handler OTG_FS_IRQHandler
  add_handler DMA2_Stream5_IRQHandler
  add_handler DMA2_Stream6_IRQHandler
  add_handler DMA2_Stream7_IRQHandler
  add_handler USART6_IRQHandler
  add_handler I2C3_EV_IRQHandler
  add_handler I2C3_ER_IRQHandler
  add_handler OTG_HS_EP1_OUT_IRQHandler
  add_handler OTG_HS_EP1_IN_IRQHandler
  add_handler OTG_HS_WKUP_IRQHandler
  add_handler OTG_HS_IRQHandler
  add_handler DCMI_IRQHandler
  add_handler CRYP_IRQHandler
  add_handler HASH_RNG_IRQHandler
  add_handler FPU_IRQHandler
  add_handler UART7_IRQHandler
  add_handler UART8_IRQHandler
  add_handler SPI4_IRQHandler
  add_handler SPI5_IRQHandler
  add_handler SPI6_IRQHandler
  add_handler SAI1_IRQHandler
  add_handler LTDC_IRQHandler
  add_handler LTDC_ER_IRQHandler
  add_handler DMA2D_IRQHandler

  .end
