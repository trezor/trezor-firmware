/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
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

void fsm_msgNEMGetAddress(NEMGetAddress *msg) {
  if (!msg->has_network) {
    msg->network = NEM_NETWORK_MAINNET;
  }

  const char *network;
  CHECK_PARAM((network = nem_network_name(msg->network)),
              _("Invalid NEM network"));

  CHECK_INITIALIZED
  CHECK_PIN

  RESP_INIT(NEMAddress);

  HDNode *node = fsm_getDerivedNode(ED25519_KECCAK_NAME, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;

  if (!hdnode_get_nem_address(node, msg->network, resp->address)) return;

  if (msg->has_show_display && msg->show_display) {
    char desc[16];
    strlcpy(desc, network, sizeof(desc));
    strlcat(desc, ":", sizeof(desc));

    if (!fsm_layoutAddress(resp->address, desc, true, 0, msg->address_n,
                           msg->address_n_count, false, NULL, 0, 0, NULL)) {
      return;
    }
  }

  msg_write(MessageType_MessageType_NEMAddress, resp);
  layoutHome();
}

void fsm_msgNEMSignTx(NEMSignTx *msg) {
  const char *reason;

#define NEM_CHECK_PARAM(s) CHECK_PARAM((reason = (s)) == NULL, reason)
#define NEM_CHECK_PARAM_WHEN(b, s) \
  CHECK_PARAM(!(b) || (reason = (s)) == NULL, reason)

  CHECK_PARAM(msg->has_transaction, _("No common provided"));

  // Ensure exactly one transaction is provided
  unsigned int provided = msg->has_transfer + msg->has_provision_namespace +
                          msg->has_mosaic_creation + msg->has_supply_change +
                          msg->has_aggregate_modification +
                          msg->has_importance_transfer;
  CHECK_PARAM(provided != 0, _("No transaction provided"));
  CHECK_PARAM(provided == 1, _("More than one transaction provided"));

  NEM_CHECK_PARAM(nem_validate_common(&msg->transaction, false));
  NEM_CHECK_PARAM_WHEN(
      msg->has_transfer,
      nem_validate_transfer(&msg->transfer, msg->transaction.network));
  NEM_CHECK_PARAM_WHEN(
      msg->has_provision_namespace,
      nem_validate_provision_namespace(&msg->provision_namespace,
                                       msg->transaction.network));
  NEM_CHECK_PARAM_WHEN(msg->has_mosaic_creation,
                       nem_validate_mosaic_creation(&msg->mosaic_creation,
                                                    msg->transaction.network));
  NEM_CHECK_PARAM_WHEN(msg->has_supply_change,
                       nem_validate_supply_change(&msg->supply_change));
  NEM_CHECK_PARAM_WHEN(msg->has_aggregate_modification,
                       nem_validate_aggregate_modification(
                           &msg->aggregate_modification, !msg->has_multisig));
  NEM_CHECK_PARAM_WHEN(
      msg->has_importance_transfer,
      nem_validate_importance_transfer(&msg->importance_transfer));

  bool cosigning = msg->has_cosigning && msg->cosigning;
  if (msg->has_multisig) {
    NEM_CHECK_PARAM(nem_validate_common(&msg->multisig, true));

    CHECK_PARAM(msg->transaction.network == msg->multisig.network,
                _("Inner transaction network is different"));
  } else {
    CHECK_PARAM(!cosigning, _("No multisig transaction to cosign"));
  }

  CHECK_INITIALIZED
  CHECK_PIN

  const char *network = nem_network_name(msg->transaction.network);

  if (msg->has_multisig) {
    char address[NEM_ADDRESS_SIZE + 1];
    nem_get_address(msg->multisig.signer.bytes, msg->multisig.network, address);

    if (!nem_askMultisig(address, network, cosigning, msg->transaction.fee)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled,
                      _("Signing cancelled by user"));
      layoutHome();
      return;
    }
  }

  RESP_INIT(NEMSignedTx);

  HDNode *node =
      fsm_getDerivedNode(ED25519_KECCAK_NAME, msg->transaction.address_n,
                         msg->transaction.address_n_count, NULL);
  if (!node) return;

  hdnode_fill_public_key(node);

  const NEMTransactionCommon *common =
      msg->has_multisig ? &msg->multisig : &msg->transaction;

  char address[NEM_ADDRESS_SIZE + 1];
  hdnode_get_nem_address(node, common->network, address);

  if (msg->has_transfer) {
    nem_canonicalizeMosaics(&msg->transfer);
  }

  if (msg->has_transfer && !nem_askTransfer(common, &msg->transfer, network)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled,
                    _("Signing cancelled by user"));
    layoutHome();
    return;
  }

  if (msg->has_provision_namespace &&
      !nem_askProvisionNamespace(common, &msg->provision_namespace, network)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled,
                    _("Signing cancelled by user"));
    layoutHome();
    return;
  }

  if (msg->has_mosaic_creation &&
      !nem_askMosaicCreation(common, &msg->mosaic_creation, network, address)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled,
                    _("Signing cancelled by user"));
    layoutHome();
    return;
  }

  if (msg->has_supply_change &&
      !nem_askSupplyChange(common, &msg->supply_change, network)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled,
                    _("Signing cancelled by user"));
    layoutHome();
    return;
  }

  if (msg->has_aggregate_modification &&
      !nem_askAggregateModification(common, &msg->aggregate_modification,
                                    network, !msg->has_multisig)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled,
                    _("Signing cancelled by user"));
    layoutHome();
    return;
  }

  if (msg->has_importance_transfer &&
      !nem_askImportanceTransfer(common, &msg->importance_transfer, network)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled,
                    _("Signing cancelled by user"));
    layoutHome();
    return;
  }

  nem_transaction_ctx context;
  nem_transaction_start(&context, &node->public_key[1], resp->data.bytes,
                        sizeof(resp->data.bytes));

  if (msg->has_multisig) {
    uint8_t buffer[sizeof(resp->data.bytes)];

    nem_transaction_ctx inner;
    nem_transaction_start(&inner, msg->multisig.signer.bytes, buffer,
                          sizeof(buffer));

    if (msg->has_transfer &&
        !nem_fsmTransfer(&inner, NULL, &msg->multisig, &msg->transfer)) {
      layoutHome();
      return;
    }

    if (msg->has_provision_namespace &&
        !nem_fsmProvisionNamespace(&inner, &msg->multisig,
                                   &msg->provision_namespace)) {
      layoutHome();
      return;
    }

    if (msg->has_mosaic_creation &&
        !nem_fsmMosaicCreation(&inner, &msg->multisig, &msg->mosaic_creation)) {
      layoutHome();
      return;
    }

    if (msg->has_supply_change &&
        !nem_fsmSupplyChange(&inner, &msg->multisig, &msg->supply_change)) {
      layoutHome();
      return;
    }

    if (msg->has_aggregate_modification &&
        !nem_fsmAggregateModification(&inner, &msg->multisig,
                                      &msg->aggregate_modification)) {
      layoutHome();
      return;
    }

    if (msg->has_importance_transfer &&
        !nem_fsmImportanceTransfer(&inner, &msg->multisig,
                                   &msg->importance_transfer)) {
      layoutHome();
      return;
    }

    if (!nem_fsmMultisig(&context, &msg->transaction, &inner, cosigning)) {
      layoutHome();
      return;
    }
  } else {
    if (msg->has_transfer &&
        !nem_fsmTransfer(&context, node, &msg->transaction, &msg->transfer)) {
      layoutHome();
      return;
    }

    if (msg->has_provision_namespace &&
        !nem_fsmProvisionNamespace(&context, &msg->transaction,
                                   &msg->provision_namespace)) {
      layoutHome();
      return;
    }

    if (msg->has_mosaic_creation &&
        !nem_fsmMosaicCreation(&context, &msg->transaction,
                               &msg->mosaic_creation)) {
      layoutHome();
      return;
    }

    if (msg->has_supply_change &&
        !nem_fsmSupplyChange(&context, &msg->transaction,
                             &msg->supply_change)) {
      layoutHome();
      return;
    }

    if (msg->has_aggregate_modification &&
        !nem_fsmAggregateModification(&context, &msg->transaction,
                                      &msg->aggregate_modification)) {
      layoutHome();
      return;
    }

    if (msg->has_importance_transfer &&
        !nem_fsmImportanceTransfer(&context, &msg->transaction,
                                   &msg->importance_transfer)) {
      layoutHome();
      return;
    }
  }

  resp->has_data = true;
  resp->data.size =
      nem_transaction_end(&context, node->private_key, resp->signature.bytes);

  resp->has_signature = true;
  resp->signature.size = sizeof(ed25519_signature);

  msg_write(MessageType_MessageType_NEMSignedTx, resp);
  layoutHome();
}

void fsm_msgNEMDecryptMessage(NEMDecryptMessage *msg) {
  RESP_INIT(NEMDecryptedMessage);

  CHECK_INITIALIZED

  CHECK_PARAM(nem_network_name(msg->network), _("Invalid NEM network"));
  CHECK_PARAM(msg->has_payload, _("No payload provided"));
  CHECK_PARAM(msg->payload.size >= NEM_ENCRYPTED_PAYLOAD_SIZE(0),
              _("Invalid encrypted payload"));
  CHECK_PARAM(msg->has_public_key, _("No public key provided"));
  CHECK_PARAM(msg->public_key.size == 32, _("Invalid public key"));

  char address[NEM_ADDRESS_SIZE + 1];
  nem_get_address(msg->public_key.bytes, msg->network, address);

  layoutNEMDialog(&bmp_icon_question, _("Cancel"), _("Confirm"),
                  _("Decrypt message"), _("Confirm address?"), address);
  if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  CHECK_PIN

  const HDNode *node = fsm_getDerivedNode(ED25519_KECCAK_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  const uint8_t *salt = msg->payload.bytes;
  uint8_t *iv = &msg->payload.bytes[NEM_SALT_SIZE];

  const uint8_t *payload = &msg->payload.bytes[NEM_SALT_SIZE + AES_BLOCK_SIZE];
  size_t size = msg->payload.size - NEM_SALT_SIZE - AES_BLOCK_SIZE;

  // hdnode_nem_decrypt mutates the IV, so this will modify msg
  bool ret = hdnode_nem_decrypt(node, msg->public_key.bytes, iv, salt, payload,
                                size, resp->payload.bytes);
  if (!ret) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to decrypt payload"));
    layoutHome();
    return;
  }

  resp->has_payload = true;
  resp->payload.size = NEM_DECRYPTED_SIZE(resp->payload.bytes, size);

  layoutNEMTransferPayload(resp->payload.bytes, resp->payload.size, true);
  if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  msg_write(MessageType_MessageType_NEMDecryptedMessage, resp);
  layoutHome();
}
