
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2016-2022 STMicroelectronics, all rights reserved
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
 *      PROJECT:   ST25R200 firmware
 *      Revision: 
 *      LANGUAGE:  ISO C99
 */

/*! \file st25r200_irq.c
 *
 *  \author Gustavo Patricio
 *
 *  \brief ST25R200 Interrupt handling
 *
 */

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/

#include "st25r200_irq.h"
#include "st25r200_com.h"
#include "st25r200.h"
#include "rfal_utils.h"

/*
 ******************************************************************************
 * LOCAL DATA TYPES
 ******************************************************************************
 */

/*! Holds current and previous interrupt callback pointer as well as current Interrupt status and mask */
typedef struct
{
    void      (*prevCallback)(void); /*!< call back function for ST25R200 interrupt          */
    void      (*callback)(void);     /*!< call back function for ST25R200 interrupt          */
    uint32_t  status;                /*!< latest interrupt status                             */
    uint32_t  mask;                  /*!< Interrupt mask. Negative mask = ST25R200 mask regs */
} st25r200Interrupt;


/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/

/*! Length of the interrupt registers       */
#define ST25R200_INT_REGS_LEN          ( (ST25R200_REG_IRQ3 - ST25R200_REG_IRQ1) + 1U )

/*
******************************************************************************
* GLOBAL VARIABLES
******************************************************************************
*/

static volatile st25r200Interrupt   st25r200interrupt; /*!< Instance of ST25R200 interrupt */

/*
******************************************************************************
* GLOBAL FUNCTIONS
******************************************************************************
*/
void st25r200InitInterrupts( void )
{
    platformIrqST25RPinInitialize();
    platformIrqST25RSetCallback( st25r200Isr );
    
    st25r200interrupt.callback     = NULL;
    st25r200interrupt.prevCallback = NULL;
    st25r200interrupt.status       = ST25R200_IRQ_MASK_NONE;
    st25r200interrupt.mask         = ST25R200_IRQ_MASK_NONE;
}


/*******************************************************************************/
void st25r200Isr( void )
{
    st25r200CheckForReceivedInterrupts();
    
    /* Check if callback is set and run it */
    if( NULL != st25r200interrupt.callback )
    {
        st25r200interrupt.callback();
    }
}


/*******************************************************************************/
void st25r200CheckForReceivedInterrupts( void )
{
    uint8_t  iregs[ST25R200_INT_REGS_LEN];
    uint32_t irqStatus;

#ifdef ST25R_POLL_IRQ
    /* Exit immediately in case of no IRQ */
    if( platformGpioIsLow( ST25R_INT_PORT, ST25R_INT_PIN ) )
    {
        return;
    }
#endif /* ST25R_POLL_IRQ */  
    
    /* Initialize iregs */
    irqStatus = ST25R200_IRQ_MASK_NONE;
    RFAL_MEMSET( iregs, (int32_t)(ST25R200_IRQ_MASK_ALL & 0xFFU), ST25R200_INT_REGS_LEN );
    
    /* In case the IRQ is Edge (not Level) triggered read IRQs until done */
    while( platformGpioIsHigh( ST25R_INT_PORT, ST25R_INT_PIN ) )
    {
       st25r200ReadMultipleRegisters( ST25R200_REG_IRQ1, iregs, ST25R200_INT_REGS_LEN );
       
       irqStatus |= (uint32_t)iregs[0];
       irqStatus |= (uint32_t)iregs[1]<<8;
       irqStatus |= (uint32_t)iregs[2]<<16;
    }

    /* Forward all interrupts, even masked ones to application */
    platformProtectST25RIrqStatus();
    st25r200interrupt.status |= irqStatus;
    platformUnprotectST25RIrqStatus();

    /* Send an IRQ event to LED handling */
    st25r200ledEvtIrq( st25r200interrupt.status );
}


/*******************************************************************************/
void st25r200ModifyInterrupts(uint32_t clr_mask, uint32_t set_mask)
{
    uint8_t  i;
    uint32_t old_mask;
    uint32_t new_mask;

    old_mask = st25r200interrupt.mask;
    new_mask = ((~old_mask & set_mask) | (old_mask & clr_mask));
    st25r200interrupt.mask &= ~clr_mask;
    st25r200interrupt.mask |= set_mask;
    
    for(i=0; i<ST25R200_INT_REGS_LEN; i++)
    { 
        if( ((new_mask >> (8U*i)) & 0xFFU) == 0U )
        {
            continue;
        }
        
        st25r200WriteRegister(ST25R200_REG_IRQ_MASK1 + i, (uint8_t)((st25r200interrupt.mask>>(8U*i)) & 0xFFU) );
    }
    return;
}


/*******************************************************************************/
uint32_t st25r200WaitForInterruptsTimed( uint32_t mask, uint16_t tmo )
{
    uint32_t tmrDelay;
    uint32_t status;
    
    tmrDelay = platformTimerCreate( tmo );
    
    /* Run until specific interrupt has happen or the timer has expired */
    do 
    {
    #ifdef ST25R_POLL_IRQ
        st25r200CheckForReceivedInterrupts();
    #endif /* ST25R_POLL_IRQ */ 
        
        status = (st25r200interrupt.status & mask);
    } while( ( (!platformTimerIsExpired( tmrDelay )) || (tmo == 0U)) && (status == 0U) );

    platformTimerDestroy( tmrDelay );
    
    status = st25r200interrupt.status & mask;
    
    platformProtectST25RIrqStatus();
    st25r200interrupt.status &= ~status;
    platformUnprotectST25RIrqStatus();
    
    return status;
}


/*******************************************************************************/
uint32_t st25r200GetInterrupt( uint32_t mask )
{
    uint32_t irqs;

    irqs = (st25r200interrupt.status & mask);
    if(irqs != ST25R200_IRQ_MASK_NONE)
    {
        platformProtectST25RIrqStatus();
        st25r200interrupt.status &= ~irqs;
        platformUnprotectST25RIrqStatus();
    }

    return irqs;
}


/*******************************************************************************/
void st25r200ClearAndEnableInterrupts( uint32_t mask )
{
    st25r200GetInterrupt( mask );
    st25r200EnableInterrupts( mask );
}


/*******************************************************************************/
void st25r200EnableInterrupts(uint32_t mask)
{
    st25r200ModifyInterrupts(mask, 0);
}


/*******************************************************************************/
void st25r200DisableInterrupts(uint32_t mask)
{
    st25r200ModifyInterrupts(0, mask);
}

/*******************************************************************************/
void st25r200ClearInterrupts( void )
{
    uint8_t iregs[ST25R200_INT_REGS_LEN];

    st25r200ReadMultipleRegisters(ST25R200_REG_IRQ1, iregs, ST25R200_INT_REGS_LEN);

    platformProtectST25RIrqStatus();
    st25r200interrupt.status = ST25R200_IRQ_MASK_NONE;
    platformUnprotectST25RIrqStatus();
    return;
}


/*******************************************************************************/
void st25r200IRQCallbackSet( void (*cb)(void) )
{
    st25r200interrupt.prevCallback = st25r200interrupt.callback;
    st25r200interrupt.callback     = cb;
}


/*******************************************************************************/
void st25r200IRQCallbackRestore( void )
{
    st25r200interrupt.callback     = st25r200interrupt.prevCallback;
    st25r200interrupt.prevCallback = NULL;
}

