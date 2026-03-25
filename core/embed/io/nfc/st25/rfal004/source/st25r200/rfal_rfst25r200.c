
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

/*! \file
 *
 *  \author Gustavo Patricio 
 *
 *  \brief RF Abstraction Layer (RFAL)
 *  
 *  RFAL implementation for ST25R200
 */


/*
******************************************************************************
* INCLUDES
******************************************************************************
*/

#include "rfal_chip.h"
#include "rfal_utils.h"
#include "st25r200.h"
#include "st25r200_com.h"
#include "st25r200_irq.h"
#include "rfal_analogConfig.h"


/*
 ******************************************************************************
 * ENABLE SWITCHS
 ******************************************************************************
 */

/* Specific features may be enabled or disabled by user at rfal_platform.h 
 * Default configuration (ST25R dependant) also provided at rfal_defConfig.h
 *  
 *    RFAL_FEATURE_LISTEN_MODE
 *    RFAL_FEATURE_WAKEUP_MODE
 *    RFAL_FEATURE_LOWPOWER_MODE
 */


/*
******************************************************************************
* GLOBAL TYPES
******************************************************************************
*/

/*! Struct that holds all involved on a Transceive including the context passed by the caller     */
typedef struct{
    rfalTransceiveState     state;       /*!< Current transceive state                            */
    rfalTransceiveState     lastState;   /*!< Last transceive state (debug purposes)              */
    ReturnCode              status;      /*!< Current status/error of the transceive              */
    
    rfalTransceiveContext   ctx;         /*!< The transceive context given by the caller          */
    
} rfalTxRx;


/*! Struct that holds certain WU mode information to be retrieved by rfalWakeUpModeGetInfo        */
typedef struct{                                                                                   
    bool                     irqWut;     /*!< Wake-Up Timer IRQ received                          */
    bool                     irqWui;     /*!< WU I channel IRQ received                           */
    bool                     irqWuq;     /*!< WU Q channel IRQ received                           */
    uint8_t                  status;     /*!< Wake-Up Status                                      */
}rfalWakeUpData;


/*! Struct that holds all context for the Wake-Up Mode                                            */
typedef struct{
    rfalWumState            state;       /*!< Current Wake-Up Mode state                          */
    rfalWakeUpConfig        cfg;         /*!< Current Wake-Up Mode context                        */
    rfalWakeUpData          info;        /*!< Current Wake-Up Mode information                    */
} rfalWum;


/*! Struct that holds all context for the Low Power Mode                                          */
typedef struct{
    bool                    isRunning;
    rfalLpMode              mode;
} rfalLpm;


/*! Struct that holds the timings GT and FDTs                           */
typedef struct{
    uint32_t                GT;          /*!< GT in 1/fc                */
    uint32_t                FDTListen;   /*!< FDTListen in 1/fc         */
    uint32_t                FDTPoll;     /*!< FDTPoll in 1/fc           */
} rfalTimings;


/*! Struct that holds the software timers                               */
typedef struct{
    uint32_t                GT;          /*!< RFAL's GT timer           */
    uint32_t                RXE;         /*!< Timer between RXS and RXE */
} rfalTimers;


/*! Struct that holds the RFAL's callbacks                              */
typedef struct{
    rfalPreTxRxCallback     preTxRx;     /*!< RFAL's Pre TxRx callback  */
    rfalPostTxRxCallback    postTxRx;    /*!< RFAL's Post TxRx callback */
    rfalSyncTxRxCallback    syncTxRx;    /*!< RFAL's Sync TxRx callback */
} rfalCallbacks;


/*! Struct that holds counters to control the FIFO on Tx and Rx                                                                          */
typedef struct{    
    uint16_t                expWL;       /*!< The amount of bytes expected to be Tx when a WL interrupt occours                          */
    uint16_t                bytesTotal;  /*!< Total bytes to be transmitted OR the total bytes received                                  */
    uint16_t                bytesWritten;/*!< Amount of bytes already written on FIFO (Tx) OR read (RX) from FIFO and written on rxBuffer*/
    uint8_t                 status[ST25R200_FIFO_STATUS_LEN];   /*!< FIFO Status Registers                                              */
} rfalFIFO;


/*! Struct that holds RFAL's configuration settings                                                     */
typedef struct{    
    uint16_t                obsvModeTx;  /*!< RFAL's config of the ST25R200's observation mode while Tx */
    uint16_t                obsvModeRx;  /*!< RFAL's config of the ST25R200's observation mode while Rx */
    uint8_t                 obsvModeCfg[ST25R200_OBS_MODE_LEN]; /*!< RFAL's ST25R200's obs mode aux     */
    rfalEHandling           eHandling;   /*!< RFAL's error handling config/mode                         */
} rfalConfigs;


/*! Struct that holds NFC-A data - Used only inside rfalISO14443ATransceiveAnticollisionFrame()         */
typedef struct{
    uint8_t                 collByte;    /*!< NFC-A Anticollision collision byte                        */
    uint8_t                 *buf;        /*!< NFC-A Anticollision frame buffer                          */
    uint8_t                 *bytesToSend;/*!< NFC-A Anticollision NFCID|UID byte context                */
    uint8_t                 *bitsToSend; /*!< NFC-A Anticollision NFCID|UID bit context                 */
    uint16_t                *rxLength;   /*!< NFC-A Anticollision received length                       */
} rfalNfcaWorkingData;


/*! RFAL instance                                                                                       */
typedef struct{
    rfalState               state;       /*!< RFAL's current state                                      */
    rfalMode                mode;        /*!< RFAL's current mode                                       */
    rfalBitRate             txBR;        /*!< RFAL's current Tx Bit Rate                                */
    rfalBitRate             rxBR;        /*!< RFAL's current Rx Bit Rate                                */
    bool                    field;       /*!< Current field state (On / Off)                            */
                                                                                                        
    rfalConfigs             conf;        /*!< RFAL's configuration settings                             */
    rfalTimings             timings;     /*!< RFAL's timing setting                                     */
    rfalTxRx                TxRx;        /*!< RFAL's transceive management                              */
    rfalFIFO                fifo;        /*!< RFAL's FIFO management                                    */
    rfalTimers              tmr;         /*!< RFAL's Software timers                                    */
    rfalCallbacks           callbacks;   /*!< RFAL's callbacks                                          */
                                                                                                        
                                                                                                        
#if RFAL_FEATURE_WAKEUP_MODE
    rfalWum                 wum;         /*!< RFAL's Wake-up mode management                            */
#endif /* RFAL_FEATURE_WAKEUP_MODE */
                                                                                                        
#if RFAL_FEATURE_LOWPOWER_MODE
    rfalLpm                 lpm;         /*!< RFAL's Low power mode management                          */
#endif /* RFAL_FEATURE_LOWPOWER_MODE */

#if RFAL_FEATURE_NFCA
    rfalNfcaWorkingData     nfcaData;    /*!< RFAL's working data when supporting NFC-A                 */
#endif /* RFAL_FEATURE_NFCA */

} rfal;


/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/

#define RFAL_FIFO_IN_WL                 128U                                          /*!< Number of bytes in the FIFO when WL interrupt occurs while Tx                   */
#define RFAL_FIFO_OUT_WL                (ST25R200_FIFO_DEPTH - RFAL_FIFO_IN_WL)       /*!< Number of bytes sent/out of the FIFO when WL interrupt occurs while Tx          */

#define RFAL_FIFO_STATUS_REG1           0U                                            /*!< Location of FIFO status register 1 in local copy                                */
#define RFAL_FIFO_STATUS_REG2           1U                                            /*!< Location of FIFO status register 2 in local copy                                */
#define RFAL_FIFO_STATUS_INVALID        0xFFU                                         /*!< Value indicating that the local FIFO status in invalid|cleared                  */

#define RFAL_ST25R200_GPT_MAX_1FC      rfalConv8fcTo1fc(  0xFFFFU )                   /*!< Max GPT steps in 1fc (0xFFFF steps of 8/fc    => 0xFFFF * 590ns  = 38,7ms)      */
#define RFAL_ST25R200_NRT_MAX_1FC      rfalConv4096fcTo1fc( 0xFFFFU )                 /*!< Max NRT steps in 1fc (0xFFFF steps of 4096/fc => 0xFFFF * 302us  = 19.8s )      */
#define RFAL_ST25R200_NRT_DISABLED     0U                                             /*!< NRT Disabled: All 0 No-response timer is not started, wait forever              */
#define RFAL_ST25R200_MRT_MAX_1FC      rfalConv64fcTo1fc( 0x00FFU )                   /*!< Max MRT steps in 1fc (0x00FF steps of 64/fc   => 0x00FF * 4.72us = 1.2ms )      */
#define RFAL_ST25R200_MRT_MIN_1FC      rfalConv64fcTo1fc( 0x0004U )                   /*!< Min MRT steps in 1fc ( 0<=mrt<=4 ; 4 (64/fc)  => 0x0004 * 4.72us = 18.88us )    */
#define RFAL_ST25R200_GT_MAX_1FC       rfalConvMsTo1fc( 6000U )                       /*!< Max GT value allowed in 1/fc (SFGI=14 => SFGT + dSFGT = 5.4s)                   */
#define RFAL_ST25R200_GT_MIN_1FC       rfalConvMsTo1fc(RFAL_ST25R200_SW_TMR_MIN_1MS)  /*!< Min GT value allowed in 1/fc                                                    */
#define RFAL_ST25R200_SW_TMR_MIN_1MS   1U                                             /*!< Min value of a SW timer in ms                                                   */

#define RFAL_OBSMODE_DISABLE            0x0000U                                       /*!< Observation Mode disabled                                                       */

#define RFAL_RX_INC_BYTE_LEN            (uint8_t)1U                                   /*!< Threshold where incoming rx shall be considered incomplete byte NFC - T2T       */
#define RFAL_EMVCO_RX_MAXLEN            (uint8_t)4U                                   /*!< Maximum value where EMVCo to apply special error handling                       */

#define RFAL_NORXE_TOUT                 50U                                           /*!< Timeout to be used on a potential missing RXE                                   */

#define RFAL_ISO14443A_SHORTFRAME_LEN   7U                                            /*!< Number of bits of a Short Frame in bits             Digital 2.0  6.3.2  & 6.6   */
#define RFAL_ISO14443A_SDD_RES_LEN      5U                                            /*!< SDD_RES | Anticollision (UID CLn) length  -  rfalNfcaSddRes                     */

#define RFAL_LM_NFCID_INCOMPLETE        0x04U                                         /*!<  NFCA NFCID not complete bit in SEL_RES (SAK)                                   */

#define RFAL_ISO15693_IGNORE_BITS       rfalConvBytesToBits(2U)                       /*!< Ignore collisions before the UID (RES_FLAG + DSFID)                             */
#define RFAL_ISO15693_INV_RES_LEN       12U                                           /*!< ISO15693 Inventory response length with CRC (bytes)                             */
#define RFAL_ISO15693_INV_RES_DUR       4U                                            /*!< ISO15693 Inventory response duration @ 26 kbps (ms)                             */

#define RFAL_PD_SETTLE                  3U                                            /*!< Settling duration after entering PD/WU mode                                     */

/*******************************************************************************/

#define RFAL_FDT_POLL_ADJUSTMENT        rfalConvUsTo1fc(80U)                          /*!< FDT Poll adjustment: Time between the expiration of GPT to the actual Tx        */
#define RFAL_FDT_LISTEN_MRT_ADJUSTMENT  64U                                           /*!< MRT jitter adjustment: timeout will be between [ tout ; tout + 64 cycles ]      */


/*! t1max = 323,3us = 4384/fc = 68.5 * 64/fc
 *         12 = 768/fc unmodulated time of single subcarrior SoF */
#define RFAL_ISO15693_FWT             rfalConv64fcTo1fc(69U + 12U)

/*! FWT adjustment: 
 *    64 : NRT jitter between TXE and NRT start      */
#define RFAL_FWT_ADJUSTMENT             64U

/*! FWT ISO14443A adjustment:  
 *   512  : 4bit length
 *    64  : Half a bit duration due to ST25R200 Coherent receiver (1/fc)         */
#define RFAL_FWT_A_ADJUSTMENT           (512U + 64U)

/*! FWT ISO14443B adjustment:  
 *    SOF (14etu) + 1Byte (10etu) + 1etu (IRQ comes 1etu after first byte) - 3etu (ST25R200 sends TXE 3etu after) */
#define RFAL_FWT_B_ADJUSTMENT           (((14U + 10U + 1U) - 3U) * 128U)

/*! FWT ISO15693 adjustment:  
 *    SOF (2bd) + n bits (n * bd) (at 26kbps) */
#define RFAL_FWT_V_ADJUSTMENT           ((2U * 512U) + (5U * 512U))


/*! Time between our field Off and other peer field On : Tadt + (n x Trfw)
 * Ecma 340 11.1.2 - Tadt: [56.64 , 188.72] us ;  n: [0 , 3]  ; Trfw = 37.76 us        
 * Should be: 189 + (3*38) = 303us ; we'll use a more relaxed setting: 605 us    */
#define RFAL_AP2P_FIELDON_TADTTRFW      rfalConvUsTo1fc(605U)


/*! FDT Listen adjustment for ISO14443A   EMVCo 2.6  4.8.1.3  ;  Digital 1.1  6.10
 *
 *  276: Time from the rising pulse of the pause of the logic '1' (i.e. the time point to measure the deaftime from), 
 *       to the actual end of the EOF sequence (the point where the MRT starts). Please note that the ST25R uses the 
 *       ISO14443-2 definition where the EOF consists of logic '0' followed by sequence Y. 
 *  -64: Further adjustment for receiver to be ready just before first bit
 */
#define RFAL_FDT_LISTEN_A_ADJUSTMENT    (276U-64U)


/*! FDT Listen adjustment for ISO14443B   EMVCo 2.6  4.8.1.6  ;  Digital 1.1  7.9
 *
 *  340: Time from the rising edge of the EoS to the starting point of the MRT timer (sometime after the final high 
 *       part of the EoS is completed)
 */
#define RFAL_FDT_LISTEN_B_ADJUSTMENT    340U


/*! FDT Listen adjustment for ISO15693
 * ISO15693 2000  8.4  t1 MIN = 4192/fc
 * ISO15693 2009  9.1  t1 MIN = 4320/fc
 * Digital 2.1 B.5 FDTV,LISTEN,MIN  = 4310/fc
 * Set FDT Listen one step earlier than on the more recent spec versions for greater interoprability
 */
#define RFAL_FDT_LISTEN_V_ADJUSTMENT    64U


/*! TR1 MIN for ISO14443B       EMVCo 3.1  A.5  ;  Digital 2.2  B.3 ; ISO14443-3 2018  7.10.3.2
 *
 *  NFC Forum  TR1,MIN(DEFAULT) 1264 (1/fc)   [ 256  ; 1280 ] (1/fc)   (for Poller|PCD:  +/- 16/fc)
 *             TR1,MAX          3200 (1/fc)
 *                 
 *  EMVCo      TR1,MIN          1264 (1/fc)
 *
 *  ISO        TR1,MIN          [ 80 ; 64 ; 16] (1/fs) => [ 1280 ; 1024 ; 256 ] (1/fc)
 *             TR1,MAX          200 (1/fs) => 3200 (1/fc)
 *
 * TR1_min: 58 (1/fs) + start_wait
 *
 */
#define RFAL_TR1MIN       58U


/*! Maximal required waiting for rx_on after RX_REST
*   
*  SPI at 10MHz: 1byte = 800ns  |  38bytes = 30.4us 
*  15 => ISR (4bytes) + 15x Reg Read (2bytes)
 */
#define RFAL_RX_REST_ON_WAIT           15U



/*
******************************************************************************
* GLOBAL MACROS
******************************************************************************
*/

#define rfalCalcNumBytes( nBits )                (((uint32_t)(nBits) + 7U) / 8U)                                 /*!< Returns the number of bytes required to fit given the number of bits */

#define rfalTimerStart( timer, time_ms )         do{ platformTimerDestroy( timer ); (timer) = platformTimerCreate((uint16_t)(time_ms)); } while(0) /*!< Configures and starts timer        */
#define rfalTimerisExpired( timer )              platformTimerIsExpired( timer )                                 /*!< Checks if timer has expired                                          */
#define rfalTimerDestroy( timer )                platformTimerDestroy( timer )                                   /*!< Destroys timer                                                       */

#define rfalST25R200ObsModeDisable()            st25r200WriteTestRegister(0x02U, 0x00U)                          /*!< Disable ST25R200 Observation mode                                    */
#define rfalST25R200ObsModeTx()                 do{ gRFAL.conf.obsvModeCfg[0]=(uint8_t)(gRFAL.conf.obsvModeTx>>8U); gRFAL.conf.obsvModeCfg[1]=(uint8_t)(gRFAL.conf.obsvModeTx&0xFFU); st25r200WriteMultipleTestRegister(0x02U, gRFAL.conf.obsvModeCfg, 2U); }while(0)  /*!< Enable Tx Observation mode                                           */
#define rfalST25R200ObsModeRx()                 do{ gRFAL.conf.obsvModeCfg[0]=(uint8_t)(gRFAL.conf.obsvModeRx>>8U); gRFAL.conf.obsvModeCfg[1]=(uint8_t)(gRFAL.conf.obsvModeRx&0xFFU); st25r200WriteMultipleTestRegister(0x02U, gRFAL.conf.obsvModeCfg, 2U); }while(0)  /*!< Enable Rx Observation mode                                           */


#define rfalCheckDisableObsMode()                if(gRFAL.conf.obsvModeRx != 0U){ rfalST25R200ObsModeDisable(); } /*!< Checks if the observation mode is enabled, and applies on ST25R200  */
#define rfalCheckEnableObsModeTx()               if(gRFAL.conf.obsvModeTx != 0U){ rfalST25R200ObsModeTx(); }      /*!< Checks if the observation mode is enabled, and applies on ST25R200  */
#define rfalCheckEnableObsModeRx()               if(gRFAL.conf.obsvModeRx != 0U){ rfalST25R200ObsModeRx(); }      /*!< Checks if the observation mode is enabled, and applies on ST25R200  */


#define rfalGetIncmplBits( FIFOStatus2 )         (( (FIFOStatus2) >> 1) & 0x07U)                                           /*!< Returns the number of bits from fifo status                */
#define rfalIsIncompleteByteError( error )       (((error) >= RFAL_ERR_INCOMPLETE_BYTE) && ((error) <= RFAL_ERR_INCOMPLETE_BYTE_07)) /*!< Checks if given error is a Incomplete error      */

#define rfalAdjACBR( b )                         (((uint16_t)(b) >= (uint16_t)RFAL_BR_52p97) ? (uint16_t)(b) : ((uint16_t)(b)+1U))          /*!< Adjusts ST25R Bit rate to Analog Configuration              */
#define rfalConvBR2ACBR( b )                     (((rfalAdjACBR((b)))<<RFAL_ANALOG_CONFIG_BITRATE_SHIFT) & RFAL_ANALOG_CONFIG_BITRATE_MASK) /*!< Converts ST25R Bit rate to Analog Configuration bit rate id */
#define rfalConvBitRate( br )                    ( (((br)==RFAL_BR_106) || ((br)==RFAL_BR_26p48)) ? (ST25R200_BR_106_26) : ST25R200_BR_424_53 )

/*
 ******************************************************************************
 * LOCAL VARIABLES
 ******************************************************************************
 */

static rfal gRFAL;              /*!< RFAL module instance               */

/*
******************************************************************************
* LOCAL FUNCTION PROTOTYPES
******************************************************************************
*/

static void rfalTransceiveTx( void );
static void rfalTransceiveRx( void );
static ReturnCode rfalTransceiveRunBlockingTx( void );
static void rfalPrepareTransceive( void );
static void rfalCleanupTransceive( void );
static void rfalErrorHandling( void );

static ReturnCode rfalRunTransceiveWorker( void );
#if RFAL_FEATURE_WAKEUP_MODE
static void rfalRunWakeUpModeWorker( void );
#endif /* RFAL_FEATURE_WAKEUP_MODE */

static bool rfalWaitRxOn( void );
static void rfalFIFOStatusUpdate( void );
static void rfalFIFOStatusClear( void );
static bool rfalFIFOStatusIsMissingPar( void );
static bool rfalFIFOStatusIsIncompleteByte( void );
static uint16_t rfalFIFOStatusGetNumBytes( void );
static uint8_t  rfalFIFOGetNumIncompleteBits( void );


/*
******************************************************************************
* GLOBAL FUNCTIONS
******************************************************************************
*/


/*******************************************************************************/
ReturnCode rfalInitialize( void )
{
    ReturnCode err;
    
    RFAL_EXIT_ON_ERR( err, st25r200Initialize() );
    
    st25r200ClearInterrupts();
    
    /* Disable any previous observation mode */
    rfalST25R200ObsModeDisable();
    
    /*******************************************************************************/    
    /* Apply RF Chip generic initialization */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_INIT) );
    
    /* Clear FIFO status local copy */
    rfalFIFOStatusClear();
    
    
    /*******************************************************************************/
    gRFAL.state              = RFAL_STATE_INIT;
    gRFAL.mode               = RFAL_MODE_NONE;
    gRFAL.field              = false;
    
    /* Set RFAL default configs */
    gRFAL.conf.obsvModeRx    = RFAL_OBSMODE_DISABLE;
    gRFAL.conf.obsvModeTx    = RFAL_OBSMODE_DISABLE;
    gRFAL.conf.eHandling     = RFAL_ERRORHANDLING_NONE;
    
    /* Transceive set to IDLE */
    gRFAL.TxRx.lastState     = RFAL_TXRX_STATE_IDLE;
    gRFAL.TxRx.state         = RFAL_TXRX_STATE_IDLE;
    
    /* Disable all timings */
    gRFAL.timings.FDTListen  = RFAL_TIMING_NONE;
    gRFAL.timings.FDTPoll    = RFAL_TIMING_NONE;
    gRFAL.timings.GT         = RFAL_TIMING_NONE;

    rfalTimerDestroy( gRFAL.tmr.GT );
    gRFAL.tmr.GT             = RFAL_TIMING_NONE;
    
    gRFAL.callbacks.preTxRx  = NULL;
    gRFAL.callbacks.postTxRx = NULL;
    gRFAL.callbacks.syncTxRx = NULL;

#if RFAL_FEATURE_WAKEUP_MODE
    /* Initialize Wake-Up Mode */
    gRFAL.wum.state = RFAL_WUM_STATE_NOT_INIT;
#endif /* RFAL_FEATURE_WAKEUP_MODE */

#if RFAL_FEATURE_LOWPOWER_MODE
    /* Initialize Low Power Mode */
    gRFAL.lpm.isRunning     = false;
#endif /* RFAL_FEATURE_LOWPOWER_MODE */
    
    
    /*******************************************************************************/    
    /* Perform Automatic Calibration (if configured to do so).                     *
     * Registers set by rfalSetAnalogConfig will tell rfalCalibrate what to perform*/
     /* PRQA S 2987 1 # MISRA 2.2 - Feature not available - placeholder  */
    rfalCalibrate();
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalCalibrate( void )
{
    /*******************************************************************************/
    /* Perform ST25R200 regulators calibration                                     */
    /*******************************************************************************/
    
    /* Automatic regulator adjustment only performed if not set manually on Analog Configs */
    if( st25r200CheckReg( ST25R200_REG_GENERAL, ST25R200_REG_GENERAL_reg_s, 0x00 ) )       
    {
        return rfalAdjustRegulators( NULL );
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalAdjustRegulators( uint16_t* result )
{
    /* Adjust the regulators with both Tx and Rx enabled for a realistic RW load conditions */
    st25r200TxRxOn();
    st25r200AdjustRegulators( ST25R200_REG_DROP_DO_NOT_SET, result );
    st25r200TxRxOff();
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalSetRegulators( uint8_t regulation )
{   
    return st25r200SetRegulators( regulation );
}


/*******************************************************************************/
void rfalSetUpperLayerCallback( rfalUpperLayerCallback pFunc )
{
    st25r200IRQCallbackSet( pFunc );
}


/*******************************************************************************/
void rfalSetPreTxRxCallback( rfalPreTxRxCallback pFunc )
{
    gRFAL.callbacks.preTxRx = pFunc;
}


/*******************************************************************************/
void rfalSetSyncTxRxCallback( rfalSyncTxRxCallback pFunc )
{
    gRFAL.callbacks.syncTxRx = pFunc;
}


/*******************************************************************************/
void rfalSetPostTxRxCallback( rfalPostTxRxCallback pFunc )
{
    gRFAL.callbacks.postTxRx = pFunc;
}


/*******************************************************************************/
void rfalSetLmEonCallback( rfalLmEonCallback pFunc )
{
    RFAL_NO_WARNING( pFunc );
    return;   /* ERR_NOTSUPP */
}


/*******************************************************************************/
ReturnCode rfalDeinitialize( void )
{
    /* Deinitialize chip */
    st25r200Deinitialize();
    
    /* Set Analog configurations for deinitialization */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_DEINIT) );
 
    gRFAL.state = RFAL_STATE_IDLE;
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
void rfalSetObsvMode( uint32_t txMode, uint32_t rxMode )
{
    gRFAL.conf.obsvModeTx = (uint16_t)txMode;
    gRFAL.conf.obsvModeRx = (uint16_t)rxMode;
}


/*******************************************************************************/
void rfalGetObsvMode( uint8_t* txMode, uint8_t* rxMode )
{
    if(txMode != NULL)
    {
        *txMode = (uint8_t)gRFAL.conf.obsvModeTx;
    }
    
    if(rxMode != NULL)
    {
        *rxMode = (uint8_t)gRFAL.conf.obsvModeRx;
    }
}


/*******************************************************************************/
void rfalDisableObsvMode( void )
{
    gRFAL.conf.obsvModeTx = RFAL_OBSMODE_DISABLE;
    gRFAL.conf.obsvModeRx = RFAL_OBSMODE_DISABLE;
}


/*******************************************************************************/
ReturnCode rfalSetMode( rfalMode mode, rfalBitRate txBR, rfalBitRate rxBR )
{

    /* Check if RFAL is not initialized */
    if( gRFAL.state == RFAL_STATE_IDLE )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check allowed bit rate value */
    if( (txBR == RFAL_BR_KEEP) || (rxBR == RFAL_BR_KEEP) )
    {
        return RFAL_ERR_PARAM;
    }
   
    switch( mode )
    {
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCA:
            
            /* Enable ISO14443A mode */
            st25r200WriteRegister( ST25R200_REG_PROTOCOL, ST25R200_REG_PROTOCOL_om_iso14443a );
            
            /* Set Analog configurations for this mode and bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            break;
            
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCA_T1T:
            
            /* Enable Topaz mode */
            st25r200WriteRegister( ST25R200_REG_PROTOCOL, ST25R200_REG_PROTOCOL_om_topaz );
            
            /* Set Analog configurations for this mode and bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            break;
            
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCB:
            
            /* Enable ISO14443B mode */
            st25r200WriteRegister( ST25R200_REG_PROTOCOL, ST25R200_REG_PROTOCOL_om_iso14443b );
            
            /* Set Tx SOF and EOF */
            st25r200ChangeRegisterBits(  ST25R200_REG_PROTOCOL_TX2,
                                        ( ST25R200_REG_PROTOCOL_TX2_b_tx_sof_mask | ST25R200_REG_PROTOCOL_TX2_b_tx_eof ),
                                        ( ST25R200_REG_PROTOCOL_TX2_b_tx_sof_0_10etu | ST25R200_REG_PROTOCOL_TX2_b_tx_sof_1_2etu | ST25R200_REG_PROTOCOL_TX2_b_tx_eof_10etu ) );
                        
            /* Set Rx SOF and EOF */
            st25r200ChangeRegisterBits(  ST25R200_REG_PROTOCOL_RX1, 
                                        ( ST25R200_REG_PROTOCOL_RX1_b_rx_sof | ST25R200_REG_PROTOCOL_RX1_b_rx_eof ),
                                        ( ST25R200_REG_PROTOCOL_RX1_b_rx_sof | ST25R200_REG_PROTOCOL_RX1_b_rx_eof ) );
        
            /* Set the minimum TR1 (excluding start_wait) */
            st25r200ChangeRegisterBits( ST25R200_REG_PROTOCOL_RX2, ST25R200_REG_PROTOCOL_RX2_tr1_min_len_mask, RFAL_TR1MIN );

            /* Set Analog configurations for this mode and bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            break;
            
        /*******************************************************************************/    
        case RFAL_MODE_POLL_B_PRIME:
            
            /* Enable ISO14443B mode */
            st25r200WriteRegister( ST25R200_REG_PROTOCOL, ST25R200_REG_PROTOCOL_om_iso14443b );
            
            /* Set Tx SOF, EOF and EOF */
            st25r200ChangeRegisterBits(  ST25R200_REG_PROTOCOL_TX2,
                                        ( ST25R200_REG_PROTOCOL_TX2_b_tx_sof_mask | ST25R200_REG_PROTOCOL_TX2_b_tx_eof ),
                                        ( ST25R200_REG_PROTOCOL_TX2_b_tx_sof_0_10etu | ST25R200_REG_PROTOCOL_TX2_b_tx_sof_1_2etu | ST25R200_REG_PROTOCOL_TX2_b_tx_eof_10etu ) );
                        
            /* Set Rx SOF and EOF */
            st25r200ChangeRegisterBits( ST25R200_REG_PROTOCOL_RX1, 
                                        ( ST25R200_REG_PROTOCOL_RX1_b_rx_sof | ST25R200_REG_PROTOCOL_RX1_b_rx_eof ),
                                        ( ST25R200_REG_PROTOCOL_RX1_b_rx_eof ) );
        
            /* Set the minimum TR1 (excluding start_wait) */
            st25r200ChangeRegisterBits( ST25R200_REG_PROTOCOL_RX2, ST25R200_REG_PROTOCOL_RX2_tr1_min_len_mask, RFAL_TR1MIN );


            /* Set Analog configurations for this mode and bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            break;
            
        /*******************************************************************************/    
        case RFAL_MODE_POLL_B_CTS:
            
            /* Enable ISO14443B mode */
            st25r200WriteRegister( ST25R200_REG_PROTOCOL, ST25R200_REG_PROTOCOL_om_iso14443b );
            
            /* Set Tx SOF and EOF */
            st25r200ChangeRegisterBits(  ST25R200_REG_PROTOCOL_TX2,
                                        ( ST25R200_REG_PROTOCOL_TX2_b_tx_sof_mask | ST25R200_REG_PROTOCOL_TX2_b_tx_eof ),
                                        ( ST25R200_REG_PROTOCOL_TX2_b_tx_sof_0_10etu | ST25R200_REG_PROTOCOL_TX2_b_tx_sof_1_2etu | ST25R200_REG_PROTOCOL_TX2_b_tx_eof_10etu ) );
                        
            /* Set Rx SOF EOF */
            st25r200ChangeRegisterBits(  ST25R200_REG_PROTOCOL_RX1, 
                                        ( ST25R200_REG_PROTOCOL_RX1_b_rx_sof | ST25R200_REG_PROTOCOL_RX1_b_rx_eof ),
                                         0x00 );
        
            /* Set the minimum TR1 (excluding start_wait) */    
            st25r200ChangeRegisterBits( ST25R200_REG_PROTOCOL_RX2, ST25R200_REG_PROTOCOL_RX2_tr1_min_len_mask, RFAL_TR1MIN );

            /* Set Analog configurations for this mode and bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            break;
        
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCV:
        case RFAL_MODE_POLL_PICOPASS:
                
                /* Enable ISO15693 mode */
                st25r200WriteRegister( ST25R200_REG_PROTOCOL, ST25R200_REG_PROTOCOL_om_iso15693 );
        
                /* Set Analog configurations for this mode and bit rate */
                rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
                rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
                break;
        
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCF:
        case RFAL_MODE_POLL_ACTIVE_P2P:
        case RFAL_MODE_LISTEN_ACTIVE_P2P:
        case RFAL_MODE_LISTEN_NFCA:
        case RFAL_MODE_LISTEN_NFCF:
        case RFAL_MODE_LISTEN_NFCB:
            return RFAL_ERR_NOTSUPP;
            
        /*******************************************************************************/
        default:
            return RFAL_ERR_NOT_IMPLEMENTED;
    }
    
    /* Set state as STATE_MODE_SET only if not initialized yet (PSL) */
    gRFAL.state = ((gRFAL.state < RFAL_STATE_MODE_SET) ? RFAL_STATE_MODE_SET : gRFAL.state);
    gRFAL.mode  = mode;
    
    /* Apply the given bit rate */
    return rfalSetBitRate(txBR, rxBR);
}


/*******************************************************************************/
rfalMode rfalGetMode( void )
{
    return gRFAL.mode;
}

/*******************************************************************************/
ReturnCode rfalSetBitRate( rfalBitRate txBR, rfalBitRate rxBR )
{
    ReturnCode ret;
    
    /* Check if RFAL is not initialized */
    if( gRFAL.state == RFAL_STATE_IDLE )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    
    if( ( (txBR != RFAL_BR_KEEP) && (txBR != RFAL_BR_106) && (txBR != RFAL_BR_26p48))                          || 
        ( (rxBR != RFAL_BR_KEEP) && (rxBR!= RFAL_BR_106) && (rxBR != RFAL_BR_26p48) && (rxBR != RFAL_BR_52p97))  )
    {
        return RFAL_ERR_PARAM;
    }
    
    /* Store the new Bit Rates */
    gRFAL.txBR = ((txBR == RFAL_BR_KEEP) ? gRFAL.txBR : txBR);
    gRFAL.rxBR = ((rxBR == RFAL_BR_KEEP) ? gRFAL.rxBR : rxBR);
    

    /* Set bit rate register */
    RFAL_EXIT_ON_ERR( ret, st25r200SetBitrate( (uint8_t)rfalConvBitRate(gRFAL.txBR), (uint8_t)rfalConvBitRate(gRFAL.rxBR )) );
    
    
    switch( gRFAL.mode )
    {
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCA:
        case RFAL_MODE_POLL_NFCA_T1T:
            
            /* Set Analog configurations for this bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_POLL_COMMON) );
            rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | rfalConvBR2ACBR(gRFAL.txBR) | RFAL_ANALOG_CONFIG_TX ) );
            rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | rfalConvBR2ACBR(gRFAL.rxBR) | RFAL_ANALOG_CONFIG_RX ) );
            break;
            
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCB:
        case RFAL_MODE_POLL_B_PRIME:
        case RFAL_MODE_POLL_B_CTS:
            
            /* Set Analog configurations for this bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_POLL_COMMON) );
            rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | rfalConvBR2ACBR(gRFAL.txBR) | RFAL_ANALOG_CONFIG_TX ) );
            rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | rfalConvBR2ACBR(gRFAL.rxBR) | RFAL_ANALOG_CONFIG_RX ) );
            break;
        
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCV:
        case RFAL_MODE_POLL_PICOPASS:
            
                /* Set Analog configurations for this bit rate */
                rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_POLL_COMMON) );
                rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | rfalConvBR2ACBR(gRFAL.txBR) | RFAL_ANALOG_CONFIG_TX ) );
                rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | rfalConvBR2ACBR(gRFAL.rxBR) | RFAL_ANALOG_CONFIG_RX ) );
                break;
        
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCF:
        case RFAL_MODE_POLL_ACTIVE_P2P:
        case RFAL_MODE_LISTEN_ACTIVE_P2P:
        case RFAL_MODE_LISTEN_NFCA:
        case RFAL_MODE_LISTEN_NFCF:
        case RFAL_MODE_LISTEN_NFCB:
        case RFAL_MODE_NONE:
            return RFAL_ERR_WRONG_STATE;
            
        /*******************************************************************************/
        default:
            return RFAL_ERR_NOT_IMPLEMENTED;
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalGetBitRate( rfalBitRate *txBR, rfalBitRate *rxBR )
{
    if( (gRFAL.state == RFAL_STATE_IDLE) || (gRFAL.mode == RFAL_MODE_NONE) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    if( txBR != NULL )
    {
        *txBR = gRFAL.txBR;
    }
    
    if( rxBR != NULL )
    {
        *rxBR = gRFAL.rxBR;
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
void rfalSetErrorHandling( rfalEHandling eHandling )
{
    switch(eHandling)
    {
        case RFAL_ERRORHANDLING_NONE:
            st25r200ClrRegisterBits( ST25R200_REG_EMD1, ST25R200_REG_EMD1_emd_en );
            break;
            
        case RFAL_ERRORHANDLING_EMD:

            st25r200ModifyRegister(  ST25R200_REG_EMD1,
                                    ( ST25R200_REG_EMD1_emd_thld_mask | ST25R200_REG_EMD1_emd_thld_ff | ST25R200_REG_EMD1_emd_en ),
                                    ( (RFAL_EMVCO_RX_MAXLEN<<ST25R200_REG_EMD1_emd_thld_shift) | ST25R200_REG_EMD1_emd_thld_ff | ST25R200_REG_EMD1_emd_en_on ) );
            break;
        
        default:
            /* MISRA 16.4: no empty default statement (a comment being enough) */
            break;
    }

    gRFAL.conf.eHandling = eHandling;
}


/*******************************************************************************/
rfalEHandling rfalGetErrorHandling( void )
{
    return gRFAL.conf.eHandling;
}


/*******************************************************************************/
void rfalSetFDTPoll( uint32_t FDTPoll )
{
    gRFAL.timings.FDTPoll = RFAL_MIN( FDTPoll, RFAL_ST25R200_GPT_MAX_1FC );
}


/*******************************************************************************/
uint32_t rfalGetFDTPoll( void )
{
    return gRFAL.timings.FDTPoll;
}


/*******************************************************************************/
void rfalSetFDTListen( uint32_t FDTListen )
{
    gRFAL.timings.FDTListen = RFAL_MIN( FDTListen, RFAL_ST25R200_MRT_MAX_1FC );
}


/*******************************************************************************/
uint32_t rfalGetFDTListen( void )
{
    return gRFAL.timings.FDTListen;
}


/*******************************************************************************/
void rfalSetGT( uint32_t GT )
{
    gRFAL.timings.GT = RFAL_MIN( GT, RFAL_ST25R200_GT_MAX_1FC );
}


/*******************************************************************************/
uint32_t rfalGetGT( void )
{
    return gRFAL.timings.GT;
}


/*******************************************************************************/
bool rfalIsGTExpired( void )
{
    if( gRFAL.tmr.GT != RFAL_TIMING_NONE )
    {
        if( !rfalTimerisExpired( gRFAL.tmr.GT ) )
        {
            return false;
        }
    }    
    return true;
}


/*******************************************************************************/
ReturnCode rfalFieldOnAndStartGT( void )
{
    ReturnCode ret;
    
    /* Check if RFAL has been initialized (Oscillator should be running) and also
     * if a direct register access has been performed and left the Oscillator Off */
    if( (!st25r200IsOscOn()) || (gRFAL.state < RFAL_STATE_INIT) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    ret = RFAL_ERR_NONE;
    
    /* Set Analog configurations for Field On event */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_FIELD_ON) );
    
    /*******************************************************************************/
    /* Perform collision avoidance and turn field On if not already On */
    if( (!st25r200IsTxEnabled()) || (!gRFAL.field) )
    {
        st25r200TxRxOn();
        gRFAL.field = st25r200IsTxEnabled();
    }
    
    /*******************************************************************************/
    /* Start GT timer in case the GT value is set */
    if( (gRFAL.timings.GT != RFAL_TIMING_NONE) )
    {
        /* Ensure that a SW timer doesn't have a lower value then the minimum  */
        rfalTimerStart( gRFAL.tmr.GT, rfalConv1fcToMs( RFAL_MAX( (gRFAL.timings.GT), RFAL_ST25R200_GT_MIN_1FC) ) );
    }
    
    return ret;
}


/*******************************************************************************/
ReturnCode rfalFieldOff( void )
{
    /* Check whether a TxRx is not yet finished */
    if( gRFAL.TxRx.state != RFAL_TXRX_STATE_IDLE )
    {
        rfalCleanupTransceive();
    }
    
    /* Disable Tx and Rx */
    st25r200TxRxOff();
    
    /* Set Analog configurations for Field Off event */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_FIELD_OFF) );
    gRFAL.field = false;
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalStartTransceive( const rfalTransceiveContext *ctx )
{
    uint32_t FxTAdj;  /* FWT or FDT adjustment calculation */
    
    /* Check for valid parameters */
    if( ctx == NULL )
    {
        return RFAL_ERR_PARAM;
    }
    
    /* Ensure that RFAL is already Initialized and the mode has been set */
    if( gRFAL.state >= RFAL_STATE_MODE_SET )
    {
        /*******************************************************************************/
        /* Check whether the field is already On, otherwise no TXE will be received  */
        if( (!st25r200IsTxEnabled()) && (ctx->txBuf != NULL) )
        {
            return RFAL_ERR_WRONG_STATE;
        }
        
        gRFAL.TxRx.ctx = *ctx;
        
        /*******************************************************************************/
        if( gRFAL.timings.FDTListen != RFAL_TIMING_NONE )
        {
            /* Calculate MRT adjustment accordingly to the current mode */
            FxTAdj = RFAL_FDT_LISTEN_MRT_ADJUSTMENT;
            if(gRFAL.mode == RFAL_MODE_POLL_NFCA)      { FxTAdj += (uint32_t)RFAL_FDT_LISTEN_A_ADJUSTMENT; }
            if(gRFAL.mode == RFAL_MODE_POLL_NFCA_T1T)  { FxTAdj += (uint32_t)RFAL_FDT_LISTEN_A_ADJUSTMENT; }
            if(gRFAL.mode == RFAL_MODE_POLL_NFCB)      { FxTAdj += (uint32_t)RFAL_FDT_LISTEN_B_ADJUSTMENT; }
            if(gRFAL.mode == RFAL_MODE_POLL_NFCV)      { FxTAdj += (uint32_t)RFAL_FDT_LISTEN_V_ADJUSTMENT; }
            
            /* Ensure that MRT is using 64/fc steps */
            st25r200ChangeRegisterBits(ST25R200_REG_MRT_SQT_CONF, ST25R200_REG_MRT_SQT_CONF_mrt_step_mask, ST25R200_REG_MRT_SQT_CONF_mrt_step_64fc );
            
            /* Set Minimum FDT(Listen) in which PICC is not allowed to send a response */
            st25r200WriteRegister( ST25R200_REG_MRT, (uint8_t)rfalConv1fcTo64fc( (FxTAdj > gRFAL.timings.FDTListen) ? RFAL_ST25R200_MRT_MIN_1FC : (gRFAL.timings.FDTListen - FxTAdj) ) );
        }
        
        /*******************************************************************************/
        /* FDT Poll will be loaded in rfalPrepareTransceive() once the previous was expired */
        
        /*******************************************************************************/
        if( (gRFAL.TxRx.ctx.fwt != RFAL_FWT_NONE) && (gRFAL.TxRx.ctx.fwt != 0U) )
        {
            /* Ensure proper timing configuration */
            if( gRFAL.timings.FDTListen >= gRFAL.TxRx.ctx.fwt )
            {
                return RFAL_ERR_PARAM;
            }
            
            FxTAdj = RFAL_FWT_ADJUSTMENT;
            if(gRFAL.mode == RFAL_MODE_POLL_NFCA)      { FxTAdj += (uint32_t)RFAL_FWT_A_ADJUSTMENT;    }
            if(gRFAL.mode == RFAL_MODE_POLL_NFCA_T1T)  { FxTAdj += (uint32_t)RFAL_FWT_A_ADJUSTMENT;    }
            if(gRFAL.mode == RFAL_MODE_POLL_NFCB)      { FxTAdj += (uint32_t)RFAL_FWT_B_ADJUSTMENT;    }
            if(gRFAL.mode == RFAL_MODE_POLL_NFCV)      { FxTAdj += (uint32_t)RFAL_FWT_V_ADJUSTMENT;    }
            
            /* Ensure that the given FWT doesn't exceed NRT maximum */
            gRFAL.TxRx.ctx.fwt = RFAL_MIN( (gRFAL.TxRx.ctx.fwt + FxTAdj), RFAL_ST25R200_NRT_MAX_1FC );
            
            /* Set FWT in the NRT */
            st25r200SetNoResponseTime( rfalConv1fcTo64fc( gRFAL.TxRx.ctx.fwt ) );
        }
        else
        {
            /* Disable NRT, no NRE will be triggered, therefore wait endlessly for Rx */
            st25r200SetNoResponseTime( RFAL_ST25R200_NRT_DISABLED );
        }
        
        gRFAL.state       = RFAL_STATE_TXRX;
        gRFAL.TxRx.state  = RFAL_TXRX_STATE_TX_IDLE;
        gRFAL.TxRx.status = RFAL_ERR_BUSY;

        
        /*******************************************************************************/
        /* Check if the Transceive start performing Tx or goes directly to Rx          */
        if( (gRFAL.TxRx.ctx.txBuf == NULL) || (gRFAL.TxRx.ctx.txBufLen == 0U) )
        {
            /* Clear FIFO, Clear and Enable the Interrupts */
            rfalPrepareTransceive( );
            
            /* No Tx done, enable the Receiver */
            st25r200ExecuteCommand( ST25R200_CMD_UNMASK_RECEIVE_DATA );

            /* Start NRT manually, if FWT = 0 (wait endlessly for Rx) chip will ignore anyhow */
            st25r200ExecuteCommand( ST25R200_CMD_START_NRT );

            gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_IDLE;
        }
        
        return RFAL_ERR_NONE;
    }
    
    return RFAL_ERR_WRONG_STATE;
}


/*******************************************************************************/
bool rfalIsTransceiveInTx( void )
{
    return ( (gRFAL.TxRx.state >= RFAL_TXRX_STATE_TX_IDLE) && (gRFAL.TxRx.state < RFAL_TXRX_STATE_RX_IDLE) );
}


/*******************************************************************************/
bool rfalIsTransceiveInRx( void )
{
    return (gRFAL.TxRx.state >= RFAL_TXRX_STATE_RX_IDLE);
}


/*******************************************************************************/
ReturnCode rfalTransceiveBlockingTx( uint8_t* txBuf, uint16_t txBufLen, uint8_t* rxBuf, uint16_t rxBufLen, uint16_t* actLen, uint32_t flags, uint32_t fwt )
{
    ReturnCode               ret;
    rfalTransceiveContext    ctx;
    
    rfalCreateByteFlagsTxRxContext( ctx, txBuf, txBufLen, rxBuf, rxBufLen, actLen, flags, fwt );
    RFAL_EXIT_ON_ERR( ret, rfalStartTransceive( &ctx ) );
    
    return rfalTransceiveRunBlockingTx();
}


/*******************************************************************************/
static ReturnCode rfalTransceiveRunBlockingTx( void )
{
    ReturnCode ret;
        
    do{
        rfalWorker();
        ret = rfalGetTransceiveStatus();
    }
    while( (rfalIsTransceiveInTx()) && (ret == RFAL_ERR_BUSY) );
    
    if( rfalIsTransceiveInRx() )
    {
        return RFAL_ERR_NONE;
    }
    
    return ret;
}


/*******************************************************************************/
ReturnCode rfalTransceiveBlockingRx( void )
{
    ReturnCode ret;
    
    do{
        rfalWorker();
        ret = rfalGetTransceiveStatus();
    }
    while( (rfalIsTransceiveInRx()) || (ret == RFAL_ERR_BUSY) );
        
    return ret;
}


/*******************************************************************************/
ReturnCode rfalTransceiveBlockingTxRx( uint8_t* txBuf, uint16_t txBufLen, uint8_t* rxBuf, uint16_t rxBufLen, uint16_t* actLen, uint32_t flags, uint32_t fwt )
{
    ReturnCode ret;
    
    RFAL_EXIT_ON_ERR( ret, rfalTransceiveBlockingTx( txBuf, txBufLen, rxBuf, rxBufLen, actLen, flags, fwt ) );
    ret = rfalTransceiveBlockingRx();
    
    /* Convert received bits to bytes */
    if( actLen != NULL )
    {
        *actLen = rfalConvBitsToBytes(*actLen);
    }
    
    return ret;
}


/*******************************************************************************/
static ReturnCode rfalRunTransceiveWorker( void )
{
    if( gRFAL.state == RFAL_STATE_TXRX )
    {     
        /* Run Tx or Rx state machines */
        if( rfalIsTransceiveInTx() )
        {
            rfalTransceiveTx();
            return rfalGetTransceiveStatus();
        }
        if( rfalIsTransceiveInRx() )
        {
            rfalTransceiveRx();
            return rfalGetTransceiveStatus();
        }
    }    
    return RFAL_ERR_WRONG_STATE;
}


/*******************************************************************************/
rfalTransceiveState rfalGetTransceiveState( void )
{
    return gRFAL.TxRx.state;
}


/*******************************************************************************/
ReturnCode rfalGetTransceiveStatus( void )
{
    return ((gRFAL.TxRx.state == RFAL_TXRX_STATE_IDLE) ? gRFAL.TxRx.status : RFAL_ERR_BUSY);
}


/*******************************************************************************/
ReturnCode rfalGetTransceiveRSSI( uint16_t *rssi )
{
    if( rssi != NULL )
    {
        (*rssi) = 0U;
    }
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
bool rfalIsTransceiveSubcDetected( void )
{
    if( (gRFAL.state == RFAL_STATE_TXRX) || (gRFAL.TxRx.state == RFAL_TXRX_STATE_IDLE) )
    {
        return (st25r200GetInterrupt( ST25R200_IRQ_MASK_SUBC_START ) != 0U);
    }
    return false;
}


/*******************************************************************************/
void rfalWorker( void )
{
    platformProtectWorker();               /* Protect RFAL Worker/Task/Process */
    
#ifdef ST25R_POLL_IRQ
    st25r200CheckForReceivedInterrupts();
#endif /* ST25R_POLL_IRQ */
    
    switch( gRFAL.state )
    {
        case RFAL_STATE_TXRX:
            rfalRunTransceiveWorker();
            break;
        
    #if RFAL_FEATURE_WAKEUP_MODE
        case RFAL_STATE_WUM:
            rfalRunWakeUpModeWorker();
            break;
    #endif /* RFAL_FEATURE_WAKEUP_MODE */
            
        /* Nothing to be done */
        default:            
            /* MISRA 16.4: no empty default statement (a comment being enough) */
            break;
    }
    
    platformUnprotectWorker();             /* Unprotect RFAL Worker/Task/Process */
}


/*******************************************************************************/
static void rfalErrorHandling( void )
{
    uint16_t fifoBytesToRead;
 
    fifoBytesToRead = rfalFIFOStatusGetNumBytes();
    

    /*******************************************************************************/
    /* ISO14443A Mode                                                              */
    /*******************************************************************************/
    if( gRFAL.mode == RFAL_MODE_POLL_NFCA )
    {
        /*******************************************************************************/
        /* If we received a frame with a incomplete byte we`ll raise a specific error  *
         * ( support for T2T 4 bit ACK / NAK, MIFARE and Kovio )                       */    
        /*******************************************************************************/
        if( (gRFAL.TxRx.status == RFAL_ERR_PAR) || (gRFAL.TxRx.status == RFAL_ERR_CRC) )
        {
            if( (rfalFIFOStatusIsIncompleteByte()) && (fifoBytesToRead == RFAL_RX_INC_BYTE_LEN) )
            {
                st25r200ReadFifo( (uint8_t*)(gRFAL.TxRx.ctx.rxBuf), fifoBytesToRead );
                if( (gRFAL.TxRx.ctx.rxRcvdLen) != NULL )
                {
                    *gRFAL.TxRx.ctx.rxRcvdLen = rfalFIFOGetNumIncompleteBits();
                }
                
                gRFAL.TxRx.status = RFAL_ERR_INCOMPLETE_BYTE;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
            }
        }
    }
}


/*******************************************************************************/
static void rfalCleanupTransceive( void )
{
    /*******************************************************************************/
    /* Transceive flags                                                            */
    /*******************************************************************************/
    
    /* Restore default settings on Tx Parity and CRC */
    st25r200SetRegisterBits( ST25R200_REG_PROTOCOL_TX1, (ST25R200_REG_PROTOCOL_TX1_a_tx_par | ST25R200_REG_PROTOCOL_TX1_tx_crc) );
    
    /* Restore default settings on Receiving parity + CRC bits */
    st25r200SetRegisterBits( ST25R200_REG_PROTOCOL_RX1, ( ST25R200_REG_PROTOCOL_RX1_a_rx_par | ST25R200_REG_PROTOCOL_RX1_rx_crc) );
    
    /* Restore AGC enabled */
    st25r200SetRegisterBits( ST25R200_REG_RX_DIG, ST25R200_REG_RX_DIG_agc_en );
    
    /*******************************************************************************/
    /* Execute Post Transceive Callback                                            */
    /*******************************************************************************/
    if( gRFAL.callbacks.postTxRx != NULL )
    {
        gRFAL.callbacks.postTxRx();
    }
    /*******************************************************************************/
}


/*******************************************************************************/
static void rfalPrepareTransceive( void )
{
    uint32_t maskInterrupts;
    uint32_t clrMaskInterrupts;
    uint8_t  reg;
    
    /* Reset receive logic with STOP command */
    st25r200ExecuteCommand( ST25R200_CMD_STOP );
    
    /* Reset Rx Gain */
    st25r200ExecuteCommand( ST25R200_CMD_CLEAR_RXGAIN );
    
    /*******************************************************************************/
    /* FDT Poll                                                                    */
    /*******************************************************************************/
    /* In Passive communications General Purpose Timer is used to measure FDT Poll */
    if( gRFAL.timings.FDTPoll != RFAL_TIMING_NONE )
    {
        /* Configure GPT to start at RX end */
        st25r200SetStartGPTimer( (uint16_t)rfalConv1fcTo8fc( ((gRFAL.timings.FDTPoll < RFAL_FDT_POLL_ADJUSTMENT) ? gRFAL.timings.FDTPoll : (gRFAL.timings.FDTPoll - RFAL_FDT_POLL_ADJUSTMENT)) ), ST25R200_REG_NRT_GPT_CONF_gptc_erx );
    }
    
    /*******************************************************************************/
    /* Execute Pre Transceive Callback                                             */
    /*******************************************************************************/
    if( gRFAL.callbacks.preTxRx != NULL )
    {
        gRFAL.callbacks.preTxRx();
    }
    /*******************************************************************************/
    
    /* IRQs that require immediate serving (ISR) for TxRx */
    maskInterrupts = ( ST25R200_IRQ_MASK_WL   | ST25R200_IRQ_MASK_TXE  |
                       ST25R200_IRQ_MASK_RXS  | ST25R200_IRQ_MASK_RXE  |
                       ST25R200_IRQ_MASK_PAR  | ST25R200_IRQ_MASK_CRC  |
                       ST25R200_IRQ_MASK_HFE  | ST25R200_IRQ_MASK_SFE  |
                       ST25R200_IRQ_MASK_NRE                            );
    
    /* IRQs that do not require immediate serving but may be used for TxRx */
    clrMaskInterrupts = ST25R200_IRQ_MASK_SUBC_START;
    
    /*******************************************************************************/
    /* Transceive flags                                                            */
    /*******************************************************************************/
    /* Transmission Flags */
    reg = (ST25R200_REG_PROTOCOL_TX1_tx_crc_on | ST25R200_REG_PROTOCOL_TX1_a_tx_par_on);
    

    /* Check if automatic Parity bits is to be disabled */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_PAR_TX_NONE) != 0U )
    {
        reg &= ~ST25R200_REG_PROTOCOL_TX1_a_tx_par;
    }
    
    /* Check if automatic Parity bits is to be disabled */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_CRC_TX_MANUAL) != 0U )
    {
        reg &= ~ST25R200_REG_PROTOCOL_TX1_tx_crc;
    }
    
    /* Apply current TxRx flags on Tx Register */
    st25r200ChangeRegisterBits( ST25R200_REG_PROTOCOL_TX1, (ST25R200_REG_PROTOCOL_TX1_tx_crc | ST25R200_REG_PROTOCOL_TX1_a_tx_par), reg );
    
    
    /* Check if NFCIP1 mode is to be enabled */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_NFCIP1_ON) != 0U )
    {
        /* No NFCIP1 HW handling: ignore */
    }
    
    
    /* Reception Flags */
    reg = (ST25R200_REG_PROTOCOL_RX1_a_rx_par_on | ST25R200_REG_PROTOCOL_RX1_rx_crc_on);
    
    /* Check if Parity check is to be skipped and to keep the parity bits in FIFO */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_PAR_RX_KEEP) != 0U )
    {
        reg &= ~ST25R200_REG_PROTOCOL_RX1_a_rx_par;
    }
    
    /* Check if CRC check is to be skipped */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_CRC_RX_MANUAL) != 0U )
    {
        reg &= ~ST25R200_REG_PROTOCOL_RX1_rx_crc;
    }
    
    /* Apply current TxRx flags on Tx Register */
    st25r200ChangeRegisterBits( ST25R200_REG_PROTOCOL_RX1, (ST25R200_REG_PROTOCOL_RX1_a_rx_par | ST25R200_REG_PROTOCOL_RX1_rx_crc), reg );
    
    
    /* Check if AGC is to be disabled */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_AGC_OFF) != 0U )
    {
        st25r200ClrRegisterBits( ST25R200_REG_RX_DIG, ST25R200_REG_RX_DIG_agc_en );
    }
    else
    {
        st25r200SetRegisterBits( ST25R200_REG_RX_DIG, ST25R200_REG_RX_DIG_agc_en );
    }
    /*******************************************************************************/
    
    
    /*******************************************************************************/
    /* EMD NRT mode                                                              */
    /*******************************************************************************/
    if( gRFAL.conf.eHandling == RFAL_ERRORHANDLING_EMD )
    {
        st25r200SetRegisterBits( ST25R200_REG_NRT_GPT_CONF, ST25R200_REG_NRT_GPT_CONF_nrt_emd );
        maskInterrupts |= ST25R200_IRQ_MASK_RX_REST;
    }
    else
    {
        st25r200ClrRegisterBits( ST25R200_REG_NRT_GPT_CONF, ST25R200_REG_NRT_GPT_CONF_nrt_emd );
    }
    /*******************************************************************************/
    
    
    /*******************************************************************************/
    /* Clear and enable these interrupts */
    st25r200GetInterrupt( (maskInterrupts | clrMaskInterrupts) );
    st25r200EnableInterrupts( maskInterrupts );
    
    /* Clear FIFO status local copy */
    rfalFIFOStatusClear();
}


/*******************************************************************************/
static void rfalTransceiveTx( void )
{
    uint32_t   irqs;
    uint16_t   tmp;
    ReturnCode ret;
    
    /* Suppress warning in case NFC-V feature is disabled */
    ret = RFAL_ERR_NONE;
    RFAL_NO_WARNING( ret );
    
    irqs = ST25R200_IRQ_MASK_NONE;
    
    if( gRFAL.TxRx.state != gRFAL.TxRx.lastState )
    {
        gRFAL.TxRx.lastState = gRFAL.TxRx.state;
    }
    
    switch( gRFAL.TxRx.state )
    {
        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_IDLE:
            /* Nothing to do */
            gRFAL.TxRx.state = RFAL_TXRX_STATE_TX_WAIT_GT ;
            /* fall through */

        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_WAIT_GT:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            if( !rfalIsGTExpired() )
            {
                break;
            }
            
            rfalTimerDestroy( gRFAL.tmr.GT );
            gRFAL.tmr.GT = RFAL_TIMING_NONE;
            
            gRFAL.TxRx.state = RFAL_TXRX_STATE_TX_WAIT_FDT;
            /* fall through */
            
        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_WAIT_FDT:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            /* In Passive communications GPT is used to measure FDT Poll */
            if( st25r200IsGPTRunning() )
            {                
               break;
            }
            
            gRFAL.TxRx.state = RFAL_TXRX_STATE_TX_PREP_TX;
            /* fall through */
        
        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_PREP_TX:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            /* Clear FIFO, Clear and Enable the Interrupts */
            rfalPrepareTransceive( );

            /* ST25R200 has a fixed FIFO water level */
            gRFAL.fifo.expWL = RFAL_FIFO_OUT_WL;
        
            /* Calculate the bytes needed to be Written into FIFO (a incomplete byte will be added as 1byte) */
            gRFAL.fifo.bytesTotal = (uint16_t)rfalCalcNumBytes(gRFAL.TxRx.ctx.txBufLen);
            
            /* Set the number of full bytes and bits to be transmitted */
            st25r200SetNumTxBits( gRFAL.TxRx.ctx.txBufLen );
            
            /* Load FIFO with total length or FIFO's maximum */
            gRFAL.fifo.bytesWritten = RFAL_MIN( gRFAL.fifo.bytesTotal, ST25R200_FIFO_DEPTH );
            st25r200WriteFifo( gRFAL.TxRx.ctx.txBuf, gRFAL.fifo.bytesWritten );
        
            /* Check if Observation Mode is enabled and set it on ST25R */
            rfalCheckEnableObsModeTx();
            
            gRFAL.TxRx.state = RFAL_TXRX_STATE_TX_TRANSMIT;
            /* fall through */
            
            
        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_TRANSMIT:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */            

            /*******************************************************************************/
            /* Execute Sync Transceive Callback                                             */
            /*******************************************************************************/
            if( gRFAL.callbacks.syncTxRx != NULL )
            {
                /* If set, wait for sync callback to signal sync/trigger transmission */
                if( !gRFAL.callbacks.syncTxRx() )
                {
                    break;
                }
            }
            
            /*******************************************************************************/
            /* Trigger/Start transmission                                                  */
            st25r200ExecuteCommand( ST25R200_CMD_TRANSMIT );
             
            /* Check if a WL level is expected or TXE should come */
            gRFAL.TxRx.state = (( gRFAL.fifo.bytesWritten < gRFAL.fifo.bytesTotal ) ? RFAL_TXRX_STATE_TX_WAIT_WL : RFAL_TXRX_STATE_TX_WAIT_TXE);
            break;

        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_WAIT_WL:
            
            irqs = st25r200GetInterrupt( (ST25R200_IRQ_MASK_WL | ST25R200_IRQ_MASK_TXE) );
            if( irqs == ST25R200_IRQ_MASK_NONE )
            {
               break;  /* No interrupt to process */
            }
            
            if( ((irqs & ST25R200_IRQ_MASK_WL) != 0U) && ((irqs & ST25R200_IRQ_MASK_TXE) == 0U) )
            {
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_TX_RELOAD_FIFO;
            }
            else
            {
                gRFAL.TxRx.status = RFAL_ERR_IO;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_TX_FAIL;
                break;
            }
            
            /* fall through */
            
        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_RELOAD_FIFO:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            /* Load FIFO with the remaining length or maximum available */
            tmp = RFAL_MIN( (gRFAL.fifo.bytesTotal - gRFAL.fifo.bytesWritten), gRFAL.fifo.expWL);       /* tmp holds the number of bytes written on this iteration */
            st25r200WriteFifo( &gRFAL.TxRx.ctx.txBuf[gRFAL.fifo.bytesWritten], tmp );
            
            /* Update total written bytes to FIFO */
            gRFAL.fifo.bytesWritten += tmp;
            
            /* Check if a WL level is expected or TXE should come */
            gRFAL.TxRx.state = (( gRFAL.fifo.bytesWritten < gRFAL.fifo.bytesTotal ) ? RFAL_TXRX_STATE_TX_WAIT_WL : RFAL_TXRX_STATE_TX_WAIT_TXE);
            break;
            
            
        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_WAIT_TXE:
           
            irqs = st25r200GetInterrupt( (ST25R200_IRQ_MASK_WL | ST25R200_IRQ_MASK_TXE) );
            if( irqs == ST25R200_IRQ_MASK_NONE )
            {
               break;  /* No interrupt to process */
            }
                        
            
            if( (irqs & ST25R200_IRQ_MASK_TXE) != 0U )
            {
                gRFAL.TxRx.state = RFAL_TXRX_STATE_TX_DONE;
            }
            else if( (irqs & ST25R200_IRQ_MASK_WL) != 0U )
            {
                break;  /* Ignore ST25R200 FIFO WL if total TxLen is already on the FIFO */
            }
            else
            {
               gRFAL.TxRx.status = RFAL_ERR_IO;
               gRFAL.TxRx.state  = RFAL_TXRX_STATE_TX_FAIL;
               break;
            }
            
            /* fall through */
           
                           
        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_DONE:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            /* If no rxBuf is provided do not wait/expect Rx */
            if( gRFAL.TxRx.ctx.rxBuf == NULL )
            {
                /* Check if Observation Mode was enabled and disable it on ST25R */
                rfalCheckDisableObsMode();
                
                /* Clean up Transceive */
                rfalCleanupTransceive();
                                
                gRFAL.TxRx.status = RFAL_ERR_NONE;
                gRFAL.TxRx.state  =  RFAL_TXRX_STATE_IDLE;
                break;
            }
            
            rfalCheckEnableObsModeRx();
            
            /* Goto Rx */
            gRFAL.TxRx.state  =  RFAL_TXRX_STATE_RX_IDLE;
            break;
           
        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_FAIL:
            
            /* Error should be assigned by previous state */
            if( gRFAL.TxRx.status == RFAL_ERR_BUSY )
            {                
                gRFAL.TxRx.status = RFAL_ERR_SYSTEM;
            }
            
            /* Check if Observation Mode was enabled and disable it on ST25R */
            rfalCheckDisableObsMode();
            
            /* Clean up Transceive */
            rfalCleanupTransceive();
            
            gRFAL.TxRx.state = RFAL_TXRX_STATE_IDLE;
            break;
        
        /*******************************************************************************/
        default:
            gRFAL.TxRx.status = RFAL_ERR_SYSTEM;
            gRFAL.TxRx.state  = RFAL_TXRX_STATE_TX_FAIL;
            break;
    }
}


/*******************************************************************************/
static void rfalTransceiveRx( void )
{
    uint32_t irqs;
    uint16_t tmp;
    uint16_t aux;
    uint8_t  reg;
    
    irqs = ST25R200_IRQ_MASK_NONE;
    
    if( gRFAL.TxRx.state != gRFAL.TxRx.lastState )
    {
        gRFAL.TxRx.lastState = gRFAL.TxRx.state;
    }
    
    switch( gRFAL.TxRx.state )
    {
        /*******************************************************************************/
        case RFAL_TXRX_STATE_RX_IDLE:
            
            /* Clear rx counters */
            gRFAL.fifo.bytesWritten   = 0;            /* Total bytes written on RxBuffer         */
            gRFAL.fifo.bytesTotal     = 0;            /* Total bytes in FIFO will now be from Rx */
            if( gRFAL.TxRx.ctx.rxRcvdLen != NULL )
            {
                *gRFAL.TxRx.ctx.rxRcvdLen = 0;
            }
           
            gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_WAIT_RXS;
            
            /* fall through */
           
        /*******************************************************************************/
        case RFAL_TXRX_STATE_RX_WAIT_RXS:    /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            /*******************************************************************************/
            irqs = st25r200GetInterrupt( (ST25R200_IRQ_MASK_RXS | ST25R200_IRQ_MASK_NRE ) );
            if( irqs == ST25R200_IRQ_MASK_NONE )
            {
                break;  /* No interrupt to process */
            }
            
            /* Only raise Timeout if NRE is detected with no Rx Start (NRT EMD mode) */
            if( ((irqs & ST25R200_IRQ_MASK_NRE) != 0U) && ((irqs & ST25R200_IRQ_MASK_RXS) == 0U) )
            {
                gRFAL.TxRx.status = RFAL_ERR_TIMEOUT;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;                
                break;
            }
            
            if( (irqs & ST25R200_IRQ_MASK_RXS) != 0U )
            {
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_WAIT_RXE;
            }
            else
            {
                gRFAL.TxRx.status = RFAL_ERR_IO;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
                break;
            }
            
            /* Remove NRE that might appear together (NRT EMD mode), and remove RXS */
            irqs &= ~(ST25R200_IRQ_MASK_RXS | ST25R200_IRQ_MASK_NRE);
            
            /* fall through */
            
        /*******************************************************************************/    
        case RFAL_TXRX_STATE_RX_WAIT_RXE:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            irqs |= st25r200GetInterrupt( ( ST25R200_IRQ_MASK_RXE  | ST25R200_IRQ_MASK_WL | ST25R200_IRQ_MASK_RX_REST ) );
            if( irqs == ST25R200_IRQ_MASK_NONE )
            {
                break;  /* No interrupt to process */
            }
            
            if( ((irqs & ST25R200_IRQ_MASK_RX_REST) != 0U) && ((irqs & ST25R200_IRQ_MASK_RXE) == 0U) )
            {
                /* RX_REST indicates that Receiver has been reseted due to EMD, therefore a RXS + RXE should *
                 * follow if a good reception is followed within the valid initial timeout                   */
                
                /* Check whether NRT has expired already, if so signal a timeout */
                if( st25r200GetInterrupt( ST25R200_IRQ_MASK_NRE ) != 0U )
                {
                    gRFAL.TxRx.status = RFAL_ERR_TIMEOUT;
                    gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
                    break;
                }
                
                st25r200ReadRegister( ST25R200_REG_STATUS, &reg );
                if( ((reg & ST25R200_REG_STATUS_nrt_on) == 0U) )
                {
                    gRFAL.TxRx.status = RFAL_ERR_TIMEOUT;
                    gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
                    break;
                }
                
                /* Discard any previous RXS and transmission errors */
                st25r200GetInterrupt( (ST25R200_IRQ_MASK_RXS | ST25R200_IRQ_MASK_SFE | ST25R200_IRQ_MASK_HFE | ST25R200_IRQ_MASK_CRC) );
                
                /* Check whether a following reception has already started and is ongoing */
                if( ((reg & ST25R200_REG_STATUS_rx_act) != 0U) )
                {
                    gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_WAIT_RXE;
                    break;
                }
                
                /*  NRT is still running and reception is not currently active.                  *
                 *  Unable to determine whether the receiver has been enabled already, because   *
                 *  upon RX_REST, rx_on takes ~30us to become high again.                        *
                 *  Guarantee this timming to ensure reception has already taken place           */
                if( (!rfalWaitRxOn()) )
                {
                    gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_WAIT_RXE;
                    break;
                }
                
                gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_WAIT_RXS;
                break;
            }
            
            if( ((irqs & ST25R200_IRQ_MASK_WL) != 0U) && ((irqs & ST25R200_IRQ_MASK_RXE) == 0U) )
            {
                gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_READ_FIFO;
                break;
            }
            
            /* After RXE retrieve and check for any error irqs */
            irqs |= st25r200GetInterrupt( (ST25R200_IRQ_MASK_CRC | ST25R200_IRQ_MASK_PAR | ST25R200_IRQ_MASK_HFE | ST25R200_IRQ_MASK_SFE | ST25R200_IRQ_MASK_COL) );
            
            gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_ERR_CHECK;
            /* fall through */
            
            
        /*******************************************************************************/    
        case RFAL_TXRX_STATE_RX_ERR_CHECK:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            if( (irqs & ST25R200_IRQ_MASK_HFE) != 0U )
            {
                gRFAL.TxRx.status = RFAL_ERR_FRAMING;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_READ_DATA;
                
                /* Check if there's a specific error handling for this */
                rfalErrorHandling();
                break;
            }
            else if( ((irqs & ST25R200_IRQ_MASK_SFE) != 0U) )
            {
                gRFAL.TxRx.status = RFAL_ERR_FRAMING;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_READ_DATA;
                
                /* Check if there's a specific error handling for this */
                rfalErrorHandling();
                break;
            }
            else if( (irqs & ST25R200_IRQ_MASK_PAR) != 0U )
            {
                gRFAL.TxRx.status = RFAL_ERR_PAR;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_READ_DATA;
                
                /* Check if there's a specific error handling for this */
                rfalErrorHandling();
                break;
            }
            else if( (irqs & ST25R200_IRQ_MASK_COL) != 0U )
            {
                gRFAL.TxRx.status = RFAL_ERR_RF_COLLISION;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_READ_DATA;
                
                /* Check if there's a specific error handling for this */
                rfalErrorHandling();
                break;
            }
            else if( (irqs & ST25R200_IRQ_MASK_CRC) != 0U )
            {
                gRFAL.TxRx.status = RFAL_ERR_CRC;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_READ_DATA;
                
                /* Check if there's a specific error handling for this */
                rfalErrorHandling();
                break;
            }
            else if( (irqs & ST25R200_IRQ_MASK_RXE) != 0U )
            {
                /* Reception ended without any error indication,                  *
                 * check FIFO status for malformed or incomplete frames           */
                
                /* Check if the reception ends with an incomplete byte (residual bits) */
                if( rfalFIFOStatusIsIncompleteByte() )
                {
                   gRFAL.TxRx.status = RFAL_ERR_INCOMPLETE_BYTE;
                }
                /* Check if the reception ends missing parity bit */
                else if( rfalFIFOStatusIsMissingPar() )
                {
                   gRFAL.TxRx.status = RFAL_ERR_FRAMING;
                }
                else
                {
                    /* MISRA 15.7 - Empty else */
                }
                
                gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_READ_DATA;
            }
            else
            {
                gRFAL.TxRx.status = RFAL_ERR_IO;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
                break;
            }
                        
            /* fall through */
            
            
        /*******************************************************************************/    
        case RFAL_TXRX_STATE_RX_READ_DATA:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
                      
            tmp = rfalFIFOStatusGetNumBytes();
                        
            /*******************************************************************************/
            /* Check if CRC should not be placed in rxBuf                                  */
            if( ((gRFAL.TxRx.ctx.flags & (uint32_t)RFAL_TXRX_FLAGS_CRC_RX_KEEP) == 0U) )
            {
                /* if received frame was bigger than CRC */
                if( (uint16_t)(gRFAL.fifo.bytesTotal + tmp) > 0U )
                {
                    /* By default CRC will not be placed into the rxBuffer */
                    if( ( tmp > RFAL_CRC_LEN) )  
                    {
                        tmp -= RFAL_CRC_LEN;
                    }
                    /* If the CRC was already placed into rxBuffer (due to WL interrupt where CRC was already in FIFO Read)
                     * cannot remove it from rxBuf. Can only remove it from rxBufLen not indicate the presence of CRC    */ 
                    else if(gRFAL.fifo.bytesTotal > RFAL_CRC_LEN)                       
                    {                        
                        gRFAL.fifo.bytesTotal -= RFAL_CRC_LEN;
                    }
                    else
                    {
                        /* MISRA 15.7 - Empty else */
                    }
                }
            }
            
            gRFAL.fifo.bytesTotal += tmp;                    /* add to total bytes counter */
            
            /*******************************************************************************/
            /* Check if remaining bytes fit on the rxBuf available                         */
            if( gRFAL.fifo.bytesTotal > rfalConvBitsToBytes(gRFAL.TxRx.ctx.rxBufLen) )
            {
                tmp = (uint16_t)( rfalConvBitsToBytes(gRFAL.TxRx.ctx.rxBufLen) - gRFAL.fifo.bytesWritten);
                
                /* Transmission errors have precedence over buffer error */
                if( gRFAL.TxRx.status == RFAL_ERR_BUSY )
                {
                    gRFAL.TxRx.status = RFAL_ERR_NOMEM;
                }
            }

            /*******************************************************************************/
            /* Retrieve remaining bytes from FIFO to rxBuf, and assign total length rcvd   */
            st25r200ReadFifo( &gRFAL.TxRx.ctx.rxBuf[gRFAL.fifo.bytesWritten], tmp);
            if( gRFAL.TxRx.ctx.rxRcvdLen != NULL )
            {
                (*gRFAL.TxRx.ctx.rxRcvdLen) = (uint16_t)rfalConvBytesToBits( gRFAL.fifo.bytesTotal );
                if( rfalFIFOStatusIsIncompleteByte() )
                {
                    (*gRFAL.TxRx.ctx.rxRcvdLen) -= (RFAL_BITS_IN_BYTE - rfalFIFOGetNumIncompleteBits());
                }
            }
            
            /*******************************************************************************/
            /* If an error as been marked/detected don't fall into to RX_DONE  */
            if( gRFAL.TxRx.status != RFAL_ERR_BUSY )
            {
                gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_FAIL;
                break;
            }
            
            gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_DONE;
            /* fall through */
                            
            
        /*******************************************************************************/    
        case RFAL_TXRX_STATE_RX_DONE:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            /* Check if Observation Mode was enabled and disable it on ST25R */
            rfalCheckDisableObsMode();
            
            /* Clean up Transceive */
            rfalCleanupTransceive();
            
            gRFAL.TxRx.status = RFAL_ERR_NONE;
            gRFAL.TxRx.state  = RFAL_TXRX_STATE_IDLE;
            break;
            
            
        /*******************************************************************************/    
        case RFAL_TXRX_STATE_RX_READ_FIFO:
            
            tmp = rfalFIFOStatusGetNumBytes();
            gRFAL.fifo.bytesTotal += tmp;
            
            /*******************************************************************************/
            /* Calculate the amount of bytes that still fits in rxBuf                      */
            aux = (( gRFAL.fifo.bytesTotal > rfalConvBitsToBytes(gRFAL.TxRx.ctx.rxBufLen) ) ? (rfalConvBitsToBytes(gRFAL.TxRx.ctx.rxBufLen) - gRFAL.fifo.bytesWritten) : tmp);
            
            /*******************************************************************************/
            /* Retrieve incoming bytes from FIFO to rxBuf, and store already read amount   */
            st25r200ReadFifo( &gRFAL.TxRx.ctx.rxBuf[gRFAL.fifo.bytesWritten], aux);
            gRFAL.fifo.bytesWritten += aux;
            
            /*******************************************************************************/
            /* If the bytes already read were not the full FIFO WL, dump the remaining     *
             * FIFO so that ST25R can continue with reception                              */
            if( aux < tmp )
            {
                st25r200ReadFifo( NULL, (tmp - aux) );
            }
            
            rfalFIFOStatusClear();
            gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_WAIT_RXE;
            break;
            
            
        /*******************************************************************************/    
        case RFAL_TXRX_STATE_RX_FAIL:
            
            /* Check if Observation Mode was enabled and disable it on ST25R */
            rfalCheckDisableObsMode();
            
            /* Clean up Transceive */
            rfalCleanupTransceive();
            
            /* Error should be assigned by previous state */
            if( gRFAL.TxRx.status == RFAL_ERR_BUSY )
            {                
                gRFAL.TxRx.status = RFAL_ERR_SYSTEM;
            }
            
            gRFAL.TxRx.state = RFAL_TXRX_STATE_IDLE;
            break;
            
        /*******************************************************************************/
        default:
            gRFAL.TxRx.status = RFAL_ERR_SYSTEM;
            gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
            break;           
    }    
}


/*******************************************************************************/
static bool rfalWaitRxOn( void )
{
    uint8_t n;
    
    for( n = 0; n < RFAL_RX_REST_ON_WAIT; n++ )
    {
        if( st25r200CheckReg( ST25R200_REG_STATUS, ST25R200_REG_STATUS_rx_on, ST25R200_REG_STATUS_rx_on ) )
        {
            return true;
        }
    }
    
    return false;
}



/*******************************************************************************/
static void rfalFIFOStatusUpdate( void )
{
    if(gRFAL.fifo.status[RFAL_FIFO_STATUS_REG2] == RFAL_FIFO_STATUS_INVALID)
    {
        st25r200ReadMultipleRegisters( ST25R200_REG_FIFO_STATUS1, gRFAL.fifo.status, ST25R200_FIFO_STATUS_LEN );
    }
}


/*******************************************************************************/
static void rfalFIFOStatusClear( void )
{
    gRFAL.fifo.status[RFAL_FIFO_STATUS_REG2] = RFAL_FIFO_STATUS_INVALID;
}


/*******************************************************************************/
static uint16_t rfalFIFOStatusGetNumBytes( void )
{
    uint16_t result;
    
    rfalFIFOStatusUpdate();
    
    result  = ((((uint16_t)gRFAL.fifo.status[RFAL_FIFO_STATUS_REG2] & ST25R200_REG_FIFO_STATUS2_fifo_b8) >> ST25R200_REG_FIFO_STATUS2_fifo_b_shift) << RFAL_BITS_IN_BYTE);
    result |= (((uint16_t)gRFAL.fifo.status[RFAL_FIFO_STATUS_REG1]) & 0x00FFU);
    return result;
}


/*******************************************************************************/
static bool rfalFIFOStatusIsIncompleteByte( void )
{
    rfalFIFOStatusUpdate();
    return ((gRFAL.fifo.status[RFAL_FIFO_STATUS_REG2] & ST25R200_REG_FIFO_STATUS2_fifo_lb_mask) != 0U);
}


/*******************************************************************************/
static bool rfalFIFOStatusIsMissingPar( void )
{
    rfalFIFOStatusUpdate();
    return ((gRFAL.fifo.status[RFAL_FIFO_STATUS_REG2] & ST25R200_REG_FIFO_STATUS2_np_lb) != 0U);
}


/*******************************************************************************/
static uint8_t rfalFIFOGetNumIncompleteBits( void )
{
    rfalFIFOStatusUpdate();
    return ((gRFAL.fifo.status[RFAL_FIFO_STATUS_REG2] & ST25R200_REG_FIFO_STATUS2_fifo_lb_mask) >> ST25R200_REG_FIFO_STATUS2_fifo_lb_shift);
}


#if RFAL_FEATURE_NFCA

/*******************************************************************************/
ReturnCode rfalISO14443ATransceiveShortFrame( rfal14443AShortFrameCmd txCmd, uint8_t* rxBuf, uint8_t rxBufLen, uint16_t* rxRcvdLen, uint32_t fwt )
{
    rfalTransceiveContext ctx;
    ReturnCode            ret;
    uint8_t               cmd;

    /* Check if RFAL is properly initialized */
    if( (!st25r200IsTxEnabled()) || (gRFAL.state < RFAL_STATE_MODE_SET) || (( gRFAL.mode != RFAL_MODE_POLL_NFCA ) && ( gRFAL.mode != RFAL_MODE_POLL_NFCA_T1T )) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check for valid parameters */
    if( (rxBuf == NULL) || (rxRcvdLen == NULL) || (fwt == RFAL_FWT_NONE) )
    {
        return RFAL_ERR_PARAM;
    }
    
    /*******************************************************************************/
    /* Enable collision recognition */
    st25r200SetRegisterBits( ST25R200_REG_PROTOCOL_RX1, ST25R200_REG_PROTOCOL_RX1_antcl );
    
    cmd = (uint8_t)txCmd;
    ctx.txBuf    = &cmd;
    ctx.txBufLen = RFAL_ISO14443A_SHORTFRAME_LEN;

    
    /*******************************************************************************/        
    /* Prepare for Transceive, Receive only (bypass Tx states) */
    ctx.flags     = ( (uint32_t)RFAL_TXRX_FLAGS_CRC_TX_MANUAL | (uint32_t)RFAL_TXRX_FLAGS_PAR_TX_NONE | (uint32_t)RFAL_TXRX_FLAGS_CRC_RX_KEEP | (uint32_t)RFAL_TXRX_FLAGS_CRC_RX_MANUAL );
    ctx.rxBuf     = rxBuf;
    ctx.rxBufLen  = rxBufLen;
    ctx.rxRcvdLen = rxRcvdLen;
    ctx.fwt       = fwt;
    
    RFAL_EXIT_ON_ERR( ret, rfalStartTransceive( &ctx ) );
    
    /*******************************************************************************/
    /* Run Transceive blocking */
    ret = rfalTransceiveRunBlockingTx();
    if( ret == RFAL_ERR_NONE)
    {
        ret = rfalTransceiveBlockingRx();
    }
    
    /* Disable collision detection again */
    st25r200ClrRegisterBits( ST25R200_REG_PROTOCOL_RX1, ST25R200_REG_PROTOCOL_RX1_antcl );
    /*******************************************************************************/
        
    return ret;
}


/*******************************************************************************/
ReturnCode rfalISO14443ATransceiveAnticollisionFrame( uint8_t *buf, uint8_t *bytesToSend, uint8_t *bitsToSend, uint16_t *rxLength, uint32_t fwt )
{
    ReturnCode ret;

    RFAL_EXIT_ON_ERR( ret, rfalISO14443AStartTransceiveAnticollisionFrame( buf, bytesToSend, bitsToSend, rxLength, fwt ) );
    rfalRunBlocking( ret, rfalISO14443AGetTransceiveAnticollisionFrameStatus() );
    
    return ret;
}


/*******************************************************************************/
ReturnCode rfalISO14443AStartTransceiveAnticollisionFrame( uint8_t *buf, uint8_t *bytesToSend, uint8_t *bitsToSend, uint16_t *rxLength, uint32_t fwt )
{
    ReturnCode            ret;
    rfalTransceiveContext ctx;
    
    /* Check if RFAL is properly initialized */
    if( (gRFAL.state < RFAL_STATE_MODE_SET) || ( gRFAL.mode != RFAL_MODE_POLL_NFCA ) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check for valid parameters */
    if( (buf == NULL) || (bytesToSend == NULL) || (bitsToSend == NULL) || (rxLength == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
    
    /*******************************************************************************/
    /* Set speficic Analog Config for Anticolission if needed */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_ANTICOL) );
    
    
    /*******************************************************************************/
    /* Enable collision recognition and place response next to request*/
    st25r200SetRegisterBits( ST25R200_REG_PROTOCOL_RX1, (ST25R200_REG_PROTOCOL_RX1_antcl | ST25R200_REG_PROTOCOL_RX1_rx_nbtx) );
    
    
    /*******************************************************************************/
    /* Prepare for Transceive                                                      */
    ctx.flags     = ( (uint32_t)RFAL_TXRX_FLAGS_CRC_TX_MANUAL | (uint32_t)RFAL_TXRX_FLAGS_CRC_RX_KEEP | (uint32_t)RFAL_TXRX_FLAGS_CRC_RX_MANUAL | (uint32_t)RFAL_TXRX_FLAGS_AGC_ON );
    ctx.txBuf     = buf;
    ctx.txBufLen  = (uint16_t)(rfalConvBytesToBits( *bytesToSend ) + *bitsToSend );
    ctx.rxBuf     = &buf[*bytesToSend];
    ctx.rxBufLen  = (uint16_t)rfalConvBytesToBits( RFAL_ISO14443A_SDD_RES_LEN );
    ctx.rxRcvdLen = rxLength;
    ctx.fwt       = fwt;
    
    RFAL_EXIT_ON_ERR( ret, rfalStartTransceive( &ctx ) );
    
    /* Additionally enable bit collision interrupt */
    st25r200GetInterrupt( ST25R200_IRQ_MASK_COL );
    st25r200EnableInterrupts( ST25R200_IRQ_MASK_COL );
    
    /*******************************************************************************/
    gRFAL.nfcaData.collByte = 0;
    
    /* Save the collision byte */
    if ((*bitsToSend) > 0U)
    {
        buf[(*bytesToSend)] <<= (RFAL_BITS_IN_BYTE - (*bitsToSend));
        buf[(*bytesToSend)] >>= (RFAL_BITS_IN_BYTE - (*bitsToSend));
        gRFAL.nfcaData.collByte = buf[(*bytesToSend)];
    }
    
    gRFAL.nfcaData.buf         = buf;
    gRFAL.nfcaData.bytesToSend = bytesToSend;
    gRFAL.nfcaData.bitsToSend  = bitsToSend;
    gRFAL.nfcaData.rxLength    = rxLength;
    
    /*******************************************************************************/
    /* Run Transceive Tx */
    return rfalTransceiveRunBlockingTx();
}


/*******************************************************************************/
ReturnCode rfalISO14443AGetTransceiveAnticollisionFrameStatus( void )
{
    ReturnCode   ret;
    uint8_t      collData;
    
    RFAL_EXIT_ON_BUSY( ret, rfalGetTransceiveStatus() );
    
    /*******************************************************************************/
    if ((*gRFAL.nfcaData.bitsToSend) > 0U)
    {
       gRFAL.nfcaData.buf[(*gRFAL.nfcaData.bytesToSend)] >>= (*gRFAL.nfcaData.bitsToSend);
       gRFAL.nfcaData.buf[(*gRFAL.nfcaData.bytesToSend)] <<= (*gRFAL.nfcaData.bitsToSend);
       gRFAL.nfcaData.buf[(*gRFAL.nfcaData.bytesToSend)] |= gRFAL.nfcaData.collByte;
    }

    if( (RFAL_ERR_RF_COLLISION == ret) )
    {                      
       /* Read out collision register */
       st25r200ReadRegister( ST25R200_REG_COLLISION, &collData);

       (*gRFAL.nfcaData.bytesToSend) = ((collData >> ST25R200_REG_COLLISION_c_byte_shift) & 0x0FU); /* 4-bits Byte information */
       (*gRFAL.nfcaData.bitsToSend)  = ((collData >> ST25R200_REG_COLLISION_c_bit_shift)  & 0x07U); /* 3-bits bit information  */
    }
    
   
    /*******************************************************************************/
    /* Disable Collision interrupt */
    st25r200DisableInterrupts( (ST25R200_IRQ_MASK_COL) );
    
    /* Disable collision detection again */
    st25r200ClrRegisterBits( ST25R200_REG_PROTOCOL_RX1, (ST25R200_REG_PROTOCOL_RX1_antcl | ST25R200_REG_PROTOCOL_RX1_rx_nbtx) );
    /*******************************************************************************/
    
    /* Restore common Analog configurations for this mode */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | rfalConvBR2ACBR(gRFAL.txBR) | RFAL_ANALOG_CONFIG_TX) );
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | rfalConvBR2ACBR(gRFAL.rxBR) | RFAL_ANALOG_CONFIG_RX) );
    
    return ret;
}

#endif /* RFAL_FEATURE_NFCA */

#if RFAL_FEATURE_NFCV

/*******************************************************************************/
ReturnCode rfalISO15693TransceiveAnticollisionFrame( uint8_t *txBuf, uint8_t txBufLen, uint8_t *rxBuf, uint8_t rxBufLen, uint16_t *actLen )
{
    ReturnCode            ret;
    rfalTransceiveContext ctx;
    
    /* Check if RFAL is properly initialized */
    if( (gRFAL.state < RFAL_STATE_MODE_SET) || ( gRFAL.mode != RFAL_MODE_POLL_NFCV ) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /*******************************************************************************/
    /* Set speficic Analog Config for Anticolission if needed */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_ANTICOL) );
    
    
    /*******************************************************************************/
    /* Enable anti collision to recognise bit collisions  */
    st25r200SetRegisterBits( ST25R200_REG_PROTOCOL_RX1, ST25R200_REG_PROTOCOL_RX1_antcl );
    
    /* REMARK: Flag RFAL_TXRX_FLAGS_NFCV_FLAG_MANUAL disregarded */
    /*******************************************************************************/
    /* Prepare for Transceive  */
    ctx.flags     = (RFAL_TXRX_FLAGS_DEFAULT | (uint32_t)RFAL_TXRX_FLAGS_AGC_ON); /* Disable Automatic Gain Control (AGC) for better detection of collision */
    ctx.txBuf     = txBuf;
    ctx.txBufLen  = (uint16_t)rfalConvBytesToBits(txBufLen);
    ctx.rxBuf     = rxBuf;
    ctx.rxBufLen  = (uint16_t)rfalConvBytesToBits(rxBufLen);
    ctx.rxRcvdLen = actLen;
    ctx.fwt       = RFAL_ISO15693_FWT;
    
    RFAL_EXIT_ON_ERR( ret, rfalStartTransceive( &ctx ) );
    
    /* Additionally enable bit collision interrupt */
    st25r200GetInterrupt( ST25R200_IRQ_MASK_COL );
    st25r200EnableInterrupts( ST25R200_IRQ_MASK_COL );
    
    /*******************************************************************************/
    /* Run Transceive blocking */
    ret = rfalTransceiveRunBlockingTx();
    if( ret == RFAL_ERR_NONE)
    {
        ret = rfalTransceiveBlockingRx();
    }
    
    /* REMARK: CRC is being returned to keep alignment with ST25R3911/ST25R3916 (due to stream mode limitations) */
    if( ret == RFAL_ERR_NONE )
    {
        (*ctx.rxRcvdLen) += (uint16_t)rfalConvBytesToBits(RFAL_CRC_LEN);
    }   
    
    /*******************************************************************************/
    /* Disable Collision interrupt */
    st25r200DisableInterrupts( (ST25R200_IRQ_MASK_COL) );
    
    /* Disable collision detection again */
    st25r200ClrRegisterBits( ST25R200_REG_PROTOCOL_RX1, ST25R200_REG_PROTOCOL_RX1_antcl );
    /*******************************************************************************/
    
    /* Restore common Analog configurations for this mode */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | rfalConvBR2ACBR(gRFAL.txBR) | RFAL_ANALOG_CONFIG_TX) );
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | rfalConvBR2ACBR(gRFAL.rxBR) | RFAL_ANALOG_CONFIG_RX) );

    return ret;
}

/*******************************************************************************/
ReturnCode rfalISO15693TransceiveEOFAnticollision( uint8_t *rxBuf, uint8_t rxBufLen, uint16_t *actLen )
{
    ReturnCode ret;
    
    RFAL_EXIT_ON_ERR( ret, rfalISO15693TransceiveEOF( rxBuf, rxBufLen, actLen ) );
    (*actLen) = (uint16_t)rfalConvBytesToBits( (*actLen) );
    
    return ret;
}

/*******************************************************************************/
ReturnCode rfalISO15693TransceiveEOF( uint8_t *rxBuf, uint16_t rxBufLen, uint16_t *actLen )
{
    ReturnCode ret;

    /* Check if RFAL is properly initialized */
    if( (!st25r200IsTxEnabled()) || (gRFAL.state < RFAL_STATE_MODE_SET) || ( gRFAL.mode != RFAL_MODE_POLL_NFCV ) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check for valid parameters */
    if( (rxBuf == NULL) || (actLen == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
    
    
    /*******************************************************************************/
    /* Wait for GT and FDT */
    while( !rfalIsGTExpired() )      { /* MISRA 15.6: mandatory brackets */ };
    while( st25r200IsGPTRunning() )  { /* MISRA 15.6: mandatory brackets */ };

    rfalTimerDestroy( gRFAL.tmr.GT );
    gRFAL.tmr.GT = RFAL_TIMING_NONE;
    
    /*******************************************************************************/        
    /* Prepare for Transceive, Receive only (bypass Tx states) */
    gRFAL.TxRx.ctx.flags     = ( (uint32_t)RFAL_TXRX_FLAGS_CRC_TX_MANUAL );
    gRFAL.TxRx.ctx.rxBuf     = rxBuf;
    gRFAL.TxRx.ctx.rxBufLen  = (uint16_t)rfalConvBytesToBits(rxBufLen);
    gRFAL.TxRx.ctx.rxRcvdLen = actLen;
    gRFAL.TxRx.ctx.fwt       = RFAL_ISO15693_FWT;
    
    /*******************************************************************************/
    /* ISO15693 EOF frame shall come after Inventory or Write alike command        */
    /* FWT , FDT(Poll), FDT(Listen) must be loaded in the previous transceive      */
    /*******************************************************************************/
    rfalPrepareTransceive();
    
    /*******************************************************************************/
    /* Enable anti collision to recognise bit collisions  */
    st25r200SetRegisterBits( ST25R200_REG_PROTOCOL_RX1, ST25R200_REG_PROTOCOL_RX1_antcl );
    
    /* Also enable bit collision interrupt */
    st25r200GetInterrupt( ST25R200_IRQ_MASK_COL );
    st25r200EnableInterrupts( ST25R200_IRQ_MASK_COL );
    
    /* Check if Observation Mode is enabled and set it on ST25R */
    rfalCheckEnableObsModeTx();
    
    /* Send EOF */
    st25r200ExecuteCommand( ST25R200_CMD_TRANSMIT_EOF );
    
    /* Wait for TXE */
    if( st25r200WaitForInterruptsTimed( ST25R200_IRQ_MASK_TXE, (uint16_t)RFAL_MAX( rfalConv1fcToMs( RFAL_ISO15693_FWT ), RFAL_ST25R200_SW_TMR_MIN_1MS ) ) == 0U )
    {
        ret = RFAL_ERR_IO;
    }
    else
    {
        /* Check if Observation Mode is enabled and set it on ST25R */
        rfalCheckEnableObsModeRx();
        
        /* Jump into a transceive Rx state for reception (bypass Tx states) */
        gRFAL.state       = RFAL_STATE_TXRX;
        gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_IDLE;
        gRFAL.TxRx.status = RFAL_ERR_BUSY;
        
        /* Execute Transceive Rx blocking */
        ret = rfalTransceiveBlockingRx();
    }
    
    
    /* Converts received length to bytes */
    (*actLen) = rfalConvBitsToBytes( (*actLen) );
    
    
    /* REMARK: CRC is being returned to keep alignment with ST25R3911/ST25R3916 (due to stream mode limitations) */
    if( ret == RFAL_ERR_NONE )
    {
        (*actLen) += RFAL_CRC_LEN;
    }  
    
    
    /* Disable collision detection again */
    st25r200ClrRegisterBits( ST25R200_REG_PROTOCOL_RX1, ST25R200_REG_PROTOCOL_RX1_antcl );
    
    /* Disable Collision interrupt */
    st25r200DisableInterrupts( (ST25R200_IRQ_MASK_COL) );
    
    return ret;
}

#endif /* RFAL_FEATURE_NFCV */


#if RFAL_FEATURE_NFCF

/*******************************************************************************/
ReturnCode rfalFeliCaPoll( rfalFeliCaPollSlots slots, uint16_t sysCode, uint8_t reqCode, rfalFeliCaPollRes* pollResList, uint8_t pollResListSize, uint8_t *devicesDetected, uint8_t *collisionsDetected )
{
    RFAL_NO_WARNING( slots );
    RFAL_NO_WARNING( sysCode );
    RFAL_NO_WARNING( reqCode );
    RFAL_NO_WARNING( pollResListSize );
    
    if( pollResList != NULL )
    {
        RFAL_MEMSET( pollResList, 0x00, sizeof(rfalFeliCaPollRes) );
    }
    
    if( devicesDetected != NULL )
    {
        (*devicesDetected) = 0U;
    }
    
    if( collisionsDetected != NULL )
    {
        (*collisionsDetected) = 0U;
    }

    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalStartFeliCaPoll( rfalFeliCaPollSlots slots, uint16_t sysCode, uint8_t reqCode, rfalFeliCaPollRes* pollResList, uint8_t pollResListSize, uint8_t *devicesDetected, uint8_t *collisionsDetected )
{
    RFAL_NO_WARNING( slots );
    RFAL_NO_WARNING( sysCode );
    RFAL_NO_WARNING( reqCode );
    RFAL_NO_WARNING( pollResListSize );
    
    if( pollResList != NULL )
    {
        RFAL_MEMSET( pollResList, 0x00, sizeof(rfalFeliCaPollRes) );
    }
    
    if( devicesDetected != NULL )
    {
        (*devicesDetected) = 0U;
    }
    
    if( collisionsDetected != NULL )
    {
        (*collisionsDetected) = 0U;
    }
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalGetFeliCaPollStatus( void )
{
    return RFAL_ERR_NOTSUPP;
}

#endif /* RFAL_FEATURE_NFCF */


/*****************************************************************************
 *  Listen Mode                                                              *  
 *****************************************************************************/

/*******************************************************************************/
bool rfalIsExtFieldOn( void )
{
    return st25r200IsExtFieldOn();
}

#if RFAL_FEATURE_LISTEN_MODE

/*******************************************************************************/
ReturnCode rfalListenStart( uint32_t lmMask, const rfalLmConfPA *confA, const rfalLmConfPB *confB, const rfalLmConfPF *confF, uint8_t *rxBuf, uint16_t rxBufLen, uint16_t *rxLen )
{   
    RFAL_NO_WARNING( lmMask );
    RFAL_NO_WARNING( confA );
    RFAL_NO_WARNING( confB );
    RFAL_NO_WARNING( confF );
    
    if( (rxBuf != NULL) && (rxBufLen > 0U) )
    {
        RFAL_MEMSET( rxBuf, 0x00, rfalConvBitsToBytes( rxBufLen ) );
    }
    
    if( rxLen != NULL )
    {
        (*rxLen) = 0U;
    }
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalListenStop( void )
{
    return RFAL_ERR_NONE;
}

/*******************************************************************************/
ReturnCode rfalListenSleepStart( rfalLmState sleepSt, uint8_t *rxBuf, uint16_t rxBufLen, uint16_t *rxLen )
{
    RFAL_NO_WARNING( sleepSt );
    RFAL_NO_WARNING( rxBufLen );
    
    if( (rxBuf != NULL) && (rxBufLen > 0U) )
    {
        RFAL_MEMSET( rxBuf, 0x00, rfalConvBitsToBytes( rxBufLen ) );
    }
    
    if( rxLen != NULL )
    {
        (*rxLen) = 0U;
    }
    
    return RFAL_ERR_NOTSUPP;
}

/*******************************************************************************/
rfalLmState rfalListenGetState( bool *dataFlag, rfalBitRate *lastBR )
{
    if( dataFlag != NULL )
    {
        (*dataFlag) = false;
    }
    
    if( lastBR != NULL )
    {
        (*lastBR) = RFAL_BR_KEEP;
    }
    
    return RFAL_LM_STATE_NOT_INIT;
}

/*******************************************************************************/
ReturnCode rfalListenSetState( rfalLmState newSt )
{
    RFAL_NO_WARNING( newSt );
    
    return RFAL_ERR_NOTSUPP;
}

#endif /* RFAL_FEATURE_LISTEN_MODE */


/*******************************************************************************
 *  Wake-Up Mode                                                               *
 *******************************************************************************/

#if RFAL_FEATURE_WAKEUP_MODE

/*******************************************************************************/
ReturnCode rfalWakeUpModeStart( const rfalWakeUpConfig *config )
{   
    uint8_t                aux;
    uint8_t                measI;
    uint8_t                measQ;
    uint32_t               irqs;
    
    
    /* The Wake-Up procedure is further detailled in Application Note: AN5993 */
    
    if( config == NULL )
    {
        gRFAL.wum.cfg.period       = RFAL_WUM_PERIOD_215MS;
        gRFAL.wum.cfg.irqTout      = false;
        gRFAL.wum.cfg.skipCal      = false;
        gRFAL.wum.cfg.skipReCal    = false;
        gRFAL.wum.cfg.delCal       = true;
        gRFAL.wum.cfg.delRef       = true;
        gRFAL.wum.cfg.autoAvg      = true;
        gRFAL.wum.cfg.measFil      = RFAL_WUM_MEAS_FIL_SLOW;
        gRFAL.wum.cfg.measDur      = RFAL_WUM_MEAS_DUR_44_28;
                                   
        gRFAL.wum.cfg.I.enabled    = true;
        gRFAL.wum.cfg.Q.enabled    = true;
                                   
        gRFAL.wum.cfg.I.delta      = 4U;
        gRFAL.wum.cfg.I.reference  = RFAL_WUM_REFERENCE_AUTO;
        gRFAL.wum.cfg.I.threshold  = ( (uint8_t)RFAL_WUM_TRE_ABOVE | (uint8_t)RFAL_WUM_TRE_BELOW );
        gRFAL.wum.cfg.I.aaWeight   = RFAL_WUM_AA_WEIGHT_32;
        gRFAL.wum.cfg.I.aaInclMeas = true;
        
        gRFAL.wum.cfg.Q.delta      = 4U;
        gRFAL.wum.cfg.Q.reference  = RFAL_WUM_REFERENCE_AUTO;
        gRFAL.wum.cfg.Q.threshold  = ( (uint8_t)RFAL_WUM_TRE_ABOVE | (uint8_t)RFAL_WUM_TRE_BELOW );
        gRFAL.wum.cfg.Q.aaWeight   = RFAL_WUM_AA_WEIGHT_32;
        gRFAL.wum.cfg.Q.aaInclMeas = true;
    }
    else
    {
        gRFAL.wum.cfg = *config;
    }

    /* Check for valid configuration */
    if( ( (gRFAL.wum.cfg.I.enabled == false) &&  (gRFAL.wum.cfg.Q.enabled == false) )   ||            /* Running wake-up requires one of the modes being enabled      */
        ( (gRFAL.wum.cfg.I.enabled == true)  &&  (gRFAL.wum.cfg.I.threshold == 0U) )    ||            /* If none of the treshold bits is set the WU will not executed */
        ( (gRFAL.wum.cfg.Q.enabled == true)  &&  (gRFAL.wum.cfg.Q.threshold == 0U) )
        )
    {
        return RFAL_ERR_PARAM;
    }


    irqs  = ST25R200_IRQ_MASK_NONE;
    measI = 0U;
    measQ = 0U;
    
    /* Disable Tx, Rx */
    st25r200TxRxOff();
    
    /* Set Analog configurations for Wake-up On event */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_WAKEUP_ON) );
    
    
    /*******************************************************************************/
    /* Prepare Wake-Up Timer Control Register */
    aux = (uint8_t)(((uint8_t)gRFAL.wum.cfg.period & 0x0FU) << ST25R200_REG_WAKEUP_CONF1_wut_shift);
    
    if( gRFAL.wum.cfg.irqTout )
    {
        aux  |= ST25R200_REG_WAKEUP_CONF1_wuti;
        irqs |= ST25R200_IRQ_MASK_WUT;
    }
    
    st25r200WriteRegister( ST25R200_REG_WAKEUP_CONF1, aux );
    
    
    /* Prepare Wake-Up  Control Register 2 */
    aux  = 0U;
    aux |= (uint8_t)( gRFAL.wum.cfg.skipReCal                           ? ST25R200_REG_WAKEUP_CONF2_skip_recal : 0x00U );
    aux |= (uint8_t)( gRFAL.wum.cfg.skipCal                             ? ST25R200_REG_WAKEUP_CONF2_skip_cal   : 0x00U );
    aux |= (uint8_t)( gRFAL.wum.cfg.delCal                              ? 0x00U : ST25R200_REG_WAKEUP_CONF2_skip_twcal );
    aux |= (uint8_t)( gRFAL.wum.cfg.delRef                              ? 0x00U : ST25R200_REG_WAKEUP_CONF2_skip_twref );
    aux |= (uint8_t)( gRFAL.wum.cfg.autoAvg                             ? ST25R200_REG_WAKEUP_CONF2_iq_aaref   : 0x00U );
    aux |= (uint8_t)( (gRFAL.wum.cfg.measFil == RFAL_WUM_MEAS_FIL_FAST) ? ST25R200_REG_WAKEUP_CONF2_td_mf      : 0x00U );
    aux |= (uint8_t)( (uint8_t)gRFAL.wum.cfg.measDur & ST25R200_REG_WAKEUP_CONF2_td_mt_mask );
    
    st25r200WriteRegister( ST25R200_REG_WAKEUP_CONF2, aux );
    
    
    /* Check if a manual reference is to be obtained */
    if( (!gRFAL.wum.cfg.autoAvg)                                                                  && 
        (( (gRFAL.wum.cfg.I.reference == RFAL_WUM_REFERENCE_AUTO) && (gRFAL.wum.cfg.I.enabled) )  || 
         ( (gRFAL.wum.cfg.Q.reference == RFAL_WUM_REFERENCE_AUTO) && (gRFAL.wum.cfg.Q.enabled) ))    )
    {
        /* Disable calibration automatics, perform manual calibration before reference measurement */
        st25r200SetRegisterBits( ST25R200_REG_WAKEUP_CONF2, (ST25R200_REG_WAKEUP_CONF2_skip_cal | ST25R200_REG_WAKEUP_CONF2_skip_recal) );
        
        /* Perform Manual Calibration and enter PD mode*/
        st25r200CalibrateWU( NULL, NULL );
        st25r200ClrRegisterBits( ST25R200_REG_OPERATION, ST25R200_REG_OPERATION_en );
        
        platformDelay( RFAL_PD_SETTLE );
        st25r200MeasureWU( &measI, &measQ );
    }
    
    
    /*******************************************************************************/
    /* Check if I-Channel is to be checked */
    if( gRFAL.wum.cfg.I.enabled )
    {
        st25r200ChangeRegisterBits( ST25R200_REG_WU_I_DELTA, ST25R200_REG_WU_I_DELTA_i_diff_mask, gRFAL.wum.cfg.I.delta );
        
        aux  = 0U;
        aux |= (uint8_t)(gRFAL.wum.cfg.I.aaInclMeas ? ST25R200_REG_WU_I_CONF_i_iirqm : 0x00U);
        aux |= (uint8_t)(((uint8_t)gRFAL.wum.cfg.I.aaWeight << ST25R200_REG_WU_I_CONF_i_aaw_shift) & ST25R200_REG_WU_I_CONF_i_aaw_mask);
        aux |= (uint8_t)(gRFAL.wum.cfg.I.threshold & ST25R200_REG_WU_I_CONF_i_tdi_en_mask);
        st25r200WriteRegister( ST25R200_REG_WU_I_CONF, aux );
        
        if( !gRFAL.wum.cfg.autoAvg )
        {
            /* Set reference manually */
            st25r200WriteRegister(ST25R200_REG_WU_I_REF, ((gRFAL.wum.cfg.I.reference == RFAL_WUM_REFERENCE_AUTO) ? measI : gRFAL.wum.cfg.I.reference) );
        }
        
        irqs |= ST25R200_IRQ_MASK_WUI;
    }
    else
    {
        st25r200ClrRegisterBits( ST25R200_REG_WU_I_CONF, ST25R200_REG_WU_I_CONF_i_tdi_en_mask );
    }
    
    /*******************************************************************************/
    /* Check if Q-Channel is to be checked */
    if( gRFAL.wum.cfg.Q.enabled )
    {
        st25r200ChangeRegisterBits( ST25R200_REG_WU_Q_DELTA, ST25R200_REG_WU_Q_DELTA_q_diff_mask, gRFAL.wum.cfg.Q.delta );
        
        aux = 0U;
        aux |= (uint8_t)(gRFAL.wum.cfg.Q.aaInclMeas ? ST25R200_REG_WU_Q_CONF_q_iirqm : 0x00U);
        aux |= (uint8_t)(((uint8_t)gRFAL.wum.cfg.Q.aaWeight << ST25R200_REG_WU_Q_CONF_q_aaw_shift) & ST25R200_REG_WU_Q_CONF_q_aaw_mask);
        aux |= (uint8_t)(gRFAL.wum.cfg.Q.threshold & ST25R200_REG_WU_Q_CONF_q_tdi_en_mask);
        st25r200WriteRegister( ST25R200_REG_WU_Q_CONF, aux );
        
        if( !gRFAL.wum.cfg.autoAvg )
        {
            /* Set reference manually */
            st25r200WriteRegister(ST25R200_REG_WU_Q_REF, ((gRFAL.wum.cfg.Q.reference == RFAL_WUM_REFERENCE_AUTO) ? measQ : gRFAL.wum.cfg.Q.reference) );
        }
        
        irqs |= ST25R200_IRQ_MASK_WUQ;
    }
    else
    {
        st25r200ClrRegisterBits( ST25R200_REG_WU_Q_CONF, ST25R200_REG_WU_Q_CONF_q_tdi_en_mask );
    }
    
    /* Disable and clear all interrupts except Wake-Up IRQs */
    st25r200DisableInterrupts( ST25R200_IRQ_MASK_ALL );
    st25r200GetInterrupt( irqs );
    st25r200EnableInterrupts( irqs );
    
    /* Disable Oscilattor, Tx, Rx and Regulators */
    st25r200ClrRegisterBits( ST25R200_REG_OPERATION, (ST25R200_REG_OPERATION_tx_en | ST25R200_REG_OPERATION_rx_en | ST25R200_REG_OPERATION_am_en | ST25R200_REG_OPERATION_en) );
    
    /* Clear WU info struct */
    RFAL_MEMSET(&gRFAL.wum.info, 0x00, sizeof(gRFAL.wum.info)); 
    
    gRFAL.wum.state = RFAL_WUM_STATE_ENABLED;
    gRFAL.state     = RFAL_STATE_WUM;
      
    /* Enable Low Power Wake-Up Mode */
    st25r200SetRegisterBits( ST25R200_REG_OPERATION, ST25R200_REG_OPERATION_wu_en );

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
bool rfalWakeUpModeHasWoke( void )
{   
    return (gRFAL.wum.state >= RFAL_WUM_STATE_ENABLED_WOKE);
}


/*******************************************************************************/
bool rfalWakeUpModeIsEnabled( void )
{   
    return ((gRFAL.state == RFAL_STATE_WUM) && (gRFAL.wum.state >= RFAL_WUM_STATE_ENABLED));
}


/*******************************************************************************/
ReturnCode rfalWakeUpModeGetInfo( bool force, rfalWakeUpInfo *info )
{
    /* Check if WU mode is running */
    if( (gRFAL.state != RFAL_STATE_WUM) || (gRFAL.wum.state < RFAL_WUM_STATE_ENABLED) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check for valid parameters */
    if( info == NULL )
    {
        return RFAL_ERR_PARAM;
    }
    
    /* Clear info structure */
    RFAL_MEMSET( info, 0x00, sizeof(rfalWakeUpInfo) );
    
    /* Update general information */ 
    info->irqWut          = gRFAL.wum.info.irqWut;
    gRFAL.wum.info.irqWut = false;
    
    /* WUT IRQ is signaled when WUT expires. Delay slightly for the actual measurement to be performed */
    if( info->irqWut )
    {
        platformDelay( 1 );
    }
    
    /* Retrieve values if there was an WUT, WUI or WUQ event (or forced) */
    if( force || (info->irqWut) || (gRFAL.wum.info.irqWui) || (gRFAL.wum.info.irqWuq) )
    {
        /* Update status information */
        st25r200ReadRegister( ST25R200_REG_DISPLAY4, &info->status );
        info->status &= (ST25R200_REG_DISPLAY4_q_tdi_mask | ST25R200_REG_DISPLAY4_i_tdi_mask);
        
        if( gRFAL.wum.cfg.I.enabled )
        {
            st25r200ReadRegister( ST25R200_REG_WU_I_ADC, &info->I.lastMeas );
            st25r200ReadRegister( ST25R200_REG_WU_I_CAL, &info->I.calib );
            st25r200ReadRegister( ST25R200_REG_WU_I_REF, &info->I.reference );
        
            /* Update IRQ information and clear flag upon retrieving */
            info->I.irqWu         = gRFAL.wum.info.irqWui;
            gRFAL.wum.info.irqWui = false;
        }
        
        if( gRFAL.wum.cfg.Q.enabled )
        {
            st25r200ReadRegister( ST25R200_REG_WU_Q_ADC, &info->Q.lastMeas );
            st25r200ReadRegister( ST25R200_REG_WU_Q_CAL, &info->Q.calib );
            st25r200ReadRegister( ST25R200_REG_WU_Q_REF, &info->Q.reference );
        
            /* Update IRQ information and clear flag upon retrieving */
            info->Q.irqWu         = gRFAL.wum.info.irqWuq;
            gRFAL.wum.info.irqWuq = false;
        }
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
static void rfalRunWakeUpModeWorker( void )
{
    uint32_t irqs;
    uint8_t  aux;
    
    if( gRFAL.state != RFAL_STATE_WUM )
    {
        return;
    }

    switch( gRFAL.wum.state )
    {
        case RFAL_WUM_STATE_ENABLED:
        case RFAL_WUM_STATE_ENABLED_WOKE:
            
            irqs = st25r200GetInterrupt( ( ST25R200_IRQ_MASK_WUT | ST25R200_IRQ_MASK_WUI | ST25R200_IRQ_MASK_WUQ ) );
            if( irqs == ST25R200_IRQ_MASK_NONE )
            {
               break;  /* No interrupt to process */
            }
            
            /*******************************************************************************/
            /* Check and mark which measurement(s) cause interrupt */
            if((irqs & ST25R200_IRQ_MASK_WUI) != 0U)
            {
                gRFAL.wum.info.irqWui = true;
                st25r200ReadRegister( ST25R200_REG_WU_I_ADC, &aux );
                gRFAL.wum.state = RFAL_WUM_STATE_ENABLED_WOKE;
            }
            
            if((irqs & ST25R200_IRQ_MASK_WUQ) != 0U)
            {
                gRFAL.wum.info.irqWuq = true;
                st25r200ReadRegister( ST25R200_REG_WU_Q_ADC, &aux );
                gRFAL.wum.state = RFAL_WUM_STATE_ENABLED_WOKE;
            }

            if((irqs & ST25R200_IRQ_MASK_WUT) != 0U)
            {
                gRFAL.wum.info.irqWut = true;
            }
            
            break;
            
        default:
            /* MISRA 16.4: no empty default statement (a comment being enough) */
            break;
    }
}


/*******************************************************************************/
ReturnCode rfalWakeUpModeStop( void )
{
    if( gRFAL.wum.state == RFAL_WUM_STATE_NOT_INIT )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    gRFAL.wum.state = RFAL_WUM_STATE_NOT_INIT;
    
    /* Disable Wake-Up Mode */
    st25r200ClrRegisterBits( ST25R200_REG_OPERATION, ST25R200_REG_OPERATION_wu_en );
    st25r200DisableInterrupts( (ST25R200_IRQ_MASK_WUT | ST25R200_IRQ_MASK_WUQ | ST25R200_IRQ_MASK_WUI ) );
    
    /* Re-Enable the Oscillator and Regulators */
    st25r200OscOn();
    
    /* Stop any ongoing activity */
    st25r200ExecuteCommand( ST25R200_CMD_STOP );
    
    /* Set Analog configurations for Wake-up Off event */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_WAKEUP_OFF) );
      
    return RFAL_ERR_NONE;
}

#endif /* RFAL_FEATURE_WAKEUP_MODE */


/*******************************************************************************/
ReturnCode rfalWlcPWptMonitorStart( const rfalWakeUpConfig *config ) 
{
    RFAL_NO_WARNING(config);
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalWlcPWptMonitorStop( void ) 
{
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
bool rfalWlcPWptIsFodDetected( void )
{   
    return false;
}


/*******************************************************************************/
bool rfalWlcPWptIsStopDetected( void )
{   
    return false;
}


/*******************************************************************************
 *  Low-Power Mode                                                             *
 *******************************************************************************/

#if RFAL_FEATURE_LOWPOWER_MODE

/*******************************************************************************/
ReturnCode rfalLowPowerModeStart( rfalLpMode mode )
{
    /* Check if RFAL is not initialized */
    if( gRFAL.state < RFAL_STATE_INIT )
    {
        return RFAL_ERR_WRONG_STATE;
    }

    if( mode == RFAL_LP_MODE_HR )
    {
    #ifndef ST25R_RESET_PIN
        return RFAL_ERR_DISABLED;
    #else
        platformGpioSet( ST25R_RESET_PORT, ST25R_RESET_PIN );
    #endif /* ST25R_RESET_PIN */
    }
    else
    {
        /* Stop any ongoing activity and set the device in low power by disabling oscillator, transmitter, receiver and AM regulator */
        st25r200ExecuteCommand( ST25R200_CMD_STOP );
        st25r200ClrRegisterBits( ST25R200_REG_OPERATION, ( ST25R200_REG_OPERATION_en    | ST25R200_REG_OPERATION_rx_en | 
                                                           ST25R200_REG_OPERATION_wu_en | ST25R200_REG_OPERATION_tx_en | ST25R200_REG_OPERATION_am_en) );
        
        rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_LOWPOWER_ON) );
        
    }

    gRFAL.state         = RFAL_STATE_IDLE;
    gRFAL.lpm.isRunning = true;
    gRFAL.lpm.mode      = mode;
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalLowPowerModeStop( void )
{
    ReturnCode ret;
    
    /* Check if RFAL is on right state */
    if( !gRFAL.lpm.isRunning )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
#ifdef ST25R_RESET_PIN
    if( gRFAL.lpm.mode == RFAL_LP_MODE_HR )
    {
        rfalInitialize();
    }
    else
#endif /* ST25R_RESET_PIN */
    {
        /* Re-enable device */
        RFAL_EXIT_ON_ERR( ret, st25r200OscOn());
        
        rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_LOWPOWER_OFF) );
    }
    
    gRFAL.state         = RFAL_STATE_INIT;
    gRFAL.lpm.isRunning = false;
    return RFAL_ERR_NONE;
}

#endif /* RFAL_FEATURE_LOWPOWER_MODE */

/*******************************************************************************
 *  RF Chip                                                                    *  
 *******************************************************************************/

/*******************************************************************************/
ReturnCode rfalChipWriteReg( uint16_t reg, const uint8_t* values, uint8_t len )
{
    if( !st25r200IsRegValid( (uint8_t)reg) )
    {
        return RFAL_ERR_PARAM;
    }
    
    return st25r200WriteMultipleRegisters( (uint8_t)reg, values, len );
}


/*******************************************************************************/
ReturnCode rfalChipReadReg( uint16_t reg, uint8_t* values, uint8_t len )
{
    if( !st25r200IsRegValid( (uint8_t)reg) )
    {
        return RFAL_ERR_PARAM;
    }
    
    return st25r200ReadMultipleRegisters( (uint8_t)reg, values, len );
}


/*******************************************************************************/
ReturnCode rfalChipExecCmd( uint16_t cmd )
{
    if( !st25r200IsCmdValid( (uint8_t)cmd) )
    {
        return RFAL_ERR_PARAM;
    }
    
    return st25r200ExecuteCommand( (uint8_t) cmd );
}


/*******************************************************************************/
ReturnCode rfalChipWriteTestReg( uint16_t reg, uint8_t value )
{
    return st25r200WriteTestRegister( (uint8_t)reg, value );
}


/*******************************************************************************/
ReturnCode rfalChipReadTestReg( uint16_t reg, uint8_t* value )
{
    return st25r200ReadTestRegister( (uint8_t)reg, value );
}


/*******************************************************************************/
ReturnCode rfalChipChangeRegBits( uint16_t reg, uint8_t valueMask, uint8_t value )
{
    if( !st25r200IsRegValid( (uint8_t)reg) )
    {
        return RFAL_ERR_PARAM;
    }
    
    return st25r200ChangeRegisterBits( (uint8_t)reg, valueMask, value );
}


/*******************************************************************************/
ReturnCode rfalChipChangeTestRegBits( uint16_t reg, uint8_t valueMask, uint8_t value )
{
    return st25r200ChangeTestRegisterBits( (uint8_t)reg, valueMask, value );
}


/*******************************************************************************/
ReturnCode rfalChipSetRFO( uint8_t rfo )
{
    return st25r200ChangeRegisterBits( ST25R200_REG_TX_DRIVER, ST25R200_REG_TX_DRIVER_d_res_mask, rfo);
}


/*******************************************************************************/
ReturnCode rfalChipGetRFO( uint8_t* result )
{
    ReturnCode ret;
    
    ret = st25r200ReadRegister(ST25R200_REG_TX_DRIVER, result);
    
    if( result != NULL)
    {
        (*result) = ( (*result) & ST25R200_REG_TX_DRIVER_d_res_mask );
    }

    return ret;
}


/*******************************************************************************/
ReturnCode rfalChipSetLMMod( uint8_t mod, uint8_t unmod )
{
    RFAL_NO_WARNING(mod);
    RFAL_NO_WARNING(unmod);
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalChipGetLMMod( uint8_t* mod, uint8_t* unmod )
{
    if( mod != NULL )
    {
        (*mod) = 0U;
    }
    
    if( unmod != NULL )
    {
        (*unmod) = 0U;
    }
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalChipGetLmFieldInd( uint8_t* result )
{
    if( result != NULL )
    {
        (*result) = 0U;
    }
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalChipMeasureAmplitude( uint8_t* result )
{
    if( result != NULL )
    {
        (*result) = 0U;
    }
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalChipMeasurePhase( uint8_t* result )
{
    if( result != NULL )
    {
        (*result) = 0U;
    }
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalChipMeasureCapacitance( uint8_t* result )
{
    if( result != NULL )
    {
        (*result) = 0U;
    }
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalChipMeasurePowerSupply( uint8_t param, uint8_t* result )
{
    RFAL_NO_WARNING(param);
    
    if( result != NULL )
    {
        (*result) = 0U;
    }
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalChipMeasureIQ( int8_t* resI, int8_t* resQ )
{
    st25r200ClearCalibration();
    return st25r200MeasureIQ( resI, resQ );
}


/*******************************************************************************/
ReturnCode rfalChipMeasureCombinedIQ( uint8_t* result )
{
    ReturnCode err;
    uint8_t    reg;
    
    /* Apply|Use same sensitivity setting between measurements*/
    st25r200ReadRegister( ST25R200_REG_RX_ANA2, &reg );
    st25r200WriteRegister( ST25R200_REG_RX_ANA2, ((reg & ~ST25R200_REG_RX_ANA2_afe_gain_td_mask) | ST25R200_REG_RX_ANA2_afe_gain_td2 | ST25R200_REG_RX_ANA2_afe_gain_td1) );
    
    err = st25r200MeasureCombinedIQ( result );
    
    /* Restore previous sensitivity */
    st25r200WriteRegister( ST25R200_REG_RX_ANA2, reg );
    
    return err;
}


/*******************************************************************************/
ReturnCode rfalChipMeasureI( uint8_t* result )
{
    ReturnCode err;
    uint8_t    reg;
    
    /* Apply|Use same sensitivity setting between measurements*/
    st25r200ReadRegister( ST25R200_REG_RX_ANA2, &reg );
    st25r200WriteRegister( ST25R200_REG_RX_ANA2, ((reg & ~ST25R200_REG_RX_ANA2_afe_gain_td_mask) | ST25R200_REG_RX_ANA2_afe_gain_td2 | ST25R200_REG_RX_ANA2_afe_gain_td1) );
    
    err = st25r200MeasureI( result );
    
    /* Restore previous sensitivity */
    st25r200WriteRegister( ST25R200_REG_RX_ANA2, reg );
    
    return err;
}


/*******************************************************************************/
ReturnCode rfalChipMeasureQ( uint8_t* result )
{
    ReturnCode err;
    uint8_t    reg;
    
    /* Apply|Use same sensitivity setting between measurements*/
    st25r200ReadRegister( ST25R200_REG_RX_ANA2, &reg );
    st25r200WriteRegister( ST25R200_REG_RX_ANA2, ((reg & ~ST25R200_REG_RX_ANA2_afe_gain_td_mask) | ST25R200_REG_RX_ANA2_afe_gain_td2 | ST25R200_REG_RX_ANA2_afe_gain_td1) );
    
    err = st25r200MeasureQ( result );
    
    /* Restore previous sensitivity */
    st25r200WriteRegister( ST25R200_REG_RX_ANA2, reg );
    
    return err;
}


/*******************************************************************************/
ReturnCode rfalChipMeasureCurrent( uint8_t* result )
{
    if( result != NULL )
    {
        (*result) = 0U;
    }
    
    return RFAL_ERR_NOTSUPP;
}


/*******************************************************************************/
ReturnCode rfalChipSetAntennaMode( bool single, bool rfiox )
{
    return st25r200SetAntennaMode(single, rfiox );
}
