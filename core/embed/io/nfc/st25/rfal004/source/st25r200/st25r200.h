
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

/*! \file st25r200.h
 *
 *  \author Gustavo Patricio
 *
 *  \brief ST25R200 high level interface
 *
 *
 * \addtogroup RFAL
 * @{
 *
 * \addtogroup RFAL-HAL
 * \brief RFAL Hardware Abstraction Layer
 * @{
 *
 * \addtogroup ST25R200
 * \brief RFAL ST25R200 Driver
 * @{
 * 
 * \addtogroup ST25R200_Driver
 * \brief RFAL ST25R200 Driver
 * @{
 * 
 */


#ifndef ST25R200_H
#define ST25R200_H

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include "rfal_platform.h"
#include "rfal_utils.h"
#include "st25r200_com.h"

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

/* ST25R200 direct commands */
#define ST25R200_CMD_SET_DEFAULT              0x60U    /*!< Puts the chip in default state (same as after power-up) */
#define ST25R200_CMD_STOP                     0x62U    /*!< Stops all activities and clears FIFO                    */
#define ST25R200_CMD_CLEAR_FIFO               0x64U    /*!< Clears FIFO, Collision and IRQ status                   */
#define ST25R200_CMD_CLEAR_RXGAIN             0x66U    /*!< Clears FIFO, Collision and IRQ status                   */
#define ST25R200_CMD_ADJUST_REGULATORS        0x68U    /*!< Adjust regulators                                       */
#define ST25R200_CMD_TRANSMIT                 0x6AU    /*!< Transmit                                                */
#define ST25R200_CMD_TRANSMIT_EOF             0x6CU    /*!< Transmit ISO15693 EOF                                   */
#define ST25R200_CMD_MASK_RECEIVE_DATA        0x70U    /*!< Mask receive data                                       */
#define ST25R200_CMD_UNMASK_RECEIVE_DATA      0x72U    /*!< Unmask receive data                                     */
#define ST25R200_CMD_CALIBRATE_WU             0x74U    /*!< Calibrate Wake-up Measurement                           */
#define ST25R200_CMD_CLEAR_WU_CALIB           0x76U    /*!< Clear Wake-up Calibratation                             */
#define ST25R200_CMD_MEASURE_WU               0x78U    /*!< Measure Wake-up I and Q components                      */
#define ST25R200_CMD_MEASURE_IQ               0x7AU    /*!< Measure I and Q components                              */
#define ST25R200_CMD_SENSE_RF                 0x7CU    /*!< Sense RF on RFI pins                                    */
#define ST25R200_CMD_TRANSPARENT_MODE         0xE0U    /*!< Transparent mode                                        */
#define ST25R200_CMD_START_GP_TIMER           0xE2U    /*!< Start the general purpose timer                         */
#define ST25R200_CMD_START_WUT                0xE4U    /*!< Start the wake-up timer                                 */
#define ST25R200_CMD_START_MRT                0xE6U    /*!< Start the mask-receive timer                            */
#define ST25R200_CMD_START_NRT                0xE8U    /*!< Start the no-response timer                             */
#define ST25R200_CMD_STOP_NRT                 0xEAU    /*!< Stop No Response Timer                                  */
#define ST25R200_CMD_TEST_ACCESS              0xFCU    /*!< Enable R/W access to the test registers                 */


#define ST25R200_BR_DO_NOT_SET                0xFFU    /*!< Indicates not to change this Bit Rate                   */
#define ST25R200_BR_106_26                    0x00U    /*!< ST25R200 Bit Rate  106 kbps (fc/128) / 26 kbps(fc/512)  */
#define ST25R200_BR_212                       0x01U    /*!< ST25R200 Bit Rate  212 kbps (fc/64)                     */
#define ST25R200_BR_424_53                    0x02U    /*!< ST25R200 Bit Rate  424 kbps (fc/32) / 53 kbps(fc/256)   */
#define ST25R200_BR_848                       0x03U    /*!< ST25R200 Bit Rate  848 kbps (fc/16)                     */

#define ST25R200_REG_DROP_200                 0U       /*!< ST25R200 target drop for regulator adjustment: 200mV    */
#define ST25R200_REG_DROP_250                 1U       /*!< ST25R200 target drop for regulator adjustment: 250mV    */
#define ST25R200_REG_DROP_300                 2U       /*!< ST25R200 target drop for regulator adjustment: 300mV    */
#define ST25R200_REG_DROP_350                 3U       /*!< ST25R200 target drop for regulator adjustment: 350mV    */
#define ST25R200_REG_DROP_400                 4U       /*!< ST25R200 target drop for regulator adjustment: 400mV    */
#define ST25R200_REG_DROP_450                 5U       /*!< ST25R200 target drop for regulator adjustment: 450mV    */
#define ST25R200_REG_DROP_500                 6U       /*!< ST25R200 target drop for regulator adjustment: 500mV    */
#define ST25R200_REG_DROP_550                 7U       /*!< ST25R200 target drop for regulator adjustment: 550mV    */
#define ST25R200_REG_DROP_DO_NOT_SET          0xFFU    /*!< Indicates not to change this setting (regd)             */

#define ST25R200_REG_LEN                      1U       /*!< Number of bytes in a ST25R200 register                  */
#define ST25R200_CMD_LEN                      1U       /*!< ST25R200 CMD length                                     */
#define ST25R200_FIFO_DEPTH                   256U     /*!< Depth of FIFO                                           */
                                              
#define ST25R200_WRITE_MODE                   (0U << 7)           /*!< ST25R200 Operation Mode: Write               */
#define ST25R200_READ_MODE                    (1U << 7)           /*!< ST25R200 Operation Mode: Read                */
#define ST25R200_CMD_MODE                     ST25R200_WRITE_MODE /*!< ST25R200 Operation Mode: Direct Command      */
#define ST25R200_FIFO_ACCESS                  (0x5FU)             /*!< ST25R200 FIFO Access                         */

/*
******************************************************************************
* GLOBAL MACROS
******************************************************************************
*/

/*! Enables the Transmitter (Field On) and Receiver */
#define st25r200TxRxOn()             st25r200SetRegisterBits( ST25R200_REG_OPERATION, (ST25R200_REG_OPERATION_rx_en | ST25R200_REG_OPERATION_tx_en ) )

/*! Disables the Transmitter (Field Off) and Receiver                                         */
#define st25r200TxRxOff()            st25r200ClrRegisterBits( ST25R200_REG_OPERATION, (ST25R200_REG_OPERATION_rx_en | ST25R200_REG_OPERATION_tx_en ) )

/*! Disables the Transmitter (Field Off) */
#define st25r200TxOff()              st25r200ClrRegisterBits( ST25R200_REG_OPERATION, ST25R200_REG_OPERATION_tx_en )

/*! Checks if General Purpose Timer is still running by reading gpt_on flag */
#define st25r200IsGPTRunning( )      st25r200CheckReg( ST25R200_REG_STATUS, ST25R200_REG_STATUS_gpt_on, ST25R200_REG_STATUS_gpt_on )

/*! Checks if Transmitter is enabled (Field On) */
#define st25r200IsTxEnabled()        st25r200CheckReg( ST25R200_REG_OPERATION, ST25R200_REG_OPERATION_tx_en, ST25R200_REG_OPERATION_tx_en )

/*! Checks if NRT is in EMV mode */
#define st25r200IsNRTinEMV()         st25r200CheckReg( ST25R200_REG_NRT_GPT_CONF, ST25R200_REG_NRT_GPT_CONF_nrt_emd, ST25R200_REG_NRT_GPT_CONF_nrt_emd_on )

/*! Checks if last FIFO byte is complete */
#define st25r200IsLastFIFOComplete() st25r200CheckReg( ST25R200_REG_FIFO_STATUS2, ST25R200_REG_FIFO_STATUS2_fifo_lb_mask, 0 )

/*! Checks if the Oscillator is enabled  */
#define st25r200IsOscOn()            st25r200CheckReg( ST25R200_REG_OPERATION, ST25R200_REG_OPERATION_en, ST25R200_REG_OPERATION_en )

/*! Checks if Transmitter (Field On) is enabled */
#define st25r200IsTxOn()             st25r200CheckReg( ST25R200_REG_OPERATION, ST25R200_REG_OPERATION_tx_en, ST25R200_REG_OPERATION_tx_en )

/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/

/*! 
 *****************************************************************************
 *  \brief  Initialise ST25R200 driver
 *
 *  This function initialises the ST25R200 driver.
 *
 *  \return RFAL_ERR_NONE         : Operation successful
 *  \return RFAL_ERR_HW_MISMATCH  : Expected HW do not match or communication error
 *****************************************************************************
 */
ReturnCode st25r200Initialize( void );


/*! 
 *****************************************************************************
 *  \brief  Deinitialize ST25R200 driver
 *
 *  Calling this function deinitializes the ST25R200 driver.
 *
 *****************************************************************************
 */
void st25r200Deinitialize( void );


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
ReturnCode st25r200OscOn( void );


/*! 
 *****************************************************************************
 *  \brief  Sets the bitrate
 *
 *  This function sets the bitrates for rx and tx
 *
 *  \param txRate : speed is 2^txrate * 106 kb/s
 *                  0xff : don't set txrate (ST25R200_BR_DO_NOT_SET)
 *  \param rxRate : speed is 2^rxrate * 106 kb/s
 *                  0xff : don't set rxrate (ST25R200_BR_DO_NOT_SET)
 *
 *  \return RFAL_ERR_PARAM: At least one bit rate was invalid
 *  \return RFAL_ERR_NONE : No error, both bit rates were set
 *
 *****************************************************************************
 */
ReturnCode st25r200SetBitrate( uint8_t txRate, uint8_t rxRate );


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
 *  \return RFAL_ERR_IO : Error during communication with ST25R200
 *  \return RFAL_ERR_NONE : No error
 *
 *****************************************************************************
 */
ReturnCode st25r200AdjustRegulators( uint8_t drop, uint16_t* result );


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
 *  \return RFAL_ERR_IO    : Error during communication with ST25R200
 *  \return RFAL_ERR_PARAM : Invalid regulator setting
 *  \return RFAL_ERR_NONE  : No error
 *
 *****************************************************************************
 */
ReturnCode st25r200SetRegulators( uint8_t regulation );

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
 *  \warning Before executing I|Q Measurement the WU calibration
 *           shall be cleared, \see st25r200ClearCalibration()
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r200MeasureIQ( int8_t* resI, int8_t* resQ );


/*! 
 *****************************************************************************
 *  \brief  Measure Combined I/Q
 *
 *  This function performs an I/Q measurement and returns the 
 *  vectorial magnitude
 *
 *  \param[out] res: 8 bit result of the I Q magnitude
 *                   Max value is: 127
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r200MeasureCombinedIQ( uint8_t* res );


/*! 
 *****************************************************************************
 *  \brief  Measure I
 *
 *  This function measures I channel
 *
 *  \param[out] res: I channel
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r200MeasureI( uint8_t* res );


/*! 
 *****************************************************************************
 *  \brief  Measure Q
 *
 *  This function measures Q channel
 *
 *  \param[out] res: Q channel
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r200MeasureQ( uint8_t* res );


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
ReturnCode st25r200CalibrateWU( uint8_t* resI, uint8_t* resQ );


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
ReturnCode st25r200ClearCalibration( void );


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
ReturnCode st25r200MeasureWU( uint8_t* resI, uint8_t* resQ );


/*! 
 *****************************************************************************
 *  \brief  Check External Filed 
 *
 *  This function checks if External Field is detected by performing 
 *  Sense RF procedure
 *
 *  \warning ST25R200 is not equipped with an External Field Detector block.
 *            One can try to assess the presence of an external RF carrier by
 *            observing the signal on the RFIs while own field is turned off.
 *            WU calibration will be cleared.
 *
 *  \return  true external signal was sensed
 *  \return  false unable to detect the presence of  an external field
 *  
 *****************************************************************************
 */
bool st25r200IsExtFieldOn( void );


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
uint32_t st25r200GetNoResponseTime( void );


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
ReturnCode st25r200SetNoResponseTime( uint32_t nrt );


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
ReturnCode st25r200SetStartNoResponseTimer( uint32_t nrt );


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
void st25r200SetGPTime( uint16_t gpt );


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
ReturnCode st25r200SetStartGPTimer( uint16_t gpt, uint8_t trigger );


/*! 
 *****************************************************************************
 *  \brief  Sets the number Tx Bits
 *  
 *  Sets ST25R200 internal registers with correct number of complete bytes and
 *  bits to be sent
 *  
 *  \param [in] nBits : number of bits to be set/transmitted
 *    
 *****************************************************************************
 */
void st25r200SetNumTxBits( uint16_t nBits );


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
uint16_t st25r200GetNumFIFOBytes( void );


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
uint8_t st25r200GetNumFIFOLastBits( void );


/*! 
 *****************************************************************************
 *  \brief  Perform Collision Avoidance
 *
 *  Performs Collision Avoidance
 *
 *  \return RFAL_ERR_PARAM        : Invalid parameter 
 *  \return RFAL_ERR_RF_COLLISION : Collision detected
 *  \return RFAL_ERR_NONE         : No collision detected
 *  
 *****************************************************************************
 */
ReturnCode st25r200PerformCollisionAvoidance( void );


/*! 
 *****************************************************************************
 *  \brief  Check Identity
 *
 *  Checks if the chip ID is as expected.
 *  
 *  5 bit IC type code for ST25R200: 00101
 *  The 3 lsb contain the IC revision code
 *   
 *  \param[out] rev : the IC revision code
 *    
 *  \return  true when IC type is as expected
 *  \return  false otherwise
 */
bool st25r200CheckChipID( uint8_t *rev );


/*! 
 *****************************************************************************
 *  \brief  Register Dump
 *
 * Retrieves all internal registers from ST25R200
 *
 *  \param[out] resRegDump : pointer to the struct/buffer where the reg dump
 *                               will be written
 *  \param[in,out] sizeRegDump : number of registers requested and the ones actually 
 *                               written
 *
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 */
ReturnCode st25r200GetRegsDump( uint8_t* resRegDump, uint8_t* sizeRegDump );


/*! 
 *****************************************************************************
 *  \brief  Check if command is valid
 *
 *  Checks if the given command is a valid ST25R200 command
 *
 *  \param[in] cmd: Command to check
 *  
 *  \return  true if is a valid command
 *  \return  false otherwise
 *
 *****************************************************************************
 */
bool st25r200IsCmdValid( uint8_t cmd );


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
ReturnCode st25r200ExecuteCommandAndGetResult( uint8_t cmd, uint8_t resReg, uint8_t tOut, uint8_t* result );


/*! 
 *****************************************************************************
 *  \brief  Gets the RSSI values
 *
 *  This function gets the RSSI value of the previous reception taking into 
 *  account the gain reductions that were used. 
 *  RSSI value for both AM and PM channel can be retrieved.
 *
 *  \param[out] iRssi: the RSSI on the I channel expressed in mV 
 *  \param[out] qRssi: the RSSI on the Q channel expressed in mV 
 *  
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_NONE  : No error
 *  
 *****************************************************************************
 */
ReturnCode st25r200GetRSSI( uint16_t *iRssi, uint16_t *qRssi );


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
 * \return  RFAL_ERR_IO      : Internal error
 * \return  RFAL_ERR_NOTSUPP : Feature not supported
 * \return  RFAL_ERR_NONE    : No error
 *****************************************************************************
 */
ReturnCode st25r200SetAntennaMode( bool single, bool rfiox );

#endif /* ST25R200_H */

/**
  * @}
  *
  * @}
  *
  * @}
  * 
  * @}
  */
