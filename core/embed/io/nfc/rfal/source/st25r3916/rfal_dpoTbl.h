
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
 *      $Revision: $
 *      LANGUAGE:  ISO C99
 */

/*! \file
 *
 *  \author Martin Zechleitner 
 *
 *  \brief RF Dynamic Power Table default values
 */


#ifndef ST25R3916_DPO_H
#define ST25R3916_DPO_H

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
 
#if defined(ST25R3916)

    /*! ST25R3916 Default DPO table */
    /*  PRQA S 3674 2 # CERT ARR02 - Flexible array will be used with sizeof, on adding elements error-prone manual update of size would be required */
    /*  PRQA S 3406 1 # MISRA 8.6 - Externally generated table included by the library */   /*  PRQA S 1514 1 # MISRA 8.9 - Externally generated table included by the library */
const rfalDpoEntry rfalDpoDefaultSettings [] = {
                { 0x00, 255, 200 },
                { 0x01, 210, 150 },
                { 0x02, 160, 100 },
                { 0x03, 110, 50  }
};

#elif defined(ST25R3916B)  /* ST25R3916B has an increased resolution on the driver resistance (d_res) */
    
    /*! ST25R3916B Default DPO table */
    /*  PRQA S 3674 2 # CERT ARR02 - Flexible array will be used with sizeof, on adding elements error-prone manual update of size would be required */
    /*  PRQA S 3406 1 # MISRA 8.6 - Externally generated table included by the library */   /*  PRQA S 1514 1 # MISRA 8.9 - Externally generated table included by the library */
    const rfalDpoEntry rfalDpoDefaultSettings [] = {
                    { 0x00, 255, 200 },
                    { 0x05, 210, 150 },
                    { 0x09, 160, 100 },
                    { 0x0B, 110, 50  }
    };
    
#endif /* ST25R3916 */
 


#endif /* ST25R3916_DPO_H */
