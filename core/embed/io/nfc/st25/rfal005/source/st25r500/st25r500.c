
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

/*! \file st25r500.c
 *
 *  \author Gustavo Patricio
 *
 *  \brief ST25R500 High Level interface
 *
 */

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/

#include "st25r500.h"
#include "st25r500_com.h"
#include "st25r500_irq.h"
#include "rfal_utils.h"


/*
 ******************************************************************************
 * ENABLE SWITCH
 ******************************************************************************
 */
 
#ifndef ST25R500
#error "RFAL: Missing ST25R device selection. Please globally define ST25R500."
#endif /* ST25R500 */

/*
******************************************************************************
* LOCAL DEFINES
******************************************************************************
*/

#define ST25R500_SUPPLY_THRESHOLD            3600U   /*!< Power supply measure threshold between 3.3V or 5V                   */
#define ST25R500_NRT_MAX                     0xFFFFU /*!< Max Register value of NRT                                           */
#define ST25R500_MRT_MAX                     0xFFU   /*!< Max Register value of MRT                                           */

#define ST25R500_RESET_DUR                   1U      /*!< Reset high duration  (tBOOT)                                        */ 
#define ST25R500_TOUT_WU_MEASUREMENT         2U      /*!< Max duration time of WU Measure|Calibration                         */
#define ST25R500_TOUT_DIAG_MEASUREMENT       2U      /*!< Max duration time of a single Diag Measurement                      */
#define ST25R500_TOUT_ADJUST_REGULATORS      4U      /*!< Max Adjust Regulators duration                                      */ 
#define ST25R500_TOUT_CALIBRATE_AWS_RC       10U     /*!< Max Calibrate RC duration                                           */
#define ST25R500_TOUT_CA                     5U      /*!< Max Field On duration                                               */ 

#define ST25R500_TEST_REG_PATTERN            0x33U   /*!< Register Read Write test pattern used during selftest               */
#define ST25R500_TEST_WU_TOUT                16U     /*!< Timeout used on WU timer during self test                           */
#define ST25R500_TEST_TMR_TOUT               20U     /*!< Timeout used during self test                                       */
#define ST25R500_TEST_TMR_TOUT_DELTA         2U      /*!< Timeout used during self test                                       */
#define ST25R500_TEST_TMR_TOUT_8FC           (ST25R500_TEST_TMR_TOUT * 1695U)  /*!< Timeout in 8/fc                           */

#define ST25R500_TEST_FD_TRESHOLD            60U     /*!< External carrier presence treshold                                  */

#define ST25R500_RSSI_CONV_BASE              10U     /*!< dB to mV conversion mV =10^(dB/20)                                  */
#define ST25R500_RSSI_CONV_FACTOR            20U     /*!< dB to mV conversion mV =10^(dB/20)                                  */
#define ST25R500_PHASE_PI                    3.1416  /*!< Local pi definition                                                 */ 
#define ST25R500_PHASE_CONV_FACTOR           127U    /*!< Conversion factor for Phase measurement                             */
#define ST25R500_IQ_CONV_FACTOR              2U      /*!< Conversion factor for I/Q measurement                               */



/*
******************************************************************************
* LOCAL CONSTANTS
******************************************************************************
*/

/*
******************************************************************************
* LOCAL MACROS
******************************************************************************
*/
#define st25r500TestModeSaveDisable(v)             do{ st25r500ReadTestRegister( 0x02U, &(v)); st25r500WriteTestRegister(0x02U, 0x00U);}while(0)
#define st25r500TestModeRestore(v)                 st25r500WriteTestRegister(0x02U, (v))


/*
******************************************************************************
* LOCAL VARIABLES
******************************************************************************
*/

static uint32_t gST25R500NRT_64fcs;

/*
******************************************************************************
* LOCAL FUNCTION PROTOTYPES
******************************************************************************
*/
static ReturnCode st25r500MeasureIQCalib( uint16_t* uI, uint16_t* uQ, int16_t* sI, int16_t* sQ );

/*
 ******************************************************************************
 * LOCAL FUNCTION
 ******************************************************************************
 */

ReturnCode st25r500ExecuteCommandAndGetResult( uint8_t cmd, uint8_t resReg, uint8_t tOut, uint8_t* result )
{
    /* Clear and enable Direct Command interrupt */
    st25r500GetInterrupt( ST25R500_IRQ_MASK_DCT );
    st25r500EnableInterrupts( ST25R500_IRQ_MASK_DCT );

    st25r500ExecuteCommand( cmd );

    st25r500WaitForInterruptsTimed( ST25R500_IRQ_MASK_DCT, tOut );
    st25r500DisableInterrupts( ST25R500_IRQ_MASK_DCT );

    /* After execution read out the result if the pointer is not NULL */
    if( result != NULL )
    {
        st25r500ReadRegister( resReg, result );
    }

    return RFAL_ERR_NONE;

}

/*
******************************************************************************
* GLOBAL FUNCTIONS
******************************************************************************
*/

ReturnCode st25r500Initialize( void )
{
    ReturnCode ret;
    
    /* Ensure a defined chip select state */
    platformSpiDeselect();


#ifdef ST25R_RESET_PIN
    /* Reset the ST25R500 using the RESET pin */
    platformGpioSet( ST25R_RESET_PORT, ST25R_RESET_PIN );
    platformDelay( ST25R500_RESET_DUR );
    platformGpioClear( ST25R_RESET_PORT, ST25R_RESET_PIN );
    platformDelay( ST25R500_RESET_DUR );
#endif /* ST25R_RESET_PIN */
    
    
    /* Set default state on the ST25R500 */
    st25r500ExecuteCommand( ST25R500_CMD_SET_DEFAULT );
    if( !st25r500CheckChipID( NULL ) )
    {
        platformErrorHandle();
        return RFAL_ERR_HW_MISMATCH;
    }
    
    st25r500InitInterrupts();
    st25r500ledInit();
    
    gST25R500NRT_64fcs = 0;


#ifdef ST25R_SELFTEST
    
    /******************************************************************************
     * Check communication interface: 
     *  - write a pattern in a register
     *  - reads back the register value
     *  - return RFAL_ERR_IO in case the read value is different
     */
    st25r500WriteRegister( ST25R500_REG_WAKEUP_CONF2, ST25R500_TEST_REG_PATTERN );
    if( !st25r500CheckReg( ST25R500_REG_WAKEUP_CONF2, 0xFFU, ST25R500_TEST_REG_PATTERN ) )
    {
        platformErrorHandle();
        return RFAL_ERR_IO;
    }
    
    /* Restore default value */
    st25r500WriteRegister( ST25R500_REG_WAKEUP_CONF2, 0x00U );

    /*
     * Check IRQ Handling:
     *  - use the Wake-up timer to trigger an IRQ
     *  - wait the Wake-up timer interrupt
     *  - return RFAL_ERR_TIMEOUT when the Wake-up timer interrupt is not received
     */
    st25r500EnableInterrupts( ST25R500_IRQ_MASK_WUT );
    st25r500ExecuteCommand( ST25R500_CMD_START_WUT );
    
    if( st25r500WaitForInterruptsTimed(ST25R500_IRQ_MASK_WUT, ST25R500_TEST_WU_TOUT) == 0U )
    {
        platformErrorHandle();
        return RFAL_ERR_TIMEOUT;
    }
    
    st25r500DisableInterrupts( ST25R500_IRQ_MASK_WUT );
    st25r500WriteRegister( ST25R500_REG_WAKEUP_CONF1, 0x00U );
    /*******************************************************************************/
    
#endif /* ST25R_SELFTEST */


    /* Enable Oscillator and wait until it gets stable */
    RFAL_EXIT_ON_ERR( ret, st25r500OscOn() );

    /* Trigger RC calibration */
    st25r500ExecuteCommandAndGetResult( ST25R500_CMD_CALIBRATE_RC,  0U, ST25R500_TOUT_CALIBRATE_AWS_RC, NULL );

    /* Make sure Transmitter and Receiver are disabled */
    st25r500TxRxOff();
    
    
#ifdef ST25R_SELFTEST_TIMER
    /******************************************************************************
     * Check SW timer operation :
     *  - use the General Purpose timer to measure an amount of time
     *  - test whether an interrupt is seen when less time was given
     *  - test whether an interrupt is seen when sufficient time was given
     */
    
    st25r500EnableInterrupts( ST25R500_IRQ_MASK_GPE );
    st25r500SetStartGPTimer( (uint16_t)ST25R500_TEST_TMR_TOUT_8FC, ST25R500_REG_NRT_GPT_CONF_gptc_no_trigger);
    if( st25r500WaitForInterruptsTimed( ST25R500_IRQ_MASK_GPE, (ST25R500_TEST_TMR_TOUT - ST25R500_TEST_TMR_TOUT_DELTA)) != 0U )
    {
        platformErrorHandle();
        return RFAL_ERR_SYSTEM;
    }
    
    /* Stop all activities to stop the GP timer */
    st25r500ExecuteCommand( ST25R500_CMD_STOP );
    st25r500ClearAndEnableInterrupts( ST25R500_IRQ_MASK_GPE );
    st25r500SetStartGPTimer( (uint16_t)ST25R500_TEST_TMR_TOUT_8FC, ST25R500_REG_NRT_GPT_CONF_gptc_no_trigger );
    if(st25r500WaitForInterruptsTimed( ST25R500_IRQ_MASK_GPE, (ST25R500_TEST_TMR_TOUT + ST25R500_TEST_TMR_TOUT_DELTA)) == 0U )
    {
        platformErrorHandle();
        return RFAL_ERR_SYSTEM;
    }
    
    /* Stop all activities to stop the GP timer */
    st25r500ExecuteCommand( ST25R500_CMD_STOP );
    /*******************************************************************************/
#endif /* ST25R_SELFTEST_TIMER */
    
    
    /* After reset all interrupts are enabled, so disable them at first */
    st25r500DisableInterrupts( ST25R500_IRQ_MASK_ALL );
    
    /* And clear them, just to be sure */
    st25r500ClearInterrupts();
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
void st25r500Deinitialize( void )
{
    /* Stop any ongoing activity */
    st25r500ExecuteCommand( ST25R500_CMD_STOP );
    st25r500DisableInterrupts( ST25R500_IRQ_MASK_ALL );
    
    /* Set the device in PD mode */
    st25r500ClrRegisterBits( ST25R500_REG_OPERATION, ( ST25R500_REG_OPERATION_en   | ST25R500_REG_OPERATION_rx_en |
                                                       ST25R500_REG_OPERATION_vdddr_en | ST25R500_REG_OPERATION_wu_en | ST25R500_REG_OPERATION_tx_en ) );

    return;
}


/*******************************************************************************/
ReturnCode st25r500OscOn( void )
{
    /* Check if oscillator is already turned on and stable                                                */        
    /* Use ST25R500_REG_OP_CONTROL_en instead of ST25R500_REG_AUX_DISPLAY_osc_ok to be on the safe side */    
    if( !st25r500IsOscOn() )
    {
        /* Clear any eventual previous oscillator frequency stable IRQ and enable it */
        st25r500ClearAndEnableInterrupts( ST25R500_IRQ_MASK_OSC );
        
        /* Clear any oscillator IRQ that was potentially pending on ST25R */
        st25r500GetInterrupt( ST25R500_IRQ_MASK_OSC );

        /* Enable oscillator and regulator output */
        st25r500SetRegisterBits( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_en );

        /* Wait for the oscillator interrupt */
        st25r500WaitForInterruptsTimed( ST25R500_IRQ_MASK_OSC, ST25R500_TOUT_OSC_STABLE );
        st25r500DisableInterrupts( ST25R500_IRQ_MASK_OSC );
    }
    
    if( !st25r500CheckReg( ST25R500_REG_STATUS1, (ST25R500_REG_STATUS1_osc_ok | ST25R500_REG_STATUS1_agd_ok), (ST25R500_REG_STATUS1_osc_ok | ST25R500_REG_STATUS1_agd_ok) ) )
    {
        return RFAL_ERR_SYSTEM;
    }    
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500AdjustRegulators( uint8_t drop, uint16_t* result )
{
    uint8_t res;

    /* Check if target drop is to be updated */
    if( drop != ST25R500_REG_DROP_DO_NOT_SET )
    {
        st25r500ChangeRegisterBits( ST25R500_REG_DRIVER, ST25R500_REG_DRIVER_regd_mask, (drop << ST25R500_REG_DRIVER_regd_shift) );
    }
    
    /* Set voltages to be defined by result of Adjust Regulators command */
    st25r500ClrRegisterBits( ST25R500_REG_REGULATOR, ST25R500_REG_REGULATOR_reg_s );

    /* Execute Adjust regulators cmd and retrieve result */
    st25r500ExecuteCommandAndGetResult( ST25R500_CMD_ADJUST_REGULATORS, ST25R500_REG_ANA_DISPLAY1, ST25R500_TOUT_ADJUST_REGULATORS, &res );

    /* Calculate result in mV */
    res = ((res&ST25R500_REG_ANA_DISPLAY1_regc_mask)>>ST25R500_REG_ANA_DISPLAY1_regc_shift);
    
    if( result != NULL )
    {
        *result += ((uint16_t)res * 47U);      /* 47mV steps                      */
    }
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500SetRegulators( uint8_t regulation )
{
    /* Check valid setting */
    if( regulation > ST25R500_REG_REGULATOR_rege_mask )
    {
        return RFAL_ERR_PARAM;
    }
   
    st25r500ChangeRegisterBits( ST25R500_REG_REGULATOR, ST25R500_REG_REGULATOR_rege_mask, regulation );
    
    /* Set voltages to be manually defined by rege setting */
    st25r500SetRegisterBits( ST25R500_REG_REGULATOR, ST25R500_REG_REGULATOR_reg_s );

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
static ReturnCode st25r500MeasureIQCalib( uint16_t* uI, uint16_t* uQ, int16_t* sI, int16_t* sQ )
{
    uint16_t    I;
    uint16_t    Q;
    int16_t     siI;
    int16_t     siQ;
    uint8_t     tMode;
    ReturnCode  ret;
    
    st25r500TestModeSaveDisable( tMode );
    RFAL_EXIT_ON_ERR( ret, st25r500CalibrateWU( &I, &Q ) );
    st25r500TestModeRestore( tMode );
    
    
    /*******************************************************************************/
    /* Normalize to signed values */
    siI = (0x100 - (int16_t)I);
    siQ = (0x100 - (int16_t)Q);
    
    /*******************************************************************************/
    /* Check and set output parameters */
    if( uI != NULL )
    {
        *uI = I;
    }
    if( uQ != NULL )
    {
        *uQ = Q;
    }
    if( sI != NULL )
    {
        *sI = siI;
    }
    if( sQ != NULL )
    {
        *sQ = siQ;
    }
    
    return ret;
}





/*******************************************************************************/
ReturnCode st25r500GetCeGain( uint8_t *result )
{
    /* Check if device is correct state                     */
    /* In CE Mode afe_gain shows received signal indication */
    if( (!st25r500CheckReg(ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_ce_en, ST25R500_REG_OPERATION_ce_en )) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    if( result != NULL )
    {
        st25r500ReadRegister( ST25R500_REG_ANA_DISPLAY2, result );
        (*result) &= ST25R500_REG_ANA_DISPLAY2_afe_gain_mask;
    }
        
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500MeasureIQ( int8_t* resI, int8_t* resQ )
{
    ReturnCode ret;
    uint8_t    aux;
    
    RFAL_EXIT_ON_ERR( ret, st25r500ExecuteCommandAndGetResult( ST25R500_CMD_MEASURE_IQ, 0, ST25R500_TOUT_WU_MEASUREMENT, NULL ) );
    
    if( resI != NULL )
    {
        st25r500ReadRegister( ST25R500_REG_WU_I_ADC, &aux );
        (*resI) = (int8_t)aux;
    }
    
    if( resQ != NULL )
    {
        st25r500ReadRegister( ST25R500_REG_WU_Q_ADC, &aux );
        (*resQ) = (int8_t)aux;
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500MeasureCombinedIQ( uint8_t* res )
{
    int16_t     sI;
    int16_t     sQ;
    ReturnCode  ret;
    uint16_t    result;
    
    RFAL_EXIT_ON_ERR( ret, st25r500MeasureIQCalib( NULL, NULL, &sI, &sQ ) );
    
    
    #ifdef RFAL_CMATH
        result = ((uint16_t) sqrt( ((double)sI * (double)sI) + ((double)sQ * (double)sQ) ));  /*  PRQA S 5209 # MISRA 4.6 - External function (sqrt()) requires double */
    #else
        if( sI < 0 ) { sI *= -1; }
        if( sQ < 0 ) { sQ *= -1; }
        
        result = (( (uint16_t)sI + (uint16_t)sQ ) / 2U);
    #endif /* RFAL_CMATH */
    
    /* As root could go up to 360, either divide or truncate before converting to 8bit
     * Real signals shall never go that high with proper configuration */
    if( result > (uint16_t)UINT8_MAX )
    {
        result = UINT8_MAX;
    }
    
    if( res != NULL )
    {
        (*res) = (uint8_t)result;
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500MeasureI( uint8_t* res )
{
    uint16_t    I;
    ReturnCode  ret;
    
    RFAL_EXIT_ON_ERR( ret, st25r500MeasureIQCalib( &I, NULL, NULL, NULL ) );
    
    if( res != NULL )
    {
        (*res) = (uint8_t) (I / ST25R500_IQ_CONV_FACTOR);
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500MeasureQ( uint8_t* res )
{
    uint16_t    Q;
    ReturnCode  ret;
    
    RFAL_EXIT_ON_ERR( ret, st25r500MeasureIQCalib( NULL, &Q, NULL, NULL ) );
    
    if( res != NULL )
    {
        (*res) = (uint8_t) (Q / ST25R500_IQ_CONV_FACTOR);
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500MeasureAmplitude( uint8_t* result )
{
    return st25r500MeasureCombinedIQ( result );
}


/*******************************************************************************/
ReturnCode st25r500MeasurePhase( uint8_t* res )
{
    
#ifndef RFAL_CMATH
    
    if( res != NULL )
    {
        (*res) = 0;
    }
    
    return RFAL_ERR_DISABLED;
#else
    
    int16_t     sI;
    int16_t     sQ;
    ReturnCode  ret;
    double      result;                                                                                     /*  PRQA S 5209 # MISRA 4.6 - External function (atan2()) requires double */
    
    RFAL_EXIT_ON_ERR( ret, st25r500MeasureIQCalib( NULL, NULL, &sI, &sQ ) );
    
    result = atan2( (double)sQ, (double)sI);                              /* Result from [-pi;pi]   */      /*  PRQA S 5209 # MISRA 4.6 - External function (atan2()) requires double */
    result += ST25R500_PHASE_PI;                                          /* Now from [0;2pi]       */
    result = ((result / ST25R500_PHASE_PI) * ST25R500_PHASE_CONV_FACTOR); /* Normalize angle into 0..255 */
    
    if( res != NULL )
    {
        (*res) = (uint8_t) result;
    }
    
    return RFAL_ERR_NONE;
#endif /* RFAL_CMATH */
}

/*******************************************************************************/
ReturnCode st25r500DiagMeasure( uint8_t meas, uint16_t *res )
{
    uint8_t  tMode;
    uint8_t  reg;
    uint16_t measurement;
    uint8_t  ceMem[ST25R500_DIAG_MEAS_CMD_LEN];
    uint8_t  result[ST25R500_DIAG_MEAS_RES_LEN];
    const uint8_t  command[ST25R500_DIAG_MEAS_CMD_LEN] = { meas, 0x00 };


    st25r500ReadRegister( ST25R500_REG_OPERATION, &reg );

    /* Check proper operation mode, device must be in RD mode */
    if( (ST25R500_REG_OPERATION_en & reg) == 0U )
    {
        return RFAL_ERR_WRONG_STATE;
    }

    /* Ensure no test mode being used and ensure restoring CE memory */
    st25r500TestModeSaveDisable( tMode );
    st25r500ReadMultipleRegisters( ST25R500_REG_CEM_A, ceMem, sizeof(ceMem) );

    /* Diagnostic Measurements require Rx enabled.                   *
     * For convenience, enabled it temporarily if currently disabled */
    if( (ST25R500_REG_OPERATION_rx_en & reg) == 0U )
    {
        st25r500WriteRegister( ST25R500_REG_OPERATION, (reg | ST25R500_REG_OPERATION_rx_en) );
    }


    /* Execute Diagnostic measurement */
    st25r500WriteMultipleRegisters( ST25R500_REG_CEM_A, command, sizeof(command) );
    st25r500ExecuteCommandAndGetResult( ST25R500_CMD_TRIGGER_DIAG, 0, ST25R500_TOUT_DIAG_MEASUREMENT, NULL );
    st25r500ReadFifo( result, sizeof(result) );

    measurement  = ( (uint16_t)result[ST25R500_DIAG_MEAS_CMD]<<8U );
    measurement |= (result[ST25R500_DIAG_MEAS_CMD+1U]);

    if( res != NULL )
    {
        (*res) = measurement;
    }


    /* In case Rx was temporarily enabled, restore initial state */
    if( (ST25R500_REG_OPERATION_rx_en & reg) == 0U )
    {
        st25r500WriteRegister( ST25R500_REG_OPERATION, reg );
    }

    /* Restore previous Test modes and CE memory */
    st25r500WriteMultipleRegisters( ST25R500_REG_CEM_A, ceMem, sizeof(ceMem) );
    st25r500TestModeRestore( tMode );

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500MeasureCurrent( uint8_t* res )
{
    ReturnCode ret;
    uint16_t   rawResult;

    rawResult = 0;
    
    ret = st25r500DiagMeasure( ST25R500_DIAG_MEAS_I_VDD_DR, &rawResult );
    if( res != NULL )
    {
        /* Saturate if too large, expected value should be < ~160 */
        if( rawResult > (uint16_t)UINT8_MAX )
        {
            *res = UINT8_MAX;
        }
        else
        {
            (*res) = (uint8_t)rawResult;
        }
    }

    return ret;
}


/*******************************************************************************/
ReturnCode st25r500ClearCalibration( void )
{
    return  st25r500ExecuteCommand( ST25R500_CMD_CLEAR_WU_CALIB );
}


/*******************************************************************************/
ReturnCode st25r500CalibrateWU( uint16_t* resI, uint16_t* resQ )
{
    ReturnCode ret;
    uint8_t    resLSB;
    uint8_t    resMSB;
    uint16_t   aux;
    
    RFAL_EXIT_ON_ERR( ret, st25r500ExecuteCommandAndGetResult( ST25R500_CMD_CALIBRATE_WU, 0, ST25R500_TOUT_WU_MEASUREMENT, NULL ) );
    
    if( resI != NULL )
    {
        st25r500ReadRegister( ST25R500_REG_WU_I_CAL,   &resLSB );
        st25r500ReadRegister( ST25R500_REG_WU_I_DELTA, &resMSB );
        
        resMSB  = ((resMSB & ST25R500_REG_WU_I_DELTA_i_cal8_mask) >> ST25R500_REG_WU_I_DELTA_i_cal8_shift);   /* MISRA 10.8 */
        aux     = (((uint16_t)resMSB<<8U) | (uint16_t)resLSB);                                                /* MISRA 10.8 */
        (*resI) = aux;
    }
    
    if( resQ != NULL )
    {
        st25r500ReadRegister( ST25R500_REG_WU_Q_CAL,   &resLSB );
        st25r500ReadRegister( ST25R500_REG_WU_Q_DELTA, &resMSB );
        
        resMSB  = ((resMSB & ST25R500_REG_WU_Q_DELTA_q_cal8_mask) >> ST25R500_REG_WU_Q_DELTA_q_cal8_shift);   /* MISRA 10.8 */
        aux     = (((uint16_t)resMSB<<8U) | (uint16_t)resLSB);                                                /* MISRA 10.8 */
        (*resQ) = aux;
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500MeasureWU( uint8_t* resI, uint8_t* resQ )
{
    ReturnCode ret;
    
    RFAL_EXIT_ON_ERR( ret, st25r500ExecuteCommandAndGetResult( ST25R500_CMD_MEASURE_WU, 0, ST25R500_TOUT_WU_MEASUREMENT, NULL ) );
    
    if( resI != NULL )
    {
        st25r500ReadRegister( ST25R500_REG_WU_I_ADC, resI );
    }
    
    if( resQ != NULL )
    {
        st25r500ReadRegister( ST25R500_REG_WU_Q_ADC, resQ );
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500SetBitrate( uint8_t txRate, uint8_t rxRate )
{
    uint8_t reg;

    st25r500ReadRegister( ST25R500_REG_PROTOCOL, &reg );
    if( rxRate != ST25R500_BR_DO_NOT_SET )
    {
        if( rxRate > ST25R500_BR_848 )
        {
            return RFAL_ERR_PARAM;
        }

        reg  = (uint8_t)(reg & ~ST25R500_REG_PROTOCOL_rx_rate_mask);     /* MISRA 10.3 */
        reg |= (rxRate << ST25R500_REG_PROTOCOL_rx_rate_shift);
    }
    
    if( txRate != ST25R500_BR_DO_NOT_SET )
    {
        if( txRate > ST25R500_BR_848 )
        {
            return RFAL_ERR_PARAM;
        }
        
        reg  = (uint8_t)(reg & ~ST25R500_REG_PROTOCOL_tx_rate_mask);     /* MISRA 10.3 */
        reg |= (txRate << ST25R500_REG_PROTOCOL_tx_rate_shift);
    }
    return st25r500ChangeRegisterBits( ST25R500_REG_PROTOCOL, (ST25R500_REG_PROTOCOL_rx_rate_mask | ST25R500_REG_PROTOCOL_tx_rate_mask), reg );
}


/*******************************************************************************/
ReturnCode st25r500PerformCollisionAvoidance( uint8_t atThreshold, uint8_t dtThreshold, uint8_t nTRFW )
{
    uint8_t    treMask;
    uint32_t   irqs;
    ReturnCode err;
    
    
    err = RFAL_ERR_INTERNAL;
    
    
    /* Check if new thresholds are to be applied */
    if( (atThreshold != ST25R500_THRESHOLD_DO_NOT_SET) || (dtThreshold != ST25R500_THRESHOLD_DO_NOT_SET) )
    {
        treMask = 0;
        
        if(atThreshold != ST25R500_THRESHOLD_DO_NOT_SET)
        {
            treMask |= ST25R500_REG_EFD_THRESHOLD_efd_at_mask;
        }
        
        if(dtThreshold != ST25R500_THRESHOLD_DO_NOT_SET)
        {
            treMask |= ST25R500_REG_EFD_THRESHOLD_efd_dt_mask;
        }
            
        /* Set Detection Threshold and|or Collision Avoidance Threshold */
        st25r500ChangeRegisterBits( ST25R500_REG_EFD_THRESHOLD, treMask, (atThreshold & ST25R500_REG_EFD_THRESHOLD_efd_at_mask) | (dtThreshold & ST25R500_REG_EFD_THRESHOLD_efd_dt_mask ) );
    }
    
    /* Set n x TRFW */
    st25r500ChangeRegisterBits( ST25R500_REG_GENERAL, ST25R500_REG_GENERAL_nfc_n_mask, nTRFW );
        
    /*******************************************************************************/
    /* Enable and clear CA specific interrupts and execute command */
    st25r500GetInterrupt( ST25R500_IRQ_MASK_DCT );
    st25r500EnableInterrupts( ST25R500_IRQ_MASK_DCT );
    
    st25r500ExecuteCommand( ST25R500_CMD_NFC_FIELD_ON );
    
    /*******************************************************************************/
    /* Wait for initial APON interrupt, indicating anticollision avoidance done and ST25R500's 
     * field is now on, or a CAC indicating a collision */   
    irqs = st25r500WaitForInterruptsTimed( ST25R500_IRQ_MASK_DCT, ST25R500_TOUT_CA );    
   
    if( ((irqs & ST25R500_IRQ_MASK_DCT) != 0U) )
    {
        if( st25r500CheckReg( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_tx_en, ST25R500_REG_OPERATION_tx_en ) )
        {
            err = RFAL_ERR_NONE;
        }
        else
        {
            err = RFAL_ERR_RF_COLLISION;
        }
    }
        
    /* Clear any previous External Field events and disable CA specific interrupts */
    st25r500GetInterrupt( (ST25R500_IRQ_MASK_EOF | ST25R500_IRQ_MASK_EON) );
    st25r500DisableInterrupts( ST25R500_IRQ_MASK_DCT );
    
    return err;
}


/*******************************************************************************/
void st25r500SetNumTxBits( uint16_t nBits )
{
    st25r500WriteRegister( ST25R500_REG_TX_FRAME2, (uint8_t)((nBits >> 0) & 0xFFU) );
    st25r500WriteRegister( ST25R500_REG_TX_FRAME1, (uint8_t)((nBits >> 8) & 0xFFU) );
}


/*******************************************************************************/
uint16_t st25r500GetNumFIFOBytes( void )
{
    uint8_t  reg;
    uint16_t result;
    
    
    st25r500ReadRegister( ST25R500_REG_FIFO_STATUS2, &reg );
    reg    = ((reg & ST25R500_REG_FIFO_STATUS2_fifo_b8) >> ST25R500_REG_FIFO_STATUS2_fifo_b_shift);
    result = ((uint16_t)reg << 8);
    
    st25r500ReadRegister( ST25R500_REG_FIFO_STATUS1, &reg );
    result |= (((uint16_t)reg) & 0x00FFU);

    return result;
}


/*******************************************************************************/
uint8_t st25r500GetNumFIFOLastBits( void )
{
    uint8_t  reg;
    
    st25r500ReadRegister( ST25R500_REG_FIFO_STATUS2, &reg );
    
    return ((reg & ST25R500_REG_FIFO_STATUS2_fifo_lb_mask) >> ST25R500_REG_FIFO_STATUS2_fifo_lb_shift);
}


/*******************************************************************************/
uint32_t st25r500GetNoResponseTime( void )
{
    return gST25R500NRT_64fcs;
}


/*******************************************************************************/
ReturnCode st25r500SetMRT( uint32_t value_fc )
{
    ReturnCode err = RFAL_ERR_NONE;

    if( value_fc <= (16U * ST25R500_MRT_MAX) )
    {
        st25r500ChangeRegisterBits( ST25R500_REG_MRT1, ST25R500_REG_MRT1_mrt_step_mask,  ST25R500_REG_MRT1_mrt_step_16fc);
        st25r500WriteRegister( ST25R500_REG_MRT2, (uint8_t)(value_fc / 16U));
    }
    else if( value_fc <= (32U * ST25R500_MRT_MAX) )
    {
        st25r500ChangeRegisterBits( ST25R500_REG_MRT1, ST25R500_REG_MRT1_mrt_step_mask,  ST25R500_REG_MRT1_mrt_step_32fc);
        st25r500WriteRegister( ST25R500_REG_MRT2, (uint8_t)(value_fc / 32U));
    }
    else if( value_fc <= (64U * ST25R500_MRT_MAX) )
    {
        st25r500ChangeRegisterBits( ST25R500_REG_MRT1, ST25R500_REG_MRT1_mrt_step_mask,  ST25R500_REG_MRT1_mrt_step_64fc);
        st25r500WriteRegister( ST25R500_REG_MRT2, (uint8_t)(value_fc / 64U));
    }
    else if( value_fc <= (512U * ST25R500_MRT_MAX) )
    {
        st25r500ChangeRegisterBits( ST25R500_REG_MRT1, ST25R500_REG_MRT1_mrt_step_mask,  ST25R500_REG_MRT1_mrt_step_512fc);
        st25r500WriteRegister( ST25R500_REG_MRT2, (uint8_t)(value_fc / 512U));
    }
    else
    {
        err = RFAL_ERR_PARAM;
        st25r500ChangeRegisterBits( ST25R500_REG_MRT1, ST25R500_REG_MRT1_mrt_step_mask,  ST25R500_REG_MRT1_mrt_step_512fc );
        st25r500WriteRegister( ST25R500_REG_MRT2, ST25R500_MRT_MAX );
    }
    return err;
}


/*******************************************************************************/
ReturnCode st25r500SetNoResponseTime( uint32_t nrt )
{    
    ReturnCode err;
    uint8_t    nrt_step;    
    uint32_t   tmpNRT;

    tmpNRT = nrt;                                                     /* MISRA 17.8 */
    err    = RFAL_ERR_NONE;
    
    gST25R500NRT_64fcs = tmpNRT;                                      /* Store given NRT value in 64/fc into local var       */
    nrt_step = ST25R500_REG_NRT_GPT_CONF_nrt_step_64fc;               /* Set default NRT in steps of 64/fc                   */
    
    
    if( tmpNRT > ST25R500_NRT_MAX )                                   /* Check if the given NRT value fits using 64/fc steps */
    {
        nrt_step  = ST25R500_REG_NRT_GPT_CONF_nrt_step_4096fc;        /* If not, change NRT set to 4096/fc                   */
        tmpNRT = ((tmpNRT + 63U) / 64U);                               /* Calculate number of steps in 4096/fc                */
        
        if( tmpNRT > ST25R500_NRT_MAX )                               /* Check if the NRT value fits using 64/fc steps       */
        {
            tmpNRT = ST25R500_NRT_MAX;                                /* Assign the maximum possible                         */
            err = RFAL_ERR_PARAM;                                           /* Signal parameter error                              */
        }
        gST25R500NRT_64fcs = (64U * tmpNRT);
    }

    /* Set the ST25R500 NRT step units and the value */
    st25r500ChangeRegisterBits( ST25R500_REG_NRT_GPT_CONF, ST25R500_REG_NRT_GPT_CONF_nrt_step, nrt_step );
    st25r500WriteRegister( ST25R500_REG_NRT1, (uint8_t)(tmpNRT >> 8U) );
    st25r500WriteRegister( ST25R500_REG_NRT2, (uint8_t)(tmpNRT & 0xFFU) );

    return err;
}


/*******************************************************************************/
ReturnCode st25r500SetStartNoResponseTimer( uint32_t nrt )
{
    ReturnCode err;
    
    err = st25r500SetNoResponseTime( nrt );
    if(err == RFAL_ERR_NONE)
    {
        st25r500ExecuteCommand( ST25R500_CMD_START_NRT );
    }
    
    return err;
}


/*******************************************************************************/
void st25r500SetGPTime( uint16_t gpt )
{
    st25r500WriteRegister( ST25R500_REG_GPT1, (uint8_t)(gpt >> 8) );
    st25r500WriteRegister( ST25R500_REG_GPT2, (uint8_t)(gpt & 0xFFU) );
}


/*******************************************************************************/
ReturnCode st25r500SetStartGPTimer( uint16_t gpt, uint8_t trigger )
{
    st25r500SetGPTime( gpt );
    st25r500ChangeRegisterBits( ST25R500_REG_NRT_GPT_CONF, ST25R500_REG_NRT_GPT_CONF_gptc_mask, trigger );
    
    /* If there's no trigger source, start GPT immediately */
    if( trigger == ST25R500_REG_NRT_GPT_CONF_gptc_no_trigger )
    {
        st25r500ExecuteCommand( ST25R500_CMD_START_GP_TIMER );
    }

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
bool st25r500CheckChipID( uint8_t *rev )
{
    uint8_t ID;
    
    ID = 0;    
    st25r500ReadRegister( ST25R500_REG_IC_ID, &ID );
    
    /* Check if IC Identity Register contains ST25R500's IC type code */
    if( (ID & ST25R500_REG_IC_ID_ic_type_mask) != ST25R500_REG_IC_ID_ic_type_st25r500 )
    {
        return false;
    }
        
    if(rev != NULL)
    {
        *rev = (ID & ST25R500_REG_IC_ID_ic_rev_mask);
    }
    
    return true;
}


/*******************************************************************************/
ReturnCode st25r500GetRegsDump( uint8_t* resRegDump, uint8_t* sizeRegDump )
{
    uint8_t regIt;
    uint8_t regDump[ST25R500_REG_EFD_THRESHOLD+1U];

    if( (sizeRegDump == NULL) || (resRegDump == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
    
    for( regIt = ST25R500_REG_OPERATION; regIt < RFAL_SIZEOF_ARRAY(regDump); regIt++ )
    {
        st25r500ReadRegister( regIt, &regDump[regIt] );
    }
    

    *sizeRegDump = RFAL_MIN(*sizeRegDump, regIt);
    if( *sizeRegDump > 0U )                                   /* MISRA 21.18 */
    {
        RFAL_MEMCPY( resRegDump, regDump, *sizeRegDump );
    }

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
bool st25r500IsCmdValid( uint8_t cmd )
{
    if( (cmd < ST25R500_CMD_SET_DEFAULT) || (cmd > ST25R500_CMD_STOP_NRT) )
    {
        return false;
    }
    return true;
}


/*******************************************************************************/
ReturnCode st25r500GetRSSI( uint16_t *iRssi, uint16_t *qRssi )
{
    uint8_t  rssi;
    /*
      dB can be converted to mV by 10^(dB/20).
      An equivelent model can be applied avoid usage of powe and float
    
      FIXME: Non acurate RSSI aproximation
    */
     
    if( iRssi != NULL )
    {
        st25r500ReadRegister( ST25R500_REG_RSSI_I, &rssi );
        rssi &= ST25R500_REG_RSSI_I_rssi_i_mask;
        
    #ifdef RFAL_CMATH
        (*iRssi) = (uint16_t) pow( ST25R500_RSSI_CONV_BASE, ( (double)rssi / ST25R500_RSSI_CONV_FACTOR) );     /*  PRQA S 5209 # MISRA 4.6 - External function (pow()) requires double */
    #else
        (*iRssi) = rssi;
    #endif /* RFAL_CMATH */
    }
    
    if( qRssi != NULL )
    {
        st25r500ReadRegister( ST25R500_REG_RSSI_Q, &rssi );
        rssi &= ST25R500_REG_RSSI_Q_rssi_q_mask;
        
    #ifdef RFAL_CMATH
        (*qRssi) = (uint16_t) pow( ST25R500_RSSI_CONV_BASE, ( (double)rssi / ST25R500_RSSI_CONV_FACTOR) );     /*  PRQA S 5209 # MISRA 4.6 - External function (pow()) requires double */
    #else
        (*qRssi) = rssi;
    #endif /* RFAL_CMATH */
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500SetAntennaMode( bool single, bool rfiox )
{
    uint8_t val;
    
    val  = 0U;
    val |= ((single)? ST25R500_REG_GENERAL_single : 0U);
    val |= ((rfiox) ? ST25R500_REG_GENERAL_rfo2   : 0U);
    
    return st25r500ChangeRegisterBits( ST25R500_REG_GENERAL, (ST25R500_REG_GENERAL_single | ST25R500_REG_GENERAL_rfo2), val );
}
