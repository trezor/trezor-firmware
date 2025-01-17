
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

/*! \file rfal_iso15693_2.h
 *
 *  \author Ulrich Herrmann
 *
 *  \brief Implementation of ISO-15693-2
 *
 */
/*!
 * 
 */

#ifndef RFAL_ISO_15693_2_H
#define RFAL_ISO_15693_2_H

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include "rfal_platform.h"
#include "rfal_utils.h"

/*
******************************************************************************
* GLOBAL DATATYPES
******************************************************************************
*/
/*! Enum holding possible VCD codings  */
typedef enum
{
    ISO15693_VCD_CODING_1_4,
    ISO15693_VCD_CODING_1_256
}rfalIso15693VcdCoding_t;

/*! Enum holding possible VICC datarates */

/*! Configuration parameter used by rfalIso15693PhyConfigure  */
typedef struct
{
    rfalIso15693VcdCoding_t coding;       /*!< desired VCD coding                                       */
    uint32_t                speedMode;    /*!< 0: normal mode, 1: 2^1 = x2 Fast mode, 2 : 2^2 = x4 mode, 3 : 2^3 = x8 mode - all rx pulse numbers and times are divided by 1,2,4,8 */
}rfalIso15693PhyConfig_t;

/*! Parameters how the stream mode should work */
struct iso15693StreamConfig {
    uint8_t useBPSK;              /*!< 0: subcarrier, 1:BPSK */
    uint8_t din;                  /*!< the divider for the in subcarrier frequency: fc/2^din  */
    uint8_t dout;                 /*!< the divider for the in subcarrier frequency fc/2^dout */
    uint8_t report_period_length; /*!< the length of the reporting period 2^report_period_length*/
};
/*
******************************************************************************
* GLOBAL CONSTANTS
******************************************************************************
*/

#define ISO15693_REQ_FLAG_TWO_SUBCARRIERS 0x01U   /*!< Flag indication that communication uses two subcarriers */
#define ISO15693_REQ_FLAG_HIGH_DATARATE   0x02U   /*!< Flag indication that communication uses high bitrate    */
#define ISO15693_MASK_FDT_LISTEN         (65)     /*!< t1min = 308,2us = 4192/fc = 65.5 * 64/fc                */

/*! t1max = 323,3us = 4384/fc = 68.5 * 64/fc
 *         12 = 768/fc unmodulated time of single subcarrior SoF */
#define ISO15693_FWT (69 + 12)




/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/
/*! 
 *****************************************************************************
 *  \brief  Initialize the ISO15693 phy
 *
 *  \param[in] config : ISO15693 phy related configuration (See rfalIso15693PhyConfig_t)
 *  \param[out] needed_stream_config : return a pointer to the stream config 
 *              needed for this iso15693 config. To be used for configure RF chip.
 *
 *  \return RFAL_ERR_IO   : Error during communication.
 *  \return RFAL_ERR_NONE : No error.
 *
 *****************************************************************************
 */
extern ReturnCode rfalIso15693PhyConfigure(const rfalIso15693PhyConfig_t* config, const struct iso15693StreamConfig ** needed_stream_config  );

/*! 
 *****************************************************************************
 *  \brief  Return current phy configuration
 *
 *  This function returns current Phy configuration previously
 *  set by rfalIso15693PhyConfigure
 *
 *  \param[out] config : ISO15693 phy configuration.
 *
 *  \return RFAL_ERR_NONE : No error.
 *
 *****************************************************************************
 */
extern ReturnCode rfalIso15693PhyGetConfiguration(rfalIso15693PhyConfig_t* config);

/*! 
 *****************************************************************************
 *  \brief  Code an ISO15693 compatible frame
 *
 *  This function takes \a length bytes from \a buffer, perform proper
 *  encoding and sends out the frame to the ST25R391x.
 *
 *  \param[in] buffer    : data to send, modified to adapt flags.
 *  \param[in] length    : number of bytes to send.
 *  \param[in] sendCrc   : If set to true, CRC is appended to the frame
 *  \param[in] sendFlags : If set to true, flag field is sent according to
 *                                 ISO15693.
 *  \param[in] picopassMode   :  If set to true, the coding will be according to Picopass
 *  \param[out] subbit_total_length : Return the complete bytes which need to 
 *                                   be send for the current coding
 *  \param[in,out] offset     : Set to 0 for first transfer, function will update it to
                                point to next byte to be coded
 *  \param[out] outbuf        : buffer where the function will store the coded subbit stream
 *  \param[out] outBufSize    : the size of the output buffer
 *  \param[out] actOutBufSize : the amount of data stored into the buffer at this call
 *
 *  \return RFAL_ERR_IO     : Error during communication.
 *  \return RFAL_ERR_AGAIN  : Data was not coded all the way. Call function again with a new/emptied buffer
 *  \return RFAL_ERR_NO_MEM : In case outBuf is not big enough. Needs to have at 
                               least 5 bytes for 1of4 coding and 65 bytes for 1of256 coding
 *  \return RFAL_ERR_NONE   : No error
 *
 *****************************************************************************
 */
extern ReturnCode rfalIso15693VCDCode(uint8_t* buffer, uint16_t length, bool sendCrc, bool sendFlags, bool picopassMode,
                                       uint16_t *subbit_total_length, uint16_t *offset,
                                       uint8_t* outbuf, uint16_t outBufSize, uint16_t* actOutBufSize);


/*! 
 *****************************************************************************
 *  \brief  Receive an ISO15693 compatible frame
 *
 *  This function receives an ISO15693 frame from the ST25R391x, decodes the frame
 *  and writes the raw data to \a buffer.
 *  \note Buffer needs to be big enough to hold CRC also (+2 bytes)
 *
 *  \param[in] inBuf        : buffer with the hamming coded stream to be decoded
 *  \param[in] inBufLen     : number of bytes to decode (=length of buffer).
 *  \param[out] outBuf      : buffer where received data shall be written to.
 *  \param[in] outBufLen    : Length of output buffer, should be approx twice the size of inBuf
 *  \param[out] outBufPos   : The number of decoded bytes. Could be used in 
 *                              extended implementation to allow multiple calls
 *  \param[out] bitsBeforeCol : in case of RFAL_ERR_RF_COLLISION this value holds the
 *                               number of bits in the current byte where the collision happened
 *  \param[in] ignoreBits   : number of bits in the beginning where collisions will be ignored
 *  \param[in] picopassMode :  if set to true, the decoding will be according to Picopass
 *
 *  \return RFAL_ERR_RF_COLLISION : collision occured, data uncorrect
 *  \return RFAL_ERR_CRC          : CRC error, data uncorrect
 *  \return RFAL_ERR_TIMEOUT      : timeout waiting for data.
 *  \return RFAL_ERR_NONE         : No error
 *
 *****************************************************************************
 */
extern ReturnCode rfalIso15693VICCDecode(const uint8_t *inBuf,
                                          uint16_t inBufLen,
                                          uint8_t* outBuf,
                                          uint16_t outBufLen,
                                          uint16_t* outBufPos,
                                          uint16_t* bitsBeforeCol,
                                          uint16_t ignoreBits,
                                          bool picopassMode );

#endif /* RFAL_ISO_15693_2_H */

