
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
 *      PROJECT:   ST25R firmware
 *      $Revision: $
 *      LANGUAGE:  ISO C99
 */

/*! \file rfal_dlma.h
 *
 *  \brief Dynamic load modulation adjustment
 *  
 *  This module provides an interface to perform the load modulation dynamically 
 *  
 *  
 * \addtogroup RFAL
 * @{
 *
 * \addtogroup RFAL-HAL
 * \brief RFAL Hardware Abstraction Layer
 * @{
 *
 * \addtogroup DLMA
 * \brief RFAL Dynamic Load modulation
 * @{
 * 
 */


#ifndef RFAL_DLMA_H
#define RFAL_DLMA_H

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_platform.h"
#include "rfal_utils.h"

/*
 ******************************************************************************
 * GLOBAL DEFINES
 ******************************************************************************
 */

#define RFAL_DLMA_TABLE_MAX_ENTRIES         4U                                                          /*!< Max DLMA entries       */
#define RFAL_DLMA_TABLE_PARAM_LEN           sizeof(rfalDlmaEntry)                                       /*!< DLMA Parameter length  */
#define RFAL_DLMA_TABLE_SIZE_MAX            (RFAL_DLMA_TABLE_MAX_ENTRIES * RFAL_DLMA_TABLE_PARAM_LEN)   /*!< Max DLMA table size    */

/*
******************************************************************************
* GLOBAL TYPES
******************************************************************************
*/

/*! Function pointer to methode doing the reference measurement */
typedef ReturnCode (*rfalDlmaMeasureFunc)(uint8_t* res);

/*! Function pointer to the Adjustment method */
typedef ReturnCode (*rfalDlmaAdjustFunc)(uint8_t mod, uint8_t unmod);


/*! DLMA table entry struct */
typedef struct 
{
    uint8_t unmodRes;                       /*!< RFO resistance in Passive Listen Mode: Unmodulated state */
    uint8_t modRes;                         /*!< RFO resistance in Passive Listen Mode: Modulated state   */
    uint8_t inc;                            /*!< Threshold for incrementing                               */
    uint8_t dec;                            /*!< Threshold for decrementing                               */
}rfalDlmaEntry;


/*! DLMA information struct */
typedef struct 
{
    bool                enabled;            /*!< Enabled state                                            */
    uint8_t             tableEntry;         /*!< Current entry used                                       */
    uint8_t             tableEntries;       /*!< Number of entries used                                   */
    uint8_t             refMeasurement;     /*!< Last measurement used to adjust                          */
    rfalDlmaAdjustFunc  adjustCallback;     /*!< Pointer to the adjust callback                           */
    rfalDlmaMeasureFunc measureCallback;    /*!< Pointer to the measure callback                          */
} rfalDlmaInfo;


/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/


/*! 
 *****************************************************************************
 * \brief  Initialize dynamic power table
 *  
 *  This function sets the internal dynamic power table to the default 
 *  values stored in rfal_DlmaTbl.h
 *  
 *****************************************************************************
 */
void rfalDlmaInitialize( void );


/*! 
 *****************************************************************************
 * \brief  Set the measurement methode
 *  
 * This function sets the measurement method used for reference measurement.
 * Based on the measurement the power will then be adjusted
 *  
 * \param[in]  pFunc: callback of measurement function
 *
 *****************************************************************************
 */
void rfalDlmaSetMeasureCallback( rfalDlmaMeasureFunc pFunc );


/*! 
 *****************************************************************************
 * \brief  Set the measurement methode
 *  
 * This function sets the adjust method.
 *  
 * \param[in]  pFunc: callback of adjust function
 *
 *****************************************************************************
 */
void rfalDlmaSetAdjustCallback( rfalDlmaAdjustFunc pFunc );


/*! 
 *****************************************************************************
 * \brief  Dynamic LMA table write
 *  
 * Load the dynamic power table  
 *
 * \param[in]  powerTbl        :  location of power Table to be loaded
 * \param[in]  powerTblEntries : number of entries of the power Table to be loaded
 * 
 * \return RFAL_ERR_NONE    : No error
 * \return RFAL_ERR_PARAM   : If configTbl is invalid
 * \return RFAL_ERR_NOMEM   : If the given Table is bigger exceeds the max size
 *****************************************************************************
 */
ReturnCode rfalDlmaTableWrite( const rfalDlmaEntry* powerTbl, uint8_t powerTblEntries );


/*! 
 *****************************************************************************
 * \brief  Dynamic LMA table Read
 *  
 * Read the dynamic power table  
 *
 * \param[out]   tblBuf        : location to the rfalDlmaEntry[] to place the Table 
 * \param[in]    tblBufEntries : number of entries available in tblBuf to place the power Table
 * \param[out]   tableEntries  : returned number of entries actually written into tblBuf
 * 
 * \return RFAL_ERR_NONE        : No error
 * \return RFAL_ERR_WRONG_STATE : If configTbl is invalid 
 * \return RFAL_ERR_PARAM       : If parameters are invalid
 *****************************************************************************
 */
ReturnCode rfalDlmaTableRead( rfalDlmaEntry* tblBuf, uint8_t tblBufEntries, uint8_t* tableEntries );


/*! 
 *****************************************************************************
 * \brief  Dynamic LMA adjust
 *  
 * It measures the current output and adjusts the power accordingly to 
 * the dynamic power table  
 * 
 * \return RFAL_ERR_NONE        : No error
 * \return RFAL_ERR_PARAM       : If configTbl is invalid or parameters are invalid
 * \return RFAL_ERR_WRONG_STATE : If the current state is valid for DLMA Adjustment
 *****************************************************************************
 */
ReturnCode rfalDlmaAdjust( void );


/*! 
 *****************************************************************************
 * \brief  Dynamic LMA set enabled state
 *  
 * \param[in] enable : new active state
 *
 * Set state to enable or disable the Dynamic LMA adjustment 
 * 
 *****************************************************************************
 */
void rfalDlmaSetEnabled( bool enable );


/*! 
 *****************************************************************************
 * \brief  Get the Dynamic LMA enabled state
 *  
 * Get state of the Dynamic power adjustment 
 * 
 * \return true   : DLMA is enabled
 * \return false  : DLMA is disabled
 *****************************************************************************
 */
bool rfalDlmaIsEnabled( void );


/*!
 *****************************************************************************
 * \brief  Get DLMA information
 *  
 * Get the DLMA information|status
 * 
 * \param[out] info  : DLMA information
 *
 * \return RFAL_ERR_PARAM : Invalid parameters
 * \return RFAL_ERR_NONE  : No Error
 *****************************************************************************
 */
ReturnCode rfalDlmaGetInfo( rfalDlmaInfo* info );


#endif /* RFAL_DLMA_H */

/**
  * @}
  *
  * @}
  *
  * @}
  */
