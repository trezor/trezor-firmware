
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2016 STMicroelectronics, all rights reserved
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

/*! \file rfal_nfc.h
 *
 *  \brief RFAL NFC device
 *  
 *  This module provides the required features to behave as an NFC Poller 
 *  or Listener device. It grants an easy to use interface for the following
 *  activities: Technology Detection, Collision Resolution, Activation,
 *  Data Exchange, and Deactivation
 *  
 *  This layer is influenced by (but not fully aligned with) the NFC Forum 
 *  specifications, in particular: Activity 2.0 and NCI 2.0
 *
 *  
 *    
 * \addtogroup RFAL
 * @{
 * 
 * \addtogroup RFAL-HL
 * \brief RFAL Higher Layer
 * @{
 * 
 * \addtogroup NFC
 * \brief RFAL NFC Device
 * @{
 *  
 */

#ifndef RFAL_NFC_H
#define RFAL_NFC_H

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include "rfal_platform.h"
#include "rfal_utils.h"
#include "rfal_rf.h"
#include "rfal_nfca.h"
#include "rfal_nfcb.h"
#include "rfal_nfcf.h"
#include "rfal_nfcv.h"
#include "rfal_st25tb.h"
#include "rfal_nfcDep.h"
#include "rfal_isoDep.h"


/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/

#define RFAL_NFC_TECH_NONE               0x0000U  /*!< No technology                     */
#define RFAL_NFC_POLL_TECH_A             0x0001U  /*!< Poll NFC-A technology Flag        */
#define RFAL_NFC_POLL_TECH_B             0x0002U  /*!< Poll NFC-B technology Flag        */
#define RFAL_NFC_POLL_TECH_F             0x0004U  /*!< Poll NFC-F technology Flag        */
#define RFAL_NFC_POLL_TECH_V             0x0008U  /*!< Poll NFC-V technology Flag        */
#define RFAL_NFC_POLL_TECH_AP2P          0x0010U  /*!< Poll AP2P technology Flag         */
#define RFAL_NFC_POLL_TECH_ST25TB        0x0020U  /*!< Poll ST25TB technology Flag       */
#define RFAL_NFC_POLL_TECH_PROP          0x0040U  /*!< Poll Proprietary technology Flag  */
#define RFAL_NFC_LISTEN_TECH_A           0x1000U  /*!< Listen NFC-A technology Flag      */
#define RFAL_NFC_LISTEN_TECH_B           0x2000U  /*!< Listen NFC-B technology Flag      */
#define RFAL_NFC_LISTEN_TECH_F           0x4000U  /*!< Listen NFC-F technology Flag      */
#define RFAL_NFC_LISTEN_TECH_AP2P        0x8000U  /*!< Listen AP2P technology Flag       */


/*
******************************************************************************
* GLOBAL MACROS
******************************************************************************
*/

/*! Checks if a device is currently activated */
#define rfalNfcIsDevActivated( st )        ( ((st)>= RFAL_NFC_STATE_ACTIVATED) && ((st)<RFAL_NFC_STATE_DEACTIVATION) )

/*! Checks if a device is in discovery */
#define rfalNfcIsInDiscovery( st )         ( ((st)>= RFAL_NFC_STATE_START_DISCOVERY) && ((st)<RFAL_NFC_STATE_ACTIVATED) )

/*! Checks if remote device is in Poll mode */
#define rfalNfcIsRemDevPoller( tp )    ( ((tp)>= RFAL_NFC_POLL_TYPE_NFCA) && ((tp)<=RFAL_NFC_POLL_TYPE_AP2P ) )

/*! Checks if remote device is in Listen mode */
#define rfalNfcIsRemDevListener( tp )  ( ((int16_t)(tp)>= (int16_t)RFAL_NFC_LISTEN_TYPE_NFCA) && ((tp)<=RFAL_NFC_LISTEN_TYPE_AP2P) )

/*! Sets the discover parameters to its default values */
#define rfalNfcDefaultDiscParams( dp )  if( (dp) != NULL) {                                        \
                                        RFAL_MEMSET( (dp), 0x00, sizeof(rfalNfcDiscoverParam) );   \
                                        ((dp))->compMode               = RFAL_COMPLIANCE_MODE_NFC; \
                                        ((dp))->devLimit               = 1U;                       \
                                        ((dp))->nfcfBR                 = RFAL_BR_212;              \
                                        ((dp))->ap2pBR                 = RFAL_BR_424;              \
                                        ((dp))->maxBR                  = RFAL_BR_KEEP;             \
                                        ((dp))->isoDepFS               = RFAL_ISODEP_FSXI_256;     \
                                        ((dp))->nfcDepLR               = RFAL_NFCDEP_LR_254;       \
                                        ((dp))->GBLen                  = 0U;                       \
                                        ((dp))->p2pNfcaPrio            = false;                    \
                                        ((dp))->wakeupEnabled          = false;                    \
                                        ((dp))->wakeupConfigDefault    = true;                     \
                                        ((dp))->wakeupPollBefore       = false;                    \
                                        ((dp))->wakeupNPolls           = 1U;                       \
                                        ((dp))->totalDuration          = 1000U;                    \
                                        ((dp))->techs2Find             = RFAL_NFC_TECH_NONE;       \
                                        ((dp))->techs2Bail             = RFAL_NFC_TECH_NONE;       \
                                        }

/*
******************************************************************************
* GLOBAL ENUMS
******************************************************************************
*/

/*
******************************************************************************
* GLOBAL TYPES
******************************************************************************
*/

/*! Main state                                                                       */
typedef enum{
    RFAL_NFC_STATE_NOTINIT                  =  0,   /*!< Not Initialized state       */
    RFAL_NFC_STATE_IDLE                     =  1,   /*!< Initialize state            */
    RFAL_NFC_STATE_START_DISCOVERY          =  2,   /*!< Start Discovery loop state  */
    RFAL_NFC_STATE_WAKEUP_MODE              =  3,   /*!< Wake-Up state               */
    RFAL_NFC_STATE_POLL_TECHDETECT          =  10,  /*!< Technology Detection state  */
    RFAL_NFC_STATE_POLL_COLAVOIDANCE        =  11,  /*!< Collision Avoidance state   */
    RFAL_NFC_STATE_POLL_SELECT              =  12,  /*!< Wait for Selection state    */
    RFAL_NFC_STATE_POLL_ACTIVATION          =  13,  /*!< Activation state            */
    RFAL_NFC_STATE_LISTEN_TECHDETECT        =  20,  /*!< Listen Tech Detect          */
    RFAL_NFC_STATE_LISTEN_COLAVOIDANCE      =  21,  /*!< Listen Collision Avoidance  */
    RFAL_NFC_STATE_LISTEN_ACTIVATION        =  22,  /*!< Listen Activation state     */
    RFAL_NFC_STATE_LISTEN_SLEEP             =  23,  /*!< Listen Sleep state          */
    RFAL_NFC_STATE_ACTIVATED                =  30,  /*!< Activated state             */
    RFAL_NFC_STATE_DATAEXCHANGE             =  31,  /*!< Data Exchange Start state   */
    RFAL_NFC_STATE_DATAEXCHANGE_DONE        =  33,  /*!< Data Exchange terminated    */
    RFAL_NFC_STATE_DEACTIVATION             =  34   /*!< Deactivation state          */
}rfalNfcState;


/*! Device type                                                                       */
typedef enum{
    RFAL_NFC_LISTEN_TYPE_NFCA               =  0,   /*!< NFC-A Listener device type  */
    RFAL_NFC_LISTEN_TYPE_NFCB               =  1,   /*!< NFC-B Listener device type  */
    RFAL_NFC_LISTEN_TYPE_NFCF               =  2,   /*!< NFC-F Listener device type  */
    RFAL_NFC_LISTEN_TYPE_NFCV               =  3,   /*!< NFC-V Listener device type  */
    RFAL_NFC_LISTEN_TYPE_ST25TB             =  4,   /*!< ST25TB Listener device type */
    RFAL_NFC_LISTEN_TYPE_AP2P               =  5,   /*!< AP2P Listener device type   */
    RFAL_NFC_LISTEN_TYPE_PROP               =  6,   /*!< Proprietary Listen dev type */
    RFAL_NFC_POLL_TYPE_NFCA                 =  10,  /*!< NFC-A Poller device type    */
    RFAL_NFC_POLL_TYPE_NFCB                 =  11,  /*!< NFC-B Poller device type    */
    RFAL_NFC_POLL_TYPE_NFCF                 =  12,  /*!< NFC-F Poller device type    */
    RFAL_NFC_POLL_TYPE_NFCV                 =  13,  /*!< NFC-V Poller device type    */
    RFAL_NFC_POLL_TYPE_AP2P                 =  15   /*!< AP2P Poller device type     */
}rfalNfcDevType;


/*! Device interface                                                                 */
typedef enum{
    RFAL_NFC_INTERFACE_RF                   = 0,    /*!< RF Frame interface          */
    RFAL_NFC_INTERFACE_ISODEP               = 1,    /*!< ISO-DEP interface           */
    RFAL_NFC_INTERFACE_NFCDEP               = 2     /*!< NFC-DEP interface           */
}rfalNfcRfInterface;


/*! Deactivation type                                                                     */
typedef enum{
    RFAL_NFC_DEACTIVATE_IDLE                = 0,    /*!< Deactivate and go to IDLE        */
    RFAL_NFC_DEACTIVATE_SLEEP               = 1,    /*!< Deactivate and go to SELECT      */
    RFAL_NFC_DEACTIVATE_DISCOVERY           = 2     /*!< Deactivate and restart DISCOVERY */
}rfalNfcDeactivateType;


/*! Device struct containing all its details                                          */
typedef struct{
    rfalNfcDevType type;                            /*!< Device's type                */
    union{                              /*  PRQA S 0750 # MISRA 19.2 - Members of the union will not be used concurrently, only one technology at a time */
        rfalNfcaListenDevice   nfca;                /*!< NFC-A Listen Device instance */
        rfalNfcbListenDevice   nfcb;                /*!< NFC-B Listen Device instance */
        rfalNfcfListenDevice   nfcf;                /*!< NFC-F Listen Device instance */
        rfalNfcvListenDevice   nfcv;                /*!< NFC-V Listen Device instance */
        rfalSt25tbListenDevice st25tb;              /*!< ST25TB Listen Device instance*/
    }dev;                                           /*!< Device's instance            */
                                                    
    uint8_t                    *nfcid;              /*!< Device's NFCID               */
    uint8_t                    nfcidLen;            /*!< Device's NFCID length        */
    rfalNfcRfInterface         rfInterface;         /*!< Device's interface           */
    
    union{                              /*  PRQA S 0750 # MISRA 19.2 - Members of the union will not be used concurrently, only one protocol at a time */            
        rfalIsoDepDevice       isoDep;              /*!< ISO-DEP instance             */
        rfalNfcDepDevice       nfcDep;              /*!< NFC-DEP instance             */
    }proto;                                         /*!< Device's protocol            */
}rfalNfcDevice;


/*! Callbacks for Proprietary|Other Technology      Activity 2.1   &   EMVCo 3.0  9.2 */
typedef ReturnCode (* rfalNfcPropCallback)(void);


/*! Struct that holds the Proprietary NFC callbacks                                                                                  */
typedef struct{
    rfalNfcPropCallback    rfalNfcpPollerInitialize;                    /*!< Prorietary NFC Initialization callback                  */
    rfalNfcPropCallback    rfalNfcpPollerTechnologyDetection;           /*!< Prorietary NFC Technoly Detection callback              */
    rfalNfcPropCallback    rfalNfcpPollerStartCollisionResolution;      /*!< Prorietary NFC Start Collision Resolution callback      */
    rfalNfcPropCallback    rfalNfcpPollerGetCollisionResolutionStatus;  /*!< Prorietary NFC Get Collision Resolution status callback */
    rfalNfcPropCallback    rfalNfcpStartActivation;                     /*!< Prorietary NFC Start Activation callback                */
    rfalNfcPropCallback    rfalNfcpGetActivationStatus;                 /*!< Prorietary NFC Get Activation status callback           */
} rfalNfcPropCallbacks;


/*! Discovery parameters                                                                                                             */
typedef struct{                                                                                             
    rfalComplianceMode     compMode;                         /*!< Compliancy mode to be used                                         */
    uint16_t               techs2Find;                       /*!< Technologies to search for                                         */
    uint16_t               techs2Bail;                       /*!< Bail-out after certain NFC technologies                            */
    uint16_t               totalDuration;                    /*!< Duration of a whole Poll + Listen cycle        NCI 2.1 Table 46    */
    uint8_t                devLimit;                         /*!< Max number of devices                      Activity 2.1  Table 11  */
    rfalBitRate            maxBR;                            /*!< Max Bit rate to be used                        NCI 2.1  Table 28   */
                                                                                                                   
    rfalBitRate            nfcfBR;                           /*!< Bit rate to poll for NFC-F                     NCI 2.1  Table 27   */
    uint8_t                nfcid3[RFAL_NFCDEP_NFCID3_LEN];   /*!< NFCID3 to be used on the ATR_REQ/ATR_RES                           */
    uint8_t                GB[RFAL_NFCDEP_GB_MAX_LEN];       /*!< General bytes to be used on the ATR-REQ        NCI 2.1  Table 29   */
    uint8_t                GBLen;                            /*!< Length of the General Bytes                    NCI 2.1  Table 29   */
    rfalBitRate            ap2pBR;                           /*!< Bit rate to poll for AP2P                      NCI 2.1  Table 31   */
    bool                   p2pNfcaPrio;                      /*!< NFC-A P2P (true) or ISO14443-4/T4T (false) priority                */
    rfalNfcPropCallbacks   propNfc;                          /*!< Proprietary Technlogy callbacks                                    */
                                                                                                                                    
                                                                                                                                    
    rfalIsoDepFSxI         isoDepFS;                         /*!< ISO-DEP Poller announced maximum frame size   Digital 2.2 Table 60 */
    uint8_t                nfcDepLR;                         /*!< NFC-DEP Poller & Listener maximum frame size  Digital 2.2 Table 90 */
                                                                                                                                    
    rfalLmConfPA           lmConfigPA;                       /*!< Configuration for Passive Listen mode NFC-A                        */
    rfalLmConfPF           lmConfigPF;                       /*!< Configuration for Passive Listen mode NFC-A                        */
                                                                                                                                     
    void                   (*notifyCb)( rfalNfcState st );   /*!< Callback to Notify upper layer                                     */
                                                                                                                                     
    bool                   wakeupEnabled;                    /*!< Enable Wake-Up mode before polling                                 */
    bool                   wakeupConfigDefault;              /*!< Wake-Up mode default configuration                                 */
    rfalWakeUpConfig       wakeupConfig;                     /*!< Wake-Up mode configuration                                         */
    bool                   wakeupPollBefore;                 /*!< Flag to Poll wakeupNPolls times before entering Wake-up            */
    uint16_t               wakeupNPolls;                     /*!< Number of polling cycles before|after entering Wake-up             */
}rfalNfcDiscoverParam;


/*! Buffer union, only one interface is used at a time                                                             */
typedef union{  /*  PRQA S 0750 # MISRA 19.2 - Members of the union will not be used concurrently, only one interface at a time */
    uint8_t                  rfBuf[RFAL_FEATURE_NFC_RF_BUF_LEN]; /*!< RF buffer                                    */
    rfalIsoDepApduBufFormat  isoDepBuf;                          /*!< ISO-DEP buffer format (with header/prologue) */
    rfalNfcDepPduBufFormat   nfcDepBuf;                          /*!< NFC-DEP buffer format (with header/prologue) */
}rfalNfcBuffer;

/*******************************************************************************/

/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/

/*! 
 *****************************************************************************
 * \brief  RFAL NFC Worker
 *  
 * It runs the internal state machine and runs the RFAL RF worker.
 *****************************************************************************
 */
void rfalNfcWorker( void );


/*! 
 *****************************************************************************
 * \brief  RFAL NFC Initialize
 *  
 * It initializes this module and its dependencies
 *
 * \return RFAL_ERR_WRONG_STATE  : Incorrect state for this operation
 * \return RFAL_ERR_IO           : Generic internal error
 * \return RFAL_ERR_NONE         : No error
 *****************************************************************************
 */
ReturnCode rfalNfcInitialize( void );


/*!
 *****************************************************************************
 * \brief  RFAL NFC Discovery
 *  
 * It set the device in Discovery state.
 * In discovery it will Poll and/or Listen for the technologies configured, 
 * and perform Wake-up mode if configured to do so.
 *
 * The device list passed on disParams must not be empty.
 * The number of devices on the list is indicated by the devLimit and shall
 * be at >= 1.
 *
 * \param[in]  disParams         : discovery configuration parameters
 *
 * \return RFAL_ERR_WRONG_STATE  : Incorrect state for this operation
 * \return RFAL_ERR_PARAM        : Invalid parameters
 * \return RFAL_ERR_NONE         : No error
 *****************************************************************************
 */
ReturnCode rfalNfcDiscover( const rfalNfcDiscoverParam *disParams );


/*!
 *****************************************************************************
 * \brief  RFAL NFC Get State
 *  
 * It returns the current state
 *
 * \return rfalNfcState : the current state
 *****************************************************************************
 */
rfalNfcState rfalNfcGetState( void );


/*!
 *****************************************************************************
 * \brief  RFAL NFC Get Devices Found
 *  
 * It returns the location of the device list and the number of 
 * devices found.
 *
 * \param[out]  devList          : device list location
 * \param[out]  devCnt           : number of devices found
 *
 * \return RFAL_ERR_WRONG_STATE  : Incorrect state for this operation
 *                                 Discovery still ongoing
 * \return RFAL_ERR_PARAM        : Invalid parameters
 * \return RFAL_ERR_NONE         : No error
 *****************************************************************************
 */
ReturnCode rfalNfcGetDevicesFound( rfalNfcDevice **devList, uint8_t *devCnt );


/*!
 *****************************************************************************
 * \brief  RFAL NFC Get Active Device
 *  
 * It returns the location of the device current Active device
 *
 * \param[out]  dev                : device info location
 *
 * \return RFAL_ERR_WRONG_STATE    : Incorrect state for this operation
 *                                   No device activated
 * \return RFAL_ERR_PARAM          : Invalid parameters
 * \return RFAL_ERR_NONE           : No error
 *****************************************************************************
 */
ReturnCode rfalNfcGetActiveDevice( rfalNfcDevice **dev );


/*!
 *****************************************************************************
 * \brief  RFAL NFC Select Device
 *  
 * It selects the device to be activated.
 * It shall be called when more than one device has been identified to 
 * indicate which device shall be actived
 * 
 * \param[in]  devIdx            : device index to be activated
 *
 * \return RFAL_ERR_WRONG_STATE  : Incorrect state for this operation
 *                                 Not in select state
 * \return RFAL_ERR_PARAM        : Invalid parameters
 * \return RFAL_ERR_NONE         : No error
 *****************************************************************************
 */
ReturnCode rfalNfcSelect( uint8_t devIdx );


/*!
 *****************************************************************************
 * \brief  RFAL NFC Start Data Exchange
 *  
 * After a device has been activated, it starts a data exchange.
 * It handles automatically which interface/protocol to be used and acts accordingly.
 *
 * In Listen mode the first frame/data shall be sent by the Reader/Initiator
 * therefore this method must be called first with txDataLen set to zero 
 * to retrieve the rxData and rcvLen locations.
 *
 *
 * \param[in]  txData       : data to be transmitted
 * \param[in]  txDataLen    : size of the data to be transmitted (in bits or bytes - see below)
 * \param[out] rxData       : location of the received data after operation is completed
 * \param[out] rvdLen       : location of the length of the received data (in bits or bytes - see below)
 * \param[in]  fwt          : FWT to be used in case of RF interface.
 *                            If ISO-DEP or NFC-DEP interface is used, this will be ignored
 *
 * \warning In order to support a wider range of protocols, when RF interface is used the lengths 
 *          are in number of bits (not bytes). Therefore both input txDataLen and output rvdLen refer to 
 *          bits. If ISO-DEP or NFC-DEP interface is used those are expressed in number of bytes.
 *
 *
 * \return RFAL_ERR_WRONG_STATE  : Incorrect state for this operation
 * \return RFAL_ERR_PARAM        : Invalid parameters
 * \return RFAL_ERR_NONE         : No error
 *****************************************************************************
 */
ReturnCode rfalNfcDataExchangeStart( uint8_t *txData, uint16_t txDataLen, uint8_t **rxData, uint16_t **rvdLen, uint32_t fwt );


/*! 
 *****************************************************************************
 * \brief  RFAL NFC Get Data Exchange Status
 *  
 * Gets current Data Exchange status
 *
 * \return  RFAL_ERR_NONE         : Transceive done with no error
 * \return  RFAL_ERR_BUSY         : Transceive ongoing
 *  \return RFAL_ERR_AGAIN        : received one chaining block, copy received data 
 *                                  and continue to call this method to retrieve the 
 *                                  remaining blocks
 * \return  RFAL_ERR_XXXX         : Error occurred
 * \return  RFAL_ERR_TIMEOUT      : No response
 * \return  RFAL_ERR_FRAMING      : Framing error detected
 * \return  RFAL_ERR_PAR          : Parity error detected
 * \return  RFAL_ERR_CRC          : CRC error detected
 * \return  RFAL_ERR_LINK_LOSS    : Link Loss - External Field is Off
 * \return  RFAL_ERR_RF_COLLISION : Collision detected
 * \return  RFAL_ERR_IO           : Internal error
 *****************************************************************************
 */
ReturnCode rfalNfcDataExchangeGetStatus( void );


/*! 
 *****************************************************************************
 * \brief  RFAL NFC Deactivate
 *  
 * It triggers the deactivation procedure to terminate communications with 
 * remote device. 
 * In case the deactivation type is RFAL_NFC_DEACTIVATE_SLEEP the field is
 * kept On and device selection shall follow. Otherwise the field will 
 * be turned Off.
 *
 * \warning In case the deactivation type is RFAL_NFC_DEACTIVATE_IDLE the 
 *  deactivation procedure is executed immediately and in a blocking manner
 *
 * \param[in]  deactType         : Type of deactivation to be performed
 *
 * \return RFAL_ERR_WRONG_STATE  : Incorrect state for this operation
 * \return RFAL_ERR_NONE         : No error
 *****************************************************************************
 */
ReturnCode rfalNfcDeactivate( rfalNfcDeactivateType deactType );

#endif /* RFAL_NFC_H */


/**
  * @}
  *
  * @}
  *
  * @}
  */
