
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2016-2023 STMicroelectronics, all rights reserved
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

/*! \file st25r500_irq.c
 *
 *  \author Gustavo Patricio
 *
 *  \brief ST25R500 Interrupt handling
 *
 */

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/

#include "st25r500_irq.h"
#include "st25r500_com.h"
#include "st25r500.h"
#include "rfal_utils.h"

/*
 ******************************************************************************
 * LOCAL DATA TYPES
 ******************************************************************************
 */

/*! Holds current and previous interrupt callback pointer as well as current Interrupt status and mask */
typedef struct
{
    void      (*prevCallback)(void); /*!< call back function for ST25R500 interrupt          */
    void      (*callback)(void);     /*!< call back function for ST25R500 interrupt          */
    uint32_t  status;                /*!< latest interrupt status                             */
    uint32_t  mask;                  /*!< Interrupt mask. Negative mask = ST25R500 mask regs */
} st25r500Interrupt;


/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/

/*! Length of the interrupt registers       */
#define ST25R500_INT_REGS_LEN          ( (ST25R500_REG_IRQ3 - ST25R500_REG_IRQ1) + 1U )

/*
******************************************************************************
* GLOBAL VARIABLES
******************************************************************************
*/

static volatile st25r500Interrupt   st25r500interrupt; /*!< Instance of ST25R500 interrupt */

/*
******************************************************************************
* GLOBAL FUNCTIONS
******************************************************************************
*/
void st25r500InitInterrupts( void )
{
    platformIrqST25RPinInitialize();
    platformIrqST25RSetCallback( st25r500Isr );
    
    st25r500interrupt.callback     = NULL;
    st25r500interrupt.prevCallback = NULL;
    st25r500interrupt.status       = ST25R500_IRQ_MASK_NONE;
    st25r500interrupt.mask         = ST25R500_IRQ_MASK_NONE;
}


/*******************************************************************************/
void st25r500Isr( void )
{
    st25r500CheckForReceivedInterrupts();
    
    /* Check if callback is set and run it */
    if( NULL != st25r500interrupt.callback )
    {
        st25r500interrupt.callback();
    }
}


/*******************************************************************************/
void st25r500CheckForReceivedInterrupts( void )
{
    uint8_t  iregs[ST25R500_INT_REGS_LEN];
    uint32_t irqStatus;

#ifdef ST25R_POLL_IRQ
    /* Exit immediately in case of no IRQ */
    if( platformGpioIsLow( ST25R_INT_PORT, ST25R_INT_PIN ) )
    {
        return;
    }
#endif /* ST25R_POLL_IRQ */  
    
    /* Initialize iregs */
    irqStatus = ST25R500_IRQ_MASK_NONE;
    RFAL_MEMSET( iregs, (int32_t)(ST25R500_IRQ_MASK_ALL & 0xFFU), ST25R500_INT_REGS_LEN );
    
    /* In case the IRQ is Edge (not Level) triggered read IRQs until done */
    while( platformGpioIsHigh( ST25R_INT_PORT, ST25R_INT_PIN ) )
    {
       st25r500ReadMultipleRegisters( ST25R500_REG_IRQ1, iregs, ST25R500_INT_REGS_LEN );
       
       irqStatus |= (uint32_t)iregs[0];
       irqStatus |= (uint32_t)iregs[1]<<8;
       irqStatus |= (uint32_t)iregs[2]<<16;
    }

    /* Forward all interrupts, even masked ones to application */
    platformProtectST25RIrqStatus();
    st25r500interrupt.status |= irqStatus;
    platformUnprotectST25RIrqStatus();

    /* Send an IRQ event to LED handling */
    st25r500ledEvtIrq( st25r500interrupt.status );
}


/*******************************************************************************/
void st25r500ModifyInterrupts(uint32_t clr_mask, uint32_t set_mask)
{
    uint8_t  i;
    uint32_t old_mask;
    uint32_t new_mask;
    

    old_mask = st25r500interrupt.mask;
    new_mask = ((~old_mask & set_mask) | (old_mask & clr_mask));
    st25r500interrupt.mask &= ~clr_mask;
    st25r500interrupt.mask |= set_mask;
    
    for(i=0; i<ST25R500_INT_REGS_LEN; i++)
    { 
        if( ((new_mask >> (8U*i)) & 0xFFU) == 0U )
        {
            continue;
        }
        
        st25r500WriteRegister(ST25R500_REG_IRQ_MASK1 + i, (uint8_t)((st25r500interrupt.mask>>(8U*i)) & 0xFFU) );
    }
    return;
}


/*******************************************************************************/
uint32_t st25r500WaitForInterruptsTimed( uint32_t mask, uint16_t tmo )
{
    uint32_t tmrDelay;
    uint32_t status;
    
    tmrDelay = platformTimerCreate( tmo );
    
    /* Run until specific interrupt has happen or the timer has expired */
    do 
    {
    #ifdef ST25R_POLL_IRQ
        st25r500CheckForReceivedInterrupts();
    #endif /* ST25R_POLL_IRQ */ 
        
        status = (st25r500interrupt.status & mask);
    } while( ( (!platformTimerIsExpired( tmrDelay )) || (tmo == 0U)) && (status == 0U) );

    platformTimerDestroy( tmrDelay );
    
    status = st25r500interrupt.status & mask;
    
    platformProtectST25RIrqStatus();
    st25r500interrupt.status &= ~status;
    platformUnprotectST25RIrqStatus();
    
    return status;
}


/*******************************************************************************/
uint32_t st25r500GetInterrupt( uint32_t mask )
{
    uint32_t irqs;

    irqs = (st25r500interrupt.status & mask);
    if(irqs != ST25R500_IRQ_MASK_NONE)
    {
        platformProtectST25RIrqStatus();
        st25r500interrupt.status &= ~irqs;
        platformUnprotectST25RIrqStatus();
    }

    return irqs;
}


/*******************************************************************************/
void st25r500ClearAndEnableInterrupts( uint32_t mask )
{
    st25r500GetInterrupt( mask );
    st25r500EnableInterrupts( mask );
}


/*******************************************************************************/
void st25r500EnableInterrupts(uint32_t mask)
{
    st25r500ModifyInterrupts(mask, 0);
}


/*******************************************************************************/
void st25r500DisableInterrupts(uint32_t mask)
{
    st25r500ModifyInterrupts(0, mask);
}


/*******************************************************************************/
void st25r500ClearInterrupts( void )
{
    uint8_t iregs[ST25R500_INT_REGS_LEN];

    st25r500ReadMultipleRegisters(ST25R500_REG_IRQ1, iregs, ST25R500_INT_REGS_LEN);

    platformProtectST25RIrqStatus();
    st25r500interrupt.status = ST25R500_IRQ_MASK_NONE;
    platformUnprotectST25RIrqStatus();
    return;
}


/*******************************************************************************/
void st25r500IRQCallbackSet( void (*cb)(void) )
{
    st25r500interrupt.prevCallback = st25r500interrupt.callback;
    st25r500interrupt.callback     = cb;
}


/*******************************************************************************/
void st25r500IRQCallbackRestore( void )
{
    st25r500interrupt.callback     = st25r500interrupt.prevCallback;
    st25r500interrupt.prevCallback = NULL;
}

