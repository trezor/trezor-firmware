
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

/*! \file
 *
 *  \author Gustavo Patricio
 *
 *  \brief RFAL Features/Capabilities Definition for ST25R500
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
#define RFAL_SUPPORT_MODE_POLL_ACTIVE_P2P          false         /*!< RFAL Poll AP2P mode support switch    */
#define RFAL_SUPPORT_MODE_LISTEN_NFCA              true          /*!< RFAL Listen NFCA mode support switch  */
#define RFAL_SUPPORT_MODE_LISTEN_NFCB              false         /*!< RFAL Listen NFCB mode support switch  */
#define RFAL_SUPPORT_MODE_LISTEN_NFCF              true          /*!< RFAL Listen NFCF mode support switch  */
#define RFAL_SUPPORT_MODE_LISTEN_ACTIVE_P2P        false         /*!< RFAL Listen AP2P mode support switch  */


/*******************************************************************************/
/*! RFAL supported Card Emulation (CE)        */
#define RFAL_SUPPORT_CE                            ( RFAL_SUPPORT_MODE_LISTEN_NFCA || RFAL_SUPPORT_MODE_LISTEN_NFCB || RFAL_SUPPORT_MODE_LISTEN_NFCF )

/*! RFAL supported Reader/Writer (RW)         */
#define RFAL_SUPPORT_RW                            ( RFAL_SUPPORT_MODE_POLL_NFCA || RFAL_SUPPORT_MODE_POLL_NFCB || RFAL_SUPPORT_MODE_POLL_NFCF || RFAL_SUPPORT_MODE_POLL_NFCV )

/*! RFAL support for Active P2P (AP2P)        */
#define RFAL_SUPPORT_AP2P                          ( RFAL_SUPPORT_MODE_POLL_ACTIVE_P2P || RFAL_SUPPORT_MODE_LISTEN_ACTIVE_P2P )


/*******************************************************************************/
#define RFAL_SUPPORT_BR_RW_26                       true         /*!< RFAL RW   26 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_53                       true         /*!< RFAL RW   53 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_106                      true         /*!< RFAL RW  106 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_212                      true         /*!< RFAL RW  212 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_424                      true         /*!< RFAL RW  424 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_848                      true         /*!< RFAL RW  848 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_1695                     false        /*!< RFAL RW 1695 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_3390                     false        /*!< RFAL RW 3390 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_6780                     false        /*!< RFAL RW 6780 Bit Rate support switch   */
#define RFAL_SUPPORT_BR_RW_13560                    false        /*!< RFAL RW 6780 Bit Rate support switch   */


/*******************************************************************************/
#define RFAL_SUPPORT_BR_AP2P_106                    false        /*!< RFAL AP2P  106 Bit Rate support switch */
#define RFAL_SUPPORT_BR_AP2P_212                    false        /*!< RFAL AP2P  212 Bit Rate support switch */
#define RFAL_SUPPORT_BR_AP2P_424                    false        /*!< RFAL AP2P  424 Bit Rate support switch */
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
    RFAL_WUM_PERIOD_12MS      = 0x00,     /*!< Wake-Up timer ~12.5ms                                      */
    RFAL_WUM_PERIOD_25MS      = 0x01,     /*!< Wake-Up timer ~25ms                                        */
    RFAL_WUM_PERIOD_50MS      = 0x02,     /*!< Wake-Up timer ~50ms                                        */
    RFAL_WUM_PERIOD_75MS      = 0x03,     /*!< Wake-Up timer ~75ms                                        */
    RFAL_WUM_PERIOD_100MS     = 0x04,     /*!< Wake-Up timer ~100ms                                       */
    RFAL_WUM_PERIOD_125MS     = 0x05,     /*!< Wake-Up timer ~125ms                                       */
    RFAL_WUM_PERIOD_150MS     = 0x06,     /*!< Wake-Up timer ~150ms                                       */
    RFAL_WUM_PERIOD_200MS     = 0x07,     /*!< Wake-Up timer ~200ms                                       */
    RFAL_WUM_PERIOD_250MS     = 0x08,     /*!< Wake-Up timer ~250ms                                       */
    RFAL_WUM_PERIOD_300MS     = 0x09,     /*!< Wake-Up timer ~300ms                                       */
    RFAL_WUM_PERIOD_350MS     = 0x0A,     /*!< Wake-Up timer ~350ms                                       */
    RFAL_WUM_PERIOD_400MS     = 0x0B,     /*!< Wake-Up timer ~400ms                                       */
    RFAL_WUM_PERIOD_500MS     = 0x0C,     /*!< Wake-Up timer ~500ms                                       */
    RFAL_WUM_PERIOD_800MS     = 0x0D,     /*!< Wake-Up timer ~800ms                                       */
    RFAL_WUM_PERIOD_1000MS    = 0x0E,     /*!< Wake-Up timer ~1000ms                                      */
    RFAL_WUM_PERIOD_INF       = 0x0F,     /*!< Wake-Up timer Infinite                                     */
} rfalWumPeriod;


/*! RFAL Wake-Up weight of last measurement result for auto- averaging */
typedef enum
{
    RFAL_WUM_AA_WEIGHT_4       = 0x00,    /*!< Wake-Up Auto Average Weight 4                              */
    RFAL_WUM_AA_WEIGHT_8       = 0x01,    /*!< Wake-Up Auto Average Weight 8                              */
    RFAL_WUM_AA_WEIGHT_16      = 0x02,    /*!< Wake-Up Auto Average Weight 16                             */
    RFAL_WUM_AA_WEIGHT_32      = 0x03,    /*!< Wake-Up Auto Average Weight 32                             */
    RFAL_WUM_AA_WEIGHT_50      = 0x04,    /*!< Wake-Up Auto Average Weight 50                             */
    RFAL_WUM_AA_WEIGHT_64      = 0x05,    /*!< Wake-Up Auto Average Weight 64                             */
    RFAL_WUM_AA_WEIGHT_100     = 0x06,    /*!< Wake-Up Auto Average Weight 100                            */
    RFAL_WUM_AA_WEIGHT_128     = 0x07,    /*!< Wake-Up Auto Average Weight 128                            */    
} rfalWumAAWeight;


/*! RFAL Wake-Up mesurement duration */
typedef enum {
    RFAL_WUM_MEAS_DUR_26_10    = 0,       /*!< WU measurement duration: 26.0us (slow) / 10.6us (fast)     */
    RFAL_WUM_MEAS_DUR_30_14    = 1,       /*!< WU measurement duration: 29.5us (slow) / 14.2us (fast)     */
    RFAL_WUM_MEAS_DUR_34_19    = 2,       /*!< WU measurement duration: 34.2us (slow) / 18.9us (fast)     */
    RFAL_WUM_MEAS_DUR_44_28    = 3,       /*!< WU measurement duration: 43.7us (slow) / 28.3us (fast)     */
}rfalWumMeasDuration;


/*! RFAL Wake-Up mesurement filter */
typedef enum {
    RFAL_WUM_MEAS_FIL_SLOW    = false,    /*!< Wake-Up measurement slow filter                            */
    RFAL_WUM_MEAS_FIL_FAST    = true,     /*!< Wake-up measurement fast filter                            */
}rfalWumMeasFilter;



/*! RFAL Wake-Up trigger tresholds for threshold bitmask config */
enum {
    RFAL_WUM_TRE_ABOVE    = (1U<<2),      /*!< Wake-up trigger threshold: above upper limit               */
    RFAL_WUM_TRE_BETWEEN  = (1U<<1),      /*!< Wake-up trigger threshold: between upper and lower limit   */
    RFAL_WUM_TRE_BELOW    = (1U<<0),      /*!< Wake-up trigger threshold: below lower limit               */
};


/*! RFAL Wake-Up channel configuration */
typedef struct {
    bool             enabled;             /*!< Inductive Amplitude measurement enabled                    */
    uint8_t          delta;               /*!< Delta between the reference and measurement to wake-up     */
    uint8_t          reference;           /*!< Reference to be used;RFAL_WUM_REFERENCE_AUTO sets it auto  */
    uint8_t          threshold;           /*!< Wake-Up trigger treshold bitmask                           */
    bool             aaInclMeas;          /*!< When AutoAvg is enabled, include IRQ measurement           */
    rfalWumAAWeight  aaWeight;            /*!< When AutoAvg is enabled, last measure weight               */
}rfalWumMeasChannel;


/*! RFAL Wake-Up Mode configuration */
typedef struct
{
    rfalWumPeriod        period;          /*!< Wake-Up Timer period;how often measurement(s) is performed */
    bool                 irqTout;         /*!< IRQ due to Wake-up timer and measurement event (wutme)     */
    bool                 autoAvg;         /*!< Use the HW Auto Averaging feature on the enabled channel(s)*/
    bool                 skipCal;         /*!< Do not preform calibration starting WU mode                */
    bool                 skipReCal;       /*!< Do not preform recalibration during WU mode                */
    bool                 delCal;          /*!< Delay calibration step starting WU mode                    */
    bool                 delRef;          /*!< Delay reference step starting WU mode                      */
    rfalWumMeasDuration  measDur;         /*!< Wake-up measurement duration config                        */
    rfalWumMeasFilter    measFil;         /*!< Wake-up measurement filter config                          */
    
    rfalWumMeasChannel   I;               /*!< I channel Configuration                                    */
    rfalWumMeasChannel   Q;               /*!< Q channel Configuration                                    */
} rfalWakeUpConfig;


/*! RFAL Wake-Up Mode information */
typedef struct
{
    bool                 irqWut;          /*!< Wake-Up timer and measurement event IRQ (cleared upon read)*/
    uint8_t              status;          /*!< Wake-Up status                                             */

    struct{
        uint8_t          lastMeas;        /*!< Value of the latest measurement                            */
        uint8_t          reference;       /*!< Current reference value                                    */
        uint8_t          calib;           /*!< Current calibration value                                  */
        bool             irqWu;           /*!< Amplitude WU IRQ received (cleared upon read)              */
    }I;                                   /*!< I channel Information                                      */

    struct{
        uint8_t          lastMeas;        /*!< Value of the latest measurement                            */
        uint8_t          reference;       /*!< Current reference value                                    */
        uint8_t          calib;           /*!< Current calibration value                                  */
        bool             irqWu;           /*!< Phase WU IRQ received (cleared upon read)                  */
    }Q;                                   /*!< Q channel Information                                      */
    
    struct{
        bool             irqWptFod;       /*!< WLC WPT FOD detected                                       */
        bool             irqWptStop;      /*!< WLC WPT Stop condition detected                            */
    }WLC;                                 /*!< WLC Wireless Power Transfer phase                          */
} rfalWakeUpInfo;


#endif /* RFAL_FEATURES_H */
