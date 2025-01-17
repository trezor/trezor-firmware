
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

/*! \file
 *
 *  \author Gustavo Patricio 
 *
 *  \brief RFAL Features/Capabilities Definition for ST25R3916
 */


#ifndef RFAL_FEATURES_H
#define RFAL_FEATURES_H

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include "rfal_platform.h"

/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/

#define RFAL_SUPPORT_MODE_POLL_NFCA                true          /*!< RFAL Poll NFCA mode support switch    */
#define RFAL_SUPPORT_MODE_POLL_NFCB                true          /*!< RFAL Poll NFCB mode support switch    */
#define RFAL_SUPPORT_MODE_POLL_NFCF                true          /*!< RFAL Poll NFCF mode support switch    */
#define RFAL_SUPPORT_MODE_POLL_NFCV                true          /*!< RFAL Poll NFCV mode support switch    */
#define RFAL_SUPPORT_MODE_POLL_ACTIVE_P2P          true          /*!< RFAL Poll AP2P mode support switch    */
#define RFAL_SUPPORT_MODE_LISTEN_NFCA              true          /*!< RFAL Listen NFCA mode support switch  */
#define RFAL_SUPPORT_MODE_LISTEN_NFCB              false         /*!< RFAL Listen NFCB mode support switch  */
#define RFAL_SUPPORT_MODE_LISTEN_NFCF              true          /*!< RFAL Listen NFCF mode support switch  */
#define RFAL_SUPPORT_MODE_LISTEN_ACTIVE_P2P        true          /*!< RFAL Listen AP2P mode support switch  */


/*******************************************************************************/
/*! RFAL supported Card Emulation (CE)        */
#define RFAL_SUPPORT_CE                            ( RFAL_SUPPORT_MODE_LISTEN_NFCA || RFAL_SUPPORT_MODE_LISTEN_NFCB || RFAL_SUPPORT_MODE_LISTEN_NFCF )

/*! RFAL supported Reader/Writer (RW)         */
#define RFAL_SUPPORT_RW                            ( RFAL_SUPPORT_MODE_POLL_NFCA || RFAL_SUPPORT_MODE_POLL_NFCB || RFAL_SUPPORT_MODE_POLL_NFCF || RFAL_SUPPORT_MODE_POLL_NFCV )

/*! RFAL support for Active P2P (AP2P)        */
#define RFAL_SUPPORT_AP2P                          ( RFAL_SUPPORT_MODE_POLL_ACTIVE_P2P || RFAL_SUPPORT_MODE_LISTEN_ACTIVE_P2P )


/*******************************************************************************/
#define RFAL_SUPPORT_BR_RW_106                      true         /*!< RFAL RW  106 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_212                      true         /*!< RFAL RW  212 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_424                      true         /*!< RFAL RW  424 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_848                      true         /*!< RFAL RW  848 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_1695                     false        /*!< RFAL RW 1695 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_3390                     false        /*!< RFAL RW 3390 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_6780                     false        /*!< RFAL RW 6780 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_13560                    false        /*!< RFAL RW 6780 Bit Rate support switch   */


/*******************************************************************************/
#define RFAL_SUPPORT_BR_AP2P_106                    true         /*!< RFAL AP2P  106 Bit Rate support switch */
#define RFAL_SUPPORT_BR_AP2P_212                    true         /*!< RFAL AP2P  212 Bit Rate support switch */
#define RFAL_SUPPORT_BR_AP2P_424                    true         /*!< RFAL AP2P  424 Bit Rate support switch */
#define RFAL_SUPPORT_BR_AP2P_848                    false        /*!< RFAL AP2P  848 Bit Rate support switch */


/*******************************************************************************/
#define RFAL_SUPPORT_BR_CE_A_106                    true         /*!< RFAL CE A 106 Bit Rate support switch  */
#define RFAL_SUPPORT_BR_CE_A_212                    false        /*!< RFAL CE A 212 Bit Rate support switch  */
#define RFAL_SUPPORT_BR_CE_A_424                    false        /*!< RFAL CE A 424 Bit Rate support switch  */
#define RFAL_SUPPORT_BR_CE_A_848                    false        /*!< RFAL CE A 848 Bit Rate support switch  */


/*******************************************************************************/
#define RFAL_SUPPORT_BR_CE_B_106                    false        /*!< RFAL CE B 106 Bit Rate support switch  */
#define RFAL_SUPPORT_BR_CE_B_212                    false        /*!< RFAL CE B 212 Bit Rate support switch  */
#define RFAL_SUPPORT_BR_CE_B_424                    false        /*!< RFAL CE B 424 Bit Rate support switch  */
#define RFAL_SUPPORT_BR_CE_B_848                    false        /*!< RFAL CE B 848 Bit Rate support switch  */


/*******************************************************************************/
#define RFAL_SUPPORT_BR_CE_F_212                    true         /*!< RFAL CE F 212 Bit Rate support switch  */
#define RFAL_SUPPORT_BR_CE_F_424                    true         /*!< RFAL CE F 424 Bit Rate support switch  */



/*
******************************************************************************
* DEVICE SPECIFIC FEATURE DEFINITIONS
******************************************************************************
*/

/*! RFAL Wake-Up Period/Timer */
typedef enum 
{
    RFAL_WUM_PERIOD_10MS      = 0x00,     /*!< Wake-Up timer 10ms                                         */
    RFAL_WUM_PERIOD_20MS      = 0x01,     /*!< Wake-Up timer 20ms                                         */
    RFAL_WUM_PERIOD_30MS      = 0x02,     /*!< Wake-Up timer 30ms                                         */
    RFAL_WUM_PERIOD_40MS      = 0x03,     /*!< Wake-Up timer 40ms                                         */
    RFAL_WUM_PERIOD_50MS      = 0x04,     /*!< Wake-Up timer 50ms                                         */
    RFAL_WUM_PERIOD_60MS      = 0x05,     /*!< Wake-Up timer 60ms                                         */
    RFAL_WUM_PERIOD_70MS      = 0x06,     /*!< Wake-Up timer 70ms                                         */
    RFAL_WUM_PERIOD_80MS      = 0x07,     /*!< Wake-Up timer 80ms                                         */
    RFAL_WUM_PERIOD_100MS     = 0x10,     /*!< Wake-Up timer 100ms                                        */
    RFAL_WUM_PERIOD_200MS     = 0x11,     /*!< Wake-Up timer 200ms                                        */
    RFAL_WUM_PERIOD_300MS     = 0x12,     /*!< Wake-Up timer 300ms                                        */
    RFAL_WUM_PERIOD_400MS     = 0x13,     /*!< Wake-Up timer 400ms                                        */
    RFAL_WUM_PERIOD_500MS     = 0x14,     /*!< Wake-Up timer 500ms                                        */
    RFAL_WUM_PERIOD_600MS     = 0x15,     /*!< Wake-Up timer 600ms                                        */
    RFAL_WUM_PERIOD_700MS     = 0x16,     /*!< Wake-Up timer 700ms                                        */
    RFAL_WUM_PERIOD_800MS     = 0x17,     /*!< Wake-Up timer 800ms                                        */
} rfalWumPeriod;                                                                                          
                                                                                                          
                                                                                                          
/*! RFAL Wake-Up Period/Timer */                                                                          
typedef enum                                                                                              
{                                                                                                         
    RFAL_WUM_AA_WEIGHT_4       = 0x00,    /*!< Wake-Up Auto Average Weight 4                              */
    RFAL_WUM_AA_WEIGHT_8       = 0x01,    /*!< Wake-Up Auto Average Weight 8                              */
    RFAL_WUM_AA_WEIGHT_16      = 0x02,    /*!< Wake-Up Auto Average Weight 16                             */
    RFAL_WUM_AA_WEIGHT_32      = 0x03,    /*!< Wake-Up Auto Average Weight 32                             */
} rfalWumAAWeight;


/*! RFAL Wake-Up Mode configuration */
typedef struct 
{
    rfalWumPeriod        period;          /*!< Wake-Up Timer period;how often measurement(s) is performed */
    bool                 irqTout;         /*!< IRQ at every timeout will refresh the measurement(s)       */
    bool                 swTagDetect;     /*!< Use SW Tag Detection instead of HW Wake-Up mode            */
    
    struct{                               
        bool             enabled;         /*!< Reference from WU mode enabled                             */
        rfalWumPeriod    refDelay;        /*!< Obtain reference from WU after delay time                  */
    }refWU;                               /*!< Reference obtained from PD|WU mode                         */
                                          
    struct{                               
        bool             enabled;         /*!< Inductive Amplitude measurement enabled                    */
        uint8_t          delta;           /*!< Delta between the reference and measurement to wake-up     */
        uint8_t          fracDelta;       /*!< Fractional part of the delta [0;3] 0.25 steps (SW TD only) */
        uint16_t         reference;       /*!< Reference to be used;RFAL_WUM_REFERENCE_AUTO sets it auto  */
        bool             autoAvg;         /*!< Use the HW Auto Averaging feature                          */
        bool             aaInclMeas;      /*!< When AutoAvg is enabled, include IRQ measurement           */
        rfalWumAAWeight  aaWeight;        /*!< When AutoAvg is enabled, last measure weight               */
    }indAmp;                              /*!< Inductive Amplitude Configuration                          */
    struct{                                                                                               
        bool             enabled;         /*!< Inductive Phase measurement enabled                        */
        uint8_t          delta;           /*!< Delta between the reference and measurement to wake-up     */
        uint8_t          fracDelta;       /*!< Fractional part of the delta [0;3] 0.25 steps (SW TD only) */
        uint16_t         reference;       /*!< Reference to be used;RFAL_WUM_REFERENCE_AUTO sets it auto  */
        bool             autoAvg;         /*!< Use the HW Auto Averaging feature                          */
        bool             aaInclMeas;      /*!< When AutoAvg is enabled, include IRQ measurement           */
        rfalWumAAWeight  aaWeight;        /*!< When AutoAvg is enabled, last measure weight               */
    }indPha;                              /*!< Inductive Phase Configuration                              */
    struct{                                                                                               
        bool             enabled;         /*!< Capacitive measurement enabled                             */
        uint8_t          delta;           /*!< Delta between the reference and measurement to wake-up     */
        uint16_t         reference;       /*!< Reference to be used;RFAL_WUM_REFERENCE_AUTO sets it auto  */
        bool             autoAvg;         /*!< Use the HW Auto Averaging feature                          */
        bool             aaInclMeas;      /*!< When AutoAvg is enabled, include IRQ measurement           */
        rfalWumAAWeight  aaWeight;        /*!< When AutoAvg is enabled, last measure weight               */
    }cap;                                 /*!< Capacitive Configuration                                   */
} rfalWakeUpConfig;


/*! RFAL Wake-Up Mode information */
typedef struct 
{
    bool                 irqWut;          /*!< Wake-Up Timer IRQ received (cleared upon read)             */   
    struct{
        uint8_t          lastMeas;        /*!< Value of the latest measurement                            */
        uint16_t         reference;       /*!< Current reference value (TD format if SW TD enabled)       */
        bool             irqWu;           /*!< Amplitude WU IRQ received (cleared upon read)              */
    }indAmp;                              /*!< Inductive Amplitude                                        */
    struct{                                                                                               
        uint8_t          lastMeas;        /*!< Value of the latest measurement                            */
        uint16_t         reference;       /*!< Current reference value (TD format if SW TD enabled)       */
        bool             irqWu;           /*!< Phase WU IRQ received (cleared upon read)                  */
    }indPha;                              /*!< Inductive Phase                                            */
    struct{                                                                                               
        uint8_t          lastMeas;        /*!< Value of the latest measurement                            */
        uint16_t         reference;       /*!< Current reference value                                    */
        bool             irqWu;           /*!< Capacitive WU IRQ received (cleared upon read)             */
    }cap;                                 /*!< Capacitive                                                 */
} rfalWakeUpInfo;

#endif /* RFAL_FEATURES_H */
