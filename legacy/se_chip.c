#include "se_chip.h"
#include "mi2c.h"
#include "rtt_log.h"

// mode is export seed
void se_get_seed(bool mode, const char *passphrase, uint8_t *seed) {
  rtt_log_print("SE gen seed");
  uint8_t cmd[1024];
  uint16_t resplen;
  int passphraselen = strnlen(passphrase, 256);
  uint8_t salt[8 + 256] = {0};
  memcpy(salt, "mnemonic", 8);
  memcpy(salt + 8, passphrase, passphraselen);

  cmd[0] = mode;
  // salt LV
  cmd[1] = (passphraselen + 8) & 0xFF;
  cmd[2] = ((passphraselen + 8) >> 8) & 0xFF;
  memcpy(cmd + 3, salt, passphraselen + 8);
  MI2CDRV_Transmit(MI2C_CMD_WR_PIN, MNEMONIC_INDEX_TOSEED, cmd,
                   (passphraselen + 8) + 3, seed, &resplen, MI2C_ENCRYPT,
                   SET_SESTORE_DATA);
  return;
}

bool se_ecdsa_get_pubkey(uint32_t *address, uint8_t count, uint8_t *pubkey) {
  rtt_log_print("SE get pubkey");
  uint8_t resp[256];
  uint16_t resp_len;
  if (MI2C_OK != MI2CDRV_Transmit(MI2C_CMD_ECC_EDDSA, EDDSA_INDEX_CHILDKEY,
                                  (uint8_t *)address, count * 4, resp,
                                  &resp_len, MI2C_PLAIN, SET_SESTORE_DATA)) {
    return false;
  }
  memcpy(pubkey, resp + 1 + 4 + 32 + 33, 33);
  return true;
}

bool se_set_value(const uint16_t key, const void *val_dest, uint16_t len) {
  rtt_log_print("SE set key=%x", key);
  uint8_t flag = key >> 8;
  if (MI2C_OK != MI2CDRV_Transmit(MI2C_CMD_WR_PIN, (key & 0xFF),
                                  (uint8_t *)val_dest, len, NULL, 0,
                                  (flag & MI2C_PLAIN), SET_SESTORE_DATA)) {
    rtt_log_print("SE set key failed");
    return false;
  }
  rtt_log_print("SE set key suucess");
  return true;
}

bool se_get_value(const uint16_t key, void *val_dest, uint16_t max_len,
                  uint16_t *len) {
  rtt_log_print("SE get key=%x value", key);
  uint8_t flag = key >> 8;
  if (MI2C_OK != MI2CDRV_Transmit(MI2C_CMD_WR_PIN, (key & 0xFF), NULL, 0,
                                  val_dest, len, (flag & MI2C_PLAIN),
                                  GET_SESTORE_DATA)) {
    rtt_log_print("SE get key failed");
    return false;
  }
  if (*len > max_len) {
    return false;
  }
  rtt_log_print("SE get key suucess");
  return true;
}
bool se_delete_key(const uint16_t key) {
  rtt_log_print("SE delete key=%x", key);
  if (MI2C_OK != MI2CDRV_Transmit(MI2C_CMD_WR_PIN, (key & 0xFF), NULL, 0, NULL,
                                  0, MI2C_PLAIN, DELETE_SESTORE_DATA)) {
    rtt_log_print("SE delelte key failed");
    return false;
  }
  rtt_log_print("SE delelte key suucess");
  return true;
}

void se_reset_storage(const uint16_t key) {
  rtt_log_print("SE reset storage");
  if (MI2C_OK == MI2CDRV_Transmit(MI2C_CMD_WR_PIN, (key & 0xFF), NULL, 0, NULL,
                                  NULL, MI2C_ENCRYPT, SET_SESTORE_DATA)) {
    rtt_log_print("SE reset suucess");
  } else
    rtt_log_print("SE reset failed");
}
