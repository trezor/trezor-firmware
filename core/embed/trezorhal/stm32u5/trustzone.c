#include "trustzone.h"

#ifdef BOARDLOADER

#include STM32_HAL_H

void trustzone_init(void) {
#if defined(__SAUREGION_PRESENT) && (__SAUREGION_PRESENT == 1U)

#if defined(SAU_INIT_REGION0) && (SAU_INIT_REGION0 == 1U)
  SAU_INIT_REGION(0);
#endif

#if defined(SAU_INIT_REGION1) && (SAU_INIT_REGION1 == 1U)
  SAU_INIT_REGION(1);
#endif

#if defined(SAU_INIT_REGION2) && (SAU_INIT_REGION2 == 1U)
  SAU_INIT_REGION(2);
#endif

#if defined(SAU_INIT_REGION3) && (SAU_INIT_REGION3 == 1U)
  SAU_INIT_REGION(3);
#endif

#if defined(SAU_INIT_REGION4) && (SAU_INIT_REGION4 == 1U)
  SAU_INIT_REGION(4);
#endif

#if defined(SAU_INIT_REGION5) && (SAU_INIT_REGION5 == 1U)
  SAU_INIT_REGION(5);
#endif

#if defined(SAU_INIT_REGION6) && (SAU_INIT_REGION6 == 1U)
  SAU_INIT_REGION(6);
#endif

#if defined(SAU_INIT_REGION7) && (SAU_INIT_REGION7 == 1U)
  SAU_INIT_REGION(7);
#endif

  /* repeat this for all possible SAU regions */

#endif /* defined (__SAUREGION_PRESENT) && (__SAUREGION_PRESENT == 1U) */

#if defined(SAU_INIT_CTRL) && (SAU_INIT_CTRL == 1U)
  SAU->CTRL =
      ((SAU_INIT_CTRL_ENABLE << SAU_CTRL_ENABLE_Pos) & SAU_CTRL_ENABLE_Msk) |
      ((SAU_INIT_CTRL_ALLNS << SAU_CTRL_ALLNS_Pos) & SAU_CTRL_ALLNS_Msk);
#endif

#if defined(SCB_CSR_AIRCR_INIT) && (SCB_CSR_AIRCR_INIT == 1U)
  SCB->SCR = (SCB->SCR & ~(SCB_SCR_SLEEPDEEPS_Msk)) |
             ((SCB_CSR_DEEPSLEEPS_VAL << SCB_SCR_SLEEPDEEPS_Pos) &
              SCB_SCR_SLEEPDEEPS_Msk);

  SCB->AIRCR =
      (SCB->AIRCR & ~(SCB_AIRCR_VECTKEY_Msk | SCB_AIRCR_SYSRESETREQS_Msk |
                      SCB_AIRCR_BFHFNMINS_Msk | SCB_AIRCR_PRIS_Msk)) |
      ((0x05FAU << SCB_AIRCR_VECTKEY_Pos) & SCB_AIRCR_VECTKEY_Msk) |
      ((SCB_AIRCR_SYSRESETREQS_VAL << SCB_AIRCR_SYSRESETREQS_Pos) &
       SCB_AIRCR_SYSRESETREQS_Msk) |
      ((SCB_AIRCR_PRIS_VAL << SCB_AIRCR_PRIS_Pos) & SCB_AIRCR_PRIS_Msk) |
      ((SCB_AIRCR_BFHFNMINS_VAL << SCB_AIRCR_BFHFNMINS_Pos) &
       SCB_AIRCR_BFHFNMINS_Msk);
#endif /* defined (SCB_CSR_AIRCR_INIT) && (SCB_CSR_AIRCR_INIT == 1U) */

#if defined(__FPU_USED) && (__FPU_USED == 1U) && defined(TZ_FPU_NS_USAGE) && \
    (TZ_FPU_NS_USAGE == 1U)

  SCB->NSACR = (SCB->NSACR & ~(SCB_NSACR_CP10_Msk | SCB_NSACR_CP11_Msk)) |
               ((SCB_NSACR_CP10_11_VAL << SCB_NSACR_CP10_Pos) &
                (SCB_NSACR_CP10_Msk | SCB_NSACR_CP11_Msk));

  FPU->FPCCR = (FPU->FPCCR & ~(FPU_FPCCR_TS_Msk | FPU_FPCCR_CLRONRETS_Msk |
                               FPU_FPCCR_CLRONRET_Msk)) |
               ((FPU_FPCCR_TS_VAL << FPU_FPCCR_TS_Pos) & FPU_FPCCR_TS_Msk) |
               ((FPU_FPCCR_CLRONRETS_VAL << FPU_FPCCR_CLRONRETS_Pos) &
                FPU_FPCCR_CLRONRETS_Msk) |
               ((FPU_FPCCR_CLRONRET_VAL << FPU_FPCCR_CLRONRET_Pos) &
                FPU_FPCCR_CLRONRET_Msk);
#endif

#if defined(NVIC_INIT_ITNS0) && (NVIC_INIT_ITNS0 == 1U)
  NVIC->ITNS[0] = NVIC_INIT_ITNS0_VAL;
#endif

#if defined(NVIC_INIT_ITNS1) && (NVIC_INIT_ITNS1 == 1U)
  NVIC->ITNS[1] = NVIC_INIT_ITNS1_VAL;
#endif

#if defined(NVIC_INIT_ITNS2) && (NVIC_INIT_ITNS2 == 1U)
  NVIC->ITNS[2] = NVIC_INIT_ITNS2_VAL;
#endif

#if defined(NVIC_INIT_ITNS3) && (NVIC_INIT_ITNS3 == 1U)
  NVIC->ITNS[3] = NVIC_INIT_ITNS3_VAL;
#endif

#if defined(NVIC_INIT_ITNS4) && (NVIC_INIT_ITNS4 == 1U)
  NVIC->ITNS[4] = NVIC_INIT_ITNS4_VAL;
#endif
}

void trustzone_run(void) {
  uint32_t index;
  MPCBB_ConfigTypeDef MPCBB_desc;

  /* Enable GTZC peripheral clock */
  __HAL_RCC_GTZC1_CLK_ENABLE();
  __HAL_RCC_GTZC2_CLK_ENABLE();

  /* -------------------------------------------------------------------------*/
  /*                   Memory isolation configuration                         */
  /* Initializes the memory that secure application books for non secure      */
  /* -------------------------------------------------------------------------*/

  /* -------------------------------------------------------------------------*/
  /* Internal RAM :                                                  */
  /* The booking is done through GTZC MPCBB.                         */
  /* Internal SRAMs are secured by default and configured by block   */
  /* of 512 bytes.                                                   */

  MPCBB_desc.SecureRWIllegalMode = GTZC_MPCBB_SRWILADIS_DISABLE;
  MPCBB_desc.InvertSecureState = GTZC_MPCBB_INVSECSTATE_NOT_INVERTED;
  MPCBB_desc.AttributeConfig.MPCBB_LockConfig_array[0] =
      0x00000000U; /* Unlocked configuration */

  for (index = 0; index < 52; index++) {
    MPCBB_desc.AttributeConfig.MPCBB_SecConfig_array[index] = 0xFFFFFFFFU;
    MPCBB_desc.AttributeConfig.MPCBB_PrivConfig_array[index] = 0x00000000U;
  }

  HAL_GTZC_MPCBB_ConfigMem(SRAM1_BASE, &MPCBB_desc);
  HAL_GTZC_MPCBB_ConfigMem(SRAM2_BASE, &MPCBB_desc);
  HAL_GTZC_MPCBB_ConfigMem(SRAM3_BASE, &MPCBB_desc);
  HAL_GTZC_MPCBB_ConfigMem(SRAM4_BASE, &MPCBB_desc);
  HAL_GTZC_MPCBB_ConfigMem(SRAM5_BASE, &MPCBB_desc);

  /* -------------------------------------------------------------------------*/
  /* Internal Flash */
  /* The booking is done in both IDAU/SAU and FLASH interface */

  /* Flash memory is secured by default and modified with Option Byte Loading */
  /* Insure SECWM2_PSTRT > SECWM2_PEND in order to have all Bank2 non-secure  */

  /* -------------------------------------------------------------------------*/
  /* External OctoSPI memory */
  /* The booking is done in both IDAU/SAU and GTZC MPCWM interface */

  /* Default secure configuration */
  /* Else need to use HAL_GTZC_TZSC_MPCWM_ConfigMemAttributes() */

  /* -------------------------------------------------------------------------*/
  /* External NOR/FMC memory */
  /* The booking is done in both IDAU/SAU and GTZC MPCWM interface */

  /* Default secure configuration */
  /* Else need to use HAL_GTZC_TZSC_MPCWM_ConfigMemAttributes() */

  /* -------------------------------------------------------------------------*/
  /* External NAND/FMC memory */
  /* The booking is done in both IDAU/SAU and GTZC MPCWM interface */

  /* Default secure configuration */
  /* Else need to use HAL_GTZC_TZSC_MPCWM_ConfigMemAttributes() */

  /* -------------------------------------------------------------------------*/
  /*                   Peripheral isolation configuration                     */
  /* Initializes the peripherals and features that secure application books   */
  /* for secure (RCC, PWR, RTC, EXTI, DMA, OTFDEC, etc..) or leave them to    */
  /* non-secure (GPIO (secured by default))                                   */
  /* -------------------------------------------------------------------------*/

  HAL_GTZC_TZSC_ConfigPeriphAttributes(GTZC_PERIPH_LTDC, GTZC_TZSC_PERIPH_SEC);
  HAL_GTZC_TZSC_ConfigPeriphAttributes(GTZC_PERIPH_DSI, GTZC_TZSC_PERIPH_SEC);
  HAL_GTZC_TZSC_ConfigPeriphAttributes(GTZC_PERIPH_GFXMMU,
                                       GTZC_TZSC_PERIPH_SEC);
  HAL_GTZC_TZSC_ConfigPeriphAttributes(GTZC_PERIPH_GFXMMU_REG,
                                       GTZC_TZSC_PERIPH_SEC);
  HAL_GTZC_TZSC_ConfigPeriphAttributes(GTZC_PERIPH_DMA2D, GTZC_TZSC_PERIPH_SEC);

  /* Clear all illegal access flags in GTZC TZIC */
  HAL_GTZC_TZIC_ClearFlag(GTZC_PERIPH_ALL);

  /* Enable all illegal access interrupts in GTZC TZIC */
  HAL_GTZC_TZIC_EnableIT(GTZC_PERIPH_ALL);

  /* Enable GTZC secure interrupt */
  HAL_NVIC_SetPriority(GTZC_IRQn, 0, 0); /* Highest priority level */
  HAL_NVIC_EnableIRQ(GTZC_IRQn);
}
#endif
