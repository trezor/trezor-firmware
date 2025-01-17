
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

/*! \file rfal_crc.c
 *
 *  \author Oliver Regenfelder
 *
 *  \brief CRC calculation implementation
 *
 */

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include "rfal_crc.h"

/*
******************************************************************************
* LOCAL FUNCTION PROTOTYPES
******************************************************************************
*/
static uint16_t rfalCrcUpdateCcitt(uint16_t crcSeed, uint8_t dataByte);

/*
******************************************************************************
* GLOBAL FUNCTIONS
******************************************************************************
*/
uint16_t rfalCrcCalculateCcitt(uint16_t preloadValue, const uint8_t* buf, uint16_t length)
{
    uint16_t crc = preloadValue;
    uint16_t index;

    for (index = 0; index < length; index++)
    {
        crc = rfalCrcUpdateCcitt(crc, buf[index]);
    }

    return crc;
}

/*
******************************************************************************
* LOCAL FUNCTIONS
******************************************************************************
*/
static uint16_t rfalCrcUpdateCcitt(uint16_t crcSeed, uint8_t dataByte)
{
    uint16_t crc = crcSeed;
    uint8_t  dat = dataByte;
    
    dat ^= (uint8_t)(crc & 0xFFU);
    dat ^= (dat << 4);

    crc = (crc >> 8)^(((uint16_t) dat) << 8)^(((uint16_t) dat) << 3)^(((uint16_t) dat) >> 4);

    return crc;
}

