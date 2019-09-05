/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2018 alepop <alepooop@gmail.com>
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

void fsm_msgHederaGetPublicKey(const HederaGetPublicKey *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  RESP_INIT(HederaPublicKey);

  HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;

  hdnode_fill_public_key(node);

  resp->has_public_key = true;
  resp->public_key.size = 32;

  if (msg->has_show_display && msg->show_display) {
    layoutHederaPublicKey(&node->public_key[1]);
    if (!protectButton(ButtonRequestType_ButtonRequest_PublicKey, true)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
  }

  memcpy(&resp->public_key.bytes, &node->public_key[1],
         sizeof(resp->public_key.bytes));

  msg_write(MessageType_MessageType_HederaPublicKey, resp);

  layoutHome();
}

void fsm_msgHederaSignTx(const HederaSignTx *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  RESP_INIT(HederaSignedTx);

  HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;

  hdnode_fill_public_key(node);

  hedera_sign_tx(node, msg, resp);

  msg_write(MessageType_MessageType_HederaSignedTx, resp);

  layoutHome();
}
