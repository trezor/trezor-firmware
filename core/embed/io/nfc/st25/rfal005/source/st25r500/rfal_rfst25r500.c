
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

/*! \file rfal_rfst25r500.c
 *
 *  \author Gustavo Patricio 
 *
 *  \brief RF Abstraction Layer (RFAL)
 *  
 *  RFAL implementation for ST25R500
 */


/*
******************************************************************************
* INCLUDES
******************************************************************************
*/

#include "rfal_chip.h"
#include "rfal_utils.h"
#include "st25r500.h"
#include "st25r500_com.h"
#include "st25r500_irq.h"
#include "st25r500_dpocr.h"
#include "rfal_analogConfig.h"
#include "rfal_dpo.h"

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
    bool                     irqWutme;   /*!< Wake-Up Timer IRQ received after WU measurement     */
    uint8_t                  status;     /*!< Wake-Up Status                                      */
    bool                     irqWptFod;  /*!< Wake-Up WLC WPT FOD IRQ received                    */
    bool                     irqWptStop; /*!< Wake-Up WLC WPT Stop IRQ received                   */
}rfalWakeUpData;


/*! Local struct that holds context for the Listen Mode                                           */
typedef struct{
    rfalLmState             state;       /*!< Current Listen Mode state                           */
    uint32_t                mdMask;      /*!< Listen Mode mask used                               */
    uint32_t                mdReg;       /*!< Listen Mode register value used                     */
    uint32_t                mdIrqs;      /*!< Listen Mode IRQs used                               */
    rfalBitRate             brDetected;  /*!< Last bit rate detected                              */
    
    uint8_t*                rxBuf;       /*!< Location to store incoming data in Listen Mode      */
    uint16_t                rxBufLen;    /*!< Length of rxBuf                                     */
    uint16_t*               rxLen;       /*!< Pointer to write the data length placed into rxBuf  */
    bool                    dataFlag;    /*!< Listen Mode current Data Flag                       */
    bool                    iniFlag;     /*!< Listen Mode initialized Flag  (FeliCa slots)        */
} rfalLm;


/*! Struct that holds all context for the Wake-Up Mode                                            */
typedef struct{
    rfalWumState            state;       /*!< Current Wake-Up Mode state                          */
    rfalWakeUpConfig        cfg;         /*!< Current Wake-Up Mode context                        */
    rfalWakeUpData          info;        /*!< Current Wake-Up Mode information                    */
    bool                    wlcPWpt;     /*!< NFC Forum WLC WPT phase monitoring                  */
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
    uint32_t                txRx;        /*!< Transceive sanity timer   */
} rfalTimers;


/*! Struct that holds the RFAL's callbacks                              */
typedef struct{
    rfalPreTxRxCallback     preTxRx;     /*!< RFAL's Pre TxRx callback  */
    rfalPostTxRxCallback    postTxRx;    /*!< RFAL's Post TxRx callback */
    rfalSyncTxRxCallback    syncTxRx;    /*!< RFAL's Sync TxRx callback */
    rfalLmEonCallback       lmEon;       /*!< RFAL's LM EON callback    */
} rfalCallbacks;


/*! Struct that holds counters to control the FIFO on Tx and Rx                                                                          */
typedef struct{    
    uint16_t                expWL;       /*!< The amount of bytes expected to be Tx when a WL interrupt occours                          */
    uint16_t                bytesTotal;  /*!< Total bytes to be transmitted OR the total bytes received                                  */
    uint16_t                bytesWritten;/*!< Amount of bytes already written on FIFO (Tx) OR read (RX) from FIFO and written on rxBuffer*/
    uint8_t                 status[ST25R500_FIFO_STATUS_LEN];   /*!< FIFO Status Registers                                              */
} rfalFIFO;


/*! Struct that holds RFAL's configuration settings                                                     */
typedef struct{    
    uint16_t                obsvModeTx;  /*!< RFAL's config of the ST25R500's observation mode while Tx */
    uint16_t                obsvModeRx;  /*!< RFAL's config of the ST25R500's observation mode while Rx */
    uint8_t                 obsvModeCfg[ST25R500_OBS_MODE_LEN]; /*!< RFAL's ST25R200's obs mode aux     */
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


/*! Struct that holds NFC-F data - Used only inside rfalFelicaPoll()                                           */
typedef struct{
    uint16_t           actLen;                                      /* Received length                         */
    rfalFeliCaPollRes* pollResList;                                 /* Location of NFC-F device list           */
    uint8_t            pollResListSize;                             /* Size of NFC-F device list               */
    uint8_t            devDetected;                                 /* Number of devices detected              */
    uint8_t            colDetected;                                 /* Number of collisions detected           */
    uint8_t            *devicesDetected;                            /* Location to place number of devices     */
    uint8_t            *collisionsDetected;                         /* Location to place number of collisions  */
    rfalEHandling      curHandling;                                 /* RFAL's error handling                   */
    rfalFeliCaPollRes  pollResponses[RFAL_FELICA_POLL_MAX_SLOTS];   /* FeliCa Poll response buffer (16 slots)  */
} rfalNfcfWorkingData;


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
                                                                                                        
#if RFAL_FEATURE_LISTEN_MODE
    rfalLm                  Lm;          /*!< RFAL's listen mode management                             */
#endif /* RFAL_FEATURE_LISTEN_MODE */

#if RFAL_FEATURE_WAKEUP_MODE
    rfalWum                 wum;         /*!< RFAL's Wake-up mode management                            */
#endif /* RFAL_FEATURE_WAKEUP_MODE */

#if RFAL_FEATURE_LOWPOWER_MODE
    rfalLpm                 lpm;         /*!< RFAL's Low power mode management                          */
#endif /* RFAL_FEATURE_LOWPOWER_MODE */
                                                                                                        
#if RFAL_FEATURE_NFCA
    rfalNfcaWorkingData     nfcaData;    /*!< RFAL's working data when supporting NFC-A                 */
#endif /* RFAL_FEATURE_NFCA */

#if RFAL_FEATURE_NFCF
    rfalNfcfWorkingData     nfcfData;    /*!< RFAL's working data when supporting NFC-F                 */
#endif /* RFAL_FEATURE_NFCF */

} rfal;


/*! Felica's command set */
typedef enum {
    FELICA_CMD_POLLING                  = 0x00, /*!< Felica Poll/REQC command (aka SENSF_REQ) to identify a card    */
    FELICA_CMD_POLLING_RES              = 0x01, /*!< Felica Poll/REQC command (aka SENSF_RES) response              */
    FELICA_CMD_REQUEST_SERVICE          = 0x02, /*!< verify the existence of Area and Service                       */
    FELICA_CMD_REQUEST_RESPONSE         = 0x04, /*!< verify the existence of a card                                 */
    FELICA_CMD_READ_WITHOUT_ENCRYPTION  = 0x06, /*!< read Block Data from a Service that requires no authentication */
    FELICA_CMD_WRITE_WITHOUT_ENCRYPTION = 0x08, /*!< write Block Data to a Service that requires no authentication  */
    FELICA_CMD_REQUEST_SYSTEM_CODE      = 0x0C, /*!< acquire the System Code registered to a card                   */
    FELICA_CMD_AUTHENTICATION1          = 0x10, /*!< authenticate a card                                            */
    FELICA_CMD_AUTHENTICATION2          = 0x12, /*!< allow a card to authenticate a Reader/Writer                   */
    FELICA_CMD_READ                     = 0x14, /*!< read Block Data from a Service that requires authentication    */
    FELICA_CMD_WRITE                    = 0x16, /*!< write Block Data to a Service that requires authentication     */
} rfalFeliCaCmd;


/*! Union representing all CE Memory sections */
typedef union{  /*  PRQA S 0750 # MISRA 19.2 - Both members are of the same type, just different names.  Thus no problem can occur. */
    uint8_t CEMem_A[ST25R500_CEM_A_LEN];       /*!< CE Memory area allocated for NFC-A configuration               */
    uint8_t CEMem_F[ST25R500_CEM_F_LEN];       /*!< CE Memory area allocated for NFC-F configuration               */
} rfalCEMem;


/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/

#define RFAL_FIFO_IN_WL                 128U                                          /*!< Number of bytes in the FIFO when WL interrupt occurs while Tx                   */
#define RFAL_FIFO_OUT_WL                (ST25R500_FIFO_DEPTH - RFAL_FIFO_IN_WL)       /*!< Number of bytes sent/out of the FIFO when WL interrupt occurs while Tx          */

#define RFAL_FIFO_STATUS_REG1           0U                                            /*!< Location of FIFO status register 1 in local copy                                */
#define RFAL_FIFO_STATUS_REG2           1U                                            /*!< Location of FIFO status register 2 in local copy                                */
#define RFAL_FIFO_STATUS_INVALID        0xFFU                                         /*!< Value indicating that the local FIFO status in invalid|cleared                  */

#define RFAL_ST25R500_GPT_MAX_1FC       rfalConv8fcTo1fc(  0xFFFFU )                  /*!< Max GPT steps in 1fc (0xFFFF steps of 8/fc    => 0xFFFF * 590ns  = 38,7ms)      */
#define RFAL_ST25R500_NRT_MAX_1FC       rfalConv4096fcTo1fc( 0xFFFFU )                /*!< Max NRT steps in 1fc (0xFFFF steps of 4096/fc => 0xFFFF * 302us  = 19.8s )      */
#define RFAL_ST25R500_NRT_DISABLED      0U                                            /*!< NRT Disabled: All 0 No-response timer is not started, wait forever              */
#define RFAL_ST25R500_MRT_MAX_1FC       rfalConv64fcTo1fc( 0x00FFU )                  /*!< Max MRT steps in 1fc (0x00FF steps of 64/fc   => 0x00FF * 4.72us = 1.2ms )      */
#define RFAL_ST25R500_MRT_MIN_1FC       rfalConv64fcTo1fc( 0x0004U )                  /*!< Min MRT steps in 1fc ( 0<=mrt<=4 ; 4 (64/fc)  => 0x0004 * 4.72us = 18.88us )    */
#define RFAL_ST25R500_GT_MAX_1FC        rfalConvMsTo1fc( 6000U )                      /*!< Max GT value allowed in 1/fc (SFGI=14 => SFGT + dSFGT = 5.4s)                   */
#define RFAL_ST25R500_GT_MIN_1FC        rfalConvMsTo1fc(RFAL_ST25R500_SW_TMR_MIN_1MS) /*!< Min GT value allowed in 1/fc                                                    */
#define RFAL_ST25R500_SW_TMR_MIN_1MS    1U                                            /*!< Min value of a SW timer in ms                                                   */

#define RFAL_OBSMODE_DISABLE            0x0000U                                       /*!< Observation Mode disabled                                                       */

#define RFAL_RX_INC_BYTE_LEN            (uint8_t)1U                                   /*!< Threshold where incoming rx shall be considered incomplete byte NFC - T2T       */
#define RFAL_EMVCO_RX_MAXLEN            (uint8_t)4U                                   /*!< Maximum value where EMVCo to apply special error handling                       */

#define RFAL_NORXE_TOUT                 50U                                           /*!< Timeout to be used on a potential missing RXE                                   */

#define RFAL_FELICA_POLL_DELAY_TIME     512U                                          /*!<  FeliCa Poll Processing time is 2.417 ms ~512*64/fc Digital 1.1 A4              */
#define RFAL_FELICA_POLL_SLOT_TIME      256U                                          /*!<  FeliCa Poll Time Slot duration is 1.208 ms ~256*64/fc Digital 1.1 A4           */

#define RFAL_LM_SENSF_RD0_POS           17U                                           /*!<  FeliCa SENSF_RES Request Data RD0 position                                     */
#define RFAL_LM_SENSF_RD1_POS           18U                                           /*!<  FeliCa SENSF_RES Request Data RD1 position                                     */

#define RFAL_ISO14443A_SHORTFRAME_LEN   7U                                            /*!< Number of bits of a Short Frame in bits             Digital 2.0  6.3.2  & 6.6   */
#define RFAL_ISO14443A_SDD_RES_LEN      5U                                            /*!< SDD_RES | Anticollision (UID CLn) length  -  rfalNfcaSddRes                     */

#define RFAL_LM_NFCID_INCOMPLETE        0x04U                                         /*!<  NFCA NFCID not complete bit in SEL_RES (SAK)                                   */

#define RFAL_ISO15693_IGNORE_BITS       rfalConvBytesToBits(2U)                       /*!< Ignore collisions before the UID (RES_FLAG + DSFID)                             */
#define RFAL_ISO15693_INV_RES_LEN       12U                                           /*!< ISO15693 Inventory response length with CRC (bytes)                             */
#define RFAL_ISO15693_INV_RES_DUR       4U                                            /*!< ISO15693 Inventory response duration @ 26 kbps (ms)                             */

#define RFAL_PD_SETTLE                  3U                                            /*!< Settling duration after entering PD/WU mode                                     */


/*******************************************************************************/

#define RFAL_LM_GT                      rfalConvMsTo1fc(3U)                           /*!< Listen Mode Guard Time enforced (GT - Passive)                                  */
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
 *    64  : Half a bit duration due to ST25R500 Coherent receiver (1/fc)         */
#define RFAL_FWT_A_ADJUSTMENT           (512U + 64U)

/*! FWT ISO14443B adjustment:  
 *    SOF (14etu) + 1Byte (10etu) + 1etu (IRQ comes 1etu after first byte) - 3etu (ST25R500 sends TXE 3etu after) */
#define RFAL_FWT_B_ADJUSTMENT           (((14U + 10U + 1U) - 3U) * 128U)

/*! FWT FeliCa 212 adjustment:  
 *    1024 : Length of the two Sync bytes at 212kbps */
#define RFAL_FWT_F_212_ADJUSTMENT       1024U

/*! FWT FeliCa 424 adjustment:  
 *    512 : Length of the two Sync bytes at 424kbps  */
#define RFAL_FWT_F_424_ADJUSTMENT       512U

/*! FWT ISO15693 adjustment:  
 *    SOF (4bd) + 4 bits (x * 8bd)  (using longest bd at 26kbps) */
#define RFAL_FWT_V_ADJUSTMENT           ((4U * 512U) + (4U * 512U))


/*! Time between our field Off and other peer field On : Tadt + (n x Trfw)
 * Ecma 340 11.1.2 - Tadt: [56.64 , 188.72] us ;  n: [0 , 3]  ; Trfw = 37.76 us        
 * Should be: 189 + (3*38) = 303us ; we'll use a more relaxed setting: 605 us    */
#define RFAL_AP2P_FIELDON_TADTTRFW      rfalConvUsTo1fc(605U)


/*! FDT Listen adjustment for ISO14443A   EMVCo 2.6  4.8.1.3  ;  Digital 1.1  6.10
 *
 *  276: Time from the rising pulse of the pause of the logic '1' (i.e. the time point to measure the deaftime from), 
 *       to the actual end of the EOF sequence (the point where the MRT starts). Please note that the ST25R500 uses the
 *       ISO14443-2 definition where the EOF consists of logic '0' followed by sequence Y. 
 *  -16: Further adjustment for receiver to be ready just before first bit
 */
#define RFAL_FDT_LISTEN_A_ADJUSTMENT    (276U-16U)

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
#define RFAL_TR1MIN                     58U


/*! Adjustment to ensure min time between VDD_DR enable and Field On 10us
*   
*  SPI at 10MHz: 1byte = 800ns  |  13bytes = 10.4us 
*  13 => SPI command + 12 byte transaction
 */
#define RFAL_VDD_DR_ADJUSTMENT          12U


/*! Adjustment to ensure min time between Oscilattor On and RFI Field Indicator 150us
*   
*  SPI at 10MHz: 1byte = 800ns  |  190bytes = 152us 
*  190 => SPI command + 189 byte transaction
 */
#define RFAL_RFIND_ADJUSTMENT           189U


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

/*! Calculates Transceive Sanity Timer. It accounts for the slowest bit rate and the longest data format
 *    1s for transmission and reception of a 4K message at 106kpbs (~425ms each direction)
 *       plus TxRx preparation and FIFO load over Serial Interface                                      */
#define rfalCalcSanityTmr( fwt )                 (uint16_t)(1000U + rfalConv1fcToMs((fwt)))

#define rfalCalcNumBytes( nBits )                (((uint32_t)(nBits) + 7U) / 8U)                                 /*!< Returns the number of bytes required to fit given the number of bits */

#define rfalTimerStart( timer, time_ms )         do{ platformTimerDestroy( timer ); (timer) = platformTimerCreate((uint16_t)(time_ms)); } while(0) /*!< Configures and starts timer        */
#define rfalTimerisExpired( timer )              platformTimerIsExpired( timer )                                 /*!< Checks if timer has expired                                          */
#define rfalTimerDestroy( timer )                platformTimerDestroy( timer )                                   /*!< Destroys timer                                                       */

#define rfalST25R500ObsModeDisable()            st25r500WriteTestRegister(0x02U, (0x00U))                        /*!< Disable ST25R500 Observation mode                                    */
#define rfalST25R500ObsModeTx()                 do{ gRFAL.conf.obsvModeCfg[0]=(uint8_t)(gRFAL.conf.obsvModeTx>>8U); gRFAL.conf.obsvModeCfg[1]=(uint8_t)(gRFAL.conf.obsvModeTx&0xFFU); st25r500WriteMultipleTestRegister(0x02U, gRFAL.conf.obsvModeCfg, 2U); }while(0)  /*!< Enable Tx Observation mode                                           */
#define rfalST25R500ObsModeRx()                 do{ gRFAL.conf.obsvModeCfg[0]=(uint8_t)(gRFAL.conf.obsvModeRx>>8U); gRFAL.conf.obsvModeCfg[1]=(uint8_t)(gRFAL.conf.obsvModeRx&0xFFU); st25r500WriteMultipleTestRegister(0x02U, gRFAL.conf.obsvModeCfg, 2U); }while(0)  /*!< Enable Rx Observation mode                                           */


#define rfalCheckDisableObsMode()                if(gRFAL.conf.obsvModeRx != 0U){ rfalST25R500ObsModeDisable(); } /*!< Checks if the observation mode is enabled, and applies on ST25R500  */
#define rfalCheckEnableObsModeTx()               if(gRFAL.conf.obsvModeTx != 0U){ rfalST25R500ObsModeTx(); }      /*!< Checks if the observation mode is enabled, and applies on ST25R500  */
#define rfalCheckEnableObsModeRx()               if(gRFAL.conf.obsvModeRx != 0U){ rfalST25R500ObsModeRx(); }      /*!< Checks if the observation mode is enabled, and applies on ST25R500  */


#define rfalGetIncmplBits( FIFOStatus2 )         (( (FIFOStatus2) >> 1) & 0x07U)                                           /*!< Returns the number of bits from fifo status                */
#define rfalIsIncompleteByteError( error )       (((error) >= RFAL_ERR_INCOMPLETE_BYTE) && ((error) <= RFAL_ERR_INCOMPLETE_BYTE_07)) /*!< Checks if given error is a Incomplete error      */

#define rfalAdjACBR( b )                         (((uint16_t)(b) >= (uint16_t)RFAL_BR_211p88) ? (uint16_t)(b) : ((uint16_t)(b)+1U))         /*!< Adjusts ST25R Bit rate to Analog Configuration              */
#define rfalConvBR2ACBR( b )                     (((rfalAdjACBR((b)))<<RFAL_ANALOG_CONFIG_BITRATE_SHIFT) & RFAL_ANALOG_CONFIG_BITRATE_MASK) /*!< Converts ST25R Bit rate to Analog Configuration bit rate id */
#define rfalConvBitRate( br )                    ((((br)==RFAL_BR_26p48) ? (ST25R500_BR_106_26) : (((br)==RFAL_BR_52p97) ? (ST25R500_BR_212_53) : (((br)==RFAL_BR_105p94) ? (ST25R500_BR_424) : (((br)==RFAL_BR_211p88) ? (ST25R500_BR_848) : (uint8_t)(br))) )))

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
#if RFAL_FEATURE_LISTEN_MODE
static ReturnCode rfalRunListenModeWorker( void );
#endif /* RFAL_FEATURE_LISTEN_MODE */

static ReturnCode rfalRunTransceiveWorker( void );
#if RFAL_FEATURE_WAKEUP_MODE
static void rfalRunWakeUpModeWorker( void );
static ReturnCode rfalWUModeStart( const rfalWakeUpConfig *config );
#endif /* RFAL_FEATURE_WAKEUP_MODE */

static void rfalDpoReqAdjust( void );
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
    
    RFAL_EXIT_ON_ERR( err, st25r500Initialize() );
    
    st25r500ClearInterrupts();
    
    /* Disable any previous observation mode */
    rfalST25R500ObsModeDisable();
    
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
    rfalTimerDestroy( gRFAL.tmr.RXE );
    rfalTimerDestroy( gRFAL.tmr.txRx );
    gRFAL.tmr.GT             = RFAL_TIMING_NONE;
    gRFAL.tmr.RXE            = RFAL_TIMING_NONE;
    gRFAL.tmr.txRx           = RFAL_TIMING_NONE;
    
    gRFAL.callbacks.preTxRx  = NULL;
    gRFAL.callbacks.postTxRx = NULL;
    gRFAL.callbacks.syncTxRx = NULL;
    gRFAL.callbacks.lmEon    = NULL;


#if RFAL_FEATURE_LISTEN_MODE
    /* Initialize Listen Mode */
    gRFAL.Lm.state           = RFAL_LM_STATE_NOT_INIT;
    gRFAL.Lm.brDetected      = RFAL_BR_KEEP;
    gRFAL.Lm.iniFlag         = false;
#endif /* RFAL_FEATURE_LISTEN_MODE */

#if RFAL_FEATURE_WAKEUP_MODE
    /* Initialize Wake-Up Mode */
    gRFAL.wum.state   = RFAL_WUM_STATE_NOT_INIT;
    gRFAL.wum.wlcPWpt = false;
#endif /* RFAL_FEATURE_WAKEUP_MODE */

#if RFAL_FEATURE_LOWPOWER_MODE
    /* Initialize Low Power Mode */
    gRFAL.lpm.isRunning     = false;
#endif /* RFAL_FEATURE_LOWPOWER_MODE */
    
    
    /*******************************************************************************/    
    /* Perform Automatic Calibration (if configured to do so).                     *
     * Registers set by rfalSetAnalogConfig will tell rfalCalibrate what to perform*/
    rfalCalibrate();
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalCalibrate( void )
{
    /*******************************************************************************/
    /* Perform ST25R500 regulators calibration                                     */
    /*******************************************************************************/
    
    /* Automatic regulator adjustment only performed if not set manually on Analog Configs */
    if( st25r500CheckReg( ST25R500_REG_REGULATOR, ST25R500_REG_REGULATOR_reg_s, 0x00 ) )
    {
        rfalAdjustRegulators( NULL );
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalAdjustRegulators( uint16_t* result )
{
    /* Adjust the regulators with both Tx and Rx enabled for a realistic RW load conditions */
    st25r500VDDDROn();
    st25r500ReadFifo( NULL, RFAL_VDD_DR_ADJUSTMENT );  /* Dummy SPI read to ensure min time */
    st25r500TxRxOn();
    
    st25r500AdjustRegulators( ST25R500_REG_DROP_DO_NOT_SET, result );
    
    st25r500TxRxOff();
    st25r500VDDDROff();
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalSetRegulators( uint8_t regulation )
{   
    return st25r500SetRegulators( regulation );
}


/*******************************************************************************/
void rfalSetUpperLayerCallback( rfalUpperLayerCallback pFunc )
{
    st25r500IRQCallbackSet( pFunc );
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
    gRFAL.callbacks.lmEon = pFunc;
}


/*******************************************************************************/
ReturnCode rfalDeinitialize( void )
{
    /* Deinitialize chip */
    st25r500Deinitialize();
    
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
    uint8_t aux;
    
    /* Suppress warning in case Listen Mode feature is disabled */
    aux = 0;
    RFAL_NO_WARNING( aux );

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
            st25r500WriteRegister( ST25R500_REG_PROTOCOL, ST25R500_REG_PROTOCOL_om_iso14443a );
            
            /* Set Analog configurations for this mode and bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            break;
            
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCA_T1T:
            
            /* Enable Topaz mode */
            st25r500WriteRegister( ST25R500_REG_PROTOCOL, ST25R500_REG_PROTOCOL_om_topaz );
            
            /* Set Analog configurations for this mode and bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            break;
            
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCB:
            
            /* Enable ISO14443B mode */
            st25r500WriteRegister( ST25R500_REG_PROTOCOL, ST25R500_REG_PROTOCOL_om_iso14443b );
            
            /* Set Tx SOF and EOF */
            st25r500ChangeRegisterBits(  ST25R500_REG_PROTOCOL_TX2,
                                        ( ST25R500_REG_PROTOCOL_TX2_b_tx_sof_mask | ST25R500_REG_PROTOCOL_TX2_b_tx_eof ),
                                        ( ST25R500_REG_PROTOCOL_TX2_b_tx_sof_0_10etu | ST25R500_REG_PROTOCOL_TX2_b_tx_sof_1_2etu | ST25R500_REG_PROTOCOL_TX2_b_tx_eof_10etu ) );
                        
            /* Set Rx SOF and EOF */
            st25r500ChangeRegisterBits(  ST25R500_REG_PROTOCOL_RX1, 
                                        ( ST25R500_REG_PROTOCOL_RX1_b_rx_sof | ST25R500_REG_PROTOCOL_RX1_b_rx_eof ),
                                        ( ST25R500_REG_PROTOCOL_RX1_b_rx_sof | ST25R500_REG_PROTOCOL_RX1_b_rx_eof ) );
        
            /* Set the minimum TR1 (start_wait) */
            st25r500ChangeRegisterBits( ST25R500_REG_PROTOCOL_RX2, ST25R500_REG_PROTOCOL_RX2_tr1_min_len_mask, RFAL_TR1MIN );

            /* Set Analog configurations for this mode and bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            break;
            
        /*******************************************************************************/    
        case RFAL_MODE_POLL_B_PRIME:
            
            /* Enable ISO14443B mode */
            st25r500WriteRegister( ST25R500_REG_PROTOCOL, ST25R500_REG_PROTOCOL_om_iso14443b );
            
            /* Set Tx SOF, EOF and EOF */
            st25r500ChangeRegisterBits(  ST25R500_REG_PROTOCOL_TX2,
                                        ( ST25R500_REG_PROTOCOL_TX2_b_tx_sof_mask | ST25R500_REG_PROTOCOL_TX2_b_tx_eof ),
                                        ( ST25R500_REG_PROTOCOL_TX2_b_tx_sof_0_10etu | ST25R500_REG_PROTOCOL_TX2_b_tx_sof_1_2etu | ST25R500_REG_PROTOCOL_TX2_b_tx_eof_10etu ) );
                        
            /* Set Rx SOF and EOF */
            st25r500ChangeRegisterBits( ST25R500_REG_PROTOCOL_RX1, 
                                        ( ST25R500_REG_PROTOCOL_RX1_b_rx_sof | ST25R500_REG_PROTOCOL_RX1_b_rx_eof ),
                                        ( ST25R500_REG_PROTOCOL_RX1_b_rx_eof ) );
        
            /* Set the minimum TR1 (start_wait) */
            st25r500ChangeRegisterBits( ST25R500_REG_PROTOCOL_RX2, ST25R500_REG_PROTOCOL_RX2_tr1_min_len_mask, RFAL_TR1MIN );


            /* Set Analog configurations for this mode and bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            break;
            
        /*******************************************************************************/    
        case RFAL_MODE_POLL_B_CTS:
            
            /* Enable ISO14443B mode */
            st25r500WriteRegister( ST25R500_REG_PROTOCOL, ST25R500_REG_PROTOCOL_om_iso14443b );
            
            /* Set Tx SOF and EOF */
            st25r500ChangeRegisterBits(  ST25R500_REG_PROTOCOL_TX2,
                                        ( ST25R500_REG_PROTOCOL_TX2_b_tx_sof_mask | ST25R500_REG_PROTOCOL_TX2_b_tx_eof ),
                                        ( ST25R500_REG_PROTOCOL_TX2_b_tx_sof_0_10etu | ST25R500_REG_PROTOCOL_TX2_b_tx_sof_1_2etu | ST25R500_REG_PROTOCOL_TX2_b_tx_eof_10etu ) );
                        
            /* Set Rx SOF EOF */
            st25r500ChangeRegisterBits(  ST25R500_REG_PROTOCOL_RX1, 
                                        ( ST25R500_REG_PROTOCOL_RX1_b_rx_sof | ST25R500_REG_PROTOCOL_RX1_b_rx_eof ),
                                         0x00 );
        
            /* Set the minimum TR1 (start_wait) */
            st25r500ChangeRegisterBits( ST25R500_REG_PROTOCOL_RX2, ST25R500_REG_PROTOCOL_RX2_tr1_min_len_mask, RFAL_TR1MIN );

            /* Set Analog configurations for this mode and bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            break;
        
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCF:
            
                /* Enable FeliCa mode */
                st25r500WriteRegister( ST25R500_REG_PROTOCOL, ST25R500_REG_PROTOCOL_om_felica );
        
                /* Set Analog configurations for this mode and bit rate */
                rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCF | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
                rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCF | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
                break;
        
        /*******************************************************************************/
        case RFAL_MODE_POLL_NFCV:
        case RFAL_MODE_POLL_PICOPASS:
                
                /* Enable ISO15693 mode */
                st25r500WriteRegister( ST25R500_REG_PROTOCOL, ST25R500_REG_PROTOCOL_om_iso15693 );
        
                /* Set Analog configurations for this mode and bit rate */
                rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
                rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
                break;
        
#if RFAL_FEATURE_LISTEN_MODE
        /*******************************************************************************/
        case RFAL_MODE_LISTEN_NFCA:
            
            /* Enable CE ISO14443A mode */
            st25r500SetRegisterBits(ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_ce_en );
            st25r500WriteRegister( ST25R500_REG_PROTOCOL, ST25R500_REG_PROTOCOL_om_iso14443a );
            
            /* Set Analog configurations for this mode */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_LISTEN | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_LISTEN | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            
        
        
            /* If coming from different technology (e.g. PSL) change state to A state */
            st25r500ReadRegister( ST25R500_REG_CE_STATUS1, &aux );
            aux &= ST25R500_REG_CE_STATUS1_ce_state_mask;
            if( aux == ST25R500_REG_CE_STATUS1_ce_state_ce_f )
            {
                st25r500ChangeRegisterBits( ST25R500_REG_CE_STATUS1, ST25R500_REG_CE_STATUS1_ce_state_mask, ST25R500_REG_CE_STATUS1_ce_state_ce_a );
            }
            break;
            
        /*******************************************************************************/
        case RFAL_MODE_LISTEN_NFCF:
            
            /* Enable CE FeliCa mode */
            st25r500SetRegisterBits(ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_ce_en );
            st25r500WriteRegister( ST25R500_REG_PROTOCOL, ST25R500_REG_PROTOCOL_om_felica );
            
            /* Set Analog configurations for this mode */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_LISTEN | RFAL_ANALOG_CONFIG_TECH_NFCF | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX) );
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_LISTEN | RFAL_ANALOG_CONFIG_TECH_NFCF | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX) );
            
            /* If coming from different technology (e.g. PSL) change state to F state */
            st25r500ReadRegister( ST25R500_REG_CE_STATUS1, &aux );
            aux &= ST25R500_REG_CE_STATUS1_ce_state_mask;
            if( (aux >= ST25R500_REG_CE_STATUS1_ce_state_ready_a) && (aux <= ST25R500_REG_CE_STATUS1_ce_state_active_ax) )
            {
                st25r500ChangeRegisterBits( ST25R500_REG_CE_STATUS1, ST25R500_REG_CE_STATUS1_ce_state_mask, ST25R500_REG_CE_STATUS1_ce_state_ce_f );
            }
            break;
        
#else
        case RFAL_MODE_LISTEN_NFCA:
        case RFAL_MODE_LISTEN_NFCF:
#endif
        case RFAL_MODE_POLL_ACTIVE_P2P:
        case RFAL_MODE_LISTEN_ACTIVE_P2P:
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
    
    
    if( ( (txBR != RFAL_BR_KEEP) && (txBR > RFAL_BR_848) && (txBR != RFAL_BR_26p48) )                                                                                    || 
        ( (rxBR != RFAL_BR_KEEP) && (rxBR > RFAL_BR_848) && (rxBR != RFAL_BR_26p48) && (rxBR != RFAL_BR_52p97) && (rxBR != RFAL_BR_105p94) && (rxBR != RFAL_BR_211p88)  )   )
    {
        return RFAL_ERR_PARAM;
    }
    
    /* Store the new Bit Rates */
    gRFAL.txBR = ((txBR == RFAL_BR_KEEP) ? gRFAL.txBR : txBR);
    gRFAL.rxBR = ((rxBR == RFAL_BR_KEEP) ? gRFAL.rxBR : rxBR);
    

    /* Set bit rate register */
    RFAL_EXIT_ON_ERR( ret, st25r500SetBitrate( (uint8_t)rfalConvBitRate(gRFAL.txBR), (uint8_t)rfalConvBitRate(gRFAL.rxBR )) );
    
    
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
        case RFAL_MODE_POLL_NFCF:
            /* Set Analog configurations for this bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_POLL_COMMON) );
            rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCF | rfalConvBR2ACBR(gRFAL.txBR) | RFAL_ANALOG_CONFIG_TX ) );
            rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCF | rfalConvBR2ACBR(gRFAL.rxBR) | RFAL_ANALOG_CONFIG_RX ) );
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
        case RFAL_MODE_LISTEN_NFCA:
            
            /* Set Analog configurations for this bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_LISTEN_COMMON) );
            rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_LISTEN | RFAL_ANALOG_CONFIG_TECH_NFCA | rfalConvBR2ACBR(gRFAL.txBR) | RFAL_ANALOG_CONFIG_TX ) );
            rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_LISTEN | RFAL_ANALOG_CONFIG_TECH_NFCA | rfalConvBR2ACBR(gRFAL.rxBR) | RFAL_ANALOG_CONFIG_RX ) );
            break;
                
        /*******************************************************************************/
        case RFAL_MODE_LISTEN_NFCF:
                        
            /* Set Analog configurations for this bit rate */
            rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_LISTEN_COMMON) );
            rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_LISTEN | RFAL_ANALOG_CONFIG_TECH_NFCF | rfalConvBR2ACBR(gRFAL.txBR) | RFAL_ANALOG_CONFIG_TX ) );
            rfalSetAnalogConfig( (rfalAnalogConfigId)(RFAL_ANALOG_CONFIG_LISTEN | RFAL_ANALOG_CONFIG_TECH_NFCF | rfalConvBR2ACBR(gRFAL.rxBR) | RFAL_ANALOG_CONFIG_RX ) );
            break;
        
        /*******************************************************************************/
        case RFAL_MODE_POLL_ACTIVE_P2P:
        case RFAL_MODE_LISTEN_ACTIVE_P2P:
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
            st25r500ClrRegisterBits( ST25R500_REG_EMD1, ST25R500_REG_EMD1_emd_en );
            break;
            
        case RFAL_ERRORHANDLING_EMD:
            st25r500ModifyRegister(  ST25R500_REG_EMD1,
                                    ( ST25R500_REG_EMD1_emd_thld_mask | ST25R500_REG_EMD1_emd_thld_ff | ST25R500_REG_EMD1_emd_en ),
                                    ( (RFAL_EMVCO_RX_MAXLEN<<ST25R500_REG_EMD1_emd_thld_shift) | ST25R500_REG_EMD1_emd_thld_ff | ST25R500_REG_EMD1_emd_en_on ) );
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
    gRFAL.timings.FDTPoll = RFAL_MIN( FDTPoll, RFAL_ST25R500_GPT_MAX_1FC );
}


/*******************************************************************************/
uint32_t rfalGetFDTPoll( void )
{
    return gRFAL.timings.FDTPoll;
}


/*******************************************************************************/
void rfalSetFDTListen( uint32_t FDTListen )
{
    gRFAL.timings.FDTListen = RFAL_MIN( FDTListen, RFAL_ST25R500_MRT_MAX_1FC );
}


/*******************************************************************************/
uint32_t rfalGetFDTListen( void )
{
    return gRFAL.timings.FDTListen;
}


/*******************************************************************************/
void rfalSetGT( uint32_t GT )
{
    gRFAL.timings.GT = RFAL_MIN( GT, RFAL_ST25R500_GT_MAX_1FC );
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
    if( (!st25r500IsOscOn()) || (gRFAL.state < RFAL_STATE_INIT) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    ret = RFAL_ERR_NONE;
    
    /* Ensure VDD_DR regulator is enabled */
    st25r500VDDDROn();
    
    /* Set Analog configurations for Field On event */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_FIELD_ON) );
    
    /*******************************************************************************/
    /* Perform collision avoidance and turn field On if not already On */
    if( (!st25r500IsTxEnabled()) || (!gRFAL.field) )
    {
        ret = st25r500PerformCollisionAvoidance( ST25R500_THRESHOLD_DO_NOT_SET, ST25R500_THRESHOLD_DO_NOT_SET, 0U );
        gRFAL.field = st25r500IsTxEnabled();
        
        /* Only turn on Receiver and Transmitter if field was successfully turned On */
        if(gRFAL.field)
        {
            st25r500TxRxOn(); /* Enable Tx and Rx (Tx is already On)*/
        }
    }
    
    
    
    /*******************************************************************************/
    /* Start GT timer in case the GT value is set */
    if( (gRFAL.timings.GT != RFAL_TIMING_NONE) )
    {
        /* Ensure that a SW timer doesn't have a lower value then the minimum  */
        rfalTimerStart( gRFAL.tmr.GT, rfalConv1fcToMs( RFAL_MAX( (gRFAL.timings.GT), RFAL_ST25R500_GT_MIN_1FC) ) );
    }
    
	/* If DPO used, request to perform the adjustment */
    rfalDpoReqAdjust();
        
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
    st25r500TxRxOff();
    
    /* Disable VDD_DR regulator */
    st25r500VDDDROff();
    
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
    if( (gRFAL.state >= RFAL_STATE_MODE_SET) )
    {
        /*******************************************************************************/
        /* Check whether the field is already On, otherwise no TXE will be received  */
        if( (!st25r500IsTxEnabled()) && ((!rfalIsModePassiveListen( gRFAL.mode )) && (ctx->txBuf != NULL)) )
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
            
            /* Set Minimum FDT(Listen) in which PICC is not allowed to send a response */
            st25r500SetMRT( (FxTAdj > gRFAL.timings.FDTListen) ? RFAL_ST25R500_MRT_MIN_1FC : (gRFAL.timings.FDTListen - FxTAdj) );
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
            if(gRFAL.mode == RFAL_MODE_POLL_NFCF)
            {
                FxTAdj += (uint32_t)((gRFAL.txBR == RFAL_BR_212) ? RFAL_FWT_F_212_ADJUSTMENT : RFAL_FWT_F_424_ADJUSTMENT );
            }
            
            
            /* Ensure that the given FWT doesn't exceed NRT maximum */
            gRFAL.TxRx.ctx.fwt = RFAL_MIN( (gRFAL.TxRx.ctx.fwt + FxTAdj), RFAL_ST25R500_NRT_MAX_1FC );
            
            /* Set FWT in the NRT */
            st25r500SetNoResponseTime( rfalConv1fcTo64fc( gRFAL.TxRx.ctx.fwt ) );
        }
        else
        {
            /* Disable NRT, no NRE will be triggered, therefore wait endlessly for Rx */
            st25r500SetNoResponseTime( RFAL_ST25R500_NRT_DISABLED );
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
            st25r500ExecuteCommand( ST25R500_CMD_UNMASK_RECEIVE_DATA );

            /* Start NRT manually, if FWT = 0 (wait endlessly for Rx) chip will ignore anyhow */
            st25r500ExecuteCommand( ST25R500_CMD_START_NRT );

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
        /*******************************************************************************/
        /* Check Transceive Sanity Timer has expired */
        if( gRFAL.tmr.txRx != RFAL_TIMING_NONE )
        {
            if( rfalTimerisExpired( gRFAL.tmr.txRx ) )
            {
                /* If sanity timer has expired abort ongoing transceive and signal error */
                gRFAL.TxRx.status = RFAL_ERR_IO;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
            }
        }
        
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
    uint16_t iRSSI;
    uint16_t qRSSI;
    
    if( rssi == NULL )
    {
        return RFAL_ERR_PARAM;
    }
    
    st25r500GetRSSI( &iRSSI, &qRSSI );
    
 #ifdef RFAL_CMATH
    *rssi = (uint16_t) sqrt( ((double)iRSSI*(double)iRSSI) + ((double)qRSSI*(double)qRSSI) );               /*  PRQA S 5209 # MISRA 4.6 - External function (sqrt()) requires double */
#else
    *rssi = ((iRSSI + qRSSI) / 2U);
#endif
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
bool rfalIsTransceiveSubcDetected( void )
{
    if( (gRFAL.state == RFAL_STATE_TXRX) || (gRFAL.TxRx.state == RFAL_TXRX_STATE_IDLE) )
    {
        return (st25r500GetInterrupt( ST25R500_IRQ_MASK_SUBC_START ) != 0U);
    }
    return false;
}


/*******************************************************************************/
void rfalWorker( void )
{
    platformProtectWorker();               /* Protect RFAL Worker/Task/Process */
    
#ifdef ST25R_POLL_IRQ
    st25r500CheckForReceivedInterrupts();
#endif /* ST25R_POLL_IRQ */
    
    switch( gRFAL.state )
    {
        case RFAL_STATE_TXRX:
            rfalRunTransceiveWorker();
            break;
        
    #if RFAL_FEATURE_LISTEN_MODE
        case RFAL_STATE_LM:
            rfalRunListenModeWorker();
            break;
    #endif /* RFAL_FEATURE_LISTEN_MODE */    
        
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
                st25r500ReadFifo( (uint8_t*)(gRFAL.TxRx.ctx.rxBuf), fifoBytesToRead );
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
    
    /* Restore default settings on Tx Parity, CRC and SB|F0*/
    st25r500ChangeRegisterBits( ST25R500_REG_PROTOCOL_TX1, (ST25R500_REG_PROTOCOL_TX1_a_tx_par | ST25R500_REG_PROTOCOL_TX1_tx_crc | ST25R500_REG_PROTOCOL_TX1_a_nfc_f0), (ST25R500_REG_PROTOCOL_TX1_a_tx_par | ST25R500_REG_PROTOCOL_TX1_tx_crc) );
    
    /* Restore default settings on Receiving parity + CRC bits */
    st25r500SetRegisterBits( ST25R500_REG_PROTOCOL_RX1, ( ST25R500_REG_PROTOCOL_RX1_a_rx_par | ST25R500_REG_PROTOCOL_RX1_rx_crc) );
    
    /* Restore AGC enabled */
    st25r500SetRegisterBits( ST25R500_REG_RX_DIG, ST25R500_REG_RX_DIG_agc_en );
    
    /*******************************************************************************/
    
    
    /*******************************************************************************/
    /* Transceive timers                                                           */
    /*******************************************************************************/
    rfalTimerDestroy( gRFAL.tmr.txRx );
    rfalTimerDestroy( gRFAL.tmr.RXE );
    gRFAL.tmr.txRx   = RFAL_TIMING_NONE;
    gRFAL.tmr.RXE    = RFAL_TIMING_NONE;
    /*******************************************************************************/
    
    
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
    
    /* Check if we are in RW mode */
    if( !rfalIsModePassiveListen( gRFAL.mode ) )
    {
        /* Reset receive logic with STOP command */
        st25r500ExecuteCommand( ST25R500_CMD_STOP );
    
        /* Reset Rx Gain */
        st25r500ExecuteCommand( ST25R500_CMD_CLEAR_RXGAIN );
    }
    else
    {
        /* In Passive Listen Mode do not use STOP as it stops FDT timer */
        st25r500ExecuteCommand( ST25R500_CMD_CLEAR_FIFO );
    }

    
    /*******************************************************************************/
    /* FDT Poll                                                                    */
    /*******************************************************************************/

    /* In Passive communications General Purpose Timer is used to measure FDT Poll */
    if( gRFAL.timings.FDTPoll != RFAL_TIMING_NONE )
    {
        /* Configure GPT to start at RX end */
        st25r500SetStartGPTimer( (uint16_t)rfalConv1fcTo8fc( ((gRFAL.timings.FDTPoll < RFAL_FDT_POLL_ADJUSTMENT) ? gRFAL.timings.FDTPoll : (gRFAL.timings.FDTPoll - RFAL_FDT_POLL_ADJUSTMENT)) ), ST25R500_REG_NRT_GPT_CONF_gptc_erx );
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
    maskInterrupts = ( ST25R500_IRQ_MASK_WL     | ST25R500_IRQ_MASK_TXE  |
                       ST25R500_IRQ_MASK_RXS    | ST25R500_IRQ_MASK_RXE  |
                       ST25R500_IRQ_MASK_RX_ERR | ST25R500_IRQ_MASK_COL  |
                       ST25R500_IRQ_MASK_NRE    | ST25R500_IRQ_MASK_RXE_CE);
    
    if( rfalIsModePassiveListen( gRFAL.mode ) )
    { /* In Listen mode EOF should terminate an ongoing transceive */
        maskInterrupts |= ST25R500_IRQ_MASK_EOF;
    }

    /* IRQs that do not  require immediate serving but may be used for TxRx */
    clrMaskInterrupts = ST25R500_IRQ_MASK_SUBC_START;
    
    /*******************************************************************************/
    /* Transceive flags                                                            */
    /*******************************************************************************/
    
    /* Transmission Flags */
    reg = (ST25R500_REG_PROTOCOL_TX1_tx_crc_on | ST25R500_REG_PROTOCOL_TX1_a_tx_par_on);
    

    /* Check if automatic Parity bits is to be disabled */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_PAR_TX_NONE) != 0U )
    {
        reg &= ~ST25R500_REG_PROTOCOL_TX1_a_tx_par;
    }
    
    /* Check if automatic Parity bits is to be disabled */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_CRC_TX_MANUAL) != 0U )
    {
        reg &= ~ST25R500_REG_PROTOCOL_TX1_tx_crc;
    }
    
    /* Check if NFCIP1 mode is to be enabled */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_NFCIP1_ON) != 0U )
    {
        reg |= ST25R500_REG_PROTOCOL_TX1_a_nfc_f0;
    }
    
    /* Apply current TxRx flags on Tx Register */
    st25r500ChangeRegisterBits( ST25R500_REG_PROTOCOL_TX1, (ST25R500_REG_PROTOCOL_TX1_a_nfc_f0 | ST25R500_REG_PROTOCOL_TX1_tx_crc | ST25R500_REG_PROTOCOL_TX1_a_tx_par), reg );
    
    
    /* Reception Flags */
    reg = (ST25R500_REG_PROTOCOL_RX1_a_rx_par_on | ST25R500_REG_PROTOCOL_RX1_rx_crc_on);
    
    /* Check if Parity check is to be skipped and to keep the parity bits in FIFO */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_PAR_RX_KEEP) != 0U )
    {
        reg &= ~ST25R500_REG_PROTOCOL_RX1_a_rx_par;
    }
    
    /* Check if CRC check is to be skipped */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_CRC_RX_MANUAL) != 0U )
    {
        reg &= ~ST25R500_REG_PROTOCOL_RX1_rx_crc;
    }
    
    /* Apply current TxRx flags on Tx Register */
    st25r500ChangeRegisterBits( ST25R500_REG_PROTOCOL_RX1, (ST25R500_REG_PROTOCOL_RX1_a_rx_par | ST25R500_REG_PROTOCOL_RX1_rx_crc), reg );
    
    
    /* Check if AGC is to be disabled */
    if( (gRFAL.TxRx.ctx.flags & (uint8_t)RFAL_TXRX_FLAGS_AGC_OFF) != 0U )
    {
        st25r500ClrRegisterBits( ST25R500_REG_RX_DIG, ST25R500_REG_RX_DIG_agc_en );
    }
    else
    {
        st25r500SetRegisterBits( ST25R500_REG_RX_DIG, ST25R500_REG_RX_DIG_agc_en );
    }
    /*******************************************************************************/
    
    
    /*******************************************************************************/
    /* EMVCo NRT mode                                                              */
    /*******************************************************************************/
    if( gRFAL.conf.eHandling == RFAL_ERRORHANDLING_EMD )
    {
        st25r500SetRegisterBits( ST25R500_REG_NRT_GPT_CONF, ST25R500_REG_NRT_GPT_CONF_nrt_emv );
        maskInterrupts |= ST25R500_IRQ_MASK_RX_REST;
    }
    else
    {
        st25r500ClrRegisterBits( ST25R500_REG_NRT_GPT_CONF, ST25R500_REG_NRT_GPT_CONF_nrt_emv );
    }
    /*******************************************************************************/
    
    
    /*******************************************************************************/
    /* Start transceive Sanity Timer if a FWT is used */
    if( (gRFAL.TxRx.ctx.fwt != RFAL_FWT_NONE) && (gRFAL.TxRx.ctx.fwt != 0U) )
    {
        rfalTimerStart( gRFAL.tmr.txRx, rfalCalcSanityTmr( gRFAL.TxRx.ctx.fwt ) );
    }
    /*******************************************************************************/
    
    
    /*******************************************************************************/
    /* Clear and enable these interrupts */
    st25r500GetInterrupt( (maskInterrupts | clrMaskInterrupts) );
    st25r500EnableInterrupts( maskInterrupts );
    
    /* Clear FIFO status local copy */
    rfalFIFOStatusClear();
}


/*******************************************************************************/
static void rfalTransceiveTx( void )
{
    uint32_t    irqs;
    uint16_t    tmp;
    ReturnCode  ret;
    
    /* Suppress warning in case NFC-V feature is disabled */
    ret = RFAL_ERR_NONE;
    RFAL_NO_WARNING( ret );
    
    irqs = ST25R500_IRQ_MASK_NONE;
    
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
            if( st25r500IsGPTRunning() )
            {                
               break;
            }
            
            gRFAL.TxRx.state = RFAL_TXRX_STATE_TX_PREP_TX;
            /* fall through */
            
        
        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_PREP_TX:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            /* Clear FIFO, Clear and Enable the Interrupts */
            rfalPrepareTransceive( );

            /* ST25R500 has a fixed FIFO water level */
            gRFAL.fifo.expWL = RFAL_FIFO_OUT_WL;
        
            /* Calculate the bytes needed to be Written into FIFO (a incomplete byte will be added as 1byte) */
            gRFAL.fifo.bytesTotal = (uint16_t)rfalCalcNumBytes(gRFAL.TxRx.ctx.txBufLen);
            
            /* Set the number of full bytes and bits to be transmitted */
            st25r500SetNumTxBits( gRFAL.TxRx.ctx.txBufLen );
            
            /* Load FIFO with total length or FIFO's maximum */
            gRFAL.fifo.bytesWritten = RFAL_MIN( gRFAL.fifo.bytesTotal, ST25R500_FIFO_DEPTH );
            st25r500WriteFifo( gRFAL.TxRx.ctx.txBuf, gRFAL.fifo.bytesWritten );
        
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
            st25r500ExecuteCommand( ST25R500_CMD_TRANSMIT );
             
            /* Check if a WL level is expected or TXE should come */
            gRFAL.TxRx.state = (( gRFAL.fifo.bytesWritten < gRFAL.fifo.bytesTotal ) ? RFAL_TXRX_STATE_TX_WAIT_WL : RFAL_TXRX_STATE_TX_WAIT_TXE);
            break;

        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_WAIT_WL:
            
            irqs = st25r500GetInterrupt( (ST25R500_IRQ_MASK_WL | ST25R500_IRQ_MASK_TXE) );
            if( irqs == ST25R500_IRQ_MASK_NONE )
            {
               break;  /* No interrupt to process */
            }
            
            if( ((irqs & ST25R500_IRQ_MASK_WL) != 0U) && ((irqs & ST25R500_IRQ_MASK_TXE) == 0U) )
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
            st25r500WriteFifo( &gRFAL.TxRx.ctx.txBuf[gRFAL.fifo.bytesWritten], tmp );
            
            /* Update total written bytes to FIFO */
            gRFAL.fifo.bytesWritten += tmp;
            
            /* Check if a WL level is expected or TXE should come */
            gRFAL.TxRx.state = (( gRFAL.fifo.bytesWritten < gRFAL.fifo.bytesTotal ) ? RFAL_TXRX_STATE_TX_WAIT_WL : RFAL_TXRX_STATE_TX_WAIT_TXE);
            break;
            
            
        /*******************************************************************************/
        case RFAL_TXRX_STATE_TX_WAIT_TXE:
           
            irqs = st25r500GetInterrupt( (ST25R500_IRQ_MASK_WL | ST25R500_IRQ_MASK_TXE | ST25R500_IRQ_MASK_EOF) );
            if( irqs == ST25R500_IRQ_MASK_NONE )
            {
               break;  /* No interrupt to process */
            }
                        
            
            if( (irqs & ST25R500_IRQ_MASK_TXE) != 0U )
            {
                gRFAL.TxRx.state = RFAL_TXRX_STATE_TX_DONE;
            }
            else if( (irqs & ST25R500_IRQ_MASK_WL) != 0U )
            {
                break;  /* Ignore ST25R500 FIFO WL if total TxLen is already on the FIFO */
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
    uint32_t  irqs;
    uint16_t  tmp;
    uint16_t  aux;
    uint8_t   reg;
    
    irqs = ST25R500_IRQ_MASK_NONE;
    
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
            irqs = st25r500GetInterrupt( (ST25R500_IRQ_MASK_RXS | ST25R500_IRQ_MASK_NRE | ST25R500_IRQ_MASK_EOF ) );
            if( irqs == ST25R500_IRQ_MASK_NONE )
            {
                break;  /* No interrupt to process */
            }
            
            /* Only raise Timeout if NRE is detected with no Rx Start (NRT EMV mode) */
            if( ((irqs & ST25R500_IRQ_MASK_NRE) != 0U) && ((irqs & ST25R500_IRQ_MASK_RXS) == 0U) )
            {
                gRFAL.TxRx.status = RFAL_ERR_TIMEOUT;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
                break;
            }
            
            /* Only raise Link Loss if EOF is detected with no Rx Start */
            if( ((irqs & ST25R500_IRQ_MASK_EOF) != 0U) && ((irqs & ST25R500_IRQ_MASK_RXS) == 0U) )
            {
                gRFAL.TxRx.status =  RFAL_ERR_LINK_LOSS;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
                break;
            }
            
            if( (irqs & ST25R500_IRQ_MASK_RXS) != 0U )
            {
                /*******************************************************************************/
                /* Use a SW timer to handle an eventual missing RXE                            */
                rfalTimerStart( gRFAL.tmr.RXE, RFAL_NORXE_TOUT );
                /*******************************************************************************/
                
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_WAIT_RXE;
            }
            else
            {
                gRFAL.TxRx.status = RFAL_ERR_IO;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
                break;
            }
            
            /* remove NRE that might appear together (NRT EMV mode), and remove RXS */
            irqs &= ~(ST25R500_IRQ_MASK_RXS | ST25R500_IRQ_MASK_NRE);
            
            /* fall through */
            
            
        /*******************************************************************************/    
        case RFAL_TXRX_STATE_RX_WAIT_RXE:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            irqs |= st25r500GetInterrupt( ( ST25R500_IRQ_MASK_RXE_CE | ST25R500_IRQ_MASK_RXE  | ST25R500_IRQ_MASK_WL | ST25R500_IRQ_MASK_RX_REST ) );
            if( irqs == ST25R500_IRQ_MASK_NONE )
            {
                /*******************************************************************************/
                /* SW timer is used to timeout upon a missing RXE                              */
                if( rfalTimerisExpired( gRFAL.tmr.RXE ) )
                {
                    gRFAL.TxRx.status = RFAL_ERR_FRAMING;
                    gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
                }
                /*******************************************************************************/
                
                break;  /* No interrupt to process */
            }
            
            if( ((irqs & ST25R500_IRQ_MASK_RX_REST) != 0U) && ((irqs & ST25R500_IRQ_MASK_RXE) == 0U) )
            {
                /* RX_REST indicates that Receiver has been reseted due to EMD, therefore a RXS + RXE should *
                 * follow if a good reception is followed within the valid initial timeout                   */
                
                /* Check whether NRT has expired already, if so signal a timeout */
                if( st25r500GetInterrupt( ST25R500_IRQ_MASK_NRE ) != 0U )
                {
                    gRFAL.TxRx.status = RFAL_ERR_TIMEOUT;
                    gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
                    break;
                }
                
                st25r500ReadRegister( ST25R500_REG_STATUS2, &reg );
                if( ((reg & ST25R500_REG_STATUS2_nrt_on) == 0U) )
                {
                    gRFAL.TxRx.status = RFAL_ERR_TIMEOUT;
                    gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_FAIL;
                    break;
                }
                
                /* Discard any previous RXS and transmission errors */
                st25r500GetInterrupt( ST25R500_IRQ_MASK_RXS );
                
                /* Check whether a following reception has already started and is ongoing */
                if( ((reg & ST25R500_REG_STATUS2_rx_act) != 0U) )
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
            
            if( ((irqs & ST25R500_IRQ_MASK_WL) != 0U) && ((irqs & ST25R500_IRQ_MASK_RXE) == 0U) )
            {
                gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_READ_FIFO;
                break;
            }
            
            /* After RXE retrieve and check for any error irqs */
            irqs |= st25r500GetInterrupt( (ST25R500_IRQ_MASK_RX_ERR | ST25R500_IRQ_MASK_COL) );
            
            gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_ERR_CHECK;
            /* fall through */
            
            
        /*******************************************************************************/    
        case RFAL_TXRX_STATE_RX_ERR_CHECK:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            if( (irqs & ST25R500_IRQ_MASK_COL) != 0U )
            {
                gRFAL.TxRx.status = RFAL_ERR_RF_COLLISION;
                gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_READ_DATA;
                
                
                
                /* Check if there's a specific error handling for this */
                rfalErrorHandling();
                break;
            }
            else if( (irqs & ST25R500_IRQ_MASK_RX_ERR) != 0U )
            {
                /* Retrieve reception errors */
                st25r500ReadRegister( ST25R500_REG_STATUS_STATIC3, &reg );
                
                if( ((reg & ST25R500_REG_STATUS_STATIC3_s_hfe) != 0U) || ((reg & ST25R500_REG_STATUS_STATIC3_s_sfe) != 0U) )
                {
                    gRFAL.TxRx.status = RFAL_ERR_FRAMING;
                    gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_READ_DATA;
                    
                    /* Check if there's a specific error handling for this */
                    rfalErrorHandling();
                    break;
                }
                else if( (reg & ST25R500_REG_STATUS_STATIC3_s_par) != 0U )
                {
                    gRFAL.TxRx.status = RFAL_ERR_PAR;
                    gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_READ_DATA;
                    
                    /* Check if there's a specific error handling for this */
                    rfalErrorHandling();
                    break;
                }
                else if( (reg & ST25R500_REG_STATUS_STATIC3_s_crc) != 0U )
                {
                    gRFAL.TxRx.status = RFAL_ERR_CRC;
                    gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_READ_DATA;
                    
                    /* Check if there's a specific error handling for this */
                    rfalErrorHandling();
                    break;
                }
                else
                {
                    /* MISRA 15.7 - Empty else */
                }
            }
            else if( (irqs & ST25R500_IRQ_MASK_RXE) != 0U )
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
            else if( (irqs & ST25R500_IRQ_MASK_RXE_CE) != 0U )
            {
                /* Reception ended with automatic response.
                 * This can happen if CE state machine still active and sending
                 * automated responses.
                 * Typical appearance is on having received S(DSL) with en_dsl_a=1    */

                /* SLEEP_REQ status does not fit in all imaginable uses cases
                 * but works nicely with ISODEP layer */
                gRFAL.TxRx.status = RFAL_ERR_SLEEP_REQ;
                gRFAL.TxRx.state = RFAL_TXRX_STATE_RX_DONE;
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
            st25r500ReadFifo( &gRFAL.TxRx.ctx.rxBuf[gRFAL.fifo.bytesWritten], tmp);
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
            
            /*******************************************************************************/
            /* Use a SW timer to handle an eventual missing RXE                            */
            rfalTimerStart( gRFAL.tmr.RXE, RFAL_NORXE_TOUT );
            /*******************************************************************************/
            
            tmp = rfalFIFOStatusGetNumBytes();
            gRFAL.fifo.bytesTotal += tmp;
            
            /*******************************************************************************/
            /* Calculate the amount of bytes that still fits in rxBuf                      */
            aux = (( gRFAL.fifo.bytesTotal > rfalConvBitsToBytes(gRFAL.TxRx.ctx.rxBufLen) ) ? (rfalConvBitsToBytes(gRFAL.TxRx.ctx.rxBufLen) - gRFAL.fifo.bytesWritten) : tmp);
            
            /*******************************************************************************/
            /* Retrieve incoming bytes from FIFO to rxBuf, and store already read amount   */
            st25r500ReadFifo( &gRFAL.TxRx.ctx.rxBuf[gRFAL.fifo.bytesWritten], aux);
            gRFAL.fifo.bytesWritten += aux;
            
            /*******************************************************************************/
            /* If the bytes already read were not the full FIFO WL, dump the remaining     *
             * FIFO so that ST25R can continue with reception                              */
            if( aux < tmp )
            {
                st25r500ReadFifo( NULL, (tmp - aux) );
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
static void rfalDpoReqAdjust( void )
{
    /* If DPO used, request to perform the adjustment */
    
#if RFAL_FEATURE_DPO    
    rfalDpoReqAdj();
#endif /* RFAL_FEATURE_DPO */
    
#if RFAL_FEATURE_DPO_CR
    st25r500DpocrReqAdj();
#endif /* RFAL_FEATURE_DPO_CR */
}


/*******************************************************************************/
static bool rfalWaitRxOn( void )
{
    uint8_t n;
    
    for( n = 0; n < RFAL_RX_REST_ON_WAIT; n++ )
    {
        if( st25r500CheckReg( ST25R500_REG_STATUS2, ST25R500_REG_STATUS2_rx_on, ST25R500_REG_STATUS2_rx_on ) )
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
        st25r500ReadMultipleRegisters( ST25R500_REG_FIFO_STATUS1, gRFAL.fifo.status, ST25R500_FIFO_STATUS_LEN );
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
    
    result  = ((((uint16_t)gRFAL.fifo.status[RFAL_FIFO_STATUS_REG2] & ST25R500_REG_FIFO_STATUS2_fifo_b8) >> ST25R500_REG_FIFO_STATUS2_fifo_b_shift) << RFAL_BITS_IN_BYTE);
    result |= (((uint16_t)gRFAL.fifo.status[RFAL_FIFO_STATUS_REG1]) & 0x00FFU);
    return result;
}


/*******************************************************************************/
static bool rfalFIFOStatusIsIncompleteByte( void )
{
    rfalFIFOStatusUpdate();
    return ((gRFAL.fifo.status[RFAL_FIFO_STATUS_REG2] & ST25R500_REG_FIFO_STATUS2_fifo_lb_mask) != 0U);
}


/*******************************************************************************/
static bool rfalFIFOStatusIsMissingPar( void )
{
    rfalFIFOStatusUpdate();
    return ((gRFAL.fifo.status[RFAL_FIFO_STATUS_REG2] & ST25R500_REG_FIFO_STATUS2_np_lb) != 0U);
}


/*******************************************************************************/
static uint8_t rfalFIFOGetNumIncompleteBits( void )
{
    rfalFIFOStatusUpdate();
    return ((gRFAL.fifo.status[RFAL_FIFO_STATUS_REG2] & ST25R500_REG_FIFO_STATUS2_fifo_lb_mask) >> ST25R500_REG_FIFO_STATUS2_fifo_lb_shift);
}


#if RFAL_FEATURE_NFCA

/*******************************************************************************/
ReturnCode rfalISO14443ATransceiveShortFrame( rfal14443AShortFrameCmd txCmd, uint8_t* rxBuf, uint8_t rxBufLen, uint16_t* rxRcvdLen, uint32_t fwt )
{
    rfalTransceiveContext ctx;
    ReturnCode            ret;
    uint8_t               cmd;

    /* Check if RFAL is properly initialized */
    if( (!st25r500IsTxEnabled()) || (gRFAL.state < RFAL_STATE_MODE_SET) || (( gRFAL.mode != RFAL_MODE_POLL_NFCA ) && ( gRFAL.mode != RFAL_MODE_POLL_NFCA_T1T )) )
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
    st25r500SetRegisterBits( ST25R500_REG_PROTOCOL_RX1, ST25R500_REG_PROTOCOL_RX1_antcl );
    
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
    st25r500ClrRegisterBits( ST25R500_REG_PROTOCOL_RX1, ST25R500_REG_PROTOCOL_RX1_antcl );
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
    st25r500SetRegisterBits( ST25R500_REG_PROTOCOL_RX1, (ST25R500_REG_PROTOCOL_RX1_antcl | ST25R500_REG_PROTOCOL_RX1_rx_nbtx) );
    
    
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
    st25r500GetInterrupt( ST25R500_IRQ_MASK_COL );
    st25r500EnableInterrupts( ST25R500_IRQ_MASK_COL );
    
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
       st25r500ReadRegister( ST25R500_REG_COLLISION, &collData);

       (*gRFAL.nfcaData.bytesToSend) = ((collData >> ST25R500_REG_COLLISION_c_byte_shift) & 0x0FU); /* 4-bits Byte information */
       (*gRFAL.nfcaData.bitsToSend)  = ((collData >> ST25R500_REG_COLLISION_c_bit_shift)  & 0x07U); /* 3-bits bit information  */
    }
    
   
    /*******************************************************************************/
    /* Disable Collision interrupt */
    st25r500DisableInterrupts( (ST25R500_IRQ_MASK_COL) );
    
    /* Disable collision detection again */
    st25r500ClrRegisterBits( ST25R500_REG_PROTOCOL_RX1, (ST25R500_REG_PROTOCOL_RX1_antcl | ST25R500_REG_PROTOCOL_RX1_rx_nbtx) );
    /*******************************************************************************/
    
    /* Restore common Analog configurations for this mode */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | rfalConvBR2ACBR(gRFAL.txBR) | RFAL_ANALOG_CONFIG_TX) );
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | rfalConvBR2ACBR(gRFAL.rxBR) | RFAL_ANALOG_CONFIG_RX) );
    
    /* If DPO used, request to perform the adjustment as default settings have been used */
    rfalDpoReqAdjust();
    
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
    st25r500SetRegisterBits( ST25R500_REG_PROTOCOL_RX1, ST25R500_REG_PROTOCOL_RX1_antcl );
    
    
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
    st25r500GetInterrupt( ST25R500_IRQ_MASK_COL );
    st25r500EnableInterrupts( ST25R500_IRQ_MASK_COL );
    
    /*******************************************************************************/
    /* Run Transceive blocking */
    ret = rfalTransceiveRunBlockingTx();
    if( ret == RFAL_ERR_NONE)
    {
        ret = rfalTransceiveBlockingRx();
    }
    
    /* REMARK: CRC is being reported due to stream mode limitation on 11/16, to be re-evaluated */
    if( ret == RFAL_ERR_NONE )
    {
        *ctx.rxRcvdLen += (uint16_t)rfalConvBytesToBits(RFAL_CRC_LEN);
    }   
    
    /*******************************************************************************/
    /* Disable Collision interrupt */
    st25r500DisableInterrupts( (ST25R500_IRQ_MASK_COL) );
    
    /* Disable collision detection again */
    st25r500ClrRegisterBits( ST25R500_REG_PROTOCOL_RX1, ST25R500_REG_PROTOCOL_RX1_antcl );
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
    if( (!st25r500IsTxEnabled()) || (gRFAL.state < RFAL_STATE_MODE_SET) || ( gRFAL.mode != RFAL_MODE_POLL_NFCV ) )
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
    while( st25r500IsGPTRunning() )  { /* MISRA 15.6: mandatory brackets */ };

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
    st25r500SetRegisterBits( ST25R500_REG_PROTOCOL_RX1, ST25R500_REG_PROTOCOL_RX1_antcl );
    
    /* Also enable bit collision interrupt */
    st25r500GetInterrupt( ST25R500_IRQ_MASK_COL );
    st25r500EnableInterrupts( ST25R500_IRQ_MASK_COL );
    
    /* Check if Observation Mode is enabled and set it on ST25R */
    rfalCheckEnableObsModeTx();
    
    /* Send EOF */
    st25r500ExecuteCommand( ST25R500_CMD_TRANSMIT_EOF );
    
    /* Wait for TXE */
    if( st25r500WaitForInterruptsTimed( ST25R500_IRQ_MASK_TXE, (uint16_t)RFAL_MAX( rfalConv1fcToMs( RFAL_ISO15693_FWT ), RFAL_ST25R500_SW_TMR_MIN_1MS ) ) == 0U )
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
    st25r500ClrRegisterBits( ST25R500_REG_PROTOCOL_RX1, ST25R500_REG_PROTOCOL_RX1_antcl );
    
    /* Disable Collision interrupt */
    st25r500DisableInterrupts( (ST25R500_IRQ_MASK_COL) );
    
    return ret;
}

#endif /* RFAL_FEATURE_NFCV */


#if RFAL_FEATURE_NFCF

/*******************************************************************************/
ReturnCode rfalFeliCaPoll( rfalFeliCaPollSlots slots, uint16_t sysCode, uint8_t reqCode, rfalFeliCaPollRes* pollResList, uint8_t pollResListSize, uint8_t *devicesDetected, uint8_t *collisionsDetected )
{
    ReturnCode ret;

    RFAL_EXIT_ON_ERR( ret, rfalStartFeliCaPoll( slots, sysCode, reqCode, pollResList, pollResListSize, devicesDetected, collisionsDetected ) );
    rfalRunBlocking( ret, rfalGetFeliCaPollStatus() );
    
    return ret;
}


/*******************************************************************************/
ReturnCode rfalStartFeliCaPoll( rfalFeliCaPollSlots slots, uint16_t sysCode, uint8_t reqCode, rfalFeliCaPollRes* pollResList, uint8_t pollResListSize, uint8_t *devicesDetected, uint8_t *collisionsDetected )
{
    ReturnCode        ret;
    uint8_t           frame[RFAL_FELICA_POLL_REQ_LEN - RFAL_FELICA_LEN_LEN];  /* LEN is added by ST25R automatically */
    uint8_t           frameIdx;
    
    /* Check if RFAL is properly initialized */
    if( (gRFAL.state < RFAL_STATE_MODE_SET) || ( gRFAL.mode != RFAL_MODE_POLL_NFCF ) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    frameIdx                   = 0;
    gRFAL.nfcfData.colDetected = 0;
    gRFAL.nfcfData.devDetected = 0;
    
    /*******************************************************************************/
    /* Compute SENSF_REQ frame */
    frame[frameIdx++] = (uint8_t)FELICA_CMD_POLLING; /* CMD: SENF_REQ                       */   
    frame[frameIdx++] = (uint8_t)(sysCode >> 8);     /* System Code (SC)                    */
    frame[frameIdx++] = (uint8_t)(sysCode & 0xFFU);  /* System Code (SC)                    */
    frame[frameIdx++] = reqCode;                     /* Communication Parameter Request (RC)*/
    frame[frameIdx++] = (uint8_t)slots;              /* TimeSlot (TSN)                      */
    
    
    /*******************************************************************************/
    /* NRT should not stop on reception - Fake EMD which uses NRT in nrt_emv       *
     * RFAL_ERRORHANDLING_EMD has no special handling for NFC-F mode               */
    gRFAL.nfcfData.curHandling = gRFAL.conf.eHandling;
    gRFAL.conf.eHandling       = RFAL_ERRORHANDLING_EMD;
    
    
    /*******************************************************************************/
    /* Run transceive blocking, 
     * Calculate Total Response Time in(64/fc): 
     *                       512 PICC process time + (n * 256 Time Slot duration)  */       
    RFAL_EXIT_ON_ERR( ret, rfalTransceiveBlockingTx( frame, 
                                    (uint16_t)frameIdx, 
                                    (uint8_t*)gRFAL.nfcfData.pollResponses,
                                    RFAL_FELICA_POLL_RES_LEN, 
                                    &gRFAL.nfcfData.actLen,
                                    (RFAL_TXRX_FLAGS_DEFAULT),
                                    rfalConv64fcTo1fc( RFAL_FELICA_POLL_DELAY_TIME + (RFAL_FELICA_POLL_SLOT_TIME * ((uint32_t)slots + 1U)) ) ) );
                                    
   /* Store context */
   gRFAL.nfcfData.pollResList        = pollResList;
   gRFAL.nfcfData.pollResListSize    = pollResListSize;
   gRFAL.nfcfData.devicesDetected    = devicesDetected;
   gRFAL.nfcfData.collisionsDetected = collisionsDetected;
   
   return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalGetFeliCaPollStatus( void )
{
    ReturnCode ret;
    
    /* Check if RFAL is properly initialized */
    if( (gRFAL.state != RFAL_STATE_TXRX) || ( gRFAL.mode != RFAL_MODE_POLL_NFCF ) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Wait until transceive has terminated */
    RFAL_EXIT_ON_BUSY( ret, rfalGetTransceiveStatus() );
    
    /* Upon timeout the full Poll Delay + (Slot time)*(nbSlots) has expired */
    if( ret != RFAL_ERR_TIMEOUT )  
    {
        /* Reception done, reEnabled Rx for following Slot */
        /* The Rx reEnable is done before the check of NRT to be as fast as possible for the upcoming slot       *
         *  Tslot = 1208us | SENSF_RES (19 payload bytes at 212) = 1135us -> Potentially ~75us between responses */
        st25r500ExecuteCommand( ST25R500_CMD_UNMASK_RECEIVE_DATA );
        st25r500ExecuteCommand( ST25R500_CMD_CLEAR_RXGAIN );
        rfalFIFOStatusClear();
        
        /* If the reception was OK, new device found */
        if( ret == RFAL_ERR_NONE )
        {
           gRFAL.nfcfData.devDetected++;
           
           /* Overwrite the Transceive context for the next reception */
           gRFAL.TxRx.ctx.rxBuf = (uint8_t*)gRFAL.nfcfData.pollResponses[gRFAL.nfcfData.devDetected];
        }
        /* If the reception was not OK, mark as collision */
        else
        {
            gRFAL.nfcfData.colDetected++;
        }
        
        /* Check whether that NRT has not expired meanwhile */
        if( st25r500CheckReg( ST25R500_REG_STATUS2, ST25R500_REG_STATUS2_nrt_on, ST25R500_REG_STATUS2_nrt_on ) )
        {
            /* Jump again into transceive Rx state for the following reception */
            gRFAL.TxRx.status = RFAL_ERR_BUSY;
            gRFAL.state       = RFAL_STATE_TXRX;
            gRFAL.TxRx.state  = RFAL_TXRX_STATE_RX_IDLE;
            return RFAL_ERR_BUSY;
        }
        
        /* In case NRT has expired meanwhile, ensure that Rx is disabled */
        st25r500ExecuteCommand( ST25R500_CMD_MASK_RECEIVE_DATA );
    }

    
    /*******************************************************************************/
    /* Back to previous error handling (restore NRT to normal mode)                */
    gRFAL.conf.eHandling = gRFAL.nfcfData.curHandling;
    
    
    /*******************************************************************************/
    /* Assign output parameters if requested                                       */
    if( (gRFAL.nfcfData.pollResList != NULL) && (gRFAL.nfcfData.pollResListSize > 0U) && (gRFAL.nfcfData.devDetected > 0U) )
    {
        RFAL_MEMCPY( gRFAL.nfcfData.pollResList, gRFAL.nfcfData.pollResponses, (RFAL_FELICA_POLL_RES_LEN * (uint32_t)RFAL_MIN(gRFAL.nfcfData.pollResListSize, gRFAL.nfcfData.devDetected) ) );
    }
    
    if( gRFAL.nfcfData.devicesDetected != NULL )
    {
        *gRFAL.nfcfData.devicesDetected = gRFAL.nfcfData.devDetected;
    }
    
    if( gRFAL.nfcfData.collisionsDetected != NULL )
    {
        *gRFAL.nfcfData.collisionsDetected = gRFAL.nfcfData.colDetected;
    }

    return (( (gRFAL.nfcfData.colDetected != 0U) || (gRFAL.nfcfData.devDetected != 0U)) ? RFAL_ERR_NONE : ret);
}

#endif /* RFAL_FEATURE_NFCF */


/*****************************************************************************
 *  Listen Mode                                                              *  
 *****************************************************************************/

/*******************************************************************************/
bool rfalIsExtFieldOn( void )
{
    /* EFD output only available in CE mode */
    return st25r500IsExtFieldOn();
}

#if RFAL_FEATURE_LISTEN_MODE

/*******************************************************************************/
ReturnCode rfalListenStart( uint32_t lmMask, const rfalLmConfPA *confA, const rfalLmConfPB *confB, const rfalLmConfPF *confF, uint8_t *rxBuf, uint16_t rxBufLen, uint16_t *rxLen )
{
    rfalCEMem   CEMem;       /*  PRQA S 0759 # MISRA 19.2 - Allocating Union where members are of the same type, just different names.  Thus no problem can occur. */
    uint8_t*    pCEMem;
    uint8_t     autoResp;
    
    
    /* Check if RFAL is initialized */
    if( gRFAL.state < RFAL_STATE_INIT )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    gRFAL.Lm.state  = RFAL_LM_STATE_NOT_INIT;
    gRFAL.Lm.mdIrqs = ST25R500_IRQ_MASK_NONE;
    gRFAL.Lm.mdReg  = ST25R500_REG_PROTOCOL_om_sbrdm;
    
    RFAL_MEMSET( (uint8_t*)&CEMem, 0x00, sizeof(rfalCEMem) );
    
    /* By default disable all automatic responses */     
    autoResp = 0x00;
    
    
    /*******************************************************************************/
    if( (lmMask & RFAL_LM_MASK_NFCA) != 0U )
    {
        /* Check if the conf has been provided */
        if( confA == NULL )
        {
            return RFAL_ERR_PARAM;
        }
        
        pCEMem = (uint8_t*)&CEMem;
        
        /*******************************************************************************/
        /* Check and set supported NFCID Length */
        switch(confA->nfcidLen)
        {
            case RFAL_LM_NFCID_LEN_04:
                st25r500ChangeRegisterBits( ST25R500_REG_CE_CONFIG2, ST25R500_REG_CE_CONFIG2_nfc_id, ST25R500_REG_CE_CONFIG2_nfc_id_4bytes );
                break;
                
            case RFAL_LM_NFCID_LEN_07:
                st25r500ChangeRegisterBits( ST25R500_REG_CE_CONFIG2, ST25R500_REG_CE_CONFIG2_nfc_id, ST25R500_REG_CE_CONFIG2_nfc_id_7bytes );
                break;
                
            default:
                return RFAL_ERR_PARAM;
        }
        
        /*******************************************************************************/
        /* Set NFCID */
        RFAL_MEMCPY( pCEMem, confA->nfcid, RFAL_NFCID1_DOUBLE_LEN );
        pCEMem = &pCEMem[RFAL_NFCID1_DOUBLE_LEN];                  /* MISRA 18.4 */
        
        /* Set SENS_RES */
        RFAL_MEMCPY( pCEMem, confA->SENS_RES, RFAL_LM_SENS_RES_LEN );
        pCEMem = &pCEMem[RFAL_LM_SENS_RES_LEN];                    /* MISRA 18.4 */
        
        /* Set SEL_RES */
        *(pCEMem++) = ( (confA->nfcidLen == RFAL_LM_NFCID_LEN_04) ? ( confA->SEL_RES & ~RFAL_LM_NFCID_INCOMPLETE ) : (confA->SEL_RES | RFAL_LM_NFCID_INCOMPLETE) );
        *(pCEMem++) = ( confA->SEL_RES & ~RFAL_LM_NFCID_INCOMPLETE );
        *(pCEMem++) = ( confA->SEL_RES & ~RFAL_LM_NFCID_INCOMPLETE );
        
        /* Write into CEMem-A */
        st25r500WriteMultipleRegisters( ST25R500_REG_CEM_A, CEMem.CEMem_A, ST25R500_CEM_A_LEN );
        st25r500ReadMultipleRegisters( ST25R500_REG_CEM_A, CEMem.CEMem_A, ST25R500_CEM_A_LEN );
        
        
        /*******************************************************************************/
        /* Enable automatic responses for A */
        autoResp |= ST25R500_REG_CE_CONFIG1_en_106_ac_a;
        gRFAL.Lm.mdReg  = ST25R500_REG_PROTOCOL_om_iso14443a;
        
        gRFAL.Lm.mdIrqs |= (ST25R500_IRQ_MASK_RXE);
    }
    
    /*******************************************************************************/
    if( (lmMask & RFAL_LM_MASK_NFCB) != 0U )
    {
        /* Check if the conf has been provided */
        if( confB == NULL )
        {
            return RFAL_ERR_PARAM;
        }
        
        return RFAL_ERR_NOTSUPP;
    }
    
    /*******************************************************************************/
    if( (lmMask & RFAL_LM_MASK_NFCF) != 0U )
    {
        pCEMem = (uint8_t*)CEMem.CEMem_F;
                       
        /* Check if the conf has been provided */
        if( confF == NULL )
        {
            return RFAL_ERR_PARAM;
        }
        
        /*******************************************************************************/
        /* Set System Code */
        RFAL_MEMCPY( pCEMem, confF->SC, RFAL_LM_SENSF_SC_LEN );
        pCEMem = &pCEMem[RFAL_LM_SENSF_SC_LEN];             /* MISRA 18.4 */
                            
        /* Set SENSF_RES */
        RFAL_MEMCPY( pCEMem, confF->SENSF_RES, RFAL_LM_SENSF_RES_LEN );

        /* Set RD bytes to 0x00 as ST25R500 cannot support advances features */
        pCEMem[RFAL_LM_SENSF_RD0_POS] = 0x00;   /* NFC Forum Digital 1.1 Table 46: 0x00                   */
        pCEMem[RFAL_LM_SENSF_RD1_POS] = 0x00;   /* NFC Forum Digital 1.1 Table 47: No automatic bit rates */
        
        pCEMem = &pCEMem[RFAL_LM_SENS_RES_LEN];             /* MISRA 18.4 */
                               
        /* Write into CEMem-F */
        st25r500WriteMultipleRegisters( ST25R500_REG_CEM_F, CEMem.CEMem_F, ST25R500_CEM_F_LEN );        
        
        
        /*******************************************************************************/
        /* Enable automatic responses for F */
        autoResp |= ST25R500_REG_CE_CONFIG1_en_212_424_1r;
        gRFAL.Lm.mdReg  = ST25R500_REG_PROTOCOL_om_felica;
        
        /* In CE NFC-F any data without error will be passed to FIFO, to support CUP */
        gRFAL.Lm.mdIrqs |= (ST25R500_IRQ_MASK_RXE);
    }
    
    /*******************************************************************************/
    if( (lmMask & RFAL_LM_MASK_ACTIVE_P2P) != 0U )
    {
        return RFAL_ERR_NOTSUPP;
    }
    
    
    
    /* Check if one of the modes were selected */
    if( autoResp != 0x00U )
    {
        gRFAL.state     = RFAL_STATE_LM;
        gRFAL.Lm.mdMask = lmMask;
        
        gRFAL.Lm.rxBuf    = rxBuf;
        gRFAL.Lm.rxBufLen = rxBufLen;
        gRFAL.Lm.rxLen    = rxLen;
        *gRFAL.Lm.rxLen   = 0;
        gRFAL.Lm.dataFlag = false;
        gRFAL.Lm.iniFlag  = true;
        
        
        /* Apply the Automatic Responses configuration */
        st25r500ChangeRegisterBits( ST25R500_REG_CE_CONFIG1, (ST25R500_REG_CE_CONFIG1_ce_signal_all | ST25R500_REG_CE_CONFIG1_en_other_idle | ST25R500_REG_CE_CONFIG1_en_dsl_a | ST25R500_REG_CE_CONFIG1_en_ce4a  | ST25R500_REG_CE_CONFIG1_en_106_ac_a | ST25R500_REG_CE_CONFIG1_en_212_424_1r), 
                                                             ( ST25R500_REG_CE_CONFIG1_ce_signal_all | ST25R500_REG_CE_CONFIG1_en_other_idle | autoResp) );
        
        /* Disable GPT trigger source */
        st25r500ChangeRegisterBits( ST25R500_REG_NRT_GPT_CONF, ST25R500_REG_NRT_GPT_CONF_gptc_mask, ST25R500_REG_NRT_GPT_CONF_gptc_no_trigger );
      
        /* On Bit Rate Detection Mode ST25R will filter incoming frames during MRT time starting on External Field On event, use 512/fc steps */
        st25r500ChangeRegisterBits(ST25R500_REG_MRT1, ST25R500_REG_MRT1_mrt_step_mask, ST25R500_REG_MRT1_mrt_step_512fc );
        st25r500WriteRegister( ST25R500_REG_MRT2, (uint8_t)rfalConv1fcTo512fc( RFAL_LM_GT ) );
        
        
        /* Restore default settings on NFCIP1 mode, parity and CRC */
        st25r500ChangeRegisterBits( ST25R500_REG_PROTOCOL_TX1, (ST25R500_REG_PROTOCOL_TX1_a_tx_par | ST25R500_REG_PROTOCOL_TX1_tx_crc | ST25R500_REG_PROTOCOL_TX1_a_nfc_f0), (ST25R500_REG_PROTOCOL_TX1_a_tx_par | ST25R500_REG_PROTOCOL_TX1_tx_crc) );
        st25r500SetRegisterBits( ST25R500_REG_PROTOCOL_RX1, (ST25R500_REG_PROTOCOL_RX1_a_rx_par | ST25R500_REG_PROTOCOL_RX1_rx_crc) );
        
        /* External Field Detector enabled as Automatics on rfalInitialize() */
        
        /* Enable CE mode */
        st25r500ChangeRegisterBits( ST25R500_REG_OPERATION, (ST25R500_REG_OPERATION_ce_en | ST25R500_REG_OPERATION_wu_en | ST25R500_REG_OPERATION_tx_en | ST25R500_REG_OPERATION_rx_en), (ST25R500_REG_OPERATION_ce_en | ST25R500_REG_OPERATION_rx_en) );
        
        /* Set Analog configurations for generic Listen mode */
        /* Not on SetState(POWER OFF) as otherwise would be applied on every Field Event */
        rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_LISTEN_ON) );

        /* If both are enabled need to use bitrate detection */
        if ( ((autoResp & ST25R500_REG_CE_CONFIG1_en_212_424_1r) != 0U) && ((autoResp & ST25R500_REG_CE_CONFIG1_en_106_ac_a) != 0U) )
        { 
            gRFAL.Lm.mdReg  = ST25R500_REG_PROTOCOL_om_sbrdm;
        }
        
        /* Initialize as POWER_OFF and set proper mode in RF Chip */
        rfalListenSetState( RFAL_LM_STATE_POWER_OFF );
    }
    else
    {
        return RFAL_ERR_REQUEST;   /* Listen Start called but no mode was enabled */
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
static ReturnCode rfalRunListenModeWorker( void )
{
    uint32_t  irqs;
    uint8_t   tmp;
    
    if( gRFAL.state != RFAL_STATE_LM )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    switch( gRFAL.Lm.state )
    {
        /*******************************************************************************/
        case RFAL_LM_STATE_POWER_OFF:
            
            irqs = st25r500GetInterrupt( (  ST25R500_IRQ_MASK_EON ) );
            if( irqs == ST25R500_IRQ_MASK_NONE )
            {
                break;  /* No interrupt to process */
            }
            
            if( (irqs & ST25R500_IRQ_MASK_EON) != 0U )
            {
                rfalListenSetState( RFAL_LM_STATE_IDLE );
            }
            else
            {
                break;
            }
            /* fall through */
            
              
        /*******************************************************************************/
        case RFAL_LM_STATE_IDLE:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
        case RFAL_LM_STATE_SLEEP_A:
        case RFAL_LM_STATE_SLEEP_B:
        case RFAL_LM_STATE_SLEEP_AF:
            
            irqs = st25r500GetInterrupt( ( ST25R500_IRQ_MASK_NFCT | ST25R500_IRQ_MASK_EOF | ST25R500_IRQ_MASK_CE_SC | ST25R500_IRQ_MASK_TXE) );
            if( irqs == ST25R500_IRQ_MASK_NONE )
            {
                break;  /* No interrupt to process */
            }
            
            /* Retrieve CE status */
            st25r500ReadRegister( ST25R500_REG_CE_STATUS1, &tmp );
            
            if( (irqs & ST25R500_IRQ_MASK_NFCT) != 0U )
            {
                gRFAL.Lm.brDetected = (rfalBitRate) ((uint8_t)((tmp & ST25R500_REG_CE_STATUS1_nfc_rate_mask) >> ST25R500_REG_CE_STATUS1_nfc_rate_shift)); /* PRQA S 4342 # MISRA 10.5 - Guaranteed that no invalid enum values may be created. See also equalityGuard_RFAL_BR_106 ff.*/
            }
            
            /* If EOF has already been received processing of other events is neglectable */
            if( ((irqs & ST25R500_IRQ_MASK_EOF) != 0U)  && (!gRFAL.Lm.dataFlag) )
            {
                rfalListenSetState( RFAL_LM_STATE_POWER_OFF );
            }
            else if( ((irqs & ST25R500_IRQ_MASK_CE_SC) != 0U) )
            {
                /* CE state  */
                tmp &= ST25R500_REG_CE_STATUS1_ce_state_mask;
                
                if( (tmp == ST25R500_REG_CE_STATUS1_ce_state_ce_f) && ((gRFAL.Lm.mdMask & RFAL_LM_MASK_NFCF) != 0U) )
                {
                    gRFAL.Lm.brDetected = RFAL_BR_212;                /* Not really relevant, chip will handle 212 and 424 always in parallel */
                    rfalListenSetState( RFAL_LM_STATE_READY_F );
                }
                else if( (tmp > ST25R500_REG_CE_STATUS1_ce_state_sleep_a) && ((gRFAL.Lm.mdMask & RFAL_LM_MASK_NFCA) != 0U) )
                {
                    gRFAL.Lm.brDetected = RFAL_BR_106;
                    rfalListenSetState( RFAL_LM_STATE_READY_Ax );
                }
                else if( (tmp > ST25R500_REG_CE_STATUS1_ce_state_idle) && ((gRFAL.Lm.mdMask & RFAL_LM_MASK_NFCA) != 0U) )
                {
                    gRFAL.Lm.brDetected = RFAL_BR_106;
                    rfalListenSetState( RFAL_LM_STATE_READY_A );
                }
                else
                {
                    /* MISRA 15.7 - Empty else */
                }
            }
            else
            {
                /* MISRA 15.7 - Empty else */
            }
            break;
            
            /*******************************************************************************/
            case RFAL_LM_STATE_READY_F:
                
                irqs = st25r500GetInterrupt( ( ST25R500_IRQ_MASK_RXE | ST25R500_IRQ_MASK_EOF | ST25R500_IRQ_MASK_RX_ERR) );
                if( irqs == ST25R500_IRQ_MASK_NONE )
                {
                    break;  /* No interrupt to process */
                }

                /* If EOF has already been received processing of other events is neglectable */
                if( (irqs & ST25R500_IRQ_MASK_EOF) != 0U )
                {
                    rfalListenSetState( RFAL_LM_STATE_POWER_OFF );
                }
                else if( (irqs & ST25R500_IRQ_MASK_RXE) != 0U )
                {
                    if( (irqs & ST25R500_IRQ_MASK_RX_ERR) != 0U )
                    {
                        if( (!st25r500CheckReg( ST25R500_REG_STATUS_STATIC3, ST25R500_REG_STATUS_STATIC3_s_mask, 0x00)) )
                        {
                            st25r500ExecuteCommand( ST25R500_CMD_CLEAR_FIFO );
                            st25r500ExecuteCommand( ST25R500_CMD_UNMASK_RECEIVE_DATA );
                            break; /* A bad reception occurred, remain in same state */
                        }
                    }
                    
                    /* Retrieve received data */
                    *gRFAL.Lm.rxLen = st25r500GetNumFIFOBytes();
                    st25r500ReadFifo( gRFAL.Lm.rxBuf, RFAL_MIN( *gRFAL.Lm.rxLen, rfalConvBitsToBytes(gRFAL.Lm.rxBufLen) ) );
                    
                    /* Check if the data we got has at least the CRC and remove it, otherwise leave at 0 */
                    *gRFAL.Lm.rxLen  -= ((*gRFAL.Lm.rxLen > RFAL_CRC_LEN) ? RFAL_CRC_LEN : *gRFAL.Lm.rxLen);
                    *gRFAL.Lm.rxLen  = (uint16_t)rfalConvBytesToBits( *gRFAL.Lm.rxLen );
                    gRFAL.Lm.dataFlag = true;
                }
                else if( (irqs & ST25R500_IRQ_MASK_RXE_CE) != 0U )
                {
                    break;          /* Remain in same state */
                }
                else
                {
                    /* MISRA 15.7 - Empty else */
                }
                break;
                
            /*******************************************************************************/
            case RFAL_LM_STATE_READY_A:
            case RFAL_LM_STATE_READY_Ax:
                
                irqs = st25r500GetInterrupt( (  ST25R500_IRQ_MASK_EOF | ST25R500_IRQ_MASK_CE_SC  ) );
                if( irqs == ST25R500_IRQ_MASK_NONE )
                {
                    break;  /* No interrupt to process */
                }
                
                /* If EOF has already been received processing of other events is neglectable */
                if( (irqs & ST25R500_IRQ_MASK_EOF) != 0U )
                {
                    rfalListenSetState( RFAL_LM_STATE_POWER_OFF );
                }
                else if( ((irqs & ST25R500_IRQ_MASK_CE_SC) != 0U) )
                {
                    /* Retrieve CE status */
                    st25r500ReadRegister( ST25R500_REG_CE_STATUS1, &tmp );
                    
                    if( (tmp & ST25R500_REG_CE_STATUS1_ce_state_mask) == ST25R500_REG_CE_STATUS1_ce_state_active_ax )
                    {
                        rfalListenSetState( RFAL_LM_STATE_ACTIVE_Ax );
                    }
                    else if( (tmp & ST25R500_REG_CE_STATUS1_ce_state_mask) == ST25R500_REG_CE_STATUS1_ce_state_active_a )
                    {
                        rfalListenSetState( RFAL_LM_STATE_ACTIVE_A );
                    }
                    else
                    {
                        /* MISRA 15.7 - Empty else */
                    }
                }
                else
                {
                    /* MISRA 15.7 - Empty else */
                }
                break;
            
            /*******************************************************************************/                
            case RFAL_LM_STATE_ACTIVE_A:
            case RFAL_LM_STATE_ACTIVE_Ax:
                
                irqs = st25r500GetInterrupt( ( ST25R500_IRQ_MASK_RXE | ST25R500_IRQ_MASK_EOF | ST25R500_IRQ_MASK_RX_ERR) );
                if( irqs == ST25R500_IRQ_MASK_NONE )
                {                        
                    break;  /* No interrupt to process */
                }

                /* If EOF has already been received processing of other events is neglectable */
                if( (irqs & ST25R500_IRQ_MASK_EOF) != 0U )
                {
                    rfalListenSetState( RFAL_LM_STATE_POWER_OFF );
                }
                else if( (irqs & ST25R500_IRQ_MASK_RXE) != 0U )
                {
                    *gRFAL.Lm.rxLen = st25r500GetNumFIFOBytes();
                    
                    if( ((!st25r500CheckReg( ST25R500_REG_STATUS_STATIC3, ST25R500_REG_STATUS_STATIC3_s_mask, 0x00)) && ( (irqs & ST25R500_IRQ_MASK_RX_ERR) != 0U )) || (*gRFAL.Lm.rxLen <= RFAL_CRC_LEN)  )
                    {
                        /* Clear rx context and FIFO */
                        *gRFAL.Lm.rxLen = 0;
                        st25r500ExecuteCommand( ST25R500_CMD_CLEAR_FIFO );
                        st25r500ExecuteCommand( ST25R500_CMD_UNMASK_RECEIVE_DATA );
                        
                        /* Check if we should go to IDLE or Sleep */ 
                        if( gRFAL.Lm.state == RFAL_LM_STATE_ACTIVE_Ax )
                        {
                            rfalListenSleepStart( RFAL_LM_STATE_SLEEP_A, gRFAL.Lm.rxBuf, gRFAL.Lm.rxBufLen, gRFAL.Lm.rxLen );
                        }
                        else
                        {
                            rfalListenSetState( RFAL_LM_STATE_IDLE );
                        }
                        
                        st25r500DisableInterrupts( ST25R500_IRQ_MASK_RXE );
                        break;
                    }

                    /* Remove CRC from length */
                    *gRFAL.Lm.rxLen -= RFAL_CRC_LEN;
                    
                    /* Retrieve received data */
                    st25r500ReadFifo( gRFAL.Lm.rxBuf, RFAL_MIN( *gRFAL.Lm.rxLen, rfalConvBitsToBytes(gRFAL.Lm.rxBufLen) ) );                    
                    *gRFAL.Lm.rxLen   = (uint16_t)rfalConvBytesToBits( *gRFAL.Lm.rxLen );
                    gRFAL.Lm.dataFlag = true;
                }
                else
                {
                    /* MISRA 15.7 - Empty else */
                }
                break;
                
            /*******************************************************************************/
            case RFAL_LM_STATE_CARDEMU_4A:
            case RFAL_LM_STATE_CARDEMU_4B:
            case RFAL_LM_STATE_CARDEMU_3:
            case RFAL_LM_STATE_TARGET_F:
            case RFAL_LM_STATE_TARGET_A:
                break;
                
            /*******************************************************************************/
            default:
                return RFAL_ERR_WRONG_STATE;
    }
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalListenStop( void )
{
        
    /* Check if RFAL is initialized */
    if( gRFAL.state < RFAL_STATE_INIT )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    gRFAL.Lm.state = RFAL_LM_STATE_NOT_INIT;
    
    /* Check if Observation Mode was enabled and disable it on ST25R */
    rfalCheckDisableObsMode();
    
    /* Disable Tx , Rx and CE mode */
    st25r500ClrRegisterBits(ST25R500_REG_OPERATION, (ST25R500_REG_OPERATION_ce_en | ST25R500_REG_OPERATION_rx_en | ST25R500_REG_OPERATION_tx_en) );
    
    /* Re-Enable the Oscillator if not running */
    st25r500OscOn();
    
    /* Disable all automatic responses */
    st25r500ClrRegisterBits( ST25R500_REG_CE_CONFIG1, (ST25R500_REG_CE_CONFIG1_en_106_ac_a | ST25R500_REG_CE_CONFIG1_en_212_424_1r) );
    
    
    /* As there's no Off mode, set default value: ISO14443A with automatic RF Collision Avoidance Off */
    st25r500WriteRegister( ST25R500_REG_PROTOCOL, (ST25R500_REG_PROTOCOL_rx_rate_106_26 | ST25R500_REG_PROTOCOL_tx_rate_106 | ST25R500_REG_PROTOCOL_om_iso14443a) );
    
    st25r500DisableInterrupts( (ST25R500_IRQ_MASK_CE_SC | ST25R500_IRQ_MASK_RXE_CE | ST25R500_IRQ_MASK_NFCT | ST25R500_IRQ_MASK_OSC | ST25R500_IRQ_MASK_TXE ) );
    st25r500GetInterrupt( (ST25R500_IRQ_MASK_CE_SC | ST25R500_IRQ_MASK_RXE_CE | ST25R500_IRQ_MASK_NFCT | ST25R500_IRQ_MASK_OSC | ST25R500_IRQ_MASK_TXE ) );
    
    /* Set Analog configurations for Listen Off event */
    rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_LISTEN_OFF) );
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalListenSleepStart( rfalLmState sleepSt, uint8_t *rxBuf, uint16_t rxBufLen, uint16_t *rxLen )
{

    /* Check if RFAL is not initialized */
    if( gRFAL.state < RFAL_STATE_INIT )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    switch(sleepSt)
    {
        /*******************************************************************************/
        case RFAL_LM_STATE_SLEEP_A:
            
            /* Enable automatic responses for A */
            st25r500SetRegisterBits( ST25R500_REG_CE_CONFIG1, ST25R500_REG_CE_CONFIG1_en_106_ac_a );
            
            /* Reset NFC-A target */
            st25r500ChangeRegisterBits( ST25R500_REG_CE_STATUS1, ST25R500_REG_CE_STATUS1_ce_state_mask, ST25R500_REG_CE_STATUS1_ce_state_sleep_a );
            break;
            
        /*******************************************************************************/
        case RFAL_LM_STATE_SLEEP_AF:
            
            /* Enable automatic responses for A + F */
            st25r500SetRegisterBits( ST25R500_REG_CE_CONFIG1, (ST25R500_REG_CE_CONFIG1_en_106_ac_a | ST25R500_REG_CE_CONFIG1_en_212_424_1r) );
            
            /* Reset NFC-A target state */
            st25r500ChangeRegisterBits( ST25R500_REG_CE_STATUS1, ST25R500_REG_CE_STATUS1_ce_state_mask, ST25R500_REG_CE_STATUS1_ce_state_sleep_a );
            
            /* Set Bit Rate detection for NFC-A and NFC-F (no need to re-arm) */
            st25r500ChangeRegisterBits( ST25R500_REG_PROTOCOL, ST25R500_REG_PROTOCOL_om_mask, (uint8_t)gRFAL.Lm.mdReg );

            break;
            
        /*******************************************************************************/
        case RFAL_LM_STATE_SLEEP_B:
            /* REMARK: Support for NFC-B would be added here  */
            return RFAL_ERR_NOT_IMPLEMENTED;
            
        /*******************************************************************************/
        default:
            return RFAL_ERR_PARAM;
            
    }
    
    
    /* Ensure that the  NFCIP1 mode is disabled */
    st25r500ClrRegisterBits( ST25R500_REG_PROTOCOL_TX1, ST25R500_REG_PROTOCOL_TX1_a_nfc_f0 );
    
    st25r500ExecuteCommand( ST25R500_CMD_UNMASK_RECEIVE_DATA );
    
    
    /* Clear and enable required IRQs */
    st25r500ClearAndEnableInterrupts( (ST25R500_IRQ_MASK_NFCT | ST25R500_IRQ_MASK_RXS | ST25R500_IRQ_MASK_RX_ERR | ST25R500_IRQ_MASK_EON | ST25R500_IRQ_MASK_EOF  | gRFAL.Lm.mdIrqs ) );
    
    /* Check whether the field was turn off right after the Sleep request */
    if( !rfalIsExtFieldOn() )
    {
        #if 0 /* Debug purposes */
            rfalLogD( "RFAL: curState: %02X newState: %02X \r\n", gRFAL.Lm.state, RFAL_LM_STATE_NOT_INIT );
        #endif
        
        rfalListenStop();
        return RFAL_ERR_LINK_LOSS;
    }
    
    #if 0 /* Debug purposes */
        rfalLogD( "RFAL: curState: %02X newState: %02X \r\n", gRFAL.Lm.state, sleepSt );
    #endif

    /* Set the new Sleep State*/
    gRFAL.Lm.state    = sleepSt;
    gRFAL.state       = RFAL_STATE_LM;
    
    gRFAL.Lm.rxBuf    = rxBuf;
    gRFAL.Lm.rxBufLen = rxBufLen;
    gRFAL.Lm.rxLen    = rxLen;
    *gRFAL.Lm.rxLen   = 0;
    gRFAL.Lm.dataFlag = false;
             
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
rfalLmState rfalListenGetState( bool *dataFlag, rfalBitRate *lastBR )
{
    /* Allow state retrieval even if gRFAL.state != RFAL_STATE_LM so  *
     * that this Lm state can be used by caller after activation      */

    if( lastBR != NULL )
    {
        *lastBR = gRFAL.Lm.brDetected;
    }
    
    if( dataFlag != NULL )
    {
        *dataFlag = gRFAL.Lm.dataFlag;
    }
    
    return gRFAL.Lm.state;
}

/*******************************************************************************/
ReturnCode rfalListenSetState( rfalLmState newSt )
{
    ReturnCode ret;
    rfalLmState newState;
    bool        reSetState;

    /* Check if RFAL is initialized */
    if( gRFAL.state < RFAL_STATE_INIT )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* SetState clears the Data flag */
    gRFAL.Lm.dataFlag = false;
    newState          = newSt;
    ret               = RFAL_ERR_NONE;

    do{
        reSetState = false;

        /*******************************************************************************/
        switch( newState )
        {
            /*******************************************************************************/
            case RFAL_LM_STATE_POWER_OFF:
                
                /* Enable the receiver and reset logic */
                st25r500SetRegisterBits( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_rx_en );
                st25r500ExecuteCommand( ST25R500_CMD_STOP );
                
                if( (gRFAL.Lm.mdMask & RFAL_LM_MASK_NFCA) != 0U )
                {
                    /* Enable automatic responses for A */
                    st25r500SetRegisterBits( ST25R500_REG_CE_CONFIG1, ST25R500_REG_CE_CONFIG1_en_106_ac_a );
                }
                
                if( (gRFAL.Lm.mdMask & RFAL_LM_MASK_NFCF) != 0U )
                {
                    /* Enable automatic responses for F */
                    st25r500SetRegisterBits( ST25R500_REG_CE_CONFIG1, ST25R500_REG_CE_CONFIG1_en_212_424_1r );
                }
                
                
                /*******************************************************************************/
                /* Ensure that the  NFCIP1 mode is disabled */
                st25r500ClrRegisterBits( ST25R500_REG_PROTOCOL_TX1, ST25R500_REG_PROTOCOL_TX1_a_nfc_f0 );
                
                
                /*******************************************************************************/
                /* Clear and enable required IRQs */
                st25r500DisableInterrupts( ST25R500_IRQ_MASK_ALL );
                
                st25r500ClearAndEnableInterrupts( (ST25R500_IRQ_MASK_NFCT | ST25R500_IRQ_MASK_OSC | ST25R500_IRQ_MASK_EON | ST25R500_IRQ_MASK_EOF | ST25R500_IRQ_MASK_CE_SC | ST25R500_IRQ_MASK_RXE_CE | ST25R500_IRQ_MASK_TXE | gRFAL.Lm.mdIrqs ) );
                
                /*******************************************************************************/
                /* Clear the bitRate previously detected */
                gRFAL.Lm.brDetected = RFAL_BR_KEEP;
                
                
                /*******************************************************************************/
                /* Apply the initial mode */
                st25r500ChangeRegisterBits( ST25R500_REG_PROTOCOL, ST25R500_REG_PROTOCOL_om_mask, (uint8_t)gRFAL.Lm.mdReg );
                
                /*******************************************************************************/
                /* Check if external Field is already On */
                if( rfalIsExtFieldOn() )
                {
                    reSetState = true;
                    newState   = RFAL_LM_STATE_IDLE;                         /* Set IDLE state */
                }
            #if 1
                else
                {  /* Perform bit rate detection in Low power mode */
                    st25r500ClrRegisterBits( ST25R500_REG_OPERATION, (ST25R500_REG_OPERATION_tx_en | ST25R500_REG_OPERATION_rx_en | ST25R500_REG_OPERATION_en) );
                }
            #endif
                break;
            
            /*******************************************************************************/
            case RFAL_LM_STATE_IDLE:
            
                /*******************************************************************************/
                /* Check if device is coming from Low Power bit rate detection */
                if( !st25r500IsOscOn() )
                {
                    /* Exit Low Power mode and confirm the temporarily enable */
                    st25r500SetRegisterBits( ST25R500_REG_OPERATION, (ST25R500_REG_OPERATION_en | ST25R500_REG_OPERATION_rx_en) );
                
                    if( !st25r500CheckReg( ST25R500_REG_STATUS1, (ST25R500_REG_STATUS1_osc_ok | ST25R500_REG_STATUS1_agd_ok), (ST25R500_REG_STATUS1_osc_ok | ST25R500_REG_STATUS1_agd_ok) ) )
                    {
                        /* Wait for Oscilator ready */
                        if( st25r500WaitForInterruptsTimed( ST25R500_IRQ_MASK_OSC, ST25R500_TOUT_OSC_STABLE ) == 0U )
                        {
                            ret = RFAL_ERR_IO;
                            break;
                        }
                    }
                }
                else
                {
                    st25r500GetInterrupt( ST25R500_IRQ_MASK_OSC );
                }
                
                
                /*******************************************************************************/
                /* Execute LM EON Callback                                                     */
                /*******************************************************************************/
                if( gRFAL.callbacks.lmEon != NULL )
                {
                    /* Dummy SPI read to ensure min time for RF indicator to become available */ 
                    st25r500ReadFifo( NULL, RFAL_RFIND_ADJUSTMENT );
                    
                    gRFAL.callbacks.lmEon();
                }
                /*******************************************************************************/
                
            
                /*******************************************************************************/
                
                /* If we are in ACTIVE_A, reEnable Listen for A before going to IDLE, otherwise do nothing */
                if( gRFAL.Lm.state == RFAL_LM_STATE_ACTIVE_A )
                {
                    /* Enable automatic responses for A and Reset NFCA target state */
                    st25r500SetRegisterBits( ST25R500_REG_CE_CONFIG1, ST25R500_REG_CE_CONFIG1_en_106_ac_a );
                    st25r500ChangeRegisterBits( ST25R500_REG_CE_STATUS1, ST25R500_REG_CE_STATUS1_ce_state_mask, ST25R500_REG_CE_STATUS1_ce_state_idle );
                }

                
                /* ReEnable the receiver */
                st25r500ExecuteCommand( ST25R500_CMD_CLEAR_FIFO );
                st25r500ExecuteCommand( ST25R500_CMD_UNMASK_RECEIVE_DATA );
                
                /*******************************************************************************/
                /* Check if Observation Mode is enabled and set it on ST25R */
                rfalCheckEnableObsModeRx();
                break;
                
            /*******************************************************************************/        
            case RFAL_LM_STATE_READY_F:
                
                /* ReEnable the receiver */
                st25r500ExecuteCommand( ST25R500_CMD_UNMASK_RECEIVE_DATA ); /* Unmask the receiver as upper layer has seen the frame (e.g. after SENSF_REQ with wrong system code */
                break;
                
            /*******************************************************************************/
            case RFAL_LM_STATE_READY_Ax:
            case RFAL_LM_STATE_READY_A:
                
                gRFAL.state = RFAL_STATE_LM;                    /* Keep in Listen Mode */
                break;
                
            /*******************************************************************************/
            case RFAL_LM_STATE_ACTIVE_Ax:
            case RFAL_LM_STATE_ACTIVE_A:
                
                /* Start looking for any incoming data */
                st25r500ClearAndEnableInterrupts( ST25R500_IRQ_MASK_RXS | ST25R500_IRQ_MASK_RXE | ST25R500_IRQ_MASK_RX_ERR );
            
                /* Disable automatic responses for A */
                st25r500ClrRegisterBits( ST25R500_REG_CE_CONFIG1, (ST25R500_REG_CE_CONFIG1_en_106_ac_a ) );
                
                /* Set Mode NFC-A only */
                ret = rfalSetMode( RFAL_MODE_LISTEN_NFCA, gRFAL.Lm.brDetected, gRFAL.Lm.brDetected );
                break;
            
            /*******************************************************************************/
            case RFAL_LM_STATE_CARDEMU_3:
            case RFAL_LM_STATE_TARGET_F:
                /* Disable Automatic response SENSF_REQ */
                st25r500ClrRegisterBits( ST25R500_REG_CE_CONFIG1, (ST25R500_REG_CE_CONFIG1_en_212_424_1r) );
            
                /* Set Mode NFC-F only */
                ret = rfalSetMode( RFAL_MODE_LISTEN_NFCF, gRFAL.Lm.brDetected, gRFAL.Lm.brDetected );
                gRFAL.state = RFAL_STATE_LM;                    /* Keep in Listen Mode */
                break;
                
            /*******************************************************************************/    
            case RFAL_LM_STATE_SLEEP_A:
            case RFAL_LM_STATE_SLEEP_B:
            case RFAL_LM_STATE_SLEEP_AF:
                /* These sleep states have to be set by the rfalListenSleepStart() method */
                return RFAL_ERR_REQUEST;
                
            /*******************************************************************************/    
            case RFAL_LM_STATE_CARDEMU_4A:
            case RFAL_LM_STATE_CARDEMU_4B:
            case RFAL_LM_STATE_TARGET_A:
                /* States not handled by the LM, just keep state context */
                break;
                
            /*******************************************************************************/
            default:
                return RFAL_ERR_WRONG_STATE;
        }
    }
    while( reSetState );
    
    gRFAL.Lm.state = newState;
    
    return ret;
}

#endif /* RFAL_FEATURE_LISTEN_MODE */


/*******************************************************************************
 *  Wake-Up Mode                                                               *
 *******************************************************************************/

#if RFAL_FEATURE_WAKEUP_MODE

/*******************************************************************************/
ReturnCode rfalWakeUpModeStart( const rfalWakeUpConfig *config )
{
    return rfalWUModeStart( config );
}


/*******************************************************************************/
static ReturnCode rfalWUModeStart( const rfalWakeUpConfig *config )
{   
    uint8_t                aux;
    uint8_t                measI;
    uint8_t                measQ;
    uint32_t               irqs;
    
    
    /* The Wake-Up procedure is explained in detail in Application Note: AN #TBD */
    if( config == NULL )
    {
        gRFAL.wum.cfg.period       = RFAL_WUM_PERIOD_100MS;
        gRFAL.wum.cfg.irqTout      = false;
        gRFAL.wum.cfg.skipCal      = false;
        gRFAL.wum.cfg.skipReCal    = false;
        gRFAL.wum.cfg.delCal       = true;
        gRFAL.wum.cfg.delRef       = true;
        gRFAL.wum.cfg.autoAvg      = true;
        gRFAL.wum.cfg.measFil      = RFAL_WUM_MEAS_FIL_FAST;
        gRFAL.wum.cfg.measDur      = RFAL_WUM_MEAS_DUR_44_28;
                                   
        gRFAL.wum.cfg.I.enabled    = true;
        gRFAL.wum.cfg.Q.enabled    = true;
                                   
        gRFAL.wum.cfg.I.delta      = 7U;
        gRFAL.wum.cfg.I.reference  = RFAL_WUM_REFERENCE_AUTO;
        gRFAL.wum.cfg.I.threshold  = ( (uint8_t)RFAL_WUM_TRE_ABOVE | (uint8_t)RFAL_WUM_TRE_BELOW );
        gRFAL.wum.cfg.I.aaWeight   = RFAL_WUM_AA_WEIGHT_64;
        gRFAL.wum.cfg.I.aaInclMeas = true;
        
        gRFAL.wum.cfg.Q.delta      = 7U;
        gRFAL.wum.cfg.Q.reference  = RFAL_WUM_REFERENCE_AUTO;
        gRFAL.wum.cfg.Q.threshold  = ( (uint8_t)RFAL_WUM_TRE_ABOVE | (uint8_t)RFAL_WUM_TRE_BELOW );
        gRFAL.wum.cfg.Q.aaWeight   = RFAL_WUM_AA_WEIGHT_64;
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

    irqs  = ST25R500_IRQ_MASK_NONE;
    measI = 0U;
    measQ = 0U;

    if( !gRFAL.wum.wlcPWpt )
    {
        /* Disable Tx, Rx */
        st25r500TxRxOff();
      
      /* Set Analog configurations for Wake-up On event */
      rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_WAKEUP_ON) );
    }
    
    
    /*******************************************************************************/
    /* Prepare Wake-Up Timer Control Register */
    aux = (uint8_t)(((uint8_t)gRFAL.wum.cfg.period & 0x0FU) << ST25R500_REG_WAKEUP_CONF1_wut_shift);
    
    if( gRFAL.wum.cfg.irqTout )
    {
        irqs |= ST25R500_IRQ_MASK_WUTME;
    }
    
    st25r500WriteRegister( ST25R500_REG_WAKEUP_CONF1, aux );
    
    /* Prepare Wake-Up  Control Register 2 */
    aux  = 0U;
    aux |= (uint8_t)( gRFAL.wum.cfg.skipReCal                             ? ST25R500_REG_WAKEUP_CONF3_skip_recal : 0x00U );
    aux |= (uint8_t)( gRFAL.wum.cfg.skipCal                               ? ST25R500_REG_WAKEUP_CONF3_skip_cal   : 0x00U );
    aux |= (uint8_t)( gRFAL.wum.cfg.delCal                                ? 0x00U : ST25R500_REG_WAKEUP_CONF3_skip_twcal );
    aux |= (uint8_t)( gRFAL.wum.cfg.delRef                                ? 0x00U : ST25R500_REG_WAKEUP_CONF3_skip_twref );
    aux |= (uint8_t)( gRFAL.wum.cfg.autoAvg                               ? ST25R500_REG_WAKEUP_CONF3_iq_aaref   : 0x00U );
    aux |= (uint8_t)( (gRFAL.wum.cfg.measFil == RFAL_WUM_MEAS_FIL_FAST)   ? ST25R500_REG_WAKEUP_CONF3_td_mf      : 0x00U );
    aux |= (uint8_t)( (uint8_t)gRFAL.wum.cfg.measDur   & ST25R500_REG_WAKEUP_CONF3_td_mt_mask );
    
    st25r500WriteRegister( ST25R500_REG_WAKEUP_CONF3, aux );
    
    /* Check if a manual reference is to be obtained */
    if( (!gRFAL.wum.cfg.autoAvg)                                                                  && 
        (( (gRFAL.wum.cfg.I.reference == RFAL_WUM_REFERENCE_AUTO) && (gRFAL.wum.cfg.I.enabled) )  || 
         ( (gRFAL.wum.cfg.Q.reference == RFAL_WUM_REFERENCE_AUTO) && (gRFAL.wum.cfg.Q.enabled) ))  )
    {
        /* Disable calibration automatics, perform manual calibration before reference measurement */
        st25r500SetRegisterBits( ST25R500_REG_WAKEUP_CONF3, (ST25R500_REG_WAKEUP_CONF3_skip_cal | ST25R500_REG_WAKEUP_CONF3_skip_recal) );
        
        /* Perform Manual Calibration and enter PD mode*/
        st25r500CalibrateWU( NULL, NULL );
        st25r500ClrRegisterBits( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_en );

        platformDelay( RFAL_PD_SETTLE );
        st25r500MeasureWU( &measI, &measQ );
    }
        
    /*******************************************************************************/
    /* Check if I-Channel is to be checked */
    if( gRFAL.wum.cfg.I.enabled )
    {
        st25r500ChangeRegisterBits( ST25R500_REG_WU_I_DELTA, ST25R500_REG_WU_I_DELTA_i_diff_mask, gRFAL.wum.cfg.I.delta );
        
        aux  = 0U;
        aux |= (uint8_t)(gRFAL.wum.cfg.I.aaInclMeas ? ST25R500_REG_WU_I_CONF_i_iirqm : 0x00U);
        aux |= (uint8_t)(((uint8_t)gRFAL.wum.cfg.I.aaWeight << ST25R500_REG_WU_I_CONF_i_aaw_shift) & ST25R500_REG_WU_I_CONF_i_aaw_mask);
        aux |= (uint8_t)(gRFAL.wum.cfg.I.threshold & ST25R500_REG_WU_I_CONF_i_tdi_en_mask);
        st25r500WriteRegister( ST25R500_REG_WU_I_CONF, aux );
        
        if( !gRFAL.wum.cfg.autoAvg )
        {
            /* Set reference manually */
            st25r500WriteRegister(ST25R500_REG_WU_I_REF, ((gRFAL.wum.cfg.I.reference == RFAL_WUM_REFERENCE_AUTO) ? measI : gRFAL.wum.cfg.I.reference) );
        }
        
        irqs |= ST25R500_IRQ_MASK_WUI;
    }
    else
    {
        st25r500ClrRegisterBits( ST25R500_REG_WU_I_CONF, ST25R500_REG_WU_I_CONF_i_tdi_en_mask );
    }
    
    /*******************************************************************************/
    /* Check if Q-Channel is to be checked */
    if( gRFAL.wum.cfg.Q.enabled )
    {
        st25r500ChangeRegisterBits( ST25R500_REG_WU_Q_DELTA, ST25R500_REG_WU_Q_DELTA_q_diff_mask, gRFAL.wum.cfg.Q.delta );
        
        aux = 0U;
        aux |= (uint8_t)(gRFAL.wum.cfg.Q.aaInclMeas ? ST25R500_REG_WU_Q_CONF_q_iirqm : 0x00U);
        aux |= (uint8_t)(((uint8_t)gRFAL.wum.cfg.Q.aaWeight << ST25R500_REG_WU_Q_CONF_q_aaw_shift) & ST25R500_REG_WU_Q_CONF_q_aaw_mask);
        aux |= (uint8_t)(gRFAL.wum.cfg.Q.threshold & ST25R500_REG_WU_Q_CONF_q_tdi_en_mask);
        st25r500WriteRegister( ST25R500_REG_WU_Q_CONF, aux );
        
        if( !gRFAL.wum.cfg.autoAvg )
        {
            /* Set reference manually */
            st25r500WriteRegister(ST25R500_REG_WU_Q_REF, ((gRFAL.wum.cfg.Q.reference == RFAL_WUM_REFERENCE_AUTO) ? measQ : gRFAL.wum.cfg.Q.reference) );
        }
        
        irqs |= ST25R500_IRQ_MASK_WUQ;
    }
    else
    {
        st25r500ClrRegisterBits( ST25R500_REG_WU_Q_CONF, ST25R500_REG_WU_Q_CONF_q_tdi_en_mask );
    }
    
    
    /* Clear WU info struct */
    RFAL_MEMSET(&gRFAL.wum.info, 0x00, sizeof(gRFAL.wum.info));
    
    /* Disable and clear all interrupts except Wake-Up IRQs */
    st25r500DisableInterrupts( ST25R500_IRQ_MASK_ALL );
    
    if( gRFAL.wum.wlcPWpt )
    {
      irqs &= ~(ST25R500_IRQ_MASK_WUI | ST25R500_IRQ_MASK_WUQ);
      irqs |= (ST25R500_IRQ_MASK_WPT_FOD | ST25R500_IRQ_MASK_WPT_STOP);
      
      st25r500GetInterrupt( irqs );
      st25r500EnableInterrupts( irqs );
      
      /* Enable Wake-Up Mode monitoring of WLC WPT phase */
      st25r500SetRegisterBits( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_wpt_en );
    }
    else
    {
      st25r500GetInterrupt( irqs );
      st25r500EnableInterrupts( irqs );

      /* Disable Oscilattor, Tx, Rx and Regulators */
      st25r500ClrRegisterBits( ST25R500_REG_OPERATION, (ST25R500_REG_OPERATION_tx_en | ST25R500_REG_OPERATION_rx_en | ST25R500_REG_OPERATION_vdddr_en | ST25R500_REG_OPERATION_en) );

      /* Enable Low Power Wake-Up Mode */
      st25r500SetRegisterBits( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_wu_en );
    }
    
    gRFAL.wum.state = RFAL_WUM_STATE_ENABLED;
    gRFAL.state     = RFAL_STATE_WUM;

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
    info->irqWut            = gRFAL.wum.info.irqWutme;
    gRFAL.wum.info.irqWut   = false;
    gRFAL.wum.info.irqWutme = false;
    
    /* Retrieve values if there was any WU related IRQ event (or forced) */
    if( (force) || (info->irqWut) || (gRFAL.wum.info.irqWui) || (gRFAL.wum.info.irqWuq) || (gRFAL.wum.info.irqWptFod) || (gRFAL.wum.info.irqWptStop) )
    {
        /* Update status information */
        st25r500ReadRegister( ST25R500_REG_WU_STATUS, &info->status );
        info->status &= (ST25R500_REG_WU_STATUS_q_tdi_mask | ST25R500_REG_WU_STATUS_i_tdi_mask);
        
        if( gRFAL.wum.cfg.I.enabled )
        {
            st25r500ReadRegister( ST25R500_REG_WU_I_ADC, &info->I.lastMeas );
            st25r500ReadRegister( ST25R500_REG_WU_I_CAL, &info->I.calib );
            st25r500ReadRegister( ST25R500_REG_WU_I_REF, &info->I.reference );
        
            /* Update IRQ information and clear flag upon retrieving */
            info->I.irqWu         = gRFAL.wum.info.irqWui;
            gRFAL.wum.info.irqWui = false;
        }
        
        if( gRFAL.wum.cfg.Q.enabled )
        {
            st25r500ReadRegister( ST25R500_REG_WU_Q_ADC, &info->Q.lastMeas );
            st25r500ReadRegister( ST25R500_REG_WU_Q_CAL, &info->Q.calib );
            st25r500ReadRegister( ST25R500_REG_WU_Q_REF, &info->Q.reference );
        
            /* Update IRQ information and clear flag upon retrieving */
            info->Q.irqWu         = gRFAL.wum.info.irqWuq;
            gRFAL.wum.info.irqWuq = false;
        }
        
        if( gRFAL.wum.wlcPWpt )
        {
            /* Update IRQ information and clear flag upon retrieving */
            info->WLC.irqWptFod      = gRFAL.wum.info.irqWptFod;
            gRFAL.wum.info.irqWptFod = false;
          
            /* Update IRQ information and clear flag upon retrieving */
            info->WLC.irqWptStop      = gRFAL.wum.info.irqWptStop;
            gRFAL.wum.info.irqWptStop = false;
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
            irqs = st25r500GetInterrupt( ( ST25R500_IRQ_MASK_WUT  | ST25R500_IRQ_MASK_WUI | ST25R500_IRQ_MASK_WUQ | ST25R500_IRQ_MASK_WUTME |
                                                                                     ST25R500_IRQ_MASK_WPT_STOP | ST25R500_IRQ_MASK_WPT_FOD ) );
            if( irqs == ST25R500_IRQ_MASK_NONE )
            {
               break;  /* No interrupt to process */
            }
            
            /*******************************************************************************/
            /* Check and mark which measurement(s) cause interrupt */
            if((irqs & ST25R500_IRQ_MASK_WUT) != 0U)
            {
                gRFAL.wum.info.irqWut = true;
            }
            if((irqs & ST25R500_IRQ_MASK_WUI) != 0U)
            {
                gRFAL.wum.info.irqWui = true;
                st25r500ReadRegister( ST25R500_REG_WU_I_ADC, &aux );
                gRFAL.wum.state = RFAL_WUM_STATE_ENABLED_WOKE;
            }
            
            if((irqs & ST25R500_IRQ_MASK_WUQ) != 0U)
            {
                gRFAL.wum.info.irqWuq = true;

                st25r500ReadRegister( ST25R500_REG_WU_Q_ADC, &aux );
                gRFAL.wum.state = RFAL_WUM_STATE_ENABLED_WOKE;
            }

            if((irqs & ST25R500_IRQ_MASK_WUTME) != 0U)
            {
                gRFAL.wum.info.irqWutme = true;
              
                st25r500ReadRegister( ST25R500_REG_WU_I_ADC, &aux );
                st25r500ReadRegister( ST25R500_REG_WU_Q_ADC, &aux );
            }
            
            if((irqs & ST25R500_IRQ_MASK_WPT_STOP) != 0U)
            {
                gRFAL.wum.info.irqWptStop = true;
            }
            if((irqs & ST25R500_IRQ_MASK_WPT_FOD) != 0U)
            {
                gRFAL.wum.info.irqWptFod = true;
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
    
    
    if( gRFAL.wum.wlcPWpt )
    {
        gRFAL.wum.wlcPWpt = false;
        st25r500ClrRegisterBits( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_wpt_en );
        st25r500DisableInterrupts( (ST25R500_IRQ_MASK_WUT | ST25R500_IRQ_MASK_WUTME | ST25R500_IRQ_MASK_WPT_STOP | ST25R500_IRQ_MASK_WPT_FOD) );
    }
    else
    {
        /* Disable Wake-Up Mode, and restore default DAC control to calibration result */
        st25r500ClrRegisterBits( ST25R500_REG_OPERATION, ST25R500_REG_OPERATION_wu_en );
        st25r500DisableInterrupts( (ST25R500_IRQ_MASK_WUT | ST25R500_IRQ_MASK_WUTME | ST25R500_IRQ_MASK_WUQ | ST25R500_IRQ_MASK_WUI) );

        st25r500TxRxOff();

        /* Re-Enable the Oscillator */
        st25r500OscOn();

        /* Set Analog configurations for Wake-up Off event */
        rfalSetAnalogConfig( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_WAKEUP_OFF) );
    }
    
    /* Stop any ongoing activity */
    st25r500ExecuteCommand( ST25R500_CMD_STOP );
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalWlcPWptMonitorStart( const rfalWakeUpConfig *config ) 
{
    rfalWakeUpConfig wuConf;
    
    if( (!st25r500IsTxEnabled()) || (gRFAL.state < RFAL_STATE_INIT) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    wuConf.period       = RFAL_WUM_PERIOD_200MS;  /* 151us in WLC WPT */
    wuConf.irqTout      = false;
    wuConf.skipCal      = false;
    wuConf.skipReCal    = false;
    wuConf.delCal       = true;
    wuConf.delRef       = true;
    wuConf.autoAvg      = true;
    wuConf.measFil      = RFAL_WUM_MEAS_FIL_SLOW;
    wuConf.measDur      = RFAL_WUM_MEAS_DUR_44_28;
                               
    wuConf.I.enabled    = true;
    wuConf.Q.enabled    = true;
                               
    wuConf.I.delta      = 5U;
    wuConf.I.reference  = RFAL_WUM_REFERENCE_AUTO;
    wuConf.I.threshold  = ( (uint8_t)RFAL_WUM_TRE_ABOVE | (uint8_t)RFAL_WUM_TRE_BELOW );
    wuConf.I.aaWeight   = RFAL_WUM_AA_WEIGHT_32;
    wuConf.I.aaInclMeas = false;
    
    wuConf.Q.delta      = 5U;
    wuConf.Q.reference  = RFAL_WUM_REFERENCE_AUTO;
    wuConf.Q.threshold  = ( (uint8_t)RFAL_WUM_TRE_ABOVE | (uint8_t)RFAL_WUM_TRE_BELOW );
    wuConf.Q.aaWeight   = RFAL_WUM_AA_WEIGHT_32;
    wuConf.Q.aaInclMeas = false;
    
    gRFAL.wum.wlcPWpt   = true;
        
    if( config != NULL )
    {   
        /* Load certain user specific parameters */
        wuConf.I.delta = config->I.delta;
        wuConf.Q.delta = config->Q.delta;
    }
    
    return rfalWUModeStart( &wuConf );
}


/*******************************************************************************/
ReturnCode rfalWlcPWptMonitorStop( void ) 
{
    return rfalWakeUpModeStop();
}


/*******************************************************************************/
bool rfalWlcPWptIsFodDetected( void )
{   
    return ((gRFAL.wum.state >= RFAL_WUM_STATE_ENABLED_WOKE) && (gRFAL.wum.info.irqWptFod));
}


/*******************************************************************************/
bool rfalWlcPWptIsStopDetected( void )
{   
    return ((gRFAL.wum.state >= RFAL_WUM_STATE_ENABLED_WOKE) && (gRFAL.wum.info.irqWptStop));
}

#endif /* RFAL_FEATURE_WAKEUP_MODE */


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
        /* Stop any ongoing activity and set the device in low power by disabling oscillator, transmitter, receiver and external field detector */
        st25r500ExecuteCommand( ST25R500_CMD_STOP );
        st25r500ClrRegisterBits( ST25R500_REG_OPERATION, ( ST25R500_REG_OPERATION_en  | ST25R500_REG_OPERATION_rx_en | ST25R500_REG_OPERATION_vdddr_en |
                                                           ST25R500_REG_OPERATION_wu_en   | ST25R500_REG_OPERATION_tx_en )                                  );
        
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
        RFAL_EXIT_ON_ERR( ret, st25r500OscOn() );
        
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
    if( !st25r500IsRegValid( (uint8_t)reg) )
    {
        return RFAL_ERR_PARAM;
    }
    
    return st25r500WriteMultipleRegisters( (uint8_t)reg, values, len );
}


/*******************************************************************************/
ReturnCode rfalChipReadReg( uint16_t reg, uint8_t* values, uint8_t len )
{
    if( !st25r500IsRegValid( (uint8_t)reg) )
    {
        return RFAL_ERR_PARAM;
    }
    
    return st25r500ReadMultipleRegisters( (uint8_t)reg, values, len );
}


/*******************************************************************************/
ReturnCode rfalChipExecCmd( uint16_t cmd )
{
    if( !st25r500IsCmdValid( (uint8_t)cmd) )
    {
        return RFAL_ERR_PARAM;
    }
    
    return st25r500ExecuteCommand( (uint8_t) cmd );
}


/*******************************************************************************/
ReturnCode rfalChipWriteTestReg( uint16_t reg, uint8_t value )
{
    return st25r500WriteTestRegister( (uint8_t)reg, value );
}


/*******************************************************************************/
ReturnCode rfalChipReadTestReg( uint16_t reg, uint8_t* value )
{
    return st25r500ReadTestRegister( (uint8_t)reg, value );
}


/*******************************************************************************/
ReturnCode rfalChipChangeRegBits( uint16_t reg, uint8_t valueMask, uint8_t value )
{
    if( !st25r500IsRegValid( (uint8_t)reg) )
    {
        return RFAL_ERR_PARAM;
    }
    
    return st25r500ChangeRegisterBits( (uint8_t)reg, valueMask, value );
}


/*******************************************************************************/
ReturnCode rfalChipChangeTestRegBits( uint16_t reg, uint8_t valueMask, uint8_t value )
{
    st25r500ChangeTestRegisterBits( (uint8_t)reg, valueMask, value );
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalChipSetRFO( uint8_t rfo )
{
    return st25r500ChangeRegisterBits( ST25R500_REG_DRIVER, ST25R500_REG_DRIVER_d_res_mask, rfo );
}


/*******************************************************************************/
ReturnCode rfalChipGetRFO( uint8_t* result )
{
    ReturnCode ret;
    
    ret = st25r500ReadRegister(ST25R500_REG_DRIVER, result);
    
    if( result != NULL )
    {
        (*result) = ( (*result) & ST25R500_REG_DRIVER_d_res_mask );
    }

    return ret;
}


/*******************************************************************************/
ReturnCode rfalChipGetLmFieldInd( uint8_t* result )
{
    return st25r500GetCeGain(result);
}


/*******************************************************************************/
ReturnCode rfalChipSetLMMod( uint8_t mod, uint8_t unmod )
{
    return st25r500WriteRegister( ST25R500_REG_CE_TX_MOD1, (((mod << ST25R500_REG_CE_TX_MOD1_cem_res_shift) & ST25R500_REG_CE_TX_MOD1_cem_res_mask) | ((unmod & ST25R500_REG_CE_TX_MOD1_ce_res_mask) )) );
}


/*******************************************************************************/
ReturnCode rfalChipGetLMMod( uint8_t* mod, uint8_t* unmod )
{
    ReturnCode ret;
    uint8_t    reg;
    
    ret = st25r500ReadRegister( ST25R500_REG_CE_TX_MOD1, &reg );
    
    if( mod != NULL )
    {
        (*mod) = ( ((reg & ST25R500_REG_CE_TX_MOD1_cem_res_mask) >> ST25R500_REG_CE_TX_MOD1_cem_res_shift) );
    }
    
    if( unmod != NULL )
    {
        (*unmod) = ( ((reg & ST25R500_REG_CE_TX_MOD1_ce_res_mask) >> ST25R500_REG_CE_TX_MOD1_ce_res_shift) );
    }
    
    return ret;
}


/*******************************************************************************/
ReturnCode rfalChipMeasureAmplitude( uint8_t* result )
{
    ReturnCode err;
    
    err = st25r500MeasureAmplitude( result );
    
    return err;
}


/*******************************************************************************/
ReturnCode rfalChipMeasurePhase( uint8_t* result )
{
    ReturnCode err;
    
    err = st25r500MeasurePhase( result );
    
    return err;
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
    ReturnCode err;
    uint16_t rawResult;

    err = st25r500DiagMeasure( param, &rawResult );

    /* Result is expected to be 9 bit - interface allows only 8 bits: Divide by 2 | shift right
     * This means conversion factors need to be doubled compared to DS factors */
    rawResult >>= 1U;

    if( rawResult > (uint16_t)UINT8_MAX )
    {
        rawResult = (uint16_t)UINT8_MAX;
    }

    if( result != NULL )
    {
        (*result) = (uint8_t)rawResult;
    }
    
    return err;
}


/*******************************************************************************/
ReturnCode rfalChipMeasureIQ( int8_t* resI, int8_t* resQ )
{
    return st25r500MeasureIQ( resI, resQ );
}


/*******************************************************************************/
ReturnCode rfalChipMeasureCombinedIQ( uint8_t* result )
{
    ReturnCode err;
    
    err = st25r500MeasureCombinedIQ( result );
    
    return err;
}


/*******************************************************************************/
ReturnCode rfalChipMeasureI( uint8_t* result )
{
    ReturnCode err;    
    
    err = st25r500MeasureI( result );
    
    return err;
}


/*******************************************************************************/
ReturnCode rfalChipMeasureQ( uint8_t* result )
{
    ReturnCode err;
    
    err = st25r500MeasureQ( result );
    
    return err;
}


/*******************************************************************************/
ReturnCode rfalChipMeasureCurrent( uint8_t* result )
{
    ReturnCode err;
    
    err = st25r500MeasureCurrent( result );
    
    return err;
}


/*******************************************************************************/
ReturnCode rfalChipSetAntennaMode( bool single, bool rfiox )
{
    return st25r500SetAntennaMode(single, rfiox );
}



