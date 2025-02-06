
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

/*! \file rfal_t2t.h
 *
 *  \author Gustavo Patricio
 *
 *  \brief Provides NFC-A T2T convenience methods and definitions
 *  
 *  This module provides an interface to perform as a NFC-A Reader/Writer
 *  to handle a Type 2 Tag T2T
 *  
 *  
 * \addtogroup RFAL
 * @{
 *
 * \addtogroup RFAL-AL
 * \brief RFAL Abstraction Layer
 * @{
 *
 * \addtogroup T2T
 * \brief RFAL T2T Module
 * @{
 *  
 */


#ifndef RFAL_T2T_H
#define RFAL_T2T_H

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_platform.h"
#include "rfal_utils.h"
#include "rfal_rf.h"

/*
 ******************************************************************************
 * GLOBAL DEFINES
 ******************************************************************************
 */

#define RFAL_T2T_BLOCK_LEN            4U                          /*!< T2T block length           */
#define RFAL_T2T_READ_DATA_LEN        (4U * RFAL_T2T_BLOCK_LEN)   /*!< T2T READ data length       */
#define RFAL_T2T_WRITE_DATA_LEN       RFAL_T2T_BLOCK_LEN          /*!< T2T WRITE data length      */

/*
******************************************************************************
* GLOBAL TYPES
******************************************************************************
*/


/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/

/*! 
 *****************************************************************************
 * \brief  NFC-A T2T Poller Read
 *  
 * This method sends a Read command to a NFC-A T2T Listener device  
 *
 *
 * \param[in]   blockNum         : Number of the block to read
 * \param[out]  rxBuf            : pointer to place the read data
 * \param[in]   rxBufLen         : size of rxBuf (RFAL_T2T_READ_DATA_LEN)
 * \param[out]  rcvLen           : actual received data
 * 
 * \return RFAL_ERR_WRONG_STATE  : RFAL not initialized or mode not set
 * \return RFAL_ERR_PARAM        : Invalid parameter
 * \return RFAL_ERR_PROTO        : Protocol error
 * \return RFAL_ERR_NONE         : No error
 *****************************************************************************
 */
ReturnCode rfalT2TPollerRead( uint8_t blockNum, uint8_t* rxBuf, uint16_t rxBufLen, uint16_t *rcvLen );


/*! 
 *****************************************************************************
 * \brief  NFC-A T2T Poller Write
 *  
 * This method sends a Write command to a NFC-A T2T Listener device  
 *
 *
 * \param[in]  blockNum          : Number of the block to write
 * \param[in]  wrData            : data to be written on the given block
 *                                 size must be of RFAL_T2T_WRITE_DATA_LEN
 * 
 * \return RFAL_ERR_WRONG_STATE  : RFAL not initialized or mode not set
 * \return RFAL_ERR_PARAM        : Invalid parameter
 * \return RFAL_ERR_PROTO        : Protocol error
 * \return RFAL_ERR_NONE         : No error
 *****************************************************************************
 */
ReturnCode rfalT2TPollerWrite( uint8_t blockNum, const uint8_t* wrData );


/*! 
 *****************************************************************************
 * \brief  NFC-A T2T Poller Sector Select 
 *  
 * This method sends a Sector Select commands to a NFC-A T2T Listener device  
 *
 * \param[in]  sectorNum         : Sector Number
 * 
 * \return RFAL_ERR_WRONG_STATE  : RFAL not initialized or mode not set
 * \return RFAL_ERR_PARAM        : Invalid parameter
 * \return RFAL_ERR_PROTO        : Protocol error
 * \return RFAL_ERR_NONE         : No error
 *****************************************************************************
 */
ReturnCode rfalT2TPollerSectorSelect( uint8_t sectorNum );

#endif /* RFAL_T2T_H */

/**
  * @}
  *
  * @}
  *
  * @}
  */
