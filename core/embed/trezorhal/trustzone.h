#ifndef __TREZORHAL_TRUSTZONE__
#define __TREZORHAL_TRUSTZONE__

#ifdef BOARDLOADER
#define CMSE_NS_CALL __attribute((cmse_nonsecure_call))
#define CMSE_NS_ENTRY __attribute((cmse_nonsecure_entry))

typedef void CMSE_NS_CALL (*funcptr)(void);

/* typedef for non-secure callback functions */
typedef funcptr funcptr_NS;

#include STM32_HAL_H

/*
//-------- <<< Use Configuration Wizard in Context Menu >>> -----------------
*/

/*
// <e>Initialize Security Attribution Unit (SAU) CTRL register
*/
#define SAU_INIT_CTRL 1

/*
//   <q> Enable SAU
//   <i> Value for SAU->CTRL register bit ENABLE
*/
#define SAU_INIT_CTRL_ENABLE 0

/*
//   <o> When SAU is disabled
//     <0=> All Memory is Secure
//     <1=> All Memory is Non-Secure
//   <i> Value for SAU->CTRL register bit ALLNS
//   <i> When all Memory is Non-Secure (ALLNS is 1), IDAU can override memory
map configuration.
*/
#define SAU_INIT_CTRL_ALLNS 1

/*
// </e>
*/

/*
// <h>Initialize Security Attribution Unit (SAU) Address Regions
// <i>SAU configuration specifies regions to be one of:
// <i> - Secure and Non-Secure Callable
// <i> - Non-Secure
// <i>Note: All memory regions not configured by SAU are Secure
*/
#define SAU_REGIONS_MAX 8 /* Max. number of SAU regions */

/*
//   <e>Initialize SAU Region 0
//   <i> Setup SAU Region 0 memory attributes
*/
#define SAU_INIT_REGION0 0

/*
//     <o>Start Address <0-0xFFFFFFE0>
*/
#define SAU_INIT_START0 0x0C1FE000 /* start address of SAU region 0 */

/*
//     <o>End Address <0x1F-0xFFFFFFFF>
*/
#define SAU_INIT_END0 0x0C1FFFFF /* end address of SAU region 0 */

/*
//     <o>Region is
//         <0=>Non-Secure
//         <1=>Secure, Non-Secure Callable
*/
#define SAU_INIT_NSC0 1
/*
//   </e>
*/

/*
//   <e>Initialize SAU Region 1
//   <i> Setup SAU Region 1 memory attributes
*/
#define SAU_INIT_REGION1 0

/*
//     <o>Start Address <0-0xFFFFFFE0>
*/
#define SAU_INIT_START1 0x08200000 /* start address of SAU region 1 */

/*
//     <o>End Address <0x1F-0xFFFFFFFF>
*/
#define SAU_INIT_END1 0x083FFFFF /* end address of SAU region 1 */

/*
//     <o>Region is
//         <0=>Non-Secure
//         <1=>Secure, Non-Secure Callable
*/
#define SAU_INIT_NSC1 0
/*
//   </e>
*/

/*
//   <e>Initialize SAU Region 2
//   <i> Setup SAU Region 2 memory attributes
*/
#define SAU_INIT_REGION2 0

/*
//     <o>Start Address <0-0xFFFFFFE0>
*/
#define SAU_INIT_START2 0x200D0000 /* start address of SAU region 2 */

/*
//     <o>End Address <0x1F-0xFFFFFFFF>
*/
#define SAU_INIT_END2 0x2026FFFF /* end address of SAU region 2 */

/*
//     <o>Region is
//         <0=>Non-Secure
//         <1=>Secure, Non-Secure Callable
*/
#define SAU_INIT_NSC2 0
/*
//   </e>
*/

/*
//   <e>Initialize SAU Region 3
//   <i> Setup SAU Region 3 memory attributes
*/
#define SAU_INIT_REGION3 0

/*
//     <o>Start Address <0-0xFFFFFFE0>
*/
#define SAU_INIT_START3 0x40000000 /* start address of SAU region 3 */

/*
//     <o>End Address <0x1F-0xFFFFFFFF>
*/
#define SAU_INIT_END3 0x4FFFFFFF /* end address of SAU region 3 */

/*
//     <o>Region is
//         <0=>Non-Secure
//         <1=>Secure, Non-Secure Callable
*/
#define SAU_INIT_NSC3 0
/*
//   </e>
*/

/*
//   <e>Initialize SAU Region 4
//   <i> Setup SAU Region 4 memory attributes
*/
#define SAU_INIT_REGION4 0

/*
//     <o>Start Address <0-0xFFFFFFE0>
*/
#define SAU_INIT_START4 0x60000000 /* start address of SAU region 4 */

/*
//     <o>End Address <0x1F-0xFFFFFFFF>
*/
#define SAU_INIT_END4 0xAFFFFFFF /* end address of SAU region 4 */

/*
//     <o>Region is
//         <0=>Non-Secure
//         <1=>Secure, Non-Secure Callable
*/
#define SAU_INIT_NSC4 0
/*
//   </e>
*/

/*
//   <e>Initialize SAU Region 5
//   <i> Setup SAU Region 5 memory attributes
*/
#define SAU_INIT_REGION5 0

/*
//     <o>Start Address <0-0xFFFFFFE0>
*/
#define SAU_INIT_START5 0x0BF90000 /* start address of SAU region 5 */

/*
//     <o>End Address <0x1F-0xFFFFFFFF>
*/
#define SAU_INIT_END5 0x0BFA8FFF /* end address of SAU region 5 */

/*
//     <o>Region is
//         <0=>Non-Secure
//         <1=>Secure, Non-Secure Callable
*/
#define SAU_INIT_NSC5 0
/*
//   </e>
*/

/*
//   <e>Initialize SAU Region 6
//   <i> Setup SAU Region 6 memory attributes
*/
#define SAU_INIT_REGION6 0

/*
//     <o>Start Address <0-0xFFFFFFE0>
*/
#define SAU_INIT_START6 0x00000000 /* start address of SAU region 6 */

/*
//     <o>End Address <0x1F-0xFFFFFFFF>
*/
#define SAU_INIT_END6 0x00000000 /* end address of SAU region 6 */

/*
//     <o>Region is
//         <0=>Non-Secure
//         <1=>Secure, Non-Secure Callable
*/
#define SAU_INIT_NSC6 0
/*
//   </e>
*/

/*
//   <e>Initialize SAU Region 7
//   <i> Setup SAU Region 7 memory attributes
*/
#define SAU_INIT_REGION7 0

/*
//     <o>Start Address <0-0xFFFFFFE0>
*/
#define SAU_INIT_START7 0x00000000 /* start address of SAU region 7 */

/*
//     <o>End Address <0x1F-0xFFFFFFFF>
*/
#define SAU_INIT_END7 0x00000000 /* end address of SAU region 7 */

/*
//     <o>Region is
//         <0=>Non-Secure
//         <1=>Secure, Non-Secure Callable
*/
#define SAU_INIT_NSC7 0
/*
//   </e>
*/

/*
// </h>
*/

/*
// <e>Setup behaviour of Sleep and Exception Handling
*/
#define SCB_CSR_AIRCR_INIT 0

/*
//   <o> Deep Sleep can be enabled by
//     <0=>Secure and Non-Secure state
//     <1=>Secure state only
//   <i> Value for SCB->CSR register bit DEEPSLEEPS
*/
#define SCB_CSR_DEEPSLEEPS_VAL 0

/*
//   <o>System reset request accessible from
//     <0=> Secure and Non-Secure state
//     <1=> Secure state only
//   <i> Value for SCB->AIRCR register bit SYSRESETREQS
*/
#define SCB_AIRCR_SYSRESETREQS_VAL 0

/*
//   <o>Priority of Non-Secure exceptions is
//     <0=> Not altered
//     <1=> Lowered to 0x04-0x07
//   <i> Value for SCB->AIRCR register bit PRIS
*/
#define SCB_AIRCR_PRIS_VAL 0

/*
//   <o>BusFault, HardFault, and NMI target
//     <0=> Secure state
//     <1=> Non-Secure state
//   <i> Value for SCB->AIRCR register bit BFHFNMINS
*/
#define SCB_AIRCR_BFHFNMINS_VAL 0

/*
// </e>
*/

/*
// <e>Setup behaviour of Floating Point Unit
*/
#define TZ_FPU_NS_USAGE 1

/*
// <o>Floating Point Unit usage
//     <0=> Secure state only
//     <3=> Secure and Non-Secure state
//   <i> Value for SCB->NSACR register bits CP10, CP11
*/
#define SCB_NSACR_CP10_11_VAL 3

/*
// <o>Treat floating-point registers as Secure
//     <0=> Disabled
//     <1=> Enabled
//   <i> Value for FPU->FPCCR register bit TS
*/
#define FPU_FPCCR_TS_VAL 0

/*
// <o>Clear on return (CLRONRET) accessibility
//     <0=> Secure and Non-Secure state
//     <1=> Secure state only
//   <i> Value for FPU->FPCCR register bit CLRONRETS
*/
#define FPU_FPCCR_CLRONRETS_VAL 0

/*
// <o>Clear floating-point caller saved registers on exception return
//     <0=> Disabled
//     <1=> Enabled
//   <i> Value for FPU->FPCCR register bit CLRONRET
*/
#define FPU_FPCCR_CLRONRET_VAL 1

/*
// </e>
*/

/*
// <h>Setup Interrupt Target
*/

/*
//   <e>Initialize ITNS 0 (Interrupts 0..31)
*/
#define NVIC_INIT_ITNS0 1

/*
// Interrupts 0..31
//   <o.0>  WWDG_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.1>  PVD_PVM_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.2>  RTC_IRQn              <0=> Secure state <1=> Non-Secure state
//   <o.3>  RTC_S_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.4>  TAMP_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.5>  RAMCFG_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.6>  FLASH_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.7>  FLASH_S_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.8>  GTZC_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.9>  RCC_IRQn              <0=> Secure state <1=> Non-Secure state
//   <o.10> RCC_S_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.11> EXTI0_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.12> EXTI1_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.13> EXTI2_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.14> EXTI3_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.15> EXTI4_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.16> EXTI5_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.17> EXTI6_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.18> EXTI7_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.19> EXTI8_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.20> EXTI9_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.21> EXTI10_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.22> EXTI11_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.23> EXTI12_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.24> EXTI13_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.25> EXTI14_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.26> EXTI15_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.27> IWDG_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.29> GPDMA1_Channel0_IRQn   <0=> Secure state <1=> Non-Secure state
//   <o.30> GPDMA1_Channel1_IRQn   <0=> Secure state <1=> Non-Secure state
//   <o.31> GPDMA1_Channel2_IRQn   <0=> Secure state <1=> Non-Secure state
*/
#define NVIC_INIT_ITNS0_VAL 0x00000000

/*
//   </e>
*/

/*
//   <e>Initialize ITNS 1 (Interrupts 32..63)
*/
#define NVIC_INIT_ITNS1 1

/*
// Interrupts 32..63
//   <o.0>  GPDMA1_Channel3_IRQn  <0=> Secure state <1=> Non-Secure state
//   <o.1>  GPDMA1_Channel4_IRQn  <0=> Secure state <1=> Non-Secure state
//   <o.2>  GPDMA1_Channel5_IRQn  <0=> Secure state <1=> Non-Secure state
//   <o.3>  GPDMA1_Channel6_IRQn  <0=> Secure state <1=> Non-Secure state
//   <o.4>  GPDMA1_Channel7_IRQn  <0=> Secure state <1=> Non-Secure state
//   <o.5>  ADC1_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.6>  DAC1_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.7>  FDCAN1_IT0_IRQn       <0=> Secure state <1=> Non-Secure state
//   <o.8>  FDCAN1_IT1_IRQn       <0=> Secure state <1=> Non-Secure state
//   <o.9>  TIM1_BRK_IRQn         <0=> Secure state <1=> Non-Secure state
//   <o.10> TIM1_UP_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.11> TIM1_TRG_COM_IRQn     <0=> Secure state <1=> Non-Secure state
//   <o.12> TIM1_CC_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.13> TIM2_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.14> TIM3_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.15> TIM4_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.16> TIM5_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.17> TIM6_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.18> TIM7_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.19> TIM8_BRK_IRQn         <0=> Secure state <1=> Non-Secure state
//   <o.20> TIM8_UP_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.21> TIM8_TRG_COM_IRQn     <0=> Secure state <1=> Non-Secure state
//   <o.22> TIM8_CC_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.23> I2C1_EV_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.24> I2C1_ER_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.25> I2C2_EV_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.26> I2C2_ER_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.27> SPI1_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.28> SPI2_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.29> USART1_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.30> USART2_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.31> USART3_IRQn           <0=> Secure state <1=> Non-Secure state
*/
#define NVIC_INIT_ITNS1_VAL 0x00000000

/*
//   </e>
*/

/*
//   <e>Initialize ITNS 2 (Interrupts 64..95)
*/
#define NVIC_INIT_ITNS2 1

/*
// Interrupts 64..95
//   <o.0>  UART4_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.1>  UART5_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.2>  LPUART1_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.3>  LPTIM1_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.4>  LPTIM2_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.5>  TIM15_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.6>  TIM16_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.7>  TIM17_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.8>  COMP_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.9>  OTG_HS_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.10> CRS_IRQn              <0=> Secure state <1=> Non-Secure state
//   <o.11> FMC_IRQn              <0=> Secure state <1=> Non-Secure state
//   <o.12> OCTOSPI1_IRQn         <0=> Secure state <1=> Non-Secure state
//   <o.13> PWR_S3WU_IRQn         <0=> Secure state <1=> Non-Secure state
//   <o.14> SDMMC1_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.15> SDMMC2_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.16> GPDMA1_Channel8_IRQn  <0=> Secure state <1=> Non-Secure state
//   <o.17> GPDMA1_Channel9_IRQn  <0=> Secure state <1=> Non-Secure state
//   <o.18> GPDMA1_Channel10_IRQn <0=> Secure state <1=> Non-Secure state
//   <o.19> GPDMA1_Channel11_IRQn <0=> Secure state <1=> Non-Secure state
//   <o.20> GPDMA1_Channel12_IRQn <0=> Secure state <1=> Non-Secure state
//   <o.21> GPDMA1_Channel13_IRQn <0=> Secure state <1=> Non-Secure state
//   <o.22> GPDMA1_Channel14_IRQn <0=> Secure state <1=> Non-Secure state
//   <o.23> GPDMA1_Channel15_IRQn <0=> Secure state <1=> Non-Secure state
//   <o.24> I2C3_EV_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.25> I2C3_ER_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.26> SAI1_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.27> SAI2_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.28> TSC_IRQn              <0=> Secure state <1=> Non-Secure state
//   <o.30> RNG_IRQn              <0=> Secure state <1=> Non-Secure state
//   <o.31> FPU_IRQn              <0=> Secure state <1=> Non-Secure state
*/
#define NVIC_INIT_ITNS2_VAL 0x00000000

/*
//   </e>
*/

/*
//   <e>Initialize ITNS 3 (Interrupts 96..127)
*/
#define NVIC_INIT_ITNS3 1

/*
// Interrupts 96..127
//   <o.0>  HASH_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.2>  LPTIM3_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.3>  SPI3_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.4>  I2C4_ER_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.5>  I2C4_EV_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.6>  MDF1_FLT0_IRQn        <0=> Secure state <1=> Non-Secure state
//   <o.7>  MDF1_FLT1_IRQn        <0=> Secure state <1=> Non-Secure state
//   <o.8>  MDF1_FLT2_IRQn        <0=> Secure state <1=> Non-Secure state
//   <o.9>  MDF1_FLT3_IRQn        <0=> Secure state <1=> Non-Secure state
//   <o.10> UCPD1_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.11> ICACHE_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.14> LPTIM4_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.15> DCACHE1_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.16> ADF1_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.17> ADC4_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.18> LPDMA1_Channel0_IRQn  <0=> Secure state <1=> Non-Secure state
//   <o.19> LPDMA1_Channel1_IRQn  <0=> Secure state <1=> Non-Secure state
//   <o.20> LPDMA1_Channel2_IRQn  <0=> Secure state <1=> Non-Secure state
//   <o.21> LPDMA1_Channel3_IRQn  <0=> Secure state <1=> Non-Secure state
//   <o.22> DMA2D_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.23> DCMI_PSSI_IRQn        <0=> Secure state <1=> Non-Secure state
//   <o.24> OCTOSPI2_IRQn         <0=> Secure state <1=> Non-Secure state
//   <o.25> MDF1_FLT4_IRQn        <0=> Secure state <1=> Non-Secure state
//   <o.26> MDF1_FLT5_IRQn        <0=> Secure state <1=> Non-Secure state
//   <o.27> CORDIC_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.28> FMAC_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.30> USART6_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.31> I2C5_ER_IRQn          <0=> Secure state <1=> Non-Secure state
*/
#define NVIC_INIT_ITNS3_VAL 0x00000000

/*
//   </e>
*/

/*
//   <e>Initialize ITNS 4 (Interrupts 109..138)
*/
#define NVIC_INIT_ITNS4 1

/*
// Interrupts 96..138
//   <o.0>  I2C5_EV_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.1>  I2C6_ER_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.2>  I2C6_EV_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.3>  HSPI1_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.4>  GPU2D_IRQn            <0=> Secure state <1=> Non-Secure state
//   <o.5>  GPU2D_ER_IRQn         <0=> Secure state <1=> Non-Secure state
//   <o.6>  GFXMMU_IRQn           <0=> Secure state <1=> Non-Secure state
//   <o.7>  LTDC_IRQn             <0=> Secure state <1=> Non-Secure state
//   <o.8>  LTDC_ER_IRQn          <0=> Secure state <1=> Non-Secure state
//   <o.9>  DSI_IRQn              <0=> Secure state <1=> Non-Secure state
//   <o.10> DCACHE2_IRQn          <0=> Secure state <1=> Non-Secure state
*/
#define NVIC_INIT_ITNS4_VAL 0x00000000

/*
//   </e>
*/

/*
// </h>
*/

/*
    max 8 SAU regions.
    SAU regions are defined in partition.h
 */

#define SAU_INIT_REGION(n)                              \
  SAU->RNR = (n & SAU_RNR_REGION_Msk);                  \
  SAU->RBAR = (SAU_INIT_START##n & SAU_RBAR_BADDR_Msk); \
  SAU->RLAR = (SAU_INIT_END##n & SAU_RLAR_LADDR_Msk) |  \
              ((SAU_INIT_NSC##n << SAU_RLAR_NSC_Pos) & SAU_RLAR_NSC_Msk) | 1U

extern void trustzone_init(void);

extern void trustzone_run(void);

#endif
#endif
