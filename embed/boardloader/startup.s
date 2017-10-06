  .syntax unified

  // Reference:
  // Table 61 - STM32F405 Reference manual (RM0090)
  // Section B1.5 - ARMv7-M Architecture Reference Manual
  .section .vector_table, "a"
vector_table:
  .word main_stack_base // defined in linker script
  .word reset_handler
  .word NMI_Handler
  .word HardFault_Handler
  .word MemManage_Handler
  .word BusFault_Handler
  .word UsageFault_Handler
  .word 0
  .word 0
  .word 0
  .word 0
  .word SVC_Handler
  .word DebugMon_Handler
  .word 0
  .word PendSV_Handler
  .word SysTick_Handler
  .word WWDG_IRQHandler
  .word PVD_IRQHandler
  .word TAMP_STAMP_IRQHandler
  .word RTC_WKUP_IRQHandler
  .word FLASH_IRQHandler
  .word RCC_IRQHandler
  .word EXTI0_IRQHandler
  .word EXTI1_IRQHandler
  .word EXTI2_IRQHandler
  .word EXTI3_IRQHandler
  .word EXTI4_IRQHandler
  .word DMA1_Stream0_IRQHandler
  .word DMA1_Stream1_IRQHandler
  .word DMA1_Stream2_IRQHandler
  .word DMA1_Stream3_IRQHandler
  .word DMA1_Stream4_IRQHandler
  .word DMA1_Stream5_IRQHandler
  .word DMA1_Stream6_IRQHandler
  .word ADC_IRQHandler
  .word CAN1_TX_IRQHandler
  .word CAN1_RX0_IRQHandler
  .word CAN1_RX1_IRQHandler
  .word CAN1_SCE_IRQHandler
  .word EXTI9_5_IRQHandler
  .word TIM1_BRK_TIM9_IRQHandler
  .word TIM1_UP_TIM10_IRQHandler
  .word TIM1_TRG_COM_TIM11_IRQHandler
  .word TIM1_CC_IRQHandler
  .word TIM2_IRQHandler
  .word TIM3_IRQHandler
  .word TIM4_IRQHandler
  .word I2C1_EV_IRQHandler
  .word I2C1_ER_IRQHandler
  .word I2C2_EV_IRQHandler
  .word I2C2_ER_IRQHandler
  .word SPI1_IRQHandler
  .word SPI2_IRQHandler
  .word USART1_IRQHandler
  .word USART2_IRQHandler
  .word USART3_IRQHandler
  .word EXTI15_10_IRQHandler
  .word RTC_Alarm_IRQHandler
  .word OTG_FS_WKUP_IRQHandler
  .word TIM8_BRK_TIM12_IRQHandler
  .word TIM8_UP_TIM13_IRQHandler
  .word TIM8_TRG_COM_TIM14_IRQHandler
  .word TIM8_CC_IRQHandler
  .word DMA1_Stream7_IRQHandler
  .word FSMC_IRQHandler
  .word SDIO_IRQHandler
  .word TIM5_IRQHandler
  .word SPI3_IRQHandler
  .word UART4_IRQHandler
  .word UART5_IRQHandler
  .word TIM6_DAC_IRQHandler
  .word TIM7_IRQHandler
  .word DMA2_Stream0_IRQHandler
  .word DMA2_Stream1_IRQHandler
  .word DMA2_Stream2_IRQHandler
  .word DMA2_Stream3_IRQHandler
  .word DMA2_Stream4_IRQHandler
  .word ETH_IRQHandler
  .word ETH_WKUP_IRQHandler
  .word CAN2_TX_IRQHandler
  .word CAN2_RX0_IRQHandler
  .word CAN2_RX1_IRQHandler
  .word CAN2_SCE_IRQHandler
  .word OTG_FS_IRQHandler
  .word DMA2_Stream5_IRQHandler
  .word DMA2_Stream6_IRQHandler
  .word DMA2_Stream7_IRQHandler
  .word USART6_IRQHandler
  .word I2C3_EV_IRQHandler
  .word I2C3_ER_IRQHandler
  .word OTG_HS_EP1_OUT_IRQHandler
  .word OTG_HS_EP1_IN_IRQHandler
  .word OTG_HS_WKUP_IRQHandler
  .word OTG_HS_IRQHandler
  .word DCMI_IRQHandler
  .word 0
  .word HASH_RNG_IRQHandler
  .word FPU_IRQHandler

  .weak NMI_Handler
  .thumb_set NMI_Handler, default_handler

  .weak HardFault_Handler
  .thumb_set HardFault_Handler, default_handler

  .weak MemManage_Handler
  .thumb_set MemManage_Handler, default_handler

  .weak BusFault_Handler
  .thumb_set BusFault_Handler, default_handler

  .weak UsageFault_Handler
  .thumb_set UsageFault_Handler, default_handler

  .weak SVC_Handler
  .thumb_set SVC_Handler, default_handler

  .weak DebugMon_Handler
  .thumb_set DebugMon_Handler, default_handler

  .weak PendSV_Handler
  .thumb_set PendSV_Handler, default_handler

  .weak SysTick_Handler
  .thumb_set SysTick_Handler, default_handler

  .weak WWDG_IRQHandler
  .thumb_set WWDG_IRQHandler, default_handler

  .weak PVD_IRQHandler
  .thumb_set PVD_IRQHandler, default_handler

  .weak TAMP_STAMP_IRQHandler
  .thumb_set TAMP_STAMP_IRQHandler, default_handler

  .weak RTC_WKUP_IRQHandler
  .thumb_set RTC_WKUP_IRQHandler, default_handler

  .weak FLASH_IRQHandler
  .thumb_set FLASH_IRQHandler, default_handler

  .weak RCC_IRQHandler
  .thumb_set RCC_IRQHandler, default_handler

  .weak EXTI0_IRQHandler
  .thumb_set EXTI0_IRQHandler, default_handler

  .weak EXTI1_IRQHandler
  .thumb_set EXTI1_IRQHandler, default_handler

  .weak EXTI2_IRQHandler
  .thumb_set EXTI2_IRQHandler, default_handler

  .weak EXTI3_IRQHandler
  .thumb_set EXTI3_IRQHandler, default_handler

  .weak EXTI4_IRQHandler
  .thumb_set EXTI4_IRQHandler, default_handler

  .weak DMA1_Stream0_IRQHandler
  .thumb_set DMA1_Stream0_IRQHandler, default_handler

  .weak DMA1_Stream1_IRQHandler
  .thumb_set DMA1_Stream1_IRQHandler, default_handler

  .weak DMA1_Stream2_IRQHandler
  .thumb_set DMA1_Stream2_IRQHandler, default_handler

  .weak DMA1_Stream3_IRQHandler
  .thumb_set DMA1_Stream3_IRQHandler, default_handler

  .weak DMA1_Stream4_IRQHandler
  .thumb_set DMA1_Stream4_IRQHandler, default_handler

  .weak DMA1_Stream5_IRQHandler
  .thumb_set DMA1_Stream5_IRQHandler, default_handler

  .weak DMA1_Stream6_IRQHandler
  .thumb_set DMA1_Stream6_IRQHandler, default_handler

  .weak ADC_IRQHandler
  .thumb_set ADC_IRQHandler, default_handler

  .weak CAN1_TX_IRQHandler
  .thumb_set CAN1_TX_IRQHandler, default_handler

  .weak CAN1_RX0_IRQHandler
  .thumb_set CAN1_RX0_IRQHandler, default_handler

  .weak CAN1_RX1_IRQHandler
  .thumb_set CAN1_RX1_IRQHandler, default_handler

  .weak CAN1_SCE_IRQHandler
  .thumb_set CAN1_SCE_IRQHandler, default_handler

  .weak EXTI9_5_IRQHandler
  .thumb_set EXTI9_5_IRQHandler, default_handler

  .weak TIM1_BRK_TIM9_IRQHandler
  .thumb_set TIM1_BRK_TIM9_IRQHandler, default_handler

  .weak TIM1_UP_TIM10_IRQHandler
  .thumb_set TIM1_UP_TIM10_IRQHandler, default_handler

  .weak TIM1_TRG_COM_TIM11_IRQHandler
  .thumb_set TIM1_TRG_COM_TIM11_IRQHandler, default_handler

  .weak TIM1_CC_IRQHandler
  .thumb_set TIM1_CC_IRQHandler, default_handler

  .weak TIM2_IRQHandler
  .thumb_set TIM2_IRQHandler, default_handler

  .weak TIM3_IRQHandler
  .thumb_set TIM3_IRQHandler, default_handler

  .weak TIM4_IRQHandler
  .thumb_set TIM4_IRQHandler, default_handler

  .weak I2C1_EV_IRQHandler
  .thumb_set I2C1_EV_IRQHandler, default_handler

  .weak I2C1_ER_IRQHandler
  .thumb_set I2C1_ER_IRQHandler, default_handler

  .weak I2C2_EV_IRQHandler
  .thumb_set I2C2_EV_IRQHandler, default_handler

  .weak I2C2_ER_IRQHandler
  .thumb_set I2C2_ER_IRQHandler, default_handler

  .weak SPI1_IRQHandler
  .thumb_set SPI1_IRQHandler, default_handler

  .weak SPI2_IRQHandler
  .thumb_set SPI2_IRQHandler, default_handler

  .weak USART1_IRQHandler
  .thumb_set USART1_IRQHandler, default_handler

  .weak USART2_IRQHandler
  .thumb_set USART2_IRQHandler, default_handler

  .weak USART3_IRQHandler
  .thumb_set USART3_IRQHandler, default_handler

  .weak EXTI15_10_IRQHandler
  .thumb_set EXTI15_10_IRQHandler, default_handler

  .weak RTC_Alarm_IRQHandler
  .thumb_set RTC_Alarm_IRQHandler, default_handler

  .weak OTG_FS_WKUP_IRQHandler
  .thumb_set OTG_FS_WKUP_IRQHandler, default_handler

  .weak TIM8_BRK_TIM12_IRQHandler
  .thumb_set TIM8_BRK_TIM12_IRQHandler, default_handler

  .weak TIM8_UP_TIM13_IRQHandler
  .thumb_set TIM8_UP_TIM13_IRQHandler, default_handler

  .weak TIM8_TRG_COM_TIM14_IRQHandler
  .thumb_set TIM8_TRG_COM_TIM14_IRQHandler, default_handler

  .weak TIM8_CC_IRQHandler
  .thumb_set TIM8_CC_IRQHandler, default_handler

  .weak DMA1_Stream7_IRQHandler
  .thumb_set DMA1_Stream7_IRQHandler, default_handler

  .weak FSMC_IRQHandler
  .thumb_set FSMC_IRQHandler, default_handler

  .weak SDIO_IRQHandler
  .thumb_set SDIO_IRQHandler, default_handler

  .weak TIM5_IRQHandler
  .thumb_set TIM5_IRQHandler, default_handler

  .weak SPI3_IRQHandler
  .thumb_set SPI3_IRQHandler, default_handler

  .weak UART4_IRQHandler
  .thumb_set UART4_IRQHandler, default_handler

  .weak UART5_IRQHandler
  .thumb_set UART5_IRQHandler, default_handler

  .weak TIM6_DAC_IRQHandler
  .thumb_set TIM6_DAC_IRQHandler, default_handler

  .weak TIM7_IRQHandler
  .thumb_set TIM7_IRQHandler, default_handler

  .weak DMA2_Stream0_IRQHandler
  .thumb_set DMA2_Stream0_IRQHandler, default_handler

  .weak DMA2_Stream1_IRQHandler
  .thumb_set DMA2_Stream1_IRQHandler, default_handler

  .weak DMA2_Stream2_IRQHandler
  .thumb_set DMA2_Stream2_IRQHandler, default_handler

  .weak DMA2_Stream3_IRQHandler
  .thumb_set DMA2_Stream3_IRQHandler, default_handler

  .weak DMA2_Stream4_IRQHandler
  .thumb_set DMA2_Stream4_IRQHandler, default_handler

  .weak ETH_IRQHandler
  .thumb_set ETH_IRQHandler, default_handler

  .weak ETH_WKUP_IRQHandler
  .thumb_set ETH_WKUP_IRQHandler, default_handler

  .weak CAN2_TX_IRQHandler
  .thumb_set CAN2_TX_IRQHandler, default_handler

  .weak CAN2_RX0_IRQHandler
  .thumb_set CAN2_RX0_IRQHandler, default_handler

  .weak CAN2_RX1_IRQHandler
  .thumb_set CAN2_RX1_IRQHandler, default_handler

  .weak CAN2_SCE_IRQHandler
  .thumb_set CAN2_SCE_IRQHandler, default_handler

  .weak OTG_FS_IRQHandler
  .thumb_set OTG_FS_IRQHandler, default_handler

  .weak DMA2_Stream5_IRQHandler
  .thumb_set DMA2_Stream5_IRQHandler, default_handler

  .weak DMA2_Stream6_IRQHandler
  .thumb_set DMA2_Stream6_IRQHandler, default_handler

  .weak DMA2_Stream7_IRQHandler
  .thumb_set DMA2_Stream7_IRQHandler, default_handler

  .weak USART6_IRQHandler
  .thumb_set USART6_IRQHandler, default_handler

  .weak I2C3_EV_IRQHandler
  .thumb_set I2C3_EV_IRQHandler, default_handler

  .weak I2C3_ER_IRQHandler
  .thumb_set I2C3_ER_IRQHandler, default_handler

  .weak OTG_HS_EP1_OUT_IRQHandler
  .thumb_set OTG_HS_EP1_OUT_IRQHandler, default_handler

  .weak OTG_HS_EP1_IN_IRQHandler
  .thumb_set OTG_HS_EP1_IN_IRQHandler, default_handler

  .weak OTG_HS_WKUP_IRQHandler
  .thumb_set OTG_HS_WKUP_IRQHandler, default_handler

  .weak OTG_HS_IRQHandler
  .thumb_set OTG_HS_IRQHandler, default_handler

  .weak DCMI_IRQHandler
  .thumb_set DCMI_IRQHandler, default_handler

  .weak HASH_RNG_IRQHandler
  .thumb_set HASH_RNG_IRQHandler, default_handler

  .weak FPU_IRQHandler
  .thumb_set FPU_IRQHandler, default_handler

  .text

  .global memset_reg
  .type memset_reg, STT_FUNC
memset_reg:
  // call with the following (note that the arguments are not validated prior to use):
  // r0 - address of first word to write (inclusive)
  // r1 - address of first word following the address in r0 to NOT write (exclusive)
  // r2 - word value to be written
  // both addresses in r0 and r1 needs to be divisible by 4!
  .L_loop_begin:
    str r2, [r0], 4 // store the word in r2 to the address in r0, post-indexed
    cmp r0, r1
  bne .L_loop_begin
  bx lr

  .global reset_handler
  .type reset_handler, STT_FUNC
reset_handler:
  bl SystemInit

  // wipe memory to remove any possible vestiges of sensitive data
  ldr r0, =ccmram_start // r0 - point to beginning of CCMRAM
  ldr r1, =ccmram_end   // r1 - point to byte after the end of CCMRAM
  ldr r2, =0            // r2 - the word-sized value to be written
  bl memset_reg

  ldr r0, =sram_start   // r0 - point to beginning of SRAM
  ldr r1, =sram_end     // r1 - point to byte after the end of SRAM
  ldr r2, =0            // r2 - the word-sized value to be written
  bl memset_reg

  // copy data in from flash
  ldr r0, =data_vma     // dst addr
  ldr r1, =data_lma     // src addr
  ldr r2, =data_size    // size in bytes
  bl memcpy

  // enter the application code
  bl main

  // loop forever if the application code returns
  b .

  .type default_handler, STT_FUNC
default_handler:
  b . // loop forever

  .end
