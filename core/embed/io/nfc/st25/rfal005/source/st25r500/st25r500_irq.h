
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2023 STMicroelectronics, all rights reserved
  *
  * Unless required by applicable law or agreed to in writing, software
  * distributed under the License is distributed on an "AS IS" BASIS,
  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied,
  * AND SPECIFICALLY DISCLAIMING THE IMPLIED WARRANTIES OF MERCHANTABILITY,
  * FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
  * See the License for the specific language governing permissions and
  * limitations under the License.
  *
******************************************************************************/



/*
 *      PROJECT:   ST25R500 firmware
 *      Revision: 
 *      LANGUAGE:  ISO C99
 */

/*! \file st25r500_irq.h
 *
 *  \author Gustavo Patricio
 *
 *  \brief ST25R500 Interrupt handling
 *
 * \addtogroup RFAL
 * @{
 *
 * \addtogroup RFAL-HAL
 * \brief RFAL Hardware Abstraction Layer
 * @{
 *
 * \addtogroup ST25R500
 * \brief RFAL ST25R500 Driver
 * @{
 * 
 * \addtogroup ST25R500_IRQ
 * \brief RFAL ST25R500 IRQ
 * @{
 * 
 */

#ifndef ST25R500_IRQ_H
#define ST25R500_IRQ_H

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/

#include "rfal_platform.h"

/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/

#define ST25R500_IRQ_MASK_ALL             (uint32_t)(0xFFFFFFFFUL)  /*!< All ST25R500 interrupt sources                             */
#define ST25R500_IRQ_MASK_NONE            (uint32_t)(0x00000000UL)  /*!< No ST25R500 interrupt source                               */

/* Main interrupt register */
#define ST25R500_IRQ_MASK_SUBC_START      (uint32_t)(0x00000080U)   /*!< ST25R500 subcarrier start interrupt                        */
#define ST25R500_IRQ_MASK_COL             (uint32_t)(0x00000040U)   /*!< ST25R500 bit collision interrupt                           */
#define ST25R500_IRQ_MASK_WL              (uint32_t)(0x00000020U)   /*!< ST25R500 FIFO water level interrupt                        */
#define ST25R500_IRQ_MASK_RX_REST         (uint32_t)(0x00000010U)   /*!< ST25R500 automatic reception restart interrupt             */
#define ST25R500_IRQ_MASK_RXE             (uint32_t)(0x00000008U)   /*!< ST25R500 end of receive interrupt                          */
#define ST25R500_IRQ_MASK_RXS             (uint32_t)(0x00000004U)   /*!< ST25R500 start of receive interrupt                        */
#define ST25R500_IRQ_MASK_TXE             (uint32_t)(0x00000002U)   /*!< ST25R500 end of transmission interrupt                     */
#define ST25R500_IRQ_MASK_RX_ERR          (uint32_t)(0x00000001U)   /*!< ST25R500 Reception error interrupt                         */

/* Timer and Error interrupt register */
#define ST25R500_IRQ_MASK_GPE             (uint32_t)(0x00008000U)   /*!< ST25R500 general purpose timer expired interrupt           */
#define ST25R500_IRQ_MASK_NRE             (uint32_t)(0x00004000U)   /*!< ST25R500 no-response timer expired interrupt               */
#define ST25R500_IRQ_MASK_WPT_STOP        (uint32_t)(0x00002000U)   /*!< ST25R500 WPT stop received interrupt                       */
#define ST25R500_IRQ_MASK_WPT_FOD         (uint32_t)(0x00001000U)   /*!< ST25R500 WPT FOD received interrupt                        */
#define ST25R500_IRQ_MASK_RFU             (uint32_t)(0x00000800U)   /*!< ST25R500 RFU                                               */
#define ST25R500_IRQ_MASK_CE_SC           (uint32_t)(0x00000400U)   /*!< ST25R500 CE state change interrupt                         */
#define ST25R500_IRQ_MASK_RXE_CE          (uint32_t)(0x00000200U)   /*!< ST25R500 end of reception in CE interrupt                  */
#define ST25R500_IRQ_MASK_NFCT            (uint32_t)(0x00000100U)   /*!< ST25R500 bit rate was recognized interrupt                 */

/* Wake-up interrupt register */
#define ST25R500_IRQ_MASK_WUTME           (uint32_t)(0x00800000U)   /*!< ST25R500 WU Measure event interrupt                        */
#define ST25R500_IRQ_MASK_EOF             (uint32_t)(0x00400000U)   /*!< ST25R500 External Field Off interrupt                      */
#define ST25R500_IRQ_MASK_EON             (uint32_t)(0x00200000U)   /*!< ST25R500 External Field On interrupt                       */
#define ST25R500_IRQ_MASK_DCT             (uint32_t)(0x00100000U)   /*!< ST25R500 termination of direct command interrupt           */
#define ST25R500_IRQ_MASK_WUQ             (uint32_t)(0x00080000U)   /*!< ST25R500 wake-up Q-Channel interrupt                       */
#define ST25R500_IRQ_MASK_WUI             (uint32_t)(0x00040000U)   /*!< ST25R500 wake-up I-Channel interrupt                       */
#define ST25R500_IRQ_MASK_WUT             (uint32_t)(0x00020000U)   /*!< ST25R500 wake-up timer interrupt                           */
#define ST25R500_IRQ_MASK_OSC             (uint32_t)(0x00010000U)   /*!< ST25R500 oscillator stable interrupt                       */

/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/


/*! 
 *****************************************************************************
 *  \brief  Wait until an ST25R500 interrupt occurs
 *
 *  This function is used to access the ST25R500 interrupt flags. Use this
 *  to wait for max. \a tmo milliseconds for the \b first interrupt indicated
 *  with mask \a mask to occur.
 *
 *  \param[in] mask : mask indicating the interrupts to wait for.
 *  \param[in] tmo : time in milliseconds until timeout occurs. If set to 0
 *                   the functions waits forever.
 *
 *  \return : 0 if timeout occured otherwise a mask indicating the cleared
 *              interrupts.
 *
 *****************************************************************************
 */
uint32_t st25r500WaitForInterruptsTimed( uint32_t mask, uint16_t tmo );

/*! 
 *****************************************************************************
 *  \brief  Get status for the given interrupt
 *
 *  This function is used to check whether the interrupt given by \a mask
 *  has occured. If yes the interrupt gets cleared. This function returns
 *  only status bits which are inside \a mask.
 *
 *  \param[in] mask : mask indicating the interrupt to check for.
 *
 *  \return the mask of the interrupts occurred
 *
 *****************************************************************************
 */
uint32_t st25r500GetInterrupt( uint32_t mask );

/*! 
 *****************************************************************************
 *  \brief  Init the 200 interrupt
 *
 *  This function is used to check whether the interrupt given by \a mask
 *  has occured. 
 *
 *****************************************************************************
 */
void st25r500InitInterrupts( void );

/*! 
 *****************************************************************************
 *  \brief  Modifies the Interrupt
 *
 *  This function modifies the interrupt
 *  
 *  \param[in] clr_mask : bit mask to be cleared on the interrupt mask 
 *  \param[in] set_mask : bit mask to be set on the interrupt mask 
 *****************************************************************************
 */
void st25r500ModifyInterrupts( uint32_t clr_mask, uint32_t set_mask );

/*! 
 *****************************************************************************
 *  \brief Checks received interrupts
 *
 *  Checks received interrupts and saves the result into global params
 *****************************************************************************
 */
void st25r500CheckForReceivedInterrupts( void );

/*! 
 *****************************************************************************
 *  \brief  ISR Service routine
 *
 *  This function modiefies the interupt
 *****************************************************************************
 */
void  st25r500Isr( void );

/*! 
 *****************************************************************************
 *  \brief  Enable a given ST25R500 Interrupt source
 *
 *  This function enables all interrupts given by \a mask, 
 *  ST25R500_IRQ_MASK_ALL enables all interrupts.
 *
 *  \param[in] mask: mask indicating the interrupts to be enabled
 *
 *****************************************************************************
 */
void st25r500EnableInterrupts( uint32_t mask );

/*! 
 *****************************************************************************
 *  \brief  Disable one or more a given ST25R500 Interrupt sources
 *
 *  This function disables all interrupts given by \a mask. 0xff disables all.
 *
 *  \param[in] mask: mask indicating the interrupts to be disabled.
 *
 *****************************************************************************
 */
void st25r500DisableInterrupts( uint32_t mask );

/*! 
 *****************************************************************************
 *  \brief  Clear all ST25R500 irq flags
 *
 *****************************************************************************
 */
void st25r500ClearInterrupts( void );

/*! 
 *****************************************************************************
 *  \brief  Clears and then enables the given ST25R500 Interrupt sources
 *
 *  \param[in] mask: mask indicating the interrupts to be cleared and enabled
 *****************************************************************************
 */
void st25r500ClearAndEnableInterrupts( uint32_t mask );

/*! 
 *****************************************************************************
 *  \brief  Sets IRQ callback for the ST25R500 interrupt
 *
 *  \param[in] cb: pointer to the callback method
 *
 *****************************************************************************
 */
void st25r500IRQCallbackSet( void (*cb)( void ) );

/*! 
 *****************************************************************************
 *  \brief  Sets IRQ callback for the ST25R500 interrupt
 *
 *****************************************************************************
 */
void st25r500IRQCallbackRestore( void );

#endif /* ST25R500_IRQ_H */

/**
  * @}
  *
  * @}
  *
  * @}
  * 
  * @}
  */
