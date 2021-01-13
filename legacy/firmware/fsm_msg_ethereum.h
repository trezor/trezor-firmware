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

void fsm_msgEthereumGetPublicKey(const EthereumGetPublicKey *msg) {
  RESP_INIT(EthereumPublicKey);

  CHECK_INITIALIZED

  CHECK_PIN

  // we use Bitcoin-like format for ETH
  const CoinInfo *coin = fsm_getCoin(true, "Bitcoin");
  if (!coin) return;

  const char *curve = coin->curve_name;
  uint32_t fingerprint;
  HDNode *node = fsm_getDerivedNode(curve, msg->address_n, msg->address_n_count,
                                    &fingerprint);
  if (!node) return;
  hdnode_fill_public_key(node);

  if (msg->has_show_display && msg->show_display) {
    layoutPublicKey(node->public_key);
    if (!protectButton(ButtonRequestType_ButtonRequest_PublicKey, true)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
  }

  resp->has_node = true;
  resp->node.depth = node->depth;
  resp->node.fingerprint = fingerprint;
  resp->node.child_num = node->child_num;
  resp->node.chain_code.size = 32;
  memcpy(resp->node.chain_code.bytes, node->chain_code, 32);
  resp->node.has_private_key = false;
  resp->node.public_key.size = 33;
  memcpy(resp->node.public_key.bytes, node->public_key, 33);

  resp->has_xpub = true;
  hdnode_serialize_public(node, fingerprint, coin->xpub_magic, resp->xpub,
                          sizeof(resp->xpub));

  msg_write(MessageType_MessageType_EthereumPublicKey, resp);
  layoutHome();
}

void fsm_msgEthereumSignTx(EthereumSignTx *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  ethereum_signing_init(msg, node);
}

void fsm_msgEthereumTxAck(const EthereumTxAck *msg) {
  ethereum_signing_txack(msg);
}

void fsm_msgEthereumGetAddress(const EthereumGetAddress *msg) {
  RESP_INIT(EthereumAddress);

  CHECK_INITIALIZED

  CHECK_PIN

  const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  uint8_t pubkeyhash[20];

  if (!hdnode_get_ethereum_pubkeyhash(node, pubkeyhash)) return;

  uint32_t slip44 =
      (msg->address_n_count > 1) ? (msg->address_n[1] & 0x7fffffff) : 0;
  bool rskip60 = false;
  uint32_t chain_id = 0;
  // constants from trezor-common/defs/ethereum/networks.json
  switch (slip44) {
    case 137:
      rskip60 = true;
      chain_id = 30;
      break;
    case 37310:
      rskip60 = true;
      chain_id = 31;
      break;
  }

  resp->has_address = true;
  resp->address[0] = '0';
  resp->address[1] = 'x';
  ethereum_address_checksum(pubkeyhash, resp->address + 2, rskip60, chain_id);
  // ethereum_address_checksum adds trailing zero

  if (msg->has_show_display && msg->show_display) {
    char desc[16];
    strlcpy(desc, "Address:", sizeof(desc));

    if (!fsm_layoutAddress(resp->address, desc, false, 0, msg->address_n,
                           msg->address_n_count, true, NULL, 0, 0, NULL)) {
      return;
    }
  }

  msg_write(MessageType_MessageType_EthereumAddress, resp);
  layoutHome();
}

void fsm_msgEthereumSignMessage(const EthereumSignMessage *msg) {
  RESP_INIT(EthereumMessageSignature);

  CHECK_INITIALIZED

  layoutSignMessage(msg->message.bytes, msg->message.size);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  CHECK_PIN

  const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  ethereum_message_sign(msg, node, resp);
  layoutHome();
}

void fsm_msgEthereumVerifyMessage(const EthereumVerifyMessage *msg) {
  CHECK_PARAM(msg->has_address, _("No address provided"));
  CHECK_PARAM(msg->has_message, _("No message provided"));

  if (ethereum_message_verify(msg) != 0) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Invalid signature"));
    return;
  }

  uint8_t pubkeyhash[20];
  if (!ethereum_parse(msg->address, pubkeyhash)) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Invalid address"));
    return;
  }

  layoutVerifyAddress(NULL, msg->address);
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

  layoutHome();
}
