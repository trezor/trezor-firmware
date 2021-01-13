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

void fsm_msgLiskGetAddress(const LiskGetAddress *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  RESP_INIT(LiskAddress);

  HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;

  resp->has_address = true;
  hdnode_fill_public_key(node);
  lisk_get_address_from_public_key(&node->public_key[1], resp->address);

  if (msg->has_show_display && msg->show_display) {
    if (!fsm_layoutAddress(resp->address, _("Address:"), true, 0,
                           msg->address_n, msg->address_n_count, false, NULL, 0,
                           0, NULL)) {
      return;
    }
  }

  msg_write(MessageType_MessageType_LiskAddress, resp);

  layoutHome();
}

void fsm_msgLiskGetPublicKey(const LiskGetPublicKey *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  RESP_INIT(LiskPublicKey);

  HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;

  hdnode_fill_public_key(node);

  resp->has_public_key = true;
  resp->public_key.size = 32;

  if (msg->has_show_display && msg->show_display) {
    layoutLiskPublicKey(&node->public_key[1]);
    if (!protectButton(ButtonRequestType_ButtonRequest_PublicKey, true)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
  }

  memcpy(&resp->public_key.bytes, &node->public_key[1],
         sizeof(resp->public_key.bytes));

  msg_write(MessageType_MessageType_LiskPublicKey, resp);

  layoutHome();
}

void fsm_msgLiskSignMessage(const LiskSignMessage *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  RESP_INIT(LiskMessageSignature);

  HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;

  hdnode_fill_public_key(node);

  lisk_sign_message(node, msg, resp);

  msg_write(MessageType_MessageType_LiskMessageSignature, resp);

  layoutHome();
}

void fsm_msgLiskVerifyMessage(const LiskVerifyMessage *msg) {
  if (lisk_verify_message(msg)) {
    char address[MAX_LISK_ADDRESS_SIZE];
    lisk_get_address_from_public_key((const uint8_t *)&msg->public_key,
                                     address);

    layoutLiskVerifyAddress(address);
    if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
    layoutVerifyMessage(msg->message.bytes, msg->message.size);
    if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
    fsm_sendSuccess(_("Message verified"));
  } else {
    fsm_sendFailure(FailureType_Failure_DataError, _("Invalid signature"));
  }

  layoutHome();
}

void fsm_msgLiskSignTx(LiskSignTx *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  RESP_INIT(LiskSignedTx);

  HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;

  hdnode_fill_public_key(node);

  lisk_sign_tx(node, msg, resp);

  msg_write(MessageType_MessageType_LiskSignedTx, resp);

  layoutHome();
}
