
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2022 STMicroelectronics, all rights reserved
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

/*! \file st25r200.c
 *
 *  \author Gustavo Patricio
 *
 *  \brief ST25R200 High Level interface
 *
 */

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/

#include "st25r200.h"
#include "st25r200_com.h"
#include "st25r200_irq.h"
#include "rfal_utils.h"

/*
 ******************************************************************************
 * ENABLE SWITCH
 ******************************************************************************
 */
 
#ifndef ST25R200
#error "RFAL: Missing ST25R device selection. Please globally define ST25R200."
#endif /* ST25R200 */

/*
******************************************************************************
* LOCAL DEFINES
******************************************************************************
*/

#define ST25R200_SUPPLY_THRESHOLD            3600U   /*!< Power supply measure threshold between 3.3V or 5V                   */
#define ST25R200_NRT_MAX                     0xFFFFU /*!< Max Register value of NRT                                           */

#define ST25R200_RESET_DUR                   1U      /*!< Reset high duration                                                 */
#define ST25R200_TOUT_MEASUREMENT            2U      /*!< Max duration time of WU Measure|Calibration                         */
#define ST25R200_TOUT_OSC_STABLE             5U      /*!< Timeout for Oscillator to get stable                                */
#define ST25R200_TOUT_ADJUST_REGULATORS      10U     /*!< Max Adjust Regulators duration                                      */ 
#define ST25R200_TOUT_AGD_OK                 2U      /*!< Max time for AGD to become stable                                   */ 

#define ST25R200_TEST_REG_PATTERN            0x33U   /*!< Register Read Write test pattern used during selftest               */
#define ST25R200_TEST_WU_TOUT                11U     /*!< Timeout used on WU timer during self test                           */
#define ST25R200_TEST_TMR_TOUT               20U     /*!< Timeout used during self test                                       */
#define ST25R200_TEST_TMR_TOUT_DELTA         2U      /*!< Timeout used during self test                                       */
#define ST25R200_TEST_TMR_TOUT_8FC           (ST25R200_TEST_TMR_TOUT * 1695U)  /*!< Timeout in 8/fc                           */

#define ST25R200_TEST_FD_TRESHOLD            60U     /*!< External carrier presence treshold                                 */

/*
******************************************************************************
* LOCAL CONSTANTS
******************************************************************************
*/

/*
******************************************************************************
* LOCAL VARIABLES
******************************************************************************
*/

static uint32_t gST25R200NRT_64fcs;

/*
******************************************************************************
* LOCAL FUNCTION PROTOTYPES
******************************************************************************
*/
static ReturnCode st25r200WaitAgd( void );

/*
 ******************************************************************************
 * LOCAL FUNCTION
 ******************************************************************************
 */
 
/*******************************************************************************/
static ReturnCode st25r200WaitAgd( void )
{
    uint32_t ts;
    
    /* Wait for AGD to become stable whithin a max ST25R200_TOUT_AGD_OK */
    ts = platformGetSysTick();
    while( (platformGetSysTick() < (ts + ST25R200_TOUT_AGD_OK)) )
    {
        if( st25r200CheckReg( ST25R200_REG_DISPLAY1, ST25R200_REG_DISPLAY1_agd_ok, ST25R200_REG_DISPLAY1_agd_ok ) )
        {
            return RFAL_ERR_NONE;
        }
    }
    
    return RFAL_ERR_SYSTEM;
}


/*
******************************************************************************
* GLOBAL FUNCTIONS
******************************************************************************
*/

ReturnCode st25r200Initialize( void )
{
    ReturnCode ret;
    
    /* Ensure a defined chip select state */
    platformSpiDeselect();

#ifdef ST25R_RESET_PIN
    /* Reset the ST25R200 using the RESET pin */
    platformGpioSet( ST25R_RESET_PORT, ST25R_RESET_PIN );
    platformDelay( ST25R200_RESET_DUR );
    platformGpioClear( ST25R_RESET_PORT, ST25R_RESET_PIN );
    platformDelay( ST25R200_RESET_DUR );
#endif /* ST25R_RESET_PIN */
    
    /* Set default state on the ST25R200 */
    st25r200ExecuteCommand( ST25R200_CMD_SET_DEFAULT );
    if( !st25r200CheckChipID( NULL ) )
    {
        platformErrorHandle();
        return RFAL_ERR_HW_MISMATCH;
    }
    
    st25r200InitInterrupts();
    st25r200ledInit();
    
    gST25R200NRT_64fcs = 0;


#ifdef ST25R_SELFTEST
    
    /******************************************************************************
     * Check communication interface: 
     *  - write a pattern in a register
     *  - reads back the register value
     *  - return RFAL_ERR_IO in case the read value is different
     */
    st25r200WriteRegister( ST25R200_REG_WAKEUP_CONF2, ST25R200_TEST_REG_PATTERN );
    if( !st25r200CheckReg( ST25R200_REG_WAKEUP_CONF2, 0xFFU, ST25R200_TEST_REG_PATTERN ) )
    {
        platformErrorHandle();
        return RFAL_ERR_IO;
    }
    
    /* Restore default value */
    st25r200WriteRegister( ST25R200_REG_WAKEUP_CONF2, 0x00U );

    /*
     * Check IRQ Handling:
     *  - use the Wake-up timer to trigger an IRQ
     *  - wait the Wake-up timer interrupt
     *  - return RFAL_ERR_TIMEOUT when the Wake-up timer interrupt is not received
     */
    st25r200WriteRegister( ST25R200_REG_WAKEUP_CONF1, ST25R200_REG_WAKEUP_CONF1_wuti );
    st25r200EnableInterrupts( ST25R200_IRQ_MASK_WUT );
    st25r200ExecuteCommand( ST25R200_CMD_START_WUT );
    
    if( st25r200WaitForInterruptsTimed(ST25R200_IRQ_MASK_WUT, ST25R200_TEST_WU_TOUT) == 0U )
    {
        platformErrorHandle();
        return RFAL_ERR_TIMEOUT;
    }
    
    st25r200DisableInterrupts( ST25R200_IRQ_MASK_WUT );
    st25r200WriteRegister( ST25R200_REG_WAKEUP_CONF1, 0x00U );
    /*******************************************************************************/
    
#endif /* ST25R_SELFTEST */


    /* Enable Oscillator and wait until it gets stable */
    RFAL_EXIT_ON_ERR( ret, st25r200OscOn() );
    
    /* Make sure Transmitter and Receiver are disabled */
    st25r200TxRxOff();
    
    
#ifdef ST25R_SELFTEST_TIMER
    /******************************************************************************
     * Check SW timer operation :
     *  - use the General Purpose timer to measure an amount of time
     *  - test whether an interrupt is seen when less time was given
     *  - test whether an interrupt is seen when sufficient time was given
     */
    
    st25r200EnableInterrupts( ST25R200_IRQ_MASK_GPE );
    st25r200SetStartGPTimer( (uint16_t)ST25R200_TEST_TMR_TOUT_8FC, ST25R200_REG_NRT_GPT_CONF_gptc_no_trigger);
    if( st25r200WaitForInterruptsTimed( ST25R200_IRQ_MASK_GPE, (ST25R200_TEST_TMR_TOUT - ST25R200_TEST_TMR_TOUT_DELTA)) != 0U )
    {
        platformErrorHandle();
        return RFAL_ERR_SYSTEM;
    }
    
    /* Stop all activities to stop the GP timer */
    st25r200ExecuteCommand( ST25R200_CMD_STOP );
    st25r200ClearAndEnableInterrupts( ST25R200_IRQ_MASK_GPE );
    st25r200SetStartGPTimer( (uint16_t)ST25R200_TEST_TMR_TOUT_8FC, ST25R200_REG_NRT_GPT_CONF_gptc_no_trigger );
    if(st25r200WaitForInterruptsTimed( ST25R200_IRQ_MASK_GPE, (ST25R200_TEST_TMR_TOUT + ST25R200_TEST_TMR_TOUT_DELTA)) == 0U )
    {
        platformErrorHandle();
        return RFAL_ERR_SYSTEM;
    }
    
    /* Stop all activities to stop the GP timer */
    st25r200ExecuteCommand( ST25R200_CMD_STOP );
    /*******************************************************************************/
#endif /* ST25R_SELFTEST_TIMER */
    
    
    /* After reset all interrupts are enabled, so disable them at first */
    st25r200DisableInterrupts( ST25R200_IRQ_MASK_ALL );
    
    /* And clear them, just to be sure */
    st25r200ClearInterrupts();
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
void st25r200Deinitialize( void )
{
    /* Stop any ongoing activity */
    st25r200ExecuteCommand( ST25R200_CMD_STOP );
    st25r200DisableInterrupts( ST25R200_IRQ_MASK_ALL );    

    /* Set the device in PD mode */
    st25r200ClrRegisterBits( ST25R200_REG_OPERATION, ( ST25R200_REG_OPERATION_en    | ST25R200_REG_OPERATION_rx_en | 
                                                       ST25R200_REG_OPERATION_wu_en | ST25R200_REG_OPERATION_tx_en | ST25R200_REG_OPERATION_am_en) );

    return;
}


/*******************************************************************************/
ReturnCode st25r200OscOn( void )
{
    ReturnCode ret;
    uint8_t    reg;
    
    /* Check if oscillator is already turned on and stable                                              */
    /* Use ST25R200_REG_OP_CONTROL_en instead of ST25R200_REG_AUX_DISPLAY_osc_ok to be on the safe side */
    if( !st25r200IsOscOn() )
    {
        /* Clear any eventual previous oscillator frequency stable IRQ and enable it */
        st25r200ClearAndEnableInterrupts( ST25R200_IRQ_MASK_OSC );
        
        /* Clear any oscillator IRQ that was potentially pending on ST25R */
        st25r200GetInterrupt( ST25R200_IRQ_MASK_OSC );

        /* Enable oscillator and regulator output */
        st25r200SetRegisterBits( ST25R200_REG_OPERATION, ST25R200_REG_OPERATION_en );

        /* Wait for the oscillator interrupt */
        st25r200WaitForInterruptsTimed( ST25R200_IRQ_MASK_OSC, ST25R200_TOUT_OSC_STABLE );
        st25r200DisableInterrupts( ST25R200_IRQ_MASK_OSC );
    }
    
    st25r200ReadRegister( ST25R200_REG_DISPLAY1, &reg );
    
    /* Ensure osc_ok flag is set */
    if( (reg & ST25R200_REG_DISPLAY1_osc_ok) != ST25R200_REG_DISPLAY1_osc_ok )
    {
        return RFAL_ERR_SYSTEM;
    }
    
    /* Check whether AGD has become stable and wait if needed */
    if( (reg & ST25R200_REG_DISPLAY1_agd_ok) != ST25R200_REG_DISPLAY1_agd_ok )
    {
        RFAL_EXIT_ON_ERR( ret, st25r200WaitAgd() );
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200AdjustRegulators( uint8_t drop, uint16_t* result )
{
    uint8_t res;

    /* Check if target drop is to be updated */
    if( drop != ST25R200_REG_DROP_DO_NOT_SET )
    {
        st25r200ChangeRegisterBits( ST25R200_REG_REGULATOR, ST25R200_REG_REGULATOR_regd_mask, (drop << ST25R200_REG_REGULATOR_regd_shift) );
    }
    
    /* Set voltages to be defined by result of Adjust Regulators command */
    st25r200ClrRegisterBits( ST25R200_REG_GENERAL, ST25R200_REG_GENERAL_reg_s );

    /* Execute Adjust regulators cmd and retrieve result */
    st25r200ExecuteCommandAndGetResult( ST25R200_CMD_ADJUST_REGULATORS, ST25R200_REG_DISPLAY1, ST25R200_TOUT_ADJUST_REGULATORS, &res );

    /* Calculate result in mV */
    res = ((res&ST25R200_REG_DISPLAY1_regc_mask)>>ST25R200_REG_DISPLAY1_regc_shift);
    
    if( result != NULL )
    {
        *result  = 2620U;                      /* Minimum regulated voltage 2.62V */
        *result += ((uint16_t)res * 80U);      /* 80mV steps                      */
    }
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200SetRegulators( uint8_t regulation )
{
    /* Check valid setting */
    if( regulation > ST25R200_REG_REGULATOR_rege_mask )
    {
        return RFAL_ERR_PARAM;
    }
   
    st25r200ChangeRegisterBits( ST25R200_REG_REGULATOR, ST25R200_REG_REGULATOR_rege_mask, regulation );
    
    /* Set voltages to be manually defined by rege setting */
    st25r200SetRegisterBits( ST25R200_REG_GENERAL, ST25R200_REG_GENERAL_reg_s );

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200ExecuteCommandAndGetResult( uint8_t cmd, uint8_t resReg, uint8_t tOut, uint8_t* result )
{
    /* Clear and enable Direct Command interrupt */
    st25r200GetInterrupt( ST25R200_IRQ_MASK_DCT );
    st25r200EnableInterrupts( ST25R200_IRQ_MASK_DCT );

    st25r200ExecuteCommand( cmd );

    st25r200WaitForInterruptsTimed( ST25R200_IRQ_MASK_DCT, tOut );
    st25r200DisableInterrupts( ST25R200_IRQ_MASK_DCT );

    /* After execution read out the result if the pointer is not NULL */
    if( result != NULL )
    {
        st25r200ReadRegister( resReg, result );
    }

    return RFAL_ERR_NONE;

}


/*******************************************************************************/
ReturnCode st25r200MeasureIQ( int8_t* resI, int8_t* resQ )
{
    ReturnCode ret;
    uint8_t    aux;
    
    RFAL_EXIT_ON_ERR( ret, st25r200ExecuteCommandAndGetResult( ST25R200_CMD_MEASURE_IQ, 0, ST25R200_TOUT_MEASUREMENT, NULL ) );
    
    if( resI != NULL )
    {
        st25r200ReadRegister( ST25R200_REG_WU_I_ADC, &aux );
        (*resI) = (int8_t)aux;
    }
    
    if( resQ != NULL )
    {
        st25r200ReadRegister( ST25R200_REG_WU_Q_ADC, &aux );
        (*resQ) = (int8_t)aux;
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200MeasureCombinedIQ( uint8_t* res )
{
    ReturnCode ret;
    uint8_t    I;
    uint8_t    Q;
    int16_t    sI;
    int16_t    sQ;
    
    RFAL_EXIT_ON_ERR( ret, st25r200CalibrateWU( &I, &Q ) );
    
    if( res != NULL )
    {
        sI = (0x80 - (int16_t)I);
        sQ = (0x80 - (int16_t)Q);

        /*******************************************************************************/
        /* Usage of SQRT from math.h and float. Due to compiler, resources or          *
         * performance issues sqrt may be not enabled by default. Possible use of      *
         * a less accurate aproach such as:                                            */
        
    #ifdef RFAL_CMATH
        (*res) = (uint8_t) sqrt( ((double)sI * (double)sI) + ((double)sQ * (double)sQ) );  /*  PRQA S 5209 # MISRA 4.6 - External function (sqrt()) requires double */
    #else
        if( sI < 0 ) { sI *= -1; }
        if( sQ < 0 ) { sQ *= -1; }
        
        (*res) = ( ( (uint8_t)sI + (uint8_t)sQ ) / 2U );
    #endif
        
        /* The vector sum of I and Q shall not exceed 127 with proper configuration    *
         * Saturate in SW to ensure this max value                                     */
        if( *res > (uint8_t)INT8_MAX )
        {
            (*res) = INT8_MAX;
        }
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200MeasureI( uint8_t* res )
{
    return st25r200CalibrateWU( res, NULL );
}


/*******************************************************************************/
ReturnCode st25r200MeasureQ( uint8_t* res )
{
    return st25r200CalibrateWU( NULL, res );
}


/*******************************************************************************/
ReturnCode st25r200ClearCalibration( void )
{
    return  st25r200ExecuteCommand( ST25R200_CMD_CLEAR_WU_CALIB );
}


/*******************************************************************************/
ReturnCode st25r200CalibrateWU( uint8_t* resI, uint8_t* resQ )
{
    ReturnCode ret;
    
    RFAL_EXIT_ON_ERR( ret, st25r200ExecuteCommandAndGetResult( ST25R200_CMD_CALIBRATE_WU, 0, ST25R200_TOUT_MEASUREMENT, NULL ) );
    
    if( resI != NULL )
    {
        st25r200ReadRegister( ST25R200_REG_WU_I_CAL, resI );
    }
    
    if( resQ != NULL )
    {
        st25r200ReadRegister( ST25R200_REG_WU_Q_CAL, resQ );
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200MeasureWU( uint8_t* resI, uint8_t* resQ )
{
    ReturnCode ret;
    
    RFAL_EXIT_ON_ERR( ret, st25r200ExecuteCommandAndGetResult( ST25R200_CMD_MEASURE_WU, 0, ST25R200_TOUT_MEASUREMENT, NULL ) );
    
    if( resI != NULL )
    {
        st25r200ReadRegister( ST25R200_REG_WU_I_ADC, resI );
    }
    
    if( resQ != NULL )
    {
        st25r200ReadRegister( ST25R200_REG_WU_Q_ADC, resQ );
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
bool st25r200IsExtFieldOn( void )
{
    uint8_t val;
    uint8_t reg;
    
    if( st25r200IsTxOn() )
    {
        return false;
    }
    
    val = 0;
    
    /* Reduce measurement sensitivity */
    st25r200ReadRegister( ST25R200_REG_RX_ANA2, &reg );
    st25r200WriteRegister( ST25R200_REG_RX_ANA2, ((reg & ~ST25R200_REG_RX_ANA2_afe_gain_td_mask) | ST25R200_REG_RX_ANA2_afe_gain_td3) );
    
    st25r200ClearCalibration();
    st25r200ExecuteCommandAndGetResult( ST25R200_CMD_SENSE_RF, ST25R200_REG_DISPLAY3, ST25R200_TOUT_MEASUREMENT, &val );
    
    /* Restore measurement sensitivity */
    st25r200WriteRegister( ST25R200_REG_RX_ANA2, reg );
    
    return ( (val > ST25R200_TEST_FD_TRESHOLD) ? true : false );
}


/*******************************************************************************/
ReturnCode st25r200SetBitrate( uint8_t txRate, uint8_t rxRate )
{
    uint8_t reg;

    st25r200ReadRegister( ST25R200_REG_PROTOCOL, &reg );
    if( rxRate != ST25R200_BR_DO_NOT_SET )
    {
        if(rxRate > ST25R200_BR_424_53)
        {
            return RFAL_ERR_PARAM;
        }

        reg  = (uint8_t)(reg & ~ST25R200_REG_PROTOCOL_rx_rate_mask);     /* MISRA 10.3 */
        reg |= (rxRate << ST25R200_REG_PROTOCOL_rx_rate_shift);
    }
    
    if( txRate != ST25R200_BR_DO_NOT_SET )
    {
        if(txRate > ST25R200_BR_106_26)
        {
            return RFAL_ERR_PARAM;
        }
        
        reg  = (uint8_t)(reg & ~ST25R200_REG_PROTOCOL_tx_rate_mask);     /* MISRA 10.3 */
        reg |= (txRate << ST25R200_REG_PROTOCOL_rx_rate_shift);
    }
    return st25r200ChangeRegisterBits( ST25R200_REG_PROTOCOL, (ST25R200_REG_PROTOCOL_rx_rate_mask | ST25R200_REG_PROTOCOL_tx_rate_mask), reg );
}


/*******************************************************************************/
ReturnCode st25r200PerformCollisionAvoidance( void )
{
    #if 1
        /*******************************************************************************/
        /* RF Collision avoidance is not supported on ST25R200                         *
         * The procedure here provided is not in alignment with Activity 2.1  3        *
         * One can assess the presence of an external RF carrier and enable its own    *
         * carrier in case no external RF carrier is detected                          */
        /*******************************************************************************/

        if( st25r200IsExtFieldOn() )
        {
            return RFAL_ERR_RF_COLLISION;
        }
        
        st25r200TxRxOn();
        return RFAL_ERR_NONE;
        
    #else
        return RFAL_ERR_NOTSUPP;
    #endif
}


/*******************************************************************************/
void st25r200SetNumTxBits( uint16_t nBits )
{
    st25r200WriteRegister( ST25R200_REG_TX_FRAME2, (uint8_t)((nBits >> 0) & 0xFFU) );
    st25r200WriteRegister( ST25R200_REG_TX_FRAME1, (uint8_t)((nBits >> 8) & 0xFFU) );
}


/*******************************************************************************/
uint16_t st25r200GetNumFIFOBytes( void )
{
    uint8_t  reg;
    uint16_t result;
    
    
    st25r200ReadRegister( ST25R200_REG_FIFO_STATUS2, &reg );
    reg    = ((reg & ST25R200_REG_FIFO_STATUS2_fifo_b8) >> ST25R200_REG_FIFO_STATUS2_fifo_b_shift);
    result = ((uint16_t)reg << 8);
    
    st25r200ReadRegister( ST25R200_REG_FIFO_STATUS1, &reg );
    result |= (((uint16_t)reg) & 0x00FFU);

    return result;
}


/*******************************************************************************/
uint8_t st25r200GetNumFIFOLastBits( void )
{
    uint8_t  reg;
    
    st25r200ReadRegister( ST25R200_REG_FIFO_STATUS2, &reg );
    
    return ((reg & ST25R200_REG_FIFO_STATUS2_fifo_lb_mask) >> ST25R200_REG_FIFO_STATUS2_fifo_lb_shift);
}


/*******************************************************************************/
uint32_t st25r200GetNoResponseTime( void )
{
    return gST25R200NRT_64fcs;
}


/*******************************************************************************/
ReturnCode st25r200SetNoResponseTime( uint32_t nrt )
{    
    ReturnCode err;
    uint8_t    nrt_step;    
    uint32_t   tmpNRT;

    tmpNRT = nrt;                                                     /* MISRA 17.8 */
    err    = RFAL_ERR_NONE;
    
    gST25R200NRT_64fcs = tmpNRT;                                      /* Store given NRT value in 64/fc into local var       */
    nrt_step = ST25R200_REG_NRT_GPT_CONF_nrt_step_64fc;               /* Set default NRT in steps of 64/fc                   */
    
    
    if( tmpNRT > ST25R200_NRT_MAX )                                   /* Check if the given NRT value fits using 64/fc steps */
    {
        nrt_step  = ST25R200_REG_NRT_GPT_CONF_nrt_step_4096fc;        /* If not, change NRT set to 4096/fc                   */
        tmpNRT = ((tmpNRT + 63U) / 64U);                              /* Calculate number of steps in 4096/fc                */
        
        if( tmpNRT > ST25R200_NRT_MAX )                               /* Check if the NRT value fits using 64/fc steps       */
        {
            tmpNRT = ST25R200_NRT_MAX;                                /* Assign the maximum possible                         */
            err = RFAL_ERR_PARAM;                                     /* Signal parameter error                              */
        }
        gST25R200NRT_64fcs = (64U * tmpNRT);
    }

    /* Set the ST25R200 NRT step units and the value */
    st25r200ChangeRegisterBits( ST25R200_REG_NRT_GPT_CONF, ST25R200_REG_NRT_GPT_CONF_nrt_step, nrt_step );
    st25r200WriteRegister( ST25R200_REG_NRT1, (uint8_t)(tmpNRT >> 8U) );
    st25r200WriteRegister( ST25R200_REG_NRT2, (uint8_t)(tmpNRT & 0xFFU) );

    return err;
}


/*******************************************************************************/
ReturnCode st25r200SetStartNoResponseTimer( uint32_t nrt )
{
    ReturnCode err;
    
    err = st25r200SetNoResponseTime( nrt );
    if(err == RFAL_ERR_NONE)
    {
        st25r200ExecuteCommand( ST25R200_CMD_START_NRT );
    }
    
    return err;
}


/*******************************************************************************/
void st25r200SetGPTime( uint16_t gpt )
{
    st25r200WriteRegister( ST25R200_REG_GPT1, (uint8_t)(gpt >> 8) );
    st25r200WriteRegister( ST25R200_REG_GPT2, (uint8_t)(gpt & 0xFFU) );
}


/*******************************************************************************/
ReturnCode st25r200SetStartGPTimer( uint16_t gpt, uint8_t trigger )
{
    st25r200SetGPTime( gpt );
    st25r200ChangeRegisterBits( ST25R200_REG_NRT_GPT_CONF, ST25R200_REG_NRT_GPT_CONF_gptc_mask, trigger );
    
    /* If there's no trigger source, start GPT immediately */
    if( trigger == ST25R200_REG_NRT_GPT_CONF_gptc_no_trigger )
    {
        st25r200ExecuteCommand( ST25R200_CMD_START_GP_TIMER );
    }

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
bool st25r200CheckChipID( uint8_t *rev )
{
    uint8_t ID;
    
    ID = 0;    
    st25r200ReadRegister( ST25R200_REG_IC_ID, &ID );
    
    /* Check if IC Identity Register contains ST25R200's IC type code */
    if( (ID & ST25R200_REG_IC_ID_ic_type_mask) != ST25R200_REG_IC_ID_ic_type_st25r200 )
    {
        return false;
    }
        
    if(rev != NULL)
    {
        *rev = (ID & ST25R200_REG_IC_ID_ic_rev_mask);
    }
    
    return true;
}


/*******************************************************************************/
ReturnCode st25r200GetRegsDump( uint8_t* resRegDump, uint8_t* sizeRegDump )
{
    uint8_t regIt;
    uint8_t regDump[ST25R200_REG_IC_ID+1U];
    
    if( (sizeRegDump == NULL) || (resRegDump == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
    
    for( regIt = ST25R200_REG_OPERATION; regIt < RFAL_SIZEOF_ARRAY(regDump); regIt++ )
    {
        st25r200ReadRegister(regIt, &regDump[regIt] );
    }
    
    *sizeRegDump = RFAL_MIN(*sizeRegDump, regIt);
    if( *sizeRegDump > 0U )                                   /* MISRA 21.18 */
    {
        RFAL_MEMCPY(resRegDump, regDump, *sizeRegDump );
    }

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
bool st25r200IsCmdValid( uint8_t cmd )
{
    if( (cmd < ST25R200_CMD_SET_DEFAULT) || (cmd > ST25R200_CMD_TEST_ACCESS) )
    {
        return false;
    }
    return true;
}


/*******************************************************************************/
ReturnCode st25r200SetAntennaMode( bool single, bool rfiox )
{
    uint8_t val;
    
    val  = 0U;
    val |= ((single)? ST25R200_REG_GENERAL_single : 0U);
    val |= ((rfiox) ? ST25R200_REG_GENERAL_rfo2   : 0U);
    
    return st25r200ChangeRegisterBits( ST25R200_REG_GENERAL, (ST25R200_REG_GENERAL_single | ST25R200_REG_GENERAL_rfo2), val );
}
