
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2019 STMicroelectronics, all rights reserved
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
 *      Revision:
 *      LANGUAGE:  ISO C99
 */

/*! \file rfal_cd.h
 *
 *  \author
 *
 *  \brief Implementation of a Card Detection Algorithm
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
 * \addtogroup CD
 * \brief RFAL Card Detection
 * @{
 *
 */

#ifndef RFAL_CD_H
#define RFAL_CD_H

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

/*
 ******************************************************************************
 * GLOBAL MACROS
 ******************************************************************************
 */

/*
******************************************************************************
* GLOBAL TYPES
******************************************************************************
*/

/*! Card Detection NFC technology type                                                                         */
typedef enum
{
    RFAL_CD_TECH_NONE       = 0x00,  /*!< No NFC Technology       */
    RFAL_CD_TECH_NFCA       = 0x01,  /*!< NFC Technology NFCB     */
    RFAL_CD_TECH_NFCB       = 0x02,  /*!< NFC Technology NFCB     */
    RFAL_CD_TECH_NFCF       = 0x04,  /*!< NFC Technology NFCF     */
    RFAL_CD_TECH_NFCV       = 0x08,  /*!< NFC Technology NFCV     */
    RFAL_CD_TECH_OTHER      = 0x10   /*!< NFC Technology OTHER    */
}rfalCdTech;


/*! Card Detection result|outcome type                                                                         */
typedef enum
{
    RFAL_CD_NOT_FOUND          = 0,  /*<! No NFC device found                                                  */
    RFAL_CD_SINGLE_DEV         = 1,  /*<! An NFC card was found                                                */
    RFAL_CD_MULTIPLE_DEV       = 2,  /*<! Multiple NFC devices found                                           */
    RFAL_CD_MULTIPLE_TECH      = 3,  /*<! Multiple NFC technologies observed in a single RF carrier            */
    RFAL_CD_CARD_TECH          = 4,  /*<! A card-exclusive NFC technology found                                */
    RFAL_CD_SINGLE_MULTI_TECH  = 5,  /*<! A single NFC device which supports multiple technologies found       */
    RFAL_CD_SINGLE_P2P         = 6,  /*<! A single NFC device which supports NFC-DEP|P2P found                 */
    RFAL_CD_SINGLE_HB          = 7,  /*<! A single NFC device where heartbeat was detected                     */
    RFAL_CD_UNKOWN             = 8   /*<! Unable to complete the Card Detection due to unknow|unexpected event */
}
rfalCdDetType;


/*! Card Detection result|outcome                                                                              */
typedef struct
{
    bool          detected;         /*!< Card detected flag                                                    */
    rfalCdDetType detType;          /*!< Card detection type                                                   */
}
rfalCdRes;


/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/

/*!
 *****************************************************************************
 * \brief  Detect Card
 *
 * This function checks if a passive NFC card is present in the vicinity
 *
 * \param[out]  result             : Pointer to detection result|outcome
 *                            
 * \return  RFAL_ERR_PARAM         : Invalid parameters
 * \return  RFAL_ERR_WRONG_STATE   : Incorrect state for this operation
 * \return  RFAL_ERR_NONE          : Detection excuted with no error
 * \return  RFAL_ERR_RF_COLLISION  : RF carrier collision detected
 * \return  RFAL_ERR_XXXX          : Error occurred
 
 *
 *****************************************************************************
 */
ReturnCode rfalCdDetectCard( rfalCdRes *result );


/*!
 *****************************************************************************
 * \brief  Start Card Detection
 *
 * This function starts the detection for a passive NFC card is present 
 * in the vicinity
 *
 * \param[out]  result             : Pointer to detection result|outcome
 *
 * \return  RFAL_ERR_PARAM         : Invalid parameters
 * \return  RFAL_ERR_WRONG_STATE   : Incorrect state for this operation
 * \return  RFAL_ERR_NONE          : Detection will be executed
 *
 *****************************************************************************
 */
ReturnCode rfalCdStartDetectCard( rfalCdRes *result );


/*!
 *****************************************************************************
 * \brief  Get Card Detection Status
 *
 * This function gets the status of the card detection
 *
 * \return  RFAL_ERR_PARAM         : Invalid parameters
 * \return  RFAL_ERR_WRONG_STATE   : Incorrect state for this operation
 * \return  RFAL_ERR_NONE          : Detection excuted with no error
 * \return  RFAL_ERR_RF_COLLISION  : RF carrier collision detected
 * \return  RFAL_ERR_XXXX          : Error occurred
 *
 *****************************************************************************
 */
ReturnCode rfalCdGetDetectCardStatus( void );


#endif /* RFAL_CD_H */

/**
  * @}
  *
  * @}
  *
  * @}
  */
