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

static bool fsm_ethereumCheckPath(uint32_t address_n_count,
                                  const uint32_t *address_n, bool pubkey_export,
                                  const EthereumNetworkInfo *network) {
  if (ethereum_path_check(address_n_count, address_n, pubkey_export, network)) {
    return true;
  }

  if (config_getSafetyCheckLevel() == SafetyCheckLevel_Strict) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Forbidden key path"));
    return false;
  }

  return fsm_layoutPathWarning();
}

static const EthereumDefinitionsDecoded *get_definitions(
    bool has_definitions, const EthereumDefinitions *definitions,
    uint64_t chain_id, const char *to) {
  const EncodedNetwork *encoded_network = NULL;
  const EncodedToken *encoded_token = NULL;
  if (has_definitions && definitions) {
    if (definitions->has_encoded_network) {
      encoded_network = &definitions->encoded_network;
    }
    if (definitions->has_encoded_token) {
      encoded_token = &definitions->encoded_token;
    }
  }

  return ethereum_get_definitions(encoded_network, encoded_token, chain_id,
                                  SLIP44_UNKNOWN, to);
}

static const EthereumNetworkInfo *get_network_definition_only(
    bool has_encoded_network, const EncodedNetwork *encoded_network,
    const uint32_t slip44) {
  const EncodedNetwork *en = NULL;
  if (has_encoded_network) {
    en = encoded_network;
  }

  const EthereumDefinitionsDecoded *defs =
      ethereum_get_definitions(en, NULL, CHAIN_ID_UNKNOWN, slip44, NULL);

  return defs ? defs->network : NULL;
}

void fsm_msgEthereumGetPublicKey(const EthereumGetPublicKey *msg) {
  RESP_INIT(EthereumPublicKey);

  CHECK_INITIALIZED

  CHECK_PIN

  // we use Bitcoin-like format for ETH
  const CoinInfo *coin = fsm_getCoin(true, "Bitcoin");
  if (!coin) return;

  // Only allow m/44' and m/45' subtrees. This allows usage with _any_ SLIP-44
  // (Ethereum or otherwise), plus the Casa multisig subtree. Anything else must
  // go through (a) GetPublicKey or (b) a dedicated coin-specific message.
  if (!msg->address_n_count || (msg->address_n[0] != (44 | PATH_HARDENED) &&
                                msg->address_n[0] != (45 | PATH_HARDENED))) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Invalid path for EthereumGetPublicKey"));
    layoutHome();
    return;
  }

  const char *curve = coin->curve_name;
  uint32_t fingerprint;
  HDNode *node = fsm_getDerivedNode(curve, msg->address_n, msg->address_n_count,
                                    &fingerprint);
  if (!node) return;

  if (hdnode_fill_public_key(node) != 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to derive public key"));
    layoutHome();
    return;
  }

  if (msg->has_show_display && msg->show_display) {
    layoutPublicKey(node->public_key);
    if (!protectButton(ButtonRequestType_ButtonRequest_PublicKey, true)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
  }

  resp->node.depth = node->depth;
  resp->node.fingerprint = fingerprint;
  resp->node.child_num = node->child_num;
  resp->node.chain_code.size = 32;
  memcpy(resp->node.chain_code.bytes, node->chain_code, 32);
  resp->node.has_private_key = false;
  resp->node.public_key.size = 33;
  memcpy(resp->node.public_key.bytes, node->public_key, 33);

  hdnode_serialize_public(node, fingerprint, coin->xpub_magic, resp->xpub,
                          sizeof(resp->xpub));

  msg_write(MessageType_MessageType_EthereumPublicKey, resp);
  layoutHome();
}

void fsm_msgEthereumSignTx(const EthereumSignTx *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  const EthereumDefinitionsDecoded *defs =
      get_definitions(msg->has_definitions, &msg->definitions, msg->chain_id,
                      msg->has_to ? msg->to : NULL);

  if (!defs || !fsm_ethereumCheckPath(msg->address_n_count, msg->address_n,
                                      false, defs->network)) {
    layoutHome();
    return;
  }

  const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  ethereum_signing_init(msg, node, defs);
}

void fsm_msgEthereumSignTxEIP1559(const EthereumSignTxEIP1559 *msg) {
  CHECK_INITIALIZED

  CHECK_PIN

  const EthereumDefinitionsDecoded *defs =
      get_definitions(msg->has_definitions, &msg->definitions, msg->chain_id,
                      msg->has_to ? msg->to : NULL);

  if (!defs || !fsm_ethereumCheckPath(msg->address_n_count, msg->address_n,
                                      false, defs->network)) {
    layoutHome();
    return;
  }

  const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  ethereum_signing_init_eip1559(msg, node, defs);
}

void fsm_msgEthereumTxAck(const EthereumTxAck *msg) {
  CHECK_UNLOCKED

  ethereum_signing_txack(msg);
}

void fsm_msgEthereumGetAddress(const EthereumGetAddress *msg) {
  RESP_INIT(EthereumAddress);

  CHECK_INITIALIZED

  CHECK_PIN

  uint32_t slip44 = (msg->address_n_count > 1)
                        ? (msg->address_n[1] & PATH_UNHARDEN_MASK)
                        : SLIP44_UNKNOWN;

  const EthereumNetworkInfo *network = get_network_definition_only(
      msg->has_encoded_network, (const EncodedNetwork *)&msg->encoded_network,
      slip44);

  if (!network || !fsm_ethereumCheckPath(msg->address_n_count, msg->address_n,
                                         false, network)) {
    layoutHome();
    return;
  }

  const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  uint8_t pubkeyhash[20];

  if (!hdnode_get_ethereum_pubkeyhash(node, pubkeyhash)) {
    layoutHome();
    return;
  }
  bool rskip60 = false;
  uint64_t chain_id = 0;
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
  ethereum_address_checksum(pubkeyhash, resp->address, rskip60, chain_id);
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

  CHECK_PIN

  uint32_t slip44 = (msg->address_n_count > 1)
                        ? (msg->address_n[1] & PATH_UNHARDEN_MASK)
                        : SLIP44_UNKNOWN;

  const EthereumNetworkInfo *network = get_network_definition_only(
      msg->has_encoded_network, (const EncodedNetwork *)&msg->encoded_network,
      slip44);

  if (!network || !fsm_ethereumCheckPath(msg->address_n_count, msg->address_n,
                                         false, network)) {
    layoutHome();
    return;
  }

  const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  uint8_t pubkeyhash[20] = {0};
  if (!hdnode_get_ethereum_pubkeyhash(node, pubkeyhash)) {
    layoutHome();
    return;
  }

  ethereum_address_checksum(pubkeyhash, resp->address, false, 0);
  // ethereum_address_checksum adds trailing zero

  layoutVerifyAddress(NULL, resp->address);
  if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  if (!fsm_layoutSignMessage(msg->message.bytes, msg->message.size)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  ethereum_message_sign(msg, node, resp);
  layoutHome();
}

void fsm_msgEthereumVerifyMessage(const EthereumVerifyMessage *msg) {
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

  if (!fsm_layoutVerifyMessage(msg->message.bytes, msg->message.size)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  layoutDialogSwipe(&bmp_icon_ok, NULL, _("Continue"), NULL, NULL,
                    _("The signature is valid."), NULL, NULL, NULL, NULL);
  if (!protectButton(ButtonRequestType_ButtonRequest_Other, true)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  fsm_sendSuccess(_("Message verified"));

  layoutHome();
}

void fsm_msgEthereumSignTypedHash(const EthereumSignTypedHash *msg) {
  RESP_INIT(EthereumTypedDataSignature);

  CHECK_INITIALIZED

  CHECK_PIN

  if (msg->domain_separator_hash.size != 32 ||
      (msg->has_message_hash && msg->message_hash.size != 32)) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Invalid hash length"));
    return;
  }

  uint32_t slip44 = (msg->address_n_count > 1)
                        ? (msg->address_n[1] & PATH_UNHARDEN_MASK)
                        : SLIP44_UNKNOWN;

  const EthereumNetworkInfo *network = get_network_definition_only(
      msg->has_encoded_network, (const EncodedNetwork *)&msg->encoded_network,
      slip44);

  if (!network || !fsm_ethereumCheckPath(msg->address_n_count, msg->address_n,
                                         false, network)) {
    layoutHome();
    return;
  }

  layoutDialogSwipe(&bmp_icon_warning, _("Abort"), _("Continue"), NULL,
                    _("Unable to show"), _("EIP-712 data."), NULL,
                    _("Sign at your own risk."), NULL, NULL);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  uint8_t pubkeyhash[20] = {0};
  if (!hdnode_get_ethereum_pubkeyhash(node, pubkeyhash)) {
    layoutHome();
    return;
  }

  ethereum_address_checksum(pubkeyhash, resp->address, false, 0);
  // ethereum_address_checksum adds trailing zero

  layoutVerifyAddress(NULL, resp->address);
  if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  layoutConfirmHash(&bmp_icon_warning, _("EIP-712 domain hash"),
                    msg->domain_separator_hash.bytes, 32);
  if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  // No message hash when setting primaryType="EIP712Domain"
  // https://ethereum-magicians.org/t/eip-712-standards-clarification-primarytype-as-domaintype/3286
  if (msg->has_message_hash) {
    layoutConfirmHash(&bmp_icon_warning, _("EIP-712 message hash"),
                      msg->message_hash.bytes, 32);
    if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
  }

  ethereum_typed_hash_sign(msg, node, resp);
  layoutHome();
}
