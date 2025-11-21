
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

/*! \file rfal_dlmaTbl.h
 *
 *  \author Gustavo Patricio
 *
 *  \brief RF Dynamic LMA Table default values
 */


#ifndef ST25R3916_DLMA_TBL_H
#define ST25R3916_DLMA_TBL_H

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_dlma.h"


/*
 ******************************************************************************
 * GLOBAL DATA TYPES
 ******************************************************************************
 */
 
/*! Default DLMA table */
/*  PRQA S 3674 2 # CERT ARR02 - Flexible array will be used with sizeof, on adding elements error-prone manual update of size would be required */
/*  PRQA S 3406 1 # MISRA 8.6 - Externally generated table included by the library */   /*  PRQA S 1514 1 # MISRA 8.9 - Externally generated table included by the library */
const rfalDlmaEntry rfalDlmaDefaultSettings [] = {
    {0x0F, 0x01,  39,   0},
    {0x0F, 0x03,  69,  40},
    {0x0F, 0x04,  79,  70},
    {0x0F, 0x05, 255,  80}
};

#endif /* ST25R3916_DLMA_TBL_H */
