
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2022 STMicroelectronics, all rights reserved
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
 *      PROJECT:   ST25R200 firmware
 *      Revision: 
 *      LANGUAGE:  ISO C99
 */

/*! \file rfal_analogConfig.h
 *
 *  \author Gustavo Patricio
 *
 *  \brief ST25R200 Analog Configuration Settings
 *  
 */

#ifndef ST25R200_ANALOGCONFIG_H
#define ST25R200_ANALOGCONFIG_H

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_analogConfig.h"
#include "st25r200_com.h"


/*
 ******************************************************************************
 * DEFINES
 ******************************************************************************
 */

/*
 ******************************************************************************
 * GLOBAL MACROS
 ******************************************************************************
 */

/*! Macro for Configuration Setting with only one register-mask-value set: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1] */
#define MODE_ENTRY_1_REG(MODE, R0, M0, V0)              \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU), 1, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0)

/*! Macro for Configuration Setting with only two register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1] */
#define MODE_ENTRY_2_REG(MODE, R0, M0, V0, R1, M1, V1)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU), 2, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1)

/*! Macro for Configuration Setting with only three register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_3_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU), 3, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2)

/*! Macro for Configuration Setting with only four register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_4_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU), 4, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3)

/*! Macro for Configuration Setting with only five register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_5_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU), 5, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4)

/*! Macro for Configuration Setting with only six register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_6_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU), 6, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5)
                                 
/*! Macro for Configuration Setting with only seven register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_7_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU), 7, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6)

/*! Macro for Configuration Setting with only eight register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_8_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU), 8, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7)

/*! Macro for Configuration Setting with only nine register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_9_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU), 9, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8)

/*! Macro for Configuration Setting with only ten register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_10_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),10, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9)

/*! Macro for Configuration Setting with eleven register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_11_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),11, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10)

/*! Macro for Configuration Setting with twelve register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_12_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10, R11, M11, V11)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),12, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10) \
                                 , (uint8_t)((uint16_t)(R11) >> 8U), (uint8_t)((R11) & 0xFFU), (uint8_t)(M11), (uint8_t)(V11)

/*! Macro for Configuration Setting with thirteen register-mask-value sets: 
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_13_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10, R11, M11, V11, R12, M12, V12)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),13, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10) \
                                 , (uint8_t)((uint16_t)(R11) >> 8U), (uint8_t)((R11) & 0xFFU), (uint8_t)(M11), (uint8_t)(V11) \
                                 , (uint8_t)((uint16_t)(R12) >> 8U), (uint8_t)((R12) & 0xFFU), (uint8_t)(M12), (uint8_t)(V12)

/*! Macro for Configuration Setting with fourteen register-mask-value sets:
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_14_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10, R11, M11, V11, R12, M12, V12, R13, M13, V13)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),14, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10) \
                                 , (uint8_t)((uint16_t)(R11) >> 8U), (uint8_t)((R11) & 0xFFU), (uint8_t)(M11), (uint8_t)(V11) \
                                 , (uint8_t)((uint16_t)(R12) >> 8U), (uint8_t)((R12) & 0xFFU), (uint8_t)(M12), (uint8_t)(V12) \
                                 , (uint8_t)((uint16_t)(R13) >> 8U), (uint8_t)((R13) & 0xFFU), (uint8_t)(M13), (uint8_t)(V13)
                                 
/*! Macro for Configuration Setting with fifteen register-mask-value sets:
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_15_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10, R11, M11, V11, R12, M12, V12, R13, M13, V13, R14, M14, V14)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),15, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10) \
                                 , (uint8_t)((uint16_t)(R11) >> 8U), (uint8_t)((R11) & 0xFFU), (uint8_t)(M11), (uint8_t)(V11) \
                                 , (uint8_t)((uint16_t)(R12) >> 8U), (uint8_t)((R12) & 0xFFU), (uint8_t)(M12), (uint8_t)(V12) \
                                 , (uint8_t)((uint16_t)(R13) >> 8U), (uint8_t)((R13) & 0xFFU), (uint8_t)(M13), (uint8_t)(V13) \
                                 , (uint8_t)((uint16_t)(R14) >> 8U), (uint8_t)((R14) & 0xFFU), (uint8_t)(M14), (uint8_t)(V14)

/*! Macro for Configuration Setting with sixteen register-mask-value sets:
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_16_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10, R11, M11, V11, R12, M12, V12, R13, M13, V13, R14, M14, V14, R15, M15, V15)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),16, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10) \
                                 , (uint8_t)((uint16_t)(R11) >> 8U), (uint8_t)((R11) & 0xFFU), (uint8_t)(M11), (uint8_t)(V11) \
                                 , (uint8_t)((uint16_t)(R12) >> 8U), (uint8_t)((R12) & 0xFFU), (uint8_t)(M12), (uint8_t)(V12) \
                                 , (uint8_t)((uint16_t)(R13) >> 8U), (uint8_t)((R13) & 0xFFU), (uint8_t)(M13), (uint8_t)(V13) \
                                 , (uint8_t)((uint16_t)(R14) >> 8U), (uint8_t)((R14) & 0xFFU), (uint8_t)(M14), (uint8_t)(V14) \
                                 , (uint8_t)((uint16_t)(R15) >> 8U), (uint8_t)((R15) & 0xFFU), (uint8_t)(M15), (uint8_t)(V15)

/*! Macro for Configuration Setting with seventeen register-mask-value sets:
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_17_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10, R11, M11, V11, R12, M12, V12, R13, M13, V13, R14, M14, V14, R15, M15, V15, R16, M16, V16)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),17, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10) \
                                 , (uint8_t)((uint16_t)(R11) >> 8U), (uint8_t)((R11) & 0xFFU), (uint8_t)(M11), (uint8_t)(V11) \
                                 , (uint8_t)((uint16_t)(R12) >> 8U), (uint8_t)((R12) & 0xFFU), (uint8_t)(M12), (uint8_t)(V12) \
                                 , (uint8_t)((uint16_t)(R13) >> 8U), (uint8_t)((R13) & 0xFFU), (uint8_t)(M13), (uint8_t)(V13) \
                                 , (uint8_t)((uint16_t)(R14) >> 8U), (uint8_t)((R14) & 0xFFU), (uint8_t)(M14), (uint8_t)(V14) \
                                 , (uint8_t)((uint16_t)(R15) >> 8U), (uint8_t)((R15) & 0xFFU), (uint8_t)(M15), (uint8_t)(V15) \
                                 , (uint8_t)((uint16_t)(R16) >> 8U), (uint8_t)((R16) & 0xFFU), (uint8_t)(M16), (uint8_t)(V16)

/*! Macro for Configuration Setting with seventeen register-mask-value sets:
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_18_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10, R11, M11, V11, R12, M12, V12, R13, M13, V13, R14, M14, V14, R15, M15, V15, R16, M16, V16, R17, M17, V17)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),18, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10) \
                                 , (uint8_t)((uint16_t)(R11) >> 8U), (uint8_t)((R11) & 0xFFU), (uint8_t)(M11), (uint8_t)(V11) \
                                 , (uint8_t)((uint16_t)(R12) >> 8U), (uint8_t)((R12) & 0xFFU), (uint8_t)(M12), (uint8_t)(V12) \
                                 , (uint8_t)((uint16_t)(R13) >> 8U), (uint8_t)((R13) & 0xFFU), (uint8_t)(M13), (uint8_t)(V13) \
                                 , (uint8_t)((uint16_t)(R14) >> 8U), (uint8_t)((R14) & 0xFFU), (uint8_t)(M14), (uint8_t)(V14) \
                                 , (uint8_t)((uint16_t)(R15) >> 8U), (uint8_t)((R15) & 0xFFU), (uint8_t)(M15), (uint8_t)(V15) \
                                 , (uint8_t)((uint16_t)(R16) >> 8U), (uint8_t)((R16) & 0xFFU), (uint8_t)(M16), (uint8_t)(V16) \
                                 , (uint8_t)((uint16_t)(R17) >> 8U), (uint8_t)((R17) & 0xFFU), (uint8_t)(M17), (uint8_t)(V17) 
                                 
/*! Macro for Configuration Setting with seventeen register-mask-value sets:
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_19_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10, R11, M11, V11, R12, M12, V12, R13, M13, V13, R14, M14, V14, R15, M15, V15, R16, M16, V16, R17, M17, V17, R18, M18, V18)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),19, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10) \
                                 , (uint8_t)((uint16_t)(R11) >> 8U), (uint8_t)((R11) & 0xFFU), (uint8_t)(M11), (uint8_t)(V11) \
                                 , (uint8_t)((uint16_t)(R12) >> 8U), (uint8_t)((R12) & 0xFFU), (uint8_t)(M12), (uint8_t)(V12) \
                                 , (uint8_t)((uint16_t)(R13) >> 8U), (uint8_t)((R13) & 0xFFU), (uint8_t)(M13), (uint8_t)(V13) \
                                 , (uint8_t)((uint16_t)(R14) >> 8U), (uint8_t)((R14) & 0xFFU), (uint8_t)(M14), (uint8_t)(V14) \
                                 , (uint8_t)((uint16_t)(R15) >> 8U), (uint8_t)((R15) & 0xFFU), (uint8_t)(M15), (uint8_t)(V15) \
                                 , (uint8_t)((uint16_t)(R16) >> 8U), (uint8_t)((R16) & 0xFFU), (uint8_t)(M16), (uint8_t)(V16) \
                                 , (uint8_t)((uint16_t)(R17) >> 8U), (uint8_t)((R17) & 0xFFU), (uint8_t)(M17), (uint8_t)(V17) \
                                 , (uint8_t)((uint16_t)(R18) >> 8U), (uint8_t)((R18) & 0xFFU), (uint8_t)(M18), (uint8_t)(V18) 
                                 
/*! Macro for Configuration Setting with seventeen register-mask-value sets:
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_20_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10, R11, M11, V11, R12, M12, V12, R13, M13, V13, R14, M14, V14, R15, M15, V15, R16, M16, V16, R17, M17, V17, R18, M18, V18, R19, M19, V19)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),20, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10) \
                                 , (uint8_t)((uint16_t)(R11) >> 8U), (uint8_t)((R11) & 0xFFU), (uint8_t)(M11), (uint8_t)(V11) \
                                 , (uint8_t)((uint16_t)(R12) >> 8U), (uint8_t)((R12) & 0xFFU), (uint8_t)(M12), (uint8_t)(V12) \
                                 , (uint8_t)((uint16_t)(R13) >> 8U), (uint8_t)((R13) & 0xFFU), (uint8_t)(M13), (uint8_t)(V13) \
                                 , (uint8_t)((uint16_t)(R14) >> 8U), (uint8_t)((R14) & 0xFFU), (uint8_t)(M14), (uint8_t)(V14) \
                                 , (uint8_t)((uint16_t)(R15) >> 8U), (uint8_t)((R15) & 0xFFU), (uint8_t)(M15), (uint8_t)(V15) \
                                 , (uint8_t)((uint16_t)(R16) >> 8U), (uint8_t)((R16) & 0xFFU), (uint8_t)(M16), (uint8_t)(V16) \
                                 , (uint8_t)((uint16_t)(R17) >> 8U), (uint8_t)((R17) & 0xFFU), (uint8_t)(M17), (uint8_t)(V17) \
                                 , (uint8_t)((uint16_t)(R18) >> 8U), (uint8_t)((R18) & 0xFFU), (uint8_t)(M18), (uint8_t)(V18) \
                                 , (uint8_t)((uint16_t)(R19) >> 8U), (uint8_t)((R19) & 0xFFU), (uint8_t)(M19), (uint8_t)(V19)
                                 
/*! Macro for Configuration Setting with seventeen register-mask-value sets:
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_21_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10, R11, M11, V11, R12, M12, V12, R13, M13, V13, R14, M14, V14, R15, M15, V15, R16, M16, V16, R17, M17, V17, R18, M18, V18, R19, M19, V19, R20, M20, V20)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),21, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10) \
                                 , (uint8_t)((uint16_t)(R11) >> 8U), (uint8_t)((R11) & 0xFFU), (uint8_t)(M11), (uint8_t)(V11) \
                                 , (uint8_t)((uint16_t)(R12) >> 8U), (uint8_t)((R12) & 0xFFU), (uint8_t)(M12), (uint8_t)(V12) \
                                 , (uint8_t)((uint16_t)(R13) >> 8U), (uint8_t)((R13) & 0xFFU), (uint8_t)(M13), (uint8_t)(V13) \
                                 , (uint8_t)((uint16_t)(R14) >> 8U), (uint8_t)((R14) & 0xFFU), (uint8_t)(M14), (uint8_t)(V14) \
                                 , (uint8_t)((uint16_t)(R15) >> 8U), (uint8_t)((R15) & 0xFFU), (uint8_t)(M15), (uint8_t)(V15) \
                                 , (uint8_t)((uint16_t)(R16) >> 8U), (uint8_t)((R16) & 0xFFU), (uint8_t)(M16), (uint8_t)(V16) \
                                 , (uint8_t)((uint16_t)(R17) >> 8U), (uint8_t)((R17) & 0xFFU), (uint8_t)(M17), (uint8_t)(V17) \
                                 , (uint8_t)((uint16_t)(R18) >> 8U), (uint8_t)((R18) & 0xFFU), (uint8_t)(M18), (uint8_t)(V18) \
                                 , (uint8_t)((uint16_t)(R19) >> 8U), (uint8_t)((R19) & 0xFFU), (uint8_t)(M19), (uint8_t)(V19) \
                                 , (uint8_t)((uint16_t)(R20) >> 8U), (uint8_t)((R20) & 0xFFU), (uint8_t)(M20), (uint8_t)(V20) 
                                 
/*! Macro for Configuration Setting with seventeen register-mask-value sets:
 *  - Configuration ID[2], Number of Register sets to follow[1], Register[2], Mask[1], Value[1], Register[2], Mask[1], Value[1], Register[2]... */
#define MODE_ENTRY_22_REG(MODE, R0, M0, V0, R1, M1, V1, R2, M2, V2, R3, M3, V3, R4, M4, V4, R5, M5, V5, R6, M6, V6, R7, M7, V7, R8, M8, V8, R9, M9, V9, R10, M10, V10, R11, M11, V11, R12, M12, V12, R13, M13, V13, R14, M14, V14, R15, M15, V15, R16, M16, V16, R17, M17, V17, R18, M18, V18, R19, M19, V19, R20, M20, V20, R21, M21, V21)  \
    (uint8_t)((uint16_t)(MODE) >> 8U), (uint8_t)((MODE) & 0xFFU),22, (uint8_t)((uint16_t)(R0) >> 8U), (uint8_t)((R0) & 0xFFU), (uint8_t)(M0), (uint8_t)(V0) \
                                 , (uint8_t)((uint16_t)(R1) >> 8U), (uint8_t)((R1) & 0xFFU), (uint8_t)(M1), (uint8_t)(V1) \
                                 , (uint8_t)((uint16_t)(R2) >> 8U), (uint8_t)((R2) & 0xFFU), (uint8_t)(M2), (uint8_t)(V2) \
                                 , (uint8_t)((uint16_t)(R3) >> 8U), (uint8_t)((R3) & 0xFFU), (uint8_t)(M3), (uint8_t)(V3) \
                                 , (uint8_t)((uint16_t)(R4) >> 8U), (uint8_t)((R4) & 0xFFU), (uint8_t)(M4), (uint8_t)(V4) \
                                 , (uint8_t)((uint16_t)(R5) >> 8U), (uint8_t)((R5) & 0xFFU), (uint8_t)(M5), (uint8_t)(V5) \
                                 , (uint8_t)((uint16_t)(R6) >> 8U), (uint8_t)((R6) & 0xFFU), (uint8_t)(M6), (uint8_t)(V6) \
                                 , (uint8_t)((uint16_t)(R7) >> 8U), (uint8_t)((R7) & 0xFFU), (uint8_t)(M7), (uint8_t)(V7) \
                                 , (uint8_t)((uint16_t)(R8) >> 8U), (uint8_t)((R8) & 0xFFU), (uint8_t)(M8), (uint8_t)(V8) \
                                 , (uint8_t)((uint16_t)(R9) >> 8U), (uint8_t)((R9) & 0xFFU), (uint8_t)(M9), (uint8_t)(V9) \
                                 , (uint8_t)((uint16_t)(R10) >> 8U), (uint8_t)((R10) & 0xFFU), (uint8_t)(M10), (uint8_t)(V10) \
                                 , (uint8_t)((uint16_t)(R11) >> 8U), (uint8_t)((R11) & 0xFFU), (uint8_t)(M11), (uint8_t)(V11) \
                                 , (uint8_t)((uint16_t)(R12) >> 8U), (uint8_t)((R12) & 0xFFU), (uint8_t)(M12), (uint8_t)(V12) \
                                 , (uint8_t)((uint16_t)(R13) >> 8U), (uint8_t)((R13) & 0xFFU), (uint8_t)(M13), (uint8_t)(V13) \
                                 , (uint8_t)((uint16_t)(R14) >> 8U), (uint8_t)((R14) & 0xFFU), (uint8_t)(M14), (uint8_t)(V14) \
                                 , (uint8_t)((uint16_t)(R15) >> 8U), (uint8_t)((R15) & 0xFFU), (uint8_t)(M15), (uint8_t)(V15) \
                                 , (uint8_t)((uint16_t)(R16) >> 8U), (uint8_t)((R16) & 0xFFU), (uint8_t)(M16), (uint8_t)(V16) \
                                 , (uint8_t)((uint16_t)(R17) >> 8U), (uint8_t)((R17) & 0xFFU), (uint8_t)(M17), (uint8_t)(V17) \
                                 , (uint8_t)((uint16_t)(R18) >> 8U), (uint8_t)((R18) & 0xFFU), (uint8_t)(M18), (uint8_t)(V18) \
                                 , (uint8_t)((uint16_t)(R19) >> 8U), (uint8_t)((R19) & 0xFFU), (uint8_t)(M19), (uint8_t)(V19) \
                                 , (uint8_t)((uint16_t)(R20) >> 8U), (uint8_t)((R20) & 0xFFU), (uint8_t)(M20), (uint8_t)(V20) \
                                 , (uint8_t)((uint16_t)(R21) >> 8U), (uint8_t)((R21) & 0xFFU), (uint8_t)(M21), (uint8_t)(V21)

/*
 ******************************************************************************
 * GLOBAL DATA TYPES
 ******************************************************************************
 */
/*  PRQA S 3674 2 # CERT ARR02 - Flexible array will be used with sizeof, on adding elements error-prone manual update of size would be required */
/*  PRQA S 3406 1 # MISRA 8.6 - Externally generated table included by the library */   /*  PRQA S 1514 1 # MISRA 8.9 - Externally generated table included by the library */
const uint8_t rfalAnalogConfigDefaultSettings[] = {
    
    /****** Default Analog Configuration for Chip-Specific Reset ******/
    MODE_ENTRY_6_REG( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_INIT)
                        , ST25R200_REG_GENERAL, ST25R200_REG_GENERAL_miso_pd_mask, (ST25R200_REG_GENERAL_miso_pd1 | ST25R200_REG_GENERAL_miso_pd2) /* SPI MISO Pull downs */
                        , ST25R200_REG_OPERATION, ST25R200_REG_OPERATION_am_en, ST25R200_REG_OPERATION_am_en                                       /* Enable AM Regulator */
                        , ST25R200_REG_TX_MOD, (ST25R200_REG_TX_MOD_reg_am | ST25R200_REG_TX_MOD_reg_am), ST25R200_REG_TX_MOD_reg_am               /* Use AM via regulator */
                        , ST25R200_REG_TX_MOD, ST25R200_REG_TX_MOD_am_mod_mask, ST25R200_REG_TX_MOD_am_mod_12percent                               /* Set Modulation index */
                        , ST25R200_REG_TX_DRIVER, ST25R200_REG_TX_DRIVER_d_res_mask, 0x00                                                          /* Set RFO resistance Active Tx */
                        , ST25R200_REG_RX_ANA2, ST25R200_REG_RX_ANA2_afe_gain_td_mask, 0x04                                                        /* Increased Gain for WU mode  */
                        )
    
    
    /****** Default Analog Configuration for Chip-Specific Poll Common ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_POLL_COMMON)
                      , ST25R200_REG_CORR5, ST25R200_REG_CORR5_en_subc_end, ST25R200_REG_CORR5_en_subc_end                                       /* Enable fast subcarrier end detection */
                      )
                      
    /****** Default Analog Configuration for Poll NFC-A Tx 106 ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_106 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R200_REG_PROTOCOL_TX1, ST25R200_REG_PROTOCOL_TX1_tr_am, 0x00                                                           /* Use OOK */
                      )
                      
    /****** Default Analog Configuration for Poll NFC-A Rx 106 ******/
    , MODE_ENTRY_4_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_106 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R200_REG_RX_DIG,       (ST25R200_REG_RX_DIG_lpf_coef_mask | ST25R200_REG_RX_DIG_hpf_coef_mask), 0x4C
                      , ST25R200_REG_CORR1,        (ST25R200_REG_CORR1_iir_coef2_mask | ST25R200_REG_CORR1_iir_coef1_mask), 0xC3
                      , ST25R200_REG_CORR5,        ST25R200_REG_CORR5_dec_f_mask, 0x02
                      , ST25R200_REG_CORR4,        (ST25R200_REG_CORR4_coll_lvl_mask | ST25R200_REG_CORR4_data_lvl_mask), 0xAA
                      )
                      
    /****** Default Analog Configuration for Poll NFC-A Anticolision setting ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_ANTICOL)
                      , ST25R200_REG_CORR4,        ST25R200_REG_CORR4_coll_lvl_mask, 0x70                                                          /* Lower collision level during anticollision */
                      )

      /****** Default Analog Configuration for Poll NFC-B Tx 106 ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_106 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R200_REG_PROTOCOL_TX1, ST25R200_REG_PROTOCOL_TX1_tr_am, ST25R200_REG_PROTOCOL_TX1_tr_am                                /* Use AM  */
                      )

      /****** Default Analog Configuration for Poll NFC-B Rx 106 ******/
    , MODE_ENTRY_4_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_106 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R200_REG_RX_DIG,       (ST25R200_REG_RX_DIG_lpf_coef_mask | ST25R200_REG_RX_DIG_hpf_coef_mask), 0x4C
                      , ST25R200_REG_CORR1,        (ST25R200_REG_CORR1_iir_coef2_mask | ST25R200_REG_CORR1_iir_coef1_mask), 0xC1
                      , ST25R200_REG_CORR5,        ST25R200_REG_CORR5_dec_f_mask, 0x03
                      , ST25R200_REG_CORR4,        ST25R200_REG_CORR4_data_lvl_mask, 0x07                                                          /* Lower data level for NFC-B */
                      )
                      
    /****** Default Analog Configuration for Poll NFC-V Tx Common ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX)
                      , ST25R200_REG_PROTOCOL_TX1, ST25R200_REG_PROTOCOL_TX1_tr_am, 0x00                                                           /* Use OOK */
                      )

    /****** Default Analog Configuration for Poll NFC-V Rx Common ******/
    , MODE_ENTRY_2_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX)
                      , ST25R200_REG_RX_DIG,       (ST25R200_REG_RX_DIG_lpf_coef_mask | ST25R200_REG_RX_DIG_hpf_coef_mask), 0x08
                      , ST25R200_REG_CORR1,        (ST25R200_REG_CORR1_iir_coef2_mask | ST25R200_REG_CORR1_iir_coef1_mask), 0xC0
                      )
    
    /****** Default Analog Configuration for Poll NFC-V Anticolision setting ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_ANTICOL)
                      , ST25R200_REG_CORR4,        ST25R200_REG_CORR4_coll_lvl_mask, 0x70                                                          /* Lower collision level during anticollision */
                      )

    /****** Default Analog Configuration for Poll NFC-V Rx 26 ******/
    , MODE_ENTRY_2_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_26 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R200_REG_CORR5,        ST25R200_REG_CORR5_dec_f_mask, 0x04
                      , ST25R200_REG_CORR4,        (ST25R200_REG_CORR4_coll_lvl_mask | ST25R200_REG_CORR4_data_lvl_mask), 0xAA                     /* Restore default levels */
                      )
                      
    /****** Default Analog Configuration for Poll NFC-V Rx 53 ******/
    , MODE_ENTRY_2_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_53 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R200_REG_CORR5,        ST25R200_REG_CORR5_dec_f_mask, 0x03
                      , ST25R200_REG_CORR4,        (ST25R200_REG_CORR4_coll_lvl_mask | ST25R200_REG_CORR4_data_lvl_mask), 0xAA                     /* Restore default levels */
                      )
    
    /****** Default Analog Configuration for Wake-up On ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_WAKEUP_ON)
                      , 0x89U, 0x01U, 0x01U                                                                                                        /* Prevent VDD_A discharge during WU (AN5993) */
                     )
                     
    /****** Default Analog Configuration for Wake-up Off ******/
    , MODE_ENTRY_2_REG( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_WAKEUP_OFF)
                      , ST25R200_REG_OPERATION, ST25R200_REG_OPERATION_am_en, ST25R200_REG_OPERATION_am_en                                         /* Re-enable AM Regulator */
                      , 0x89U, 0x01U, 0x00U                                                                                                        /* Restore VDD_A config for RD mode */
                     )
                     
    /****** Default Analog Configuration for Low Power Off ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_LOWPOWER_OFF)
                      , ST25R200_REG_OPERATION, ST25R200_REG_OPERATION_am_en, ST25R200_REG_OPERATION_am_en                                         /* Re-enable AM Regulator */
                     )                     

};

#endif /* ST25R200_ANALOGCONFIG_H */
