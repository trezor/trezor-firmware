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
  // Table 62 - STM32F427 Reference manual (RM0090)
  // Section B1.5 - ARMv7-M Architecture Reference Manual
  .section .vector_table, "a"
vector_table:
  .word _stack_section_end // defined in linker script
  add_handler reset_handler
    add_handler	NMI_Handler
    add_handler	HardFault_Handler
    add_handler	MemManage_Handler
    add_handler	BusFault_Handler
    add_handler	UsageFault_Handler
    add_handler	SecureFault_Handler
    add_handler	architecture_reserved_handler
    add_handler	architecture_reserved_handler
    add_handler	architecture_reserved_handler
    add_handler	SVC_Handler
    add_handler	DebugMon_Handler
    add_handler	architecture_reserved_handler
    add_handler	PendSV_Handler
    add_handler	SysTick_Handler
    add_handler	WWDG_IRQHandler
    add_handler	PVD_PVM_IRQHandler
    add_handler	RTC_IRQHandler
    add_handler	RTC_S_IRQHandler
    add_handler	TAMP_IRQHandler
    add_handler	RAMCFG_IRQHandler
    add_handler	FLASH_IRQHandler
    add_handler	FLASH_S_IRQHandler
    add_handler	GTZC_IRQHandler
    add_handler	RCC_IRQHandler
    add_handler	RCC_S_IRQHandler
    add_handler	EXTI0_IRQHandler
    add_handler	EXTI1_IRQHandler
    add_handler	EXTI2_IRQHandler
    add_handler	EXTI3_IRQHandler
    add_handler	EXTI4_IRQHandler
    add_handler	EXTI5_IRQHandler
    add_handler	EXTI6_IRQHandler
    add_handler	EXTI7_IRQHandler
    add_handler	EXTI8_IRQHandler
    add_handler	EXTI9_IRQHandler
    add_handler	EXTI10_IRQHandler
    add_handler	EXTI11_IRQHandler
    add_handler	EXTI12_IRQHandler
    add_handler	EXTI13_IRQHandler
    add_handler	EXTI14_IRQHandler
    add_handler	EXTI15_IRQHandler
    add_handler	IWDG_IRQHandler
    add_handler	SAES_IRQHandler
    add_handler	GPDMA1_Channel0_IRQHandler
    add_handler	GPDMA1_Channel1_IRQHandler
    add_handler	GPDMA1_Channel2_IRQHandler
    add_handler	GPDMA1_Channel3_IRQHandler
    add_handler	GPDMA1_Channel4_IRQHandler
    add_handler	GPDMA1_Channel5_IRQHandler
    add_handler	GPDMA1_Channel6_IRQHandler
    add_handler	GPDMA1_Channel7_IRQHandler
    add_handler	ADC1_2_IRQHandler
    add_handler	DAC1_IRQHandler
    add_handler	FDCAN1_IT0_IRQHandler
    add_handler	FDCAN1_IT1_IRQHandler
    add_handler	TIM1_BRK_IRQHandler
    add_handler	TIM1_UP_IRQHandler
    add_handler	TIM1_TRG_COM_IRQHandler
    add_handler	TIM1_CC_IRQHandler
    add_handler	TIM2_IRQHandler
    add_handler	TIM3_IRQHandler
    add_handler	TIM4_IRQHandler
    add_handler	TIM5_IRQHandler
    add_handler	TIM6_IRQHandler
    add_handler	TIM7_IRQHandler
    add_handler	TIM8_BRK_IRQHandler
    add_handler	TIM8_UP_IRQHandler
    add_handler	TIM8_TRG_COM_IRQHandler
    add_handler	TIM8_CC_IRQHandler
    add_handler	I2C1_EV_IRQHandler
    add_handler	I2C1_ER_IRQHandler
    add_handler	I2C2_EV_IRQHandler
    add_handler	I2C2_ER_IRQHandler
    add_handler	SPI1_IRQHandler
    add_handler	SPI2_IRQHandler
    add_handler	USART1_IRQHandler
    add_handler	USART2_IRQHandler
    add_handler	USART3_IRQHandler
    add_handler	UART4_IRQHandler
    add_handler	UART5_IRQHandler
    add_handler	LPUART1_IRQHandler
    add_handler	LPTIM1_IRQHandler
    add_handler	LPTIM2_IRQHandler
    add_handler	TIM15_IRQHandler
    add_handler	TIM16_IRQHandler
    add_handler	TIM17_IRQHandler
    add_handler	COMP_IRQHandler
    add_handler	OTG_HS_IRQHandler
    add_handler	CRS_IRQHandler
    add_handler	FMC_IRQHandler
    add_handler	OCTOSPI1_IRQHandler
    add_handler	PWR_S3WU_IRQHandler
    add_handler	SDMMC1_IRQHandler
    add_handler	SDMMC2_IRQHandler
    add_handler	GPDMA1_Channel8_IRQHandler
    add_handler	GPDMA1_Channel9_IRQHandler
    add_handler	GPDMA1_Channel10_IRQHandler
    add_handler	GPDMA1_Channel11_IRQHandler
    add_handler	GPDMA1_Channel12_IRQHandler
    add_handler	GPDMA1_Channel13_IRQHandler
    add_handler	GPDMA1_Channel14_IRQHandler
    add_handler	GPDMA1_Channel15_IRQHandler
    add_handler	I2C3_EV_IRQHandler
    add_handler	I2C3_ER_IRQHandler
    add_handler	SAI1_IRQHandler
    add_handler	SAI2_IRQHandler
    add_handler	TSC_IRQHandler
    add_handler	AES_IRQHandler
    add_handler	RNG_IRQHandler
    add_handler	FPU_IRQHandler
    add_handler	HASH_IRQHandler
    add_handler	PKA_IRQHandler
    add_handler	LPTIM3_IRQHandler
    add_handler	SPI3_IRQHandler
    add_handler	I2C4_ER_IRQHandler
    add_handler	I2C4_EV_IRQHandler
    add_handler	MDF1_FLT0_IRQHandler
    add_handler	MDF1_FLT1_IRQHandler
    add_handler	MDF1_FLT2_IRQHandler
    add_handler	MDF1_FLT3_IRQHandler
    add_handler	UCPD1_IRQHandler
    add_handler	ICACHE_IRQHandler
    add_handler	OTFDEC1_IRQHandler
    add_handler	OTFDEC2_IRQHandler
    add_handler	LPTIM4_IRQHandler
    add_handler	DCACHE1_IRQHandler
    add_handler	ADF1_IRQHandler
    add_handler	ADC4_IRQHandler
    add_handler	LPDMA1_Channel0_IRQHandler
    add_handler	LPDMA1_Channel1_IRQHandler
    add_handler	LPDMA1_Channel2_IRQHandler
    add_handler	LPDMA1_Channel3_IRQHandler
    add_handler	DMA2D_IRQHandler
    add_handler	DCMI_PSSI_IRQHandler
    add_handler	OCTOSPI2_IRQHandler
    add_handler	MDF1_FLT4_IRQHandler
    add_handler	MDF1_FLT5_IRQHandler
    add_handler	CORDIC_IRQHandler
    add_handler	FMAC_IRQHandler
    add_handler	LSECSSD_IRQHandler
    add_handler	USART6_IRQHandler
    add_handler	I2C5_ER_IRQHandler
    add_handler	I2C5_EV_IRQHandler
    add_handler	I2C6_ER_IRQHandler
    add_handler	I2C6_EV_IRQHandler
    add_handler	HSPI1_IRQHandler
    add_handler	GPU2D_IRQHandler
    add_handler	GPU2D_ER_IRQHandler
    add_handler	GFXMMU_IRQHandler
    add_handler	LTDC_IRQHandler
    add_handler	LTDC_ER_IRQHandler
    add_handler	DSI_IRQHandler
    add_handler	DCACHE2_IRQHandler

#else

  .section .vector_table, "a"
vector_table:
  .word _stack_section_start
  .word _stack_section_size
  .word reset_handler

#endif

  .end
