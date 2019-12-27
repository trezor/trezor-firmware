/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2018 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#if DEBUG_LINK

void fsm_msgDebugLinkGetState(const DebugLinkGetState *msg) {
  (void)msg;

  // Do not use RESP_INIT because it clears msg_resp, but another message
  // might be being handled
  DebugLinkState resp;
  memzero(&resp, sizeof(resp));

  resp.has_layout = true;
  resp.layout.size = OLED_BUFSIZE;
  memcpy(resp.layout.bytes, oledGetBuffer(), OLED_BUFSIZE);

  resp.has_pin = config_getPin(resp.pin, sizeof(resp.pin));

  resp.has_matrix = true;
  strlcpy(resp.matrix, pinmatrix_get(), sizeof(resp.matrix));

  resp.has_reset_entropy = true;
  resp.reset_entropy.size = reset_get_int_entropy(resp.reset_entropy.bytes);

  resp.has_reset_word = true;
  strlcpy(resp.reset_word, reset_get_word(), sizeof(resp.reset_word));

  resp.has_recovery_fake_word = true;
  strlcpy(resp.recovery_fake_word, recovery_get_fake_word(),
          sizeof(resp.recovery_fake_word));

  resp.has_recovery_word_pos = true;
  resp.recovery_word_pos = recovery_get_word_pos();

  resp.has_mnemonic_secret = config_getMnemonicBytes(
      resp.mnemonic_secret.bytes, sizeof(resp.mnemonic_secret.bytes),
      &resp.mnemonic_secret.size);
  resp.mnemonic_type = 0;  // BIP-39

  resp.has_node = config_dumpNode(&(resp.node));

  resp.has_passphrase_protection =
      config_getPassphraseProtection(&(resp.passphrase_protection));

  msg_debug_write(MessageType_MessageType_DebugLinkState, &resp);
}

void fsm_msgDebugLinkStop(const DebugLinkStop *msg) { (void)msg; }

void fsm_msgDebugLinkMemoryRead(const DebugLinkMemoryRead *msg) {
  RESP_INIT(DebugLinkMemory);

  uint32_t length = 1024;
  if (msg->has_length && msg->length < length) length = msg->length;
  resp->has_memory = true;
  memcpy(resp->memory.bytes, FLASH_PTR(msg->address), length);
  resp->memory.size = length;
  msg_debug_write(MessageType_MessageType_DebugLinkMemory, resp);
}

void fsm_msgDebugLinkMemoryWrite(const DebugLinkMemoryWrite *msg) {
  uint32_t length = msg->memory.size;
  if (msg->flash) {
    svc_flash_unlock();
    svc_flash_program(FLASH_CR_PROGRAM_X32);
    for (uint32_t i = 0; i < length; i += 4) {
      uint32_t word;
      memcpy(&word, msg->memory.bytes + i, 4);
      flash_write32(msg->address + i, word);
    }
    uint32_t dummy = svc_flash_lock();
    (void)dummy;
  } else {
#if !EMULATOR
    memcpy((void *)msg->address, msg->memory.bytes, length);
#endif
  }
}

void fsm_msgDebugLinkFlashErase(const DebugLinkFlashErase *msg) {
  svc_flash_unlock();
  svc_flash_erase_sector(msg->sector);
  uint32_t dummy = svc_flash_lock();
  (void)dummy;
}
#endif
