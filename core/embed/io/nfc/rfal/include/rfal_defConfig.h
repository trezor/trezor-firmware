
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
 *      PROJECT:   ST25R 
 *      Revision:
 *      LANGUAGE:  ISO C99
 */

/*! \file rfal_defConfig.h
 *
 *  \author Gustavo Patricio 
 *
 *  \brief RF Abstraction Layer (RFAL) default Config file
 *  
 *  This file contains a base/default configuration for the
 *  RFAL library. 
 *  Users can and shall define their on configuration acording 
 *  to their speficic system needs on rfal_platform.h.
 *
 * \addtogroup RFAL
 * @{
 *  
 */

#ifndef RFAL_CONFIG_H
#define RFAL_CONFIG_H

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include "rfal_features.h"


/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/


/*
******************************************************************************
* RFAL FEATURES DEFAULT CONFIGURATION
******************************************************************************
*/
#ifndef RFAL_FEATURE_LISTEN_MODE
    #if RFAL_SUPPORT_CE || RFAL_SUPPORT_MODE_LISTEN_ACTIVE_P2P
        #define RFAL_FEATURE_LISTEN_MODE            true       /*!< Enable RFAL support for Listen Mode                               */
    #endif /* SUPPORT LISTEN_MODE */
#endif /* RFAL_FEATURE_LISTEN_MODE */

        
#ifndef RFAL_FEATURE_WAKEUP_MODE
    #define RFAL_FEATURE_WAKEUP_MODE                true       /*!< Enable RFAL support for the Wake-Up mode                          */
#endif /* RFAL_FEATURE_WAKEUP_MODE */


#ifndef RFAL_FEATURE_LOWPOWER_MODE
    #define RFAL_FEATURE_LOWPOWER_MODE              false      /*!< RFAL support for the Low Power mode, Disabled by default          */
#endif /* RFAL_FEATURE_LOWPOWER_MODE */


#ifndef RFAL_FEATURE_NFCA
    #if RFAL_SUPPORT_MODE_POLL_NFCA
        #define RFAL_FEATURE_NFCA                   true       /*!< Enable RFAL support for NFC-A (ISO14443A)                         */
    #endif /* RFAL_SUPPORT_MODE_POLL_NFCA */
#endif /* RFAL_FEATURE_NFCA */


#ifndef RFAL_FEATURE_T1T
    #if RFAL_SUPPORT_MODE_POLL_NFCA
        #define RFAL_FEATURE_T1T                    true       /*!< Enable RFAL support for T1T (Topaz)                               */
    #endif /* RFAL_SUPPORT_MODE_POLL_NFCA */
#endif /* RFAL_FEATURE_T1T */

#ifndef RFAL_FEATURE_T2T
    #if RFAL_SUPPORT_MODE_POLL_NFCA
        #define RFAL_FEATURE_T2T                    true       /*!< Enable RFAL support for T2T                                       */
    #endif /* RFAL_SUPPORT_MODE_POLL_NFCA */
#endif /* RFAL_FEATURE_T2T */

#ifndef RFAL_FEATURE_T4T
    #if RFAL_SUPPORT_MODE_POLL_NFCA
        #define RFAL_FEATURE_T4T                    true       /*!< Enable RFAL support for T4T                                       */
    #endif /* RFAL_SUPPORT_MODE_POLL_NFCA */
#endif /* RFAL_FEATURE_T2T */


#ifndef RFAL_FEATURE_NFCB
    #if RFAL_SUPPORT_MODE_POLL_NFCB
        #define RFAL_FEATURE_NFCB                   true       /*!< Enable RFAL support for NFC-B (ISO14443B)                         */
    #endif /* RFAL_SUPPORT_MODE_POLL_NFCB */
#endif /* RFAL_FEATURE_NFCB */


#ifndef RFAL_FEATURE_ST25TB
    #if RFAL_SUPPORT_MODE_POLL_NFCB
        #define RFAL_FEATURE_ST25TB                 true       /*!< Enable RFAL support for ST25TB                                    */
    #endif /* RFAL_SUPPORT_MODE_POLL_NFCB */
#endif /* RFAL_FEATURE_ST25TB */


#ifndef RFAL_FEATURE_NFCF
    #if RFAL_SUPPORT_MODE_POLL_NFCF
        #define RFAL_FEATURE_NFCF                   true       /*!< Enable RFAL support for NFC-F (FeliCa)                            */
    #endif /* RFAL_SUPPORT_MODE_POLL_NFCF */
#endif /* RFAL_FEATURE_NFCF */


#ifndef RFAL_FEATURE_NFCV
    #if RFAL_SUPPORT_MODE_POLL_NFCV
        #define RFAL_FEATURE_NFCV                   true       /*!< Enable RFAL support for NFC-V (ISO15693)                          */
    #endif /* RFAL_SUPPORT_MODE_POLL_NFCV */
#endif /* RFAL_FEATURE_NFCV */


#ifndef RFAL_FEATURE_ISO_DEP
    #if RFAL_SUPPORT_MODE_POLL_NFCA || RFAL_SUPPORT_MODE_POLL_NFCB || RFAL_SUPPORT_CE
        #define RFAL_FEATURE_ISO_DEP                true       /*!< Enable RFAL support for ISO-DEP (ISO14443-4)                      */
    #endif /* RFAL_SUPPORT_MODE_ */
#endif /* RFAL_FEATURE_ISO_DEP */


#ifndef RFAL_FEATURE_ISO_DEP_POLL
    #if RFAL_SUPPORT_MODE_POLL_NFCA || RFAL_SUPPORT_MODE_POLL_NFCB
        #define RFAL_FEATURE_ISO_DEP_POLL           true       /*!< Enable RFAL support for Poller mode (PCD) ISO-DEP (ISO14443-4)    */
    #endif /* RFAL_SUPPORT_MODE_ */
#endif /* RFAL_FEATURE_ISO_DEP */


#ifndef RFAL_FEATURE_ISO_DEP_LISTEN
    #if RFAL_SUPPORT_CE
        #define RFAL_FEATURE_ISO_DEP_LISTEN         true       /*!< Enable RFAL support for Listen mode (PICC) ISO-DEP (ISO14443-4)   */
    #endif /* RFAL_SUPPORT_MODE_ */
#endif /* RFAL_FEATURE_ISO_DEP */


#ifndef RFAL_FEATURE_ISO_DEP_IBLOCK_MAX_LEN
    #if RFAL_FEATURE_ISO_DEP
        #define RFAL_FEATURE_ISO_DEP_IBLOCK_MAX_LEN 256U       /*!< ISO-DEP I-Block max length. Please use values as defined by rfalIsoDepFSx */
    #endif /* RFAL_FEATURE_ISO_DEP */
#endif /* RFAL_FEATURE_ISO_DEP_IBLOCK_MAX_LEN */


#ifndef RFAL_FEATURE_ISO_DEP_APDU_MAX_LEN
    #if RFAL_FEATURE_ISO_DEP
        #define RFAL_FEATURE_ISO_DEP_APDU_MAX_LEN   512U       /*!< ISO-DEP APDU max length.                                          */
    #endif /* RFAL_FEATURE_ISO_DEP */
#endif /* RFAL_FEATURE_ISO_DEP_APDU_MAX_LEN */


#ifndef RFAL_FEATURE_NFC_DEP
    #if RFAL_SUPPORT_MODE_POLL_NFCA && RFAL_SUPPORT_MODE_POLL_NFCF
        #define RFAL_FEATURE_NFC_DEP                true       /*!< Enable RFAL support for NFC-DEP (NFCIP1/P2P)                      */
    #endif /* RFAL_SUPPORT_MODE_POLL_NFCA/F */
#endif /* RFAL_FEATURE_NFC_DEP */


#ifndef RFAL_FEATURE_NFC_DEP_BLOCK_MAX_LEN
    #if RFAL_FEATURE_NFC_DEP
        #define RFAL_FEATURE_NFC_DEP_BLOCK_MAX_LEN  254U       /*!< NFC-DEP Block/Payload length. Allowed values: 64, 128, 192, 254   */
    #endif /* RFAL_FEATURE_NFC_DEP */
#endif /* RFAL_FEATURE_NFC_DEP_BLOCK_MAX_LEN */


#ifndef RFAL_FEATURE_NFC_DEP_PDU_MAX_LEN
    #if RFAL_FEATURE_NFC_DEP
        #define RFAL_FEATURE_NFC_DEP_PDU_MAX_LEN    512U       /*!< NFC-DEP PDU max length.                                           */
    #endif /* RFAL_FEATURE_NFC_DEP */
#endif /* RFAL_FEATURE_NFC_DEP_PDU_MAX_LEN */


#ifndef RFAL_FEATURE_NFC_RF_BUF_LEN
    #define RFAL_FEATURE_NFC_RF_BUF_LEN             258U       /*!< RF buffer length used by RFAL NFC layer                           */
#endif /* RFAL_FEATURE_NFC_RF_BUF_LEN */


#ifndef RFAL_FEATURE_ST25xV
    #define RFAL_FEATURE_ST25xV                     false      /*!< ST25xV Module configuration missing. Disabled by default          */
#endif                                                         
                                                               
                                                               
#ifndef RFAL_FEATURE_DYNAMIC_ANALOG_CONFIG                     
    #define RFAL_FEATURE_DYNAMIC_ANALOG_CONFIG      false      /*!< Dynamic Analog Configs configuration missing. Disabled by default */
#endif                                                         
                                                               
                                                               
#ifndef RFAL_FEATURE_DPO                                       
    #define RFAL_FEATURE_DPO                        false      /*!< Dynamic Power Module configuration missing. Disabled by default   */
#endif                                                         
                                                               
#ifndef RFAL_FEATURE_DLMA                                      
    #define RFAL_FEATURE_DLMA                       false      /*!< Dynamic LMA Module configuration missing. Disabled by default     */
#endif



 
 /*
 ******************************************************************************
 * RFAL OPTIONAL MACROS
 ******************************************************************************
 */

#ifndef platformProtectST25RIrqStatus
    #define platformProtectST25RIrqStatus()            /*!< Protect unique access to IRQ status var - IRQ disable on single thread environment (MCU) ; Mutex lock on a multi thread environment */
#endif /* platformProtectST25RIrqStatus */

#ifndef platformUnprotectST25RIrqStatus
    #define platformUnprotectST25RIrqStatus()          /*!< Unprotect the IRQ status var - IRQ enable on a single thread environment (MCU) ; Mutex unlock on a multi thread environment         */
#endif /* platformUnprotectST25RIrqStatus */

#ifndef platformProtectWorker
    #define platformProtectWorker()                    /*!< Protect RFAL Worker/Task/Process from concurrent execution on multi thread platforms   */
#endif /* platformProtectWorker */

#ifndef platformUnprotectWorker
    #define platformUnprotectWorker()                  /*!< Unprotect RFAL Worker/Task/Process from concurrent execution on multi thread platforms */
#endif /* platformUnprotectWorker */

#ifndef platformIrqST25RPinInitialize
    #define platformIrqST25RPinInitialize()            /*!< Initializes ST25R IRQ pin                     */
#endif /* platformIrqST25RPinInitialize */                                                                

#ifndef platformIrqST25RSetCallback                                                                       
    #define platformIrqST25RSetCallback( cb )          /*!< Sets ST25R ISR callback                       */
#endif /* platformIrqST25RSetCallback */                                                                  

#ifndef platformLedsInitialize                                                                            
    #define platformLedsInitialize()                   /*!< Initializes the pins used as LEDs to outputs  */
#endif /* platformLedsInitialize */                                                                       

#ifndef platformLedOff                                                                                    
    #define platformLedOff( port, pin )                /*!< Turns the given LED Off                       */
#endif /* platformLedOff */                                                                               

#ifndef platformLedOn                                                                                     
    #define platformLedOn( port, pin )                 /*!< Turns the given LED On                        */
#endif /* platformLedOn */                                                                                
                                                                                                          
#ifndef platformLedToggle                                                                                 
    #define platformLedToggle( port, pin )             /*!< Toggles the given LED                         */
#endif /* platformLedToggle */                                                                            


#ifndef platformGetSysTick                                                                                
    #define platformGetSysTick()                       /*!< Get System Tick ( 1 tick = 1 ms)              */
#endif /* platformGetSysTick */                                                                           

#ifndef platformTimerDestroy                                                                              
    #define platformTimerDestroy( timer )              /*!< Stops and released the given timer            */
#endif /* platformTimerDestroy */                                                                         

#ifndef platformLog                                                                                       
    #define platformLog(...)                           /*!< Log method                                    */
#endif /* platformLog */

#ifndef platformAssert                                                                             
    #define platformAssert( exp )                      /*!< Asserts whether the given expression is true */
#endif /* platformAssert */

#ifndef platformErrorHandle                                                                             
    #define platformErrorHandle()                      /*!< Global error handler or trap                 */
#endif /* platformErrorHandle */


#ifdef RFAL_USE_I2C

    #ifndef platformSpiTxRx                                                                             
        #define platformSpiTxRx( txBuf, rxBuf, len )   /*!< SPI transceive                               */
    #endif /* platformSpiTxRx */                                                                         
                                                                                                         
#else /* RFAL_USE_I2C */                                                                                 
                                                                                                         
    #ifndef platformI2CTx                                                                                
        #define platformI2CTx( txBuf, len, last, txOnly ) /*!< I2C Transmit                              */
    #endif /* platformI2CTx */                                                                           
                                                                                                         
    #ifndef platformI2CRx                                                                                
        #define platformI2CRx( txBuf, len )            /*!< I2C Receive                                  */
    #endif /* platformI2CRx */                                                                           
                                                                                                         
    #ifndef platformI2CStart                                                                              
        #define platformI2CStart()                     /*!< I2C Start condition                          */
    #endif /* platformI2CStart */                                                                        
                                                                                                         
    #ifndef platformI2CStop                                                                              
        #define platformI2CStop()                      /*!< I2C Stop condition                           */
    #endif /* platformI2CStop */                                                                         
                                                                                                         
    #ifndef platformI2CRepeatStart                                                                       
        #define platformI2CRepeatStart()               /*!< I2C Repeat Start                             */
    #endif /* platformI2CRepeatStart */                                                                  
                                                                                                         
    #ifndef platformI2CSlaveAddrWR                                                                       
        #define platformI2CSlaveAddrWR(add)            /*!< I2C Slave address for Write operation        */
    #endif /* platformI2CSlaveAddrWR */                                                                  
                                                                                                         
    #ifndef platformI2CSlaveAddrRD                                                                       
        #define platformI2CSlaveAddrRD(add)            /*!< I2C Slave address for Read operation         */
    #endif /* platformI2CSlaveAddrRD */
    
#endif /* RFAL_USE_I2C */

#endif  /* RFAL_CONFIG_H */


/**
  * @}
  *
  */

