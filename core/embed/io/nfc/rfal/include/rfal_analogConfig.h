
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2020 STMicroelectronics, all rights reserved
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
 *      PROJECT:   ST25R391x firmware
 *      Revision:
 *      LANGUAGE:  ISO C99
 */

/*! \file rfal_AnalogConfig.h
 *
 *  \author bkam
 *
 *  \brief RF Chip Analog Configuration Settings
 *  
 *  
 * \addtogroup RFAL
 * @{
 *
 * \addtogroup RFAL-HAL
 * \brief RFAL Hardware Abstraction Layer
 * @{
 *
 * \addtogroup AnalogConfig
 * \brief RFAL Analog Config Module
 * @{
 * 
 */

#ifndef RFAL_ANALOG_CONFIG_H
#define RFAL_ANALOG_CONFIG_H

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_platform.h"
#include "rfal_utils.h"
#include "rfal_rf.h"

/*
 ******************************************************************************
 * DEFINES
 ******************************************************************************
 */

#define RFAL_ANALOG_CONFIG_LUT_SIZE                 (87U)     /*!< Maximum number of Configuration IDs in the Loop Up Table     */
#define RFAL_ANALOG_CONFIG_LUT_NOT_FOUND            (0xFFU)   /*!< Index value indicating no Configuration IDs found            */

#define RFAL_ANALOG_CONFIG_TBL_SIZE                 (1024U)   /*!< Maximum number of Register-Mask-Value in the Setting List    */

/*
 ******************************************************************************
 * The Analog Configuration is structured as following
 * +---------+-----------------------+-----------------------------+
 * | ModeID  | Num RVM configuration | RVM (Register, Value, Mask) |
 * | (16bit) | (8bit)                | (24bit)                     |
 * +---------+-----------------------+-----------------------------+
 *
 * The Mode ID coding for different use cases is described below
 * 
 * 1. ModeID coding for NFC technologies (not chip specific)
 * +----------------------------------------------------------------------+
 * | 15  | 14 | 13 | 12 | 11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
 * +----------------------------------------------------------------------+
 * | P/L | TECH != CHIP                   | BR            | DIR           |
 * +----------------------------------------------------------------------+
 * 
 * 2. ModeID coding for chip specific modes and events
 * +----------------------------------------------------------------------+
 * | 15  | 14 | 13 | 12 | 11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
 * +----------------------------------------------------------------------+
 * | P/L | TECH == CHIP                   | CHIP_SPECIFIC                 |
 * +----------------------------------------------------------------------+
 * 
 * 3. Special ModeID coding for Direction == DPO
 * +----------------------------------------------------------------------+
 * | 15  | 14 | 13 | 12 | 11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
 * +----------------------------------------------------------------------+
 * | P/L | DPO_LVL | TECH*                | BR            | DIR == DPO    |
 * +----------------------------------------------------------------------+
 *            ^
 *            | 
 *            +----- reuse of TECH_RFU bits as DPO level indicator
 ******************************************************************************
 */
 
/* Mask bit */ 
#define RFAL_ANALOG_CONFIG_POLL_LISTEN_MODE_MASK    (0x8000U) /*!< Mask bit of Poll Mode in Analog Configuration ID             */
#define RFAL_ANALOG_CONFIG_TECH_MASK                (0x7F00U) /*!< Mask bits for Technology in Analog Configuration ID          */
#define RFAL_ANALOG_CONFIG_BITRATE_MASK             (0x00F0U) /*!< Mask bits for Bit rate in Analog Configuration ID            */
#define RFAL_ANALOG_CONFIG_DIRECTION_MASK           (0x000FU) /*!< Mask bits for Direction in Analog Configuration ID           */
#define RFAL_ANALOG_CONFIG_CHIP_SPECIFIC_MASK       (0x00FFU) /*!< Mask bits for Chip Specific Technology                       */

/* Shift values */
#define RFAL_ANALOG_CONFIG_POLL_LISTEN_MODE_SHIFT   (15U)     /*!< Shift value of Poll Mode in Analog Configuration ID          */
#define RFAL_ANALOG_CONFIG_TECH_SHIFT               (8U)      /*!< Shift value for Technology in Analog Configuration ID        */
#define RFAL_ANALOG_CONFIG_BITRATE_SHIFT            (4U)      /*!< Shift value for Technology in Analog Configuration ID        */
#define RFAL_ANALOG_CONFIG_DIRECTION_SHIFT          (0U)      /*!< Shift value for Direction in Analog Configuration ID         */

/* P/L: bit 15 */
#define RFAL_ANALOG_CONFIG_POLL                     (0x0000U) /*!< Poll Mode bit setting in Analog Configuration ID             */
#define RFAL_ANALOG_CONFIG_LISTEN                   (0x8000U) /*!< Listen Mode bit setting in Analog Configuration ID           */

/* TECH: bit 14-8 */
#define RFAL_ANALOG_CONFIG_TECH_CHIP                (0x0000U) /*!< Chip-Specific bit setting in Analog Configuration ID         */
#define RFAL_ANALOG_CONFIG_TECH_NFCA                (0x0100U) /*!< NFC-A Technology bits setting in Analog Configuration ID     */
#define RFAL_ANALOG_CONFIG_TECH_NFCB                (0x0200U) /*!< NFC-B Technology bits setting in Analog Configuration ID     */
#define RFAL_ANALOG_CONFIG_TECH_NFCF                (0x0400U) /*!< NFC-F Technology bits setting in Analog Configuration ID     */
#define RFAL_ANALOG_CONFIG_TECH_AP2P                (0x0800U) /*!< AP2P Technology bits setting in Analog Configuration ID      */
#define RFAL_ANALOG_CONFIG_TECH_NFCV                (0x1000U) /*!< NFC-V Technology bits setting in Analog Configuration ID     */
#define RFAL_ANALOG_CONFIG_TECH_RFU                 (0x2000U) /*!< RFU for Technology bits */
#define RFAL_ANALOG_CONFIG_TECH_RFU2                (0x4000U) /*!< RFU for Technology bits */

/* BR: bit 7-4 */
#define RFAL_ANALOG_CONFIG_BITRATE_COMMON           (0x0000U) /*!< Common settings for all bit rates in Analog Configuration ID */
#define RFAL_ANALOG_CONFIG_BITRATE_106              (0x0010U) /*!< 106kbits/s settings in Analog Configuration ID               */
#define RFAL_ANALOG_CONFIG_BITRATE_212              (0x0020U) /*!< 212kbits/s settings in Analog Configuration ID               */
#define RFAL_ANALOG_CONFIG_BITRATE_424              (0x0030U) /*!< 424kbits/s settings in Analog Configuration ID               */
#define RFAL_ANALOG_CONFIG_BITRATE_848              (0x0040U) /*!< 848kbits/s settings in Analog Configuration ID               */
#define RFAL_ANALOG_CONFIG_BITRATE_1695             (0x0050U) /*!< 1695kbits/s settings in Analog Configuration ID              */
#define RFAL_ANALOG_CONFIG_BITRATE_3390             (0x0060U) /*!< 3390kbits/s settings in Analog Configuration ID              */
#define RFAL_ANALOG_CONFIG_BITRATE_6780             (0x0070U) /*!< 6780kbits/s settings in Analog Configuration ID              */
#define RFAL_ANALOG_CONFIG_BITRATE_211p88           (0x0090U) /*!< 211.88kbits/s (ISO15693 x8) in Analog Configuration ID       */
#define RFAL_ANALOG_CONFIG_BITRATE_105p94           (0x00A0U) /*!< 105.94kbits/s (ISO15693 x4) in Analog Configuration ID       */
#define RFAL_ANALOG_CONFIG_BITRATE_53               (0x00B0U) /*!< 53kbits/s (ISO15693 x2) setting in Analog Configuration ID   */
#define RFAL_ANALOG_CONFIG_BITRATE_26               (0x00C0U) /*!< 26kbit/s (1 out of 4) NFC-V setting Analog Configuration ID  */
#define RFAL_ANALOG_CONFIG_BITRATE_1p6              (0x00D0U) /*!< 1.6kbit/s (1 out of 256) NFC-V setting Analog Config ID      */
#define RFAL_ANALOG_CONFIG_BITRATE_RFU              (0x00E0U) /*!< RFU for Bitrate bits                                         */
#define RFAL_ANALOG_CONFIG_BITRATE_RFU2             (0x00F0U) /*!< RFU for Bitrate bits                                         */

/* DIR: bit 3-0 */
#define RFAL_ANALOG_CONFIG_NO_DIRECTION             (0x0000U) /*!< No direction setting in Analog Conf ID (Chip Specific only)  */
#define RFAL_ANALOG_CONFIG_TX                       (0x0001U) /*!< Transmission bit setting in Analog Configuration ID          */
#define RFAL_ANALOG_CONFIG_RX                       (0x0002U) /*!< Reception bit setting in Analog Configuration ID             */
#define RFAL_ANALOG_CONFIG_ANTICOL                  (0x0003U) /*!< Anticollision setting in Analog Configuration ID             */
#define RFAL_ANALOG_CONFIG_DPO                      (0x0004U) /*!< DPO setting in Analog Configuration ID                       */
#define RFAL_ANALOG_CONFIG_DLMA                     (0x0005U) /*!< DLMA setting in Analog Configuration ID                      */
#define RFAL_ANALOG_CONFIG_DIRECTION_RFU2           (0x0006U) /*!< RFU for Direction bits                                       */
#define RFAL_ANALOG_CONFIG_DIRECTION_RFU3           (0x0007U) /*!< RFU for Direction bits                                       */
#define RFAL_ANALOG_CONFIG_DIRECTION_RFU4           (0x0008U) /*!< RFU for Direction bits                                       */
#define RFAL_ANALOG_CONFIG_DIRECTION_RFU5           (0x0009U) /*!< RFU for Direction bits                                       */
#define RFAL_ANALOG_CONFIG_DIRECTION_RFU6           (0x000AU) /*!< RFU for Direction bits                                       */
#define RFAL_ANALOG_CONFIG_DIRECTION_RFU7           (0x000BU) /*!< RFU for Direction bits                                       */
#define RFAL_ANALOG_CONFIG_DIRECTION_RFU8           (0x000CU) /*!< RFU for Direction bits                                       */
#define RFAL_ANALOG_CONFIG_DIRECTION_RFU9           (0x000DU) /*!< RFU for Direction bits                                       */
#define RFAL_ANALOG_CONFIG_DIRECTION_RFU10          (0x000EU) /*!< RFU for Direction bits                                       */
#define RFAL_ANALOG_CONFIG_DIRECTION_RFU11          (0x000FU) /*!< RFU for Direction bits                                       */

/* bit 7-0 */
#define RFAL_ANALOG_CONFIG_CHIP_INIT                (0x0000U)  /*!< Chip-Specific event: Startup;Reset;Initialize                */
#define RFAL_ANALOG_CONFIG_CHIP_DEINIT              (0x0001U)  /*!< Chip-Specific event: Deinitialize                            */
#define RFAL_ANALOG_CONFIG_CHIP_FIELD_ON            (0x0002U)  /*!< Chip-Specific event: Field On                                */
#define RFAL_ANALOG_CONFIG_CHIP_FIELD_OFF           (0x0003U)  /*!< Chip-Specific event: Field Off                               */
#define RFAL_ANALOG_CONFIG_CHIP_WAKEUP_ON           (0x0004U)  /*!< Chip-Specific event: Wake-up On                              */
#define RFAL_ANALOG_CONFIG_CHIP_WAKEUP_OFF          (0x0005U)  /*!< Chip-Specific event: Wake-up Off                             */
#define RFAL_ANALOG_CONFIG_CHIP_LISTEN_ON           (0x0006U)  /*!< Chip-Specific event: Listen On                               */
#define RFAL_ANALOG_CONFIG_CHIP_LISTEN_OFF          (0x0007U)  /*!< Chip-Specific event: Listen Off                              */
#define RFAL_ANALOG_CONFIG_CHIP_POLL_COMMON         (0x0008U)  /*!< Chip-Specific event: Poll common                             */
#define RFAL_ANALOG_CONFIG_CHIP_LISTEN_COMMON       (0x0009U)  /*!< Chip-Specific event: Listen common                           */
#define RFAL_ANALOG_CONFIG_CHIP_LOWPOWER_ON         (0x000AU)  /*!< Chip-Specific event: Low Power On                            */
#define RFAL_ANALOG_CONFIG_CHIP_LOWPOWER_OFF        (0x000BU)  /*!< Chip-Specific event: Low Power Off                           */

#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_00        (0x0010U)  /*!< Chip-Specific event: Power Level 00 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_01        (0x0011U)  /*!< Chip-Specific event: Power Level 01 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_02        (0x0012U)  /*!< Chip-Specific event: Power Level 02 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_03        (0x0013U)  /*!< Chip-Specific event: Power Level 03 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_04        (0x0014U)  /*!< Chip-Specific event: Power Level 04 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_05        (0x0015U)  /*!< Chip-Specific event: Power Level 05 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_06        (0x0016U)  /*!< Chip-Specific event: Power Level 06 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_07        (0x0017U)  /*!< Chip-Specific event: Power Level 07 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_08        (0x0018U)  /*!< Chip-Specific event: Power Level 08 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_09        (0x0019U)  /*!< Chip-Specific event: Power Level 09 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_10        (0x001AU)  /*!< Chip-Specific event: Power Level 10 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_11        (0x001BU)  /*!< Chip-Specific event: Power Level 11 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_12        (0x001CU)  /*!< Chip-Specific event: Power Level 12 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_13        (0x001DU)  /*!< Chip-Specific event: Power Level 13 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_14        (0x001EU)  /*!< Chip-Specific event: Power Level 14 (e.g DPO, WLC)           */
#define RFAL_ANALOG_CONFIG_CHIP_POWER_LVL_15        (0x001FU)  /*!< Chip-Specific event: Power Level 15 (e.g DPO, WLC)           */

#define RFAL_ANALOG_CONFIG_UPDATE_LAST              (0x00U)   /*!< Value indicating Last configuration set during update        */
#define RFAL_ANALOG_CONFIG_UPDATE_MORE              (0x01U)   /*!< Value indicating More configuration set coming during update */

 
/*
 ******************************************************************************
 * GLOBAL MACROS
 ******************************************************************************
 */

#define RFAL_ANALOG_CONFIG_ID_GET_POLL_LISTEN(id)   (RFAL_ANALOG_CONFIG_POLL_LISTEN_MODE_MASK & (id)) /*!< Check if id indicates Listen mode   */

#define RFAL_ANALOG_CONFIG_ID_GET_TECH(id)          (RFAL_ANALOG_CONFIG_TECH_MASK & (id))      /*!< Get the technology of Configuration ID     */
#define RFAL_ANALOG_CONFIG_ID_IS_CHIP(id)           (RFAL_ANALOG_CONFIG_TECH_MASK & (id))      /*!< Check if ID indicates Chip-specific        */
#define RFAL_ANALOG_CONFIG_ID_IS_NFCA(id)           (RFAL_ANALOG_CONFIG_TECH_NFCA & (id))      /*!< Check if ID indicates NFC-A                */
#define RFAL_ANALOG_CONFIG_ID_IS_NFCB(id)           (RFAL_ANALOG_CONFIG_TECH_NFCB & (id))      /*!< Check if ID indicates NFC-B                */
#define RFAL_ANALOG_CONFIG_ID_IS_NFCF(id)           (RFAL_ANALOG_CONFIG_TECH_NFCF & (id))      /*!< Check if ID indicates NFC-F                */
#define RFAL_ANALOG_CONFIG_ID_IS_AP2P(id)           (RFAL_ANALOG_CONFIG_TECH_AP2P & (id))      /*!< Check if ID indicates AP2P                 */
#define RFAL_ANALOG_CONFIG_ID_IS_NFCV(id)           (RFAL_ANALOG_CONFIG_TECH_NFCV & (id))      /*!< Check if ID indicates NFC-V                */

#define RFAL_ANALOG_CONFIG_ID_GET_BITRATE(id)       (RFAL_ANALOG_CONFIG_BITRATE_MASK & (id))   /*!< Get Bitrate of Configuration ID            */
#define RFAL_ANALOG_CONFIG_ID_IS_COMMON(id)         (RFAL_ANALOG_CONFIG_BITRATE_MASK & (id))   /*!< Check if ID indicates common bitrate       */
#define RFAL_ANALOG_CONFIG_ID_IS_106(id)            (RFAL_ANALOG_CONFIG_BITRATE_106  & (id))   /*!< Check if ID indicates 106kbits/s           */
#define RFAL_ANALOG_CONFIG_ID_IS_212(id)            (RFAL_ANALOG_CONFIG_BITRATE_212  & (id))   /*!< Check if ID indicates 212kbits/s           */
#define RFAL_ANALOG_CONFIG_ID_IS_424(id)            (RFAL_ANALOG_CONFIG_BITRATE_424  & (id))   /*!< Check if ID indicates 424kbits/s           */
#define RFAL_ANALOG_CONFIG_ID_IS_848(id)            (RFAL_ANALOG_CONFIG_BITRATE_848  & (id))   /*!< Check if ID indicates 848kbits/s           */
#define RFAL_ANALOG_CONFIG_ID_IS_1695(id)           (RFAL_ANALOG_CONFIG_BITRATE_1695 & (id))   /*!< Check if ID indicates 1695kbits/s          */
#define RFAL_ANALOG_CONFIG_ID_IS_3390(id)           (RFAL_ANALOG_CONFIG_BITRATE_3390 & (id))   /*!< Check if ID indicates 3390kbits/s          */
#define RFAL_ANALOG_CONFIG_ID_IS_6780(id)           (RFAL_ANALOG_CONFIG_BITRATE_6780 & (id))   /*!< Check if ID indicates 6780kbits/s          */
#define RFAL_ANALOG_CONFIG_ID_IS_26(id)             (RFAL_ANALOG_CONFIG_BITRATE_26   & (id))   /*!< Check if ID indicates 1 out of 4 bitrate   */
#define RFAL_ANALOG_CONFIG_ID_IS_1p6(id)            (RFAL_ANALOG_CONFIG_BITRATE_1p6  & (id))   /*!< Check if ID indicates 1 out of 256 bitrate */

#define RFAL_ANALOG_CONFIG_ID_GET_DIRECTION(id)     (RFAL_ANALOG_CONFIG_DIRECTION_MASK & (id)) /*!< Get Direction of Configuration ID          */
#define RFAL_ANALOG_CONFIG_ID_IS_TX(id)             (RFAL_ANALOG_CONFIG_TX & (id))             /*!< Check if id indicates TX                   */
#define RFAL_ANALOG_CONFIG_ID_IS_RX(id)             (RFAL_ANALOG_CONFIG_RX & (id))             /*!< Check if id indicates RX                   */

#define RFAL_ANALOG_CONFIG_CONFIG_NUM(x)            (sizeof(x)/sizeof((x)[0]))                 /*!< Get Analog Config number                   */

/*! Set Analog Config ID value by: Mode, Technology, Bitrate and Direction      */
#define RFAL_ANALOG_CONFIG_ID_SET(mode, tech, br, direction)    \
    (  RFAL_ANALOG_CONFIG_ID_GET_POLL_LISTEN(mode) \
     | RFAL_ANALOG_CONFIG_ID_GET_TECH(tech) \
     | RFAL_ANALOG_CONFIG_ID_GET_BITRATE(br) \
     | RFAL_ANALOG_CONFIG_ID_GET_DIRECTION(direction) \
    )

/*
 ******************************************************************************
 * GLOBAL DATA TYPES
 ******************************************************************************
 */

typedef uint8_t  rfalAnalogConfigMode;       /*!< Polling or Listening Mode of Configuration                    */
typedef uint8_t  rfalAnalogConfigTech;       /*!< Technology of Configuration                                   */
typedef uint8_t  rfalAnalogConfigBitrate;    /*!< Bitrate of Configuration                                      */
typedef uint8_t  rfalAnalogConfigDirection;  /*!< Transmit/Receive direction of Configuration                   */

typedef uint8_t  rfalAnalogConfigRegAddr[2]; /*!< Register Address to ST Chip                                   */
typedef uint8_t  rfalAnalogConfigRegMask;    /*!< Register Mask Value                                           */
typedef uint8_t  rfalAnalogConfigRegVal;     /*!< Register Value                                                */

typedef uint16_t rfalAnalogConfigId;         /*!< Analog Configuration ID                                       */
typedef uint16_t rfalAnalogConfigOffset;     /*!< Analog Configuration offset address in the table              */
typedef uint8_t  rfalAnalogConfigNum;        /*!< Number of Analog settings for the respective Configuration ID */


/*! Struct that contain the Register-Mask-Value set. Make sure that the whole structure size is even and unaligned! */
typedef struct {
    rfalAnalogConfigRegAddr addr;  /*!< Register Address    */
    rfalAnalogConfigRegMask mask;  /*!< Register Mask Value */
    rfalAnalogConfigRegVal  val;   /*!< Register Value      */
} rfalAnalogConfigRegAddrMaskVal;


/*! Struct that represents the Analog Configs */
typedef struct {
    uint8_t                        id[sizeof(rfalAnalogConfigId)]; /*!< Configuration ID                   */
    rfalAnalogConfigNum            num;                            /*!< Number of Config Sets to follow    */
    rfalAnalogConfigRegAddrMaskVal regSet[];                       /*!< Register-Mask-Value sets           */ /*  PRQA S 1060 # MISRA 18.7 - Flexible Array Members are the only meaningful way of denoting a variable length input buffer which follows a fixed header structure. */
} rfalAnalogConfig;


/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/

/*!
 *****************************************************************************
 * \brief Initialize the Analog Configuration
 * 
 * Reset the Analog Configuration LUT pointer to reference to default settings.
 * 
 *****************************************************************************
 */
void rfalAnalogConfigInitialize( void );


/*!
 *****************************************************************************
 * \brief Indicate if the current Analog Configuration Table is complete and ready to be used.
 * 
 * \return true if current Analog Configuration Table is complete and ready to be used.
 * \return false if current Analog Configuration Table is incomplete
 * 
 *****************************************************************************
 */
bool rfalAnalogConfigIsReady( void );


/*!
 *****************************************************************************
 * \brief  Write the whole Analog Configuration table in raw format 
 *  
 * Writes the Analog Configuration and Look Up Table with the given raw table
 * 
 * NOTE: Function does not check the validity of the given Table contents
 * 
 * \param[in]  configTbl     : location of config Table to be loaded
 * \param[in]  configTblSize : size of the config Table to be loaded
 * 
 * \return RFAL_ERR_NONE    : if setting is updated
 * \return RFAL_ERR_PARAM   : if configTbl is invalid
 * \return RFAL_ERR_NOMEM   : if the given Table is bigger exceeds the max size
 * \return RFAL_ERR_REQUEST : if the update Configuration Id is disabled
 *
 *****************************************************************************
 */
ReturnCode rfalAnalogConfigListWriteRaw( const uint8_t *configTbl, uint16_t configTblSize );


/*!
 *****************************************************************************
 * \brief  Write the Analog Configuration table with new analog settings.
 *  
 * Writes the Analog Configuration and Look Up Table with the new list of register-mask-value 
 * and Configuration ID respectively.
 * 
 * NOTE: Function does not check for the validity of the Register Address.
 * 
 * \param[in]  more    : 0x00 indicates it is last Configuration ID settings; 
 *                       0x01 indicates more Configuration ID setting(s) are coming.
 * \param[in]  *config : reference to the configuration list of current Configuraiton ID.
 *                          
 * \return RFAL_ERR_PARAM   : if Configuration ID or parameter is invalid
 * \return RFAL_ERR_NOMEM   : if LUT is full      
 * \return RFAL_ERR_REQUEST : if the update Configuration Id is disabled               
 * \return RFAL_ERR_NONE    : if setting is updated
 *
 *****************************************************************************
 */
ReturnCode rfalAnalogConfigListWrite( uint8_t more, const rfalAnalogConfig *config );


/*!
 *****************************************************************************
 * \brief  Read the whole Analog Configuration table in raw format
 *  
 * Reads the whole Analog Configuration Table in raw format
 * 
 * \param[out]   tblBuf        : location to the buffer to place the Config Table 
 * \param[in]    tblBufLen     : length of the buffer to place the Config Table
 * \param[out]   configTblSize : Config Table size 
 *                          
 * \return RFAL_ERR_PARAM : if configTbl or configTblSize is invalid
 * \return RFAL_ERR_NOMEM : if configTblSize is not enough for the whole table           
 * \return RFAL_ERR_NONE  : if read is successful
 * 
 *****************************************************************************
 */
ReturnCode rfalAnalogConfigListReadRaw( uint8_t *tblBuf, uint16_t tblBufLen, uint16_t *configTblSize );


/*!
 *****************************************************************************
 * \brief  Read the Analog Configuration table.
 *  
 * Read the Analog Configuration Table
 * 
 * \param[in]  configOffset : offset to the next Configuration ID in the List Table to be read.   
 * \param[out] more         : 0x00 indicates it is last Configuration ID settings; 
 *                            0x01 indicates more Configuration ID setting(s) are coming.
 * \param[out] config       : configuration id, number of configuration sets and register-mask-value sets
 * \param[in]  numConfig    : the remaining configuration settings space available;
 *                          
 * \return RFAL_ERR_NOMEM : if number of Configuration for respective Configuration ID is greater the the remaining configuration setting space available                
 * \return RFAL_ERR_NONE  : if read is successful
 * 
 *****************************************************************************
 */
ReturnCode rfalAnalogConfigListRead( rfalAnalogConfigOffset *configOffset, uint8_t *more, rfalAnalogConfig *config, rfalAnalogConfigNum numConfig );


/*!
 *****************************************************************************
 * \brief  Set the Analog settings of indicated Configuration ID.
 *  
 * Update the chip with indicated analog settings of indicated Configuration ID.
 *
 * \param[in]  configId : configuration ID
 *                            
 * \return RFAL_ERR_PARAM    : if Configuration ID is invalid
 * \return RFAL_ERR_INTERNAL : if error updating setting to chip                   
 * \return RFAL_ERR_NONE     : if new settings is applied to chip
 *
 *****************************************************************************
 */
ReturnCode rfalSetAnalogConfig( rfalAnalogConfigId configId );


/*!
 *****************************************************************************
 * \brief  Generates Analog Config mode ID 
 *
 * Converts RFAL mode and bitrate into Analog Config Mode ID.
 *  
 * Update the chip with indicated analog settings of indicated Configuration ID.
 *
 * \param[in]  md  :  RFAL mode format
 * \param[in]  br  :  RFAL bit rate format
 * \param[in]  dir : Analog Config communication direction
 *                            
 * \return  Analog Config Mode ID
 *
 *****************************************************************************
 */
uint16_t rfalAnalogConfigGenModeID( rfalMode md, rfalBitRate br, uint16_t dir );


#endif /* RFAL_ANALOG_CONFIG_H */

/**
  * @}
  *
  * @}
  *
  * @}
  */
