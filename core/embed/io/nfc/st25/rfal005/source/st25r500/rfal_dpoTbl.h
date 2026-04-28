
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2016-2023 STMicroelectronics, all rights reserved
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

/*! \file rfal_dpo.h
 *
 *  \author Gustavo Patricio
 *
 *  \brief RF Dynamic Power Table default values
 */


#ifndef ST25R500_DPO_H
#define ST25R500_DPO_H

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_dpo.h"


/*
 ******************************************************************************
 * GLOBAL DATA TYPES
 ******************************************************************************
 */
 
/*! Default DPO table */
/*  PRQA S 3674 2 # CERT ARR02 - Flexible array will be used with sizeof, on adding elements error-prone manual update of size would be required */
/*  PRQA S 3406 1 # MISRA 8.6 - Externally generated table included by the library */   /*  PRQA S 1514 1 # MISRA 8.9 - Externally generated table included by the library */ /*  PRQA S 1502 1 # MISRA 2.8 - Object usage dependent on feature switch (DPO vs DPO CR) */
const rfalDpoEntry rfalDpoDefaultSettings [] = { 
    { 0x00, 150, 100 },
    { 0x09, 110, 50  },
    { 0x0A, 60,  0   }
};

#endif /* ST25R500_DPO_H */
