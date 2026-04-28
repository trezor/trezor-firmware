
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

/*! \file st25r500.h
 *
 *  \author Gustavo Patricio
 *
 *  \brief ST25R500 high level interface
 *
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
 * \addtogroup ST25R500_Driver
 * \brief RFAL ST25R500 Driver
 * @{
 * 
 */


#ifndef ST25R500_H
#define ST25R500_H

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include "rfal_platform.h"
#include "rfal_utils.h"
#include "st25r500_com.h"

/*
******************************************************************************
* GLOBAL DATATYPES
******************************************************************************
*/


/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/

/* ST25R500 direct commands */
#define ST25R500_CMD_SET_DEFAULT              0x60U    /*!< Puts the chip in default state (same as after power-up) */
#define ST25R500_CMD_STOP                     0x62U    /*!< Stops all activities and clears FIFO                    */
#define ST25R500_CMD_CLEAR_FIFO               0x64U    /*!< Clears FIFO, Collision and IRQ status                   */
#define ST25R500_CMD_CLEAR_RXGAIN             0x66U    /*!< Clears FIFO, Collision and IRQ status                   */
#define ST25R500_CMD_ADJUST_REGULATORS        0x68U    /*!< Adjust regulators                                       */
#define ST25R500_CMD_TRANSMIT                 0x6AU    /*!< Transmit                                                */
#define ST25R500_CMD_TRANSMIT_EOF             0x6CU    /*!< Transmit ISO15693 EOF                                   */
#define ST25R500_CMD_NFC_FIELD_ON             0x6EU    /*!< Field On                                                */
#define ST25R500_CMD_MASK_RECEIVE_DATA        0x70U    /*!< Mask receive data                                       */
#define ST25R500_CMD_UNMASK_RECEIVE_DATA      0x72U    /*!< Unmask receive data                                     */
#define ST25R500_CMD_CALIBRATE_WU             0x74U    /*!< Calibrate Wake-up Measurement                           */
#define ST25R500_CMD_CLEAR_WU_CALIB           0x76U    /*!< Clear Wake-up Calibratation                             */
#define ST25R500_CMD_MEASURE_WU               0x78U    /*!< Measure Wake-up I and Q components                      */
#define ST25R500_CMD_MEASURE_IQ               0x7AU    /*!< Measure I and Q components                              */
#define ST25R500_CMD_SENSE_RF                 0x7CU    /*!< Sense RF on RFI pins                                    */
#define ST25R500_CMD_TRIGGER_WU_EV            0x7EU    /*!< Trigger Wake-up Event                             */
#define ST25R500_CMD_START_GP_TIMER           0xE2U    /*!< Start the general purpose timer                         */
#define ST25R500_CMD_START_WUT                0xE4U    /*!< Start the wake-up timer                                 */
#define ST25R500_CMD_START_MRT                0xE6U    /*!< Start the mask-receive timer                            */
#define ST25R500_CMD_START_NRT                0xE8U    /*!< Start the no-response timer                             */
#define ST25R500_CMD_STOP_NRT                 0xEAU    /*!< Stop No Response Timer                                  */
#define ST25R500_CMD_CALIBRATE_RC             0xEEU    /*!< Calibrate RC                                            */
#define ST25R500_CMD_TRIGGER_DIAG             0xF8U    /*!< Trigger Diagnostic Measurement                          */
#define ST25R500_CMD_TEST_ACCESS              0xFCU    /*!< Enable R/W access to the test registers                 */

#define ST25R500_BR_DO_NOT_SET                0xFFU    /*!< Indicates not to change this Bit Rate                   */
#define ST25R500_BR_106_26                    0x00U    /*!< ST25R500 Bit Rate  106 kbps (fc/128) / 26 kbps(fc/512)  */
#define ST25R500_BR_212_53                    0x01U    /*!< ST25R500 Bit Rate  212 kbps (fc/64)                     */
#define ST25R500_BR_424                       0x02U    /*!< ST25R500 Bit Rate  424 kbps (fc/32) / 53 kbps(fc/256)   */
#define ST25R500_BR_848                       0x03U    /*!< ST25R500 Bit Rate  848 kbps (fc/16)                     */

#define ST25R500_REG_DROP_200                 0U       /*!< ST25R500 target drop for regulator adjustment: 200mV    */
#define ST25R500_REG_DROP_250                 1U       /*!< ST25R500 target drop for regulator adjustment: 250mV    */
#define ST25R500_REG_DROP_300                 2U       /*!< ST25R500 target drop for regulator adjustment: 300mV    */
#define ST25R500_REG_DROP_350                 3U       /*!< ST25R500 target drop for regulator adjustment: 350mV    */
#define ST25R500_REG_DROP_400                 4U       /*!< ST25R500 target drop for regulator adjustment: 400mV    */
#define ST25R500_REG_DROP_450                 5U       /*!< ST25R500 target drop for regulator adjustment: 450mV    */
#define ST25R500_REG_DROP_500                 6U       /*!< ST25R500 target drop for regulator adjustment: 500mV    */
#define ST25R500_REG_DROP_550                 7U       /*!< ST25R500 target drop for regulator adjustment: 550mV    */
#define ST25R500_REG_DROP_DO_NOT_SET          0xFFU    /*!< Indicates not to change this setting (regd)             */

#define ST25R500_THRESHOLD_DO_NOT_SET         0xFFU    /*!< Indicates not to change this Threshold                  */

#define ST25R500_REG_LEN                      1U       /*!< Number of bytes in a ST25R500 register                  */
#define ST25R500_CMD_LEN                      1U       /*!< ST25R500 CMD length                                     */
#define ST25R500_FIFO_DEPTH                   256U     /*!< Depth of FIFO                                           */
#define ST25R500_TOUT_OSC_STABLE              5U       /*!< Timeout for Oscillator to get stable                    */
                                              
#define ST25R500_WRITE_MODE                   (0U << 7)           /*!< ST25R500 Operation Mode: Write               */
#define ST25R500_READ_MODE                    (1U << 7)           /*!< ST25R500 Operation Mode: Read                */
#define ST25R500_CMD_MODE                     ST25R500_WRITE_MODE /*!< ST25R500 Operation Mode: Direct Command      */
#define ST25R500_FIFO_ACCESS                  (0x5FU)             /*!< ST25R500 FIFO Access                         */


#define ST25R500_DIAG_MEAS_CMD                0x01U               /*!< ST25R500 Diagnostic Measurement cmd size     */
#define ST25R500_DIAG_MEAS_CMD_LEN            0x02U               /*!< ST25R500 Diagnostic Measurement cmd length   */
#define ST25R500_DIAG_MEAS_RES_LEN            0x04U               /*!< ST25R500 Diagnostic Measurement res length   */

#define ST25R500_DIAG_MEAS_I_VDD_DR           0x01U               /*!< ST25R500 Diagnostic Measurement: I_VDD_DR    */
#define ST25R500_DIAG_MEAS_VDD_TX             0x02U               /*!< ST25R500 Diagnostic Measurement: VDD_TX      */
#define ST25R500_DIAG_MEAS_VDD_DR             0x03U               /*!< ST25R500 Diagnostic Measurement: VDD_DR      */
#define ST25R500_DIAG_MEAS_VDD_IO             0x04U               /*!< ST25R500 Diagnostic Measurement: VDD_IO      */
#define ST25R500_DIAG_MEAS_VDD_D              0x0CU               /*!< ST25R500 Diagnostic Measurement: VDD_D       */
#define ST25R500_DIAG_MEAS_VDD_A              0x0DU               /*!< ST25R500 Diagnostic Measurement: VDD_A       */
#define ST25R500_DIAG_MEAS_VDD_VDD            0x11U               /*!< ST25R500 Diagnostic Measurement: VDD         */
#define ST25R500_DIAG_MEAS_VDD_AGD            0x12U               /*!< ST25R500 Diagnostic Measurement: AGD         */


/*
******************************************************************************
* GLOBAL MACROS
******************************************************************************
*/

/*! Enables the Transmitter (Field On) and Receiver */
#define st25r500TxRxOn()             st25r500SetRegisterBits( ST25R500_REG_OPERATION, (ST25R500_REG_OPERATION_rx_en | ST25R500_REG_OPERATION_tx_en ) )

/*! Disables the Transmitter (Field Off) and Receiver                                         */
#define st25r500TxRxOff()            st25r500ClrRegisterBits( ST25R500_REG_OPERATION, (ST25R500_REG_OPERATION_rx_en | ST25R500_REG_OPERATION_tx_en ) )

/*! Enables the VDD_DR regulator */
#define st25r500VDDDROn()            st25r500SetRegisterBits( ST25R500_REG_OPERATION, (ST25R500_REG_OPERATION_vdddr_en | ST25R500_REG_OPERATION_vdddr_en ) )

/*! Disables the Transmitter (Field Off) and Receiver                                         */
#define st25r500VDDDROff()           st25r500ClrRegisterBits( ST25R500_REG_OPERATION, (ST25R500_REG_OPERATION_vdddr_en | ST25R500_REG_OPERATION_vdddr_en ) )

/*! Disables the Transmitter (Field Off) */
#define st25r500TxOff()              st25r500ClrRegisterBits( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_tx_en )

/*! Checks if General Purpose Timer is still running by reading gpt_on flag */
#define st25r500IsGPTRunning( )      st25r500CheckReg( ST25R500_REG_STATUS2, ST25R500_REG_STATUS2_gpt_on, ST25R500_REG_STATUS2_gpt_on )

/*! Checks if External Filed is detected by reading ST25R3916 External Field Detector output    */
#define st25r500IsExtFieldOn()       st25r500CheckReg( ST25R500_REG_STATUS1, ST25R500_REG_STATUS1_efd_out, ST25R500_REG_STATUS1_efd_out )

/*! Checks if Transmitter is enabled (Field On) */
#define st25r500IsTxEnabled()        st25r500CheckReg( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_tx_en, ST25R500_REG_OPERATION_tx_en )

/*! Checks if NRT is in EMV mode */
#define st25r500IsNRTinEMV()         st25r500CheckReg( ST25R500_REG_NRT_GPT_CONF, ST25R500_REG_NRT_GPT_CONF_nrt_emv, ST25R500_REG_NRT_GPT_CONF_nrt_emv_on )

/*! Checks if last FIFO byte is complete */
#define st25r500IsLastFIFOComplete() st25r500CheckReg( ST25R500_REG_FIFO_STATUS2, ST25R500_REG_FIFO_STATUS2_fifo_lb_mask, 0 )

/*! Checks if the Oscillator is enabled  */
#define st25r500IsOscOn()            st25r500CheckReg( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_en, ST25R500_REG_OPERATION_en )

/*! Checks if Transmitter (Field On) is enabled */
#define st25r500IsTxOn()             st25r500CheckReg( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_tx_en, ST25R500_REG_OPERATION_tx_en )

/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/


/*! 
 *****************************************************************************
 *  \brief  Initialise ST25R500 driver
 *
 *  This function initialises the ST25R500 driver.
 *
 *  \return RFAL_ERR_NONE         : Operation successful
 *  \return RFAL_ERR_HW_MISMATCH  : Expected HW do not match or communication error
 *****************************************************************************
 */
ReturnCode st25r500Initialize( void );


/*! 
 *****************************************************************************
 *  \brief  Deinitialize ST25R500 driver
 *
 *  Calling this function deinitializes the ST25R500 driver.
 *
 *****************************************************************************
 */
void st25r500Deinitialize( void );


/*! 
 *****************************************************************************
 *  \brief  Turn on Oscillator and Regulator
 *  
 *  This function turn on oscillator and regulator and waits for the 
 *  oscillator to become stable
 * 
 *  \return RFAL_ERR_SYSTEM: Unable to verify oscilator enable|stable
 *  \return RFAL_ERR_NONE  : No error
 *****************************************************************************
 */
ReturnCode st25r500OscOn( void );


/*! 
 *****************************************************************************
 *  \brief  Sets the bitrate
 *
 *  This function sets the bitrates for rx and tx
 *
 *  \param txRate : speed is 2^txrate * 106 kb/s
 *                  0xff : don't set txrate (ST25R500_BR_DO_NOT_SET)
 *  \param rxRate : speed is 2^rxrate * 106 kb/s
 *                  0xff : don't set rxrate (ST25R500_BR_DO_NOT_SET)
 *
 *  \return RFAL_ERR_PARAM: At least one bit rate was invalid
 *  \return RFAL_ERR_NONE : No error, both bit rates were set
 *
 *****************************************************************************
 */
ReturnCode st25r500SetBitrate( uint8_t txRate, uint8_t rxRate );


/*! 
 *****************************************************************************
 *  \brief  Adjusts supply regulators according to the current supply voltage
 *
 *  The power level is measured in maximum load conditions and
 *  the regulated voltage reference is set below this level.
 *
 *  The regulated voltages will be set to the result of Adjust Regulators
 *  
 *  \param [in]  drop   : Targeted drop from supply voltage
 *  \param [out] result : Result of calibration in milliVolts
 *
 *  \return RFAL_ERR_IO : Error during communication with ST25R500
 *  \return RFAL_ERR_NONE : No error
 *
 *****************************************************************************
 */
ReturnCode st25r500AdjustRegulators( uint8_t drop, uint16_t* result );


/*! 
 *****************************************************************************
 *  \brief  Sets supply regulators 
 *
 *  Manually sets the regulated voltage setting (rege).
 *  The regulated voltages will be set to the manual configuratiom.
 *
 *  Regulation shall be set according to the desired voltage considering the 
 *  supplied voltage.
 *  
 *  \param [in] regulation : Regulator setting
 *
 *  \return RFAL_ERR_IO    : Error during communication with ST25R500
 *  \return RFAL_ERR_PARAM : Invalid regulator setting
 *  \return RFAL_ERR_NONE  : No error
 *
 *****************************************************************************
 */
ReturnCode st25r500SetRegulators( uint8_t regulation );

/*! 
 *****************************************************************************
 *  \brief  Measure Amplitude
 *
 *  This function measured the amplitude on the RFI inputs and stores the
 *  result in parameter \a result.
 *
 *  \param[out] result:  result of RF measurement (unsigned)
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r500MeasureAmplitude( uint8_t* result );

/*! 
 *****************************************************************************
 *  \brief  Get Ce gain
 *
 *  This function retieves an RFI indicator
 *  and stores the result in parameter \a result.
 *
 *  \warning This method can only be executed in Listen mode
 *
 *  \param[out] result:  received signal indicator
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r500GetCeGain( uint8_t *result );


/*! 
 *****************************************************************************
 *  \brief  Measure I/Q
 *
 *  This function performs an I/Q measurement
 *  The result is stored on the \a resI and \a resQ parameters.
 *
 *  \param[out] resI: 8 bit long result of the I channel (signed)
 *  \param[out] resQ: 8 bit long result of the Q channel (signed)
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r500MeasureIQ( int8_t* resI, int8_t* resQ );


/*!
 *****************************************************************************
 *  \brief  Measure Combined I/Q
 *
 *  This function performs an I/Q measurement and returns the
 *  vectorial magnitude
 *
 *  \param[out] res
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *
 *****************************************************************************
 */
ReturnCode st25r500MeasureCombinedIQ( uint8_t* res );


/*!
 *****************************************************************************
 *  \brief  Measure I
 *
 *  This function performs an I/Q measurement and returns I
 *
 *  \param[out] res
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *
 *****************************************************************************
 */
ReturnCode st25r500MeasureI( uint8_t* res );


/*!
 *****************************************************************************
 *  \brief  Measure Q
 *
 *  This function performs an I/Q measurement and returns Q
 *
 *  \param[out] res
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *
 *****************************************************************************
 */
ReturnCode st25r500MeasureQ( uint8_t* res );


/*!
 *****************************************************************************
 *  \brief  Measure Phase
 *
 *  This function performs an I/Q measurement and returns the
 *  vectorial angle
 *
 *  \param[out] res
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *
 *****************************************************************************
 */
ReturnCode st25r500MeasurePhase( uint8_t* res );


/*!
 *****************************************************************************
 *  \brief  Measure electrical current
 *
 *  This function performs measurement of I_VDD_DR using
 *  Diagnostic Measurement Mode
 *  For limitations see st25r500DiagMeasure().
 *
 *  \param[out] res: Raw value - approx 3.2mA/unit
 *
 *  \return RFAL_ERR_WRONG_STATE : Measurement could not be performed (e.g. en=0)
 *  \return RFAL_ERR_NONE  : No error
 *
 *****************************************************************************
 */
ReturnCode st25r500MeasureCurrent( uint8_t* res );


/*! 
 *****************************************************************************
 *  \brief  Calibrate WU
 *
 *  This function executes Wake-up Calibration
 *
 *  \param[out] resI: I channel calibration (unsigned)
 *  \param[out] resQ: Q channel calibration (unsigned)
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r500CalibrateWU( uint16_t* resI, uint16_t* resQ );


/*! 
 *****************************************************************************
 *  \brief  Clear WU Calibration
 *
 *  This function clears WU calibration 
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r500ClearCalibration( void );


/*! 
 *****************************************************************************
 *  \brief  Measure WU
 *
 *  This function performs measuremnt as executed during WU mode
 *
 *  \param[out] resI: 8 bit long result of the I channel (signed)
 *  \param[out] resQ: 8 bit long result of the Q channel (signed)
 
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r500MeasureWU( uint8_t* resI, uint8_t* resQ );


/*! 
 *****************************************************************************
 *  \brief  Get NRT time
 *
 *  This returns the last value set on the NRT
 *   
 *  \warning it does not read chip register, just the sw var that contains the 
 *  last value set before
 *
 *  \return the value of the NRT in 64/fc 
 */
uint32_t st25r500GetNoResponseTime( void );


/*!
 *****************************************************************************
 *  \brief  Set NRT time
 *
 *  This function sets the No Response Time with the given value
 *
 *  \param [in] nrt   : no response time in steps of 64/fc (4.72us)
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter (time is too large)
 *  \return RFAL_ERR_NONE  : No error
 *
 *****************************************************************************  
 */
ReturnCode st25r500SetNoResponseTime( uint32_t nrt );


/*!
 *****************************************************************************
 *  \brief  Set MRT time
 *
 *  This function sets the Mask Receive Time with the given value. It also
 *  adapts mrt_step to achieve highest precision.
 *
 *  \param [in] value_fc   : mask receive time in steps of 1/fc
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter (time is too large), max will 
 *                           be set
 *  \return RFAL_ERR_NONE  : No error
 *
 ***************************************************************************
 */
ReturnCode st25r500SetMRT( uint32_t value_fc );


/*! 
 *****************************************************************************
 *  \brief  Set and Start NRT
 *
 *  This function sets the No Response Time with the given value and 
 *  immediately starts it
 *  Used when needs to add more time before timeout without performing Tx
 *
 *  \param [in] nrt   : no response time in steps of 64/fc (4.72us)
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *
 *****************************************************************************  
 */
ReturnCode st25r500SetStartNoResponseTimer( uint32_t nrt );


/*! 
 *****************************************************************************
 *  \brief  Set GPT time
 *
 *  This function sets the General Purpose Timer time registers
 *
 *  \param [in] gpt : general purpose timer timeout in steps of 8/fc (590ns)
 *
 *****************************************************************************
 */
void st25r500SetGPTime( uint16_t gpt );


/*! 
 *****************************************************************************
 *  \brief  Set and Start GPT
 *
 *  This function sets the General Purpose Timer with the given timeout and 
 *  immediately starts it ONLY if the trigger source is not set to none.
 *
 *  \param [in] gpt     : general purpose timer timeout in  steps of8/fc (590ns)
 *  \param [in] trigger : no trigger, start of Rx, end of Rx, end of Tx in NFC mode
 *   
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error 
 *  
 *****************************************************************************
 */
ReturnCode st25r500SetStartGPTimer( uint16_t gpt, uint8_t trigger );


/*! 
 *****************************************************************************
 *  \brief  Sets the number Tx Bits
 *  
 *  Sets ST25R500 internal registers with correct number of complete bytes and
 *  bits to be sent
 *  
 *  \param [in] nBits : number of bits to be set/transmitted
 *    
 *****************************************************************************
 */
void st25r500SetNumTxBits( uint16_t nBits );


/*! 
 *****************************************************************************
 *  \brief  Get amount of bytes in FIFO
 *  
 *  Gets the number of bytes currently in the FIFO
 *  
 *  \return the number of bytes currently in the FIFO
 *    
 *****************************************************************************
 */
uint16_t st25r500GetNumFIFOBytes( void );


/*! 
 *****************************************************************************
 *  \brief  Get amount of bits of the last FIFO byte if incomplete
 *  
 *  Gets the number of bits of the last FIFO byte if incomplete
 *  
 *  \return the number of bits of the last FIFO byte if incomplete, 0 if 
 *          the last byte is complete
 *    
 *****************************************************************************
 */
uint8_t st25r500GetNumFIFOLastBits( void );


/*! 
 *****************************************************************************
 *  \brief  Perform Collision Avoidance
 *
 *  Performs Collision Avoidance with the given threshold and with the  
 *  n number of TRFW 
 *  
 *  \param[in] atThreshold : Activation Threshold  (ST25R500_REG_EFD_THRESHOLDS_efd_at_xx)
 *                           0xff : don't set Threshold (ST25R500_THRESHOLD_DO_NOT_SET)
 *  \param[in] dtThreshold : Deactivation Threshold (ST25R500_REG_EFD_THRESHOLDS_efd_dt_xx)
 *                           0xff : don't set Threshold (ST25R500_THRESHOLD_DO_NOT_SET)
 *  \param[in] nTRFW       : Number of TRFW
 *
 *  \return RFAL_ERR_PARAM        : Invalid parameter 
 *  \return RFAL_ERR_RF_COLLISION : Collision detected
 *  \return RFAL_ERR_NONE         : No collision detected
 *  
 *****************************************************************************
 */
ReturnCode st25r500PerformCollisionAvoidance( uint8_t atThreshold, uint8_t dtThreshold, uint8_t nTRFW );


/*! 
 *****************************************************************************
 *  \brief  Check Identity
 *
 *  Checks if the chip ID is as expected.
 *  
 *  5 bit IC type code for ST25R500: 00101
 *  The 3 lsb contain the IC revision code
 *   
 *  \param[out] rev : the IC revision code
 *    
 *  \return  true when IC type is as expected
 *  \return  false otherwise
 */
bool st25r500CheckChipID( uint8_t *rev );


/*! 
 *****************************************************************************
 *  \brief  Register Dump
 *
 * Retrieves all internal registers from ST25R500
 *
 *  \param[out] resRegDump : pointer to the struct/buffer where the reg dump
 *                           will be written. NULL is allowed and causes only
 *                           reading to internal buffer
 *  \param[in,out] sizeRegDump : number of registers requested and the ones actually 
 *                               written
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 */
ReturnCode st25r500GetRegsDump( uint8_t* resRegDump, uint8_t* sizeRegDump );


/*! 
 *****************************************************************************
 *  \brief  Check if command is valid
 *
 *  Checks if the given command is a valid ST25R500 command
 *
 *  \param[in] cmd: Command to check
 *  
 *  \return  true if is a valid command
 *  \return  false otherwise
 *
 *****************************************************************************
 */
bool st25r500IsCmdValid( uint8_t cmd );


/*! 
 *****************************************************************************
 *  \brief  Executes a direct command and returns the result
 *
 *  This function executes the direct command given by \a cmd waits for
 *  \a sleeptime for I_dct and returns the result read from register \a resreg.
 *  The value of cmd is not checked.
 *
 *  \param[in]  cmd   : direct command to execute
 *  \param[in]  resReg: address of the register containing the result
 *  \param[in]  tOut  : time in milliseconds to wait before reading the result
 *  \param[out] result: result
 *
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r500ExecuteCommandAndGetResult( uint8_t cmd, uint8_t resReg, uint8_t tOut, uint8_t* result );


/*! 
 *****************************************************************************
 *  \brief  Gets the RSSI values
 *
 *  This function gets the RSSI value of the previous reception taking into 
 *  account the gain reductions that were used. 
 *  RSSI value for both I and Q channel can be retrieved.
 *
 *  \param[out] iRssi: the RSSI on the I channel expressed in mV 
 *  \param[out] qRssi: the RSSI on the Q channel expressed in mV 
 *  
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r500GetRSSI( uint16_t *iRssi, uint16_t *qRssi );


/*! 
 *****************************************************************************
 * \brief  Set Antenna mode
 *
 * Sets the antenna mode. 
 * Differential or single ended antenna mode (RFO1 or RFO2)
 *
 *  \param[in]   single:   FALSE differential ; single ended mode
 *  \param[in]    rfiox:   FALSE   RFI1/RFO1  ; TRUE   RFI2/RFO2
 *
 *  \return  RFAL_ERR_IO      : Internal error
 *  \return  RFAL_ERR_NOTSUPP : Feature not supported
 *  \return  RFAL_ERR_NONE    : No error
 *****************************************************************************
 */
ReturnCode st25r500SetAntennaMode( bool single, bool rfiox );


/*!
 *****************************************************************************
 * \brief  Diagnostic Measurement
 *
 * Performs a diagnostic measurement of certain currents and voltages.
 * The function does not work when oscillator is not enabled. For its operation
 * it may temporarily enable the reciever (rx_en=1).
 * Ongoing transmissions/receptions (also in CE mode) may be garbled when
 * this functions is executed.
 *
 *  \param[in]   meas: the measurement function to perform, see ST25R500_DIAG_MEAS_*
 *  \param[out]  res:  9 bit unsigned value
 *
 * \return RFAL_ERR_WRONG_STATE : Measurement could not be performed (e.g. en=0)
 * \return  RFAL_ERR_NONE    : No error
 *****************************************************************************
 */
ReturnCode st25r500DiagMeasure( uint8_t meas, uint16_t *res );

#endif /* ST25R500_H */

/**
  * @}
  *
  * @}
  *
  * @}
  * 
  * @}
  */
