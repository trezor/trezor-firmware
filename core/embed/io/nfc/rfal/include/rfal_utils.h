
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
 *      PROJECT:   ST25R 
 *      Revision:
 *      LANGUAGE:  ISO C99
 */

/*! \file rfal_utils.h
 *
 *  \author Gustavo Patricio 
 *
 *  \brief RF Abstraction Layer (RFAL) Utils
 *  
 * \addtogroup RFAL
 * @{
 *  
 */

#ifndef RFAL_UTILS_H
#define RFAL_UTILS_H

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include <stdint.h>
#include <string.h>


/*
******************************************************************************
* GLOBAL DATA TYPES
******************************************************************************
*/

typedef uint16_t      ReturnCode; /*!< Standard Return Code type from function. */

/*
******************************************************************************
* DEFINES
******************************************************************************
*/

/*
 * Error codes to be used within the application.
 * They are represented by an uint8_t
 */

#define RFAL_ERR_NONE                           ((ReturnCode)0U)  /*!< no error occurred */
#define RFAL_ERR_NOMEM                          ((ReturnCode)1U)  /*!< not enough memory to perform the requested operation */
#define RFAL_ERR_BUSY                           ((ReturnCode)2U)  /*!< device or resource busy */
#define RFAL_ERR_IO                             ((ReturnCode)3U)  /*!< generic IO error */
#define RFAL_ERR_TIMEOUT                        ((ReturnCode)4U)  /*!< error due to timeout */
#define RFAL_ERR_REQUEST                        ((ReturnCode)5U)  /*!< invalid request or requested function can't be executed at the moment */
#define RFAL_ERR_NOMSG                          ((ReturnCode)6U)  /*!< No message of desired type */
#define RFAL_ERR_PARAM                          ((ReturnCode)7U)  /*!< Parameter error */
#define RFAL_ERR_SYSTEM                         ((ReturnCode)8U)  /*!< System error */
#define RFAL_ERR_FRAMING                        ((ReturnCode)9U)  /*!< Framing error */
#define RFAL_ERR_OVERRUN                        ((ReturnCode)10U) /*!< lost one or more received bytes */
#define RFAL_ERR_PROTO                          ((ReturnCode)11U) /*!< protocol error */
#define RFAL_ERR_INTERNAL                       ((ReturnCode)12U) /*!< Internal Error */
#define RFAL_ERR_AGAIN                          ((ReturnCode)13U) /*!< Call again */
#define RFAL_ERR_MEM_CORRUPT                    ((ReturnCode)14U) /*!< memory corruption */
#define RFAL_ERR_NOT_IMPLEMENTED                ((ReturnCode)15U) /*!< not implemented */
#define RFAL_ERR_PC_CORRUPT                     ((ReturnCode)16U) /*!< Program Counter has been manipulated or spike/noise trigger illegal operation */
#define RFAL_ERR_SEND                           ((ReturnCode)17U) /*!< error sending*/
#define RFAL_ERR_IGNORE                         ((ReturnCode)18U) /*!< indicates error detected but to be ignored */
#define RFAL_ERR_SEMANTIC                       ((ReturnCode)19U) /*!< indicates error in state machine (unexpected cmd) */
#define RFAL_ERR_SYNTAX                         ((ReturnCode)20U) /*!< indicates error in state machine (unknown cmd) */
#define RFAL_ERR_CRC                            ((ReturnCode)21U) /*!< crc error */ 
#define RFAL_ERR_NOTFOUND                       ((ReturnCode)22U) /*!< transponder not found */ 
#define RFAL_ERR_NOTUNIQUE                      ((ReturnCode)23U) /*!< transponder not unique - more than one transponder in field */ 
#define RFAL_ERR_NOTSUPP                        ((ReturnCode)24U) /*!< requested operation not supported */ 
#define RFAL_ERR_WRITE                          ((ReturnCode)25U) /*!< write error */ 
#define RFAL_ERR_FIFO                           ((ReturnCode)26U) /*!< fifo over or underflow error */ 
#define RFAL_ERR_PAR                            ((ReturnCode)27U) /*!< parity error */ 
#define RFAL_ERR_DONE                           ((ReturnCode)28U) /*!< transfer has already finished */
#define RFAL_ERR_RF_COLLISION                   ((ReturnCode)29U) /*!< collision error (Bit Collision or during RF Collision avoidance ) */
#define RFAL_ERR_HW_OVERRUN                     ((ReturnCode)30U) /*!< lost one or more received bytes */
#define RFAL_ERR_RELEASE_REQ                    ((ReturnCode)31U) /*!< device requested release */
#define RFAL_ERR_SLEEP_REQ                      ((ReturnCode)32U) /*!< device requested sleep */
#define RFAL_ERR_WRONG_STATE                    ((ReturnCode)33U) /*!< incorrent state for requested operation */
#define RFAL_ERR_MAX_RERUNS                     ((ReturnCode)34U) /*!< blocking procedure reached maximum runs */
#define RFAL_ERR_DISABLED                       ((ReturnCode)35U) /*!< operation aborted due to disabled configuration */ 
#define RFAL_ERR_HW_MISMATCH                    ((ReturnCode)36U) /*!< expected hw do not match  */
#define RFAL_ERR_LINK_LOSS                      ((ReturnCode)37U) /*!< Other device's field didn't behave as expected: turned off by Initiator in Passive mode, or AP2P did not turn on field */
#define RFAL_ERR_INVALID_HANDLE                 ((ReturnCode)38U) /*!< invalid or not initialized device handle */

#define RFAL_ERR_INCOMPLETE_BYTE                ((ReturnCode)40U) /*!< Incomplete byte rcvd         */
#define RFAL_ERR_INCOMPLETE_BYTE_01             ((ReturnCode)41U) /*!< Incomplete byte rcvd - 1 bit */    
#define RFAL_ERR_INCOMPLETE_BYTE_02             ((ReturnCode)42U) /*!< Incomplete byte rcvd - 2 bit */
#define RFAL_ERR_INCOMPLETE_BYTE_03             ((ReturnCode)43U) /*!< Incomplete byte rcvd - 3 bit */
#define RFAL_ERR_INCOMPLETE_BYTE_04             ((ReturnCode)44U) /*!< Incomplete byte rcvd - 4 bit */
#define RFAL_ERR_INCOMPLETE_BYTE_05             ((ReturnCode)45U) /*!< Incomplete byte rcvd - 5 bit */
#define RFAL_ERR_INCOMPLETE_BYTE_06             ((ReturnCode)46U) /*!< Incomplete byte rcvd - 6 bit */
#define RFAL_ERR_INCOMPLETE_BYTE_07             ((ReturnCode)47U) /*!< Incomplete byte rcvd - 7 bit */

/*
******************************************************************************
* GLOBAL MACROS
******************************************************************************
*/
/*! Common code to exit a function with the error if function f return error */
#define RFAL_EXIT_ON_ERR(r, f) \
    (r) = (f);                 \
    if (RFAL_ERR_NONE != (r))  \
    {                          \
        return (r);            \
    }
    
    
/*! Common code to exit a function if process/function f has not concluded */
#define RFAL_EXIT_ON_BUSY(r, f) \
    (r) = (f);                  \
    if (RFAL_ERR_BUSY == (r))   \
    {                           \
        return (r);             \
    }

#define RFAL_SIZEOF_ARRAY(a)     (sizeof(a) / sizeof((a)[0]))  /*!< Compute the size of an array           */
#define RFAL_MAX(a, b)           (((a) > (b)) ? (a) : (b))     /*!< Return the maximum of the 2 values     */
#define RFAL_MIN(a, b)           (((a) < (b)) ? (a) : (b))     /*!< Return the minimum of the 2 values     */
#define RFAL_GETU16(a)           (((uint16_t)(a)[0] << 8) | (uint16_t)(a)[1])/*!< Cast two Big Endian 8-bits byte array to 16-bits unsigned */
#define RFAL_GETU32(a)           (((uint32_t)(a)[0] << 24) | ((uint32_t)(a)[1] << 16) | ((uint32_t)(a)[2] << 8) | ((uint32_t)(a)[3])) /*!< Cast four Big Endian 8-bit byte array to 32-bit unsigned */


#ifdef __CSMC__
/* STM8 COSMIC */
#define RFAL_MEMMOVE(s1,s2,n)                                                 memmove(s1,s2,n)                                /*  PRQA S 5003 # CERT C 9 - string.h from Cosmic only provides functions with low qualified parameters */ /*!< map memmove to string library code */
static inline void * RFAL_MEMCPY(void *s1, const void *s2, uint32_t n)      { return memcpy(s1,s2,(uint16_t)n); }             /*  PRQA S 0431 # MISRA 1.1 - string.h from Cosmic only provides functions with low qualified parameters */
#define RFAL_MEMSET(s1,c,n)                                                   memset(s1,(char)(c),n)                          /*!< map memset to string library code  */
static inline int32_t RFAL_BYTECMP(void *s1, const void *s2, uint32_t n)    { return (int32_t)memcmp(s1,s2,(uint16_t)n); }    /*  PRQA S 0431 # MISRA 1.1 - string.h from Cosmic only provides functions with low qualified parameters */

#else   /* __CSMC__ */

#define RFAL_MEMMOVE          memmove     /*!< map memmove to string library code */
#define RFAL_MEMCPY           memcpy      /*!< map memcpy to string library code  */
#define RFAL_MEMSET           memset      /*!< map memset to string library code  */
#define RFAL_BYTECMP          memcmp      /*!< map bytecmp to string library code */
#endif /* __CSMC__ */

#define RFAL_NO_WARNING(v)      ((void) (v)) /*!< Macro to suppress compiler warning */


#ifndef NULL
  #define NULL (void*)0                 /*!< represents a NULL pointer */
#endif /* !NULL */



#endif  /* RFAL_UTILS_H */


/**
  * @}
  *
  */

