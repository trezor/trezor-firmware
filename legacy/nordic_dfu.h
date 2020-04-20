#ifndef __NORDIC_DFU_H__
#define __NORDIC_DFU_H__

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

typedef enum {
  NRF_DFU_OP_PROTOCOL_VERSION = 0x00,   //!< Retrieve protocol version.
  NRF_DFU_OP_OBJECT_CREATE = 0x01,      //!< Create selected object.
  NRF_DFU_OP_RECEIPT_NOTIF_SET = 0x02,  //!< Set receipt notification.
  NRF_DFU_OP_CRC_GET = 0x03,            //!< Request CRC of selected object.
  NRF_DFU_OP_OBJECT_EXECUTE = 0x04,     //!< Execute selected object.
  NRF_DFU_OP_OBJECT_SELECT = 0x06,      //!< Select object.
  NRF_DFU_OP_MTU_GET = 0x07,            //!< Retrieve MTU size.
  NRF_DFU_OP_OBJECT_WRITE = 0x08,       //!< Write selected object.
  NRF_DFU_OP_PING = 0x09,               //!< Ping.
  NRF_DFU_OP_HARDWARE_VERSION = 0x0A,   //!< Retrieve hardware version.
  NRF_DFU_OP_FIRMWARE_VERSION = 0x0B,   //!< Retrieve firmware version.
  NRF_DFU_OP_ABORT = 0x0C,              //!< Abort the DFU procedure.
  NRF_DFU_OP_RESPONSE = 0x60,           //!< Response.
  NRF_DFU_OP_INVALID = 0xFF,
} nrf_dfu_op_t;

typedef enum {
  NRF_DFU_RES_CODE_INVALID = 0x00,                //!< Invalid opcode.
  NRF_DFU_RES_CODE_SUCCESS = 0x01,                //!< Operation successful.
  NRF_DFU_RES_CODE_OP_CODE_NOT_SUPPORTED = 0x02,  //!< Opcode not supported.
  NRF_DFU_RES_CODE_INVALID_PARAMETER =
      0x03,  //!< Missing or invalid parameter value.
  NRF_DFU_RES_CODE_INSUFFICIENT_RESOURCES =
      0x04,  //!< Not enough memory for the data object.
  NRF_DFU_RES_CODE_INVALID_OBJECT =
      0x05,  //!< Data object does not match the firmware and hardware
             //!< requirements, the signature is wrong, or parsing the command
             //!< failed.
  NRF_DFU_RES_CODE_UNSUPPORTED_TYPE =
      0x07,  //!< Not a valid object type for a Create request.
  NRF_DFU_RES_CODE_OPERATION_NOT_PERMITTED =
      0x08,  //!< The state of the DFU process does not allow this operation.
  NRF_DFU_RES_CODE_OPERATION_FAILED = 0x0A,  //!< Operation failed.
  NRF_DFU_RES_CODE_EXT_ERROR =
      0x0B,  //!< Extended error. The next byte of the response contains the
             //!< error code of the extended error (see @ref
             //!< nrf_dfu_ext_error_code_t.
} nrf_dfu_result_t;

bool updateBle(uint8_t *init_data, uint8_t init_len, uint8_t *firmware,
               uint32_t fm_len);

#endif
