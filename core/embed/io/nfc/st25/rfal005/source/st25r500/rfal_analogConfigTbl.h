
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2023 STMicroelectronics, all rights reserved
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
 *      Revision: 
 *      LANGUAGE:  ISO C99
 */

/*! \file rfal_analogConfig.h
 *
 *  \author Gustavo Patricio
 *
 *  \brief ST25R500 Analog Configuration Settings
 *  
 */

#ifndef ST25R500_ANALOGCONFIG_H
#define ST25R500_ANALOGCONFIG_H

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_analogConfig.h"
#include "st25r500_com.h"


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
    MODE_ENTRY_17_REG( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_INIT)
                        , ST25R500_REG_GENERAL,      ST25R500_REG_GENERAL_miso_pd_mask, (ST25R500_REG_GENERAL_miso_pd1 | ST25R500_REG_GENERAL_miso_pd2) /* SPI MISO Pull downs */
                        , ST25R500_REG_REGULATOR,    ST25R500_REG_REGULATOR_reg_s, 0x00                                                               /* Force adjust regulator direct command */
                        , ST25R500_REG_DRIVER,       ST25R500_REG_DRIVER_regd_mask, ST25R500_REG_DRIVER_regd_350mV                                    /* Configure proper LDO drop-out 200mV + regd*50mV: 350mV */
                        , ST25R500_REG_TX_MOD1,     (ST25R500_REG_TX_MOD1_rgs_am | ST25R500_REG_TX_MOD1_res_am), (ST25R500_REG_TX_MOD1_rgs_am | ST25R500_REG_TX_MOD1_res_am)/* Use AM via regulator and resistor, need to replicate FIELD_OFF */
                        , ST25R500_REG_TX_MOD2,      ST25R500_REG_TX_MOD2_md_res_mask, 0x7F                                                           /* Specify md_res as highZ used with res_am */
                        , ST25R500_REG_DRIVER,       ST25R500_REG_DRIVER_d_res_mask, 0x00                                                             /* Set RFO resistance Active Tx */
                        , ST25R500_REG_RX_ANA2,      ST25R500_REG_RX_ANA2_afe_gain_td_mask, 0x02                                                      /* Increased Gain for TD */
                        , ST25R500_REG_CE_TX_MOD1,  (ST25R500_REG_CE_TX_MOD1_cem_res_mask | ST25R500_REG_CE_TX_MOD1_ce_res_mask), 0xF0                /* Set passive listen modulation: high ohmic modulated state */
                        , ST25R500_REG_GPIO,         0xFF, 0x03                                                                                       /* EMI capacitor switched for RW */
                        , ST25R500_REG_RX_ANA1,      ST25R500_REG_RX_ANA1_dig_clk_dly_mask, 0x70                                                      /* Adapt to recommended dig_clk_dly */
                        , ST25R500_REG_CE_CONFIG2,   ST25R500_REG_CE_CONFIG2_fdel_mask, 0xC0                                                          /* Set CE FDT adjustmet */
                        , ST25R500_REG_EFD_THRESHOLD, 0xFF, 0x89                                                                                      /* Set External Field Detector thresholds */
                        , ST25R500_REG_WAKEUP_CONF2, ST25R500_REG_WAKEUP_CONF2_weak_disch, ST25R500_REG_WAKEUP_CONF2_weak_disch                       /* Weak discharge VDD_A low power modes */
                        , ST25R500_REG_WAKEUP_CONF2, ST25R500_REG_WAKEUP_CONF2_tagdet_len_mask, 0x03                                                  /* Set measurement pulse to 61.4us */
                        , (RFAL_TEST_REG | ST25R500_TEST_REG_MAN_TIMING), ST25R500_TEST_REG_MAN_TIMING_main_wait_ok, ST25R500_TEST_REG_MAN_TIMING_main_wait_ok /* man_wait_ok */
                        , (RFAL_TEST_REG | ST25R500_TEST_REG_OSC_TIMING), ST25R500_TEST_REG_OSC_TIMING_wait_ok_count_set_mask, 0x3F                   /* max wait_ok_count_set for best wake-up stability */
                        , (RFAL_TEST_REG | ST25R500_TEST_REG_DIAG_MEAS), ST25R500_TEST_REG_DIAG_MEAS_discon_tad_out, ST25R500_TEST_REG_DIAG_MEAS_discon_tad_out /* Stable diagnostic measurement */
                        )
    
    /****** Default Analog Configuration for Chip-Specific Poll Common ******/
    , MODE_ENTRY_12_REG( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_POLL_COMMON)
                      , ST25R500_REG_RX_ANA2, ST25R500_REG_RX_ANA2_afe_gain_rw_mask, 0x00                                                          /* Nominal gain for RW */
                      , ST25R500_REG_CORR2,        0xFF, 0x2D                                                                                      /* Adjust Squelch and AGC */
                      , ST25R500_REG_CORR3,        ST25R500_REG_CORR3_en_subc_end, 0x00                                                            /* Disable fast subcarrier end detection */
                      , ST25R500_REG_RX_ANA4,      ST25R500_REG_RX_ANA4_en_phase_deadzone, 0x00                                                    /* en_phase_deadzone=0, needed for listen, reset for poll */
                      , ST25R500_REG_RX_ANA4,      ST25R500_REG_RX_ANA4_en_rect_cor, ST25R500_REG_RX_ANA4_en_rect_cor                              /* en_rect_cor=1 for phase drift tests in BPSK */
                      , ST25R500_REG_PROTOCOL_TX1, ST25R500_REG_PROTOCOL_TX1_p_len_mask, 0x00                                                      /* set p_len default in middle(default) */
                      , ST25R500_REG_PROTOCOL_TX1, ST25R500_REG_PROTOCOL_TX1_tr_am, ST25R500_REG_PROTOCOL_TX1_tr_am                                /* Use AM as default */
                      , ST25R500_REG_AWS_TIME2,    0xF0, 0x00                                                                                      /* tpassingx1 = 0(default) */
                      , ST25R500_REG_SQT,          0xFF, 0xFF                                                                                      /* Reset to setting which uses MRT setting */
                      , ST25R500_REG_AWS_TIME1,    0xF0, 0xF0                                                                                      /* tentx1 setting */
                      , ST25R500_REG_AWS_TIME1,    0x0F, 0x0F                                                                                      /* tdres1 setting */
                      , ST25R500_REG_PROTOCOL_TX2, ST25R500_REG_PROTOCOL_TX2_b_tx_half, ST25R500_REG_PROTOCOL_TX2_b_tx_half                        /* Set b_tx_half to not have marginal SOF/EOF */
                      )
                      
    /****** Default Analog Configuration for Poll NFC-A Tx Common ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG1, 0x10, 0x00                                                                                       /* Disable dyn_pass_sink */
                      )
                      
    /****** Default Analog Configuration for Poll NFC-A Tx 106 ******/
    , MODE_ENTRY_5_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_106 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG2,   0xFF, 0x33                                                                                     /* setting the am_filt for rising and falling edge */
                      , ST25R500_REG_PROTOCOL_TX1,  ST25R500_REG_PROTOCOL_TX1_tr_am, 0x00                                                          /* Use OOK */
                      , ST25R500_REG_TX_MOD1,       ST25R500_REG_TX_MOD1_am_mod_mask, ST25R500_REG_TX_MOD1_am_mod_97percent                        /* Set Modulation index to highest (OOK) */
                      , ST25R500_REG_TX_MOD1,      (ST25R500_REG_TX_MOD1_res_am | ST25R500_REG_TX_MOD1_rgs_am), (ST25R500_REG_TX_MOD1_res_am | ST25R500_REG_TX_MOD1_rgs_am) /* Set res_am and rgs_am */
                      , ST25R500_REG_AWS_TIME3,     0x0F, 0x00                                                                                     /* Set tdres2, only used with res_am=1, no need to clear elsewhere */
                      )
                      
    /****** Default Analog Configuration for Poll NFC-A Rx 106 ******/
    , MODE_ENTRY_12_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_106 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA2,  ST25R500_REG_RX_ANA2_afe_gain_rw_mask, 0x20                                                        /* Reduce gain */
                      , ST25R500_REG_RX_ANA1,  ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x03                                                           /* Higher hpf_ctrl for max neg LMA */
                      , ST25R500_REG_RX_DIG,  (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x68                       /* Narrower window for max neg LMA */
                      , ST25R500_REG_CORR1,   (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xF8
                      , ST25R500_REG_CORR2,    0xFF, 0x2E                                                                                         /* Increase agc_thr according #1179027 */
                      , ST25R500_REG_CORR3,    ST25R500_REG_CORR3_start_wait_mask, 0x0F
                      , ST25R500_REG_CORR4,   (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0x88                         /* With reduced gain use lower levels */
                      , ST25R500_REG_CORR5,    0xFF, 0x32
                      , ST25R500_REG_CORR6,   (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x20             /* Increase init_noise_lvl to filter noise */
                      , ST25R500_REG_RX_ANA4,  ST25R500_REG_RX_ANA4_en_rect_cor, 0                                                                /* NFC-A 106 is not BPSK */
                      , ST25R500_REG_MRT1,     ST25R500_REG_MRT1_sq_del_mask, 0x00
                      , ST25R500_REG_SQT,      0xFF, 0x1C                                                                                         /* In 16/fc steps, requires proper mrt_step */
                      )

                      
    /****** Default Analog Configuration for Poll NFC-A Anticolision setting ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_ANTICOL)
                      , ST25R500_REG_CORR4,        ST25R500_REG_CORR4_coll_lvl_mask, 0x70                                                          /* Lower collision level during anticollision */
                      )

    /****** Default Analog Configuration for Poll NFC-A Tx 212 ******/
    , MODE_ENTRY_5_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_212 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG2,   0xFF, 0x70                                                                                     /* setting the am_filt for rising and falling edge */
                      , ST25R500_REG_PROTOCOL_TX1,  ST25R500_REG_PROTOCOL_TX1_p_len_mask, 0x01                                                     /* p_len 19 instead of 18 pulses */
                      , ST25R500_REG_PROTOCOL_TX1,  ST25R500_REG_PROTOCOL_TX1_tr_am, ST25R500_REG_PROTOCOL_TX1_tr_am                               /* Use AM */
                      , ST25R500_REG_TX_MOD1,      (ST25R500_REG_TX_MOD1_res_am | ST25R500_REG_TX_MOD1_rgs_am), ST25R500_REG_TX_MOD1_rgs_am        /* Clear res_am and set rgs_am */
                      , ST25R500_REG_TX_MOD1,       ST25R500_REG_TX_MOD1_am_mod_mask, ST25R500_REG_TX_MOD1_am_mod_80percent                        /* Set Modulation index */
                      )
                      
    /****** Default Analog Configuration for Poll NFC-A Rx 212 ******/
    , MODE_ENTRY_9_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_212 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1,  ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x01
                      , ST25R500_REG_RX_DIG,  (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x48
                      , ST25R500_REG_CORR1,   (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xD4
                      , ST25R500_REG_CORR3,    ST25R500_REG_CORR3_start_wait_mask, 0x0F
                      , ST25R500_REG_CORR3,    ST25R500_REG_CORR3_en_subc_end, ST25R500_REG_CORR3_en_subc_end                                      /* Enable fast subcarrier end detection */
                      , ST25R500_REG_CORR4,   (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xA3
                      , ST25R500_REG_CORR5,    0xFF, 0x32U
                      , ST25R500_REG_CORR6,   (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x01
                      , ST25R500_REG_MRT1,     ST25R500_REG_MRT1_sq_del_mask, 0x00
                      )
                      
    /****** Default Analog Configuration for Poll NFC-A Tx 424 ******/
    , MODE_ENTRY_4_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_424 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG2,  0xFF, 0x00                                                                                      /* Setting the am_filt for rising and falling edge */
                      , ST25R500_REG_PROTOCOL_TX1, ST25R500_REG_PROTOCOL_TX1_tr_am, ST25R500_REG_PROTOCOL_TX1_tr_am                                /* Use AM */
                      , ST25R500_REG_TX_MOD1,      ST25R500_REG_TX_MOD1_am_mod_mask, ST25R500_REG_TX_MOD1_am_mod_60percent                         /* Set Modulation index */
                      , ST25R500_REG_TX_MOD1,     (ST25R500_REG_TX_MOD1_res_am | ST25R500_REG_TX_MOD1_rgs_am), ST25R500_REG_TX_MOD1_rgs_am         /* Clear res_am and set rgs_am */
                      )

    /****** Default Analog Configuration for Poll NFC-A Rx 424 ******/
    , MODE_ENTRY_10_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_424 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1, ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x01
                      , ST25R500_REG_RX_DIG,  (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x58
                      , ST25R500_REG_CORR1,        (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xD6
                      , ST25R500_REG_CORR2,        0xFF, 0x2D
                      , ST25R500_REG_CORR3,        ST25R500_REG_CORR3_start_wait_mask, 0x1F
                      , ST25R500_REG_CORR3,        ST25R500_REG_CORR3_en_subc_end, ST25R500_REG_CORR3_en_subc_end                                 /* Enable fast subcarrier end detection */
                      , ST25R500_REG_CORR4,        (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xA3
                      , ST25R500_REG_CORR5,        0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | ST25R500_REG_CORR5_no_phase | 0x01U)
                      , ST25R500_REG_CORR6,        (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x04
                      , ST25R500_REG_MRT1, ST25R500_REG_MRT1_sq_del_mask, 0x00
                      )
                      
    /****** Default Analog Configuration for Poll NFC-A Tx 848 ******/
    , MODE_ENTRY_6_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_848 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_PROTOCOL_TX1, ST25R500_REG_PROTOCOL_TX1_p_len_mask, 0x0E                                                      /* p_len 3 instead of 5 */
                      , ST25R500_REG_PROTOCOL_TX1, ST25R500_REG_PROTOCOL_TX1_tr_am, ST25R500_REG_PROTOCOL_TX1_tr_am                                /* Use AM */
                      , ST25R500_REG_TX_MOD1,      ST25R500_REG_TX_MOD1_am_mod_mask, ST25R500_REG_TX_MOD1_am_mod_97percent                         /* Set Modulation index */
                      , ST25R500_REG_AWS_CONFIG2,  0xFF, 0x00                                                                                      /* am_filt set to fastest value */
                      , ST25R500_REG_AWS_TIME2,    0xF0, 0x50                                                                                      /* tpassingx1 = 5 */
                      , ST25R500_REG_TX_MOD1,     (ST25R500_REG_TX_MOD1_res_am | ST25R500_REG_TX_MOD1_rgs_am), ST25R500_REG_TX_MOD1_rgs_am         /* Clear res_am and set rgs_am */
                      )
    /****** Default Analog Configuration for Poll NFC-A Rx 848 ******/
    , MODE_ENTRY_10_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCA | RFAL_ANALOG_CONFIG_BITRATE_848 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1, ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x01
                      , ST25R500_REG_RX_DIG,  (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x64
                      , ST25R500_REG_CORR1,       (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xAA
                      , ST25R500_REG_CORR2,        0xFF, 0x2B
                      , ST25R500_REG_CORR3,        ST25R500_REG_CORR3_start_wait_mask, 0x3F
                      , ST25R500_REG_CORR3,        ST25R500_REG_CORR3_en_subc_end, ST25R500_REG_CORR3_en_subc_end                                 /* Enable fast subcarrier end detection */
                      , ST25R500_REG_CORR4,        (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xA6
                      , ST25R500_REG_CORR5,        0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | ST25R500_REG_CORR5_no_phase | 0x00U)
                      , ST25R500_REG_CORR6,       (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x19
                      , ST25R500_REG_MRT1,         ST25R500_REG_MRT1_sq_del_mask, 0x40
                      ) 

      /****** Default Analog Configuration for Poll NFC-B Tx Common ******/
    , MODE_ENTRY_3_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG1, 0x10, 0x00                                                                                       /* Disable dyn_pass_sink */
                      , ST25R500_REG_TX_MOD1, ST25R500_REG_TX_MOD1_am_mod_mask, ST25R500_REG_TX_MOD1_am_mod_12percent                              /* Set Modulation index */
                      , ST25R500_REG_TX_MOD1,      (ST25R500_REG_TX_MOD1_res_am | ST25R500_REG_TX_MOD1_rgs_am), ST25R500_REG_TX_MOD1_rgs_am        /* Clear res_am and set rgs_am */
                      )
                      
      /****** Default Analog Configuration for Poll NFC-B Tx 106 ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_106 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG2,  0xFF, 0x44                                                                                      /* Setting the am_filt for rising and falling edge */
                      )

      /****** Default Analog Configuration for Poll NFC-B Rx 106 ******/
    , MODE_ENTRY_10_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_106 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1,      ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x02
                      , ST25R500_REG_RX_DIG,      (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x48
                      , ST25R500_REG_CORR1,       (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xD1
                      , ST25R500_REG_CORR3,        ST25R500_REG_CORR3_start_wait_mask, 0x07
                      , ST25R500_REG_CORR4,       (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xA3                      /* Lower data level for NFC-B */
                      , ST25R500_REG_CORR5,        0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | 0x03U)          /* dis_soft_sq=1 to resolve #1209674 (ISO EMD suppression), dis_agc_noise_meas=1 to resolve #1315123 */
                      , ST25R500_REG_CORR6,       (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x00
                      , ST25R500_REG_CORR3,        ST25R500_REG_CORR3_en_subc_end, ST25R500_REG_CORR3_en_subc_end                                  /* Enable fast subcarrier end detection */
                      , ST25R500_REG_MRT1,         ST25R500_REG_MRT1_sq_del_mask, 0x00
                      , ST25R500_REG_SQT,          0xFF, 0x1C                                                                                      /* In 16/fc steps, equivalent to previous 7*64/fc */
                      )

      /****** Default Analog Configuration for Poll NFC-B Tx 212 ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_212 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG2,  0xFF, 0x44                                                                                      /* Setting the am_filt for rising and falling edge */
                      )

      /****** Default Analog Configuration for Poll NFC-B Rx 212 ******/
    , MODE_ENTRY_9_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_212 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1,       ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x01
                      , ST25R500_REG_RX_DIG,       (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x48
                      , ST25R500_REG_CORR1,        (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xD4
                      , ST25R500_REG_CORR3,         ST25R500_REG_CORR3_start_wait_mask, 0x0F
                      , ST25R500_REG_CORR4,        (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xA3
                      , ST25R500_REG_CORR5,         0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | 0x02U) 
                      , ST25R500_REG_CORR3,         ST25R500_REG_CORR3_en_subc_end, ST25R500_REG_CORR3_en_subc_end                                 /* Enable fast subcarrier end detection */
                      , ST25R500_REG_CORR6,        (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x01
                      , ST25R500_REG_MRT1,          ST25R500_REG_MRT1_sq_del_mask, 0x00
                      )
                      
      /****** Default Analog Configuration for Poll NFC-B Tx 424 ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_424 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG2,  0xFF, 0x00                                                                                      /* Setting the am_filt for rising and falling edge */
                      )

      /****** Default Analog Configuration for Poll NFC-B Rx 424 ******/
    , MODE_ENTRY_10_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_424 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1,       ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x01
                      , ST25R500_REG_RX_DIG,       (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x58
                      , ST25R500_REG_CORR1,        (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xD6
                      , ST25R500_REG_CORR2,         0xFF, 0x2D
                      , ST25R500_REG_CORR3,         ST25R500_REG_CORR3_start_wait_mask, 0x1F
                      , ST25R500_REG_CORR4,        (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xA3
                      , ST25R500_REG_CORR5,         0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | ST25R500_REG_CORR5_no_phase | 0x01U)
                      , ST25R500_REG_CORR3,         ST25R500_REG_CORR3_en_subc_end, ST25R500_REG_CORR3_en_subc_end                                 /* Enable fast subcarrier end detection */
                      , ST25R500_REG_CORR6,        (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x04
                      , ST25R500_REG_MRT1,          ST25R500_REG_MRT1_sq_del_mask, 0x00
                      )
                      
      /****** Default Analog Configuration for Poll NFC-B Tx 848 ******/
    , MODE_ENTRY_4_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_848 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG2,  0xFF, 0x00                                                                                      /* setting the am_filt for rising and falling edge */
                      , ST25R500_REG_AWS_TIME1,    0xF0, 0xF0                                                                                      /* tentx1 setting */
                      , ST25R500_REG_AWS_TIME2,    0xF0, 0x10                                                                                      /* tpassingx1 = 1 */
                      , ST25R500_REG_TX_MOD1,      ST25R500_REG_TX_MOD1_am_mod_mask, ST25R500_REG_TX_MOD1_am_mod_12percent
                      )

    /****** Default Analog Configuration for Poll NFC-B Rx 848 ******/
    , MODE_ENTRY_10_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCB | RFAL_ANALOG_CONFIG_BITRATE_848 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1,      ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x01
                      , ST25R500_REG_RX_DIG,      (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x64
                      , ST25R500_REG_CORR1,       (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xAA
                      , ST25R500_REG_CORR2,        0xFF, 0x2B
                      , ST25R500_REG_CORR3,        ST25R500_REG_CORR3_start_wait_mask, 0x3F
                      , ST25R500_REG_CORR4,       (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xA6
                      , ST25R500_REG_CORR5,        0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | ST25R500_REG_CORR5_no_phase | 0x00U)
                      , ST25R500_REG_CORR3,        ST25R500_REG_CORR3_en_subc_end, ST25R500_REG_CORR3_en_subc_end                                  /* Enable fast subcarrier end detection */
                      , ST25R500_REG_CORR6,       (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x19
                      , ST25R500_REG_MRT1,         ST25R500_REG_MRT1_sq_del_mask, 0x40
                      )
                      
    /****** Default Analog Configuration for Poll NFC-F Tx Common ******/
    , MODE_ENTRY_3_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCF | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG1,   0x10, 0x00                                                                                     /* Disable dyn_pass_sink */
                      , ST25R500_REG_TX_MOD1,       ST25R500_REG_TX_MOD1_am_mod_mask, ST25R500_REG_TX_MOD1_am_mod_12percent                        /* Set Modulation index */
                      , ST25R500_REG_TX_MOD1,      (ST25R500_REG_TX_MOD1_res_am | ST25R500_REG_TX_MOD1_rgs_am), ST25R500_REG_TX_MOD1_rgs_am        /* clear res_am and set rgs_am */
                      )
                      
    /****** Default Analog Configuration for Poll NFC-F Rx Common ******/
    , MODE_ENTRY_3_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCF | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1, ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x00
                      , ST25R500_REG_CORR4,        (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xA6
                      , ST25R500_REG_MRT1, ST25R500_REG_MRT1_sq_del_mask, 0x40
                      )

    /****** Default Analog Configuration for Poll NFC-F Tx 212 ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCF | RFAL_ANALOG_CONFIG_BITRATE_212 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG2,  0xFF, 0x33                                                                                      /* setting the am_filt for rising and falling edge */
                      )

    /****** Default Analog Configuration for Poll NFC-F Rx 212 ******/
    , MODE_ENTRY_5_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCF | RFAL_ANALOG_CONFIG_BITRATE_212 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_DIG,       (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x10
                      , ST25R500_REG_CORR1,        (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xD1
                      , ST25R500_REG_CORR3,         ST25R500_REG_CORR3_start_wait_mask, 0x1F
                      , ST25R500_REG_CORR5,         0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | 0x02U)
                      , ST25R500_REG_CORR6,        (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x04
                      )
                      
    /****** Default Analog Configuration for Poll NFC-F Tx 424 ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCF | RFAL_ANALOG_CONFIG_BITRATE_424 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG2,  0xFF, 0x11                                                                                      /* setting the am_filt for rising and falling edge */
                      )

    /****** Default Analog Configuration for Poll NFC-F Rx 424 ******/
    , MODE_ENTRY_6_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCF | RFAL_ANALOG_CONFIG_BITRATE_424 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_DIG,      (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x40
                      , ST25R500_REG_CORR1,       (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xD4
                      , ST25R500_REG_CORR2,        0xFF, 0x2B
                      , ST25R500_REG_CORR3,        ST25R500_REG_CORR3_start_wait_mask, 0x3F
                      , ST25R500_REG_CORR5,        0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | 0x01U)
                      , ST25R500_REG_CORR6,       (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x09
                      )
                      
    /****** Default Analog Configuration for Poll NFC-V Tx 26 ******/
    , MODE_ENTRY_6_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_26 | RFAL_ANALOG_CONFIG_TX)
                      , ST25R500_REG_AWS_CONFIG2,   0xFF, 0x33                                                                                     /* setting the am_filt for rising and falling edge */
                      , ST25R500_REG_PROTOCOL_TX1,  ST25R500_REG_PROTOCOL_TX1_tr_am, 0                                                             /* Use OOK */
                      , ST25R500_REG_TX_MOD1,       ST25R500_REG_TX_MOD1_am_mod_mask, ST25R500_REG_TX_MOD1_am_mod_97percent                        /* Set Modulation index to highest (OOK) */
                      , ST25R500_REG_TX_MOD1,      (ST25R500_REG_TX_MOD1_res_am | ST25R500_REG_TX_MOD1_rgs_am), (ST25R500_REG_TX_MOD1_res_am | ST25R500_REG_TX_MOD1_rgs_am) /* Set res_am and rgs_am */
                      , ST25R500_REG_AWS_TIME3,     0x0F, 0x00                                                                                     /* set tdres2, only used with res_am=1, no need to clear elsewhere */
                      , ST25R500_REG_AWS_CONFIG1,   0x10, 0x00                                                                                     /* Disable dyn_pass_sink */
                      )
                      
    /****** Default Analog Configuration for Poll NFC-V Rx Common *****/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_MRT1, ST25R500_REG_MRT1_sq_del_mask, 0x40
                      )
    
    /****** Default Analog Configuration for Poll NFC-V Anticolision setting ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_COMMON | RFAL_ANALOG_CONFIG_ANTICOL)
                      , ST25R500_REG_CORR4,        ST25R500_REG_CORR4_coll_lvl_mask, 0x70                                                          /* Lower collision level during anticollision */
                      )

    /****** Default Analog Configuration for Poll NFC-V Rx 26 ******/
    , MODE_ENTRY_9_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_26 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1,       ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x01
                      , ST25R500_REG_RX_DIG,      (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x50
                      , ST25R500_REG_CORR1,       (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xD0
                      , ST25R500_REG_CORR2,        0xFF, 0x2A
                      , ST25R500_REG_CORR3,        ST25R500_REG_CORR3_start_wait_mask, 0x08
                      , ST25R500_REG_CORR4,        (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xAA                     /* Restore default levels */
                      , ST25R500_REG_CORR5,        0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | 0x04U)
                      , ST25R500_REG_CORR6,       (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x10
                      , ST25R500_REG_RX_ANA4,      ST25R500_REG_RX_ANA4_en_rect_cor, 0                                                             /* NFC-V is not BPSK */
                      )
                      
    /****** Default Analog Configuration for Poll NFC-V Rx 53 ******/
    , MODE_ENTRY_9_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_53 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1,       ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x01
                      , ST25R500_REG_RX_DIG,       (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x50
                      , ST25R500_REG_CORR1,        (ST25R500_REG_CORR1_iir_coef2_mask | ST25R500_REG_CORR1_iir_coef1_mask), 0xD2
                      , ST25R500_REG_CORR2,         0xFF, 0x2A
                      , ST25R500_REG_CORR3,         ST25R500_REG_CORR3_start_wait_mask, 0x08
                      , ST25R500_REG_CORR4,        (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xAA                     /* Restore default levels */
                      , ST25R500_REG_CORR5,         0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | 0x03U)
                      , ST25R500_REG_CORR6,        (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x10
                      , ST25R500_REG_RX_ANA4,       ST25R500_REG_RX_ANA4_en_rect_cor, 0                                                            /* NFC-V is not BPSK */
                      )
                      
/****** Default Analog Configuration for Poll NFC-V Rx 105.94 ******/
    , MODE_ENTRY_9_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_105p94 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1,    ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x01
                      , ST25R500_REG_RX_DIG,    (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x50
                      , ST25R500_REG_CORR1,      0xFF, 0xD6
                      , ST25R500_REG_CORR2,      0xFF, 0x2A
                      , ST25R500_REG_CORR3,      ST25R500_REG_CORR3_start_wait_mask, 0x09
                      , ST25R500_REG_CORR4,      (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xAA                       /* Restore default levels */
                      , ST25R500_REG_CORR5,      0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | 0x02U)
                      , ST25R500_REG_CORR6,     (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x20
                      , ST25R500_REG_RX_ANA4,    ST25R500_REG_RX_ANA4_en_rect_cor, 0                                                               /* NFC-V is not BPSK */
                      )
                      
/****** Default Analog Configuration for Poll NFC-V Rx 211.88 ******/
    , MODE_ENTRY_9_REG( (RFAL_ANALOG_CONFIG_POLL | RFAL_ANALOG_CONFIG_TECH_NFCV | RFAL_ANALOG_CONFIG_BITRATE_211p88 | RFAL_ANALOG_CONFIG_RX)
                      , ST25R500_REG_RX_ANA1,   ST25R500_REG_RX_ANA1_hpf_ctrl_mask, 0x03
                      , ST25R500_REG_RX_DIG,   (ST25R500_REG_RX_DIG_lpf_coef_mask | ST25R500_REG_RX_DIG_hpf_coef_mask), 0x34
                      , ST25R500_REG_CORR1,     0xFF, 0xDB
                      , ST25R500_REG_CORR2,     0xFF, 0x2D                                                                                         /* Reduce to have clean LMA scan */
                      , ST25R500_REG_CORR3,     ST25R500_REG_CORR3_start_wait_mask, 0x09
                      , ST25R500_REG_CORR4,    (ST25R500_REG_CORR4_coll_lvl_mask | ST25R500_REG_CORR4_data_lvl_mask), 0xAA                         /* Restore default levels */
                      , ST25R500_REG_CORR5,     0xFF, (ST25R500_REG_CORR5_dis_soft_sq | ST25R500_REG_CORR5_dis_agc_noise_meas | 0x01U)
                      , ST25R500_REG_CORR6,    (ST25R500_REG_CORR6_init_noise_lvl_mask | ST25R500_REG_CORR6_agc_freeze_cnt_mask), 0x40
                      , ST25R500_REG_RX_ANA4,   ST25R500_REG_RX_ANA4_en_rect_cor, 0                                                                /* NFC-V is not BPSK */
                      )                      
                      
    /****** Default Analog Configuration for Listen On ******/

    , MODE_ENTRY_4_REG( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_LISTEN_ON)
                      , ST25R500_REG_CORR2,         0xFF, 0x5A                                                                         /* Switch back to default agc_thr as also done in PD mode */
                      , ST25R500_REG_RX_ANA4,       ST25R500_REG_RX_ANA4_en_phase_deadzone, ST25R500_REG_RX_ANA4_en_phase_deadzone     /* en_phase_deadzone=1, needed for listen NFC-F, d.c. for listen NFC-A */
                      , ST25R500_REG_RX_ANA4,       ST25R500_REG_RX_ANA4_en_rect_cor, 0                                                /* Restore for listen mode receptions */
                      , ST25R500_REG_EFD_THRESHOLD, 0xFF, 0x89                                                                         /* Set External Field Detector thresholds */
                      )

    /****** Default Analog Configuration for Wake-up On ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_WAKEUP_ON)
                     , ST25R500_REG_RX_ANA1, ST25R500_REG_RX_ANA1_gain_boost, ST25R500_REG_RX_ANA1_gain_boost                          /* gain_boost on */
                     )
    /****** Default Analog Configuration for Wake-up Off ******/
    , MODE_ENTRY_1_REG( (RFAL_ANALOG_CONFIG_TECH_CHIP | RFAL_ANALOG_CONFIG_CHIP_WAKEUP_OFF)
                     , ST25R500_REG_RX_ANA1, ST25R500_REG_RX_ANA1_gain_boost, 0x00                                                     /* gain_boost back to off */
                     )
};

#endif /* ST25R500_ANALOGCONFIG_H */
