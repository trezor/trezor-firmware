/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2024 STMicroelectronics, all rights reserved
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
 *      $Revision: $
 *      LANGUAGE:  ISO C99
 */

/*! \file st25r500_dpocr.h
 *
 *  \author Ulrich Herrmann
 *
 *  \brief Dynamic Power Output adjustment via Current Regulation
 *
 *  This module provides an interface to perform the power adjustment dynamically
 *  using a current regulation loop with a target value (ST25R500 only)
 *
 *
 * \addtogroup RFAL
 * @{
 *
 * \addtogroup RFAL-HAL
 * \brief RFAL Hardware Abstraction Layer
 * @{
 *
 * \addtogroup ST25R500
 * \brief RFAL ST25R500 Driver
 * @{
 *
 * \addtogroup ST25R500_Driver
 * \brief RFAL ST25R500 Driver
 * @{
 *
 */


#ifndef ST25R500_DPOCR_H
#define ST25R500_DPOCR_H

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_platform.h"
#include "rfal_utils.h"

/*
 ******************************************************************************
 * C LINKAGE GUARD
 ******************************************************************************
 */
#ifdef __cplusplus
extern "C" {
#endif /* __cplusplus */

/*
 ******************************************************************************
 * GLOBAL DEFINES
 ******************************************************************************
 */

#define ST25R500_DPOCR_MAX_ENTRIES   10U                    /*!< Max number of table entries - in this version different from AC levels*/

/*
******************************************************************************
* GLOBAL TYPES
******************************************************************************
*/

/*! DPO config entry struct, to have link into AC, similar to rfal_dpo levels */

typedef struct {
    uint16_t           zloadLim;                            /*!< If current zload < zloadLim then this entry is applicable                */
    int8_t             correction;                          /*!< Typically negative value, is used to reduce the target in close distance */
    uint8_t            acEntry;                             /*!< AC DPO entry: 0-3, defaults to 0 if no entry is found                    */
}st25r500DpocrEntry;

/*! DPO config struct */
typedef struct {
    bool               enabled;                             /*!< DPO Enabled state                                                                           */
    uint16_t           target;                              /*!< Target value - electric current as per I_VDD_DR measurement                                 */
    uint8_t            minRege;                             /*!< Min regulator which will be selected                                                        */
    uint8_t            maxRege;                             /*!< Max regulator which will be selected                                                        */
    uint8_t            measRege;                            /*!< Rege setting to be used for the current measurement                                         */
    uint8_t            measDres;                            /*!< Dres setting to be used for the current measurement, may be decreased if below 100mA        */
    uint16_t           threshold;                           /*!< Sensitivity value for RFI (I/Q) which triggers re-evaluation of current.                    */
    st25r500DpocrEntry levels[ST25R500_DPOCR_MAX_ENTRIES];  /*!< Table sorted by decreasing zloadLim. The correction of the last fitting entry will be used  */
    uint8_t            numEntries;                          /*!< Number of entries to be used in table                                                       */
}st25r500DpocrConfig;


/*! DPO information struct */
typedef struct {
    uint8_t            currentEntryIdx;                     /*!< Current DPO table Index                     */
    uint8_t            currentAcEntry;                      /*!< Current AC DPO entry: 0-3                   */
    uint16_t           currentElecCurrent;                  /*!< Current DPO measured electrical current     */
    uint8_t            currentRege;                         /*!< Current ST25R500 rege setting               */
    uint8_t            currentDres;                         /*!< Current ST25R500 dres setting               */
    uint16_t           currentTarget;                       /*!< Currently used target including corrections */
    uint16_t           currentZload;                        /*!< Current Zload (from current, rege, dres)    */
} st25r500DpocrInfo;


/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/


/*!
 *****************************************************************************
 * \brief  Initialize dynamic power
 *
 * Initialize the R500 current regulation DPO
 *
 * \param[in] config : pointer to a user provided config or NULL to use the default one
 *
 * \return RFAL_ERR_NONE        : No error
 * \return RFAL_ERR_WRONG_STATE : If the current state is valid for DPO operation
 *****************************************************************************
 */
ReturnCode st25r500DpocrInitialize( const st25r500DpocrConfig *config );


/*!
 *****************************************************************************
 * \brief  Dynamic power adjust
 *
 * This function measures the current output and adjusts the power accordingly to
 * the dynamic power table.
 * This method | The adjustment shall be performed when the device
 * is already emiting RF field.
 *
 * \return RFAL_ERR_NONE        : No error
 * \return RFAL_ERR_PARAM       : If DPO is not enabled
 * \return RFAL_ERR_DISABLED    : If cannot enable DPO
 * \return RFAL_ERR_WRONG_STATE : If DPO is not initialized
 *
 *****************************************************************************
 */
ReturnCode st25r500DpocrAdjust( void );


/*!
 *****************************************************************************
 * \brief  Dynamic power set enabled state
 *
 * Set state to enable or disable the Dynamic power adjustment
 *
 * \param[in] enable : new active state
 *
 *****************************************************************************
 */
void st25r500DpocrSetEnabled( bool enable );


/*!
 *****************************************************************************
 * \brief  Write dynamic power config
 *
 * Write the dynamic power config
 *
 * \param[in]  config       : location of config to be loaded
 *
 * \return RFAL_ERR_NONE    : No error
 * \return RFAL_ERR_PARAM   : If config is invalid
 * \return RFAL_ERR_NOMEM   : If the given config table exceeds the max size
 * \return RFAL_ERR_WRONG_STATE : If DPO is not initialized
 *
 *****************************************************************************
 */
ReturnCode st25r500DpocrConfigWrite( const st25r500DpocrConfig* config );


/*!
 *****************************************************************************
 * \brief  Dynamic power config Read
 *
 * Read the dynamic power config
 *
 * \param[out]   config     : location to the config to place the current config
 *
 * \return RFAL_ERR_NONE    : No error
 * \return RFAL_ERR_PARAM   : If config is invalid
 * \return RFAL_ERR_WRONG_STATE : If DPO is not initialized
 *
 *****************************************************************************
 */
ReturnCode st25r500DpocrConfigRead( st25r500DpocrConfig* config );


/*!
 *****************************************************************************
 * \brief  Request DPO adjust
 *
 *  Flags the DPO module to perform the adjustment on the next round, even
 *  if no change has been perceived from previous measurement|state
 *
 *****************************************************************************
 */
void st25r500DpocrReqAdj( void );


/*!
 *****************************************************************************
 * \brief  Get Dynamic power information
 *
 * Get the DPO information|status
 *
 * \param[out] info       : pointer where to store the DPO info
 *
 * \return RFAL_ERR_NONE  : No error
 * \return RFAL_ERR_PARAM : Invalid parameter
 * \return RFAL_ERR_WRONG_STATE : If DPO is not initialized
 *
 *****************************************************************************
 */
ReturnCode st25r500DpocrGetInfo( st25r500DpocrInfo* info );


#ifdef __cplusplus
}
#endif /* __cplusplus */

#endif /* ST25R500_DPOCR_H */

/**
  * @}
  *
  * @}
  *
  * @}
  *
  * @}
  */
