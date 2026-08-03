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
  // Table "Interrupt and exception vectors" - STM32H5E4/5F4/5E5/5F5 reference
  //   manual (RM0517)
  // Section B1.5 - ARMv8-M Architecture Reference Manual
  //
  // The peripheral handler list below is generated from the IRQn_Type enum of
  // vendor/cmsis_device_h5/Include/stm32h5f5xx.h (positions 0..161).
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
    add_handler	PVD_AVD_IRQHandler
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
    add_handler	GPDMA1_Channel0_IRQHandler
    add_handler	GPDMA1_Channel1_IRQHandler
    add_handler	GPDMA1_Channel2_IRQHandler
    add_handler	GPDMA1_Channel3_IRQHandler
    add_handler	GPDMA1_Channel4_IRQHandler
    add_handler	GPDMA1_Channel5_IRQHandler
    add_handler	GPDMA1_Channel6_IRQHandler
    add_handler	GPDMA1_Channel7_IRQHandler
    add_handler	IWDG_IRQHandler
    add_handler	SAES_IRQHandler
    add_handler	ADC1_IRQHandler
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
    add_handler	I2C1_EV_IRQHandler
    add_handler	I2C1_ER_IRQHandler
    add_handler	I2C2_EV_IRQHandler
    add_handler	I2C2_ER_IRQHandler
    add_handler	SPI1_IRQHandler
    add_handler	SPI2_IRQHandler
    add_handler	SPI3_IRQHandler
    add_handler	USART1_IRQHandler
    add_handler	USART2_IRQHandler
    add_handler	USART3_IRQHandler
    add_handler	UART4_IRQHandler
    add_handler	UART5_IRQHandler
    add_handler	LPUART1_IRQHandler
    add_handler	LPTIM1_IRQHandler
    add_handler	TIM8_BRK_IRQHandler
    add_handler	TIM8_UP_IRQHandler
    add_handler	TIM8_TRG_COM_IRQHandler
    add_handler	TIM8_CC_IRQHandler
    add_handler	ADC2_IRQHandler
    add_handler	LPTIM2_IRQHandler
    add_handler	TIM15_IRQHandler
    add_handler	TIM16_IRQHandler
    add_handler	TIM17_IRQHandler
    add_handler	OTG_FS_IRQHandler
    add_handler	CRS_IRQHandler
    add_handler	UCPD1_IRQHandler
    add_handler	FMC_IRQHandler
    add_handler	OCTOSPI1_IRQHandler
    add_handler	SDMMC1_IRQHandler
    add_handler	I2C3_EV_IRQHandler
    add_handler	I2C3_ER_IRQHandler
    add_handler	SPI4_IRQHandler
    add_handler	SPI5_IRQHandler
    add_handler	SPI6_IRQHandler
    add_handler	USART6_IRQHandler
    add_handler	USART10_IRQHandler
    add_handler	USART11_IRQHandler
    add_handler	SAI1_IRQHandler
    add_handler	SAI2_IRQHandler
    add_handler	GPDMA2_Channel0_IRQHandler
    add_handler	GPDMA2_Channel1_IRQHandler
    add_handler	GPDMA2_Channel2_IRQHandler
    add_handler	GPDMA2_Channel3_IRQHandler
    add_handler	GPDMA2_Channel4_IRQHandler
    add_handler	GPDMA2_Channel5_IRQHandler
    add_handler	GPDMA2_Channel6_IRQHandler
    add_handler	GPDMA2_Channel7_IRQHandler
    add_handler	UART7_IRQHandler
    add_handler	UART8_IRQHandler
    add_handler	UART9_IRQHandler
    add_handler	UART12_IRQHandler
    add_handler	SDMMC2_IRQHandler
    add_handler	FPU_IRQHandler
    add_handler	ICACHE_IRQHandler
    add_handler	DCACHE1_IRQHandler
    add_handler	ETH_IRQHandler
    add_handler	ETH_WKUP_IRQHandler
    add_handler	DCMI_PSSI_IRQHandler
    add_handler	FDCAN2_IT0_IRQHandler
    add_handler	FDCAN2_IT1_IRQHandler
    add_handler	CORDIC_IRQHandler
    add_handler	FMAC_IRQHandler
    add_handler	DTS_IRQHandler
    add_handler	RNG_IRQHandler
    add_handler	OTFDEC1_IRQHandler
    add_handler	AES_IRQHandler
    add_handler	HASH_IRQHandler
    add_handler	PKA_IRQHandler
    add_handler	CEC_IRQHandler
    add_handler	TIM12_IRQHandler
    add_handler	TIM13_IRQHandler
    add_handler	TIM14_IRQHandler
    add_handler	I3C1_EV_IRQHandler
    add_handler	I3C1_ER_IRQHandler
    add_handler	I2C4_EV_IRQHandler
    add_handler	I2C4_ER_IRQHandler
    add_handler	LPTIM3_IRQHandler
    add_handler	LPTIM4_IRQHandler
    add_handler	LPTIM5_IRQHandler
    add_handler	LPTIM6_IRQHandler
    add_handler	I3C2_EV_IRQHandler
    add_handler	I3C2_ER_IRQHandler
    add_handler	COMP_IRQHandler
    add_handler	DMA2D_IRQHandler
    add_handler	JPEG_IRQHandler
    add_handler	GPDMA1_Channel8_IRQHandler
    add_handler	GPDMA1_Channel9_IRQHandler
    add_handler	GPDMA1_Channel10_IRQHandler
    add_handler	GPDMA1_Channel11_IRQHandler
    add_handler	GPDMA2_Channel8_IRQHandler
    add_handler	GPDMA2_Channel9_IRQHandler
    add_handler	GPDMA2_Channel10_IRQHandler
    add_handler	GPDMA2_Channel11_IRQHandler
    add_handler	GFXTIM_IRQHandler
    add_handler	LCD_IRQHandler
    add_handler	LCD_GBL_ERROR_IRQHandler
    add_handler	PLAY1_IRQHandler
    add_handler	PLAY1_S_IRQHandler
    add_handler	ADC3_IRQHandler
    add_handler	OCTOSPI2_IRQHandler
    add_handler	OTFDEC2_IRQHandler
    add_handler	FDCAN3_IT0_IRQHandler
    add_handler	FDCAN3_IT1_IRQHandler
    add_handler	MDF1_FLT0_IRQHandler
    add_handler	MDF1_FLT1_IRQHandler
    add_handler	MDF1_FLT2_IRQHandler
    add_handler	MDF1_FLT3_IRQHandler
    add_handler	MDF1_FLT4_IRQHandler
    add_handler	MDF1_FLT5_IRQHandler
    add_handler	ADF1_FLT0_IRQHandler
    add_handler	OTG_HS_IRQHandler

#endif

  .end
