#include "nordic_dfu.h"
#include "layout.h"
#include "sys.h"
#include "timer.h"
#include "usart.h"

#define default_prn 0
#define resp_header 0x60
#define init_type 0x01
#define fw_type 0x02

#define SLIP_END 0xC0
#define SLIP_ESC 0xDB
#define SLIP_ESC_END 0xDC
#define SLIP_ESC_ESC 0xDD

#define default_delay 200 * 500
#define long_delay 200 * 2000

static uint16_t mtu_len = 64;

static uint32_t max_size = 0;
static uint32_t offset = 0;
static uint32_t crc = 0;

static uint32_t reflect(uint32_t ref, char ch) {
  uint32_t value = 0;

  for (int i = 1; i < (ch + 1); i++) {
    if (ref & 1) value |= 1 << (ch - i);
    ref >>= 1;
  }

  return value;
}

uint32_t crc32(uint8_t *buf, uint32_t len) {
  uint32_t result = 0xFFFFFFFF;
  uint32_t m_Table[256];

  uint32_t ulPolynomial = 0x04C11DB7;

  for (int i = 0; i <= 0xFF; i++) {
    m_Table[i] = reflect(i, 8) << 24;
    for (int j = 0; j < 8; j++)
      m_Table[i] =
          (m_Table[i] << 1) ^ (m_Table[i] & (1 << 31) ? ulPolynomial : 0);
    m_Table[i] = reflect(m_Table[i], 32);
  }

  while (len--) result = (result >> 8) ^ m_Table[(result & 0xFF) ^ *buf++];

  result ^= 0xFFFFFFFF;

  return result;
}

static bool serial_transfer(uint8_t *cmd, uint32_t in_len, uint8_t *resp,
                            uint32_t *out_len, uint32_t delay) {
  uint32_t counter = delay;
  uint32_t i;
  uint32_t len = 0;
  bool slip_flag = false;
  bool transfer_end = false;
  *out_len = 0;
  // slip encode and send
  for (i = 0; i < in_len; i++) {
    if (cmd[i] == SLIP_END) {
      ble_usart_sendByte(SLIP_ESC);
      ble_usart_sendByte(SLIP_ESC_END);
    } else if (cmd[i] == SLIP_ESC) {
      ble_usart_sendByte(SLIP_ESC);
      ble_usart_sendByte(SLIP_ESC_ESC);
    } else {
      ble_usart_sendByte(cmd[i]);
    }
  }
  ble_usart_sendByte(SLIP_END);

  // slip decode andresponse
  while (counter--) {
    delay_us(5);
    if (ble_read_byte(resp) == true) {
      counter = 500;
      if (slip_flag) {
        slip_flag = false;
        if (*resp == SLIP_ESC_ESC)
          *resp = SLIP_ESC;
        else if (*resp == SLIP_ESC_END)
          *resp = SLIP_END;
        else
          break;
        len++;
        resp++;
      } else {
        if (*resp == SLIP_END) {
          len++;
          resp++;
          transfer_end = true;
          break;
        } else if (*resp == SLIP_ESC) {
          slip_flag = true;
        } else {
          len++;
          resp++;
        }
      }
    }
  }
  *out_len = len;
  return transfer_end;
}

static bool set_prn(void) {
  uint8_t cmd[64] = {0};
  uint8_t resp[64] = {0};
  uint32_t resp_len = 0;
  cmd[0] = NRF_DFU_OP_RECEIPT_NOTIF_SET;
  cmd[1] = default_prn & 0xff;
  cmd[2] = (default_prn >> 8) & 0xff;
  if (serial_transfer(cmd, 3, resp, &resp_len, default_delay) == true) {
    if ((resp[0] == resp_header) && (resp[2] == NRF_DFU_RES_CODE_SUCCESS)) {
      return true;
    }
  }
  return false;
}

static bool get_mtu(void) {
  uint8_t cmd[64] = {0};
  uint8_t resp[64] = {0};
  uint32_t resp_len = 0;
  cmd[0] = NRF_DFU_OP_MTU_GET;
  if (serial_transfer(cmd, 1, resp, &resp_len, default_delay) == true) {
    if ((resp[0] == resp_header) && (resp[2] == NRF_DFU_RES_CODE_SUCCESS)) {
      // mtu_len == (resp[4] << 8) + resp[3];
      return true;
    }
  }
  return false;
}

static bool select_object(uint8_t type) {
  uint8_t cmd[64] = {0};
  uint8_t resp[64] = {0};
  uint32_t resp_len = 0;
  cmd[0] = NRF_DFU_OP_OBJECT_SELECT;
  cmd[1] = type;
  if (serial_transfer(cmd, 2, resp, &resp_len, default_delay) == true) {
    if ((resp[0] == resp_header) && (resp[2] == NRF_DFU_RES_CODE_SUCCESS)) {
      max_size = (resp[6] << 24) + (resp[5] << 16) + (resp[4] << 8) + resp[3];
      offset = (resp[10] << 24) + (resp[9] << 16) + (resp[8] << 8) + resp[7];
      crc = (resp[14] << 24) + (resp[13] << 16) + (resp[12] << 8) + resp[11];
      if (init_type == type) {
      } else if (fw_type == type) {
      }
      return true;
    }
  }
  return false;
}
static bool create_object(uint8_t type, uint32_t size) {
  uint8_t cmd[64] = {0};
  uint8_t resp[64] = {0};
  uint32_t resp_len = 0;
  cmd[0] = NRF_DFU_OP_OBJECT_CREATE;
  cmd[1] = type;
  cmd[2] = size & 0xff;
  cmd[3] = (size >> 8) & 0xff;
  cmd[4] = (size >> 16) & 0xff;
  cmd[5] = (size >> 24) & 0xff;
  if (serial_transfer(cmd, 6, resp, &resp_len, default_delay) == true) {
    if ((resp[0] == resp_header) && (resp[2] == NRF_DFU_RES_CODE_SUCCESS)) {
      return true;
    }
  }
  return false;
}

static void write_object(uint8_t *buf, uint32_t len) {
  uint8_t cmd[128] = {0};
  uint8_t resp[64] = {0};
  uint32_t resp_len = 0;
  uint32_t offset_i = 0;
  cmd[0] = NRF_DFU_OP_OBJECT_WRITE;
  while (len / mtu_len) {
    memcpy(cmd + 1, buf + offset_i, mtu_len);
    serial_transfer(cmd, mtu_len + 1, resp, &resp_len, 0);
    offset_i += mtu_len;
    len -= mtu_len;
  }
  if (len) {
    memcpy(cmd + 1, buf + offset_i, len);
    serial_transfer(cmd, len + 1, resp, &resp_len, 0);
  }
}

static bool crc_object(uint32_t in_crc) {
  uint8_t cmd[64] = {0};
  uint8_t resp[64] = {0};
  uint32_t resp_len = 0;
  uint32_t crc_resp;
  cmd[0] = NRF_DFU_OP_CRC_GET;
  if (serial_transfer(cmd, 1, resp, &resp_len, default_delay) == true) {
    if (resp[0] == resp_header) {
      crc_resp = (resp[10] << 24) + (resp[9] << 16) + (resp[8] << 8) + resp[7];
      if (in_crc == crc_resp) return true;
    }
  }
  return false;
}
static bool excute_object(void) {
  uint8_t cmd[64] = {0};
  uint8_t resp[64] = {0};
  uint32_t resp_len = 0;
  cmd[0] = NRF_DFU_OP_OBJECT_EXECUTE;
  if (serial_transfer(cmd, 1, resp, &resp_len, long_delay) == true) {
    if ((resp[0] == resp_header) && (resp[2] == NRF_DFU_RES_CODE_SUCCESS)) {
      return true;
    }
  }
  return false;
}

static bool ping_boot(uint8_t id) {
  uint8_t cmd[64] = {0};
  uint8_t resp[64] = {0};
  uint32_t resp_len = 0;
  cmd[0] = NRF_DFU_OP_PING;
  cmd[1] = id;
  if (serial_transfer(cmd, 1, resp, &resp_len, default_delay) == true) {
    if ((resp[0] == resp_header) && (resp[2] == NRF_DFU_RES_CODE_SUCCESS)) {
      if (resp[3] == id) return true;
    }
  }
  return false;
}

static void enter_boot(void) {
  // ble power rest
  ble_power_off();
  ble_usart_disable();  // void usart rx drain current
  delay_ms(100);
  SET_COMBUS_HIGH();
  ble_power_on();
  ble_usart_enable();
  delay_ms(500);  // keep io voltage
  SET_COMBUS_LOW();
}

bool updateBle(uint8_t *init_data, uint8_t init_len, uint8_t *firmware,
               uint32_t fm_len) {
  uint32_t crc_i = 0;
  uint32_t offset_i = 0;
  uint32_t len;
  uint32_t totol_len = fm_len;

  enter_boot();

  for (uint8_t i = 0; i < 5; i++) {
    if (ping_boot(i) == true)
      break;
    else if (i == 4)
      return false;
  }

  if (set_prn() != true) return false;
  if (get_mtu() != true) return false;

  // init data
  if (create_object(init_type, init_len) != true) return false;
  crc_i = crc32(init_data, init_len);
  write_object(init_data, init_len);
  if (crc_object(crc_i) != true) return false;
  if (excute_object() != true) return false;

  // firmware
  if (select_object(fw_type) != true) return false;
  while (fm_len > 0) {
    layoutProgress("INSTALLING BLE firmware...", 1000 * offset_i / totol_len);
    len = fm_len > max_size ? max_size : fm_len;
    if (create_object(fw_type, len) != true) return false;
    crc_i = crc32(firmware, offset_i + len);
    write_object(firmware + offset_i, len);
    if (crc_object(crc_i) != true) return false;
    if (excute_object() != true) return false;
    fm_len -= len;
    offset_i += len;
  }
  return true;
}