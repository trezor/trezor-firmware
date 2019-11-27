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

void fsm_msgVsysGetAddress(const VsysGetAddress *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  RESP_INIT(VsysAddress);

  HDNode *node = fsm_getDerivedNode(CURVE25519_NAME, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;

  resp->has_address = true;
  strcpy(resp->protocol, PROTOCOL);
  strcpy(resp->opc, OPC_ACCOUNT);
  resp->api = ACCOUNT_API_VER;

  hdnode_fill_public_key(node);
  char network_byte = get_network_byte(msg->address_n, msg->address_n_count);
  vsys_get_address_from_public_key(&node->public_key[1], network_byte, resp->address);

  if (msg->has_show_display && msg->show_display) {
    if (!fsm_layoutAddress(resp->address, _("Address:"), true, 0,
                           msg->address_n, msg->address_n_count, false)) {
      return;
    }
  }

  msg_write(MessageType_MessageType_VsysAddress, resp);

  layoutHome();
}

void fsm_msgVsysGetPublicKey(const VsysGetPublicKey *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  RESP_INIT(VsysPublicKey);

  HDNode *node = fsm_getDerivedNode(CURVE25519_NAME, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;

  hdnode_fill_public_key(node);

  resp->has_public_key = true;
  resp->has_address = true;
  strcpy(resp->protocol, PROTOCOL);
  strcpy(resp->opc, OPC_ACCOUNT);
  resp->api = ACCOUNT_API_VER;

  if (msg->has_show_display && msg->show_display) {
    layoutVsysPublicKey(&node->public_key[1]);
    if (!protectButton(ButtonRequestType_ButtonRequest_PublicKey, true)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
  }

  size_t public_key_size;
  b58enc(resp->public_key, &public_key_size, &node->public_key[1], 32);

  char network_byte = get_network_byte(msg->address_n, msg->address_n_count);
  vsys_get_address_from_public_key(&node->public_key[1], network_byte, resp->address);

  msg_write(MessageType_MessageType_VsysPublicKey, resp);

  layoutHome();
}

void fsm_msgVsysSignTx(VsysSignTx *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  RESP_INIT(VsysSignedTx);

  HDNode *node = fsm_getDerivedNode(CURVE25519_NAME, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;

  hdnode_fill_public_key(node);

  layoutVsysRequireConfirmTx(msg->recipient, msg->amount);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, true)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  if (vsys_sign_tx(node, msg, resp)) {
    msg_write(MessageType_MessageType_VsysSignedTx, resp);
  }

  layoutHome();
}
