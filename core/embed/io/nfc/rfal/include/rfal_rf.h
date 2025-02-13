
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

/*! \file rfal_rf.h
 *
 *  \author Gustavo Patricio 
 *
 *  \brief RF Abstraction Layer (RFAL)
 *  
 *  RFAL (RF Abstraction Layer) provides several functionalities required to 
 *  perform RF/NFC communications. <br>The RFAL encapsulates the different 
 *  RF ICs (ST25R3911, ST25R391x, etc) into a common and easy to use interface.
 *  
 *  It provides interfaces to configure the RF IC, set/get timings, modes, bit rates,
 *  specific handlings, execute listen mode, etc. 
 *  
 *  Furthermore it provides a common interface to perform a Transceive operations.
 *  The Transceive can be executed in a blocking or non blocking way.<br>
 *  Additionally few specific Transceive methods are available to cope with the
 *  specifics of these particular operations.
 *  
 *  The most common interfaces are:
 *    <br>&nbsp; rfalInitialize()
 *    <br>&nbsp; rfalSetFDTPoll()
 *    <br>&nbsp; rfalSetFDTListen()
 *    <br>&nbsp; rfalSetGT()
 *    <br>&nbsp; rfalSetBitRate()
 *    <br>&nbsp; rfalSetMode()
 *    <br>&nbsp; rfalFieldOnAndStartGT()
 *    <br>&nbsp; rfalFieldOff()
 *    <br>&nbsp; rfalStartTransceive()
 *    <br>&nbsp; rfalGetTransceiveStatus()
 *    <br>&nbsp; rfalTransceiveBlockingTxRx()
 *    
 *  An usage example is provided here: \ref exampleRfalPoller.c
 *  \example exampleRfalPoller.c
 *    
 * \addtogroup RFAL
 * @{
 * 
 * \addtogroup RFAL-HAL
 * \brief RFAL Hardware Abstraction Layer
 * @{
 * 
 * \addtogroup RF
 * \brief RFAL RF Abstraction Layer
 * @{
 *  
 */

#ifndef RFAL_RF_H
#define RFAL_RF_H

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include "rfal_platform.h"
#include "rfal_utils.h"
#include "rfal_features.h"

/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/
#define RFAL_VERSION                               0x030001U                                    /*!< RFAL Current Version: v3.0.1                      */

#define RFAL_FWT_NONE                              0xFFFFFFFFU                                  /*!< Disabled FWT: Wait forever for a response         */
#define RFAL_GT_NONE                               RFAL_TIMING_NONE                             /*!< Disabled GT: No GT will be applied after Field On */

#define RFAL_TIMING_NONE                           0x00U                                        /*!< Timing disabled | Don't apply                     */

#define RFAL_1FC_IN_4096FC                         (uint32_t)4096U                              /*!< Number of 1/fc cycles in one 4096/fc              */
#define RFAL_1FC_IN_2048FC                         (uint32_t)2048U                              /*!< Number of 1/fc cycles in one 2048/fc              */
#define RFAL_1FC_IN_512FC                          (uint32_t)512U                               /*!< Number of 1/fc cycles in one 512/fc               */
#define RFAL_1FC_IN_64FC                           (uint32_t)64U                                /*!< Number of 1/fc cycles in one 64/fc                */
#define RFAL_1FC_IN_8FC                            (uint32_t)8U                                 /*!< Number of 1/fc cycles in one 8/fc                 */
#define RFAL_US_IN_MS                              (uint32_t)1000U                              /*!< Number of us in one ms                            */
#define RFAL_1MS_IN_1FC                            (uint32_t)13560U                             /*!< Number of 1/fc cycles in 1ms                      */
#define RFAL_BITS_IN_BYTE                          (uint16_t)8U                                 /*!< Number of bits in one byte                        */

#define RFAL_CRC_LEN                               2U                                           /*!< RF CRC LEN                                        */

/*! Default TxRx flags: Tx CRC automatic, Rx CRC removed, NFCIP1 mode off, AGC On, Tx Parity automatic, Rx Parity removed */
#define RFAL_TXRX_FLAGS_DEFAULT                    ( (uint32_t)RFAL_TXRX_FLAGS_CRC_TX_AUTO | (uint32_t)RFAL_TXRX_FLAGS_CRC_RX_REMV | (uint32_t)RFAL_TXRX_FLAGS_NFCIP1_OFF | (uint32_t)RFAL_TXRX_FLAGS_AGC_ON | (uint32_t)RFAL_TXRX_FLAGS_PAR_RX_REMV | (uint32_t)RFAL_TXRX_FLAGS_PAR_TX_AUTO | (uint32_t)RFAL_TXRX_FLAGS_NFCV_FLAG_AUTO)



#define RFAL_LM_MASK_NFCA                          ((uint32_t)1U<<(uint8_t)RFAL_MODE_LISTEN_NFCA)        /*!< Bitmask for Listen Mode enabling NFCA    */
#define RFAL_LM_MASK_NFCB                          ((uint32_t)1U<<(uint8_t)RFAL_MODE_LISTEN_NFCB)        /*!< Bitmask for Listen Mode enabling NFCB    */
#define RFAL_LM_MASK_NFCF                          ((uint32_t)1U<<(uint8_t)RFAL_MODE_LISTEN_NFCF)        /*!< Bitmask for Listen Mode enabling NFCF    */
#define RFAL_LM_MASK_ACTIVE_P2P                    ((uint32_t)1U<<(uint8_t)RFAL_MODE_LISTEN_ACTIVE_P2P)  /*!< Bitmask for Listen Mode enabling AP2P    */

#define RFAL_LM_SENS_RES_LEN                       2U                                           /*!< NFC-A SENS_RES (ATQA) length                      */
#define RFAL_LM_SENSB_RES_LEN                      13U                                          /*!< NFC-B SENSB_RES (ATQB) length                     */
#define RFAL_LM_SENSF_RES_LEN                      19U                                          /*!< NFC-F SENSF_RES  length                           */
#define RFAL_LM_SENSF_SC_LEN                       2U                                           /*!< NFC-F System Code length                          */

#define RFAL_NFCID3_LEN                            10U                                          /*!< NFCID3 length                                     */
#define RFAL_NFCID2_LEN                            8U                                           /*!< NFCID2 length                                     */
#define RFAL_NFCID1_TRIPLE_LEN                     10U                                          /*!< NFCID1 length                                     */
#define RFAL_NFCID1_DOUBLE_LEN                     7U                                           /*!< NFCID1 length                                     */
#define RFAL_NFCID1_SINGLE_LEN                     4U                                           /*!< NFCID1 length                                     */


/*
******************************************************************************
* GLOBAL MACROS
******************************************************************************
*/

/*! Returns the maximum supported bit rate for RW mode. Caller must check if mode is supported before, as even if mode is not supported will return the min  */
#define rfalGetMaxBrRW()                     ( ((RFAL_SUPPORT_BR_RW_6780)  ? RFAL_BR_6780 : ((RFAL_SUPPORT_BR_RW_3390)  ? RFAL_BR_3390 : ((RFAL_SUPPORT_BR_RW_1695)  ? RFAL_BR_1695 : ((RFAL_SUPPORT_BR_RW_848)  ? RFAL_BR_848 : ((RFAL_SUPPORT_BR_RW_424)  ? RFAL_BR_424 : ((RFAL_SUPPORT_BR_RW_212)  ? RFAL_BR_212 : RFAL_BR_106 ) ) ) ) ) ) )

/*! Returns the maximum supported bit rate for AP2P mode. Caller must check if mode is supported before, as even if mode is not supported will return the min  */
#define rfalGetMaxBrAP2P()                   ( ((RFAL_SUPPORT_BR_AP2P_848) ? RFAL_BR_848  : ((RFAL_SUPPORT_BR_AP2P_424) ? RFAL_BR_424  : ((RFAL_SUPPORT_BR_AP2P_212) ? RFAL_BR_212  : RFAL_BR_106 ) ) ) )

/*! Returns the maximum supported bit rate for CE-A mode. Caller must check if mode is supported before, as even if mode is not supported will return the min  */
#define rfalGetMaxBrCEA()                    ( ((RFAL_SUPPORT_BR_CE_A_848) ? RFAL_BR_848  : ((RFAL_SUPPORT_BR_CE_A_424) ? RFAL_BR_424  : ((RFAL_SUPPORT_BR_CE_A_212) ? RFAL_BR_212  : RFAL_BR_106 ) ) ) )

/*! Returns the maximum supported bit rate for CE-B mode. Caller must check if mode is supported before, as even if mode is not supported will return the min  */
#define rfalGetMaxBrCEB()                    ( ((RFAL_SUPPORT_BR_CE_B_848) ? RFAL_BR_848  : ((RFAL_SUPPORT_BR_CE_B_424) ? RFAL_BR_424  : ((RFAL_SUPPORT_BR_CE_B_212) ? RFAL_BR_212  : RFAL_BR_106 ) ) ) )

/*! Returns the maximum supported bit rate for CE-F mode. Caller must check if mode is supported before, as even if mode is not supported will return the min  */
#define rfalGetMaxBrCEF()                    ( ((RFAL_SUPPORT_BR_CE_F_424) ? RFAL_BR_424  : RFAL_BR_212 ) )


#define rfalIsModeActiveComm( md )           ( ((md) == RFAL_MODE_POLL_ACTIVE_P2P) || ((md) == RFAL_MODE_LISTEN_ACTIVE_P2P) )                          /*!< Checks if mode md is Active Communication  */
#define rfalIsModePassiveComm( md )          ( !rfalIsModeActiveComm(md) )                                                                             /*!< Checks if mode md is Passive Communication */
#define rfalIsModePassiveListen( md )        ( ((md) == RFAL_MODE_LISTEN_NFCA) || ((md) == RFAL_MODE_LISTEN_NFCB) || ((md) == RFAL_MODE_LISTEN_NFCF) ) /*!< Checks if mode md is Passive Listen        */
#define rfalIsModePassivePoll( md )          ( rfalIsModePassiveComm(md) && (!rfalIsModePassiveListen(md)) )                                           /*!< Checks if mode md is Passive Poll          */


#define rfalConv1fcTo8fc( t )                (uint32_t)( (uint32_t)(t) / RFAL_1FC_IN_8FC )                               /*!< Converts the given t from 1/fc to 8/fc     */
#define rfalConv8fcTo1fc( t )                (uint32_t)( (uint32_t)(t) * RFAL_1FC_IN_8FC )                               /*!< Converts the given t from 8/fc to 1/fc     */

#define rfalConv1fcTo64fc( t )               (uint32_t)( (uint32_t)(t) / RFAL_1FC_IN_64FC )                              /*!< Converts the given t from 1/fc  to 64/fc   */
#define rfalConv64fcTo1fc( t )               (uint32_t)( (uint32_t)(t) * RFAL_1FC_IN_64FC )                              /*!< Converts the given t from 64/fc to 1/fc    */

#define rfalConv1fcTo512fc( t )              (uint32_t)( (uint32_t)(t) / RFAL_1FC_IN_512FC )                             /*!< Converts the given t from 1/fc  to 512/fc  */
#define rfalConv512fcTo1fc( t )              (uint32_t)( (uint32_t)(t) * RFAL_1FC_IN_512FC )                             /*!< Converts the given t from 512/fc to 1/fc   */

#define rfalConv1fcTo2018fc( t )             (uint32_t)( (uint32_t)(t) / RFAL_1FC_IN_2048FC )                            /*!< Converts the given t from 1/fc to 2048/fc  */
#define rfalConv2048fcTo1fc( t )             (uint32_t)( (uint32_t)(t) * RFAL_1FC_IN_2048FC )                            /*!< Converts the given t from 2048/fc to 1/fc  */

#define rfalConv1fcTo4096fc( t )             (uint32_t)( (uint32_t)(t) / RFAL_1FC_IN_4096FC )                            /*!< Converts the given t from 1/fc to 4096/fc  */
#define rfalConv4096fcTo1fc( t )             (uint32_t)( (uint32_t)(t) * RFAL_1FC_IN_4096FC )                            /*!< Converts the given t from 4096/fc to 1/fc  */

#define rfalConv1fcToMs( t )                 (uint32_t)( (uint32_t)(t) / RFAL_1MS_IN_1FC )                               /*!< Converts the given t from 1/fc to ms       */
#define rfalConvMsTo1fc( t )                 (uint32_t)( (uint32_t)(t) * RFAL_1MS_IN_1FC )                               /*!< Converts the given t from ms to 1/fc       */

#define rfalConv1fcToUs( t )                 (uint32_t)( ((uint32_t)(t) * RFAL_US_IN_MS) / RFAL_1MS_IN_1FC)              /*!< Converts the given t from 1/fc to us       */
#define rfalConvUsTo1fc( t )                 (uint32_t)( ((uint32_t)(t) * RFAL_1MS_IN_1FC) / RFAL_US_IN_MS)              /*!< Converts the given t from us to 1/fc       */

#define rfalConv64fcToMs( t )                (uint32_t)( (uint32_t)(t) / (RFAL_1MS_IN_1FC / RFAL_1FC_IN_64FC) )          /*!< Converts the given t from 64/fc to ms      */
#define rfalConvMsTo64fc( t )                (uint32_t)( (uint32_t)(t) * (RFAL_1MS_IN_1FC / RFAL_1FC_IN_64FC) )          /*!< Converts the given t from ms to 64/fc      */

#define rfalConvBitsToBytes( n )             (uint16_t)( ((uint16_t)(n)+(RFAL_BITS_IN_BYTE-1U)) / (RFAL_BITS_IN_BYTE) )  /*!< Converts the given n from bits to bytes    */
#define rfalConvBytesToBits( n )             (uint32_t)( (uint32_t)(n) * (RFAL_BITS_IN_BYTE) )                           /*!< Converts the given n from bytes to bits    */


#define rfalRunBlocking( e, fn )              do{ (e)=(fn); rfalWorker(); }while( (e) == RFAL_ERR_BUSY )                      /*!< Macro used for the blocking methods        */


/*! Computes a Transceive context \a ctx with default flags and the lengths 
 * in bytes with the given arguments
 *    \a ctx   : Transceive context to be assigned  
 *    \a tB    : txBuf the pointer to the buffer to be sent
 *    \a tBL   : txBuf length in bytes
 *    \a rB    : rxBuf the pointer to the buffer to place the received frame
 *    \a rBL   : rxBuf length in bytes
 *    \a rdL   : rxRcvdLen the pointer to place the rx length 
 *    \a t     : FWT to be used on this transceive in 1/fc
 */
#define rfalCreateByteTxRxContext( ctx, tB, tBL, rB, rBL, rdL, t ) \
    (ctx).txBuf     = (uint8_t*)(tB);                                      \
    (ctx).txBufLen  = (uint16_t)rfalConvBytesToBits(tBL);                  \
    (ctx).rxBuf     = (uint8_t*)(rB);                                      \
    (ctx).rxBufLen  = (uint16_t)rfalConvBytesToBits(rBL);                  \
    (ctx).rxRcvdLen = (uint16_t*)(rdL);                                    \
    (ctx).flags     = (uint32_t)RFAL_TXRX_FLAGS_DEFAULT;                   \
    (ctx).fwt       = (uint32_t)(t);


/*! Computes a Transceive context \a ctx using lengths in bytes 
 * with the given flags and arguments
 *    \a ctx   : Transceive context to be assigned  
 *    \a tB    : txBuf the pointer to the buffer to be sent
 *    \a tBL   : txBuf length in bytes
 *    \a rB    : rxBuf the pointer to the buffer to place the received frame
 *    \a rBL   : rxBuf length in bytes
 *    \a rBL   : rxBuf length in bytes
 *    \a t     : FWT to be used on this transceive in 1/fc
 */
#define rfalCreateByteFlagsTxRxContext( ctx, tB, tBL, rB, rBL, rdL, fl, t ) \
    (ctx).txBuf     = (uint8_t*)(tB);                                       \
    (ctx).txBufLen  = (uint16_t)rfalConvBytesToBits(tBL);                   \
    (ctx).rxBuf     = (uint8_t*)(rB);                                       \
    (ctx).rxBufLen  = (uint16_t)rfalConvBytesToBits(rBL);                   \
    (ctx).rxRcvdLen = (uint16_t*)(rdL);                                     \
    (ctx).flags     = (uint32_t)(fl);                                       \
    (ctx).fwt       = (uint32_t)(t);


#define rfalLogE(...)             platformLog(__VA_ARGS__)        /*!< Macro for the error log method                  */
#define rfalLogW(...)             platformLog(__VA_ARGS__)        /*!< Macro for the warning log method                */
#define rfalLogI(...)             platformLog(__VA_ARGS__)        /*!< Macro for the info log method                   */
#define rfalLogD(...)             platformLog(__VA_ARGS__)        /*!< Macro for the debug log method                  */


/*
******************************************************************************
* GLOBAL ENUMS
******************************************************************************
*/

/* RFAL Guard Time (GT) default values                 */
#define    RFAL_GT_NFCA                      rfalConvMsTo1fc(5U)     /*!< GTA  Digital 2.0  6.10.4.1 & B.2                                                                 */
#define    RFAL_GT_NFCB                      rfalConvMsTo1fc(5U)     /*!< GTB  Digital 2.0  7.9.4.1  & B.3                                                                 */
#define    RFAL_GT_NFCF                      rfalConvMsTo1fc(20U)    /*!< GTF  Digital 2.0  8.7.4.1  & B.4                                                                 */
#define    RFAL_GT_NFCV                      rfalConvMsTo1fc(5U)     /*!< GTV  Digital 2.0  9.7.5.1  & B.5                                                                 */
#define    RFAL_GT_PICOPASS                  rfalConvMsTo1fc(1U)     /*!< GT Picopass                                                                                      */
#define    RFAL_GT_AP2P                      rfalConvMsTo1fc(5U)     /*!< TIRFG  Ecma 340  11.1.1                                                                          */
#define    RFAL_GT_AP2P_ADJUSTED             rfalConvMsTo1fc(5U+25U) /*!< Adjusted GT for greater interoperability (Sony XPERIA P, Nokia N9, Huawei P2)                    */

/* RFAL Frame Delay Time (FDT) Listen default values   */
#define    RFAL_FDT_LISTEN_NFCA_POLLER       1172U    /*!< FDTA,LISTEN,MIN (n=9) Last bit: Logic "1" - tnn,min/2 Digital 1.1  6.10 ;  EMV CCP Spec Book D v2.01  4.8.1.3   */
#define    RFAL_FDT_LISTEN_NFCB_POLLER       1008U    /*!< TR0B,MIN         Digital 1.1  7.1.3 & A.3  ; EMV CCP Spec Book D v2.01  4.8.1.3 & Table A.5                     */
#define    RFAL_FDT_LISTEN_NFCF_POLLER       2672U    /*!< TR0F,LISTEN,MIN  Digital 1.1  8.7.1.1 & A.4                                                                     */
#define    RFAL_FDT_LISTEN_NFCV_POLLER       4310U    /*!< FDTV,LISTEN,MIN  t1 min       Digital 2.1  B.5  ;  ISO15693-3 2009  9.1                                          */
#define    RFAL_FDT_LISTEN_PICOPASS_POLLER   3400U    /*!< ISO15693 t1 min - observed adjustment                                                                           */
#define    RFAL_FDT_LISTEN_AP2P_POLLER       64U      /*!< FDT AP2P No actual FDTListen is required as fields switch and collision avoidance                               */
#define    RFAL_FDT_LISTEN_NFCA_LISTENER     1172U    /*!< FDTA,LISTEN,MIN  Digital 1.1  6.10                                                                              */
#define    RFAL_FDT_LISTEN_NFCB_LISTENER     1024U    /*!< TR0B,MIN         Digital 1.1  7.1.3 & A.3  ;  EMV CCP Spec Book D v2.01  4.8.1.3 & Table A.5                    */
#define    RFAL_FDT_LISTEN_NFCF_LISTENER     2688U    /*!< TR0F,LISTEN,MIN  Digital 2.1  8.7.1.1 & B.4                                                                     */
#define    RFAL_FDT_LISTEN_AP2P_LISTENER     64U      /*!< FDT AP2P No actual FDTListen exists as fields switch and collision avoidance                                    */

/*  RFAL Frame Delay Time (FDT) Poll default values    */
#define    RFAL_FDT_POLL_NFCA_POLLER         6780U    /*!< FDTA,POLL,MIN   Digital 1.1  6.10.3.1 & A.2                                                                     */
#define    RFAL_FDT_POLL_NFCA_T1T_POLLER     384U     /*!< RRDDT1T,MIN,B1  Digital 1.1  10.7.1 & A.5                                                                       */
#define    RFAL_FDT_POLL_NFCB_POLLER         6780U    /*!< FDTB,POLL,MIN = TR2B,MIN,DEFAULT Digital 1.1 7.9.3 & A.3  ;  EMVCo 3.0 FDTB,PCD,MIN  Table A.5                  */
#define    RFAL_FDT_POLL_NFCF_POLLER         6800U    /*!< FDTF,POLL,MIN   Digital 2.1  8.7.3 & B.4                                                                        */
#define    RFAL_FDT_POLL_NFCV_POLLER         4192U    /*!< FDTV,POLL  Digital 2.1  9.7.3.1  & B.5                                                                          */
#define    RFAL_FDT_POLL_PICOPASS_POLLER     1790U    /*!< FDT Max                                                                                                         */
#define    RFAL_FDT_POLL_AP2P_POLLER         6800U    /*!< AP2P inhere FDT from the Technology used (use longest: TR0F,POLL,MIN + TR1F)     Digital 2.2  17.11.1           */


/*
******************************************************************************
* GLOBAL TYPES
******************************************************************************
*/

/*! RFAL modes    */
typedef enum {
    RFAL_MODE_NONE                   = 0,    /*!< No mode selected/defined                                         */
    RFAL_MODE_POLL_NFCA              = 1,    /*!< Mode to perform as NFCA (ISO14443A) Poller (PCD)                 */
    RFAL_MODE_POLL_NFCA_T1T          = 2,    /*!< Mode to perform as NFCA T1T (Topaz) Poller (PCD)                 */
    RFAL_MODE_POLL_NFCB              = 3,    /*!< Mode to perform as NFCB (ISO14443B) Poller (PCD)                 */
    RFAL_MODE_POLL_B_PRIME           = 4,    /*!< Mode to perform as B' Calypso (Innovatron) (PCD)                 */
    RFAL_MODE_POLL_B_CTS             = 5,    /*!< Mode to perform as CTS Poller (PCD)                              */
    RFAL_MODE_POLL_NFCF              = 6,    /*!< Mode to perform as NFCF (FeliCa) Poller (PCD)                    */
    RFAL_MODE_POLL_NFCV              = 7,    /*!< Mode to perform as NFCV (ISO15963) Poller (PCD)                  */
    RFAL_MODE_POLL_PICOPASS          = 8,    /*!< Mode to perform as PicoPass / iClass Poller (PCD)                */
    RFAL_MODE_POLL_ACTIVE_P2P        = 9,    /*!< Mode to perform as Active P2P (ISO18092) Initiator               */
    RFAL_MODE_LISTEN_NFCA            = 10,   /*!< Mode to perform as NFCA (ISO14443A) Listener (PICC)              */
    RFAL_MODE_LISTEN_NFCB            = 11,   /*!< Mode to perform as NFCA (ISO14443B) Listener (PICC)              */
    RFAL_MODE_LISTEN_NFCF            = 12,   /*!< Mode to perform as NFCA (ISO15963) Listener (PICC)               */
    RFAL_MODE_LISTEN_ACTIVE_P2P      = 13    /*!< Mode to perform as Active P2P (ISO18092) Target                  */
} rfalMode;


/*! RFAL Bit rates    */
typedef enum {
    RFAL_BR_106                      = 0,    /*!< Bit Rate 106 kbit/s (fc/128)                                     */
    RFAL_BR_212                      = 1,    /*!< Bit Rate 212 kbit/s (fc/64)                                      */
    RFAL_BR_424                      = 2,    /*!< Bit Rate 424 kbit/s (fc/32)                                      */
    RFAL_BR_848                      = 3,    /*!< Bit Rate 848 kbit/s (fc/16)                                      */
    RFAL_BR_1695                     = 4,    /*!< Bit Rate 1695 kbit/s (fc/8)                                      */
    RFAL_BR_3390                     = 5,    /*!< Bit Rate 3390 kbit/s (fc/4)                                      */
    RFAL_BR_6780                     = 6,    /*!< Bit Rate 6780 kbit/s (fc/2)                                      */
    RFAL_BR_13560                    = 7,    /*!< Bit Rate 13560 kbit/s (fc)                                       */
    RFAL_BR_211p88                   = 0xE9, /*!< Bit Rate 211,88 kbit/s (fc/64) Fast Mode VICC->VCD               */
    RFAL_BR_105p94                   = 0xEA, /*!< Bit Rate 105,94 kbit/s (fc/128) Fast Mode VICC->VCD              */
    RFAL_BR_52p97                    = 0xEB, /*!< Bit Rate 52.97 kbit/s (fc/256) Fast Mode VICC->VCD               */
    RFAL_BR_26p48                    = 0xEC, /*!< Bit Rate 26,48 kbit/s (fc/512) NFCV VICC->VCD & VCD->VICC 1of4   */
    RFAL_BR_1p66                     = 0xED, /*!< Bit Rate 1,66 kbit/s (fc/8192) NFCV VCD->VICC 1of256             */
    RFAL_BR_KEEP                     = 0xFF  /*!< Value indicating to keep the same previous bit rate              */
} rfalBitRate;


/*! RFAL Compliance modes for upper modules  */
typedef enum {
    RFAL_COMPLIANCE_MODE_NFC,                /*!< Perform with NFC Forum 1.1 compliance                            */
    RFAL_COMPLIANCE_MODE_EMV,                /*!< Perform with EMVCo compliance                                    */
    RFAL_COMPLIANCE_MODE_ISO                 /*!< Perform with ISO10373 compliance                                 */
}rfalComplianceMode;


/*! RFAL main states flags    */
typedef enum {
    RFAL_STATE_IDLE                  = 0,
    RFAL_STATE_INIT                  = 1,
    RFAL_STATE_MODE_SET              = 2,
    
    RFAL_STATE_TXRX                  = 3,
    RFAL_STATE_LM                    = 4,
    RFAL_STATE_WUM                   = 5
    
} rfalState;

/*! RFAL transceive states    */
typedef enum {
    RFAL_TXRX_STATE_IDLE             = 0,
    RFAL_TXRX_STATE_INIT             = 1,
    RFAL_TXRX_STATE_START            = 2,
        
    RFAL_TXRX_STATE_TX_IDLE          = 11,
    RFAL_TXRX_STATE_TX_WAIT_GT       = 12,
    RFAL_TXRX_STATE_TX_WAIT_FDT      = 13,
    RFAL_TXRX_STATE_TX_PREP_TX       = 14,
    RFAL_TXRX_STATE_TX_TRANSMIT      = 15,
    RFAL_TXRX_STATE_TX_WAIT_WL       = 16,
    RFAL_TXRX_STATE_TX_RELOAD_FIFO   = 17,
    RFAL_TXRX_STATE_TX_WAIT_TXE      = 18,
    RFAL_TXRX_STATE_TX_DONE          = 19,
    RFAL_TXRX_STATE_TX_FAIL          = 20,
    
    RFAL_TXRX_STATE_RX_IDLE          = 81,
    RFAL_TXRX_STATE_RX_WAIT_EON      = 82,
    RFAL_TXRX_STATE_RX_WAIT_RXS      = 83,
    RFAL_TXRX_STATE_RX_WAIT_RXE      = 84,
    RFAL_TXRX_STATE_RX_READ_FIFO     = 85,
    RFAL_TXRX_STATE_RX_ERR_CHECK     = 86,
    RFAL_TXRX_STATE_RX_READ_DATA     = 87,
    RFAL_TXRX_STATE_RX_WAIT_EOF      = 88,
    RFAL_TXRX_STATE_RX_DONE          = 89,
    RFAL_TXRX_STATE_RX_FAIL          = 90,
    
} rfalTransceiveState;


/*! RFAL transceive flags                                                                                                                    */
enum {
    RFAL_TXRX_FLAGS_CRC_TX_AUTO      = (0U<<0),   /*!< CRC will be generated automatic upon transmission                                     */
    RFAL_TXRX_FLAGS_CRC_TX_MANUAL    = (1U<<0),   /*!< CRC was calculated manually, included in txBuffer                                     */
    RFAL_TXRX_FLAGS_CRC_RX_KEEP      = (1U<<1),   /*!< Upon Reception keep the CRC in rxBuffer (reflected on rcvd length)                    */
    RFAL_TXRX_FLAGS_CRC_RX_REMV      = (0U<<1),   /*!< Remove the CRC from rxBuffer                                                          */
    RFAL_TXRX_FLAGS_NFCIP1_ON        = (1U<<2),   /*!< Enable NFCIP1 mode: Add SB(F0) and LEN bytes during Tx and skip SB(F0) byte during Rx */
    RFAL_TXRX_FLAGS_NFCIP1_OFF       = (0U<<2),   /*!< Disable NFCIP1 mode: do not append protocol bytes while Tx nor skip while Rx          */
    RFAL_TXRX_FLAGS_AGC_OFF          = (1U<<3),   /*!< Disable Automatic Gain Control, improving multiple devices collision detection. \b DEPRECATED: flag is depreacted, usage of Anticollision APIs based on Analog Config table with RFAL_ANALOG_CONFIG_ANTICOL settings */
    RFAL_TXRX_FLAGS_AGC_ON           = (0U<<3),   /*!< Enable Automatic Gain Control, improving single device reception                \b DEPRECATED: flag is deprecated, usage of Anticollision APIs based on Analog Config table with RFAL_ANALOG_CONFIG_ANTICOL settings */
    RFAL_TXRX_FLAGS_PAR_RX_KEEP      = (1U<<4),   /*!< Disable Parity check and keep the Parity and CRC bits in the received buffer          */
    RFAL_TXRX_FLAGS_PAR_RX_REMV      = (0U<<4),   /*!< Enable Parity check and remove the parity bits from the received buffer               */
    RFAL_TXRX_FLAGS_PAR_TX_NONE      = (1U<<5),   /*!< Disable automatic Parity generation (ISO14443A) and use the one provided in the buffer*/
    RFAL_TXRX_FLAGS_PAR_TX_AUTO      = (0U<<5),   /*!< Enable automatic Parity generation (ISO14443A)                                        */
    RFAL_TXRX_FLAGS_NFCV_FLAG_MANUAL = (1U<<6),   /*!< Disable automatic adaption of flag byte (ISO15693) according to current comm params   */
    RFAL_TXRX_FLAGS_NFCV_FLAG_AUTO   = (0U<<6),   /*!< Enable automatic adaption of flag byte (ISO115693) according to current comm params   */
    RFAL_TXRX_FLAGS_CRC_RX_MANUAL    = (1U<<7),   /*!< Disable automatic CRC check                                                           */
    RFAL_TXRX_FLAGS_CRC_RX_AUTO      = (0U<<7),   /*!< Enable automatic CRC check                                                            */
};


/*! RFAL error handling                                                                                                                      */
typedef enum {
    RFAL_ERRORHANDLING_NONE          = 0,         /*!< No special error handling will be performed                                           */
    RFAL_ERRORHANDLING_EMD           = 1          /*!< EMD suppression enabled  Digital 2.1  4.1.1.1 ; EMVCo 3.0  4.9.2 ; ISO 14443-3  8.3   */
} rfalEHandling;


/*! Struct that holds all context to be used on a Transceive                                                */
typedef struct {
    uint8_t*              txBuf;                  /*!< (In)  Buffer where outgoing message is located       */
    uint16_t              txBufLen;               /*!< (In)  Length of the outgoing message in bits         */
    
    uint8_t*              rxBuf;                  /*!< (Out) Buffer where incoming message will be placed   */
    uint16_t              rxBufLen;               /*!< (In)  Maximum length of the incoming message in bits */
    uint16_t*             rxRcvdLen;              /*!< (Out) Actual received length in bits                 */
    
    uint32_t              flags;                  /*!< (In)  TransceiveFlags indication special handling    */
    uint32_t              fwt;                    /*!< (In)  Frame Waiting Time in 1/fc                     */
} rfalTransceiveContext;


/*! System callback to indicate an event that requires a system reRun        */
typedef void (* rfalUpperLayerCallback)(void);

/*! Callback to be executed before a Transceive                              */
typedef void (* rfalPreTxRxCallback)(void);

/*! Callback to be executed after a Transceive                               */
typedef void (* rfalPostTxRxCallback)(void);

/*! Callback to sync actual transmission start                               */
typedef bool (* rfalSyncTxRxCallback)(void);

/*! Callback upon External Field detected while in Listen Mode              */
typedef void (* rfalLmEonCallback)(void);

/*******************************************************************************/
/*  ISO14443A                                                                  */
/*******************************************************************************/

/*! RFAL ISO 14443A Short Frame Command */
typedef enum
{
     RFAL_14443A_SHORTFRAME_CMD_WUPA = 0x52,  /*!< ISO14443A WUPA / NFC-A ALL_REQ  */
     RFAL_14443A_SHORTFRAME_CMD_REQA = 0x26   /*!< ISO14443A REQA / NFC-A SENS_REQ */    
} rfal14443AShortFrameCmd;

/*******************************************************************************/


/*******************************************************************************/
/*  FeliCa                                                                     */
/*******************************************************************************/

#define RFAL_FELICA_LEN_LEN                        1U                                           /*!< FeliCa LEN byte length                                              */
#define RFAL_FELICA_POLL_REQ_LEN                   (RFAL_FELICA_LEN_LEN + 1U + 2U + 1U + 1U)    /*!< FeliCa Poll Request length (LEN + CMD + SC + RC + TSN)              */
#define RFAL_FELICA_POLL_RES_LEN                   (RFAL_FELICA_LEN_LEN + 1U + 8U + 8U + 2U)    /*!< Maximum FeliCa Poll Response length (LEN + CMD + NFCID2 + PAD + RD) */
#define RFAL_FELICA_POLL_MAX_SLOTS                 16U                                          /*!< Maximum number of slots (TSN) on FeliCa Poll                        */


/*! NFC-F RC (Request Code) codes  NFC Forum Digital 1.1 Table 42                                                                                                        */
enum 
{
    RFAL_FELICA_POLL_RC_NO_REQUEST        =     0x00U,                                          /*!< RC: No System Code information requested                            */
    RFAL_FELICA_POLL_RC_SYSTEM_CODE       =     0x01U,                                          /*!< RC: System Code information requested                               */
    RFAL_FELICA_POLL_RC_COM_PERFORMANCE   =     0x02U                                           /*!< RC: Advanced protocol features supported                            */
};


/*! NFC-F TSN (Time Slot Number) codes  NFC Forum Digital 1.1 Table 43   */
typedef enum 
{
    RFAL_FELICA_1_SLOT    =  0,   /*!< TSN with number of Time Slots: 1  */
    RFAL_FELICA_2_SLOTS   =  1,   /*!< TSN with number of Time Slots: 2  */
    RFAL_FELICA_4_SLOTS   =  3,   /*!< TSN with number of Time Slots: 4  */
    RFAL_FELICA_8_SLOTS   =  7,   /*!< TSN with number of Time Slots: 8  */
    RFAL_FELICA_16_SLOTS  =  15   /*!< TSN with number of Time Slots: 16 */
} rfalFeliCaPollSlots;


/*! NFCF Poll Response  NFC Forum Digital 1.1 Table 44 */
typedef uint8_t rfalFeliCaPollRes[RFAL_FELICA_POLL_RES_LEN];


/*******************************************************************************/


/*******************************************************************************/
/*  Listen Mode                                                                */  
/*******************************************************************************/

/*! RFAL Listen Mode NFCID Length */
typedef enum 
{
    RFAL_LM_NFCID_LEN_04  = RFAL_NFCID1_SINGLE_LEN, /*!< Listen mode indicates  4 byte NFCID */
    RFAL_LM_NFCID_LEN_07  = RFAL_NFCID1_DOUBLE_LEN, /*!< Listen mode indicates  7 byte NFCID */
    RFAL_LM_NFCID_LEN_10  = RFAL_NFCID1_TRIPLE_LEN, /*!< Listen mode indicates 10 byte NFCID */   
} rfalLmNfcidLen;


/*! RFAL Listen Mode States */
typedef enum 
{
    RFAL_LM_STATE_NOT_INIT              = 0x00,     /*!< Not Initialized state                       */
    RFAL_LM_STATE_POWER_OFF             = 0x01,     /*!< Power Off state                             */
    RFAL_LM_STATE_IDLE                  = 0x02,     /*!< Idle state  Activity 1.1  5.2               */
    RFAL_LM_STATE_READY_A               = 0x03,     /*!< Ready A state  Activity 1.1  5.3 5.4 & 5.5  */
    RFAL_LM_STATE_READY_B               = 0x04,     /*!< Ready B state  Activity 1.1  5.11 5.12      */
    RFAL_LM_STATE_READY_F               = 0x05,     /*!< Ready F state  Activity 1.1  5.15           */
    RFAL_LM_STATE_ACTIVE_A              = 0x06,     /*!< Active A state  Activity 1.1  5.6           */
    RFAL_LM_STATE_CARDEMU_4A            = 0x07,     /*!< Card Emulation 4A state  Activity 1.1  5.10 */
    RFAL_LM_STATE_CARDEMU_4B            = 0x08,     /*!< Card Emulation 4B state  Activity 1.1  5.14 */
    RFAL_LM_STATE_CARDEMU_3             = 0x09,     /*!< Card Emulation 3 state  Activity 1.1  5.18  */
    RFAL_LM_STATE_TARGET_A              = 0x0A,     /*!< Target A state  Activity 1.1  5.9           */
    RFAL_LM_STATE_TARGET_F              = 0x0B,     /*!< Target F state  Activity 1.1  5.17          */
    RFAL_LM_STATE_SLEEP_A               = 0x0C,     /*!< Sleep A state  Activity 1.1  5.7            */
    RFAL_LM_STATE_SLEEP_B               = 0x0D,     /*!< Sleep B state  Activity 1.1  5.13           */
    RFAL_LM_STATE_READY_Ax              = 0x0E,     /*!< Ready A* state  Activity 1.1  5.3 5.4 & 5.5 */
    RFAL_LM_STATE_ACTIVE_Ax             = 0x0F,     /*!< Active A* state  Activity 1.1  5.6          */
    RFAL_LM_STATE_SLEEP_AF              = 0x10,     /*!< Sleep AF state  Activity 1.1  5.19          */
} rfalLmState;


/*! RFAL Listen Mode Passive A configs */
typedef struct 
{
    rfalLmNfcidLen   nfcidLen;                        /*!< NFCID Len (4, 7 or 10 bytes)              */
    uint8_t          nfcid[RFAL_NFCID1_TRIPLE_LEN];   /*!< NFCID                                     */
    uint8_t          SENS_RES[RFAL_LM_SENS_RES_LEN];  /*!< NFC-106k; SENS_REQ Response               */
    uint8_t          SEL_RES;                         /*!< SEL_RES (SAK) with complete NFCID1 (UID)  */
} rfalLmConfPA;


/*! RFAL Listen Mode Passive B configs */
typedef struct 
{
    uint8_t          SENSB_RES[RFAL_LM_SENSB_RES_LEN];  /*!< SENSF_RES                               */
} rfalLmConfPB;


/*! RFAL Listen Mode Passive F configs */
typedef struct 
{
    uint8_t          SC[RFAL_LM_SENSF_SC_LEN];          /*!< System Code to listen for               */
    uint8_t          SENSF_RES[RFAL_LM_SENSF_RES_LEN];  /*!< SENSF_RES                               */
} rfalLmConfPF;

/*! RFAL low power modes    */
typedef enum {
    RFAL_LP_MODE_PD  = 0,    /*!< Set RF Chip in Power Down state                                      */
    RFAL_LP_MODE_HR  = 1     /*!< Set RF Chip in Hold Reset state (available for specific devices)     */
} rfalLpMode;

/*******************************************************************************/


/*******************************************************************************/
/*  Wake-Up Mode                                                               */  
/*******************************************************************************/

#define RFAL_WUM_REFERENCE_AUTO           0xFFU      /*!< Indicates new reference is set by the driver */

/*! RFAL Wake-Up Mode States */
typedef enum 
{
    RFAL_WUM_STATE_NOT_INIT              = 0x00,     /*!< Not Initialized state                       */
    RFAL_WUM_STATE_INITIALIZING          = 0x01,     /*!< Wake-Up mode is starting                    */
    RFAL_WUM_STATE_ENABLED               = 0x02,     /*!< Wake-Up mode is enabled                     */
    RFAL_WUM_STATE_ENABLED_WOKE          = 0x03,     /*!< Wake-Up mode enabled and has received IRQ(s)*/
} rfalWumState;


/*******************************************************************************/

/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/


/*! 
 *****************************************************************************
 * \brief  RFAL Initialize
 *  
 * Initializes RFAL layer and the ST25R391x
 * Ensures that ST25R is properly connected and returns error if any problem 
 * is detected
 *
 * \warning rfalAnalogConfigInitialize() should be called before so that 
 *           the Analog config table has been previously initialized.
 *           
 * \return RFAL_ERR_HW_MISMATCH  : Expected HW do not match or communication error
 * \return RFAL_ERR_NONE         : No error
 *****************************************************************************
 */
ReturnCode rfalInitialize( void );


/*!
 *****************************************************************************
 * \brief  RFAL Calibrate 
 *  
 * Performs necessary calibration of RF chip in case it is indicated by current
 * register settings. E.g. antenna calibration and regulator calibration
 *
 * \return RFAL_ERR_WRONG_STATE  : RFAL not initialized
 * \return RFAL_ERR_NONE         : No error
 * 
 *****************************************************************************
 */
ReturnCode rfalCalibrate( void );


/*!
 *****************************************************************************
 * \brief  RFAL Adjust Regulators 
 *  
 * Adjusts ST25R391x regulators 
 * 
 * \param[out]  result : the result of the calibrate antenna in mV
 *                       NULL if result not requested
 *
 * \return RFAL_ERR_WRONG_STATE  : RFAL not initialized
 * \return RFAL_ERR_NONE         : No error
 * 
 *****************************************************************************
 */
ReturnCode rfalAdjustRegulators( uint16_t* result );


/*!
 *****************************************************************************
 * \brief RFAL Set System Callback
 *
 * Sets a callback for the driver to call when an event has occurred that 
 * may require the system to be notified
 * 
 * \param[in]  pFunc : method pointer for the upper layer callback 
 * 
 *****************************************************************************
 */
void rfalSetUpperLayerCallback( rfalUpperLayerCallback pFunc );


/*!
 *****************************************************************************
 * \brief RFAL Set Pre Tx Callback
 *
 * Sets a callback for the driver to call before a Transceive 
 * 
 * \param[in]  pFunc : method pointer for the Pre Tx callback 
 * 
 *****************************************************************************
 */
void rfalSetPreTxRxCallback( rfalPreTxRxCallback pFunc );


/*!
 *****************************************************************************
 * \brief RFAL Sync Pre Tx Callback
 *
 * Sets a callback for the driver to execute in order to Syncronize actual
 * transmission start.
 * If the callback is set TxRx will hold until Sync callback returns true.
 * 
 * \param[in]  pFunc : method pointer for the Sync Tx callback 
 * 
 *****************************************************************************
 */
void rfalSetSyncTxRxCallback( rfalSyncTxRxCallback pFunc );


/*!
 *****************************************************************************
 * \brief RFAL Set Post Tx Callback
 *
 * Sets a callback for the driver to call after a Transceive 
 * 
 * \param[in]  pFunc : method pointer for the Post Tx callback 
 * 
 *****************************************************************************
 */
void rfalSetPostTxRxCallback( rfalPostTxRxCallback pFunc );


/*! 
 *****************************************************************************
 * \brief RFAL Set LM EON Callback
 *
 * Sets a callback upon External Field On detected while in Passive Listen Mode
 *
 * \warning callabck available only on applicable devices, 
 *            supporting Passive Listen Mode
 * 
 * \param[in]  pFunc : method pointer for the LM EON callback 
 * 
 *****************************************************************************
 */
void rfalSetLmEonCallback( rfalLmEonCallback pFunc );


/*! 
 *****************************************************************************
 * \brief  RFAL Deinitialize
 *  
 * Deinitializes RFAL layer and the ST25R
 *
 * \return RFAL_ERR_NONE : No error
 * 
 *****************************************************************************
 */
ReturnCode rfalDeinitialize( void );


/*! 
 *****************************************************************************
 * \brief  RFAL Set Mode
 *  
 * Sets the mode that RFAL will operate on the following communications.
 * Proper initializations will be performed on the ST25R
 * 
 * \warning bit rate value RFAL_BR_KEEP is not allowed, only in rfalSetBitRate()
 * 
 * \warning the mode will be applied immediately on the RFchip regardless of 
 *          any ongoing operations like Transceive, ListenMode
 * 
 * \param[in]  mode : mode for the RFAL/RFchip to perform
 * \param[in]  txBR : transmit bit rate
 * \param[in]  rxBR : receive bit rate 
 * 
 * \see rfalIsGTExpired
 * \see rfalMode
 *
 * \return RFAL_ERR_WRONG_STATE  : RFAL not initialized
 * \return RFAL_ERR_PARAM        : Invalid parameter
 * \return RFAL_ERR_NONE         : No error
 * 
 *****************************************************************************
 */
ReturnCode rfalSetMode( rfalMode mode, rfalBitRate txBR, rfalBitRate rxBR );


/*! 
 *****************************************************************************
 * \brief  RFAL Get Mode
 *  
 * Gets the mode that RFAL is set to operate
 * 
 * \see rfalMode
 *
 * \return rfalMode : The current RFAL mode
 *****************************************************************************
 */
rfalMode rfalGetMode( void );


/*! 
 *****************************************************************************
 * \brief  RFAL Set Bit Rate
 *  
 * Sets the Tx and Rx bit rates with the given values 
 * The bit rate change is applied on the RF chip remaining in the same  
 * mode previous defined with rfalSetMode()
 * 
 * If no mode is defined bit rates will not be applied and an error 
 * is returned
 * 
 * \param[in]  txBR : transmit bit rate
 * \param[in]  rxBR : receive bit rate 
 * 
 * \see rfalSetMode
 * \see rfalMode
 * \see rfalBitRate
 *
 * \return RFAL_ERR_WRONG_STATE     : RFAL not initialized
 * \return RFAL_ERR_PARAM           : Invalid parameter
 * \return RFAL_ERR_NOT_IMPLEMENTED : Mode not implemented
 * \return RFAL_ERR_NONE            : No error
 * 
 *****************************************************************************
 */
ReturnCode rfalSetBitRate( rfalBitRate txBR, rfalBitRate rxBR );


/*! 
 *****************************************************************************
 * \brief  RFAL Get Bit Rate
 *  
 * Gets the Tx and Rx current bit rates 
 * 
 * If RFAL is not initialized or mode not set the bit rates return will 
 * be invalid RFAL_BR_KEEP
 * 
 * \param[out]  txBR : RFAL's current Tx Bit Rate
 * \param[out]  rxBR : RFAL's current Rx Bit Rate
 * 
 * \see rfalSetBitRate
 * \see rfalBitRate
 *
 * \return RFAL_ERR_WRONG_STATE  : RFAL not initialized or mode not set
 * \return RFAL_ERR_NONE         : No error
 *****************************************************************************
 */
ReturnCode rfalGetBitRate( rfalBitRate *txBR, rfalBitRate *rxBR );


/*! 
 *****************************************************************************
 * \brief Set Error Handling Mode
 *  
 *  Sets the error handling mode to be used by the RFAL
 *  
 * \param[in]  eHandling : the error handling mode
 * 
 *****************************************************************************
 */
void rfalSetErrorHandling( rfalEHandling eHandling );


/*! 
 *****************************************************************************
 * \brief Get Error Handling Mode
 *  
 *  Gets the error handling mode currently used by the RFAL 
 *  
 * \return rfalEHandling : Current error handling mode
 *****************************************************************************
 */
rfalEHandling rfalGetErrorHandling( void );


/*! 
 *****************************************************************************
 * \brief Set Observation Mode
 *  
 * Sets ST25R391x observation modes for RF debug purposes
 *
 * \param[in]  txMode : the observation mode to be used during transmission
 * \param[in]  rxMode : the observation mode to be used during reception
 * 
 * \warning The Observation Mode is an advanced feature and should be set 
 *          according to the documentation of the part number in use.
 *          Please refer to the corresponding Datasheet or Application Note(s)
 *****************************************************************************
 */
void rfalSetObsvMode( uint32_t txMode, uint32_t rxMode );


/*! 
 *****************************************************************************
 * \brief Get Observation Mode
 *  
 * Gets ST25R391x the current configured observation modes
 *
 * \param[in]  txMode : the current observation mode configured for transmission
 * \param[in]  rxMode : the current observation mode configured for reception
 * 
 *****************************************************************************
 */
void rfalGetObsvMode( uint8_t* txMode, uint8_t* rxMode );


/*! 
 *****************************************************************************
 * \brief Disable Observation Mode
 *  
 * Disables the ST25R391x observation mode
 *****************************************************************************
 */
void rfalDisableObsvMode( void );


/*! 
 *****************************************************************************
 * \brief  RFAL Set FDT Poll
 *  
 * Sets the Frame Delay Time (FDT) to be used on the following
 * communications.
 * 
 * FDT Poll is the minimum time following a Poll Frame during 
 * which no subsequent Poll Frame can be sent (without a response from 
 * the Listener in between)
 * FDTx,PP,MIN - Digital 1.1  6.10.2  &  7.9.2  &  8.7.2
 * 
 * \param[in]  FDTPoll : Frame Delay Time in 1/fc cycles
 *
 *****************************************************************************
 */
void rfalSetFDTPoll( uint32_t FDTPoll );


/*! 
 *****************************************************************************
 * \brief  RFAL Set FDT Poll
 *  
 * Gets the current Frame Delay Time (FDT) 
 * 
 * FDT Poll is the minimum time following a Poll Frame during 
 * which no subsequent Poll Frame can be sent (without a response from 
 * the Listener in between)
 * FDTx,PP,MIN - Digital 1.1  6.10.2  &  7.9.2  &  8.7.2
 *  
 * \return FDT : current FDT value in 1/fc cycles
 *
 *****************************************************************************
 */
uint32_t rfalGetFDTPoll( void );


/*! 
 *****************************************************************************
 * \brief  RFAL Set FDT Listen
 *  
 * Sets the Frame Delay Time (FDT) Listen minimum to be used on the 
 * following communications.
 * 
 * FDT Listen is the minimum time between a Poll Frame and a Listen Frame
 * FDTx,LISTEN,MIN - Digital 1.1  6.10.1  &  7.9.1  &  8.7.1
 *  
 * \param[in]  FDTListen : Frame Delay Time in 1/fc cycles
 *
 *****************************************************************************
 */
void rfalSetFDTListen( uint32_t FDTListen );


/*! 
 *****************************************************************************
 * \brief  RFAL Set FDT Listen
 *  
 * Gets the Frame Delay Time (FDT) Listen minimum  
 * 
 * FDT Listen is the minimum time between a Poll Frame and a Listen Frame
 * FDTx,LISTEN,MIN - Digital 1.1  6.10.1  &  7.9.1  &  8.7.1
 *  
 * \return FDT : current FDT value in 1/fc cycles
 *
 *****************************************************************************
 */
uint32_t rfalGetFDTListen( void );


/*! 
 *****************************************************************************
 * \brief  RFAL Get GT
 *  
 * Gets the current Guard Time (GT)
 *  
 * GT is the minimum time when a device in Listen Mode is exposed to an 
 * unmodulated carrier
 *  
 * \return GT :  Guard Time in 1/fc cycles
 *
 *****************************************************************************
 */
uint32_t rfalGetGT( void );


/*! 
 *****************************************************************************
 * \brief  RFAL Set GT
 *  
 * Sets the Guard Time (GT) to be used on the following communications.
 * 
 * GT is the minimum time when a device in Listen Mode is exposed to an 
 * unmodulated carrier
 *  
 * \param[in]  GT : Guard Time in 1/fc cycles
 *                  RFAL_GT_NONE if no GT should be applied
 *
 *****************************************************************************
 */
void rfalSetGT( uint32_t GT );


/*! 
 *****************************************************************************
 * \brief  RFAL Is GT expired 
 *  
 * Checks whether the GT timer has expired
 *    
 * \return true  : GT has expired or not running
 * \return false : GT is still running
 *
 *****************************************************************************
 */
bool rfalIsGTExpired( void );


/*! 
 *****************************************************************************
 * \brief  RFAL Turn Field On and Start GT
 *  
 * Turns the Field On, performing Initial Collision Avoidance
 * 
 * After Field On, if GT was set before, it starts the GT timer to be 
 * used on the following communications.
 *  
 * \return RFAL_ERR_RF_COLLISION : External field detected
 * \return RFAL_ERR_NONE         : Field turned On
 *
 *****************************************************************************
 */
ReturnCode rfalFieldOnAndStartGT( void );


/*! 
 *****************************************************************************
 * \brief  RFAL Turn Field Off
 *  
 * Turns the Field Off
 *   
 * \return RFAL_ERR_NONE : Field turned Off
 *****************************************************************************
 */
ReturnCode rfalFieldOff( void );



/*****************************************************************************
 *  Transceive                                                               *
 *****************************************************************************/

/*! 
 *****************************************************************************
 * \brief  RFAL Set transceive context
 *  
 * Set the context that will be used for the following Transceive
 * Output and input buffers have to be passed and all other details prior to 
 * the Transceive itself has been started
 * 
 * This method only sets the context. Once set, rfalWorker has
 * to be executed until is done
 * 
 * \param[in]  ctx : the context for the following Transceive
 * 
 * \see  rfalWorker
 * \see  rfalGetTransceiveStatus
 *
 * \return RFAL_ERR_NONE        : Done with no error
 * \return RFAL_ERR_WRONG_STATE : Not initialized properly 
 * \return RFAL_ERR_PARAM       : Invalid parameter or configuration
 *****************************************************************************
 */
ReturnCode rfalStartTransceive( const rfalTransceiveContext *ctx );


/*! 
 *****************************************************************************
 * \brief  Get Transceive State
 *  
 * Gets current Transceive internal State
 *
 * \return rfalTransceiveState : the current Transceive internal State
 *****************************************************************************
 */
rfalTransceiveState rfalGetTransceiveState( void );


/*! 
 *****************************************************************************
 * \brief  Get Transceive Status
 *  
 * Gets current Transceive status
 *
 * \return  RFAL_ERR_NONE         : Transceive done with no error
 * \return  RFAL_ERR_BUSY         : Transceive ongoing
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
ReturnCode rfalGetTransceiveStatus( void );


/*! 
 *****************************************************************************
 * \brief  Is Transceive in Tx
 *  
 * Checks if Transceive is in Transmission state
 *
 * \return true   Transmission ongoing
 * \return false  Not in transmission state
 *****************************************************************************
 */
bool rfalIsTransceiveInTx( void );


/*! 
 *****************************************************************************
 * \brief  Is Transceive in Rx
 *  
 * Checks if Transceive is in Reception state 
 *
 * \return true   Transmission done/reception ongoing
 * \return false  Not in reception state
 *****************************************************************************
 */
bool rfalIsTransceiveInRx( void );


/*! 
 *****************************************************************************
 * \brief  Get Transceive RSSI
 *  
 * Gets the RSSI value of the last executed Transceive in mV
 *
 * \param[out]  rssi : RSSI value
 *
 * \return  RFAL_ERR_NOTSUPP : Feature not supported
 * \return  RFAL_ERR_PARAM   : Invalid parameter
 * \return  RFAL_ERR_NONE    : No error
 *****************************************************************************
 */
ReturnCode rfalGetTransceiveRSSI( uint16_t *rssi );


/*! 
 *****************************************************************************
 * \brief  Is Transceive Subcarrier Detected
 *  
 * Checks on the last executed Transceive a subcarrier was detected
 *
 * \return true   Subcarrier was detected
 * \return false  No subcarrier detected | Not supported
 *****************************************************************************
 */
bool rfalIsTransceiveSubcDetected( void );


/*! 
 *****************************************************************************
 *  \brief RFAL Worker
 *  
 *  This runs RFAL layer, which drives the actual Transceive procedure
 *  It MUST be executed frequently in order to execute the RFAL internal
 *  states and perform the requested operations
 *
 *****************************************************************************
 */
void rfalWorker( void );


/*****************************************************************************
 *  ISO1443A                                                                 *  
 *****************************************************************************/

/*! 
 *****************************************************************************
 *  \brief Transceives an ISO14443A ShortFrame  
 *  
 *  Sends REQA or WUPA to detect if there is any PICC in the field 
 *
 * \param[in]  txCmd:     Command to be sent:
 *                           0x52 WUPA / ALL_REQ
 *                           0x26 REQA / SENS_REQ
 * \param[out] rxBuf    : buffer to place the response
 * \param[in]  rxBufLen : length of rxBuf in bytes
 * \param[out] rxRcvdLen: received length in bits
 * \param[in]  fwt      : Frame Waiting Time in 1/fc
 * 
 * \warning If fwt is set to RFAL_FWT_NONE it will make endlessly for 
 *         a response, which on a blocking method may not be the 
 *         desired usage 
 * 
 * \return RFAL_ERR_NONE         : If there is response
 * \return RFAL_ERR_TIMEOUT      : If there is no response
 * \return RFAL_ERR_RF_COLLISION : A collision was detected
 *  
 *****************************************************************************
 */
ReturnCode rfalISO14443ATransceiveShortFrame( rfal14443AShortFrameCmd txCmd, uint8_t* rxBuf, uint8_t rxBufLen, uint16_t* rxRcvdLen, uint32_t fwt );


/*!
 *****************************************************************************
 * \brief Sends an ISO14443A Anticollision Frame 
 * 
 * This is used to perform ISO14443A anti-collision. 
 * \note Anticollision is sent without CRC
 * 
 * 
 * \param[in,out] buf        : reference to ANTICOLLISION command (with known UID if any) to be sent (also out param)
 *                             reception will be place on this buf after bytesToSend 
 *                             buffer must be capable of holding a whole Anticollison frame (rfalNfcaSelReq)
 * \param[in,out] bytesToSend: reference number of full bytes to be sent (including CMD byte and SEL_PAR)
 *                             if a collision occurs will contain the number of clear bytes  
 * \param[in,out] bitsToSend : reference to number of bits (0-7) to be sent; and received (also out param)
 *                             if a collision occurs will indicate the number of clear bits (also out param)
 * \param[out]    rxLength   : reference to the return the received length in bits
 * \param[in]     fwt        : Frame Waiting Time in 1/fc
 * 
 * \return RFAL_ERR_NONE if there is no error
 *****************************************************************************
 */
ReturnCode rfalISO14443ATransceiveAnticollisionFrame( uint8_t *buf, uint8_t *bytesToSend, uint8_t *bitsToSend, uint16_t *rxLength, uint32_t fwt );


/*!
 *****************************************************************************
 * \brief Start ISO14443A Anticollision Frame transceive
 * 
 * This starts the transceive of an ISO14443A anti-collision frame.
 * \note Anticollision is sent without CRC
 * 
 * 
 * \param[in,out] buf        : reference to ANTICOLLISION command (with known UID if any) to be sent (also out param)
 *                             reception will be place on this buf after bytesToSend 
 *                             buffer must be capable of holding a whole Anticollison frame (rfalNfcaSelReq)
 * \param[in,out] bytesToSend: reference number of full bytes to be sent (including CMD byte and SEL_PAR)
 *                             if a collision occurs will contain the number of clear bytes  
 * \param[in,out] bitsToSend : reference to number of bits (0-7) to be sent; and received (also out param)
 *                             if a collision occurs will indicate the number of clear bits (also out param)
 * \param[out]    rxLength   : reference to the return the received length in bits
 * \param[in]     fwt        : Frame Waiting Time in 1/fc
 * 
 * \return RFAL_ERR_NONE if there is no error
 *****************************************************************************
 */
ReturnCode rfalISO14443AStartTransceiveAnticollisionFrame( uint8_t *buf, uint8_t *bytesToSend, uint8_t *bitsToSend, uint16_t *rxLength, uint32_t fwt );


/*!
 *****************************************************************************
 * \brief Get ISO14443A Anticollision Frame Status
 * 
 * This gets the ISO14443A anti-collision frame status.
 * 
 * 
 * \return RFAL_ERR_NONE if there is no error
 *****************************************************************************
 */
ReturnCode rfalISO14443AGetTransceiveAnticollisionFrameStatus( void );


/*****************************************************************************
 *  FeliCa                                                                   *  
 *****************************************************************************/

/*!
 *****************************************************************************
 * \brief FeliCa Poll 
 * 
 * Sends a Poll Request and collects all Poll Responses according to the 
 * given slots  
 * 
 * 
 * \param[in]   slots             : number of slots for the Poll Request
 * \param[in]   sysCode           : system code (SC) for the Poll Request  
 * \param[in]   reqCode           : request code (RC) for the Poll Request
 * \param[out]  pollResList       : list of all responses
 * \param[in]   pollResListSize   : number of responses that can be placed in pollResList 
 * \param[out]  devicesDetected   : number of cards found
 * \param[out]  collisionsDetected: number of collisions detected
 * 
 * \return RFAL_ERR_NONE        : If there is no error
 * \return RFAL_ERR_PARAM       : Invalid parameter
 * \return RFAL_ERR_WRONG_STATE : RFAL not initialized or mode not set
 * \return RFAL_ERR_TIMEOUT     : If there is no response
 *****************************************************************************
 */
ReturnCode rfalFeliCaPoll( rfalFeliCaPollSlots slots, uint16_t sysCode, uint8_t reqCode, rfalFeliCaPollRes* pollResList, uint8_t pollResListSize, uint8_t *devicesDetected, uint8_t *collisionsDetected );

/*!
 *****************************************************************************
 * \brief Start FeliCa Poll 
 * 
 * Triggers a Poll Request and all Poll Responses will be collected according 
 * to the given nuber of slots  
 * 
 * 
 * \param[in]   slots             : number of slots for the Poll Request
 * \param[in]   sysCode           : system code (SC) for the Poll Request  
 * \param[in]   reqCode           : request code (RC) for the Poll Request
 * \param[out]  pollResList       : list of all responses
 * \param[in]   pollResListSize   : number of responses that can be placed in pollResList 
 * \param[out]  devicesDetected   : number of cards found
 * \param[out]  collisionsDetected: number of collisions detected
 * 
 * \return RFAL_ERR_NONE        : If there is no error
 * \return RFAL_ERR_PARAM       : Invalid parameter
 * \return RFAL_ERR_WRONG_STATE : RFAL not initialized or mode not set
 *****************************************************************************
 */
ReturnCode rfalStartFeliCaPoll( rfalFeliCaPollSlots slots, uint16_t sysCode, uint8_t reqCode, rfalFeliCaPollRes* pollResList, uint8_t pollResListSize, uint8_t *devicesDetected, uint8_t *collisionsDetected );

/*!
 *****************************************************************************
 * \brief Get FeliCa Poll Status
 * 
 * Gets the current state of the Felica Poll Request triggered before
 *  by rfalStartFeliCaPoll()
 * 
 * 
 * 
 * \return RFAL_ERR_NONE        : If there is no error
 * \return  RFAL_ERR_BUSY       : Operation ongoing
 * \return RFAL_ERR_TIMEOUT     : If there is no response
 *****************************************************************************
 */
ReturnCode rfalGetFeliCaPollStatus( void );


/*****************************************************************************
 *  ISO15693                                                                 *  
 *****************************************************************************/

/*!
 *****************************************************************************
 * \brief Sends an ISO15693 Anticollision Frame 
 * 
 * This send the Anticollision|Inventory frame (INVENTORY_REQ)
 *
 * \warning rxBuf must be able to contain the payload and CRC
 * 
 * \param[in]  txBuf        : Buffer where outgoing message is located
 * \param[in]  txBufLen     : Length of the outgoing message in bytes
 * \param[out] rxBuf        : Buffer where incoming message will be placed
 * \param[in]  rxBufLen     : Maximum length of the incoming message in bytes
 * \param[out] actLen       : Actual received length in bits
 * 
 * \return  RFAL_ERR_NONE        : Transceive done with no error
 * \return  RFAL_ERR_WRONG_STATE : RFAL not initialized or mode not set
 * \return  RFAL_ERR_IO          : Internal error
 *****************************************************************************
 */
ReturnCode rfalISO15693TransceiveAnticollisionFrame( uint8_t *txBuf, uint8_t txBufLen, uint8_t *rxBuf, uint8_t rxBufLen, uint16_t *actLen );


/*!
 *****************************************************************************
 * \brief Sends an ISO15693 Anticollision EOF
 * 
 * This sends the Anticollision|Inventory EOF used as a slot marker
 * 
 * \warning rxBuf must be able to contain the payload and CRC
 * 
 * \param[out] rxBuf        : Buffer where incoming message will be placed
 * \param[in]  rxBufLen     : Maximum length of the incoming message in bytes
 * \param[out] actLen       : Actual received length in bits
 * 
 * \return  RFAL_ERR_NONE        : Transceive done with no error
 * \return  RFAL_ERR_WRONG_STATE : RFAL not initialized or mode not set
 * \return  RFAL_ERR_IO          : Internal error
 *****************************************************************************
 */
ReturnCode rfalISO15693TransceiveEOFAnticollision( uint8_t *rxBuf, uint8_t rxBufLen, uint16_t *actLen );


/*!
 *****************************************************************************
 * \brief Sends an ISO15693 EOF
 *
 * This is method sends an ISO15693 (EoF) used for a Write operation
 * 
 * \warning rxBuf must be able to contain the payload and CRC
 * 
 * \param[out] rxBuf        : Buffer where incoming message will be placed
 * \param[in]  rxBufLen     : Maximum length of the incoming message in bytes
 * \param[out] actLen       : Actual received length in bytes
 * 
 * \return  RFAL_ERR_NONE        : Transceive done with no error
 * \return  RFAL_ERR_IO          : Internal error
 *****************************************************************************
 */
ReturnCode rfalISO15693TransceiveEOF( uint8_t *rxBuf, uint16_t rxBufLen, uint16_t *actLen );


/*!
 *****************************************************************************
 * \brief Transceive Blocking Tx 
 *
 * This is method triggers a Transceive and executes it blocking until the 
 * Tx has been completed
 * 
 * \param[in]  txBuf    : Buffer where outgoing message is located
 * \param[in]  txBufLen : Length of the outgoing message in bytes
 * \param[out] rxBuf    : Buffer where incoming message will be placed
 * \param[in]  rxBufLen : Maximum length of the incoming message in bytes
 * \param[out] actLen   : Actual received length in bits
 * \param[in]  flags    : TransceiveFlags indication special handling
 * \param[in]  fwt      : Frame Waiting Time in 1/fc
 * 
 * \return  RFAL_ERR_NONE         : Transceive done with no error
 * \return  RFAL_ERR_BUSY         : Transceive ongoing
 * \return  RFAL_ERR_XXXX         : Error occurred
 * \return  RFAL_ERR_LINK_LOSS    : Link Loss - External Field is Off
 * \return  RFAL_ERR_RF_COLLISION : Collision detected
 * \return  RFAL_ERR_IO           : Internal error
 *****************************************************************************
 */
ReturnCode rfalTransceiveBlockingTx( uint8_t* txBuf, uint16_t txBufLen, uint8_t* rxBuf, uint16_t rxBufLen, uint16_t* actLen, uint32_t flags, uint32_t fwt );

/*!
 *****************************************************************************
 * \brief Transceive Blocking Rx 
 *
 * This is method executes the reception of an ongoing Transceive triggered 
 * before by rfalTransceiveBlockingTx()
 * 
 * \return  RFAL_ERR_NONE         : Transceive done with no error
 * \return  RFAL_ERR_BUSY         : Transceive ongoing
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
ReturnCode rfalTransceiveBlockingRx( void );

/*!
 *****************************************************************************
 * \brief Transceive Blocking 
 *
 * This is method triggers a Transceive and executes it blocking until it 
 * has been completed
 * 
 * \param[in]  txBuf    : Buffer where outgoing message is located
 * \param[in]  txBufLen : Length of the outgoing message in bytes
 * \param[out] rxBuf    : Buffer where incoming message will be placed
 * \param[in]  rxBufLen : Maximum length of the incoming message in bytes
 * \param[out] actLen   : Actual received length in bytes
 * \param[in]  flags    : TransceiveFlags indication special handling
 * \param[in]  fwt      : Frame Waiting Time in 1/fc
 * 
 * \return  RFAL_ERR_NONE         : Transceive done with no error
 * \return  RFAL_ERR_BUSY         : Transceive ongoing
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
ReturnCode rfalTransceiveBlockingTxRx( uint8_t* txBuf, uint16_t txBufLen, uint8_t* rxBuf, uint16_t rxBufLen, uint16_t* actLen, uint32_t flags, uint32_t fwt );



/*****************************************************************************
 *  Listen Mode                                                              *  
 *****************************************************************************/

/*!
 *****************************************************************************
 * \brief Is external Field On
 * 
 * Checks if external field (other peer/device) is on/detected
 * 
 * \return true  External field is On
 * \return false No external field is detected
 * 
 *****************************************************************************
 */
bool rfalIsExtFieldOn( void );


/*!
 *****************************************************************************
 * \brief Listen Mode start
 * 
 * Configures RF Chip to go into listen mode enabling the given technologies
 * 
 * 
 * \param[in]  lmMask:    mask with the enabled/disabled listen modes
 *                        use: RFAL_LM_MASK_NFCA ; RFAL_LM_MASK_NFCB ; 
 *                             RFAL_LM_MASK_NFCF ; RFAL_LM_MASK_ACTIVE_P2P 
 * \param[in]  confA:     pointer to Passive A configurations (NULL if disabled)
 * \param[in]  confB:     pointer to Passive B configurations (NULL if disabled)
 * \param[in]  confF:     pointer to Passive F configurations (NULL if disabled)
 * \param[in]  rxBuf:     buffer to place incoming data
 * \param[in]  rxBufLen:  length in bits of rxBuf
 * \param[in]  rxLen:     pointer to write the data length in bits placed into rxBuf
 *  
 * 
 * \return RFAL_ERR_WRONG_STATE : Not initialized properly
 * \return RFAL_ERR_PARAM       : Invalid parametere mask
 * \return RFAL_ERR_NONE        : Done with no error
 * 
 *****************************************************************************
 */
ReturnCode rfalListenStart( uint32_t lmMask, const rfalLmConfPA *confA, const rfalLmConfPB *confB, const rfalLmConfPF *confF, uint8_t *rxBuf, uint16_t rxBufLen, uint16_t *rxLen );


/*!
 *****************************************************************************
 * \brief Listen Mode start Sleeping
 * 
 * \param[in]  sleepSt  :  sleep state to be set
 * \param[in]  rxBuf    :  buffer to place incoming data
 * \param[in]  rxBufLen :  length in bits of rxBuf
 * \param[in]  rxLen    :  pointer to write the data length in bits placed into rxBuf
 *
 * \return RFAL_ERR_WRONG_STATE : Not initialized properly
 * \return RFAL_ERR_PARAM       : Invalid parameter
 * \return RFAL_ERR_NONE        : Done with no error
 *
 *****************************************************************************
 */
ReturnCode rfalListenSleepStart( rfalLmState sleepSt, uint8_t *rxBuf, uint16_t rxBufLen, uint16_t *rxLen );


/*!
 *****************************************************************************
 * \brief Listen Mode Stop
 * 
 * Disables the listen mode on the RF Chip 
 * 
 * \warning the listen mode will be disabled immediately on the RFchip regardless 
 *          of any ongoing operations like Transceive
 * 
 * \return RFAL_ERR_NONE : Done with no error
 * 
 *****************************************************************************
 */
ReturnCode rfalListenStop( void );


/*!
 *****************************************************************************
 * \brief Listen Mode get state
 *
 * Sets the new state of the Listen Mode and applies the necessary changes 
 * on the RF Chip
 *
 * \param[out]  dataFlag: indicates that Listen Mode has rcvd data and caller
 *                         must process it. The received message is located
 *                         at the rxBuf passed on rfalListenStart().
 *                         rfalListenSetState() will clear this flag
 *                         if NULL output parameter will no be written/returned
 * \param[out]  lastBR:   bit rate detected  of the last initiator request 
 *                         if NULL output parameter will no be written/returned
 * 
 * \return rfalLmState  RFAL_LM_STATE_NOT_INIT : LM not initialized properly
 *                      Any Other              : LM State
 * 
 *****************************************************************************
 */
rfalLmState rfalListenGetState( bool *dataFlag, rfalBitRate *lastBR );


/*!
 *****************************************************************************
 * \brief Listen Mode set state
 *
 * Sets the new state of the Listen Mode and applies the necessary changes 
 * on the RF Chip
 *  
 * \param[in] newSt : New state to go to
 * 
 * \return RFAL_ERR_WRONG_STATE : Not initialized properly
 * \return RFAL_ERR_PARAM       : Invalid parameter
 * \return RFAL_ERR_NONE        : Done with no error
 * 
 *****************************************************************************
 */
ReturnCode rfalListenSetState( rfalLmState newSt );


/*****************************************************************************
 *  Wake-Up Mode                                                             *  
 *****************************************************************************/

/*!
 *****************************************************************************
 * \brief Wake-Up Mode Start
 *
 * Sets the RF Chip in Low Power Wake-Up Mode according to the given 
 * configuration.
 * 
 * \param[in] config       : Generic Wake-Up configuration provided by lower 
 *                            layers. If NULL will automatically configure the 
 *                            Wake-Up mode
 * 
 * \return RFAL_ERR_WRONG_STATE : Not initialized properly
 * \return RFAL_ERR_PARAM       : Invalid parameter
 * \return RFAL_ERR_NONE        : Done with no error
 * 
 *****************************************************************************
 */
ReturnCode rfalWakeUpModeStart( const rfalWakeUpConfig *config );


/*!
 *****************************************************************************
 * \brief Wake-Up has Woke
 *
 * Returns true if the Wake-Up mode is enabled and it has already received 
 * the indication from the RF Chip that the surrounding environment has changed
 * and flagged at least one wake-Up interrupt
 * 
 * \return true  : Wake-Up mode enabled and has received a wake-up IRQ
 * \return false : no Wake-Up IRQ has been received
 * 
 *****************************************************************************
 */
bool rfalWakeUpModeHasWoke( void );


/*!
 *****************************************************************************
 * \brief Wake-Up is Enabled
 *
 * Returns true if the Wake-Up mode is enabled and it has already completed
 *  its starting up sequence.
 *  When the option to obtain a reference value from WU is enabled, the startup
 *  sequence takes longer. Otherwise WU mode is running after rfalWakeUpModeStart
 * 
 * \return true  : Wake-Up mode enabled 
 * \return false : Wake-Up mode not enabled 
 * 
 *****************************************************************************
 */
bool rfalWakeUpModeIsEnabled( void );

/*!
 *****************************************************************************
 * \brief Wake-Up Get Info
 *
 * Returns the current information while Wake-up mode is running
 *
 * \warning The information returned will only be updated in case force is 
 *  enabled, or if an event IRQ has happen. 
 *  Otherwise the info will be filled with zeros.
 * 
 * \param[in]  force       : Force info update info by retrieving it from device
 * \param[out] info        : pointer where WU mode info is to be stored
 *
 * \return RFAL_ERR_WRONG_STATE : Not initialized properly
 * \return RFAL_ERR_PARAM       : Invalid parameter
 * \return RFAL_ERR_NONE        : Done with no error
 *****************************************************************************
 */
ReturnCode rfalWakeUpModeGetInfo( bool force, rfalWakeUpInfo *info );

/*!
 *****************************************************************************
 * \brief Wake-Up Mode Stop
 *
 * Stops the Wake-Up Mode
 * 
 * \return RFAL_ERR_WRONG_STATE : Not initialized properly
 * \return RFAL_ERR_PARAM       : Invalid parameter
 * \return RFAL_ERR_NONE        : Done with no error
 * 
 *****************************************************************************
 */
ReturnCode rfalWakeUpModeStop( void );

/*!
 *****************************************************************************
 * \brief WLC-P WPT Monitor Start
 *
 * After WLC-P reaches its WPT state it starts the monitoring for Impedance
 *  change and WPT Stop sequeence.
 * 
 * \param[in] config       : Generic Wake-Up configuration provided by lower 
 *                            layers. If NULL will automatically configure the 
 *                            WLC-P WPT Phase
 *
 * \warning several parameters held in config will be overwritten by the driver
 *          with the appropriate settings for WPT monitoring.
 * 
 * \return RFAL_ERR_WRONG_STATE : Not initialized properly
 * \return RFAL_ERR_PARAM       : Invalid parameter
 * \return RFAL_ERR_NONE        : Done with no error
 * 
 *****************************************************************************
 */
ReturnCode rfalWlcPWptMonitorStart( const rfalWakeUpConfig *config );


/*!
 *****************************************************************************
 * \brief WLC-P WPT Monitor Start Stop
 *
 * Stops the monitoring of WLC-P WPT Phase
 * 
 * \return RFAL_ERR_WRONG_STATE : Not initialized properly
 * \return RFAL_ERR_PARAM       : Invalid parameter
 * \return RFAL_ERR_NONE        : Done with no error
 * 
 *****************************************************************************
 */
ReturnCode rfalWlcPWptMonitorStop( void );


/*!
 *****************************************************************************
 * \brief WLC-P WPT FOD is Detected
 *
 * Returns true if the WLC-P WPT is monitored and it has already received 
 * the indication from the RF Chip that FOD was detected.
 * 
 * \return true  : WLC-P WPT is monitored and has identified a FOD
 * \return false : no FOD has been identified
 * 
 *****************************************************************************
 */
bool rfalWlcPWptIsFodDetected( void );


/*!
 *****************************************************************************
 * \brief WLC-P WPT Stop is Detected
 *
 * Returns true if the WLC-P WPT is monitored and it has already received 
 * the indication from the RF Chip that a WPT Stop sequence was detected.
 * 
 * \return true  : WLC-P WPT is monitored and has identified a WPT Stop 
 * \return false : no WPT Stop IRQ has been identified
 * 
 *****************************************************************************
 */
bool rfalWlcPWptIsStopDetected( void );


/*!
 *****************************************************************************
 * \brief Low Power Mode Start
 *
 * Sets the RF Chip in Low Power Mode. 
 * In this mode the RF Chip is placed in Low Power Mode, similar to Wake-up 
 * mode but no operation nor period measurement is performed.
 * Mode must be terminated by rfalLowPowerModeStop()
 * 
 * \param[in]  mode             : low power mode to be set
 *
 * \return RFAL_ERR_WRONG_STATE : Not initialized properly
 * \return RFAL_ERR_PARAM       : Invalid parameter
 * \return RFAL_ERR_NONE        : Done with no error
 * 
 *****************************************************************************
 */
ReturnCode rfalLowPowerModeStart( rfalLpMode mode );


/*!
 *****************************************************************************
 * \brief Low Power Mode Stop
 *
 * Stops the Low Power Mode re-enabling the device
 * 
 * \return RFAL_ERR_WRONG_STATE : Not initialized properly
 * \return RFAL_ERR_PARAM       : Invalid parameter
 * \return RFAL_ERR_NONE        : Done with no error
 * 
 *****************************************************************************
 */
ReturnCode rfalLowPowerModeStop( void );


#endif /* RFAL_RF_H */


/**
  * @}
  *
  * @}
  *
  * @}
  */
