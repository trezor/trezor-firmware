/******************************************************************************
 * @attention
 *
 * COPYRIGHT 2018 STMicroelectronics, all rights reserved
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
/*! \file
 *
 *  \author
 *
 *  \brief Platform header file. Defining platform independent functionality.
 *
 */

#ifndef RFAL_PLATFORM_H
#define RFAL_PLATFORM_H

#ifdef __cplusplus
extern "C" {
#endif

/*ReturnCode
******************************************************************************
* INCLUDES
******************************************************************************
*/

#include <trezor_bsp.h>
#include "stm32u5xx_hal.h"

#include <limits.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/systimer.h>

#include "io/nfc.h"
#include "nfc_internal.h"

/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/

// Device type definition
#define ST25R3916B

// GPIO pin used for ST25R SPI SS
#define ST25R_SS_PIN SPI_INSTANCE_3_NSS_PIN

// GPIO port used for ST25R SPI SS port
#define ST25R_SS_PORT SPI_INSTANCE_3_NSS_PORT

// GPIO pin used for ST25R External Interrupt
#define ST25R_INT_PIN NFC_INT_PIN

// GPIO port used for ST25R External Interrupt
#define ST25R_INT_PORT NFC_INT_PORT

/*
******************************************************************************
* GLOBAL MACROS
******************************************************************************
*/
#define platformProtectST25RComm() \
  NVIC_DisableIRQ(EXTI10_IRQn)  // TODO: PRobably should be irq_lock instead //
                                // Protect the unique access to communication
                                // channel (disable IRQ on single thread)

#define platformUnprotectST25RComm() \
  NVIC_EnableIRQ(EXTI10_IRQn)  // TODO: Use macro here /

#define platformProtectST25RIrqStatus()                                        \
  platformProtectST25RComm() /*!< Protect unique access to IRQ status var -    \
                                IRQ disable on single thread environment (MCU) \
                                ; Mutex lock on a multi thread environment */
#define platformUnprotectST25RIrqStatus()                                      \
  platformUnprotectST25RComm() /*!< Unprotect the IRQ status var - IRQ enable  \
                                  on a single thread environment (MCU) ; Mutex \
                                  unlock on a multi thread environment */

// Turns the given GPIO High
#define platformGpioSet(port, pin) HAL_GPIO_WritePin(port, pin, GPIO_PIN_SET)

// Turns the given GPIO Low
#define platformGpioClear(port, pin) \
  HAL_GPIO_WritePin(port, pin, GPIO_PIN_RESET)

// Toggles the given GPIO
#define platformGpioToggle(port, pin) HAL_GPIO_TogglePin(port, pin)

// Checks if the given LED is High
#define platformGpioIsHigh(port, pin) \
  (HAL_GPIO_ReadPin(port, pin) == GPIO_PIN_SET)

// Checks if the given LED is Low
#define platformGpioIsLow(port, pin) (!platformGpioIsHigh(port, pin))

// Create a timer with the given time (ms)
#define platformTimerCreate(t) nfc_create_timer(t)

// Checks if the given timer is expired
#define platformTimerIsExpired(timer) nfc_timer_is_expired(timer)

// Performs a delay for the given time (ms)
#define platformDelay(t) HAL_Delay(t)

// Get System Tick ( 1 tick = 1 ms)
#define platformGetSysTick() HAL_GetTick()

// Asserts whether the given expression is true
#define platformAssert(exp) assert_param(exp)

#define platformErrorHandle()  //_Error_Handler(__FILE__, __LINE__) /*!< Global
                               // error handle\trap                    */

#define platformIrqST25RSetCallback(cb) nfc_ext_irq_set_callback(cb)

// SPI SS\CS: Chip|Slave Select
#define platformSpiSelect() \
  HAL_GPIO_WritePin(ST25R_SS_PORT, ST25R_SS_PIN, GPIO_PIN_RESET)

// SPI SS\CS: Chip|Slave Deselect
#define platformSpiDeselect() \
  HAL_GPIO_WritePin(ST25R_SS_PORT, ST25R_SS_PIN, GPIO_PIN_SET)

// SPI transceive
#define platformSpiTxRx(txBuf, rxBuf, len) \
  nfc_spi_transmit_receive(txBuf, rxBuf, len)

// Log  method
#define platformLog(...)  // logUsart(__VA_ARGS__)

/*
******************************************************************************
* GLOBAL VARIABLES
******************************************************************************
*/
extern uint8_t globalCommProtectCnt; /* Global Protection Counter provided per
                                        platform - instantiated in main.c    */

/*
******************************************************************************
* RFAL FEATURES CONFIGURATION
******************************************************************************
*/

#define RFAL_FEATURE_LISTEN_MODE \
  true /*!< Enable/Disable RFAL support for Listen Mode */
#define RFAL_FEATURE_WAKEUP_MODE \
  true /*!< Enable/Disable RFAL support for the Wake-Up mode */
#define RFAL_FEATURE_LOWPOWER_MODE \
  false /*!< Enable/Disable RFAL support for the Low Power mode */
#define RFAL_FEATURE_NFCA \
  true /*!< Enable/Disable RFAL support for NFC-A (ISO14443A) */
#define RFAL_FEATURE_NFCB \
  true /*!< Enable/Disable RFAL support for NFC-B (ISO14443B) */
#define RFAL_FEATURE_NFCF \
  true /*!< Enable/Disable RFAL support for NFC-F (FeliCa) */
#define RFAL_FEATURE_NFCV \
  true /*!< Enable/Disable RFAL support for NFC-V (ISO15693) */
#define RFAL_FEATURE_T1T \
  true /*!< Enable/Disable RFAL support for T1T (Topaz) */
#define RFAL_FEATURE_T2T true /*!< Enable/Disable RFAL support for T2T */
#define RFAL_FEATURE_T4T true /*!< Enable/Disable RFAL support for T4T */
#define RFAL_FEATURE_ST25TB                        \
  true /*!< Enable/Disable RFAL support for ST25TB \
        */
#define RFAL_FEATURE_ST25xV \
  true /*!< Enable/Disable RFAL support for ST25TV/ST25DV */
#define RFAL_FEATURE_DYNAMIC_ANALOG_CONFIG \
  false /*!< Enable/Disable Analog Configs to be dynamically updated (RAM) */
#define RFAL_FEATURE_DPO \
  true /*!< Enable/Disable RFAL Dynamic Power Output support */
#define RFAL_FEATURE_ISO_DEP \
  true /*!< Enable/Disable RFAL support for ISO-DEP (ISO14443-4) */
#define RFAL_FEATURE_ISO_DEP_POLL                                     \
  true /*!< Enable/Disable RFAL support for Poller mode (PCD) ISO-DEP \
          (ISO14443-4)    */
#define RFAL_FEATURE_ISO_DEP_LISTEN                                    \
  true /*!< Enable/Disable RFAL support for Listen mode (PICC) ISO-DEP \
          (ISO14443-4)   */
#define RFAL_FEATURE_NFC_DEP \
  true /*!< Enable/Disable RFAL support for NFC-DEP (NFCIP1/P2P) */

#define RFAL_FEATURE_ISO_DEP_IBLOCK_MAX_LEN                             \
  256U /*!< ISO-DEP I-Block max length. Please use values as defined by \
          rfalIsoDepFSx */
#define RFAL_FEATURE_NFC_DEP_BLOCK_MAX_LEN \
  254U /*!< NFC-DEP Block/Payload length. Allowed values: 64, 128, 192, 254 */
#define RFAL_FEATURE_NFC_RF_BUF_LEN \
  258U /*!< RF buffer length used by RFAL NFC layer */

#define RFAL_FEATURE_ISO_DEP_APDU_MAX_LEN                                \
  512U /*!< ISO-DEP APDU max length. Please use multiples of I-Block max \
          length       */
#define RFAL_FEATURE_NFC_DEP_PDU_MAX_LEN 512U /*!< NFC-DEP PDU max length. */

/*
******************************************************************************
* RFAL CUSTOM SETTINGS
******************************************************************************
  Custom analog configs are used to cope with Automatic Antenna Tuning (AAT)
  that are optimized differently for each board.
*/
// #define RFAL_ANALOG_CONFIG_CUSTOM                         /*!< Use Custom
// Analog Configs when defined                                    */

#ifndef platformProtectST25RIrqStatus
#define platformProtectST25RIrqStatus() /*!< Protect unique access to IRQ     \
                                           status var - IRQ disable on single \
                                           thread environment (MCU) ; Mutex   \
                                           lock on a multi thread environment \
                                         */
#endif                                  /* platformProtectST25RIrqStatus */

#ifndef platformUnprotectST25RIrqStatus
#define platformUnprotectST25RIrqStatus() /*!< Unprotect the IRQ status var - \
                                             IRQ enable on a single thread    \
                                             environment (MCU) ; Mutex unlock \
                                             on a multi thread environment */
#endif                                    /* platformUnprotectST25RIrqStatus */

#ifndef platformProtectWorker
#define platformProtectWorker() /* Protect RFAL Worker/Task/Process from \
                                   concurrent execution on multi thread  \
                                   platforms   */
#endif                          /* platformProtectWorker */

#ifndef platformUnprotectWorker
#define platformUnprotectWorker() /* Unprotect RFAL Worker/Task/Process from \
                                     concurrent execution on multi thread    \
                                     platforms */
#endif                            /* platformUnprotectWorker */

#ifndef platformIrqST25RPinInitialize
#define platformIrqST25RPinInitialize() /*!< Initializes ST25R IRQ pin */
#endif                                  /* platformIrqST25RPinInitialize */

#ifndef platformIrqST25RSetCallback
#define platformIrqST25RSetCallback(cb) /*!< Sets ST25R ISR callback */
#endif                                  /* platformIrqST25RSetCallback */

#ifndef platformLedsInitialize
#define platformLedsInitialize() /*!< Initializes the pins used as LEDs to \
                                    outputs  */
#endif                           /* platformLedsInitialize */

#ifndef platformLedOff
#define platformLedOff(port, pin) /*!< Turns the given LED Off */
#endif                            /* platformLedOff */

#ifndef platformLedOn
#define platformLedOn(port, pin) /*!< Turns the given LED On */
#endif                           /* platformLedOn */

#ifndef platformLedToggle
#define platformLedToggle(port, pin) /*!< Toggles the given LED */
#endif                               /* platformLedToggle */

#ifndef platformGetSysTick
#define platformGetSysTick() /*!< Get System Tick ( 1 tick = 1 ms) */
#endif                       /* platformGetSysTick */

#ifndef platformTimerDestroy
#define platformTimerDestroy(timer) /*!< Stops and released the given timer */
#endif                              /* platformTimerDestroy */

#ifndef platformLog
#define platformLog(...) /*!< Log method                                    */
#endif                   /* platformLog */

#ifndef platformAssert
#define platformAssert(exp) /*!< Asserts whether the given expression is true \
                             */
#endif                      /* platformAssert */

#ifndef platformErrorHandle
#define platformErrorHandle() /*!< Global error handler or trap */
#endif                        /* platformErrorHandle */

#ifdef __cplusplus
}
#endif

#endif /* RFAL_PLATFORM_H */
