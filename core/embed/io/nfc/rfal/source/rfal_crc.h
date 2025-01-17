
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

/*! \file rfal_crc.h
 *
 *  \author Ulrich Herrmann
 *
 *  \brief CRC calculation module
 *
 */
/*!
 * 
 */

#ifndef RFAL_CRC_H_
#define RFAL_CRC_H_

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include "rfal_platform.h"

/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/
/*! 
 *****************************************************************************
 *  \brief  Calculate CRC according to CCITT standard.
 *
 *  This function takes \a length bytes from \a buf and calculates the CRC
 *  for this data. The result is returned.
 *  \note This implementation calculates the CRC with LSB first, i.e. all
 *  bytes are "read" from right to left.
 *
 *  \param[in] preloadValue : Initial value of CRC calculation.
 *  \param[in] buf : buffer to calculate the CRC for.
 *  \param[in] length : size of the buffer.
 *
 *  \return 16 bit long crc value.
 *
 *****************************************************************************
 */
extern uint16_t rfalCrcCalculateCcitt(uint16_t preloadValue, const uint8_t* buf, uint16_t length);

#endif /* RFAL_CRC_H_ */

